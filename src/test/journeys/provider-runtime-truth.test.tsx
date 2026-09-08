import { describe, it, expect, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { TopBar } from "@/components/layout/TopBar";
import { useHealthStore } from "@/stores/health-store";
import {
  renderWithProviders,
  resetAllStores,
  setMockInvokeHandler,
  createDefaultMockHandler,
  mockBackendStatus,
  mockHealthData,
} from "@/test/test-utils";

describe("Provider Runtime Truth & TopBar Active Model Invariants", () => {
  beforeEach(() => {
    resetAllStores();
    setMockInvokeHandler(null);
  });

  it("topbar_state_matches_backend_status when active model is verified", async () => {
    useHealthStore.setState({
      backendOnline: true,
      providerIdentity: "lmstudio",
      providerReachable: true,
      activeModel: "microsoft/phi-4-mini-reasoning",
      configuredModel: "microsoft/phi-4-mini-reasoning",
      activeModelState: "active",
      engineState: "healthy",
    });

    renderWithProviders(<TopBar title="Test Workspace" />);

    expect(screen.getByText("microsoft/phi-4-mini-reasoning")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
  });

  it("no_frontend_model_fallback_is_present: does not fall back to configured model when active model is unverified", async () => {
    // Configured model is qwen2.5-coder:7b, but unverified (activeModel is null, engine is degraded)
    useHealthStore.setState({
      backendOnline: true,
      providerIdentity: "lmstudio",
      providerReachable: true,
      activeModel: null,
      configuredModel: "qwen2.5-coder:7b",
      activeModelState: "model_not_found",
      engineState: "degraded",
    });

    renderWithProviders(<TopBar title="Test Workspace" />);

    // TopBar MUST NOT display qwen2.5-coder
    expect(screen.queryByText("qwen2.5-coder")).not.toBeInTheDocument();
    expect(screen.getByText("No active model")).toBeInTheDocument();
    expect(screen.getByText("Degraded")).toBeInTheDocument();
  });

  it("repository_switch_does_not_reset_provider state in health store", async () => {
    const defaultMock = createDefaultMockHandler();
    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "health") {
        return {
          ...mockHealthData,
          provider_identity: "lmstudio",
          provider_reachable: true,
          active_model: "microsoft/phi-4-mini-reasoning",
          configured_model: "microsoft/phi-4-mini-reasoning",
          engine_state: "healthy",
        };
      }
      if (cmd === "get_backend_status") {
        return {
          ...mockBackendStatus,
          llm_provider: "lmstudio",
          provider_identity: "lmstudio",
          provider_reachable: true,
          active_model: "microsoft/phi-4-mini-reasoning",
          configured_model: "microsoft/phi-4-mini-reasoning",
          engine_state: "healthy",
        };
      }
      return defaultMock(cmd, args);
    });

    // Initial poll
    await useHealthStore.getState().pollHealth();

    expect(useHealthStore.getState().providerIdentity).toBe("lmstudio");
    expect(useHealthStore.getState().activeModel).toBe("microsoft/phi-4-mini-reasoning");

    // Simulate repository switch and subsequent health poll
    await useHealthStore.getState().pollHealth();

    expect(useHealthStore.getState().providerIdentity).toBe("lmstudio");
    expect(useHealthStore.getState().activeModel).toBe("microsoft/phi-4-mini-reasoning");
    expect(useHealthStore.getState().configuredModel).toBe("microsoft/phi-4-mini-reasoning");
  });

  it("settings_ui_displays_model_unavailable_when_configured_model_differs_from_active_model", async () => {
    const defaultMock = createDefaultMockHandler();
    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "get_provider_status") {
        return {
          success: true,
          provider: "lmstudio",
          base_url: "http://127.0.0.1:1234/v1",
          active_model: null,
          is_reachable: true,
          health_state: "degraded",
          discovery_status: "available",
          loaded_models: [
            {
              model_id: "microsoft/phi-4-mini-reasoning",
              name: "phi-4-mini",
              quantization: "unknown",
              is_phi4_mini: true,
              is_q6_or_higher: false,
              warning: null,
            },
          ],
          quantization_warning: null,
          api_key_configured: false,
          api_key_masked: "local",
        };
      }
      if (cmd === "get_settings") {
        return {
          ...mockBackendStatus,
          llm_provider: "lmstudio",
          llm_model: "qwen2.5-coder:7b",
        };
      }
      return defaultMock(cmd, args);
    });

    const { OllamaSettings } = await import("@/components/settings/OllamaSettings");
    renderWithProviders(<OllamaSettings />);

    // Label must say Configured Model, not Active Model
    expect(await screen.findByText("Configured Model")).toBeInTheDocument();

    // Warning banner must be present
    expect(await screen.findByTestId("model-unavailable-warning")).toBeInTheDocument();
    expect(screen.getByText("Configured Model Unavailable")).toBeInTheDocument();
    expect(screen.queryByText(/Verified active model:/)).not.toBeInTheDocument();
  });

  it("settings_ui_displays_verified_active_model_when_configured_model_matches_active_model", async () => {
    const defaultMock = createDefaultMockHandler();
    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "get_provider_status") {
        return {
          success: true,
          provider: "lmstudio",
          base_url: "http://127.0.0.1:1234/v1",
          active_model: "microsoft/phi-4-mini-reasoning",
          is_reachable: true,
          health_state: "healthy",
          discovery_status: "available",
          loaded_models: [
            {
              model_id: "microsoft/phi-4-mini-reasoning",
              name: "phi-4-mini",
              quantization: "unknown",
              is_phi4_mini: true,
              is_q6_or_higher: false,
              warning: null,
            },
          ],
          quantization_warning: null,
          api_key_configured: false,
          api_key_masked: "local",
        };
      }
      if (cmd === "get_settings") {
        return {
          ...mockBackendStatus,
          llm_provider: "lmstudio",
          llm_model: "microsoft/phi-4-mini-reasoning",
        };
      }
      return defaultMock(cmd, args);
    });

    const { OllamaSettings } = await import("@/components/settings/OllamaSettings");
    renderWithProviders(<OllamaSettings />);

    expect(await screen.findByText("Configured Model")).toBeInTheDocument();
    expect(await screen.findByText("Verified active model: microsoft/phi-4-mini-reasoning")).toBeInTheDocument();
    expect(screen.queryByTestId("model-unavailable-warning")).not.toBeInTheDocument();
  });
});
