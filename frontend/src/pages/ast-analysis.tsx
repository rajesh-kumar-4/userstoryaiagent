import { useState } from "react";
import { Layers } from "lucide-react";
import { useChangeScope } from "@/api/hooks";
import { BreakdownBars } from "@/components/charts/breakdown-bars";
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
import type { AnalysisMode, RepositoryInfo } from "@/lib/types";
import { formatNumber } from "@/lib/utils";

type ChurnRow = { path: string; churn: number; type: string };

const CHURN_COLUMNS: Column<ChurnRow>[] = [
  { key: "path", header: "File", render: (row) => <span className="font-mono text-xs">{row.path}</span>, searchText: (row) => row.path },
  { key: "type", header: "Change", render: (row) => <Badge variant="outline">{row.type}</Badge> },
  { key: "churn", header: "Churn (lines)", render: (row) => formatNumber(row.churn), className: "text-right" },
];

function AstBody({ repo }: { repo: RepositoryInfo }) {
  const scope = useChangeScope();
  const [mode, setMode] = useState<AnalysisMode>("WORKSPACE_ANALYSIS");

  const changeSet = scope.data;
  const churn = changeSet ? fileChurn(changeSet) : [];
  const byType: Record<string, number> = {};
  for (const file of changeSet?.files ?? []) byType[file.change_type] = (byType[file.change_type] ?? 0) + 1;

  return (
    <div className="space-y-6">
      <div className="rounded-md border border-warning/40 bg-warning/10 p-3 text-sm">
        The backend has no syntax-tree (AST) endpoint. This view reports file-level structure and churn for the selected scope.
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Scope</CardTitle>
          <CardDescription>Choose the change scope to inspect.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="space-y-1.5">
            <Label htmlFor="ast-mode">Scope</Label>
            <Select id="ast-mode" value={mode} onChange={(e) => setMode(e.target.value as AnalysisMode)} className="sm:w-64">
              <option value="WORKSPACE_ANALYSIS">Working tree (uncommitted)</option>
              <option value="PRE_COMMIT">Staged changes</option>
            </Select>
          </div>
          <Button onClick={() => scope.mutate({ repo_path: repo.path, analysis_mode: mode })} disabled={scope.isPending}>
            <Layers aria-hidden="true" /> {scope.isPending ? "Loading..." : "Inspect scope"}
          </Button>
        </CardContent>
      </Card>

      {scope.isPending && <LoadingState rows={3} label="Reading change scope" />}
      {scope.isError && <ErrorState error={scope.error} />}

      {changeSet && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard label="Files in scope" value={formatNumber(changeSet.files.length)} />
            <StatCard label="Lines added" value={formatNumber(changeSet.totals.added_lines ?? 0)} tone="success" />
            <StatCard label="Lines deleted" value={formatNumber(changeSet.totals.deleted_lines ?? 0)} tone="danger" />
          </div>
          <div className="grid gap-4 xl:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle>Change types</CardTitle>
              </CardHeader>
              <CardContent>
                <BreakdownBars data={byType} emptyMessage="No changed files" />
              </CardContent>
            </Card>
            <Card className="xl:col-span-2">
              <CardHeader>
                <CardTitle>File churn</CardTitle>
                <CardDescription>Ordered by lines touched.</CardDescription>
              </CardHeader>
              <CardContent>
                <DataTable columns={CHURN_COLUMNS} rows={churn} rowKey={(row) => row.path} searchable emptyMessage="No files in this scope" caption="File churn" />
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

export default function AstAnalysisPage() {
  return (
    <>
      <PageHeader title="AST Analysis" description="File-level structure and churn for the current change scope." />
      <RequireRepository>{(repo) => <AstBody repo={repo} />}</RequireRepository>
    </>
  );
}
