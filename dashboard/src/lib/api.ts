/**
 * API client — injects X-API-Key header on every request.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

export interface Post {
  id: number;
  x_post_id: string;
  author_handle: string;
  content: string;
  url: string;
  posted_at: string;
  fetched_at: string;
  relevance_score: number | null;
  is_relevant: boolean;
  labels: string[];
  digest_sent: boolean;
}

export interface PaginatedNewsResponse {
  total: number;
  page: number;
  per_page: number;
  items: Post[];
}

export interface DigestResult {
  posts_included: number;
  email_sent: boolean;
  webhook_sent: boolean;
}

export interface NewsQueryParams {
  label?: string;
  min_score?: number;
  q?: string;
  page?: number;
  per_page?: number;
  sort?: "date_desc" | "score_desc";
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
      ...init.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export function fetchNews(params: NewsQueryParams = {}): Promise<PaginatedNewsResponse> {
  const qs = new URLSearchParams();
  if (params.label) qs.set("label", params.label);
  if (params.min_score !== undefined) qs.set("min_score", String(params.min_score));
  if (params.q) qs.set("q", params.q);
  if (params.page) qs.set("page", String(params.page));
  if (params.per_page) qs.set("per_page", String(params.per_page));
  if (params.sort) qs.set("sort", params.sort);
  return apiFetch<PaginatedNewsResponse>(`/api/news?${qs}`);
}

export function triggerDigest(): Promise<DigestResult> {
  return apiFetch<DigestResult>("/api/digest/trigger", { method: "POST" });
}
