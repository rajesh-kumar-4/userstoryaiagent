import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import { useAnalyzeRepository } from "@/api/hooks";
import { DataTable, type Column } from "@/components/common/data-table";
import { PageHeader } from "@/components/common/page-header";
import { RequireRepository } from "@/components/common/require-repository";
import { RiskBadge } from "@/components/common/risk-badge";
import { ErrorState, LoadingState } from "@/components/common/states";
import { StatCard } from "@/components/common/stat-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label, Select } from "@/components/ui/input";
import { countBySeverity } from "@/lib/gates";
import type { AnalysisMode, Finding, RepositoryInfo } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

const SECURITY_PATTERN = /secur|vuln|cve|sast|sca|secret|checkmarx|sonatype/i;

const FINDING_COLUMNS: Column<Finding>[] = [
  { key: "severity", header: "Severity", render: (row) => <RiskBadge level={row.severity} /> },
  { key: "category", header: "Category", render: (row) => row.category, searchText: (row) => row.category },
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
  { key: "location", header: "Location", render: (row) => <span className="font-mono text-xs">{row.file ?? "-"}{row.line !== null ? `:${row.line}` : ""}</span> },
  { key: "source", header: "Source", render: (row) => <Badge variant="outline">{row.source}</Badge> },
];

function SecurityBody({ repo }: { repo: RepositoryInfo }) {
  const analysis = useAnalyzeRepository();
  const [mode, setMode] = useState<AnalysisMode>("WORKSPACE_ANALYSIS");

  const report = analysis.data;
  const securityFindings = report?.findings.filter((f) => SECURITY_PATTERN.test(`${f.category} ${f.source}`)) ?? [];
  const counts = countBySeverity(securityFindings);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Run security analysis</CardTitle>
          <CardDescription>Security findings come from the configured scanners (Checkmarx, Sonatype) and the local rule set.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="space-y-1.5">
            <Label htmlFor="security-mode">Scope</Label>
            <Select id="security-mode" value={mode} onChange={(e) => setMode(e.target.value as AnalysisMode)} className="sm:w-64">
              <option value="WORKSPACE_ANALYSIS">Working tree</option>
              <option value="PRE_COMMIT">Staged changes</option>
            </Select>
          </div>
          <Button onClick={() => analysis.mutate({ repo_path: repo.path, analysis_mode: mode })} disabled={analysis.isPending}>
            <ShieldCheck aria-hidden="true" /> {analysis.isPending ? "Scanning..." : "Run security scan"}
          </Button>
        </CardContent>
      </Card>

      {analysis.isPending && <LoadingState rows={3} label="Running security scan" />}
      {analysis.isError && <ErrorState error={analysis.error} />}

      {report && (
        <>
          {report.warnings.length > 0 && (
            <Alert variant="warning">
              <AlertTitle>Scanner warnings</AlertTitle>
              <AlertDescription>
                <ul className="list-disc pl-5">
                  {report.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          )}
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Security findings" value={securityFindings.length} tone={securityFindings.length > 0 ? "warning" : "success"} />
            <StatCard label="Critical" value={counts.CRITICAL} tone={counts.CRITICAL > 0 ? "danger" : "default"} />
            <StatCard label="High" value={counts.HIGH} tone={counts.HIGH > 0 ? "warning" : "default"} />
            <StatCard label="Sources" value={report.security_sources.length ? report.security_sources.join(", ") : "Local rules only"} hint={`Scanned ${formatDateTime(report.generated_at)}`} />
          </div>
          <Card>
            <CardHeader>
              <CardTitle>Security findings</CardTitle>
              <CardDescription>Findings whose category or source matches a security scanner or rule.</CardDescription>
            </CardHeader>
            <CardContent>
              <DataTable columns={FINDING_COLUMNS} rows={securityFindings} rowKey={(row) => row.finding_id} searchable searchPlaceholder="Filter security findings" emptyMessage="No security findings" caption="Security findings" />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

export default function SecurityAnalysisPage() {
  return (
    <>
      <PageHeader title="Security Analysis" description="Security scanner results and security-related findings for the selected repository." />
      <RequireRepository>{(repo) => <SecurityBody repo={repo} />}</RequireRepository>
    </>
  );
}
