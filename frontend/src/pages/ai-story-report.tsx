import { useState } from "react";
import { Sparkles } from "lucide-react";
import { useAnalyzeRepository } from "@/api/hooks";
import { AnalysisReportView } from "@/components/common/analysis-report-view";
import { PageHeader } from "@/components/common/page-header";
import { RequireRepository } from "@/components/common/require-repository";
import { RiskBadge } from "@/components/common/risk-badge";
import { ErrorState, LoadingState } from "@/components/common/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label, Select } from "@/components/ui/input";
import type { AnalysisMode, RepositoryInfo } from "@/lib/types";

const STORY_MODES: AnalysisMode[] = ["POST_COMMIT", "PRE_COMMIT", "WORKSPACE_ANALYSIS", "HISTORICAL_ANALYSIS"];

function StoryBody({ repo }: { repo: RepositoryInfo }) {
  const analysis = useAnalyzeRepository();
  const [mode, setMode] = useState<AnalysisMode>("POST_COMMIT");
  const [commitId, setCommitId] = useState("");

  const report = analysis.data;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Generate analysis narrative</CardTitle>
          <CardDescription>
            Produces the risk summary for a change. The narrative uses the configured LLM provider when available, and falls back to the rule-based summary otherwise.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="grid gap-4 md:grid-cols-[1fr_1fr_auto] md:items-end"
            onSubmit={(event) => {
              event.preventDefault();
              analysis.mutate({ repo_path: repo.path, analysis_mode: mode, commit_id: commitId.trim() || null });
            }}
          >
            <div className="space-y-1.5">
              <Label htmlFor="story-mode">Analysis mode</Label>
              <Select id="story-mode" value={mode} onChange={(e) => setMode(e.target.value as AnalysisMode)}>
                {STORY_MODES.map((m) => (
                  <option key={m} value={m}>
                    {m.replace(/_/g, " ").toLowerCase()}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="story-commit">Commit SHA (optional)</Label>
              <Input id="story-commit" value={commitId} onChange={(e) => setCommitId(e.target.value)} placeholder="Defaults to HEAD" className="font-mono" />
            </div>
            <Button type="submit" disabled={analysis.isPending}>
              <Sparkles aria-hidden="true" /> {analysis.isPending ? "Generating..." : "Generate"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {analysis.isPending && <LoadingState rows={3} label="Generating narrative" />}
      {analysis.isError && <ErrorState error={analysis.error} />}

      {report && (
        <>
          <Card className="border-primary/40">
            <CardHeader>
              <div className="flex flex-wrap items-center gap-2">
                <CardTitle>Narrative</CardTitle>
                <RiskBadge level={report.risk_level} />
                <Badge variant="outline">{report.summary_source}</Badge>
                {report.llm_provider && <Badge variant="secondary">{report.llm_provider}</Badge>}
              </div>
              <CardDescription>
                {report.changed_files.length} changed file(s), {report.findings.length} finding(s), risk score {report.risk_score}.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-line text-base leading-relaxed">{report.summary || "No narrative was produced for this analysis."}</p>
            </CardContent>
          </Card>
          <AnalysisReportView report={report} title="Supporting analysis" exportName={`story-${repo.name}`} />
        </>
      )}
    </div>
  );
}

export default function AiStoryReportPage() {
  return (
    <>
      <PageHeader title="AI Story Report" description="Narrative risk summary for a change, with the supporting evidence." />
      <RequireRepository>{(repo) => <StoryBody repo={repo} />}</RequireRepository>
    </>
  );
}
