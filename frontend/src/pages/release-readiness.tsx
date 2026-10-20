import { useState } from "react";
import { Rocket } from "lucide-react";
import { useReleaseAnalysis } from "@/api/hooks";
import { AnalysisReportView } from "@/components/common/analysis-report-view";
import { PageHeader } from "@/components/common/page-header";
import { RequireRepository } from "@/components/common/require-repository";
import { ErrorState, LoadingState } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label, Select } from "@/components/ui/input";
import { evaluateReleaseGate, type ReleaseDecision, validateBranchPair, validateRef } from "@/lib/gates";
import type { CompareMode, RepositoryInfo } from "@/lib/types";
import { cn } from "@/lib/utils";

const DECISION_STYLES: Record<ReleaseDecision, string> = {
  GO: "border-success/50 bg-success/10 text-success",
  CONDITIONAL_GO: "border-warning/50 bg-warning/10 text-warning",
  NO_GO: "border-destructive/50 bg-destructive/10 text-destructive",
};

function ReleaseBody({ repo }: { repo: RepositoryInfo }) {
  const release = useReleaseAnalysis();
  const [source, setSource] = useState(repo.current_branch ?? "");
  const [target, setTarget] = useState(repo.default_branch ?? "");
  const [compareMode, setCompareMode] = useState<CompareMode>("MERGE_BASE");

  const error = validateRef("Source branch", source, true) ?? validateRef("Target branch", target, false) ?? validateBranchPair(source, target);
  const report = release.data;
  const gate = report ? evaluateReleaseGate(report) : null;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Release candidate</CardTitle>
          <CardDescription>Compares the source branch against the target and produces a CAB readiness decision.</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="grid gap-4 md:grid-cols-2 xl:grid-cols-[1fr_1fr_12rem_auto] md:items-end"
            onSubmit={(event) => {
              event.preventDefault();
              if (error) return;
              release.mutate({
                repo_path: repo.path,
                source_branch: source.trim(),
                target_branch: target.trim() || null,
                compare_mode: compareMode,
              });
            }}
          >
            <div className="space-y-1.5">
              <Label htmlFor="release-source">Source branch</Label>
              <Input id="release-source" value={source} onChange={(e) => setSource(e.target.value)} className="font-mono" aria-invalid={Boolean(error)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="release-target">Target branch</Label>
              <Input id="release-target" value={target} onChange={(e) => setTarget(e.target.value)} placeholder="Defaults to repository default" className="font-mono" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="release-compare">Compare mode</Label>
              <Select id="release-compare" value={compareMode} onChange={(e) => setCompareMode(e.target.value as CompareMode)}>
                <option value="MERGE_BASE">Merge base</option>
                <option value="DIRECT">Direct</option>
              </Select>
            </div>
            <Button type="submit" disabled={Boolean(error) || release.isPending}>
              <Rocket aria-hidden="true" /> {release.isPending ? "Evaluating..." : "Evaluate"}
            </Button>
          </form>
          {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>

      {release.isPending && <LoadingState rows={3} label="Evaluating release" />}
      {release.isError && <ErrorState error={release.error} />}

      {gate && report && (
        <>
          <div className="grid gap-4 xl:grid-cols-3">
            <Card className={cn("border-2 xl:col-span-1", DECISION_STYLES[gate.decision])}>
              <CardContent className="flex flex-col gap-3 p-6">
                <p className="text-xs font-semibold uppercase tracking-wide">CAB decision</p>
                <p className="text-3xl font-bold">{gate.decision.replace(/_/g, " ")}</p>
                <ul className="list-disc pl-5 text-sm text-foreground">
                  {gate.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
            <Card className="xl:col-span-2">
              <CardHeader>
                <CardTitle>Release checklist</CardTitle>
                <CardDescription>Items the change advisory board reviews.</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="divide-y divide-border">
                  {gate.checklist.map((item) => (
                    <li key={item.label} className="flex items-center justify-between py-2.5 text-sm">
                      <span>{item.label}</span>
                      <span className={item.passed ? "font-semibold text-success" : "font-semibold text-destructive"}>
                        {item.passed ? "Pass" : "Fail"}
                      </span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>
          <AnalysisReportView report={report} title={`Release: ${source} to ${target || "default"}`} exportName={`release-${repo.name}`} />
        </>
      )}
    </div>
  );
}

export default function ReleaseReadinessPage() {
  return (
    <>
      <PageHeader title="Release Readiness" description="Release gate and CAB checklist for a source branch against its target." />
      <RequireRepository>{(repo) => <ReleaseBody repo={repo} />}</RequireRepository>
    </>
  );
}
