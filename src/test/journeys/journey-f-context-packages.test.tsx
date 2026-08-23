import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ContextPackages from "@/pages/ContextPackages";
import {
  renderWithProviders,
  resetAllStores,
  setMockInvokeHandler,
  createDefaultMockHandler,
  mockSavedPackages,
} from "@/test/test-utils";
import { useContextPackageStore } from "@/stores/context-package-store";
import type { SavedContextPackage } from "@/lib/api";

describe("Journey F — Context Packages Library & Comparison", () => {
  beforeEach(() => {
    resetAllStores();
    setMockInvokeHandler(null);
  });

  it("renders empty package state when no packages exist", async () => {
    const defaultMock = createDefaultMockHandler();
    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "list_context_packages") {
        return { success: true, packages: [], total_count: 0 };
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<ContextPackages />);

    await waitFor(() => {
      expect(screen.getByText(/No context packages saved yet/i)).toBeInTheDocument();
    });
  });

  it("renders saved packages catalog with metadata tokens, repository, and task", async () => {
    renderWithProviders(<ContextPackages />);

    await waitFor(() => {
      expect(screen.getByText("Context Package - Token Budgeting")).toBeInTheDocument();
    });

    expect(screen.getByText("Implement token budget pruning")).toBeInTheDocument();
    expect(screen.getByText("~420 tokens")).toBeInTheDocument();
  });

  it("filters packages by search query", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ContextPackages />);

    await waitFor(() => {
      expect(screen.getByText("Context Package - Token Budgeting")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Filter packages/i);
    await user.type(searchInput, "nonexistent-query");

    await waitFor(() => {
      expect(screen.getByText(/No matching packages/i)).toBeInTheDocument();
    });
  });

  it("selects two packages and enables comparison mode", async () => {
    const user = userEvent.setup();
    const pkg2: SavedContextPackage = {
      ...mockSavedPackages[0],
      id: "pkg-2",
      name: "Context Package - Memory Retrieval",
      task: "Optimize LanceDB vector retrieval",
      token_estimate: 310,
    };

    const defaultMock = createDefaultMockHandler();
    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "list_context_packages") {
        return { success: true, packages: [mockSavedPackages[0], pkg2], total_count: 2 };
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<ContextPackages />);

    await waitFor(() => {
      expect(screen.getByText("Context Package - Token Budgeting")).toBeInTheDocument();
      expect(screen.getByText("Context Package - Memory Retrieval")).toBeInTheDocument();
    });

    // Check compare buttons on both package cards
    const compareButtons = screen.getAllByRole("button", { name: /^Compare$/i });
    expect(compareButtons.length).toBe(2);
    await user.click(compareButtons[0]);
    await user.click(compareButtons[1]);

    // TopBar compare action button appears
    await waitFor(() => {
      expect(screen.getByText("2 Packages")).toBeInTheDocument();
    });
  });

  it("deletes a saved package from store", async () => {
    let deletedPkgId: string | null = null;
    const defaultMock = createDefaultMockHandler();

    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "delete_context_package") {
        deletedPkgId = (args as { packageId: string })?.packageId;
        return { success: true };
      }
      return defaultMock(cmd, args);
    });

    useContextPackageStore.setState({ packages: mockSavedPackages });
    expect(useContextPackageStore.getState().packages.length).toBe(1);

    await useContextPackageStore.getState().removePackage("pkg-1");

    expect(deletedPkgId).toBe("pkg-1");
    expect(useContextPackageStore.getState().packages.length).toBe(0);
  });
});
