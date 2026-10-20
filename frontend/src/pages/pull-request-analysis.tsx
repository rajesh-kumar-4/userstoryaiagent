import { useState } from "react";
import { GitPullRequest } from "lucide-react";
import { useBranches, usePullRequestAnalysis, usePullRequestRefs } from "@/api/hooks";
import { AnalysisReportView } from "@/components/common/analysis-report-view";
import { DataTable, type Column } from "@/components/common/data-table";
import { RefSelect } from "@/components/common/ref-select";
import { PageHeader } from "@/components/common/page-header";
import { RequireRepository } from "@/components/common/require-repository";
import { ErrorState, LoadingState } from "@/components/common/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { validateBranchPair, validateRef } from "@/lib/gates";
import type { PullRequestRef, RepositoryInfo } from "@/lib/types";
import { shortSha } from "@/lib/utils";

function PullRequestBody({ repo }: { repo: RepositoryInfo }) {
  const branches = useBranches(repo.id);
  const prs = usePullRequestRefs(repo.id);
  const analysis = usePullRequestAnalysis();
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");

  const options = [
    ...(prs.data ?? []).map((pr) => ({ value: pr.ref, label: `PR ${pr.number ?? ""} ${pr.ref}`.trim() })),
    ...(branches.data ?? []).map((b) => ({ value: b.name, label: b.name })),
  ];
  const unique = options.filter((o, i) => options.findIndex((x) => x.value === o.value) === i);
  const error = validateRef("Source", source, true) ?? validateRef("Target", target, true) ?? validateBranchPair(source, target);

  const columns: Column<PullRequestRef>[] = [
    { key: "number", header: "PR", render: (row) => (row.number !== null ? `#${row.number}` : "-") },
    { key: "ref", header: "Ref", render: (row) => <span className="font-mono text-xs">{row.ref}</span>, searchText: (row) => row.ref },
    { key: "head", header: "Head", render: (row) => <span className="font-mono text-xs">{shortSha(row.head_sha)}</span> },
    { key: "provider", header: "Provider", render: (row) => <Badge variant="outline">{row.provider}</Badge> },
    {
      key: "use",
      header: "",
      render: (row) => (
        <Button variant="outline" size="sm" onClick={() => setSource(row.ref)}>
          Use as source
        </Button>
      ),
      className: "text-right",
    },
  ];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Open pull request refs</CardTitle>
          <CardDescription>Refs discovered in the repository. Choose one as the source, then pick a target branch.</CardDescription>
        </CardHeader>
        <CardContent>
          {prs.isPending ? (
            <LoadingState rows={2} label="Loading pull request refs" />
          ) : prs.isError ? (
            <ErrorState error={prs.error} onRetry={() => void prs.refetch()} />
          ) : (
            <DataTable columns={columns} rows={prs.data} rowKey={(row) => row.ref} emptyMessage="No pull request refs found" caption="Pull request refs" />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Analyze pull request</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="grid gap-4 md:grid-cols-2 md:items-end"
            onSubmit={(event) => {
              event.preventDefault();
              if (error) return;
              analysis.mutate({ repo_path: repo.path, source_branch: source.trim(), target_branch: target.trim() });
            }}
          >
            <RefSelect id="pr-source" label="Source (PR head)" value={source} onChange={setSource} options={unique} />
            <RefSelect id="pr-target" label="Target (base)" value={target} onChange={setTarget} options={(branches.data ?? []).map((b) => ({ value: b.name, label: b.name }))} />
            <Button type="submit" disabled={!!error || analysis.isPending} className="md:col-span-2 md:w-fit">
              <GitPullRequest aria-hidden="true" /> {analysis.isPending ? "Analyzing..." : "Analyze pull request"}
            </Button>
          </form>
          {error && source && target && <p className="mt-3 text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>

      {analysis.isPending && <LoadingState rows={3} label="Running pull request analysis" />}
      {analysis.isError && <ErrorState error={analysis.error} />}
      {analysis.data && <AnalysisReportView report={analysis.data} title={`Pull request: ${source} into ${target}`} exportName={`pr-${source}-${target}`} />}
    </div>
  );
}

export default function PullRequestAnalysisPage() {
  return (
    <>
      <PageHeader title="Pull Request Analysis" description="Risk review of a pull request's head against its base branch." />
      <RequireRepository>{(repo) => <PullRequestBody repo={repo} />}</RequireRepository>
    </>
  );
}
