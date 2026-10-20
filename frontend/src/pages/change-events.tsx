import { useState } from "react";
import { useEvents } from "@/api/hooks";
import { useSelectedRepository } from "@/api/use-selected-repository";
import { DataTable, type Column } from "@/components/common/data-table";
import { ExportMenu } from "@/components/common/export-menu";
import { PageHeader } from "@/components/common/page-header";
import { ErrorState, LoadingState } from "@/components/common/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import { Label, Select } from "@/components/ui/input";
import type { ExportDocument } from "@/lib/exporters";
import type { ChangeEvent, EventType } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

const EVENT_TYPES: EventType[] = [
  "REPOSITORY_DISCOVERED",
  "REPOSITORY_REMOVED",
  "FILE_MODIFIED",
  "FILE_DELETED",
  "DEPENDENCY_UPDATED",
  "CONFIG_UPDATED",
  "COMMIT_CREATED",
  "BRANCH_CHANGED",
  "MERGE_COMPLETED",
  "PR_CREATED",
  "ANALYSIS_REQUESTED",
];

const LIMIT_OPTIONS = [50, 100, 200] as const;

const EVENT_COLUMNS: Column<ChangeEvent>[] = [
  { key: "when", header: "Occurred", render: (row) => formatDateTime(row.occurred_at) },
  { key: "type", header: "Type", render: (row) => <Badge variant="outline">{row.type}</Badge>, searchText: (row) => row.type },
  { key: "repository", header: "Repository", render: (row) => <span className="font-mono text-xs">{row.repository}</span>, searchText: (row) => row.repository },
  { key: "branch", header: "Branch", render: (row) => row.branch ?? "-", searchText: (row) => row.branch ?? "" },
  { key: "file", header: "File", render: (row) => <span className="font-mono text-xs">{row.file ?? "-"}</span>, searchText: (row) => row.file ?? "" },
  {
    key: "payload",
    header: "Payload",
    render: (row) => <code className="block max-w-md truncate text-xs text-muted-foreground">{JSON.stringify(row.payload)}</code>,
    searchText: (row) => JSON.stringify(row.payload),
  },
];

function buildEventsDocument(events: ChangeEvent[]): ExportDocument {
  return {
    title: "Change events",
    generatedAt: new Date().toISOString(),
    tables: [
      {
        name: "Events",
        columns: ["Occurred", "Type", "Repository", "Branch", "File", "Payload"],
        rows: events.map((e) => [e.occurred_at, e.type, e.repository, e.branch, e.file, JSON.stringify(e.payload)]),
      },
    ],
  };
}

export default function ChangeEventsPage() {
  const { id: repositoryId } = useSelectedRepository();
  const [type, setType] = useState<EventType | "">("");
  const [limit, setLimit] = useState<(typeof LIMIT_OPTIONS)[number]>(100);
  const [scoped, setScoped] = useState(false);

  const repository = scoped && repositoryId ? repositoryId : null;
  const events = useEvents(repository, type === "" ? null : type, limit);
  const rows = events.data;

  return (
    <>
      <PageHeader title="Change Events" description="Recent change events detected by the workspace monitor." />

      <Card>
        <CardHeader className="flex-row flex-wrap items-end justify-between gap-4 space-y-0">
          <div className="flex flex-wrap items-end gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="event-type">Event type</Label>
              <Select id="event-type" value={type} onChange={(e) => setType(e.target.value as EventType | "")} className="sm:w-56">
                <option value="">All types</option>
                {EVENT_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.replace(/_/g, " ").toLowerCase()}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="event-limit">Limit</Label>
              <Select id="event-limit" value={limit} onChange={(e) => setLimit(Number(e.target.value) as (typeof LIMIT_OPTIONS)[number])} className="sm:w-32">
                {LIMIT_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </Select>
            </div>
            <label className="flex items-center gap-2 pb-2 text-sm">
              <input type="checkbox" className="size-4 accent-primary" checked={scoped} onChange={(e) => setScoped(e.target.checked)} disabled={!repositoryId} />
              Selected repository only
            </label>
          </div>
          {rows && <ExportMenu fileName="change-events" jsonData={rows} buildDocument={() => buildEventsDocument(rows)} />}
        </CardHeader>
        <CardContent className="space-y-3">
          <CardDescription>Refreshes every 15 seconds while Live is on.</CardDescription>
          {events.isPending ? (
            <LoadingState rows={5} label="Loading events" />
          ) : events.isError ? (
            <ErrorState error={events.error} onRetry={() => void events.refetch()} />
          ) : (
            <DataTable columns={EVENT_COLUMNS} rows={events.data} rowKey={(row) => row.event_id} searchable searchPlaceholder="Filter events" emptyMessage="No events match the current filters" caption="Change events" />
          )}
        </CardContent>
      </Card>
    </>
  );
}
