import { useMutation, useQuery, useQueryClient, type UseQueryOptions } from "@tanstack/react-query";
import { apiRequest, repoSegment } from "@/lib/api";
import type {
  AnalysisReport,
  AnalyzeRepositoryBody,
  BranchInfo,
  ChangeEvent,
  ChangeSet,
  CommitInfo,
  CompareMode,
  CriticalityReport,
  DashboardSummary,
  HistoricalSummary,
  MonitorConfig,
  MonitorStatus,
  PullRequestRef,
  RefreshResult,
  RepositoryInfo,
  RepositoryRecord,
  RepositoryRisk,
  SimilarChange,
  SimilarChangeBody,
  TrendPoint,
  WorkspaceSummary,
  EventType,
} from "@/lib/types";
import { LIVE_POLL_MS, useAppState } from "@/state/app-state";

export const queryKeys = {
  repositories: ["repositories"] as const,
  repository: (repo: string) => ["repository", repo] as const,
  branches: (repo: string) => ["branches", repo] as const,
  commits: (repo: string, ref: string, limit: number) => ["commits", repo, ref, limit] as const,
  status: (repo: string) => ["status", repo] as const,
  pullRequests: (repo: string) => ["pull-requests", repo] as const,
  history: (repo: string, ref: string, limit: number) => ["history", repo, ref, limit] as const,
  workspace: ["workspace-summary"] as const,
  dashboardSummary: ["dashboard", "summary"] as const,
  dashboardRepos: ["dashboard", "repositories"] as const,
  dashboardTrends: (days: number) => ["dashboard", "trends", days] as const,
  monitor: ["monitor"] as const,
  events: (repository: string | null, type: string | null, limit: number) =>
    ["events", repository, type, limit] as const,
};

type QueryOpts<T> = Omit<UseQueryOptions<T>, "queryKey" | "queryFn">;

/** Polling is enabled only when the Live toggle is on. */
function useLiveInterval(): number | false {
  const { live } = useAppState();
  return live ? LIVE_POLL_MS : false;
}

// ---------- Repositories and git metadata ----------

export function useRepositories(opts?: QueryOpts<RepositoryInfo[]>) {
  return useQuery({
    queryKey: queryKeys.repositories,
    queryFn: ({ signal }) => apiRequest<RepositoryInfo[]>("/repositories", { signal }),
    ...opts,
  });
}

export function useRepository(repo: string | null) {
  return useQuery({
    queryKey: queryKeys.repository(repo ?? ""),
    queryFn: ({ signal }) => apiRequest<RepositoryInfo>(`/repositories/${repoSegment(repo ?? "")}`, { signal }),
    enabled: !!repo,
  });
}

export function useBranches(repo: string | null) {
  return useQuery({
    queryKey: queryKeys.branches(repo ?? ""),
    queryFn: ({ signal }) => apiRequest<BranchInfo[]>(`/repositories/${repoSegment(repo ?? "")}/branches`, { signal }),
    enabled: !!repo,
  });
}

export function useCommits(repo: string | null, ref = "HEAD", limit = 50) {
  return useQuery({
    queryKey: queryKeys.commits(repo ?? "", ref, limit),
    queryFn: ({ signal }) =>
      apiRequest<CommitInfo[]>(`/repositories/${repoSegment(repo ?? "")}/commits`, {
        query: { ref, limit },
        signal,
      }),
    enabled: !!repo,
  });
}

export function useRepositoryStatus(repo: string | null) {
  const refetchInterval = useLiveInterval();
  return useQuery({
    queryKey: queryKeys.status(repo ?? ""),
    queryFn: ({ signal }) => apiRequest<ChangeSet>(`/repositories/${repoSegment(repo ?? "")}/status`, { signal }),
    enabled: !!repo,
    refetchInterval,
  });
}

export function usePullRequestRefs(repo: string | null) {
  return useQuery({
    queryKey: queryKeys.pullRequests(repo ?? ""),
    queryFn: ({ signal }) =>
      apiRequest<PullRequestRef[]>(`/repositories/${repoSegment(repo ?? "")}/pull-requests`, { signal }),
    enabled: !!repo,
  });
}

export function useHistory(repo: string | null, ref = "HEAD", limit = 100) {
  return useQuery({
    queryKey: queryKeys.history(repo ?? "", ref, limit),
    queryFn: ({ signal }) =>
      apiRequest<HistoricalSummary>(`/repositories/${repoSegment(repo ?? "")}/history`, {
        query: { ref, limit },
        signal,
      }),
    enabled: !!repo,
  });
}

export function useWorkspaceSummary() {
  const refetchInterval = useLiveInterval();
  return useQuery({
    queryKey: queryKeys.workspace,
    queryFn: ({ signal }) => apiRequest<WorkspaceSummary>("/workspace/summary", { signal }),
    refetchInterval,
  });
}

export function useRefreshRepositories() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiRequest<RefreshResult>("/repositories/refresh", { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.repositories }),
  });
}

