import { useMemo } from "react";
import { useRepositories } from "@/api/hooks";
import { BreakdownBars } from "@/components/charts/breakdown-bars";
import { DependencyGraph } from "@/components/charts/dependency-graph";
import { ErrorState, LoadingState } from "@/components/common/states";
import { PageHeader } from "@/components/common/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { tagUsage } from "@/lib/graph";
import { useAppState } from "@/state/app-state";

export default function RepositoryDependencyMapPage() {
  const repos = useRepositories();
  const { repository, setRepository } = useAppState();

  const usage = useMemo(() => {
    const rows = tagUsage(repos.data ?? []);
    return Object.fromEntries(rows.map((row) => [row.tag, row.count]));
  }, [repos.data]);

  return (
    <>
      <PageHeader
        title="Repository Dependency Map"
        description="Relationships between repositories. Links show repositories that share a technology tag."
      />
      <div className="mb-4 rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning-foreground">
        The backend does not expose code-level dependency data. Edges here are based on shared technology tags, not on imports or package references.
      </div>

      {repos.isPending ? (
        <LoadingState rows={4} label="Loading repositories" />
      ) : repos.isError ? (
        <ErrorState error={repos.error} onRetry={() => void repos.refetch()} />
      ) : (
        <div className="grid gap-4 xl:grid-cols-3">
          <Card className="xl:col-span-2">
            <CardHeader>
              <CardTitle>Shared-tag graph</CardTitle>
              <CardDescription>Select a node to make that repository active.</CardDescription>
            </CardHeader>
            <CardContent>
              <DependencyGraph repositories={repos.data} selectedId={repository} onSelect={setRepository} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Technology usage</CardTitle>
              <CardDescription>Repositories per technology tag.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <BreakdownBars data={usage} emptyMessage="No technology tags detected" />
              <div className="flex flex-wrap gap-1">
                {(repos.data ?? []).map((repo) => (
                  <Badge key={repo.id} variant={repo.id === repository ? "default" : "outline"}>
                    {repo.name}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}
