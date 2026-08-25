import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import App from "@/App";
import {
  renderWithProviders,
  resetAllStores,
  setMockInvokeHandler,
  createDefaultMockHandler,
  mockHealthData,
  mockDetailedHealthData,
} from "@/test/test-utils";

describe("Journey A — First Run & Application Initialization", () => {
  beforeEach(() => {
    resetAllStores();
    setMockInvokeHandler(null); // use default healthy mock
  });

  it("launches application and renders complete navigation shell and status telemetry", async () => {
    renderWithProviders(<App />, { withRouter: false });

    // Assert main logo and navigation links
    expect(screen.getAllByText("RE:Track").length).toBeGreaterThan(0);
    expect(screen.getByText("Repositories")).toBeInTheDocument();
    expect(screen.getByText("Context Studio")).toBeInTheDocument();
    expect(screen.getByText("Context Packages")).toBeInTheDocument();
    expect(screen.getByText("Memory Graph")).toBeInTheDocument();
    expect(screen.getByText("Benchmarks")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();

    // Verify health polling populates hardware telemetry and engine status
    await waitFor(() => {
      expect(screen.getByText("Engine ready")).toBeInTheDocument();
    });
  });

  it("gracefully reflects degraded provider state when LLM is unreachable without crashing", async () => {
    const defaultMock = createDefaultMockHandler();
    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "health" || cmd === "get_health") {
        return {
          ...mockHealthData,
          status: "degraded",
          ollama_reachable: false,
          health_state: "degraded",
          engine_state: "degraded",
        };
      }
      if (cmd === "detailed_health") {
        return {
          ...mockDetailedHealthData,
          status: "degraded",
          ollama_reachable: false,
          health_state: "degraded",
          engine_state: "degraded",
        };
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<App />, { withRouter: false });

    await waitFor(() => {
      expect(screen.getByText("Engine degraded")).toBeInTheDocument();
    });
  });

  it("reflects empty repository state on first launch", async () => {
    const defaultMock = createDefaultMockHandler();
    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "list_repositories") {
        return { success: true, repositories: [], total_count: 0 };
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<App />, { withRouter: false });

    await waitFor(() => {
      expect(screen.getByText("No repositories indexed yet")).toBeInTheDocument();
    });
  });
});
