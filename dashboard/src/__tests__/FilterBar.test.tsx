import { render, screen, fireEvent } from "@testing-library/react";
import { FilterBar } from "@/components/FilterBar";

describe("FilterBar", () => {
  it("toggles label chip and calls onChange", () => {
    const onChange = jest.fn();
    render(<FilterBar onChange={onChange} />);
    const chip = screen.getByRole("button", { name: /ai-agent/i });
    fireEvent.click(chip);
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ label: "ai-agent" }));
  });

  it("updates min score via slider and calls onChange", () => {
    const onChange = jest.fn();
    render(<FilterBar onChange={onChange} />);
    const slider = screen.getByRole("slider", { name: /min score/i });
    fireEvent.change(slider, { target: { value: "8" } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ min_score: 8 }));
  });

  it("clear button resets filters", () => {
    const onChange = jest.fn();
    render(<FilterBar onChange={onChange} />);
    const chip = screen.getByRole("button", { name: /ai-agent/i });
    fireEvent.click(chip);
    const clear = screen.getByRole("button", { name: /clear/i });
    fireEvent.click(clear);
    expect(onChange).toHaveBeenLastCalledWith({});
  });

  it("selects source chip and calls onChange with source param", () => {
    const onChange = jest.fn();
    render(<FilterBar onChange={onChange} />);
    const hnBtn = screen.getByRole("button", { name: /^HN$/i });
    fireEvent.click(hnBtn);
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ source: "hackernews" }));
  });

  it("selecting All source clears source filter", () => {
    const onChange = jest.fn();
    render(<FilterBar onChange={onChange} />);
    // Select HN first
    fireEvent.click(screen.getByRole("button", { name: /^HN$/i }));
    // Then select All
    fireEvent.click(screen.getByRole("button", { name: /^All$/i }));
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(lastCall.source).toBeUndefined();
  });
});
