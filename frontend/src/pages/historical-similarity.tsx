import { useState } from "react";
import { Search } from "lucide-react";
import { useAnalysisByCommit, useSimilarChanges } from "@/api/hooks";
import { useSelectedRepository } from "@/api/use-selected-repository";
import { AnalysisReportView } from "@/components/common/analysis-report-view";
import { DataTable, type Column } from "@/components/common/data-table";
import { PageHeader } from "@/components/common/page-header";
import { RiskBadge } from "@/components/common/risk-badge";
import { ErrorState, LoadingState } from "@/components/common/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import type { SimilarChange } from "@/lib/types";
import { formatNumber, shortSha } from "@/lib/utils";

const SIMILAR_COLUMNS: Column<SimilarChange>[] = [
  { key: "level", header: "Risk", render: (row) => <RiskBadge level={row.risk_level} /> },
  { key: "similarity", header: "Similarity", render: (row) => formatNumber(row.similarity, 3), className: "text-right" },
  { key: "summary", header: "Summary", render: (row) => <span className="line-clamp-2">{row.summary}</span>, searchText: (row) => row.summary },
  {
    key: "terms",
    header: "Matched terms",
    render: (row) => (
      <div className="flex flex-wrap gap-1">
        {row.matched_terms.slice(0, 6).map((term) => (
          <Badge key={term} variant="secondary">
            {term}
          </Badge>
        ))}
      </div>
    ),
    searchText: (row) => row.matched_terms.join(" "),
  },
  { key: "commit", header: "Commit", render: (row) => <span className="font-mono text-xs">{shortSha(row.commit_id)}</span> },
  { key: "mode", header: "Mode", render: (row) => <Badge variant="outline">{row.analysis_mode}</Badge> },
];

export default function HistoricalSimilarityPage() {
  const { id: repositoryId } = useSelectedRepository();
  const similar = useSimilarChanges();
  const commitLookup = useAnalysisByCommit();
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(10);
  const [scoped, setScoped] = useState(true);
  const [commitId, setCommitId] = useState("");

  const canSearch = query.trim().length > 0 && topK >= 1 && topK <= 50;
  const repository = scoped && repositoryId ? repositoryId : null;

  return (
    <>
      <PageHeader
        title="Historical Similarity"
        description="Find past analyses with similar change descriptions, or open the analysis recorded for a commit."
      />

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Search similar changes</CardTitle>
            <CardDescription>Describe the change in plain language. Results are ranked by similarity.</CardDescription>
          </CardHeader>
          <CardContent>
            <form
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                if (canSearch) similar.mutate({ query: query.trim(), repository, top_k: topK });
              }}
            >
              <div className="space-y-1.5">
                <Label htmlFor="similar-query">Change description</Label>
                <Input id="similar-query" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. update payment retry logic" />
              </div>
              <div className="grid gap-4 sm:grid-cols-2 sm:items-end">
                <div className="space-y-1.5">
                  <Label htmlFor="similar-topk">Top results (1-50)</Label>
                  <Input id="similar-topk" type="number" min={1} max={50} value={topK} onChange={(e) => setTopK(Number(e.target.value))} />
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" className="size-4 accent-primary" checked={scoped} onChange={(e) => setScoped(e.target.checked)} disabled={!repositoryId} />
                  Only the selected repository
                </label>
              </div>
              <Button type="submit" disabled={!canSearch || similar.isPending}>
                <Search aria-hidden="true" /> {similar.isPending ? "Searching..." : "Search"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Open analysis by commit</CardTitle>
            <CardDescription>Look up the stored analysis for a commit SHA.</CardDescription>
          </CardHeader>
          <CardContent>
            <form
              className="flex flex-col gap-3 sm:flex-row sm:items-end"
              onSubmit={(event) => {
                event.preventDefault();
                if (commitId.trim()) commitLookup.mutate(commitId.trim());
              }}
            >
              <div className="flex-1 space-y-1.5">
                <Label htmlFor="commit-id">Commit SHA</Label>
                <Input id="commit-id" value={commitId} onChange={(e) => setCommitId(e.target.value)} placeholder="e.g. 3f2a9c1" className="font-mono" />
              </div>
              <Button type="submit" variant="secondary" disabled={!commitId.trim() || commitLookup.isPending}>
                {commitLookup.isPending ? "Loading..." : "Open analysis"}
              </Button>
            </form>
            {commitLookup.isError && <div className="mt-3"><ErrorState error={commitLookup.error} /></div>}
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 space-y-6">
        {similar.isPending && <LoadingState rows={3} label="Searching history" />}
        {similar.isError && <ErrorState error={similar.error} onRetry={() => similar.mutate({ query: query.trim(), repository, top_k: topK })} />}
        {similar.data && (
          <Card>
            <CardHeader>
              <CardTitle>Similar past changes</CardTitle>
              <CardDescription>{similar.data.length} result(s){repository ? " in the selected repository" : " across all repositories"}.</CardDescription>
            </CardHeader>
            <CardContent>
              <DataTable columns={SIMILAR_COLUMNS} rows={similar.data} rowKey={(row) => row.analysis_id} emptyMessage="No similar changes found" caption="Similar changes" />
            </CardContent>
          </Card>
        )}
        {commitLookup.isPending && <LoadingState rows={3} label="Loading commit analysis" />}
        {commitLookup.data && <AnalysisReportView report={commitLookup.data} title={`Analysis for ${shortSha(commitId)}`} exportName={`commit-${shortSha(commitId)}`} />}
      </div>
    </>
  );
}
