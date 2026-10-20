import { useEvents } from "@/api/hooks";
import { PageHeader } from "@/components/common/page-header";
import { RequireRepository } from "@/components/common/require-repository";
import { DataTable, type Column } from "@/components/common/data-table";
import { ErrorState, LoadingState } from "@/components/common/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ChangeEvent, RepositoryInfo } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

const EVENT_COLUMNS: Column<ChangeEvent>[] = [
  { key: "when", header: "Detected", render: (row) => formatDateTime(row.occurred_at) },
  { key: "file", header: "Manifest", render: (row) => <span className="font-mono text-xs">{row.file ?? "-"}</span>, searchText: (row) => row.file ?? "" },
  { key: "branch", header: "Branch", render: (row) => row.branch ?? "-" },
  {
    key: "payload",
    header: "Details",
    render: (row) => <code className="block max-w-lg truncate text-xs text-muted-foreground">{JSON.stringify(row.payload)}</code>,
    searchText: (row) => JSON.stringify(row.payload),
  },
];

function DependencyBody({ repo }: { repo: RepositoryInfo }) {
  const events = useEvents(repo.id, "DEPENDENCY_UPDATED", 200);

  return (
    <div className="space-y-6">
      <div className="rounded-md border border-warning/40 bg-warning/10 p-3 text-sm">
        The backend does not provide a package dependency graph. This page lists dependency manifest changes the monitor has recorded for this repository.
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Detected technologies</CardTitle>
          <CardDescription>Tags inferred from manifest files during discovery.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {repo.technology_tags.length === 0 ? (
            <span className="text-sm text-muted-foreground">No technology tags detected.</span>
          ) : (
            repo.technology_tags.map((tag) => (
              <Badge key={tag} variant="secondary">
                {tag}
              </Badge>
            ))
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Dependency manifest changes</CardTitle>
          <CardDescription>Recorded by the workspace monitor. Refreshes every 15 seconds while Live is on.</CardDescription>
        </CardHeader>
        <CardContent>
          {events.isPending ? (
            <LoadingState rows={3} label="Loading dependency events" />
          ) : events.isError ? (
            <ErrorState error={events.error} onRetry={() => void events.refetch()} />
          ) : (
            <DataTable columns={EVENT_COLUMNS} rows={events.data} rowKey={(row) => row.event_id} searchable searchPlaceholder="Filter by manifest or detail" emptyMessage="No dependency manifest changes recorded" caption="Dependency manifest changes" />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function DependencyAnalysisPage() {
  return (
    <>
      <PageHeader title="Dependency Analysis" description="Dependency manifest activity and detected technologies for the selected repository." />
      <RequireRepository>{(repo) => <DependencyBody repo={repo} />}</RequireRepository>
    </>
  );
}
