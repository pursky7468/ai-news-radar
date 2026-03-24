/**
 * NewsFeed tests — RED first, then GREEN with implementation.
 */
import { render, screen, waitFor } from "@testing-library/react";
import { server } from "./mocks/server";
import { http, HttpResponse } from "msw";
import { mockPost } from "./mocks/handlers";
import { NewsFeed } from "@/components/NewsFeed";

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

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

  it("renders X link", async () => {
    render(<NewsFeed />);
    await waitFor(() => {
      expect(screen.getByLabelText(/view on x/i)).toBeInTheDocument();
    });
  });

  it("shows load-more button when more pages exist", async () => {
    server.use(
      http.get("http://localhost:8000/api/news", () =>
        HttpResponse.json({ total: 25, page: 1, per_page: 20, items: [mockPost] })
      )
    );
    render(<NewsFeed />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /load more/i })).toBeInTheDocument();
    });
  });
});
