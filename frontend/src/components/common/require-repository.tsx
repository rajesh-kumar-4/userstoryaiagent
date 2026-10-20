import type { ReactNode } from "react";
import { useSelectedRepository } from "@/api/use-selected-repository";
import { ErrorState, LoadingState, NeedsRepository } from "@/components/common/states";
import type { RepositoryInfo } from "@/lib/types";

/**
 * Renders `children` only when a repository is selected and its detail has loaded.
 * Pass a component element that uses hooks, so the page body stays hook-safe.
 */
export function RequireRepository({ children }: { children: (repo: RepositoryInfo) => ReactNode }) {
  const { id, repo, query } = useSelectedRepository();
  if (!id) return <NeedsRepository />;
  if (query.isPending) return <LoadingState label="Loading repository" />;
  if (query.isError) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  if (!repo) return <NeedsRepository />;
  return <>{children(repo)}</>;
}
