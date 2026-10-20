"""Agent workflow: LangGraph orchestration of the ten agents, MCP tool registration, and run persistence.

Each agent is exposed as an MCP tool (`agent_<name>`). The graph invokes those tools, so direct MCP clients
and the workflow share one code path. Graph edges encode data dependencies; independent agents run in parallel.
"""

from __future__ import annotations

import hashlib
import logging
import operator
import time
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from app.agents.audit import AuditLogger
from app.agents.base import Agent, AgentDeps
from app.agents.catalog import build_agents
from app.agents.context import AgentSkipped, ContextManager, SharedContext
from app.core.events import EventBus
from app.core.redaction import redact_text
from app.domain.agents import AgentDescriptor, AgentRun, AgentStatus, AgentTrace, RunStatus
from app.domain.models import ChangeEvent, ChangeScopeRequest, EventType, utc_now
from app.mcp.registry import ToolArgumentError, ToolRegistry
from app.rag.store import VectorDocument, VectorStore

logger = logging.getLogger(__name__)

PERSIST_NODE = "persist_outputs"
MAX_TRACE_MESSAGE = 300
_SCOPE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "repo_path": {"type": "string", "description": "Repository id, name, or path inside the workspace"},
        "analysis_mode": {"type": "string", "enum": ["PRE_COMMIT", "POST_COMMIT", "BRANCH_ANALYSIS", "PR_ANALYSIS", "RELEASE_ANALYSIS"]},
        "commit_id": {"type": "string"},
        "source_branch": {"type": "string"},
        "target_branch": {"type": "string"},
        "compare_mode": {"type": "string", "enum": ["MERGE_BASE", "DIRECT"]},
    },
    "required": ["repo_path"],
}
_RUN_ID_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"run_id": {"type": "string", "minLength": 1, "maxLength": 64}},
    "required": ["run_id"],
}


class WorkflowState(TypedDict):
    run_id: str
    completed: Annotated[list[str], operator.add]


