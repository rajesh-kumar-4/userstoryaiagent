import pytest

from app.core.llm.prompt_manager import MAX_VARIABLE_CHARS, PromptError, PromptManager, PromptTemplate


def _analysis_variables(**overrides):
    values = {
        "repository": "billing-service",
        "analysis_mode": "PRE_COMMIT",
        "totals": "files_changed=1",
        "risk_level": "HIGH",
        "risk_score": 50,
        "findings": "- [HIGH] configuration_change: Configuration changed",
    }
    values.update(overrides)
    return values


def test_default_prompts_are_registered():
    assert PromptManager().names() == ["analysis_summary", "criticality_rationale", "story_generation"]


def test_render_returns_system_and_user_messages_with_untrusted_data_fence():
    messages = PromptManager().render("analysis_summary", _analysis_variables())

    assert [message.role for message in messages] == ["system", "user"]
    assert "untrusted" in messages[0].content
    assert "billing-service" in messages[1].content
    assert "<data>" in messages[1].content
    assert "(score 50)" in messages[1].content


def test_missing_variable_raises_prompt_error():
    variables = _analysis_variables()
    variables.pop("risk_level")

    with pytest.raises(PromptError, match="missing prompt variable: risk_level"):
        PromptManager().render("analysis_summary", variables)


def test_unknown_prompt_and_version_raise_prompt_error():
    manager = PromptManager()

    with pytest.raises(PromptError, match="unknown prompt: nope"):
        manager.get("nope")
    with pytest.raises(PromptError, match="unknown prompt version"):
        manager.get("analysis_summary", version=99)


def test_oversized_values_are_clipped():
    oversized = "x" * (MAX_VARIABLE_CHARS + 500)

    messages = PromptManager().render("analysis_summary", _analysis_variables(findings=oversized))

    assert "...[truncated]" in messages[1].content
    assert oversized not in messages[1].content


def test_duplicate_template_versions_are_rejected():
    template = PromptTemplate(name="dup", version=1, system="s", user="u")

    with pytest.raises(ValueError, match="duplicate prompt dup v1"):
        PromptManager([template, template])


def test_invalid_placeholder_is_reported_as_prompt_error():
    broken = PromptTemplate(name="broken", version=1, system="system", user="price $ value")

    with pytest.raises(PromptError, match="invalid prompt template: broken"):
        PromptManager([broken]).render("broken", {})
