import { render, screen, waitFor, act } from "@testing-library/react";
import { server } from "./mocks/server";
import { http, HttpResponse } from "msw";
import { mockPost } from "./mocks/handlers";
import type { Post } from "@/lib/api";
import { NewsFeed } from "@/components/NewsFeed";

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("Auto-refresh", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });
  afterEach(() => {
    jest.useRealTimers();
  });

  it("shows new-posts banner when poll returns new items", async () => {
    const newPost: Post = {
      ...mockPost,
      id: 99,
      x_post_id: "t99",
      content: "brand new AI agent post",
    };

    let callCount = 0;
    server.use(
      http.get("http://localhost:8000/api/news", () => {
        callCount++;
        if (callCount === 1) {
          return HttpResponse.json({ total: 1, page: 1, per_page: 20, items: [mockPost] });
        }
        return HttpResponse.json({ total: 2, page: 1, per_page: 20, items: [newPost, mockPost] });
      })
    );

    render(<NewsFeed pollIntervalMs={100} />);
    // Wait for initial load
    await waitFor(() => screen.getByText(/@researcher/));

    // Advance time past poll interval
    await act(async () => {
      jest.advanceTimersByTime(200);
    });

    await waitFor(() => {
      expect(screen.getByText(/new posts available/i)).toBeInTheDocument();
    });
  });

  it("does not show banner when no new posts", async () => {
    render(<NewsFeed pollIntervalMs={100} />);
    await waitFor(() => screen.getByText(/@researcher/));
    await act(async () => {
      jest.advanceTimersByTime(200);
    });
    expect(screen.queryByText(/new posts available/i)).not.toBeInTheDocument();
  });
});
