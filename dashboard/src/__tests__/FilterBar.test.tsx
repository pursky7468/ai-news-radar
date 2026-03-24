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
});
