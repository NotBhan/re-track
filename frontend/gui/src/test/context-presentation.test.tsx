import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "../App";
import { setMockInvoke } from "./setup";
import { useRepositoryStore } from "../stores/repositoryStore";
import { EvidenceViewer } from "../features/context/EvidenceViewer";
import { usePreferencesStore } from "../stores/preferencesStore";
import { invoke } from "@tauri-apps/api/core";
import type { AgentContextResponse } from "../types/api";

const MARKDOWN = [
  "# Task Context: Auth Middleware",
  "",
  "## Grounded Symbols",
  "",
  "- `create_session`",
  "",
  "```python",
  "def create_session(user):",
  "    return user",
  "```",
].join("\n");

function makeResult(overrides: Partial<AgentContextResponse> = {}): AgentContextResponse {
  return {
    success: true,
    context_markdown: MARKDOWN,
    task_summary: "Auth middleware",
    intent_category: "feature_implementation",
    extracted_symbols: ["create_session"],
    callers: [],
    callees: [],
    related_files: ["auth.py"],
    estimated_tokens: 120,
    generation_time_ms: 900,
    retrieval_time_ms: 40,
    ranking_time_ms: 12,
    synthesis_time_ms: 30,
    inference_time_ms: 800,
    evidence_state: "sufficient",
    evidence_score: 0.82,
    evidence_confidence: 1,
    ...overrides,
  };
}

async function synthesize(): Promise<void> {
  window.history.pushState({}, "", "/context");
  render(<App />);

  await waitFor(() => {
    expect(screen.getByText("Context Studio")).toBeInTheDocument();
  });

  // Synthesis requires an active repository, which arrives with hydration.
  await waitFor(() => {
    expect(useRepositoryStore.getState().selectedRepo).not.toBeNull();
  });

  fireEvent.change(screen.getByPlaceholderText(/Describe your coding task/i), {
    target: { value: "Add authentication middleware" },
  });
  fireEvent.click(screen.getByRole("button", { name: /Synthesize/i }));
}

describe("Context presentation — evidence truthfulness", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/context");
  });

  it("renders cross-validated confidence qualitatively instead of a fake percentage", () => {
    render(
      <EvidenceViewer
        result={makeResult({ evidence_confidence: 1, evidence_score: 0.82, evidence_state: "sufficient" })}
      />
    );

    expect(screen.getByText("Sufficient")).toBeInTheDocument();
    expect(screen.getByText("Evidence strength")).toBeInTheDocument();
    expect(screen.getByText("82%")).toBeInTheDocument();
    expect(screen.getByText("Cross-validated")).toBeInTheDocument();
    expect(screen.queryByText(/%\s*confidence/i)).not.toBeInTheDocument();
  });

  it("reports single-channel grounding at the engine's 0.5 confidence tier", () => {
    render(
      <EvidenceViewer
        result={makeResult({
          evidence_confidence: 0.5,
          evidence_score: 0.31,
          evidence_state: "partial",
        })}
      />
    );

    expect(screen.getByText("Partial")).toBeInTheDocument();
    expect(screen.getByText("Single-channel")).toBeInTheDocument();
    // The coarse tier is never rendered as "50% confidence".
    expect(screen.queryByText("50% confidence")).not.toBeInTheDocument();
    expect(screen.queryByText(/%\s*confidence/i)).not.toBeInTheDocument();
  });

  it("states that confidence was not computed when the engine reports zero", () => {
    render(
      <EvidenceViewer
        result={makeResult({
          evidence_confidence: 0,
          evidence_score: 0.05,
          evidence_state: "insufficient",
          abstained: true,
          abstention_reason: "Insufficient repository evidence.",
        })}
      />
    );

    expect(screen.getByText("Not computed")).toBeInTheDocument();
    expect(screen.getByText("Insufficient")).toBeInTheDocument();
    expect(screen.getByText(/abstained from unsupported claims/i)).toBeInTheDocument();
  });

  it("shows the backend's real evidence strength score", () => {
    render(<EvidenceViewer result={makeResult({ evidence_score: 0.4, evidence_confidence: 0.5 })} />);
    expect(screen.getByText("40%")).toBeInTheDocument();
  });
});

