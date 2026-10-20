"""Agent workflow and RAG endpoints."""

from fastapi import APIRouter, Depends, Path

from app.api.dependencies import get_container
from app.api.schemas import AnalyzeRepositoryRequest, RagSearchRequest
from app.api.security import require_permission
from app.container import AppContainer
from app.core.security.rbac import Permission
from app.domain.agents import AgentDescriptor, AgentRun
from app.domain.models import ChangeScopeRequest, CompareMode
from app.rag.collections import Collection
from app.rag.store import RagHit

router = APIRouter()

_RUN = [Depends(require_permission(Permission.ANALYSIS_RUN))]
_READ = [Depends(require_permission(Permission.REPOSITORY_READ))]
_SEARCH = [Depends(require_permission(Permission.SEARCH_READ))]


@router.get(
    "/agents",
    response_model=list[AgentDescriptor],
    dependencies=_READ,
    tags=["agents"],
    summary="List the ten workflow agents in execution order",
)
def list_agents(container: AppContainer = Depends(get_container)) -> list[AgentDescriptor]:
    return container.agent_workflow().describe_agents()


@router.post(
    "/agent-runs",
    response_model=AgentRun,
    dependencies=_RUN,
    tags=["agents"],
    summary="Run the ten-agent workflow for a change scope (synchronous)",
)
def create_agent_run(
    body: AnalyzeRepositoryRequest,
    container: AppContainer = Depends(get_container),
) -> AgentRun:
    scope = ChangeScopeRequest(
        repo_path=body.repo_path,
        analysis_mode=body.analysis_mode,
        commit_id=body.commit_id,
        source_branch=body.source_branch,
        target_branch=body.target_branch,
        compare_mode=body.compare_mode or CompareMode.MERGE_BASE,
    )
    return container.agent_workflow().run(scope)


@router.get(
    "/agent-runs/{run_id}",
    response_model=AgentRun,
    dependencies=_READ,
    tags=["agents"],
    summary="Return a finished agent run with outputs and audit trail",
)
def get_agent_run(
    run_id: str = Path(min_length=1, max_length=64),
    container: AppContainer = Depends(get_container),
) -> AgentRun:
    return container.agent_workflow().get_run(run_id)


@router.post(
    "/rag/search",
    response_model=list[RagHit],
    dependencies=_SEARCH,
    tags=["rag"],
    summary="Search indexed RAG collections for similar records",
)
def rag_search(body: RagSearchRequest, container: AppContainer = Depends(get_container)) -> list[RagHit]:
    collections = body.collections or list(Collection)
    return container.retriever().search(
        body.query,
        collections=collections,
        top_k=body.top_k,
        repository=body.repository,
        source_type=body.source_type,
        min_similarity=body.min_similarity,
    )
