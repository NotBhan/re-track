import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Workspace from "@/pages/Workspace";
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
    renderWithProviders(<Workspace />);

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
    renderWithProviders(<Workspace />);

    await waitFor(() => {
      expect(screen.getByText("re-track-core")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Filter workspaces...");
    await user.type(searchInput, "nonexistent-workspace");

    await waitFor(() => {
      expect(screen.getByText("No matching repositories")).toBeInTheDocument();
    });

    // Clear search
    const clearButton = screen.getAllByRole("button", { name: /Clear search filter/i })[0];
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

  it("navigates back to catalog when clicking Back to Repositories in WorkspaceHeader", async () => {
    const user = userEvent.setup();
    useRepositoryStore.setState({
      selectedId: "repo-1",
      selected: mockRepositories[0],
      repositories: mockRepositories,
    });

    renderWithProviders(<Workspace />);

    // Active workspace is shown
    expect(screen.getByRole("heading", { name: "re-track-core" })).toBeInTheDocument();
    const backBtn = screen.getByTitle("Back to Repositories");
    expect(backBtn).toBeInTheDocument();

    await user.click(backBtn);

    // After clicking back, selection is cleared and catalog is shown
    await waitFor(() => {
      expect(screen.getByText("Select Active Workspace")).toBeInTheDocument();
    });
  });

  it("opens delete confirmation modal from WorkspaceHeader and deletes repository", async () => {
    const user = userEvent.setup();
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

    useRepositoryStore.setState({
      selectedId: "repo-1",
      selected: mockRepositories[0],
      repositories: mockRepositories,
    });

    renderWithProviders(<Workspace />);

    // Click delete in WorkspaceHeader
    const deleteBtn = screen.getByTitle("Delete Repository");
    expect(deleteBtn).toBeInTheDocument();
    await user.click(deleteBtn);

    // Modal opens with safety warning and repository name
    expect(screen.getByRole("heading", { name: "Delete Repository" })).toBeInTheDocument();
    expect(screen.getByText(/Your local source code files on disk will NOT be deleted/i)).toBeInTheDocument();

    // Click confirm delete in modal
    const confirmBtn = screen.getAllByRole("button", { name: /Delete Repository/i }).find(
      (b) => b.classList.contains("bg-red-600")
    );
    expect(confirmBtn).toBeDefined();
    await user.click(confirmBtn!);

    await waitFor(() => {
      expect(deletedRepoId).toBe("repo-1");
      expect(screen.getByText("Select Active Workspace")).toBeInTheDocument();
    });
  });

  it("cancels deletion when clicking Cancel in delete modal from catalog card", async () => {
    const user = userEvent.setup();
    useRepositoryStore.setState({
      selectedId: null,
      selected: undefined,
      repositories: mockRepositories,
    });

    renderWithProviders(<Workspace />);

    await waitFor(() => {
      expect(screen.getByText("re-track-core")).toBeInTheDocument();
    });

    // Click trash button on catalog card
    const cardDeleteBtn = screen.getByRole("button", { name: "Delete re-track-core" });
    await user.click(cardDeleteBtn);

    // Modal appears
    expect(screen.getByRole("heading", { name: "Delete Repository" })).toBeInTheDocument();

    // Click Cancel
    const cancelBtn = screen.getByRole("button", { name: "Cancel" });
    await user.click(cancelBtn);

    // Modal dismissed, repo still in catalog
    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: "Delete Repository" })).not.toBeInTheDocument();
      expect(screen.getByText("re-track-core")).toBeInTheDocument();
    });
  });
});
