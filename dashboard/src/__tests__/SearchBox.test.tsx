import { render, screen, fireEvent } from "@testing-library/react";
import { SearchBox } from "@/components/SearchBox";
import type { Post } from "@/lib/api";

const posts: Post[] = [
  {
    id: 1, x_post_id: "t1", author_handle: "a", content: "multi-agent orchestration demo",
    url: "https://x.com/t1", posted_at: "2026-03-01T00:00:00Z", fetched_at: "2026-03-01T00:01:00Z",
    relevance_score: 8, is_relevant: true, labels: ["ai-agent"], digest_sent: false,
  },
  {
    id: 2, x_post_id: "t2", author_handle: "b", content: "cooking pasta recipe",
    url: "https://x.com/t2", posted_at: "2026-03-01T00:00:00Z", fetched_at: "2026-03-01T00:01:00Z",
    relevance_score: 0, is_relevant: false, labels: ["other"], digest_sent: false,
  },
];

describe("SearchBox", () => {
  it("filters visible posts by keyword", () => {
    render(<SearchBox posts={posts} />);
    const input = screen.getByRole("searchbox");
    fireEvent.change(input, { target: { value: "multi-agent" } });
    expect(screen.getByText(/multi-agent orchestration/i)).toBeInTheDocument();
    expect(screen.queryByText(/cooking pasta/i)).not.toBeInTheDocument();
  });

  it("shows empty state when no match", () => {
    render(<SearchBox posts={posts} />);
    const input = screen.getByRole("searchbox");
    fireEvent.change(input, { target: { value: "xyz_no_match_xyz" } });
    expect(screen.getByText(/no posts match your search/i)).toBeInTheDocument();
  });
});
