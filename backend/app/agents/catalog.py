"""Agent catalog: the ten agents in execution order (indices 0-9)."""

from __future__ import annotations

from app.agents.base import Agent, AgentDeps
from app.agents.code_analysis import AstAnalysisAgent, DependencyAnalysisAgent, GitDiffAgent
from app.agents.discovery import RepositoryDiscoveryAgent
from app.agents.history import HistoryAnalysisAgent
from app.agents.narrative import CriticalityAgent, StoryGenerationAgent
from app.agents.risk_analysis import ImpactAnalysisAgent, RiskAnalysisAgent, SecurityAnalysisAgent

AGENT_CLASSES: tuple[type[Agent], ...] = (
    RepositoryDiscoveryAgent,
    GitDiffAgent,
    AstAnalysisAgent,
    DependencyAnalysisAgent,
    SecurityAnalysisAgent,
    ImpactAnalysisAgent,
    RiskAnalysisAgent,
    HistoryAnalysisAgent,
    StoryGenerationAgent,
    CriticalityAgent,
)


def build_agents(deps: AgentDeps) -> list[Agent]:
    agents = [cls(deps) for cls in AGENT_CLASSES]
    if [agent.index for agent in agents] != list(range(len(agents))):
        raise RuntimeError("agent indices must be contiguous and ordered")
    return agents
