import { http, HttpResponse } from "msw";
import type { Post, PaginatedNewsResponse, DigestResult } from "@/lib/api";

const BASE = "http://localhost:8000";

export const mockPost: Post = {
  id: 1,
  x_post_id: "t1",
  author_handle: "researcher",
  content: "AI agent uses tool calling to accomplish complex tasks",
  url: "https://x.com/i/web/status/t1",
  posted_at: "2026-03-01T12:00:00Z",
  fetched_at: "2026-03-01T12:01:00Z",
  relevance_score: 8.5,
  is_relevant: true,
  labels: ["ai-agent"],
  digest_sent: false,
};

export const handlers = [
  http.get(`${BASE}/api/news`, () =>
    HttpResponse.json<PaginatedNewsResponse>({
      total: 1,
      page: 1,
      per_page: 20,
      items: [mockPost],
    })
  ),

  http.post(`${BASE}/api/digest/trigger`, () =>
    HttpResponse.json<DigestResult>({
      posts_included: 1,
      email_sent: true,
      webhook_sent: false,
    })
  ),
];
