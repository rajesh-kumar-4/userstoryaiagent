import { FileSearch } from "lucide-react";
import { usePreCommitAnalysis } from "@/api/hooks";
import { AnalysisReportView } from "@/components/common/analysis-report-view";
import { PageHeader } from "@/components/common/page-header";
import { RequireRepository } from "@/components/common/require-repository";
import { ErrorState, LoadingState } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { evaluatePreCommitGate, type PreCommitDecision } from "@/lib/gates";
import type { RepositoryInfo } from "@/lib/types";
import { cn } from "@/lib/utils";

const DECISION_STYLES: Record<PreCommitDecision, string> = {
  PASS: "border-success/50 bg-success/10 text-success",
  WARN: "border-warning/50 bg-warning/10 text-warning",
  BLOCK: "border-destructive/50 bg-destructive/10 text-destructive",
};

function PreCommitBody({ repo }: { repo: RepositoryInfo }) {
  const validation = usePreCommitAnalysis();
  const report = validation.data;
  const gate = report ? evaluatePreCommitGate(report) : null;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex-row flex-wrap items-center justify-between gap-3 space-y-0">
          <div>
            <CardTitle>Staged changes</CardTitle>
            <CardDescription>Validates the currently staged changes in {repo.name} before commit.</CardDescription>
          </div>
          <Button onClick={() => validation.mutate(repo.path)} disabled={validation.isPending}>
            <FileSearch aria-hidden="true" /> {validation.isPending ? "Validating..." : "Validate"}
          </Button>
        </CardHeader>
      </Card>

      {validation.isPending && <LoadingState rows={3} label="Validating staged changes" />}
      {validation.isError && <ErrorState error={validation.error} onRetry={() => validation.mutate(repo.path)} />}

      {gate && report && (
        <>
          <Card className={cn("border-2", DECISION_STYLES[gate.decision])}>
            <CardContent className="flex flex-col gap-3 p-6">
              <p className="text-xs font-semibold uppercase tracking-wide">Commit decision</p>
              <p className="text-3xl font-bold">{gate.decision}</p>
              <ul className="list-disc pl-5 text-sm text-foreground">
                {gate.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
          <AnalysisReportView report={report} title="Pre-commit analysis" exportName={`pre-commit-${repo.name}`} />
        </>
      )}
    </div>
  );
}

export default function PreCommitValidationPage() {
  return (
    <>
      <PageHeader title="Pre-Commit Validation" description="Gate decision for staged changes: PASS, WARN, or BLOCK." />
      <RequireRepository>{(repo) => <PreCommitBody repo={repo} />}</RequireRepository>
    </>
  );
}
