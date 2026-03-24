import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { server } from "./mocks/server";
import { http, HttpResponse } from "msw";
import { DigestButton } from "@/components/DigestButton";

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("DigestButton", () => {
  it("shows success toast on trigger", async () => {
    render(<DigestButton />);
    fireEvent.click(screen.getByRole("button", { name: /send digest/i }));
    await waitFor(() => {
      expect(screen.getByText(/digest sent/i)).toBeInTheDocument();
    });
  });

  it("shows error toast on failure", async () => {
    server.use(
      http.post("http://localhost:8000/api/digest/trigger", () =>
        HttpResponse.json({ detail: "Internal error" }, { status: 500 })
      )
    );
    render(<DigestButton />);
    fireEvent.click(screen.getByRole("button", { name: /send digest/i }));
    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });
});
