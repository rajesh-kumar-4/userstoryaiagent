import { useState } from "react";
import { Crosshair } from "lucide-react";
import { useAnalyzeRepository, useChangeScope } from "@/api/hooks";
import { BreakdownBars } from "@/components/charts/breakdown-bars";
import { ScoreGauge } from "@/components/charts/score-gauge";
import { DataTable, type Column } from "@/components/common/data-table";
import { PageHeader } from "@/components/common/page-header";
import { RequireRepository } from "@/components/common/require-repository";
import { ErrorState, LoadingState } from "@/components/common/states";
import { StatCard } from "@/components/common/stat-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label, Select } from "@/components/ui/input";
import { fileChurn } from "@/lib/gates";
import type { AnalysisMode, ChangeSet, RepositoryInfo } from "@/lib/types";
import { formatNumber } from "@/lib/utils";

type ChurnRow = { path: string; churn: number; type: string };

/** Groups a file path by its top-level folder ("(root)" for files at the repository root). */
function topFolder(path: string): string {
  const parts = path.split(/[\\/]/);
  return parts.length > 1 ? parts[0] : "(root)";
}

function groupByFolder(changeSet: ChangeSet): Record<string, number> {
  const map: Record<string, number> = {};
  for (const file of changeSet.files) {
    const key = topFolder(file.path);
    map[key] = (map[key] ?? 0) + 1;
  }
  return map;
}

const CHURN_COLUMNS: Column<ChurnRow>[] = [
  { key: "path", header: "File", render: (row) => <span className="font-mono text-xs">{row.path}</span>, searchText: (row) => row.path },
  { key: "type", header: "Change", render: (row) => <Badge variant="outline">{row.type}</Badge> },
  { key: "churn", header: "Churn", render: (row) => formatNumber(row.churn), className: "text-right" },
];

function ImpactBody({ repo }: { repo: RepositoryInfo }) {
  const analysis = useAnalyzeRepository();
  const scope = useChangeScope();
  const [mode, setMode] = useState<AnalysisMode>("PRE_COMMIT");

  const running = analysis.isPending || scope.isPending;
  const changeSet = scope.data;
  const churn = changeSet ? fileChurn(changeSet) : [];
  const report = analysis.data;

  const runAssessment = () => {
    analysis.mutate({ repo_path: repo.path, analysis_mode: mode });
    scope.mutate({ repo_path: repo.path, analysis_mode: mode });
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Assess blast radius</CardTitle>
          <CardDescription>Combines the risk analysis with the file-level change scope.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="space-y-1.5">
            <Label htmlFor="impact-mode">Scope</Label>
            <Select id="impact-mode" value={mode} onChange={(e) => setMode(e.target.value as AnalysisMode)} className="sm:w-64">
              <option value="PRE_COMMIT">Staged changes</option>
              <option value="WORKSPACE_ANALYSIS">Working tree</option>
            </Select>
          </div>
          <Button onClick={runAssessment} disabled={running}>
            <Crosshair aria-hidden="true" /> {running ? "Assessing..." : "Assess impact"}
          </Button>
        </CardContent>
      </Card>

      {running && <LoadingState rows={3} label="Assessing impact" />}
      {analysis.isError && <ErrorState error={analysis.error} />}
      {scope.isError && <ErrorState error={scope.error} />}

      {(report || changeSet) && !running && (
        <>
          <div className="grid gap-4 xl:grid-cols-3">
            <Card>
              <CardContent className="flex justify-center py-6">
                {report ? <ScoreGauge score={report.risk_score} level={report.risk_level} label="Impact risk" /> : <span className="text-sm text-muted-foreground">Risk analysis unavailable</span>}
              </CardContent>
            </Card>
            <div className="grid gap-4 sm:grid-cols-2 xl:col-span-2">
              <StatCard label="Files affected" value={formatNumber(changeSet?.files.length ?? 0)} />
              <StatCard label="Findings" value={formatNumber(report?.findings.length ?? 0)} tone={(report?.findings.length ?? 0) > 0 ? "warning" : "success"} />
              <StatCard label="Lines added" value={formatNumber(changeSet?.totals.added_lines ?? 0)} tone="success" />
              <StatCard label="Lines deleted" value={formatNumber(changeSet?.totals.deleted_lines ?? 0)} tone="danger" />
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle>Impact by folder</CardTitle>
                <CardDescription>Changed files grouped by top-level folder.</CardDescription>
              </CardHeader>
              <CardContent>{changeSet ? <BreakdownBars data={groupByFolder(changeSet)} emptyMessage="No changed files" /> : null}</CardContent>
            </Card>
            <Card className="xl:col-span-2">
              <CardHeader>
                <CardTitle>Affected files</CardTitle>
                <CardDescription>Ordered by lines touched.</CardDescription>
              </CardHeader>
              <CardContent>
                <DataTable columns={CHURN_COLUMNS} rows={churn} rowKey={(row) => row.path} searchable emptyMessage="No files in scope" caption="Affected files" />
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

export default function ImpactAnalysisPage() {
  return (
    <>
      <PageHeader title="Impact Analysis" description="Blast radius of pending changes: affected files, folders, and the resulting risk." />
      <RequireRepository>{(repo) => <ImpactBody repo={repo} />}</RequireRepository>
    </>
  );
}
