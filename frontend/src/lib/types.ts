// Types mirror the FastAPI/pydantic contract in backend/app/domain and backend/app/api.
// Datetimes arrive as ISO-8601 strings.

export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type AnalysisMode =
  | "PRE_COMMIT"
  | "POST_COMMIT"
  | "PR_ANALYSIS"
  | "BRANCH_ANALYSIS"
  | "RELEASE_ANALYSIS"
  | "WORKSPACE_ANALYSIS"
  | "HISTORICAL_ANALYSIS";

export type CompareMode = "MERGE_BASE" | "DIRECT";

export type BranchKind = "MAIN" | "DEVELOP" | "RELEASE" | "FEATURE" | "BUGFIX" | "HOTFIX" | "OTHER";

export type ChangeType = "ADDED" | "MODIFIED" | "DELETED" | "RENAMED" | "UNTRACKED";

export type ChangeArea = "STAGED" | "UNSTAGED" | "UNTRACKED" | "COMMITTED" | "COMPARISON";

export type EventType =
  | "REPOSITORY_DISCOVERED"
  | "REPOSITORY_REMOVED"
  | "FILE_MODIFIED"
  | "FILE_DELETED"
  | "DEPENDENCY_UPDATED"
  | "CONFIG_UPDATED"
  | "COMMIT_CREATED"
  | "BRANCH_CHANGED"
  | "MERGE_COMPLETED"
  | "PR_CREATED"
  | "ANALYSIS_REQUESTED";

export type MonitorMode = "MANUAL" | "SCHEDULED" | "CONTINUOUS";

export interface Finding {
  finding_id: string;
  category: string;
  severity: Severity;
  title: string;
  detail: string;
  file: string | null;
  line: number | null;
  source: string;
}

export interface AnalysisReport {
  analysis_id: string;
  repository: string;
  analysis_mode: AnalysisMode;
  commit_id: string | null;
  base_sha: string | null;
  target_sha: string | null;
  changed_files: string[];
  totals: Record<string, number>;
  findings: Finding[];
  risk_score: number;
  risk_level: Severity;
  summary: string;
  summary_source: string;
  llm_provider: string | null;
  security_sources: string[];
  warnings: string[];
  generated_at: string;
}

export interface CriticalityReport {
  repository: string;
  score: number;
  level: Severity;
  factors: Record<string, number>;
  rationale: string;
  rationale_source: string;
  generated_at: string;
}

export interface SimilarChange {
  analysis_id: string;
  repository: string;
  analysis_mode: AnalysisMode;
  commit_id: string | null;
  risk_level: Severity;
  similarity: number;
  matched_terms: string[];
  summary: string;
}

export interface DashboardSummary {
  registered_repositories: number;
  analyzed_repositories: number;
  total_analyses: number;
  analyses_by_mode: Record<string, number>;
  risk_distribution: Record<Severity, number> & Record<string, number>;
  average_risk_score: number;
  last_analysis_at: string | null;
  generated_at: string;
}

export interface RepositoryRisk {
  repository: string;
  analysis_count: number;
  latest_risk_score: number;
  latest_risk_level: Severity;
  latest_analysis_at: string;
}

export interface TrendPoint {
  date: string;
  analyses: number;
  average_risk_score: number;
}

export interface RepositoryInfo {
  id: string;
  name: string;
  path: string;
  current_branch: string | null;
  default_branch: string | null;
  latest_commit: string | null;
  remote_origin: string | null;
  is_dirty: boolean;
  technology_tags: string[];
  owners: string[];
  discovered_at: string;
}

export interface RepositoryRecord {
  id: string;
  name: string;
  path: string;
  technology_tags: string[];
  owners: string[];
  discovered_at: string;
}

export interface BranchInfo {
  name: string;
  kind: BranchKind;
  is_remote: boolean;
  head_commit: string;
  is_current: boolean;
  is_default: boolean;
}

export interface CommitInfo {
  sha: string;
  short_sha: string;
  author_name: string;
  author_email: string;
  authored_at: string;
  summary: string;
  parents: string[];
}

export interface ChangedFile {
  path: string;
  old_path: string | null;
  change_type: ChangeType;
  area: ChangeArea;
  added_lines: number;
  deleted_lines: number;
  modified_lines: number;
}

export interface ChangeSet {
  repository: string;
  analysis_mode: AnalysisMode;
  base_ref: string | null;
  target_ref: string | null;
  base_sha: string | null;
  target_sha: string | null;
  files: ChangedFile[];
  totals: Record<string, number>;
  generated_at: string;
}

export interface PullRequestRef {
  provider: string;
  number: number | null;
  ref: string;
  head_sha: string;
}

export interface RefreshResult {
  added: string[];
  removed: string[];
  total: number;
  refreshed_at: string;
}

export interface ChangeEvent {
  event_id: string;
  type: EventType;
  repository: string;
  branch: string | null;
  file: string | null;
  occurred_at: string;
  payload: Record<string, unknown>;
  schema_version: number;
}

export interface HistoricalSummary {
  repository: string;
  ref: string;
  commit_count: number;
  author_count: number;
  insertions: number;
  deletions: number;
  first_commit_at: string | null;
  last_commit_at: string | null;
  top_authors: Record<string, number>;
  commits: CommitInfo[];
}

export interface RepositoryStatusSummary {
  repository: string;
  current_branch: string | null;
  latest_commit: string | null;
  changed_files: number;
  is_dirty: boolean;
  error: string | null;
}

export interface WorkspaceSummary {
  generated_at: string;
  repository_count: number;
  dirty_repository_count: number;
  repositories: RepositoryStatusSummary[];
}

export interface MonitorConfig {
  mode: MonitorMode;
  interval_seconds: number;
  debounce_seconds: number;
}

export interface MonitorStatus {
  config: MonitorConfig;
  running: boolean;
  tracked_repositories: number;
  pending_events: number;
  last_cycle_at: string | null;
  repository_errors: Record<string, string>;
}

// Request bodies (subset used by the UI).
export interface AnalyzeRepositoryBody {
  repo_path: string;
  analysis_mode?: AnalysisMode;
  commit_id?: string | null;
  source_branch?: string | null;
  target_branch?: string | null;
  compare_mode?: CompareMode;
}

export interface SimilarChangeBody {
  query: string;
  repository?: string | null;
  top_k?: number;
}
