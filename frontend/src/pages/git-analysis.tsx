import { useState } from "react";
import { useBranches, useCommits, useHistory, useRepositoryStatus } from "@/api/hooks";
import { RequireRepository } from "@/components/common/require-repository";
import { BreakdownBars } from "@/components/charts/breakdown-bars";
import { DataTable, type Column } from "@/components/common/data-table";
import { PageHeader } from "@/components/common/page-header";
import { ErrorState, LoadingState } from "@/components/common/states";
import { StatCard } from "@/components/common/stat-card";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import type { ChangedFile, CommitInfo, RepositoryInfo } from "@/lib/types";
import { formatDateTime, formatNumber, shortSha } from "@/lib/utils";

const COMMIT_COLUMNS: Column<CommitInfo>[] = [
  { key: "sha", header: "Commit", render: (row) => <span className="font-mono text-xs">{row.short_sha}</span> },
  { key: "summary", header: "Summary", render: (row) => <span className="line-clamp-2">{row.summary}</span>, searchText: (row) => row.summary },
  { key: "author", header: "Author", render: (row) => row.author_name, searchText: (row) => row.author_name },
  { key: "when", header: "Authored", render: (row) => formatDateTime(row.authored_at) },
];

const FILE_COLUMNS: Column<ChangedFile>[] = [
  { key: "path", header: "File", render: (row) => <span className="font-mono text-xs">{row.path}</span>, searchText: (row) => row.path },
  { key: "type", header: "Change", render: (row) => <Badge variant="outline">{row.change_type}</Badge> },
  { key: "area", header: "Area", render: (row) => row.area },
  { key: "churn", header: "Lines +/-/~", render: (row) => `+${row.added_lines} / -${row.deleted_lines} / ~${row.modified_lines}` },
];

function GitAnalysisBody({ repo }: { repo: RepositoryInfo }) {
  const [ref, setRef] = useState("HEAD");
  const [draftRef, setDraftRef] = useState("HEAD");
  const branches = useBranches(repo.id);
  const history = useHistory(repo.id, ref, 100);
  const status = useRepositoryStatus(repo.id);
  const commits = useCommits(repo.id, ref, 50);
  // ChangeSet has no is_dirty flag; any listed file means the working tree has changes.
  const changedCount = status.data?.files.length ?? 0;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Current branch" value={repo.current_branch ?? "-"} hint={`Default: ${repo.default_branch ?? "-"}`} />
        <StatCard label="HEAD" value={shortSha(repo.latest_commit)} hint={repo.remote_origin ?? "No remote"} />
        <StatCard
          label="Changed files"
          value={status.data ? formatNumber(changedCount) : "-"}
          tone={changedCount > 0 ? "warning" : "success"}
          hint={changedCount > 0 ? "Uncommitted changes" : "Clean working tree"}
        />
        <StatCard label="Commits in history" value={history.data ? formatNumber(history.data.commit_count) : "-"} hint={`${history.data?.author_count ?? 0} authors`} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Reference</CardTitle>
          <CardDescription>Analyze history for a branch, tag, or commit.</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="flex flex-col gap-3 sm:flex-row sm:items-end"
            onSubmit={(event) => {
              event.preventDefault();
              if (draftRef.trim()) setRef(draftRef.trim());
            }}
          >
            <div className="flex-1 space-y-1.5">
              <Label htmlFor="git-ref">Ref</Label>
              <Input id="git-ref" value={draftRef} onChange={(e) => setDraftRef(e.target.value)} list="git-ref-options" />
              <datalist id="git-ref-options">
                {branches.data?.map((branch) => (
                  <option key={branch.name} value={branch.name} />
                ))}
              </datalist>
            </div>
            <button type="submit" className="h-9 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90">
              Analyze ref
            </button>
          </form>
          {branches.isError && <div className="mt-3"><ErrorState error={branches.error} /></div>}
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Recent commits</CardTitle>
            <CardDescription>Latest commits on {ref}.</CardDescription>
          </CardHeader>
          <CardContent>
            {commits.isPending ? (
              <LoadingState rows={4} />
            ) : commits.isError ? (
              <ErrorState error={commits.error} onRetry={() => void commits.refetch()} />
            ) : (
              <DataTable columns={COMMIT_COLUMNS} rows={commits.data} rowKey={(row) => row.sha} searchable searchPlaceholder="Filter commits" emptyMessage="No commits found for this ref" caption="Recent commits" />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Top authors</CardTitle>
            <CardDescription>Commits per author in the analyzed history.</CardDescription>
          </CardHeader>
          <CardContent>
            {history.isPending ? <LoadingState rows={3} /> : history.isError ? <ErrorState error={history.error} /> : <BreakdownBars data={history.data.top_authors} emptyMessage="No authors found" />}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Working tree changes</CardTitle>
          <CardDescription>Staged, unstaged, and untracked files compared to HEAD.</CardDescription>
        </CardHeader>
        <CardContent>
          {status.isPending ? (
            <LoadingState rows={3} />
          ) : status.isError ? (
            <ErrorState error={status.error} onRetry={() => void status.refetch()} />
          ) : (
            <DataTable columns={FILE_COLUMNS} rows={status.data.files} rowKey={(row) => `${row.area}:${row.path}`} searchable emptyMessage="Working tree is clean" caption="Working tree changes" />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function GitAnalysisPage() {
  return (
    <>
      <PageHeader title="Git Analysis" description="Commit history, authorship, working tree state, and branch metadata for the selected repository." />
      <RequireRepository>{(repo) => <GitAnalysisBody repo={repo} />}</RequireRepository>
    </>
  );
}
