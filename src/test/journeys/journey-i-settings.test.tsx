import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SystemTelemetry from "@/pages/SystemTelemetry";
import {
  renderWithProviders,
  resetAllStores,
  setMockInvokeHandler,
  createDefaultMockHandler,
  mockAppSettings,
} from "@/test/test-utils";

describe("Journey I — System & Telemetry (Hot-Reloading & Persistence)", () => {
  beforeEach(() => {
    resetAllStores();
    setMockInvokeHandler(null);
  });

  it("renders system navigation with Provider & Runtime, Storage & Subsystems, Benchmarks, and Diagnostics tabs", () => {
    renderWithProviders(<SystemTelemetry />);

    expect(screen.getByText("System Architecture & Telemetry")).toBeInTheDocument();
    expect(screen.getByText("Provider & Runtime")).toBeInTheDocument();
    expect(screen.getByText("Storage & Subsystems")).toBeInTheDocument();
    expect(screen.getByText("Benchmarks")).toBeInTheDocument();
    expect(screen.getByText("Diagnostics")).toBeInTheDocument();
  });

  it("hot-reloads LLM inference provider and checks reachability", async () => {
    const user = userEvent.setup();
    let updatedProviderRequest: unknown = null;
    const defaultMock = createDefaultMockHandler();

    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "update_provider") {
        updatedProviderRequest = (args as { request?: unknown })?.request;
        return {
          success: true,
          provider: "ollama",
          base_url: "http://127.0.0.1:11434/v1",
          model: "qwen2.5-coder:7b",
          reachable: true,
          loaded_models: ["qwen2.5-coder:7b", "phi4-mini:q6_k"],
        };
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<SystemTelemetry />);

    // Click Save & Apply button in Provider & Runtime tab
    const applyButton = await screen.findByRole("button", { name: /Save & Apply/i });
    await user.click(applyButton);

    await waitFor(() => {
      expect(updatedProviderRequest).not.toBeNull();
      expect(screen.getByText(/Provider configured: ollama/i)).toBeInTheDocument();
    });
  });

  it("performs non-mutating model discovery on candidate endpoint", async () => {
    const user = userEvent.setup();
    let discoveryRequested = false;
    const defaultMock = createDefaultMockHandler();

    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "discover_provider") {
        discoveryRequested = true;
        return {
          success: true,
          provider: "lmstudio",
          base_url: "http://127.0.0.1:1234/v1",
          is_reachable: true,
          status: "available",
          models: [
            {
              model_id: "phi4-mini:q6_k",
              name: "phi4-mini",
              quantization: "q6_k",
              is_phi4_mini: true,
              is_q6_or_higher: true,
              warning: null,
            },
          ],
          message: "Discovered 1 model(s) from lmstudio.",
          error_details: null,
        };
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<SystemTelemetry />);

    // Click Discover button
    const discoverBtn = await screen.findByRole("button", { name: /Discover/i });
    await user.click(discoverBtn);

    await waitFor(() => {
      expect(discoveryRequested).toBe(true);
      expect(screen.getByText(/Discovered 1 model\(s\) from lmstudio/i)).toBeInTheDocument();
    });
  });

  it("configures and saves Cognee storage & database settings in Storage tab", async () => {
    const user = userEvent.setup();
    let savedCogneeSettings: unknown = null;
    const defaultMock = createDefaultMockHandler();

    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "update_cognee_settings") {
        savedCogneeSettings = (args as { request?: unknown })?.request || args;
        return mockAppSettings;
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<SystemTelemetry />);

    // Switch to Storage & Subsystems tab
    const storageTab = screen.getByRole("button", { name: /Storage & Subsystems/i });
    await user.click(storageTab);

    await waitFor(() => {
      expect(screen.getByText("Cognee Integration")).toBeInTheDocument();
    });

    // Click Save Settings button
    const saveBtn = screen.getByRole("button", { name: /Save Settings/i });
    await user.click(saveBtn);

    await waitFor(() => {
      expect(savedCogneeSettings).not.toBeNull();
    });
  });

  it("tests backend server connectivity and displays live health indicator in Diagnostics tab", async () => {
    const user = userEvent.setup();
    let healthChecked = false;
    const defaultMock = createDefaultMockHandler();

    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "health") {
        healthChecked = true;
        return {
          status: "ok",
          version: "0.1.0",
          cognee_initialized: true,
          ollama_reachable: true,
        };
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<SystemTelemetry />);

    // Switch to Diagnostics tab
    const diagTab = screen.getByRole("button", { name: /Diagnostics/i });
    await user.click(diagTab);

    const testBtn = await screen.findByRole("button", { name: /Test Connection/i });
    await user.click(testBtn);

    await waitFor(() => {
      expect(healthChecked).toBe(true);
      expect(screen.getByText(/Backend reachable & healthy/i)).toBeInTheDocument();
    });
  });
});
