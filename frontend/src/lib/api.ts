export const API_BASE = "/api";
export const API_KEY_STORAGE = "usai.apiKey";
const API_KEY_HEADER = "X-API-Key";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }

  get isAuthError(): boolean {
    return this.status === 401 || this.status === 403;
  }
}

/**
 * Normalizes the two error shapes the backend can return:
 * - DomainError handler: { detail: string, error: string }
 * - FastAPI validation (422): { detail: [{ loc, msg, type }] }
 * - FastAPI HTTPException: { detail: string }
 */
export function normalizeErrorDetail(status: number, body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) {
            const loc = (item as { loc?: unknown[] }).loc;
            const field = Array.isArray(loc) ? loc.filter((part) => part !== "body").join(".") : "";
            const msg = String((item as { msg: unknown }).msg);
            return field ? `${field}: ${msg}` : msg;
          }
          return String(item);
        })
        .filter(Boolean);
      if (messages.length > 0) return messages.join("; ");
    }
  }
  if (typeof body === "string" && body.trim()) return body;
  return `Request failed with status ${status}`;
}

export function getStoredApiKey(): string {
  try {
    return window.localStorage.getItem(API_KEY_STORAGE) ?? "";
  } catch {
    return "";
  }
}

export function storeApiKey(key: string): void {
  try {
    if (key) window.localStorage.setItem(API_KEY_STORAGE, key);
    else window.localStorage.removeItem(API_KEY_STORAGE);
  } catch {
    // Storage can be unavailable (private mode); the key then lasts for the session only.
  }
}

export type QueryValue = string | number | boolean | null | undefined;

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  query?: Record<string, QueryValue>;
  signal?: AbortSignal;
  apiKey?: string;
}

export function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const params = new URLSearchParams();
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null || value === "") continue;
      params.set(key, String(value));
    }
  }
  const qs = params.toString();
  return `${API_BASE}${path}${qs ? `?${qs}` : ""}`;
}

/** Encodes a repository id, name, or path for use as a `{repository:path}` route segment. */
export function repoSegment(repository: string): string {
  return encodeURIComponent(repository);
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, query, signal } = options;
  const apiKey = options.apiKey ?? getStoredApiKey();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (apiKey) headers[API_KEY_HEADER] = apiKey;

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(0, "The API is unreachable. Check that the backend is running.");
  }

  const text = await response.text();
  let parsed: unknown = undefined;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, normalizeErrorDetail(response.status, parsed));
  }
  return parsed as T;
}
