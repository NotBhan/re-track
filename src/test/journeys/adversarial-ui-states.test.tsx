import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Repositories from "@/pages/Repositories";
import ContextStudio from "@/pages/ContextStudio";
import {
  renderWithProviders,
  resetAllStores,
  setMockInvokeHandler,
  createDefaultMockHandler,
  mockRepositories,
} from "@/test/test-utils";
import { useRepositoryStore } from "@/stores/repository-store";

describe("Adversarial UI States & Race Conditions", () => {
  beforeEach(() => {
    resetAllStores();
    setMockInvokeHandler(null);
  });

  it("prevents duplicate synthesize context execution upon rapid multiple clicks", async () => {
    const user = userEvent.setup();
    let synthesisCallCount = 0;
    const defaultMock = createDefaultMockHandler();

    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "get_agent_context") {
        synthesisCallCount += 1;
        // Simulate async latency
        await new Promise((res) => setTimeout(res, 50));
        return {
          success: true,
          task_prompt: "Prune tokens",
          intent_summary: "Pruning tokens",
          suggested_focus_files: ["backend/app/main.py"],
          context_markdown: "# Pruned Context",
          estimated_tokens: 280,
          generation_time_ms: 50,
        };
      }
      return defaultMock(cmd, args);
    });

    useRepositoryStore.setState({ repositories: mockRepositories });

    renderWithProviders(<ContextStudio />, {
      initialEntries: ["/studio?repo=repo-1"],
    });

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Type the feature/i)).toBeInTheDocument();
    });

    const taskInput = screen.getByPlaceholderText(/Type the feature/i);
    await user.type(taskInput, "Prune tokens");

    const generateBtn = screen.getByRole("button", { name: /Synthesize Context/i });

    // Click multiple times rapidly
    await Promise.all([
      user.click(generateBtn),
      user.click(generateBtn),
      user.click(generateBtn),
    ]);

    await waitFor(() => {
      expect(screen.getByText("Pruned Context")).toBeInTheDocument();
    });

    // Should only have executed 1 request because button is disabled during synthesis
    expect(synthesisCallCount).toBe(1);
  });

  it("displays clear error feedback when backend service fails", async () => {
    const user = userEvent.setup();
    const defaultMock = createDefaultMockHandler();

    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "get_agent_context") {
        throw new Error("LanceDB connection refused: Vector database locked by another process");
      }
      return defaultMock(cmd, args);
    });

    useRepositoryStore.setState({ repositories: mockRepositories });

    renderWithProviders(<ContextStudio />, {
      initialEntries: ["/studio?repo=repo-1"],
    });

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Type the feature/i)).toBeInTheDocument();
    });

    const taskInput = screen.getByPlaceholderText(/Type the feature/i);
    await user.type(taskInput, "Fix broken index");

    const generateBtn = screen.getByRole("button", { name: /Synthesize Context/i });
    await user.click(generateBtn);

    await waitFor(() => {
      expect(screen.getByText(/LanceDB connection refused/i)).toBeInTheDocument();
    });
  });

  it("handles unmounting safely when navigation occurs during active async fetch", async () => {
    const defaultMock = createDefaultMockHandler();
    let slowFetchStarted = false;

    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "list_repositories") {
        slowFetchStarted = true;
        await new Promise((res) => setTimeout(res, 100));
        return { success: true, repositories: mockRepositories, total_count: mockRepositories.length };
      }
      return defaultMock(cmd, args);
    });

    const { unmount } = renderWithProviders(<Repositories />);

    expect(slowFetchStarted).toBe(true);

    // Unmount before fetch resolves
    unmount();

    // Verify unmount completes cleanly without unhandled rejection or memory leak crash
    await new Promise((res) => setTimeout(res, 150));
  });
});
