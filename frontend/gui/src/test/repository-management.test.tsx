import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import App from "../App";
import { setMockInvoke } from "./setup";
import { useRepositoryStore } from "../stores/repositoryStore";
import type { Repository } from "../types/api";

function makeRepo(overrides: Partial<Repository> & { id: string; name: string }): Repository {
  return {
    source_type: "local",
    source_url: null,
    local_path: `/workspace/${overrides.name}`,
    branch: "main",
    commit_hash: null,
    status: "indexed",
    languages: ["Python"],
    frameworks: ["FastAPI"],
    file_count: 12,
    size_bytes: 2048,
    indexed_at: "2026-01-02T10:00:00Z",
    error_message: null,
    summary: `Summary for ${overrides.name}`,
    entry_points: ["main.py"],
    architecture: "flat",
    components: ["src"],
    dependencies: [],
    metadata: {},
    ...overrides,
  };
}

const REPO_A = makeRepo({ id: "repo-a", name: "alpha-service" });
const REPO_B = makeRepo({
  id: "repo-b",
  name: "beta-service",
  status: "registered",
  source_type: "github",
  source_url: "https://github.com/example/beta-service.git",
  languages: ["TypeScript"],
  frameworks: ["React"],
  file_count: 30,
  size_bytes: 4096,
});

function listedRepos(name: string): HTMLElement[] {
  return screen.queryAllByText(name);
}

function listHandler(repos: Repository[]) {
  return async (cmd: string) => {
    if (cmd === "list_repositories") {
      return { success: true, repositories: repos, total_count: repos.length };
    }
    return undefined;
  };
}

