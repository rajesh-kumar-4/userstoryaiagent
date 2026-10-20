"""Analysis endpoints: pre/post-commit, branch, PR, release, criticality, similarity, and lookup."""

from fastapi import APIRouter, Depends, Path

from app.api.dependencies import get_container
from app.api.schemas import (
    REF_PATTERN,
    AnalyzeRepositoryRequest,
    BranchAnalysisRequest,
    PostCommitAnalysisRequest,
    PullRequestAnalysisRequest,
    RepositoryAnalysisRequest,
    ReleaseAnalysisRequest,
    SimilarChangeSearchRequest,
)
from app.api.security import require_permission
from app.container import AppContainer
from app.core.exceptions import AnalysisNotFoundError
from app.core.security.rbac import Permission
from app.domain.analysis import AnalysisReport, CriticalityReport, SimilarChange
from app.domain.models import AnalysisMode, ChangeScopeRequest, CompareMode

router = APIRouter(tags=["analysis"])

_RUN = [Depends(require_permission(Permission.ANALYSIS_RUN))]


def _scope(
    repo_path: str,
    mode: AnalysisMode,
    *,
    commit_id: str | None = None,
    source_branch: str | None = None,
    target_branch: str | None = None,
    compare_mode: CompareMode = CompareMode.MERGE_BASE,
) -> ChangeScopeRequest:
    return ChangeScopeRequest(
        repo_path=repo_path,
        analysis_mode=mode,
        commit_id=commit_id,
        source_branch=source_branch,
        target_branch=target_branch,
        compare_mode=compare_mode,
    )


@router.post(
    "/analyze-repository",
    response_model=AnalysisReport,
    dependencies=_RUN,
    summary="Run analysis for any change-scope mode (default PRE_COMMIT)",
)
def analyze_repository(
    body: AnalyzeRepositoryRequest,
    container: AppContainer = Depends(get_container),
) -> AnalysisReport:
    return container.analysis().run(
        _scope(
            body.repo_path,
            body.analysis_mode,
            commit_id=body.commit_id,
            source_branch=body.source_branch,
            target_branch=body.target_branch,
            compare_mode=body.compare_mode,
        )
    )


@router.post(
    "/pre-commit-analysis",
    response_model=AnalysisReport,
    dependencies=_RUN,
    summary="Analyze staged, unstaged, and untracked changes",
)
def pre_commit_analysis(
    body: RepositoryAnalysisRequest,
    container: AppContainer = Depends(get_container),
) -> AnalysisReport:
    return container.analysis().run(_scope(body.repo_path, AnalysisMode.PRE_COMMIT))


@router.post(
    "/post-commit-analysis",
    response_model=AnalysisReport,
    dependencies=_RUN,
    summary="Analyze a commit (default HEAD)",
)
def post_commit_analysis(
    body: PostCommitAnalysisRequest,
    container: AppContainer = Depends(get_container),
) -> AnalysisReport:
    return container.analysis().run(
        _scope(body.repo_path, AnalysisMode.POST_COMMIT, commit_id=body.commit_id)
    )


@router.post(
    "/branch-analysis",
    response_model=AnalysisReport,
    dependencies=_RUN,
    summary="Compare a source branch with a target branch",
)
def branch_analysis(
    body: BranchAnalysisRequest,
    container: AppContainer = Depends(get_container),
) -> AnalysisReport:
    return container.analysis().run(
        _scope(
            body.repo_path,
            AnalysisMode.BRANCH_ANALYSIS,
            source_branch=body.source_branch,
            target_branch=body.target_branch,
            compare_mode=body.compare_mode,
        )
    )


@router.post(
    "/pr-analysis",
    response_model=AnalysisReport,
    dependencies=_RUN,
    summary="Analyze a pull request as source and target refs",
)
def pr_analysis(
    body: PullRequestAnalysisRequest,
    container: AppContainer = Depends(get_container),
) -> AnalysisReport:
    return container.analysis().run(
        _scope(
            body.repo_path,
            AnalysisMode.PR_ANALYSIS,
            source_branch=body.source_branch,
            target_branch=body.target_branch,
        )
    )


@router.post(
    "/release-analysis",
    response_model=AnalysisReport,
    dependencies=_RUN,
    summary="Analyze a release/* branch against its target (default main)",
)
def release_analysis(
    body: ReleaseAnalysisRequest,
    container: AppContainer = Depends(get_container),
) -> AnalysisReport:
    return container.analysis().run(
        _scope(
            body.repo_path,
            AnalysisMode.RELEASE_ANALYSIS,
            source_branch=body.source_branch,
            target_branch=body.target_branch,
            compare_mode=body.compare_mode,
        )
    )


@router.post(
    "/criticality-analysis",
    response_model=CriticalityReport,
    dependencies=_RUN,
    summary="Rate how critical a repository is to the platform",
)
def criticality_analysis(
    body: RepositoryAnalysisRequest,
    container: AppContainer = Depends(get_container),
) -> CriticalityReport:
    return container.analysis().criticality(body.repo_path)


@router.post(
    "/search-similar-changes",
    response_model=list[SimilarChange],
    dependencies=[Depends(require_permission(Permission.SEARCH_READ))],
    summary="Find stored analyses similar to a free-text change description",
)
def search_similar_changes(
    body: SimilarChangeSearchRequest,
    container: AppContainer = Depends(get_container),
) -> list[SimilarChange]:
    return container.analysis_store().search(body.query, repository=body.repository, top_k=body.top_k)


@router.get(
    "/analysis/{commit_id}",
    response_model=AnalysisReport,
    dependencies=[Depends(require_permission(Permission.REPOSITORY_READ))],
    summary="Return the most recent stored analysis for a commit SHA prefix",
)
def get_analysis_by_commit(
    commit_id: str = Path(min_length=4, max_length=64, pattern=REF_PATTERN),
    container: AppContainer = Depends(get_container),
) -> AnalysisReport:
    report = container.analysis_store().find_by_commit(commit_id)
    if report is None:
        raise AnalysisNotFoundError(f"No stored analysis for commit {commit_id}")
    return report
