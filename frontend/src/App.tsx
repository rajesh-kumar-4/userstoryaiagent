import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LoadingState } from "@/components/common/states";
import { AppShell } from "@/components/layout/app-shell";
import { ApiError } from "@/lib/api";
import { AppStateProvider } from "@/state/app-state";

const DashboardPage = lazy(() => import("@/pages/dashboard"));
const ExecutiveSummaryPage = lazy(() => import("@/pages/executive-summary"));
const RepositoryExplorerPage = lazy(() => import("@/pages/repository-explorer"));
const GitAnalysisPage = lazy(() => import("@/pages/git-analysis"));
const BranchComparisonPage = lazy(() => import("@/pages/branch-comparison"));
const PullRequestAnalysisPage = lazy(() => import("@/pages/pull-request-analysis"));
const RepositoryDependencyMapPage = lazy(() => import("@/pages/repository-dependency-map"));
const AstAnalysisPage = lazy(() => import("@/pages/ast-analysis"));
const DependencyAnalysisPage = lazy(() => import("@/pages/dependency-analysis"));
const SecurityAnalysisPage = lazy(() => import("@/pages/security-analysis"));
const ImpactAnalysisPage = lazy(() => import("@/pages/impact-analysis"));
const HistoricalSimilarityPage = lazy(() => import("@/pages/historical-similarity"));
const CriticalityAssessmentPage = lazy(() => import("@/pages/criticality-assessment"));
const AiStoryReportPage = lazy(() => import("@/pages/ai-story-report"));
const PreCommitValidationPage = lazy(() => import("@/pages/pre-commit-validation"));
const ReleaseReadinessPage = lazy(() => import("@/pages/release-readiness"));
const WorkspaceMonitoringPage = lazy(() => import("@/pages/workspace-monitoring"));
const ChangeEventsPage = lazy(() => import("@/pages/change-events"));
const NotFoundPage = lazy(() => import("@/pages/not-found"));

/** Authentication and authorization failures will not succeed on retry. */
function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return false;
  return failureCount < 2;
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: shouldRetry,
      staleTime: 5_000,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppStateProvider>
        <BrowserRouter>
          <Suspense fallback={<LoadingState rows={4} label="Loading page" />}>
            <Routes>
              <Route element={<AppShell />}>
                <Route index element={<DashboardPage />} />
                <Route path="executive" element={<ExecutiveSummaryPage />} />
                <Route path="repositories" element={<RepositoryExplorerPage />} />
                <Route path="git" element={<GitAnalysisPage />} />
                <Route path="branches" element={<BranchComparisonPage />} />
                <Route path="pull-requests" element={<PullRequestAnalysisPage />} />
                <Route path="dependency-map" element={<RepositoryDependencyMapPage />} />
                <Route path="ast" element={<AstAnalysisPage />} />
                <Route path="dependencies" element={<DependencyAnalysisPage />} />
                <Route path="security" element={<SecurityAnalysisPage />} />
                <Route path="impact" element={<ImpactAnalysisPage />} />
                <Route path="similarity" element={<HistoricalSimilarityPage />} />
                <Route path="criticality" element={<CriticalityAssessmentPage />} />
                <Route path="story" element={<AiStoryReportPage />} />
                <Route path="pre-commit" element={<PreCommitValidationPage />} />
                <Route path="release" element={<ReleaseReadinessPage />} />
                <Route path="monitoring" element={<WorkspaceMonitoringPage />} />
                <Route path="events" element={<ChangeEventsPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Route>
            </Routes>
          </Suspense>
        </BrowserRouter>
      </AppStateProvider>
    </QueryClientProvider>
  );
}
