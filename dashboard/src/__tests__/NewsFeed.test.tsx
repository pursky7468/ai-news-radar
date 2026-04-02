/**
 * NewsFeed tests using jest.mock for API isolation.
 */
import { render, screen, waitFor } from "@testing-library/react";
import { mockPost } from "./mocks/mock-data";
import { NewsFeed } from "@/components/NewsFeed";

jest.mock("@/lib/api", () => ({
  fetchNews: jest.fn(),
  triggerDigest: jest.fn(),
}));

import { fetchNews } from "@/lib/api";
const mockFetchNews = fetchNews as jest.Mock;

beforeEach(() => {
  mockFetchNews.mockResolvedValue({
    total: 1, page: 1, per_page: 20, items: [mockPost],
  });
});

afterEach(() => jest.clearAllMocks());

describe("NewsFeed", () => {
  it("renders post cards after loading", async () => {
    render(<NewsFeed />);
    await waitFor(() => {
      expect(screen.getByText(/@researcher/)).toBeInTheDocument();
    });
  });

  it("shows score badge", async () => {
    render(<NewsFeed />);
    await waitFor(() => {
      expect(screen.getByLabelText(/score 8\.5/i)).toBeInTheDocument();
    });
  });

  it("shows labels", async () => {
    render(<NewsFeed />);
    await waitFor(() => {
      expect(screen.getByText("ai-agent")).toBeInTheDocument();
    });
  });

  it("shows source badge", async () => {
    render(<NewsFeed />);
    await waitFor(() => {
      expect(screen.getByLabelText(/source hackernews/i)).toBeInTheDocument();
    });
  });

  it("renders view article link for HN post", async () => {
    render(<NewsFeed />);
    await waitFor(() => {
      expect(screen.getByLabelText(/view article/i)).toBeInTheDocument();
    });
  });

  it("shows load-more button when more pages exist", async () => {
    mockFetchNews.mockResolvedValue({
      total: 25, page: 1, per_page: 20, items: [mockPost],
    });
    render(<NewsFeed />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /load more/i })).toBeInTheDocument();
    });
  });
});
