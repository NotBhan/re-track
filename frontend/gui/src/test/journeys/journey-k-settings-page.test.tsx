import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "@/App";
import Settings from "@/pages/Settings";
import {
  renderWithProviders,
  resetAllStores,
  setMockInvokeHandler,
  createDefaultMockHandler,
  mockAppSettings,
} from "@/test/test-utils";

describe("Journey K — Settings as a dedicated first-class page", () => {
  beforeEach(() => {
    resetAllStores();
    setMockInvokeHandler(null);
  });

  it("renders the dedicated Settings route using the current in-page section pattern", async () => {
    window.history.pushState({}, "", "/settings");

    renderWithProviders(<App />, { withRouter: false });

    await waitFor(() => {
      expect(window.location.pathname).toBe("/settings");
    });

    // Page chrome from the shared TopBar, not a nested settings sidebar.
    expect(
      screen.getByRole("heading", { name: /RE:Track \| Settings/i })
    ).toBeInTheDocument();

    // Exactly the supported sections are exposed.
    expect(screen.getByRole("button", { name: /Provider & Runtime/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Storage & Memory/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Diagnostics/i })).toBeInTheDocument();

    // The retired legacy presentation must not reappear.
    expect(screen.queryByText("Appearance & Theme")).not.toBeInTheDocument();
    expect(screen.queryByText("About RE:Track")).not.toBeInTheDocument();
    expect(screen.queryByText("Host URL")).not.toBeInTheDocument();
    expect(screen.queryByText("Configuration")).not.toBeInTheDocument();
  });

  it("is reachable from the primary application navigation", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/workspace");

    renderWithProviders(<App />, { withRouter: false });

    const settingsLink = await screen.findByRole("link", { name: /Settings/i });
    await user.click(settingsLink);

    await waitFor(
      () => {
        expect(window.location.pathname).toBe("/settings");
        expect(
          screen.getByRole("heading", { name: /RE:Track \| Settings/i })
        ).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it("preserves provider configuration behaviour (hot-reload apply)", async () => {
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
          loaded_models: ["qwen2.5-coder:7b"],
        };
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<Settings />, { initialEntries: ["/settings"] });

    const applyButton = await screen.findByRole("button", { name: /Save & Apply/i });
    await user.click(applyButton);

    await waitFor(() => {
      expect(updatedProviderRequest).not.toBeNull();
      expect(screen.getByText(/Provider configured: ollama/i)).toBeInTheDocument();
    });
  });

  it("preserves storage & memory configuration behaviour (cognee persistence)", async () => {
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

    renderWithProviders(<Settings />, { initialEntries: ["/settings?tab=storage"] });

    await waitFor(() => {
      expect(screen.getByText("Cognee Integration")).toBeInTheDocument();
    });
    expect(screen.getByText("Storage & Cache")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Save Settings/i }));

    await waitFor(() => {
      expect(savedCogneeSettings).not.toBeNull();
    });
  });

  it("preserves diagnostics and backend connectivity checks", async () => {
    const user = userEvent.setup();
    let healthChecks = 0;
    const defaultMock = createDefaultMockHandler();

    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "health") {
        healthChecks += 1;
        return {
          status: "ok",
          version: "0.1.0",
          cognee_initialized: true,
          ollama_reachable: true,
        };
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<Settings />, { initialEntries: ["/settings?tab=diagnostics"] });

    await waitFor(() => {
      expect(screen.getByText(/Operational Diagnostics/i)).toBeInTheDocument();
    });

    const testButton = await screen.findByRole("button", { name: /Test Connection/i });
    await user.click(testButton);

    await waitFor(() => {
      expect(healthChecks).toBeGreaterThan(0);
      expect(screen.getByText(/Backend reachable & healthy/i)).toBeInTheDocument();
    });
  });

  it("supports URL deep links and resolves retired tab identifiers", async () => {
    const first = renderWithProviders(<Settings />, {
      initialEntries: ["/settings?tab=storage"],
    });
    expect(await screen.findByText("Cognee Integration")).toBeInTheDocument();
    first.unmount();

    renderWithProviders(<Settings />, { initialEntries: ["/settings?tab=ollama"] });
    expect(await screen.findByRole("button", { name: /Save & Apply/i })).toBeInTheDocument();
  });

  it("does not break existing routes", async () => {
    window.history.pushState({}, "", "/benchmarks");
    const legacy = renderWithProviders(<App />, { withRouter: false });

    await waitFor(() => {
      expect(window.location.pathname).toBe("/system");
      expect(window.location.search).toContain("tab=benchmarks");
    });
    legacy.unmount();

    window.history.pushState({}, "", "/memory");
    renderWithProviders(<App />, { withRouter: false });

    await waitFor(() => {
      expect(window.location.pathname).toBe("/memory");
    });
    expect(screen.getByText("Repository Required")).toBeInTheDocument();
  });
});
