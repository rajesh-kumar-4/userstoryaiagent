import { useState } from "react";
import { GitCompare } from "lucide-react";
import { useBranchAnalysis, useBranches } from "@/api/hooks";
import { AnalysisReportView } from "@/components/common/analysis-report-view";
import { RefSelect } from "@/components/common/ref-select";
import { RequireRepository } from "@/components/common/require-repository";
import { PageHeader } from "@/components/common/page-header";
import { ErrorState, LoadingState } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label, Select } from "@/components/ui/input";
import { validateBranchPair, validateRef } from "@/lib/gates";
import type { CompareMode, RepositoryInfo } from "@/lib/types";

function BranchComparisonBody({ repo }: { repo: RepositoryInfo }) {
  const branches = useBranches(repo.id);
  const analysis = useBranchAnalysis();
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  const [compareMode, setCompareMode] = useState<CompareMode>("MERGE_BASE");

  const options = (branches.data ?? []).map((b) => ({
    value: b.name,
    label: `${b.name}${b.is_remote ? " (remote)" : ""}${b.is_default ? " (default)" : ""}`,
  }));
  const error = validateRef("Source branch", source, true) ?? validateRef("Target branch", target, true) ?? validateBranchPair(source, target);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Compare branches</CardTitle>
          <CardDescription>
            MERGE_BASE compares against the common ancestor. DIRECT compares the two branch tips.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {branches.isPending ? (
            <LoadingState rows={2} label="Loading branches" />
          ) : branches.isError ? (
            <ErrorState error={branches.error} onRetry={() => void branches.refetch()} />
          ) : (
            <form
              className="grid gap-4 md:grid-cols-2 xl:grid-cols-4 md:items-end"
              onSubmit={(event) => {
                event.preventDefault();
                if (error) return;
                analysis.mutate({ repo_path: repo.path, source_branch: source.trim(), target_branch: target.trim(), compare_mode: compareMode });
              }}
            >
              <RefSelect id="branch-source" label="Source branch" value={source} onChange={setSource} options={options} />
              <RefSelect id="branch-target" label="Target branch" value={target} onChange={setTarget} options={options} />
              <div className="space-y-1.5">
                <Label htmlFor="branch-mode">Compare mode</Label>
                <Select id="branch-mode" value={compareMode} onChange={(e) => setCompareMode(e.target.value as CompareMode)}>
                  <option value="MERGE_BASE">Merge base</option>
                  <option value="DIRECT">Direct</option>
                </Select>
              </div>
              <Button type="submit" disabled={!!error || analysis.isPending}>
                <GitCompare aria-hidden="true" /> {analysis.isPending ? "Comparing..." : "Compare"}
              </Button>
            </form>
          )}
          {error && source && target && <p className="mt-3 text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>

      {analysis.isPending && <LoadingState rows={3} label="Running branch analysis" />}
      {analysis.isError && <ErrorState error={analysis.error} />}
      {analysis.data && (
        <AnalysisReportView
          report={analysis.data}
          title={`Branch comparison: ${source} to ${target}`}
          exportName={`branch-${source}-${target}`}
        />
      )}
    </div>
  );
}

export default function BranchComparisonPage() {
  return (
    <>
      <PageHeader title="Branch Comparison" description="Risk and change analysis between two branches of the selected repository." />
      <RequireRepository>{(repo) => <BranchComparisonBody repo={repo} />}</RequireRepository>
    </>
  );
}