describe("Context presentation — model processing & markdown modes", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/context");
  });

  it("communicates model work with elapsed time and runtime state, never a fabricated percentage", async () => {
    let releaseSynthesis: () => void = () => {};
    const pending = new Promise<void>((resolve) => {
      releaseSynthesis = resolve;
    });

    setMockInvoke(async (cmd) => {
      if (cmd === "list_repositories") {
        return {
          success: true,
          repositories: [
            {
              id: "repo-1",
              name: "retrack-test-repo",
              source_type: "local",
              local_path: "/workspace/retrack-test-repo",
              branch: "main",
              status: "indexed",
              file_count: 42,
              size_bytes: 1024,
              languages: ["Python"],
              frameworks: [],
              entry_points: [],
              components: [],
              dependencies: [],
              metadata: {},
            },
          ],
          total_count: 1,
        };
      }
      if (cmd === "get_agent_context") {
        await pending;
        return makeResult();
      }
      if (cmd === "health") {
        return {
          status: "ok",
          provider_reachable: true,
          cognee_initialized: true,
          version: "0.1.0",
          concurrency_available_slots: 0,
          concurrency_queue_depth: 0,
        };
      }
      return undefined;
    });

    await synthesize();

    await waitFor(() => {
      expect(screen.getByText("Generating context")).toBeInTheDocument();
    });

    expect(screen.getByText(/^Elapsed \d+s$/)).toBeInTheDocument();
    expect(
      screen.getByText(/exposes no token-level progress|runtime state instead of a synthetic percentage/i)
    ).toBeInTheDocument();
    // Non-numeric by contract: the panel carries no percentage at all.
    expect(screen.getByTestId("model-processing-panel").textContent).not.toMatch(/%/);

    releaseSynthesis();

    await waitFor(() => {
      expect(screen.queryByText("Generating context")).not.toBeInTheDocument();
    });
    expect(screen.getByText("Evidence & Grounding")).toBeInTheDocument();
  });

  it("refuses to synthesize before a repository is active and explains why", async () => {
    setMockInvoke(async (cmd) => {
      if (cmd === "list_repositories") {
        // Hydration completed but no repository has been imported yet.
        return { success: true, repositories: [], total_count: 0 };
      }
      return undefined;
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("Context Studio")).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(useRepositoryStore.getState().hydrated).toBe(true);
    });

    expect(screen.getByText(/No repository is active yet/)).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/Describe your coding task/i), {
      target: { value: "Explain the auth flow" },
    });
    const synthesizeButton = screen.getByRole("button", { name: /Synthesize/ });
    expect(synthesizeButton).toBeDisabled();
    fireEvent.click(synthesizeButton);

    // No request is attempted, and no misleading error is shown.
    expect(
      vi.mocked(invoke).mock.calls.filter(([cmd]) => cmd === "get_agent_context")
    ).toHaveLength(0);
    expect(screen.queryByText(/No repository selected/)).not.toBeInTheDocument();
  });

  it("switches between rendered and raw markdown without altering content or regenerating", async () => {
    setMockInvoke(async (cmd) => {
      if (cmd === "list_repositories") {
        return {
          success: true,
          repositories: [
            {
              id: "repo-1",
              name: "retrack-test-repo",
              source_type: "local",
              local_path: "/workspace/retrack-test-repo",
              branch: "main",
              status: "indexed",
              file_count: 42,
              size_bytes: 1024,
              languages: ["Python"],
              frameworks: [],
              entry_points: [],
              components: [],
              dependencies: [],
              metadata: {},
            },
          ],
          total_count: 1,
        };
      }
      if (cmd === "get_agent_context") {
        return makeResult();
      }
      return undefined;
    });

    await synthesize();

    await waitFor(() => {
      expect(screen.getByTestId("context-rendered-markdown")).toBeInTheDocument();
    });

    // Rendered mode: markdown is presented as markup, not source text.
    const rendered = screen.getByTestId("context-rendered-markdown");
    expect(rendered.querySelector("h1")?.textContent).toBe("Task Context: Auth Middleware");
    expect(rendered.querySelector("code")).toBeTruthy();

    const callsAfterGeneration = vi.mocked(invoke).mock.calls.filter(
      ([cmd]) => cmd === "get_agent_context"
    ).length;
    expect(callsAfterGeneration).toBe(1);

    // Switch to raw markdown.
    fireEvent.click(screen.getByRole("tab", { name: /Raw Markdown/i }));

    const raw = await screen.findByTestId("context-raw-markdown");
    expect(raw.textContent).toBe(MARKDOWN);
    expect(localStorage.getItem("retrack:markdown-view")).toBe("raw");
    expect(usePreferencesStore.getState().markdownViewMode).toBe("raw");

    // Switching presentation must not trigger another model request.
    await waitFor(() => {
      const calls = vi.mocked(invoke).mock.calls.filter(([cmd]) => cmd === "get_agent_context").length;
      expect(calls).toBe(1);
    });

    // Switch back: identical source string, still no regeneration.
    fireEvent.click(screen.getByRole("tab", { name: /Rendered/i }));
    await waitFor(() => {
      expect(screen.getByTestId("context-rendered-markdown")).toBeInTheDocument();
    });
    expect(
      screen.getByTestId("context-rendered-markdown").querySelector("h1")?.textContent
    ).toBe("Task Context: Auth Middleware");
    expect(localStorage.getItem("retrack:markdown-view")).toBe("rendered");

    const totalCalls = vi.mocked(invoke).mock.calls.filter(
      ([cmd]) => cmd === "get_agent_context"
    ).length;
    expect(totalCalls).toBe(1);
  });

  it("surfaces the measured pipeline phases reported by the backend", async () => {
    setMockInvoke(async (cmd) => {
      if (cmd === "list_repositories") {
        return {
          success: true,
          repositories: [
            {
              id: "repo-1",
              name: "retrack-test-repo",
              source_type: "local",
              local_path: "/workspace/retrack-test-repo",
              branch: "main",
              status: "indexed",
              file_count: 42,
              size_bytes: 1024,
              languages: ["Python"],
              frameworks: [],
              entry_points: [],
              components: [],
              dependencies: [],
              metadata: {},
            },
          ],
          total_count: 1,
        };
      }
      if (cmd === "get_agent_context") {
        return makeResult();
      }
      return undefined;
    });

    await synthesize();

    await waitFor(() => {
      expect(screen.getByText(/retrieval 40ms/)).toBeInTheDocument();
    });
    expect(screen.getByText(/inference 800ms/)).toBeInTheDocument();
  });
});

