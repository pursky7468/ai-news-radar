import { render, screen, waitFor, act } from "@testing-library/react";
import { mockPost } from "./mocks/mock-data";
import { NewsFeed } from "@/components/NewsFeed";

jest.mock("@/lib/api", () => ({
  fetchNews: jest.fn(),
}));

import { fetchNews } from "@/lib/api";
const mockFetchNews = fetchNews as jest.Mock;

afterEach(() => jest.clearAllMocks());

describe("Auto-refresh", () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());

  it("shows new-posts banner when poll returns new items since last fetch", async () => {
    let callCount = 0;
    mockFetchNews.mockImplementation(({ since }: { since?: string }) => {
      callCount++;
      if (since) {
        // Poll with since= → new posts found
        return Promise.resolve({ total: 1, page: 1, per_page: 1, items: [mockPost] });
      }
      // Initial load
      return Promise.resolve({ total: 1, page: 1, per_page: 20, items: [mockPost] });
    });

    render(<NewsFeed pollIntervalMs={100} />);
    await waitFor(() => screen.getByText(/@researcher/));

    await act(async () => {
      jest.advanceTimersByTime(200);
    });

    await waitFor(() => {
      expect(screen.getByText(/new posts available/i)).toBeInTheDocument();
    });
  });

  it("does not show banner when poll returns no new posts", async () => {
    mockFetchNews.mockImplementation(({ since }: { since?: string }) => {
      if (since) {
        return Promise.resolve({ total: 0, page: 1, per_page: 1, items: [] });
      }
      return Promise.resolve({ total: 1, page: 1, per_page: 20, items: [mockPost] });
    });

    render(<NewsFeed pollIntervalMs={100} />);
    await waitFor(() => screen.getByText(/@researcher/));

    await act(async () => {
      jest.advanceTimersByTime(200);
    });

    expect(screen.queryByText(/new posts available/i)).not.toBeInTheDocument();
  });
});