describe("Repository Management — startup hydration & lifecycle", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/repositories");
  });

  it("hydrates previously persisted repositories on cold start without any user action", async () => {
    setMockInvoke(async (cmd) => {
      if (cmd === "list_repositories") {
        return { success: true, repositories: [REPO_A, REPO_B], total_count: 2 };
      }
      return undefined;
    });

    render(<App />);

    await waitFor(() => {
      expect(listedRepos("alpha-service").length).toBeGreaterThan(0);
      expect(listedRepos("beta-service").length).toBeGreaterThan(0);
    });

    // Both persisted repositories are listed without importing anything.
    expect(screen.getByText("Tracked Repositories")).toBeInTheDocument();
    expect(useRepositoryStore.getState().hydrated).toBe(true);
  });

  it("retries the initial fetch until the backend becomes ready after launch", async () => {
    let attempts = 0;
    setMockInvoke(async (cmd) => {
      if (cmd === "list_repositories") {
        attempts += 1;
        if (attempts === 1) {
          throw new Error("HTTP request failed: connection refused");
        }
        return { success: true, repositories: [REPO_A, REPO_B], total_count: 2 };
      }
      return undefined;
    });

    render(<App />);

    await waitFor(
      () => {
        expect(listedRepos("alpha-service").length).toBeGreaterThan(0);
        expect(listedRepos("beta-service").length).toBeGreaterThan(0);
      },
      { timeout: 4000 }
    );
    expect(attempts).toBeGreaterThanOrEqual(2);
  });

  it("keeps an actionable empty state when nothing is persisted", async () => {
    setMockInvoke(async (cmd) => {
      if (cmd === "list_repositories") {
        return { success: true, repositories: [], total_count: 0 };
      }
      return undefined;
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("No Repositories Tracked")).toBeInTheDocument();
    });
    expect(screen.getAllByRole("button", { name: /Add Repository/i }).length).toBeGreaterThan(0);
  });

  it("restores the previously active repository from the last session", async () => {
    localStorage.setItem("retrack:active-repository", "repo-b");
    setMockInvoke(listHandler([REPO_A, REPO_B]));

    render(<App />);

    await waitFor(() => {
      expect(listedRepos("beta-service").length).toBeGreaterThan(0);
    });

    // Header switcher reflects the restored active repository.
    const switcher = screen.getByRole("combobox", { name: "Active repository" });
    expect(switcher).toHaveTextContent("beta-service");

    // The management list marks it as the active repository.
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(useRepositoryStore.getState().selectedId).toBe("repo-b");
  });

  it("defaults the active repository to the first persisted repository when none was stored", async () => {
    setMockInvoke(listHandler([REPO_A, REPO_B]));

    render(<App />);

    await waitFor(() => {
      expect(useRepositoryStore.getState().selectedId).toBe("repo-a");
    });
    expect(localStorage.getItem("retrack:active-repository")).toBe("repo-a");
  });

  it("opens Add Repository from the labeled action and adds the new repository without losing existing ones", async () => {
    const repos = [REPO_A, REPO_B];
    const created = makeRepo({ id: "repo-c", name: "gamma-service", status: "registered" });

    setMockInvoke(async (cmd) => {
      if (cmd === "list_repositories") {
        return { success: true, repositories: [...repos], total_count: repos.length };
      }
      if (cmd === "create_repository") {
        repos.push(created);
        return created;
      }
      if (cmd === "scan_repository") {
        return { repository_id: created.id, file_count: 3, languages: ["Go"] };
      }
      return undefined;
    });

    render(<App />);

    await waitFor(() => {
      expect(listedRepos("alpha-service").length).toBeGreaterThan(0);
    });

    fireEvent.click(screen.getByTitle("Add or import repository"));

    await waitFor(() => {
      expect(
        screen.getByText("Track and index a local codebase or remote repository into RE:Track.")
      ).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText("/path/to/project"), {
      target: { value: "/workspace/gamma-service" },
    });
    fireEvent.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: /^Add Repository$/i })
    );

    await waitFor(() => {
      expect(listedRepos("gamma-service").length).toBeGreaterThan(0);
      expect(listedRepos("alpha-service").length).toBeGreaterThan(0);
      expect(listedRepos("beta-service").length).toBeGreaterThan(0);
    });
  });

  it("switches the active repository when another one is selected", async () => {
    setMockInvoke(listHandler([REPO_A, REPO_B]));

    render(<App />);

    await waitFor(() => {
      expect(listedRepos("beta-service").length).toBeGreaterThan(0);
    });

    const switcher = screen.getByRole("combobox", { name: "Active repository" });
    fireEvent.click(switcher);
    fireEvent.click(await screen.findByRole("option", { name: /beta-service/i }));

    await waitFor(() => {
      expect(useRepositoryStore.getState().selectedId).toBe("repo-b");
    });
    expect(localStorage.getItem("retrack:active-repository")).toBe("repo-b");
  });

  it("shows only real backend summary fields for the selected repository", async () => {
    setMockInvoke(listHandler([REPO_A]));

    render(<App />);

    await waitFor(() => {
      expect(listedRepos("alpha-service").length).toBeGreaterThan(0);
    });

    const summary = screen.getByText("Source files").closest("dl") as HTMLElement;
    expect(summary).toBeTruthy();
    expect(within(summary).getByText("12")).toBeInTheDocument();
    expect(within(summary).getByText("2 KB")).toBeInTheDocument();
    expect(within(summary).getByText("/workspace/alpha-service")).toBeInTheDocument();
    expect(within(summary).getByText(/Not available in this backend/)).toBeInTheDocument();
    expect(screen.getByText("main.py")).toBeInTheDocument();
  });

  it("re-indexes through the confirmed flow and renders backend phase progress", async () => {
    let progressCall = 0;
    let releaseIndex: () => void = () => {};
    const indexPending = new Promise<void>((resolve) => {
      releaseIndex = resolve;
    });

    setMockInvoke(async (cmd) => {
      if (cmd === "list_repositories") {
        return { success: true, repositories: [REPO_A], total_count: 1 };
      }
      if (cmd === "index_repository") {
        await indexPending;
        return {
          success: true,
          repository_path: REPO_A.local_path,
          dataset_name: REPO_A.name,
          total_files: 12,
          processed_files: 12,
          failed_files: 0,
          total_batches: 2,
          failed_paths: [],
          summary: "Indexed 12 files",
        };
      }
      if (cmd === "get_repository_progress") {
        progressCall += 1;
        return {
          success: true,
          repo_id: REPO_A.id,
          status: "indexing",
          stage: "Extracting AST call graphs and symbols...",
          stage_index: 2,
          stage_total: 5,
          processed_files: 0,
          total_files: 12,
          elapsed_ms: 800,
          languages: ["Python"],
          frameworks: ["FastAPI"],
          error: null,
          file_count: 12,
          size_bytes: 2048,
        };
      }
      return undefined;
    });

    render(<App />);

    await waitFor(() => {
      expect(listedRepos("alpha-service").length).toBeGreaterThan(0);
    });

    fireEvent.click(screen.getByRole("button", { name: /Re-index/i }));

    await waitFor(() => {
      expect(screen.getByText("Indexing alpha-service")).toBeInTheDocument();
    });

    // Live phase data reported by the backend while the run is still in flight.
    await waitFor(
      () => {
        expect(screen.getByText(/Phase 2 of 5/)).toBeInTheDocument();
        expect(screen.getByText("Extracting AST call graphs and symbols...")).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    releaseIndex();

    // Completion state replaces the running phase view.
    await waitFor(() => {
      expect(screen.getByText("Indexing completed")).toBeInTheDocument();
    });
    expect(screen.queryByText(/Phase 2 of 5/)).not.toBeInTheDocument();
    expect(progressCall).toBeGreaterThan(0);
  });

  it("prevents duplicate re-index requests while one is running", async () => {
    let releaseIndex: () => void = () => {};
    const indexPending = new Promise<void>((resolve) => {
      releaseIndex = resolve;
    });

    setMockInvoke(async (cmd) => {
      if (cmd === "list_repositories") {
        return { success: true, repositories: [REPO_A], total_count: 1 };
      }
      if (cmd === "index_repository") {
        await indexPending;
        return {
          success: true,
          repository_path: REPO_A.local_path,
          dataset_name: REPO_A.name,
          total_files: 12,
          processed_files: 12,
          failed_files: 0,
          total_batches: 1,
          failed_paths: [],
          summary: "done",
        };
      }
      return undefined;
    });

    render(<App />);

    await waitFor(() => {
      expect(listedRepos("alpha-service").length).toBeGreaterThan(0);
    });

    const reindex = screen.getByRole("button", { name: /Re-index/i });
    fireEvent.click(reindex);

    await waitFor(() => {
      expect(screen.getByText("Indexing alpha-service")).toBeInTheDocument();
    });

    // The action is disabled while the run is in flight, so no second request can be issued.
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Re-index/i })).toBeDisabled();
    });
    expect(useRepositoryStore.getState().indexing).toBe(true);

    releaseIndex();
    await waitFor(() => {
      expect(useRepositoryStore.getState().indexing).toBe(false);
    });
  });

  it("requires confirmation before deleting and updates the list immediately", async () => {
    const deleted: string[] = [];
    const remaining = [REPO_A, REPO_B];
    setMockInvoke(async (cmd, args) => {
      if (cmd === "list_repositories") {
        return { success: true, repositories: [...remaining], total_count: remaining.length };
      }
      if (cmd === "delete_repository") {
        const repoId = (args as { repoId?: string })?.repoId || "";
        deleted.push(repoId);
        const index = remaining.findIndex((r) => r.id === repoId);
        if (index >= 0) remaining.splice(index, 1);
        return { success: true };
      }
      return undefined;
    });

    render(<App />);

    await waitFor(() => {
      expect(listedRepos("alpha-service").length).toBeGreaterThan(0);
    });

    fireEvent.click(screen.getByRole("button", { name: /^Delete$/i }));

    await waitFor(() => {
      expect(screen.getByText('Delete "alpha-service"?')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Delete Repository/i }));

    await waitFor(() => {
      expect(listedRepos("alpha-service").length).toBe(0);
      expect(listedRepos("beta-service").length).toBeGreaterThan(0);
    });
    expect(deleted).toEqual(["repo-a"]);
  });

  it("surfaces delete failures and keeps the repository listed", async () => {
    setMockInvoke(async (cmd) => {
      if (cmd === "list_repositories") {
        return { success: true, repositories: [REPO_A], total_count: 1 };
      }
      if (cmd === "delete_repository") {
        throw new Error("Failed to delete repository: backend offline");
      }
      return undefined;
    });

    render(<App />);

    await waitFor(() => {
      expect(listedRepos("alpha-service").length).toBeGreaterThan(0);
    });

    fireEvent.click(screen.getByRole("button", { name: /^Delete$/i }));
    fireEvent.click(await screen.findByRole("button", { name: /Delete Repository/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/Failed to delete repository: backend offline/)
      ).toBeInTheDocument();
    });
    expect(listedRepos("alpha-service").length).toBeGreaterThan(0);
  });

  it("stays interactive at the largest supported UI scale", async () => {
    setMockInvoke(listHandler([REPO_A, REPO_B]));

    render(<App />);

    await waitFor(() => {
      expect(listedRepos("alpha-service").length).toBeGreaterThan(0);
    });

    fireEvent.click(screen.getByTitle("Zoom In (Ctrl +)"));
    fireEvent.click(screen.getByTitle("Zoom In (Ctrl +)"));
    expect(localStorage.getItem("retrack:ui-scale")).toBe("125");
    fireEvent.click(screen.getByTitle("Zoom In (Ctrl +)"));
    fireEvent.click(screen.getByTitle("Zoom In (Ctrl +)"));
    expect(localStorage.getItem("retrack:ui-scale")).toBe("150");

    // The scaled root is pinned to viewport/factor so the layout cannot clip.
    expect(document.documentElement.style.zoom).toBe("150%");
    expect(document.documentElement.style.width).toBe(
      `${Math.round(window.innerWidth / 1.5)}px`
    );

    // Controls remain operable after scaling.
    const switcher = screen.getByRole("combobox", { name: "Active repository" });
    fireEvent.click(switcher);
    fireEvent.click(await screen.findByRole("option", { name: /beta-service/i }));

    await waitFor(() => {
      expect(useRepositoryStore.getState().selectedId).toBe("repo-b");
    });
  });
});
