import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { DigestButton } from "@/components/DigestButton";

jest.mock("@/lib/api", () => ({
  triggerDigest: jest.fn(),
}));

import { triggerDigest } from "@/lib/api";
const mockTriggerDigest = triggerDigest as jest.Mock;

afterEach(() => jest.clearAllMocks());

describe("DigestButton", () => {
  it("shows success toast on trigger", async () => {
    mockTriggerDigest.mockResolvedValue({ posts_included: 1, email_sent: true, webhook_sent: false });
    render(<DigestButton />);
    fireEvent.click(screen.getByRole("button", { name: /send digest/i }));
    await waitFor(() => {
      expect(screen.getByText(/digest sent/i)).toBeInTheDocument();
    });
  });

  it("shows error toast on failure", async () => {
    mockTriggerDigest.mockRejectedValue(new Error("API error 500"));
    render(<DigestButton />);
    fireEvent.click(screen.getByRole("button", { name: /send digest/i }));
    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });
});
