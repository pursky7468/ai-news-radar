import { render, screen, fireEvent, act } from "@testing-library/react";
import { SearchBox } from "@/components/SearchBox";

describe("SearchBox", () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());

  it("calls onSearch after debounce delay", async () => {
    const onSearch = jest.fn();
    render(<SearchBox onSearch={onSearch} />);
    const input = screen.getByRole("searchbox");

    fireEvent.change(input, { target: { value: "multi-agent" } });
    // Should not be called immediately
    expect(onSearch).not.toHaveBeenCalledWith("multi-agent");

    await act(async () => {
      jest.advanceTimersByTime(300);
    });
    expect(onSearch).toHaveBeenCalledWith("multi-agent");
  });

  it("calls onSearch with empty string when input cleared", async () => {
    const onSearch = jest.fn();
    render(<SearchBox onSearch={onSearch} />);
    const input = screen.getByRole("searchbox");

    fireEvent.change(input, { target: { value: "foo" } });
    fireEvent.change(input, { target: { value: "" } });

    await act(async () => {
      jest.advanceTimersByTime(300);
    });
    expect(onSearch).toHaveBeenLastCalledWith("");
  });
});
