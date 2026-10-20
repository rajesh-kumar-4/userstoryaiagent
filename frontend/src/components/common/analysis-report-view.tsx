import { useMemo } from "react";
import { AlertTriangle } from "lucide-react";
import { BreakdownBars } from "@/components/charts/breakdown-bars";
import { ScoreGauge } from "@/components/charts/score-gauge";
import { ExportMenu } from "@/components/common/export-menu";
import { DataTable, type Column } from "@/components/common/data-table";
import { RiskBadge } from "@/components/common/risk-badge";
import { StatCard } from "@/components/common/stat-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { countBySeverity } from "@/lib/gates";
import type { AnalysisReport, Finding } from "@/lib/types";
import { formatDateTime, shortSha } from "@/lib/utils";
import type { ExportDocument } from "@/lib/exporters";

const FINDING_COLUMNS: Column<Finding>[] = [
  {
    key: "severity",
    header: "Severity",
    render: (row) => <RiskBadge level={row.severity} />,
  },
  {
    key: "category",
    header: "Category",
    render: (row) => <span className="text-xs font-medium">{row.category}</span>,
    searchText: (row) => row.category,
  },
  {
    key: "title",
    header: "Finding",
    render: (row) => (
      <div className="min-w-0">
        <p className="font-medium">{row.title}</p>
        <p className="text-xs text-muted-foreground">{row.detail}</p>
      </div>
    ),
    searchText: (row) => `${row.title} ${row.detail}`,
  },
  {
    key: "location",
    header: "Location",
    render: (row) => (
      <span className="font-mono text-xs">
        {row.file ?? "-"}
        {row.line !== null ? `:${row.line}` : ""}
      </span>
    ),
    searchText: (row) => row.file ?? "",
  },
  {
    key: "source",
    header: "Source",
    render: (row) => <Badge variant="outline">{row.source}</Badge>,
    searchText: (row) => row.source,
  },
];

export function buildReportDocument(report: AnalysisReport, title: string): ExportDocument {
  return {
    title,
    subtitle: `${report.repository} | ${report.analysis_mode} | risk ${report.risk_score} (${report.risk_level})`,
    generatedAt: report.generated_at,
    tables: [
      {
        name: "Summary",
        columns: ["Field", "Value"],
        rows: [
          ["Repository", report.repository],
          ["Analysis mode", report.analysis_mode],
          ["Risk score", report.risk_score],
          ["Risk level", report.risk_level],
          ["Summary", report.summary],
          ["Summary source", report.summary_source],
          ["Commit", report.commit_id ?? ""],
          ["Base SHA", report.base_sha ?? ""],
          ["Target SHA", report.target_sha ?? ""],
        ],
      },
      {
        name: "Findings",
        columns: ["Severity", "Category", "Title", "Detail", "File", "Line", "Source"],
        rows: report.findings.map((f) => [f.severity, f.category, f.title, f.detail, f.file, f.line, f.source]),
      },
      {
        name: "Changed files",
        columns: ["File"],
        rows: report.changed_files.map((file) => [file]),
      },
    ],
  };
}

/** Shared result view for every analysis endpoint. */
export function AnalysisReportView({
  report,
  title = "Analysis report",
  exportName = "analysis-report",
}: {
  report: AnalysisReport;
  title?: string;
  exportName?: string;
}) {
  const counts = useMemo(() => countBySeverity(report.findings), [report.findings]);
  const byCategory = useMemo(() => {
    const map: Record<string, number> = {};
    for (const finding of report.findings) map[finding.category] = (map[finding.category] ?? 0) + 1;
    return map;
  }, [report.findings]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold">{title}</h2>
          <p className="text-sm text-muted-foreground">
            {report.analysis_mode} | generated {formatDateTime(report.generated_at)}
            {report.commit_id ? ` | commit ${shortSha(report.commit_id)}` : ""}
          </p>
        </div>
        <ExportMenu
          fileName={exportName}
          jsonData={report}
          buildDocument={() => buildReportDocument(report, title)}
        />
      </div>

      {report.warnings.length > 0 && (
        <Alert variant="warning">
          <AlertTitle className="flex items-center gap-2">
            <AlertTriangle className="size-4" aria-hidden="true" /> {report.warnings.length} analysis warning(s)
          </AlertTitle>
          <AlertDescription>
            <ul className="list-disc space-y-1 pl-5">
              {report.warnings.map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,260px)_1fr]">
        <Card>
          <CardContent className="flex justify-center py-6">
            <ScoreGauge score={report.risk_score} level={report.risk_level} />
          </CardContent>
        </Card>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Findings" value={report.findings.length} hint="All severities" />
          <StatCard label="Critical / High" value={counts.CRITICAL + counts.HIGH} tone={counts.CRITICAL > 0 ? "danger" : counts.HIGH > 0 ? "warning" : "success"} />
          <StatCard label="Changed files" value={report.changed_files.length} />
          <StatCard label="Medium / Low" value={`${counts.MEDIUM} / ${counts.LOW}`} />
          <Card className="sm:col-span-2 xl:col-span-4">
            <CardHeader>
              <CardTitle>Summary</CardTitle>
              <CardDescription>
                Source: {report.summary_source}
                {report.llm_provider ? ` (${report.llm_provider})` : ""}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-line text-sm leading-relaxed">{report.summary || "No summary produced."}</p>
              {report.security_sources.length > 0 && (
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <span className="text-xs text-muted-foreground">Security sources:</span>
                  {report.security_sources.map((source) => (
                    <Badge key={source} variant="secondary">
                      {source}
                    </Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Findings by category</CardTitle>
          </CardHeader>
          <CardContent>
            <BreakdownBars data={byCategory} emptyMessage="No findings" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Totals</CardTitle>
          </CardHeader>
          <CardContent>
            <BreakdownBars data={report.totals} emptyMessage="No totals reported" />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Findings</CardTitle>
          <CardDescription>Filter by category, title, file, or source.</CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={FINDING_COLUMNS}
            rows={report.findings}
            rowKey={(row) => row.finding_id}
            searchable
            searchPlaceholder="Filter findings"
            emptyMessage="No findings for this analysis"
            caption="Analysis findings"
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Changed files</CardTitle>
        </CardHeader>
        <CardContent>
          {report.changed_files.length === 0 ? (
            <p className="text-sm text-muted-foreground">No changed files in scope.</p>
          ) : (
            <ul className="max-h-72 space-y-1 overflow-y-auto font-mono text-xs">
              {report.changed_files.map((file) => (
                <li key={file} className="truncate">
                  {file}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
