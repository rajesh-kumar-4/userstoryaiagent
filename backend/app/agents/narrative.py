"""Agents 8-9: story draft (LLM when configured) and criticality score."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import Agent, Draft
from app.agents.context import AgentSkipped, SharedContext
from app.core.exceptions import LLMProviderError
from app.core.llm.prompt_manager import PromptError
from app.core.redaction import redact_text
from app.domain.analysis import Severity, level_for_score
from app.rag.collections import Collection

logger = logging.getLogger(__name__)

MAX_FINDINGS_IN_PROMPT = 25
MAX_CRITERIA = 5
MAX_STORY_CHARS = 4000


class StoryGenerationAgent(Agent):
    index = 8
    name = "story_generation"
    description = "Drafts a user story and acceptance criteria for the change (LLM when configured)."
    collection = Collection.STORY_ANALYSIS

    def run(self, ctx: SharedContext) -> dict[str, Any]:
        record = ctx.require_repository()
        risk = ctx.output("risk_analysis")
        if not risk:
            raise AgentSkipped("risk analysis unavailable")
        areas = sorted({str(item["area"]) for item in ctx.output("git_diff").get("files", []) if item.get("area")})
        findings = risk.get("findings", [])[:MAX_FINDINGS_IN_PROMPT]
        criteria = _acceptance_criteria(findings)
        output: dict[str, Any] = {
            "source": "rule_based",
            "story": _rule_story(record.name, ctx.analysis_mode.value, areas, risk),
            "acceptance_criteria": criteria,
        }
        if self.deps.llm is None:
            return output
        findings_text = "\n".join(
            f"- [{item['severity']}] {item['category']}: {item['title']}" for item in findings
        ) or "none"
        try:
            messages = self.deps.prompts.render(
                "story_generation",
                {
                    "repository": record.name,
                    "analysis_mode": ctx.analysis_mode.value,
                    "risk_level": risk["risk_level"],
                    "risk_score": risk["risk_score"],
                    "changed_areas": ", ".join(areas) or "none",
                    "findings": redact_text(findings_text),
                },
            )
            response = self.deps.llm.complete(messages, temperature=0.2, max_tokens=400)
        except (LLMProviderError, PromptError) as exc:
            logger.warning("LLM story unavailable, using rule-based draft: %s", exc)
            return {**output, "warnings": [f"LLM story unavailable: {exc}"]}
        return {
            "source": "llm",
            "provider": response.provider,
            "story": response.content,
            "acceptance_criteria": criteria,
        }

    def documents(self, ctx: SharedContext, output: dict[str, Any]) -> list[Draft]:
        return [Draft(collection=Collection.STORY_ANALYSIS, text=str(output["story"])[:MAX_STORY_CHARS])]


class CriticalityAgent(Agent):
    index = 9
    name = "criticality"
    description = "Scores repository criticality from technology breadth, activity, and risk."
    collection = Collection.CRITICALITY_ANALYSIS

    def run(self, ctx: SharedContext) -> dict[str, Any]:
        record = ctx.require_repository()
        risk = ctx.output("risk_analysis")
        history = ctx.output("history_analysis")
        if not risk or not history:
            raise AgentSkipped("risk or history output unavailable")
        factors = {
            "technology_breadth": min(5 * len(record.technology_tags), 20),
            "contributor_breadth": min(4 * int(history["authors"]), 20),
            "commit_activity": min(int(history["commits"]) // 5, 20),
            "latest_risk": min(int(risk["risk_score"]) // 2, 30),
            "high_severity_findings": min(5 * int(risk["high_severity_count"]), 20),
        }
        score = min(100, sum(factors.values()))
        level = level_for_score(score)
        rationale, source = self._rationale(record.name, score, level, factors, int(history["commits"]))
        return {
            "score": score,
            "level": level.value,
            "factors": factors,
            "rationale": rationale,
            "rationale_source": source,
        }

    def _rationale(
        self,
        repository: str,
        score: int,
        level: Severity,
        factors: dict[str, int],
        commit_count: int,
    ) -> tuple[str, str]:
        top = sorted(((value, name) for name, value in factors.items() if value > 0), reverse=True)[:2]
        fallback = (
            f"Criticality {level.value} ({score}/100) across {commit_count} recent commit(s). "
            + (f"Largest contributors: {', '.join(name for _, name in top)}." if top else "No contributing factors.")
        )
        if self.deps.llm is None:
            return fallback, "rule_based"
        try:
            messages = self.deps.prompts.render(
                "criticality_rationale",
                {
                    "repository": repository,
                    "level": level.value,
                    "score": score,
                    "factors": ", ".join(f"{name}={value}" for name, value in factors.items()),
                    "context": f"recent commits={commit_count}",
                },
            )
            response = self.deps.llm.complete(messages, temperature=0.2, max_tokens=200)
            return response.content, "llm"
        except (LLMProviderError, PromptError) as exc:
            logger.warning("LLM rationale unavailable: %s", exc)
            return fallback, "rule_based"


def _rule_story(repository: str, mode: str, areas: list[str], risk: dict[str, Any]) -> str:
    scope = ", ".join(areas) if areas else "the changed files"
    return (
        f"As a maintainer of {repository}, I need the {mode} changes to {scope} reviewed "
        f"so that the {risk['risk_level']} risk ({risk['risk_score']}/100) is mitigated before release."
    )


def _acceptance_criteria(findings: list[dict[str, Any]]) -> list[str]:
    if not findings:
        return ["No high-risk findings remain for the changed files"]
    return [f"Resolve finding: {item['title']}" for item in findings[:MAX_CRITERIA]]
