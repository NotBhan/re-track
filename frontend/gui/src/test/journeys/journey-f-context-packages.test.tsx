import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PackageHistoryDrawer } from "@/components/context-packages/PackageHistoryDrawer";
import {
  renderWithProviders,
  resetAllStores,
  setMockInvokeHandler,
  createDefaultMockHandler,
  mockSavedPackages,
} from "@/test/test-utils";
import { useContextPackageStore } from "@/stores/context-package-store";
import type { SavedContextPackage } from "@/lib/api";

describe("Journey F — Context Packages History & Repository Scoping", () => {
  beforeEach(() => {
    resetAllStores();
    setMockInvokeHandler(null);
  });

  it("renders empty package state when no packages exist for the repository", async () => {
    const defaultMock = createDefaultMockHandler();
    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "list_context_packages") {
        return { success: true, packages: [], total_count: 0 };
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(
      <PackageHistoryDrawer
        activeRepoId="repo-empty"
        activeRepoName="empty-repo"
      />
    );

    await waitFor(() => {
      expect(
        screen.getByText(/No saved packages for this repository/i)
      ).toBeInTheDocument();
    });
  });

  it("renders saved packages scoped to active repository with tokens, relative time, and task", async () => {
    renderWithProviders(
      <PackageHistoryDrawer
        activeRepoId="repo-1"
        activeRepoName="test-repo"
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Context Package - Token Budgeting")).toBeInTheDocument();
    });

    expect(screen.getByText("Implement token budget pruning")).toBeInTheDocument();
    expect(screen.getByText(/~420 tokens/i)).toBeInTheDocument();
    expect(screen.getByText("test-repo")).toBeInTheDocument();
  });

  it("scopes packages strictly to active repository and excludes packages from other repos", async () => {
    const otherRepoPkg: SavedContextPackage = {
      ...mockSavedPackages[0],
      id: "pkg-other",
      name: "Other Repo Package",
      repository_id: "repo-other",
      repository_name: "other-repo",
      task: "Different task",
    };

    const defaultMock = createDefaultMockHandler();
    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "list_context_packages") {
        return {
          success: true,
          packages: [mockSavedPackages[0], otherRepoPkg],
          total_count: 2,
        };
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(
      <PackageHistoryDrawer
        activeRepoId="repo-1"
        activeRepoName="test-repo"
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Context Package - Token Budgeting")).toBeInTheDocument();
    });

    // Package from repo-other must NOT be displayed
    expect(screen.queryByText("Other Repo Package")).not.toBeInTheDocument();
  });

  it("allows selecting a package from history to load into Studio", async () => {
    const user = userEvent.setup();
    let selectedPkg: SavedContextPackage | null = null;

    renderWithProviders(
      <PackageHistoryDrawer
        activeRepoId="repo-1"
        activeRepoName="test-repo"
        onSelectPackage={(pkg) => {
          selectedPkg = pkg;
        }}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Context Package - Token Budgeting")).toBeInTheDocument();
    });

    const card = screen.getByText("Context Package - Token Budgeting").closest("div");
    if (card) {
      await user.click(card);
    }

    expect(selectedPkg).not.toBeNull();
    expect((selectedPkg as SavedContextPackage | null)?.id).toBe("pkg-1");
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
