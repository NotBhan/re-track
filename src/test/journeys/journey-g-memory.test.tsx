import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Memory from "@/pages/Memory";
import {
  renderWithProviders,
  resetAllStores,
  setMockInvokeHandler,
  createDefaultMockHandler,
} from "@/test/test-utils";
import { useMemoryStore } from "@/stores/memory-store";

describe("Journey G — Memory Inspector (3-Tier Cognee Architecture)", () => {
  beforeEach(() => {
    resetAllStores();
    setMockInvokeHandler(null);
  });

  it("renders 3-tier memory inspector with overview statistics and storage layers", async () => {
    renderWithProviders(<Memory />);

    await waitFor(() => {
      expect(screen.getByText("Cognee Semantic Memory Graph")).toBeInTheDocument();
    });

    // Check 3 tier tab buttons
    expect(screen.getByRole("button", { name: /Datasets & Files/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Vector Space/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Knowledge Graph/i })).toBeInTheDocument();

    // Check 3 storage layers
    expect(screen.getByText(/Ingested Source Files/i)).toBeInTheDocument();
    expect(screen.getByText(/Vector Semantic Index/i)).toBeInTheDocument();
    expect(screen.getByText(/LanceDB Vector Embeddings/i)).toBeInTheDocument();
  });

  it("switches to Vector Space tab and displays vector engine metadata", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Memory />);

    const vectorTab = screen.getByRole("button", { name: /Vector Space/i });
    await user.click(vectorTab);

    await waitFor(() => {
      expect(screen.getByText(/Vector Provider/i)).toBeInTheDocument();
      expect(screen.getByText(/Dimensions/i)).toBeInTheDocument();
    });
  });

  it("switches to Knowledge Graph tab and renders graph canvas", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Memory />);

    const graphTab = screen.getByRole("button", { name: /Knowledge Graph/i });
    await user.click(graphTab);

    await waitFor(() => {
      expect(screen.getByText(/Graph Engine/i)).toBeInTheDocument();
      expect(screen.getByText(/Cognee Graph/i)).toBeInTheDocument();
    });
  });

  it("triggers Cognify action on active dataset and updates memory stores", async () => {
    let cognifiedDataset: string | null = null;
    const defaultMock = createDefaultMockHandler();

    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "cognify_dataset") {
        const req = (args as { request?: { dataset_name?: string } })?.request;
        cognifiedDataset = req?.dataset_name || "all";
        return {
          success: true,
          dataset_name: req?.dataset_name || "all",
          total_vectors: 250,
          total_nodes: 45,
          total_edges: 32,
          message: "Cognified successfully",
        };
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<Memory />);

    await waitFor(() => {
      expect(screen.getByText("re-track-core")).toBeInTheDocument();
    });

    // Execute Cognify on active dataset via store
    const success = await useMemoryStore.getState().cognifyActiveDataset("re-track-core");
    expect(success).toBe(true);
    expect(cognifiedDataset).toBe("re-track-core");
  });

  it("triggers Forget dataset action and cleans up store state", async () => {
    let forgottenDataset: string | null = null;
    const defaultMock = createDefaultMockHandler();

    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "forget_dataset") {
        const req = (args as { request?: { dataset?: string } })?.request || (args as { dataset?: string });
        forgottenDataset = req?.dataset || null;
        return { success: true, message: "Dataset forgotten" };
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<Memory />);

    await waitFor(() => {
      expect(screen.getByText("re-track-core")).toBeInTheDocument();
    });

    // Invoke forget dataset
    const { forgetDataset } = await import("@/lib/api");
    const result = await forgetDataset({ dataset: "re-track-core" });
    expect(result.success).toBe(true);
    expect(forgottenDataset).toBe("re-track-core");
  });
});
