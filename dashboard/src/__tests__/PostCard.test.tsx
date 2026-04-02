import { render, screen } from "@testing-library/react";
import { PostCard } from "@/components/PostCard";
import type { Post } from "@/lib/api";
import { mockPost } from "./mocks/mock-data";

const hnPost: Post = { ...mockPost };

const redditPost: Post = {
  ...mockPost,
  id: 2,
  source: "reddit",
  external_id: "r_abc",
  url: "https://www.reddit.com/r/MachineLearning/comments/r_abc/",
  points: 42,
  discussion_url: null,
};

describe("PostCard", () => {
  describe("HN post", () => {
    it('shows "View article" link pointing to original URL', () => {
      render(<PostCard post={hnPost} />);
      const link = screen.getByLabelText(/view article/i);
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute("href", hnPost.url);
    });

    it('shows "HN discussion" link pointing to discussion_url', () => {
      render(<PostCard post={hnPost} />);
      const link = screen.getByLabelText(/hn discussion/i);
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute("href", hnPost.discussion_url!);
    });

    it('does not show "View source" label', () => {
      render(<PostCard post={hnPost} />);
      expect(screen.queryByLabelText(/view source/i)).toBeNull();
    });
  });

  describe("non-HN post", () => {
    it('shows single "View source" link', () => {
      render(<PostCard post={redditPost} />);
      expect(screen.getByLabelText(/view source/i)).toBeInTheDocument();
    });

    it('does not show "HN discussion" link', () => {
      render(<PostCard post={redditPost} />);
      expect(screen.queryByLabelText(/hn discussion/i)).toBeNull();
    });
  });

  describe("points badge", () => {
    it("shows points badge when points > 0", () => {
      render(<PostCard post={hnPost} />);
      expect(screen.getByLabelText("150 points")).toBeInTheDocument();
    });

    it("hides points badge when points is 0", () => {
      render(<PostCard post={{ ...hnPost, points: 0 }} />);
      expect(screen.queryByLabelText(/points/i)).toBeNull();
    });

    it("hides points badge when points is null", () => {
      render(<PostCard post={{ ...hnPost, points: null }} />);
      expect(screen.queryByLabelText(/points/i)).toBeNull();
    });
  });
});
