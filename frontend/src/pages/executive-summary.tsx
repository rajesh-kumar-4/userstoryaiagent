import { useMemo } from "react";
import { Printer } from "lucide-react";
import { useDashboardRepositories, useDashboardSummary, useDashboardTrends } from "@/api/hooks";
import { BreakdownBars } from "@/components/charts/breakdown-bars";
import { RiskDistributionChart } from "@/components/charts/risk-distribution-chart";
import { RiskTrendChart } from "@/components/charts/risk-trend-chart";
import { ExportMenu } from "@/components/common/export-menu";
import { PageHeader } from "@/components/common/page-header";
import { ErrorState, LoadingState } from "@/components/common/states";
import { RiskBadge } from "@/components/common/risk-badge";
import { StatCard } from "@/components/common/stat-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ExportDocument } from "@/lib/exporters";
import { formatDateTime, formatNumber, formatRelative } from "@/lib/utils";

export default function ExecutiveSummaryPage() {
  const summary = useDashboardSummary();
  const repos = useDashboardRepositories();
  const trends = useDashboardTrends(30);

  const payload = useMemo(
    () => ({ summary: summary.data ?? null, repositories: repos.data ?? [], trends: trends.data ?? [] }),
    [summary.data, repos.data, trends.data],
  );

  const buildDocument = (): ExportDocument => ({
    title: "USERSTORYAI Executive Summary",
    subtitle: summary.data ? `${summary.data.total_analyses} analyses across ${summary.data.analyzed_repositories} repositories` : undefined,
    generatedAt: summary.data?.generated_at,
    tables: [
      {
        name: "Overview",
        columns: ["Metric", "Value"],
        rows: [
          ["Registered repositories", summary.data?.registered_repositories ?? null],
          ["Analyzed repositories", summary.data?.analyzed_repositories ?? null],
          ["Total analyses", summary.data?.total_analyses ?? null],
          ["Average risk score", summary.data?.average_risk_score ?? null],
          ["Last analysis", summary.data?.last_analysis_at ?? null],
        ],
      },
      {
        name: "Repositories",
        columns: ["Repository", "Analyses", "Latest score", "Latest level", "Last analysis"],
        rows: (repos.data ?? []).map((r) => [r.repository, r.analysis_count, r.latest_risk_score, r.latest_risk_level, r.latest_analysis_at]),
      },
      {
        name: "Trend",
        columns: ["Date", "Analyses", "Average risk score"],
        rows: (trends.data ?? []).map((t) => [t.date, t.analyses, t.average_risk_score]),
      },
    ],
  });

  const top = [...(repos.data ?? [])].sort((a, b) => b.latest_risk_score - a.latest_risk_score).slice(0, 5);

  return (
    <>
      <PageHeader
        title="Executive Summary"
        description="One-page view for leadership: risk posture, the highest-risk repositories, and the trend."
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => window.print()}>
              <Printer aria-hidden="true" /> Print
            </Button>
            <ExportMenu fileName="usai-executive-summary" jsonData={payload} buildDocument={buildDocument} disabled={summary.isPending} />
          </>
        }
      />

      {summary.isPending ? (
        <LoadingState rows={2} />
      ) : summary.isError ? (
        <ErrorState error={summary.error} onRetry={() => void summary.refetch()} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Repositories" value={formatNumber(summary.data.registered_repositories)} hint={`${summary.data.analyzed_repositories} analyzed`} />
          <StatCard label="Total analyses" value={formatNumber(summary.data.total_analyses)} />
          <StatCard
            label="Average risk"
            value={formatNumber(summary.data.average_risk_score, 1)}
            tone={summary.data.average_risk_score >= 50 ? "danger" : summary.data.average_risk_score >= 20 ? "warning" : "success"}
          />
          <StatCard label="Last analysis" value={formatRelative(summary.data.last_analysis_at)} hint={formatDateTime(summary.data.last_analysis_at)} />
        </div>
      )}

      <div className="mt-6 grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Risk trend</CardTitle>
            <CardDescription>Average score per day, last 30 days.</CardDescription>
          </CardHeader>
          <CardContent>
            {trends.isPending ? <LoadingState rows={2} /> : trends.isError ? <ErrorState error={trends.error} /> : <RiskTrendChart data={trends.data} />}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Severity mix</CardTitle>
          </CardHeader>
          <CardContent>
            {summary.data ? <RiskDistributionChart distribution={summary.data.risk_distribution} /> : <LoadingState rows={1} />}
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Highest-risk repositories</CardTitle>
            <CardDescription>Top five by latest risk score.</CardDescription>
          </CardHeader>
          <CardContent>
            {repos.isPending ? (
              <LoadingState rows={3} />
            ) : top.length === 0 ? (
              <p className="text-sm text-muted-foreground">No repository has been analyzed yet.</p>
            ) : (
              <ol className="space-y-3">
                {top.map((row) => (
                  <li key={row.repository} className="flex items-center justify-between gap-3">
                    <span className="truncate font-medium">{row.repository}</span>
                    <span className="flex items-center gap-2">
                      <span className="font-semibold tabular-nums">{row.latest_risk_score}</span>
                      <RiskBadge level={row.latest_risk_level} />
                    </span>
                  </li>
                ))}
              </ol>
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
    </>
  );
}
