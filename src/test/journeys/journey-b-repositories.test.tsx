import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Repositories from "@/pages/Repositories";
import { CreateRepositoryIndexModal } from "@/components/repositories/CreateRepositoryIndexModal";
import {
  renderWithProviders,
  resetAllStores,
  setMockInvokeHandler,
  createDefaultMockHandler,
  mockRepositories,
} from "@/test/test-utils";
import { useRepositoryStore } from "@/stores/repository-store";

describe("Journey B — Repository Registration, Indexing & Management", () => {
  beforeEach(() => {
    resetAllStores();
    setMockInvokeHandler(null);
  });

  it("renders repository catalog with metadata badges and details", async () => {
    renderWithProviders(<Repositories />);

    // Wait for repositories to load
    await waitFor(() => {
      expect(screen.getByText("re-track-core")).toBeInTheDocument();
    });

    // Check language and architecture badges
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("TypeScript")).toBeInTheDocument();
    expect(screen.getByText("indexed")).toBeInTheDocument();
  });

  it("filters repositories by search query and shows clear button", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Repositories />);

    await waitFor(() => {
      expect(screen.getByText("re-track-core")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Filter workspaces...");
    await user.type(searchInput, "nonexistent-workspace");

    await waitFor(() => {
      expect(screen.getByText("No matching repositories")).toBeInTheDocument();
    });

    // Clear search
    const clearButton = screen.getByRole("button", { name: "Clear search filter" });
    await user.click(clearButton);

    await waitFor(() => {
      expect(screen.getByText("re-track-core")).toBeInTheDocument();
    });
  });

  it("validates empty inputs on repository registration modal", async () => {
    const user = userEvent.setup();
    let modalOpen = true;

    renderWithProviders(
      <CreateRepositoryIndexModal
        open={modalOpen}
        onOpenChange={(val) => {
          modalOpen = val;
        }}
      />
    );

    // Modal title
    expect(screen.getByText("Index Repository")).toBeInTheDocument();

    // Click submit without entering path
    const submitBtn = screen.getByRole("button", { name: /Scan & Index/i });
    await user.click(submitBtn);

    // Expect validation error messages
    await waitFor(() => {
      expect(screen.getByText("Local path is required. Click Browse to select a folder.")).toBeInTheDocument();
      expect(screen.getByText("Repository name is required")).toBeInTheDocument();
    });
  });

  it("registers a new repository and transitions to scanning and indexing", async () => {
    const user = userEvent.setup();
    let modalOpen = true;

    const defaultMock = createDefaultMockHandler();
    let scanned = false;
    let indexed = false;
    const repoList = [...mockRepositories];

    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "create_repository") {
        const newRepo = {
          ...mockRepositories[0],
          id: "repo-new",
          name: "my-test-app",
          local_path: "/home/user/my-test-app",
          status: "registered" as const,
        };
        repoList.push(newRepo);
        return newRepo;
      }
      if (cmd === "list_repositories") {
        return { success: true, repositories: repoList, total_count: repoList.length };
      }
      if (cmd === "scan_repository") {
        scanned = true;
        return {
          repository_id: "repo-new",
          file_count: 25,
          languages: ["Rust", "TypeScript"],
          frameworks: ["Tauri", "React"],
          entry_points: ["src/main.rs"],
          summary: "A desktop application",
          components: ["App", "Sidebar"],
        };
      }
      if (cmd === "get_repository_progress") {
        return {
          status: "indexed",
          stage: "Indexing Completed",
          processed_files: 25,
          total_files: 25,
          elapsed_ms: 100,
          languages: ["Rust"],
          frameworks: ["Tauri"],
          error: null,
          file_count: 25,
          size_bytes: 50000,
        };
      }
      if (cmd === "index_repository") {
        indexed = true;
        return {
          success: true,
          repository_path: "/home/user/my-test-app",
          dataset_name: "my-test-app",
          total_files: 25,
          processed_files: 25,
          failed_files: 0,
          total_batches: 1,
          failed_paths: [],
          summary: "Indexed successfully",
        };
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(
      <CreateRepositoryIndexModal
        open={modalOpen}
        onOpenChange={(val) => {
          modalOpen = val;
        }}
      />
    );

    // Enter local path and repo name
    const pathInput = screen.getByPlaceholderText("/home/user/my-project");
    const nameInput = screen.getByPlaceholderText("re-track");

    await user.type(pathInput, "/home/user/my-test-app");
    await user.type(nameInput, "my-test-app");

    // Click submit
    const submitBtn = screen.getByRole("button", { name: /Scan & Index/i });
    await user.click(submitBtn);

    // Verify scan results appear
    await waitFor(() => {
      expect(scanned).toBe(true);
      expect(screen.getByText("Detected Languages")).toBeInTheDocument();
      expect(screen.getByText("Rust")).toBeInTheDocument();
      expect(screen.getByText("Frameworks")).toBeInTheDocument();
    });

    // Click Index Now
    const indexBtn = screen.getByRole("button", { name: /Index Now/i });
    await user.click(indexBtn);

    await waitFor(() => {
      expect(indexed).toBe(true);
    });
  });

  it("deletes repository when delete action is executed", async () => {
    let deletedRepoId: string | null = null;
    let repoList = [...mockRepositories];
    const defaultMock = createDefaultMockHandler();

    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "delete_repository") {
        deletedRepoId = (args as { repoId: string })?.repoId;
        repoList = repoList.filter((r) => r.id !== deletedRepoId);
        return { success: true };
      }
      if (cmd === "list_repositories") {
        return { success: true, repositories: repoList, total_count: repoList.length };
      }
      return defaultMock(cmd, args);
    });

    // Call store deletion directly and verify state update
    useRepositoryStore.setState({ repositories: mockRepositories });
    expect(useRepositoryStore.getState().repositories.length).toBe(1);

    await useRepositoryStore.getState().removeRepo("repo-1");

    expect(deletedRepoId).toBe("repo-1");
    expect(useRepositoryStore.getState().repositories.length).toBe(0);
  });
});
