import { Gauge } from "lucide-react";
import { useCriticalityAnalysis } from "@/api/hooks";
import { ScoreBars } from "@/components/charts/breakdown-bars";
import { ScoreGauge } from "@/components/charts/score-gauge";
import { ExportMenu } from "@/components/common/export-menu";
import { PageHeader } from "@/components/common/page-header";
import { RequireRepository } from "@/components/common/require-repository";
import { ErrorState, LoadingState } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ExportDocument } from "@/lib/exporters";
import type { CriticalityReport, RepositoryInfo } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

function buildCriticalityDocument(report: CriticalityReport): ExportDocument {
  return {
    title: `Criticality assessment: ${report.repository}`,
    subtitle: `Score ${report.score} (${report.level})`,
    generatedAt: report.generated_at,
    tables: [
      {
        name: "Factors",
        columns: ["Factor", "Score"],
        rows: Object.entries(report.factors).map(([factor, score]) => [factor, score]),
      },
      {
        name: "Rationale",
        columns: ["Rationale", "Source"],
        rows: [[report.rationale, report.rationale_source]],
      },
    ],
  };
}

function CriticalityBody({ repo }: { repo: RepositoryInfo }) {
  const assessment = useCriticalityAnalysis();
  const report = assessment.data;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex-row flex-wrap items-center justify-between gap-3 space-y-0">
          <div>
            <CardTitle>Business criticality</CardTitle>
            <CardDescription>How critical this repository is, based on its scored factors.</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {report && <ExportMenu fileName={`criticality-${repo.name}`} jsonData={report} buildDocument={() => buildCriticalityDocument(report)} />}
            <Button onClick={() => assessment.mutate(repo.path)} disabled={assessment.isPending}>
              <Gauge aria-hidden="true" /> {assessment.isPending ? "Assessing..." : report ? "Re-assess" : "Assess criticality"}
            </Button>
          </div>
        </CardHeader>
      </Card>

      {assessment.isPending && <LoadingState rows={3} label="Assessing criticality" />}
      {assessment.isError && <ErrorState error={assessment.error} />}

      {report && (
        <div className="grid gap-4 xl:grid-cols-3">
          <Card>
            <CardContent className="flex flex-col items-center gap-2 py-6">
              <ScoreGauge score={report.score} level={report.level} label="Criticality" />
              <p className="text-xs text-muted-foreground">Assessed {formatDateTime(report.generated_at)}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Factors</CardTitle>
              <CardDescription>Each factor scored 0-100.</CardDescription>
            </CardHeader>
            <CardContent>
              <ScoreBars data={report.factors} emptyMessage="No factors reported" />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Rationale</CardTitle>
              <CardDescription>Source: {report.rationale_source}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-line text-sm leading-relaxed">{report.rationale || "No rationale provided."}</p>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

export default function CriticalityAssessmentPage() {
  return (
    <>
      <PageHeader title="Criticality Assessment" description="Scored business criticality of the selected repository, with rationale." />
      <RequireRepository>{(repo) => <CriticalityBody repo={repo} />}</RequireRepository>
    </>
  );
}
