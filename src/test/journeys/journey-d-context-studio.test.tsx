import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ContextStudio from "@/pages/ContextStudio";
import {
  renderWithProviders,
  resetAllStores,
  setMockInvokeHandler,
  createDefaultMockHandler,
  mockRepositories,
} from "@/test/test-utils";
import { useRepositoryStore } from "@/stores/repository-store";
import { useContextPackageStore } from "@/stores/context-package-store";

describe("Journey D — Context Studio (Power Mode Workbench)", () => {
  beforeEach(() => {
    resetAllStores();
    setMockInvokeHandler(null);
    useRepositoryStore.setState({ repositories: mockRepositories, selected: mockRepositories[0] });
  });

  it("renders Context Studio workbench with repository selector, presets, and token controls", async () => {
    renderWithProviders(<ContextStudio />);

    // Verify header and workspace badge
    expect(screen.getByText(/Context Studio/i)).toBeInTheDocument();
    expect(screen.getByText("re-track-core")).toBeInTheDocument();

    // Verify token budget controls
    expect(screen.getByText(/Token Budget/i)).toBeInTheDocument();
    expect(screen.getByText("8,000 max tokens")).toBeInTheDocument();

    // Verify tab switcher exists
    expect(screen.getByRole("button", { name: /Prompt Workbench/i })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /AST Call Graph/i }).length).toBeGreaterThan(0);
  });

  it("selects a prompt preset and executes get_agent_context synthesis", async () => {
    const user = userEvent.setup();
    let requestedPrompt: string | null = null;
    let requestedTokens: number | null = null;
    const defaultMock = createDefaultMockHandler();

    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "get_agent_context") {
        const req = (args as { request: { task_prompt: string; max_tokens: number } })?.request;
        requestedPrompt = req?.task_prompt || null;
        requestedTokens = req?.max_tokens || null;
        return {
          success: true,
          context_markdown: "## Architecture\n- Deterministic AST Parser\n\n## Implementation\nAdd token limits",
          task_summary: "Implement token budgeting",
          intent_category: "feature",
          extracted_symbols: ["generate_context", "prune_tokens"],
          callers: ["TopBar"],
          callees: ["extract_ast"],
          related_files: ["backend/app/services/context.py"],
          estimated_tokens: 380,
          generation_time_ms: 85,
        };
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<ContextStudio />);

    // Click "Synthesize Context"
    const synthesizeBtn = screen.getByRole("button", { name: /Synthesize Context/i });
    await user.click(synthesizeBtn);

    // Verify synthesis executed and markdown rendered
    await waitFor(() => {
      expect(requestedPrompt).toBeTruthy();
      expect(requestedTokens).toBe(8000);
      expect(screen.getByText(/Deterministic AST Parser/i)).toBeInTheDocument();
    });

    // Check telemetry metrics
    expect(screen.getByText("~380 tokens")).toBeInTheDocument();
  });

  it("copies synthesized package to clipboard", async () => {
    const user = userEvent.setup();

    setMockInvokeHandler(async (cmd: string) => {
      if (cmd === "get_agent_context") {
        return {
          success: true,
          context_markdown: "# Custom Context Content\n\nGenerated for agent test.",
          task_summary: "Test summary",
          intent_category: "test",
          extracted_symbols: ["test_func"],
          callers: [],
          callees: [],
          related_files: ["src/test.ts"],
          estimated_tokens: 120,
          generation_time_ms: 50,
        };
      }
      return { success: true };
    });

    renderWithProviders(<ContextStudio />);

    const synthesizeBtn = screen.getByRole("button", { name: /Synthesize Context/i });
    await user.click(synthesizeBtn);

    await waitFor(() => {
      expect(screen.getByText(/Custom Context Content/i)).toBeInTheDocument();
    });

    const copyBtn = screen.getByRole("button", { name: /Copy Context/i });
    await user.click(copyBtn);

    const clipboardText = await navigator.clipboard.readText();
    expect(clipboardText).toContain("Custom Context Content");
  });

  it("saves synthesized package to package store and backend", async () => {
    const user = userEvent.setup();
    let savedPackageTitle: string | null = null;
    const defaultMock = createDefaultMockHandler();

    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "get_agent_context") {
        return {
          success: true,
          context_markdown: "## Goal\nSave context package to disk",
          task_summary: "Save package task",
          intent_category: "storage",
          extracted_symbols: ["save_context_package"],
          callers: [],
          callees: [],
          related_files: ["src/stores/context-package-store.ts"],
          estimated_tokens: 210,
          generation_time_ms: 60,
        };
      }
      if (cmd === "save_context_package") {
        const req = (args as { request: { name: string } })?.request;
        savedPackageTitle = req?.name || null;
        return {
          id: "pkg-saved-1",
          title: req?.name || "Context Package",
          markdown: "## Goal\nSave context package to disk",
          total_tokens: 210,
          file_count: 1,
          created_at: new Date().toISOString(),
        };
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<ContextStudio />);

    // Synthesize
    const synthesizeBtn = screen.getByRole("button", { name: /Synthesize Context/i });
    await user.click(synthesizeBtn);

    await waitFor(() => {
      expect(screen.getByText(/Save context package to disk/i)).toBeInTheDocument();
    });

    // Click Save button
    const saveBtn = screen.getByRole("button", { name: /^Save$/i });
    await user.click(saveBtn);

    // Verify package store has saved package
    await waitFor(() => {
      expect(savedPackageTitle).not.toBeNull();
      expect(useContextPackageStore.getState().packages.length).toBeGreaterThan(0);
    });
  });

  it("switches to AST Call Graph tab view in desktop mode", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ContextStudio />);

    const callGraphTab = screen.getByRole("button", { name: /AST Call Graph/i });
    await user.click(callGraphTab);

    // Verify Call Graph container is rendered
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Search symbols/i)).toBeInTheDocument();
    });
  });
});
