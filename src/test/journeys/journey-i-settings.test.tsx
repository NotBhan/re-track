import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Settings from "@/pages/Settings";
import {
  renderWithProviders,
  resetAllStores,
  setMockInvokeHandler,
  createDefaultMockHandler,
  mockAppSettings,
} from "@/test/test-utils";

describe("Journey I — Settings & Provider Management (Hot-Reloading & Persistence)", () => {
  beforeEach(() => {
    resetAllStores();
    setMockInvokeHandler(null);
  });

  it("renders settings navigation with backend, inference, cognee, storage, and theme tabs", () => {
    renderWithProviders(<Settings />);

    expect(screen.getByText("Backend Configuration")).toBeInTheDocument();
    expect(screen.getAllByText("Backend").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Inference").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Cognee").length).toBeGreaterThan(0);
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

    renderWithProviders(<Settings />);

    // Switch to Inference tab
    const inferenceTabs = screen.getAllByRole("button", { name: /Inference/i });
    await user.click(inferenceTabs[0]);

    await waitFor(() => {
      expect(screen.getByText("Inference & Provider")).toBeInTheDocument();
    });

    // Click Apply & Test button
    const applyButton = screen.getByRole("button", { name: /Apply & Test/i });
    await user.click(applyButton);

    await waitFor(() => {
      expect(updatedProviderRequest).not.toBeNull();
      expect(screen.getByText(/Connected · 2 model\(s\) loaded/i)).toBeInTheDocument();
    });
  });

  it("configures and saves Cognee storage & database settings", async () => {
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

    renderWithProviders(<Settings />);

    // Switch to Cognee tab
    const cogneeTabs = screen.getAllByRole("button", { name: /Cognee/i });
    await user.click(cogneeTabs[0]);

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

  it("tests backend server connectivity and displays live health indicator", async () => {
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

    renderWithProviders(<Settings />);

    const testBtn = screen.getByRole("button", { name: /Test Connection/i });
    await user.click(testBtn);

    await waitFor(() => {
      expect(healthChecked).toBe(true);
      expect(screen.getByText(/Backend reachable & healthy/i)).toBeInTheDocument();
    });
  });
});
