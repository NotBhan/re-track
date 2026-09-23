import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Benchmarks from "@/pages/Benchmarks";
import {
  renderWithProviders,
  resetAllStores,
  setMockInvokeHandler,
  createDefaultMockHandler,
  mockBenchmarkResponse,
} from "@/test/test-utils";

describe("Journey H — Benchmark Suite (Deterministic Regression & Metric Verification)", () => {
  beforeEach(() => {
    resetAllStores();
    setMockInvokeHandler(null);
  });

  it("renders empty benchmark state prior to execution", () => {
    renderWithProviders(<Benchmarks />);

    expect(screen.getByText("Deterministic Context & Latency Benchmarks")).toBeInTheDocument();
    expect(screen.getByText("No Benchmark Run Recorded")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Execute Benchmarks Now/i })).toBeInTheDocument();
  });

  it("executes benchmark suite and displays KPI metrics, token reduction comparison, and query table", async () => {
    const user = userEvent.setup();
    let benchmarkInvoked = false;
    const defaultMock = createDefaultMockHandler();

    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "run_benchmark") {
        benchmarkInvoked = true;
        return mockBenchmarkResponse;
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<Benchmarks />);

    const runButton = screen.getByRole("button", { name: /Execute Benchmarks Now/i });
    await user.click(runButton);

    await waitFor(() => {
      expect(benchmarkInvoked).toBe(true);
    });

    // Check KPI metrics
    await waitFor(() => {
      expect(screen.getByText("Token Savings")).toBeInTheDocument();
      expect(screen.getByText("94.2")).toBeInTheDocument();
      expect(screen.getByText("Compression Ratio")).toBeInTheDocument();
      expect(screen.getByText("Retrieval Latency")).toBeInTheDocument();
      expect(screen.getByText("Total Pipeline Latency")).toBeInTheDocument();
    });

    // Check Token Budget Comparison bar
    expect(screen.getByText(/Token Budget Comparison/i)).toBeInTheDocument();
    expect(screen.getByText(/~25,000 tokens/i)).toBeInTheDocument();
    expect(screen.getByText(/~380 tokens/i)).toBeInTheDocument();

    // Check queries evaluation table
    expect(screen.getByText("Evaluation Suite Queries")).toBeInTheDocument();
    expect(screen.getByText("How does the AST call graph extract module dependencies?")).toBeInTheDocument();
  });

  it("handles benchmark execution failure with error notice", async () => {
    const user = userEvent.setup();
    const defaultMock = createDefaultMockHandler();

    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "run_benchmark") {
        throw new Error("Benchmark worker timeout (Ollama inference error)");
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<Benchmarks />);

    const runButton = screen.getByRole("button", { name: /Execute Benchmarks Now/i });
    await user.click(runButton);

    await waitFor(() => {
      expect(screen.getByText(/Benchmark worker timeout/i)).toBeInTheDocument();
    });
  });
});
