import { useState } from "react";
import { Plus, RefreshCw } from "lucide-react";
import { useRefreshRepositories, useRegisterRepository, useRepositories } from "@/api/hooks";
import { DependencyGraph } from "@/components/charts/dependency-graph";
import { DataTable, type Column } from "@/components/common/data-table";
import { PageHeader } from "@/components/common/page-header";
import { ErrorState, InlineSpinner, LoadingState } from "@/components/common/states";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import type { RepositoryInfo } from "@/lib/types";
import { formatRelative, shortSha } from "@/lib/utils";
import { useAppState } from "@/state/app-state";

export default function RepositoryExplorerPage() {
  const repos = useRepositories();
  const refresh = useRefreshRepositories();
  const register = useRegisterRepository();
  const { repository, setRepository } = useAppState();
  const [path, setPath] = useState("");

  const columns: Column<RepositoryInfo>[] = [
    {
      key: "name",
      header: "Name",
      render: (row) => (
        <div className="min-w-0">
          <p className="font-medium">{row.name}</p>
          <p className="max-w-md truncate font-mono text-xs text-muted-foreground" title={row.path}>
            {row.path}
          </p>
        </div>
      ),
      searchText: (row) => `${row.name} ${row.path}`,
    },
    {
      key: "branch",
      header: "Branch",
      render: (row) => (
        <span className="text-xs">
          {row.current_branch ?? "-"}
          {row.is_dirty && <Badge variant="MEDIUM" className="ml-2">dirty</Badge>}
        </span>
      ),
      searchText: (row) => row.current_branch ?? "",
    },
    { key: "commit", header: "HEAD", render: (row) => <span className="font-mono text-xs">{shortSha(row.latest_commit)}</span> },
    {
      key: "tags",
      header: "Technologies",
      render: (row) => (
        <div className="flex flex-wrap gap-1">
          {row.technology_tags.map((tag) => (
            <Badge key={tag} variant="secondary">
              {tag}
            </Badge>
          ))}
        </div>
      ),
      searchText: (row) => row.technology_tags.join(" "),
    },
    { key: "discovered", header: "Discovered", render: (row) => formatRelative(row.discovered_at) },
    {
      key: "select",
      header: "",
      render: (row) => (
        <Button variant={repository === row.id ? "default" : "outline"} size="sm" onClick={() => setRepository(row.id)} aria-pressed={repository === row.id}>
          {repository === row.id ? "Selected" : "Select"}
        </Button>
      ),
      className: "text-right",
    },
  ];

  return (
    <>
      <PageHeader
        title="Repository Explorer"
        description="Registered repositories discovered in the workspace. Select one to use it across the analysis pages."
        actions={
          <Button variant="outline" size="sm" onClick={() => refresh.mutate()} disabled={refresh.isPending}>
            <RefreshCw aria-hidden="true" className={refresh.isPending ? "animate-spin" : ""} />
            Rediscover
          </Button>
        }
      />

      {refresh.isSuccess && (
        <Alert variant="success" className="mb-4">
          <AlertDescription>
            Found {refresh.data.total} repositories ({refresh.data.added.length} added, {refresh.data.removed.length} removed).
          </AlertDescription>
        </Alert>
      )}
      {refresh.isError && <div className="mb-4"><ErrorState error={refresh.error} /></div>}

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Register a repository</CardTitle>
          <CardDescription>Add a repository by its absolute path. It must be inside the configured workspace root.</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="flex flex-col gap-3 sm:flex-row sm:items-end"
            onSubmit={(event) => {
              event.preventDefault();
              if (!path.trim()) return;
              register.mutate(path.trim(), { onSuccess: () => setPath("") });
            }}
          >
            <div className="flex-1 space-y-1.5">
              <Label htmlFor="register-path">Repository path</Label>
              <Input id="register-path" value={path} onChange={(e) => setPath(e.target.value)} placeholder="C:\\workspace\\my-service" />
            </div>
            <Button type="submit" disabled={!path.trim() || register.isPending}>
              <Plus aria-hidden="true" /> Register
            </Button>
          </form>
          {register.isPending && <div className="mt-3"><InlineSpinner label="Registering" /></div>}
          {register.isError && <div className="mt-3"><ErrorState error={register.error} /></div>}
          {register.isSuccess && <p className="mt-3 text-sm text-success">Registered {register.data.name}.</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Repositories</CardTitle>
          <CardDescription>{repos.data ? `${repos.data.length} registered` : "Loading..."}</CardDescription>
        </CardHeader>
        <CardContent>
          {repos.isPending ? (
            <LoadingState rows={4} label="Loading repositories" />
          ) : repos.isError ? (
            <ErrorState error={repos.error} onRetry={() => void repos.refetch()} />
          ) : (
            <DataTable
              columns={columns}
              rows={repos.data}
              rowKey={(row) => row.id}
              searchable
              searchPlaceholder="Filter by name, path, branch, or technology"
              emptyMessage="No repositories discovered. Check the workspace root setting."
              caption="Registered repositories"
            />
          )}
        </CardContent>
      </Card>

      {repos.data && repos.data.length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Relationships</CardTitle>
            <CardDescription>Repositories linked by a shared technology tag (not a code dependency graph).</CardDescription>
          </CardHeader>
          <CardContent>
            <DependencyGraph repositories={repos.data} selectedId={repository} onSelect={setRepository} />
          </CardContent>
        </Card>
      )}
    </>
  );
}
