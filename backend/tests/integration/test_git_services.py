from pathlib import Path

import pytest

from app.core.exceptions import InvalidRequestError, RefNotFoundError
from app.domain.models import AnalysisMode, ChangeArea, ChangeScopeRequest, ChangeType
from app.infrastructure.git.git_repository import validate_ref
from tests.support import commit_all, git, init_repo, write


def _by_path(files):
    return {item.path: item for item in files}


def test_explorer_lists_repositories_with_metadata(container):
    infos = container.explorer().list_repositories()

    ids = {info.id for info in infos}
    assert ids == {"billing-service", "frontend/web-app", "services/payments"}
    billing = next(info for info in infos if info.id == "billing-service")
    assert "java" in billing.technology_tags
    assert "spring-boot" in billing.technology_tags
    assert billing.current_branch == "main"
    assert billing.default_branch == "main"


def test_branches_are_listed_with_kinds_and_current_flag(container):
    branches = {branch.name: branch for branch in container.explorer().branches("billing-service")}

    assert branches["main"].is_current is True
    assert branches["main"].is_default is True
    assert branches["feature/PAY-1"].kind.value == "FEATURE"


def test_repository_resolves_by_name_and_nested_id(container):
    assert container.explorer().describe("web-app").id == "frontend/web-app"
    assert container.explorer().describe("frontend/web-app").name == "web-app"


def test_pre_commit_scope_reports_unstaged_and_untracked(container, sample_workspace):
    repo = sample_workspace / "billing-service"
    write(repo / "src" / "main" / "App.java", "class App { changed }\n")
    write(repo / "README.md", "new file\n")

    change_set = container.change_scope().resolve(
        ChangeScopeRequest(repo_path="billing-service", analysis_mode=AnalysisMode.PRE_COMMIT)
    )

    files = _by_path(change_set.files)
    assert files["src/main/App.java"].area is ChangeArea.UNSTAGED
    assert files["README.md"].change_type is ChangeType.UNTRACKED
    assert change_set.totals["files_changed"] == 2


def test_post_commit_scope_diffs_against_parent(container):
    change_set = container.change_scope().resolve(
        ChangeScopeRequest(repo_path="billing-service", analysis_mode=AnalysisMode.POST_COMMIT)
    )

    assert _by_path(change_set.files)["src/main/App.java"].change_type is ChangeType.ADDED


def test_branch_analysis_uses_merge_base_and_counts_lines(container):
    change_set = container.change_scope().resolve(
        ChangeScopeRequest(
            repo_path="billing-service",
            analysis_mode=AnalysisMode.BRANCH_ANALYSIS,
            source_branch="feature/PAY-1",
            target_branch="main",
        )
    )

    app_file = _by_path(change_set.files)["src/main/App.java"]
    assert app_file.change_type is ChangeType.MODIFIED
    assert app_file.added_lines == 2
    assert app_file.modified_lines == 1
    assert change_set.base_sha is not None


def test_release_analysis_requires_release_source(container):
    with pytest.raises(InvalidRequestError):
        container.change_scope().resolve(
            ChangeScopeRequest(
                repo_path="billing-service",
                analysis_mode=AnalysisMode.RELEASE_ANALYSIS,
                source_branch="feature/PAY-1",
                target_branch="main",
            )
        )


def test_pr_analysis_requires_both_branches(container):
    with pytest.raises(InvalidRequestError):
        container.change_scope().resolve(
            ChangeScopeRequest(repo_path="billing-service", analysis_mode=AnalysisMode.PR_ANALYSIS)
        )


def test_unknown_reference_is_not_found(container):
    with pytest.raises(RefNotFoundError):
        container.explorer().commits("billing-service", ref="does-not-exist")


@pytest.mark.parametrize("ref", ["--output=evil", "a..b", "", "main;rm"])
def test_unsafe_refs_are_rejected(ref):
    with pytest.raises(InvalidRequestError):
        validate_ref(ref)


def test_commit_listing_and_history_summary(container):
    commits = container.explorer().commits("billing-service", ref="main", limit=10)
    history = container.workspace_analysis().history("billing-service", "main", 10)

    assert [commit.summary for commit in commits] == ["initial commit"]
    assert history.commit_count == 1
    assert history.author_count == 1
    assert history.insertions > 0


def test_pull_request_refs_are_detected(container, sample_workspace):
    repo = sample_workspace / "billing-service"
    feature_sha = git(repo, "rev-parse", "feature/PAY-1")
    git(repo, "update-ref", "refs/pull/7/head", feature_sha)

    refs = container.explorer().pull_requests("billing-service")

    assert len(refs) == 1
    assert refs[0].number == 7
    assert refs[0].head_sha == feature_sha


def test_workspace_summary_counts_dirty_repositories(container, sample_workspace):
    write(sample_workspace / "frontend" / "web-app" / "scratch.txt", "x\n")
    container.registry().refresh()

    summary = container.workspace_analysis().summary()

    assert summary.repository_count == 3
    assert summary.dirty_repository_count == 1


def test_unborn_repository_reports_untracked_files(container, sample_workspace):
    fresh = init_repo(sample_workspace / "fresh-repo")
    write(fresh / "notes.md", "draft\n")
    container.registry().refresh()

    change_set = container.change_scope().resolve(
        ChangeScopeRequest(repo_path="fresh-repo", analysis_mode=AnalysisMode.PRE_COMMIT)
    )

    assert _by_path(change_set.files)["notes.md"].change_type is ChangeType.UNTRACKED
