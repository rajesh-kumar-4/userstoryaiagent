import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  apiRequest,
  buildUrl,
  getStoredApiKey,
  normalizeErrorDetail,
  repoSegment,
  storeApiKey,
} from "./api";

describe("normalizeErrorDetail", () => {
  it("returns a string detail as-is", () => {
    expect(normalizeErrorDetail(404, { detail: "Repository not found" })).toBe("Repository not found");
  });

  it("joins FastAPI validation errors and drops the body prefix", () => {
    const body = {
      detail: [
        { loc: ["body", "repo_path"], msg: "field required", type: "missing" },
        { loc: ["query", "limit"], msg: "must be positive", type: "value_error" },
      ],
    };
    expect(normalizeErrorDetail(422, body)).toBe("repo_path: field required; query.limit: must be positive");
  });

  it("falls back to a plain-text body", () => {
    expect(normalizeErrorDetail(502, "Bad gateway")).toBe("Bad gateway");
  });

  it("falls back to a status message when no detail is available", () => {
    expect(normalizeErrorDetail(500, {})).toBe("Request failed with status 500");
    expect(normalizeErrorDetail(500, "   ")).toBe("Request failed with status 500");
  });
});

describe("buildUrl", () => {
  it("prefixes the API base and skips empty query values", () => {
    expect(buildUrl("/events", { repository: "abc", event_type: null, limit: 0, filter: "" })).toBe(
      "/api/events?repository=abc&limit=0",
    );
  });

  it("omits the query string when there are no parameters", () => {
    expect(buildUrl("/health")).toBe("/api/health");
    expect(buildUrl("/health", { a: undefined })).toBe("/api/health");
  });

  it("encodes query values", () => {
    expect(buildUrl("/x", { q: "a b&c" })).toBe("/api/x?q=a+b%26c");
  });
});

describe("repoSegment", () => {
  it("encodes path separators so a repository path is a single segment", () => {
    expect(repoSegment("C:\\work\\repo one")).toBe("C%3A%5Cwork%5Crepo%20one");
  });
});

describe("API key storage", () => {
  beforeEach(() => window.localStorage.clear());

  it("round-trips a stored key", () => {
    storeApiKey("secret-key");
    expect(getStoredApiKey()).toBe("secret-key");
  });

  it("removes the key when an empty value is stored", () => {
    storeApiKey("secret-key");
    storeApiKey("");
    expect(getStoredApiKey()).toBe("");
  });
});

describe("apiRequest", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function mockFetch(response: { ok: boolean; status: number; text: string }) {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: response.ok,
      status: response.status,
      text: async () => response.text,
    });
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  it("sends the X-API-Key header and parses JSON", async () => {
    const fetchMock = mockFetch({ ok: true, status: 200, text: '{"status":"ok"}' });

    const result = await apiRequest<{ status: string }>("/health", { apiKey: "k1" });

    expect(result).toEqual({ status: "ok" });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/health");
    expect((init.headers as Record<string, string>)["X-API-Key"]).toBe("k1");
  });

  it("uses the stored key when no key is passed", async () => {
    storeApiKey("stored-key");
    const fetchMock = mockFetch({ ok: true, status: 200, text: "{}" });

    await apiRequest("/health");

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)["X-API-Key"]).toBe("stored-key");
  });

  it("serializes JSON bodies with a content type", async () => {
    const fetchMock = mockFetch({ ok: true, status: 200, text: "{}" });

    await apiRequest("/analyses", { method: "POST", body: { repo_path: "/r" } });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("POST");
    expect(init.body).toBe('{"repo_path":"/r"}');
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("throws an ApiError with the normalized detail on failure", async () => {
    mockFetch({ ok: false, status: 401, text: '{"detail":"Invalid API key"}' });

    const error = await apiRequest("/health").catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(401);
    expect((error as ApiError).detail).toBe("Invalid API key");
    expect((error as ApiError).isAuthError).toBe(true);
  });

  it("reports an unreachable API as status 0", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    const error = await apiRequest("/health").catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(0);
    expect((error as ApiError).isAuthError).toBe(false);
  });
});
