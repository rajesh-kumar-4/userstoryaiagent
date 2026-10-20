import { useRepositories } from "@/api/hooks";
import { Select } from "@/components/ui/input";
import { useAppState } from "@/state/app-state";

/** Global repository selector. The chosen repository id is shared by every analysis page. */
export function RepoSelect() {
  const { repository, setRepository } = useAppState();
  const repos = useRepositories();
  const items = repos.data ?? [];

  // Clear a stale selection when the repository is no longer registered.
  const selectedValid = !repository || items.some((repo) => repo.id === repository);

  return (
    <div className="flex min-w-0 items-center gap-2">
      <label htmlFor="repo-select" className="hidden text-xs font-medium text-muted-foreground sm:block">
        Repository
      </label>
      <Select
        id="repo-select"
        className="h-9 max-w-xs min-w-[12rem]"
        value={selectedValid ? (repository ?? "") : ""}
        onChange={(event) => setRepository(event.target.value || null)}
        disabled={repos.isLoading || (repos.isError && items.length === 0)}
        aria-label="Select repository"
      >
        <option value="">{repos.isLoading ? "Loading repositories..." : "No repository selected"}</option>
        {items.map((repo) => (
          <option key={repo.id} value={repo.id}>
            {repo.name}
            {repo.is_dirty ? " (uncommitted changes)" : ""}
          </option>
        ))}
      </Select>
    </div>
  );
}
