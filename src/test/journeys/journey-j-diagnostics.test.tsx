import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DiagnosticsSettings } from "@/components/settings/DiagnosticsSettings";
import {
  renderWithProviders,
  resetAllStores,
  setMockInvokeHandler,
  createDefaultMockHandler,
} from "@/test/test-utils";
import type { DetailedHealthResponse } from "@/lib/api";

const mockDetailedHealthResponse: DetailedHealthResponse = {
  status: "ok",
  version: "0.1.0",
  health_state: "healthy",
  storage_canonical_exists: true,
  storage_canonical_writable: true,
  legacy_storage_detected: false,
  repository_count: 3,
  context_package_count: 5,
  cache_files_count: 12,
  cache_total_bytes: 45000,
  concurrency_queue_depth: 0,
  concurrency_queue_capacity: 5,
  concurrency_available_slots: 2,
  mcp_server_ready: true,
  active_model: "qwen2.5-coder:7b",
  ollama_reachable: true,
  cognee_initialized: true,
  diagnostics_log_entries: [
    {
      level: "INFO",
      logger: "app.context_engine",
      message: "AST topology extraction initialized for repo-1",
      timestamp: "2026-08-23T12:00:00Z",
    },
    {
      level: "WARNING",
      logger: "app.mcp",
      message: "Slow client keepalive packet received",
      timestamp: "2026-08-23T12:01:00Z",
    },
  ],
};

describe("Journey J — System Diagnostics, Telemetry & Export (Production Hardening)", () => {
  beforeEach(() => {
    resetAllStores();
    setMockInvokeHandler(null);
  });

  it("renders system health telemetry, concurrency queue, and storage status", async () => {
    const defaultMock = createDefaultMockHandler();
    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "detailed_health") {
        return mockDetailedHealthResponse;
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<DiagnosticsSettings />);

    await waitFor(() => {
      expect(screen.getByText("Operational Diagnostics & Health")).toBeInTheDocument();
    });

    // Check system health cards
    expect(screen.getByText("HEALTHY")).toBeInTheDocument();
    expect(screen.getByText("System State")).toBeInTheDocument();
    expect(screen.getByText("Concurrency Queue")).toBeInTheDocument();
    expect(screen.getByText("Storage Health")).toBeInTheDocument();
    expect(screen.getByText("Online & Reachable")).toBeInTheDocument();
  });

  it("filters diagnostics log entries with search input", async () => {
    const user = userEvent.setup();
    const defaultMock = createDefaultMockHandler();
    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "detailed_health") {
        return mockDetailedHealthResponse;
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<DiagnosticsSettings />);

    await waitFor(() => {
      expect(screen.getByText(/AST topology extraction initialized/i)).toBeInTheDocument();
      expect(screen.getByText(/Slow client keepalive packet received/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Filter log events/i);
    await user.type(searchInput, "Slow client");

    await waitFor(() => {
      expect(screen.getByText(/Slow client keepalive packet received/i)).toBeInTheDocument();
      expect(screen.queryByText(/AST topology extraction initialized/i)).not.toBeInTheDocument();
    });
  });

  it("exports sanitized diagnostics bundle and displays export file location", async () => {
    const user = userEvent.setup();
    let exportCalled = false;
    const defaultMock = createDefaultMockHandler();

    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "detailed_health") {
        return mockDetailedHealthResponse;
      }
      if (cmd === "export_diagnostics") {
        exportCalled = true;
        return {
          status: "ok",
          export_path: "/home/user/.retrack/diagnostics/retrack-diag-20260823.json",
        };
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<DiagnosticsSettings />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Export Bundle/i })).toBeInTheDocument();
    });

    const exportBtn = screen.getByRole("button", { name: /Export Bundle/i });
    await user.click(exportBtn);

    await waitFor(() => {
      expect(exportCalled).toBe(true);
      expect(screen.getByText("Diagnostic Bundle Exported Successfully")).toBeInTheDocument();
      expect(screen.getByText("/home/user/.retrack/diagnostics/retrack-diag-20260823.json")).toBeInTheDocument();
    });
  });
});
