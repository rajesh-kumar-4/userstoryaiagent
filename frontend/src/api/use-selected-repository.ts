import { useRepository } from "@/api/hooks";
import { useAppState } from "@/state/app-state";

/**
 * Resolves the globally selected repository. Analysis endpoints need the filesystem path,
 * so the detail record is fetched as well.
 */
export function useSelectedRepository() {
  const { repository } = useAppState();
  const query = useRepository(repository);
  return {
    id: repository,
    repo: query.data ?? null,
    query,
  };
}
