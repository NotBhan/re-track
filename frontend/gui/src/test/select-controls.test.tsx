import { describe, it, expect, beforeEach } from "vitest";
import { useState } from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Select } from "../components/Select";

const OPTIONS = [
  { value: "alpha", label: "alpha-service", hint: "12 files · indexed" },
  { value: "beta", label: "beta-service", hint: "30 files · registered" },
  { value: "gamma", label: "gamma-service", hint: "4 files · error", disabled: true },
];

function Harness({ initial = "alpha" }: { initial?: string }) {
  const [value, setValue] = useState(initial);
  const [changes, setChanges] = useState<string[]>([]);
  return (
    <div>
      <Select
        value={value}
        onChange={(next) => {
          setValue(next);
          setChanges((prev) => [...prev, next]);
        }}
        options={OPTIONS}
        ariaLabel="Test select"
      />
      <span data-testid="value">{value}</span>
      <span data-testid="change-count">{changes.length}</span>
    </div>
  );
}

describe("Select control — design-guide listbox behaviour", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/");
  });

  it("renders the selected option and starts closed", () => {
    render(<Harness />);

    const trigger = screen.getByRole("combobox", { name: "Test select" });
    expect(trigger).toHaveTextContent("alpha-service");
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("opens a listbox with options and reflects the active selection", () => {
    render(<Harness />);

    fireEvent.click(screen.getByRole("combobox", { name: "Test select" }));

    const listbox = screen.getByRole("listbox", { name: "Test select" });
    expect(listbox).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Test select" })).toHaveAttribute(
      "aria-expanded",
      "true"
    );

    const options = screen.getAllByRole("option");
    expect(options).toHaveLength(3);
    expect(options[0]).toHaveAttribute("aria-selected", "true");
    expect(options[1]).toHaveAttribute("aria-selected", "false");
    expect(options[2]).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("option", { name: /beta-service/ })).toHaveTextContent("30 files");
  });

  it("commits the clicked option and closes the menu", async () => {
    render(<Harness />);

    fireEvent.click(screen.getByRole("combobox", { name: "Test select" }));
    fireEvent.click(screen.getByRole("option", { name: /beta-service/ }));

    expect(screen.getByTestId("value")).toHaveTextContent("beta");
    expect(screen.getByTestId("change-count")).toHaveTextContent("1");
    await waitFor(() => {
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });
  });

  it("ignores disabled options", () => {
    render(<Harness />);

    fireEvent.click(screen.getByRole("combobox", { name: "Test select" }));
    fireEvent.click(screen.getByRole("option", { name: /gamma-service/ }));

    expect(screen.getByTestId("value")).toHaveTextContent("alpha");
    expect(screen.getByTestId("change-count")).toHaveTextContent("0");
    expect(screen.getByRole("listbox")).toBeInTheDocument();
  });

  it("supports keyboard-only selection with arrow keys and Enter", async () => {
    render(<Harness />);

    const trigger = screen.getByRole("combobox", { name: "Test select" });
    trigger.focus();
    fireEvent.keyDown(trigger, { key: "ArrowDown" });

    const listbox = await screen.findByRole("listbox", { name: "Test select" });
    expect(listbox).toHaveFocus();

    fireEvent.keyDown(listbox, { key: "ArrowDown" });
    fireEvent.keyDown(listbox, { key: "Enter" });

    expect(screen.getByTestId("value")).toHaveTextContent("beta");
    await waitFor(() => {
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });
    expect(trigger).toHaveFocus();
  });

  it("closes on Escape without changing the value and restores trigger focus", async () => {
    render(<Harness />);

    const trigger = screen.getByRole("combobox", { name: "Test select" });
    fireEvent.click(trigger);

    const listbox = await screen.findByRole("listbox", { name: "Test select" });
    fireEvent.keyDown(listbox, { key: "ArrowDown" });
    fireEvent.keyDown(listbox, { key: "Escape" });

    expect(screen.getByTestId("value")).toHaveTextContent("alpha");
    expect(screen.getByTestId("change-count")).toHaveTextContent("0");
    await waitFor(() => {
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });
    expect(trigger).toHaveFocus();
  });

  it("closes when a pointer press lands outside the control", async () => {
    render(<Harness />);

    fireEvent.click(screen.getByRole("combobox", { name: "Test select" }));
    expect(screen.getByRole("listbox")).toBeInTheDocument();

    fireEvent.mouseDown(document.body);

    await waitFor(() => {
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });
  });

  it("does not open when disabled and exposes its disabled state", () => {
    render(
      <Select
        value="alpha"
        onChange={() => {}}
        options={OPTIONS}
        disabled
        ariaLabel="Disabled select"
      />
    );

    const trigger = screen.getByRole("combobox", { name: "Disabled select" });
    expect(trigger).toHaveAttribute("aria-disabled", "true");
    fireEvent.click(trigger);
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("falls back to the placeholder when the value is not among the options", () => {
    render(
      <Select
        value=""
        onChange={() => {}}
        options={OPTIONS}
        placeholder="No options selected"
        ariaLabel="Empty select"
      />
    );

    expect(screen.getByRole("combobox", { name: "Empty select" })).toHaveTextContent(
      "No options selected"
    );
  });
});