class AgentWorkflowManager:
    def __init__(
        self,
        *,
        tools: ToolRegistry,
        deps: AgentDeps,
        contexts: ContextManager,
        audit: AuditLogger,
        store: VectorStore,
        bus: EventBus,
    ) -> None:
        self._tools = tools
        self._contexts = contexts
        self._audit = audit
        self._store = store
        self._bus = bus
        self._agents: dict[str, Agent] = {agent.name: agent for agent in build_agents(deps)}
        self._graph = self._compile()
        self._register_tools()

    # ----- public API -------------------------------------------------------------------------

    def describe_agents(self) -> list[AgentDescriptor]:
        return [
            AgentDescriptor(
                index=agent.index,
                name=agent.name,
                tool=agent.tool_name,
                description=agent.description,
                collection=agent.collection.value if agent.collection else None,
            )
            for agent in sorted(self._agents.values(), key=lambda item: item.index)
        ]

    def run(self, request: ChangeScopeRequest) -> AgentRun:
        ctx = self._contexts.create(request)
        self._audit.record(ctx.run_id, "run_started", detail=f"mode={request.analysis_mode.value}")
        crashed = False
        try:
            self._graph.invoke({"run_id": ctx.run_id, "completed": []})
        except Exception:
            crashed = True
            logger.exception("agent workflow crashed (run %s)", ctx.run_id)
            self._audit.record(ctx.run_id, "run_crashed")
            self._contexts.add_warning(ctx.run_id, "workflow stopped unexpectedly; see audit trail")
        run = self._finalize(ctx, crashed=crashed)
        risk = run.outputs.get("risk_analysis", {})
        self._bus.publish(
            ChangeEvent(
                type=EventType.AGENT_RUN_COMPLETED,
                repository=run.repository or request.repo_path,
                payload={
                    "run_id": run.run_id,
                    "status": run.status.value,
                    "risk_level": risk.get("risk_level"),
                    "risk_score": risk.get("risk_score"),
                },
            )
        )
        return run

    def get_run(self, run_id: str) -> AgentRun:
        return self._contexts.get_run(run_id)

    def execute_agent(self, agent_name: str, run_id: str) -> dict[str, Any]:
        agent = self._agents[agent_name]
        ctx = self._contexts.get(run_id)
        self._audit.record(run_id, "agent_started", agent=agent.name)
        started = time.perf_counter()
        output: dict[str, Any] | None = None
        status = AgentStatus.COMPLETED
        message = ""
        try:
            output = agent.run(ctx)
        except AgentSkipped as exc:
            status = AgentStatus.SKIPPED
            message = str(exc)
        except Exception as exc:  # one failing agent must not stop the other branches
            logger.exception("agent %s failed (run %s)", agent.name, run_id)
            status = AgentStatus.FAILED
            message = f"{type(exc).__name__}: {exc}"
        duration_ms = int((time.perf_counter() - started) * 1000)
        message = redact_text(message)[:MAX_TRACE_MESSAGE]
        warnings = [f"{agent.name}: {item}" for item in (output or {}).get("warnings", [])]
        trace = AgentTrace(
            agent=agent.name,
            index=agent.index,
            status=status,
            duration_ms=duration_ms,
            message=message,
        )
        self._contexts.record(run_id, trace, output, warnings)
        self._audit.record(run_id, f"agent_{status.value.lower()}", agent=agent.name, detail=message)
        return {"agent": agent.name, "status": status.value, "duration_ms": duration_ms, "message": message}

    # ----- graph ------------------------------------------------------------------------------

    def _compile(self) -> Any:
        graph = StateGraph(WorkflowState)
        for name in self._agents:
            graph.add_node(name, self._agent_node(name))
        graph.add_node(PERSIST_NODE, self._persist_node)

        graph.add_edge(START, "repository_discovery")
        graph.add_edge("repository_discovery", "git_diff")
        graph.add_edge("git_diff", "ast_analysis")
        graph.add_edge("git_diff", "dependency_analysis")
        graph.add_edge("git_diff", "security_analysis")
        graph.add_edge("git_diff", "history_analysis")
        graph.add_edge(["ast_analysis", "dependency_analysis"], "impact_analysis")
        graph.add_edge(
            ["impact_analysis", "dependency_analysis", "security_analysis", "history_analysis"],
            "risk_analysis",
        )
        graph.add_edge("risk_analysis", "story_generation")
        graph.add_edge("risk_analysis", "criticality")
        graph.add_edge(["story_generation", "criticality"], PERSIST_NODE)
        graph.add_edge(PERSIST_NODE, END)
        return graph.compile()

    def _agent_node(self, name: str):
        def node(state: WorkflowState) -> dict[str, list[str]]:
            self._tools.call(f"agent_{name}", {"run_id": state["run_id"]})
            return {"completed": [name]}

        return node

    def _persist_node(self, state: WorkflowState) -> dict[str, list[str]]:
        self._persist(state["run_id"])
        return {"completed": [PERSIST_NODE]}

    # ----- persistence and finalization -------------------------------------------------------

    def _persist(self, run_id: str) -> None:
        ctx = self._contexts.get(run_id)
        repository = ctx.repository.id if ctx.repository else ctx.request.repo_path
        indexed = 0
        for agent in sorted(self._agents.values(), key=lambda item: item.index):
            trace = ctx.traces.get(agent.name)
            output = ctx.outputs.get(agent.name)
            if trace is None or trace.status is not AgentStatus.COMPLETED or output is None:
                continue
            try:
                for draft in agent.documents(ctx, output):
                    document = VectorDocument(
                        id=_document_id(repository, agent.name, draft.text),
                        text=draft.text,
                        metadata={
                            **draft.metadata,
                            "source_type": "agent_output",
                            "agent": agent.name,
                            "repository": repository,
                            "analysis_mode": ctx.analysis_mode.value,
                            "run_id": run_id,
                        },
                    )
                    indexed += self._store.upsert(draft.collection, [document])
            except Exception as exc:  # a RAG outage must not fail the analysis
                logger.warning("indexing skipped for agent %s: %s", agent.name, exc)
                self._contexts.add_warning(run_id, f"{agent.name}: indexing skipped ({type(exc).__name__})")
                self._audit.record(run_id, "index_failed", agent=agent.name, detail=f"{type(exc).__name__}: {exc}")
        self._audit.record(run_id, "documents_indexed", detail=str(indexed))

    def _finalize(self, ctx: SharedContext, *, crashed: bool) -> AgentRun:
        traces = sorted(ctx.traces.values(), key=lambda trace: trace.index)
        if crashed or ctx.change_set is None:
            status = RunStatus.FAILED
        elif any(trace.status is not AgentStatus.COMPLETED for trace in traces):
            status = RunStatus.PARTIAL
        else:
            status = RunStatus.COMPLETED
        self._audit.record(ctx.run_id, "run_finished", detail=status.value)
        run = AgentRun(
            run_id=ctx.run_id,
            repository=ctx.repository.id if ctx.repository else None,
            analysis_mode=ctx.analysis_mode,
            status=status,
            agents=traces,
            outputs={name: dict(output) for name, output in ctx.outputs.items()},
            warnings=list(ctx.warnings),
            audit=self._audit.for_run(ctx.run_id),
            started_at=ctx.started_at,
            finished_at=utc_now(),
        )
        self._contexts.finish(run)
        return run

    # ----- MCP tools --------------------------------------------------------------------------

    def _register_tools(self) -> None:
        for agent in self._agents.values():
            self._tools.register(
                agent.tool_name,
                agent.description,
                _RUN_ID_SCHEMA,
                self._agent_tool_handler(agent.name),
            )
        self._tools.register(
            "run_agent_workflow",
            "Runs all ten agents for a repository scope and returns the stored run.",
            _SCOPE_SCHEMA,
            self._run_tool,
        )
        self._tools.register(
            "get_agent_run",
            "Returns a finished agent run by id.",
            _RUN_ID_SCHEMA,
            lambda args: self.get_run(str(args["run_id"])).model_dump(mode="json"),
        )

    def _agent_tool_handler(self, name: str):
        return lambda args: self.execute_agent(name, str(args["run_id"]))

    def _run_tool(self, args: dict[str, Any]) -> dict[str, Any]:
        try:
            request = ChangeScopeRequest.model_validate(args)
        except ValidationError as exc:
            raise ToolArgumentError(f"invalid scope: {exc.errors()[0].get('msg')}") from exc
        return self.run(request).model_dump(mode="json")


def _document_id(repository: str, agent: str, text: str) -> str:
    digest = hashlib.sha256(f"{repository}\n{text}".encode("utf-8")).hexdigest()[:32]
    return f"{agent}:{digest}"
