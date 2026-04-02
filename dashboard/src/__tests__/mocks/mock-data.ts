import type { Post } from "@/lib/api";

export const mockPost: Post = {
  id: 1,
  source: "hackernews",
  external_id: "t1",
  author_handle: "researcher",
  content: "AI agent uses tool calling to accomplish complex tasks",
  url: "https://example.com/ai-agent-article",
  posted_at: "2026-03-01T12:00:00Z",
  fetched_at: "2026-03-01T12:01:00Z",
  relevance_score: 8.5,
  points: 150,
  is_relevant: true,
  labels: ["ai-agent"],
  digest_sent: false,
  discussion_url: "https://news.ycombinator.com/item?id=t1",
};
