import pytest

from app.core.redaction import REDACTED, redact_text, redact_url
from app.domain.branching import classify_branch
from app.domain.models import BranchKind


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("main", BranchKind.MAIN),
        ("master", BranchKind.MAIN),
        ("develop", BranchKind.DEVELOP),
        ("release/1.4", BranchKind.RELEASE),
        ("feature/PAY-1", BranchKind.FEATURE),
        ("bugfix/PAY-2", BranchKind.BUGFIX),
        ("hotfix/PAY-3", BranchKind.HOTFIX),
        ("experiment", BranchKind.OTHER),
    ],
)
def test_branch_classification(name, expected):
    assert classify_branch(name) is expected


def test_url_credentials_are_removed():
    assert redact_url("https://user:token@github.com/org/repo.git") == "https://github.com/org/repo.git"


def test_plain_url_is_unchanged():
    assert redact_url("https://github.com/org/repo.git") == "https://github.com/org/repo.git"


def test_secret_values_are_redacted_from_text():
    redacted = redact_text("connecting with password=hunter2 and api_key: abc")

    assert "hunter2" not in redacted
    assert "abc" not in redacted
    assert REDACTED in redacted