export function useRegisterRepository() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (path: string) =>
      apiRequest<RepositoryRecord>("/repositories/register", { method: "POST", body: { path } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.repositories }),
  });
}

// ---------- Dashboard ----------

export function useDashboardSummary() {
  const refetchInterval = useLiveInterval();
  return useQuery({
    queryKey: queryKeys.dashboardSummary,
    queryFn: ({ signal }) => apiRequest<DashboardSummary>("/dashboard/summary", { signal }),
    refetchInterval,
  });
}

export function useDashboardRepositories() {
  const refetchInterval = useLiveInterval();
  return useQuery({
    queryKey: queryKeys.dashboardRepos,
    queryFn: ({ signal }) => apiRequest<RepositoryRisk[]>("/dashboard/repositories", { signal }),
    refetchInterval,
  });
}

export function useDashboardTrends(days = 30) {
  const refetchInterval = useLiveInterval();
  return useQuery({
    queryKey: queryKeys.dashboardTrends(days),
    queryFn: ({ signal }) => apiRequest<TrendPoint[]>("/dashboard/trends", { query: { days }, signal }),
    refetchInterval,
  });
}

// ---------- Monitoring and events ----------

export function useMonitorStatus() {
  const refetchInterval = useLiveInterval();
  return useQuery({
    queryKey: queryKeys.monitor,
    queryFn: ({ signal }) => apiRequest<MonitorStatus>("/monitor", { signal }),
    refetchInterval,
  });
}

export function useUpdateMonitor() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (config: MonitorConfig) => apiRequest<MonitorStatus>("/monitor", { method: "PUT", body: config }),
    onSuccess: (data) => queryClient.setQueryData(queryKeys.monitor, data),
  });
}

export function useRunMonitorScan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiRequest<ChangeEvent[]>("/monitor/scan", { method: "POST" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.monitor });
      void queryClient.invalidateQueries({ queryKey: ["events"] });
    },
  });
}

export function useEvents(repository: string | null, type: EventType | null, limit = 100) {
  const refetchInterval = useLiveInterval();
  return useQuery({
    queryKey: queryKeys.events(repository, type, limit),
    queryFn: ({ signal }) =>
      apiRequest<ChangeEvent[]>("/events", {
        query: { limit, repository, event_type: type },
        signal,
      }),
    refetchInterval,
  });
}

// ---------- Analysis ----------

export function useAnalyzeRepository() {
  return useMutation({
    mutationFn: (body: AnalyzeRepositoryBody) =>
      apiRequest<AnalysisReport>("/analyze-repository", { method: "POST", body }),
  });
}

export function usePreCommitAnalysis() {
  return useMutation({
    mutationFn: (repo_path: string) =>
      apiRequest<AnalysisReport>("/pre-commit-analysis", { method: "POST", body: { repo_path } }),
  });
}

export function usePostCommitAnalysis() {
  return useMutation({
    mutationFn: (vars: { repo_path: string; commit_id?: string | null }) =>
      apiRequest<AnalysisReport>("/post-commit-analysis", { method: "POST", body: vars }),
  });
}

export function useBranchAnalysis() {
  return useMutation({
    mutationFn: (vars: {
      repo_path: string;
      source_branch: string | null;
      target_branch: string | null;
      compare_mode?: CompareMode;
    }) => apiRequest<AnalysisReport>("/branch-analysis", { method: "POST", body: vars }),
  });
}

export function usePullRequestAnalysis() {
  return useMutation({
    mutationFn: (vars: { repo_path: string; source_branch: string; target_branch: string }) =>
      apiRequest<AnalysisReport>("/pr-analysis", { method: "POST", body: vars }),
  });
}

export function useReleaseAnalysis() {
  return useMutation({
    mutationFn: (vars: {
      repo_path: string;
      source_branch: string;
      target_branch: string | null;
      compare_mode?: CompareMode;
    }) => apiRequest<AnalysisReport>("/release-analysis", { method: "POST", body: vars }),
  });
}

export function useCriticalityAnalysis() {
  return useMutation({
    mutationFn: (repo_path: string) =>
      apiRequest<CriticalityReport>("/criticality-analysis", { method: "POST", body: { repo_path } }),
  });
}

export function useSimilarChanges() {
  return useMutation({
    mutationFn: (body: SimilarChangeBody) =>
      apiRequest<SimilarChange[]>("/search-similar-changes", { method: "POST", body }),
  });
}

export function useAnalysisByCommit() {
  return useMutation({
    mutationFn: (commitId: string) => apiRequest<AnalysisReport>(`/analysis/${encodeURIComponent(commitId)}`),
  });
}

export function useChangeScope() {
  return useMutation({
    mutationFn: (body: { repo_path: string; analysis_mode: string; source_branch?: string; target_branch?: string }) =>
      apiRequest<ChangeSet>("/change-scope", { method: "POST", body }),
  });
}
