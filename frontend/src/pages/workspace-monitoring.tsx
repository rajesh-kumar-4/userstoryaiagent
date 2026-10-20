import { useState } from "react";
import { Play, Save } from "lucide-react";
import { useMonitorStatus, useRunMonitorScan, useUpdateMonitor, useWorkspaceSummary } from "@/api/hooks";
import { DataTable, type Column } from "@/components/common/data-table";
import { PageHeader } from "@/components/common/page-header";
import { StatCard } from "@/components/common/stat-card";
import { ErrorState, LoadingState } from "@/components/common/states";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label, Select } from "@/components/ui/input";
import type { MonitorConfig, MonitorMode, RepositoryStatusSummary } from "@/lib/types";
import { formatDateTime, formatNumber, formatRelative, shortSha } from "@/lib/utils";

const MONITOR_MODES: MonitorMode[] = ["MANUAL", "SCHEDULED", "CONTINUOUS"];
const MIN_INTERVAL = 1;
const MAX_INTERVAL = 86400;

const STATUS_COLUMNS: Column<RepositoryStatusSummary>[] = [
  { key: "repository", header: "Repository", render: (row) => <span className="font-medium">{row.repository}</span>, searchText: (row) => row.repository },
  { key: "branch", header: "Branch", render: (row) => row.current_branch ?? "-" },
  { key: "commit", header: "Latest commit", render: (row) => <span className="font-mono text-xs">{shortSha(row.latest_commit)}</span> },
  { key: "changed", header: "Changed files", render: (row) => formatNumber(row.changed_files), className: "text-right" },
  {
    key: "state",
    header: "State",
    render: (row) =>
      row.error ? (
        <Badge variant="CRITICAL">Error</Badge>
      ) : row.is_dirty ? (
        <Badge variant="MEDIUM">Dirty</Badge>
      ) : (
        <Badge variant="LOW">Clean</Badge>
      ),
  },
  { key: "error", header: "Error", render: (row) => <span className="text-xs text-muted-foreground">{row.error ?? ""}</span> },
];

