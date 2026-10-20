import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getStoredApiKey, storeApiKey } from "@/lib/api";

export type Theme = "dark" | "light";

const THEME_STORAGE = "usai.theme";
const LIVE_STORAGE = "usai.live";
const REPO_STORAGE = "usai.repository";

interface AppState {
  apiKey: string;
  setApiKey: (key: string) => void;
  theme: Theme;
  toggleTheme: () => void;
  live: boolean;
  setLive: (live: boolean) => void;
  repository: string | null;
  setRepository: (repository: string | null) => void;
}

const AppStateContext = createContext<AppState | null>(null);

function readStorage(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key: string, value: string | null): void {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    // Ignore storage failures; state still lives in memory.
  }
}

function initialTheme(): Theme {
  const stored = readStorage(THEME_STORAGE);
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function AppStateProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [apiKey, setApiKeyState] = useState<string>(() => getStoredApiKey());
  const [theme, setTheme] = useState<Theme>(() => initialTheme());
  const [live, setLiveState] = useState<boolean>(() => readStorage(LIVE_STORAGE) !== "off");
  const [repository, setRepositoryState] = useState<string | null>(() => readStorage(REPO_STORAGE));

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    root.style.colorScheme = theme;
    writeStorage(THEME_STORAGE, theme);
  }, [theme]);

  const setApiKey = useCallback(
    (key: string) => {
      const trimmed = key.trim();
      storeApiKey(trimmed);
      setApiKeyState(trimmed);
      // Cached data was fetched with the previous identity; drop it.
      queryClient.removeQueries();
    },
    [queryClient],
  );

  const toggleTheme = useCallback(() => setTheme((current) => (current === "dark" ? "light" : "dark")), []);

  const setLive = useCallback((value: boolean) => {
    writeStorage(LIVE_STORAGE, value ? "on" : "off");
    setLiveState(value);
  }, []);

  const setRepository = useCallback((value: string | null) => {
    writeStorage(REPO_STORAGE, value);
    setRepositoryState(value);
  }, []);

  const value = useMemo<AppState>(
    () => ({ apiKey, setApiKey, theme, toggleTheme, live, setLive, repository, setRepository }),
    [apiKey, setApiKey, theme, toggleTheme, live, setLive, repository, setRepository],
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState(): AppState {
  const context = useContext(AppStateContext);
  if (!context) throw new Error("useAppState must be used inside AppStateProvider");
  return context;
}

/** Polling interval used by real-time views. The backend has no push channel, so polling is used. */
export const LIVE_POLL_MS = 15_000;
