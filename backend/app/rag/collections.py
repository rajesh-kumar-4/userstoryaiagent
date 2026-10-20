"""ChromaDB collection names and the mapping from historical source types to collections."""

from enum import Enum


class Collection(str, Enum):
    REPOSITORIES = "repositories"
    CODE_CHANGES = "code_changes"
    GIT_ANALYSIS = "git_analysis"
    AST_ANALYSIS = "ast_analysis"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    SECURITY_ANALYSIS = "security_analysis"
    IMPACT_ANALYSIS = "impact_analysis"
    RISK_ANALYSIS = "risk_analysis"
    CRITICALITY_ANALYSIS = "criticality_analysis"
    STORY_ANALYSIS = "story_analysis"
    TEST_ANALYSIS = "test_analysis"


class SourceType(str, Enum):
    HISTORICAL_COMMIT = "historical_commit"
    RISK = "risk"
    INCIDENT = "incident"
    USER_STORY = "user_story"
    TEST_CASE = "test_case"
    RELEASE_NOTE = "release_note"
    SONAR_FINDING = "sonar_finding"
    CHECKMARX_FINDING = "checkmarx_finding"
    SONATYPE_FINDING = "sonatype_finding"
    CAB_DECISION = "cab_decision"


SOURCE_COLLECTIONS: dict[SourceType, Collection] = {
    SourceType.HISTORICAL_COMMIT: Collection.GIT_ANALYSIS,
    SourceType.RISK: Collection.RISK_ANALYSIS,
    SourceType.INCIDENT: Collection.RISK_ANALYSIS,
    SourceType.USER_STORY: Collection.STORY_ANALYSIS,
    SourceType.TEST_CASE: Collection.TEST_ANALYSIS,
    SourceType.RELEASE_NOTE: Collection.CODE_CHANGES,
    SourceType.SONAR_FINDING: Collection.SECURITY_ANALYSIS,
    SourceType.CHECKMARX_FINDING: Collection.SECURITY_ANALYSIS,
    SourceType.SONATYPE_FINDING: Collection.DEPENDENCY_ANALYSIS,
    SourceType.CAB_DECISION: Collection.RISK_ANALYSIS,
}

# Collections searched for similar historical changes.
SIMILARITY_COLLECTIONS: tuple[Collection, ...] = (
    Collection.GIT_ANALYSIS,
    Collection.CODE_CHANGES,
    Collection.RISK_ANALYSIS,
    Collection.STORY_ANALYSIS,
)