export default function WorkspaceMonitoringPage() {
  const summary = useWorkspaceSummary();
  const status = useMonitorStatus();
  const updateMonitor = useUpdateMonitor();
  const runScan = useRunMonitorScan();
  const [draft, setDraft] = useState<MonitorConfig | null>(null);

  const config = draft ?? status.data?.config ?? null;
  const intervalValid = config !== null && Number.isInteger(config.interval_seconds) && config.interval_seconds >= MIN_INTERVAL && config.interval_seconds <= MAX_INTERVAL;
  const debounceValid = config !== null && Number.isFinite(config.debounce_seconds) && config.debounce_seconds >= 0;
  const formError = !intervalValid
    ? `Interval must be a whole number between ${MIN_INTERVAL} and ${MAX_INTERVAL} seconds`
    : !debounceValid
      ? "Debounce must be zero or greater"
      : null;

  return (
    <>
      <PageHeader title="Workspace Monitoring" description="Tracked repositories, monitor configuration, and manual scans." />

      {summary.isPending ? (
        <LoadingState rows={2} label="Loading workspace" />
      ) : summary.isError ? (
        <ErrorState error={summary.error} onRetry={() => void summary.refetch()} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Repositories" value={formatNumber(summary.data.repository_count)} />
          <StatCard label="Dirty" value={formatNumber(summary.data.dirty_repository_count)} tone={summary.data.dirty_repository_count > 0 ? "warning" : "success"} />
          <StatCard label="Pending events" value={formatNumber(status.data?.pending_events ?? 0)} tone={(status.data?.pending_events ?? 0) > 0 ? "warning" : "default"} />
          <StatCard
            label="Monitor"
            value={status.data?.running ? "Running" : "Stopped"}
            hint={status.data?.last_cycle_at ? `Last cycle ${formatRelative(status.data.last_cycle_at)}` : "No cycle yet"}
            tone={status.data?.running ? "success" : "danger"}
          />
        </div>
      )}

      <div className="mt-6 grid gap-6 xl:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Monitor configuration</CardTitle>
            <CardDescription>Controls how changes are detected across tracked repositories.</CardDescription>
          </CardHeader>
          <CardContent>
            {status.isPending ? (
              <LoadingState rows={3} label="Loading monitor" />
            ) : status.isError ? (
              <ErrorState error={status.error} onRetry={() => void status.refetch()} />
            ) : config ? (
              <form
                className="space-y-4"
                onSubmit={(event) => {
                  event.preventDefault();
                  if (formError) return;
                  updateMonitor.mutate(config, { onSuccess: () => setDraft(null) });
                }}
              >
                <div className="space-y-1.5">
                  <Label htmlFor="monitor-mode">Mode</Label>
                  <Select id="monitor-mode" value={config.mode} onChange={(e) => setDraft({ ...config, mode: e.target.value as MonitorMode })}>
                    {MONITOR_MODES.map((mode) => (
                      <option key={mode} value={mode}>
                        {mode.charAt(0) + mode.slice(1).toLowerCase()}
                      </option>
                    ))}
                  </Select>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label htmlFor="monitor-interval">Interval (seconds)</Label>
                    <Input
                      id="monitor-interval"
                      type="number"
                      min={MIN_INTERVAL}
                      max={MAX_INTERVAL}
                      value={config.interval_seconds}
                      onChange={(e) => setDraft({ ...config, interval_seconds: Number(e.target.value) })}
                      aria-invalid={!intervalValid}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="monitor-debounce">Debounce (seconds)</Label>
                    <Input
                      id="monitor-debounce"
                      type="number"
                      min={0}
                      value={config.debounce_seconds}
                      onChange={(e) => setDraft({ ...config, debounce_seconds: Number(e.target.value) })}
                      aria-invalid={!debounceValid}
                    />
                  </div>
                </div>
                {formError && <p className="text-sm text-destructive">{formError}</p>}
                <div className="flex flex-wrap items-center gap-2">
                  <Button type="submit" disabled={Boolean(formError) || updateMonitor.isPending || draft === null}>
                    <Save aria-hidden="true" /> {updateMonitor.isPending ? "Saving..." : "Save configuration"}
                  </Button>
                  <Button type="button" variant="outline" onClick={() => runScan.mutate()} disabled={runScan.isPending}>
                    <Play aria-hidden="true" /> {runScan.isPending ? "Scanning..." : "Scan now"}
                  </Button>
                </div>
                {updateMonitor.isError && <ErrorState error={updateMonitor.error} />}
                {runScan.isSuccess && <p className="text-sm text-muted-foreground">Scan complete: {runScan.data.length} new event(s).</p>}
                {runScan.isError && <ErrorState error={runScan.error} />}
              </form>
            ) : null}
          </CardContent>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Repository status</CardTitle>
            <CardDescription>Refreshes every 15 seconds while Live is on.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {status.data && Object.keys(status.data.repository_errors).length > 0 && (
              <Alert variant="destructive">
                <AlertTitle>Monitor errors</AlertTitle>
                <AlertDescription>
                  <ul className="list-disc pl-5">
                    {Object.entries(status.data.repository_errors).map(([repo, message]) => (
                      <li key={repo}>
                        <span className="font-medium">{repo}</span>: {message}
                      </li>
                    ))}
                  </ul>
                </AlertDescription>
              </Alert>
            )}
            {summary.data && (
              <DataTable columns={STATUS_COLUMNS} rows={summary.data.repositories} rowKey={(row) => row.repository} searchable searchPlaceholder="Filter repositories" emptyMessage="No repositories tracked" caption="Repository status" />
            )}
            {status.data && <p className="text-xs text-muted-foreground">Tracking {status.data.tracked_repositories} repositor{status.data.tracked_repositories === 1 ? "y" : "ies"}. Generated {summary.data ? formatDateTime(summary.data.generated_at) : "-"}.</p>}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
