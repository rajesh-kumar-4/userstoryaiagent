import { Activity, AlertTriangle, GitBranch, ShieldAlert, Users } from "lucide-react";
import { useDashboardRepositories, useDashboardSummary, useDashboardTrends, useRepositories } from "@/api/hooks";
import { RiskDistributionChart } from "@/components/charts/risk-distribution-chart";
import { RiskHeatmap, type HeatmapItem } from "@/components/charts/risk-heatmap";
import { RiskTrendChart } from "@/components/charts/risk-trend-chart";
import { BreakdownBars } from "@/components/charts/breakdown-bars";
import { DataTable, type Column } from "@/components/common/data-table";
import { ErrorState, LoadingState, EmptyState } from "@/components/common/states";
import { PageHeader } from "@/components/common/page-header";
import { RiskBadge } from "@/components/common/risk-badge";
import { StatCard } from "@/components/common/stat-card";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { RepositoryRisk } from "@/lib/types";
import { formatDateTime, formatNumber, formatRelative } from "@/lib/utils";
import { useAppState } from "@/state/app-state";

const RISK_COLUMNS: Column<RepositoryRisk>[] = [
  { key: "repo", header: "Repository", render: (row) => <span className="font-medium">{row.repository}</span>, searchText: (row) => row.repository },
  { key: "count", header: "Analyses", render: (row) => formatNumber(row.analysis_count), className: "text-right" },
  {
    key: "score",
    header: "Latest score",
    render: (row) => <span className="font-semibold tabular-nums">{row.latest_risk_score}</span>,
    className: "text-right",
  },
  { key: "level", header: "Level", render: (row) => <RiskBadge level={row.latest_risk_level} /> },
  { key: "when", header: "Last analysis", render: (row) => formatRelative(row.latest_analysis_at) },
];

export default function DashboardPage() {
  const { live, setRepository } = useAppState();
  const summary = useDashboardSummary();
  const repositories = useDashboardRepositories();
  const trends = useDashboardTrends(30);
  const registry = useRepositories();

  const riskRows = repositories.data ?? [];
  const heatmap: HeatmapItem[] = riskRows.map((row) => ({
    id: row.repository,
    label: row.repository,
    score: row.latest_risk_score,
    detail: row.latest_risk_level,
  }));

  // The dashboard identifies repositories by name or id; map back to the registry id for selection.
  const selectFromRisk = (item: HeatmapItem) => {
    const match = registry.data?.find((repo) => repo.id === item.id || repo.name === item.id);
    if (match) setRepository(match.id);
  };

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Executive view of repository risk, analysis volume, and recent trends."
        actions={
          <span className="inline-flex items-center gap-2 text-xs text-muted-foreground">
            <Activity className={live ? "size-4 animate-pulse text-success" : "size-4"} aria-hidden="true" />
            {live ? "Live: refreshing every 15 seconds" : "Live updates paused"}
          </span>
        }
      />

      {summary.isPending ? (
        <LoadingState rows={2} label="Loading summary" />
      ) : summary.isError ? (
        <ErrorState error={summary.error} onRetry={() => void summary.refetch()} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Registered repositories" value={formatNumber(summary.data.registered_repositories)} icon={<GitBranch className="size-4" />} />
          <StatCard label="Analyzed repositories" value={formatNumber(summary.data.analyzed_repositories)} icon={<Users className="size-4" />} />
          <StatCard label="Total analyses" value={formatNumber(summary.data.total_analyses)} icon={<Activity className="size-4" />} />
          <StatCard
            label="Average risk score"
            value={formatNumber(summary.data.average_risk_score, 1)}
            tone={summary.data.average_risk_score >= 50 ? "danger" : summary.data.average_risk_score >= 20 ? "warning" : "success"}
            hint={`Last analysis ${formatRelative(summary.data.last_analysis_at)}`}
            icon={<ShieldAlert className="size-4" />}
          />
        </div>
      )}

      <div className="mt-6 grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Risk trend (30 days)</CardTitle>
            <CardDescription>Average risk score per day across all analyses.</CardDescription>
          </CardHeader>
          <CardContent>
            {trends.isPending ? (
              <LoadingState rows={2} />
            ) : trends.isError ? (
              <ErrorState error={trends.error} onRetry={() => void trends.refetch()} />
            ) : trends.data.length === 0 ? (
              <EmptyState title="No trend data yet" description="Run an analysis to populate the trend." />
            ) : (
              <RiskTrendChart data={trends.data} />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Risk distribution</CardTitle>
            <CardDescription>Analyses per severity level.</CardDescription>
          </CardHeader>
          <CardContent>
            {summary.data ? <RiskDistributionChart distribution={summary.data.risk_distribution} /> : <LoadingState rows={1} />}
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Repository risk heatmap</CardTitle>
            <CardDescription>Select a tile to make that repository the active one.</CardDescription>
          </CardHeader>
          <CardContent>
            {repositories.isPending ? (
              <LoadingState rows={2} />
            ) : repositories.isError ? (
              <ErrorState error={repositories.error} onRetry={() => void repositories.refetch()} />
            ) : (
              <RiskHeatmap items={heatmap} onSelect={selectFromRisk} emptyMessage="No repositories have been analyzed yet." />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Analyses by mode</CardTitle>
          </CardHeader>
          <CardContent>
            {summary.data ? <BreakdownBars data={summary.data.analyses_by_mode} emptyMessage="No analyses yet" /> : <LoadingState rows={1} />}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Repository risk ranking</CardTitle>
            <CardDescription>Latest analysis per repository, all levels.</CardDescription>
          </div>
          {summary.data && (
            <span className="text-xs text-muted-foreground">Generated {formatDateTime(summary.data.generated_at)}</span>
          )}
        </CardHeader>
        <CardContent>
          {repositories.isPending ? (
            <LoadingState rows={3} />
          ) : (
            <DataTable columns={RISK_COLUMNS} rows={riskRows} rowKey={(row) => row.repository} searchable searchPlaceholder="Filter repositories" emptyMessage="No analyses recorded yet" caption="Repository risk ranking" />
          )}
        </CardContent>
      </Card>

      <p className="mt-6 flex items-center gap-2 text-xs text-muted-foreground">
        <AlertTriangle className="size-3.5" aria-hidden="true" />
        Real-time updates use polling (every 15 seconds) because the backend has no push channel.
        <Button variant="link" size="sm" className="h-auto p-0" onClick={() => void repositories.refetch()}>
          Refresh now
        </Button>
      </p>
    </>
  );
}
