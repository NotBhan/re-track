/**
 * Journey L — inference request lifecycle.
 *
 * Guards the frontend half of the "one user action → one model inference"
 * invariant, plus cancellation/navigation behaviour while a generation is
 * in flight. The backend half lives in backend/tests/test_inference_lifecycle.py.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor, act } from "@testing-library/react";
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
import type { AgentContextResponse } from "@/lib/api";

const TASK_PLACEHOLDER = "Type the feature, refactoring, or question for your local memory...";

function contextResponse(task: string): AgentContextResponse {
  return {
    success: true,
    context_markdown: `# Context\n\n${task}`,
    task_summary: task,
    intent_category: "explanation",
    extracted_symbols: ["BudgetManager"],
    callers: [],
    callees: [],
    related_files: ["backend/app/services/budget_manager.py"],
    estimated_tokens: 128,
    generation_time_ms: 10,
    total_time_ms: 10,
    model_invoked: true,
    inference_status: "completed",
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("Journey L — inference request lifecycle", () => {
  let generationRequests: number;

  beforeEach(() => {
    resetAllStores();
    generationRequests = 0;
    useRepositoryStore.setState({
      selectedId: "repo-1",
      selected: mockRepositories[0],
      repositories: mockRepositories,
    });

    const defaultMock = createDefaultMockHandler();
    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "get_agent_context") {
        generationRequests += 1;
        const task = (args as { request?: { task_prompt?: string } })?.request?.task_prompt ?? "";
        return contextResponse(task);
      }
      return defaultMock(cmd, args);
    });
  });

  it("issues exactly one generation request per Synthesize action", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ContextStudio />);

    const promptInput = await screen.findByPlaceholderText(TASK_PLACEHOLDER);
    await user.clear(promptInput);
    await user.type(promptInput, "Explain the token budgeting pipeline");

    const synthesize = screen.getByRole("button", { name: /Synthesize Context/i });
    await user.click(synthesize);

    await waitFor(() => {
      expect(generationRequests).toBe(1);
    });
    expect(await screen.findByText(/Synthesized Context Package/i)).toBeInTheDocument();
    expect(generationRequests).toBe(1);
  });

  it("rapid repeated clicks while in flight do not start additional generations", async () => {
    const user = userEvent.setup();
    const gate = deferred<AgentContextResponse>();

    const defaultMock = createDefaultMockHandler();
    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "get_agent_context") {
        generationRequests += 1;
        return gate.promise;
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<ContextStudio />);

    const promptInput = await screen.findByPlaceholderText(TASK_PLACEHOLDER);
    await user.clear(promptInput);
    await user.type(promptInput, "Explain retrieval arbitration");

    const synthesize = screen.getByRole("button", { name: /Synthesize Context/i });
    await user.click(synthesize);
    await user.click(synthesize);
    await user.click(synthesize);

    expect(generationRequests).toBe(1);

    await act(async () => {
      gate.resolve(contextResponse("Explain retrieval arbitration"));
      await gate.promise.catch(() => undefined);
    });

    await waitFor(() => {
      expect(generationRequests).toBe(1);
    });
  });

  it("unmounting during an in-flight generation does not emit a second request", async () => {
    const user = userEvent.setup();
    const gate = deferred<AgentContextResponse>();

    const defaultMock = createDefaultMockHandler();
    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "get_agent_context") {
        generationRequests += 1;
        return gate.promise;
      }
      return defaultMock(cmd, args);
    });

    const { unmount } = renderWithProviders(<ContextStudio />);

    const promptInput = await screen.findByPlaceholderText(TASK_PLACEHOLDER);
    await user.clear(promptInput);
    await user.type(promptInput, "Explain the evidence gate");

    await user.click(screen.getByRole("button", { name: /Synthesize Context/i }));
    expect(generationRequests).toBe(1);

    // Navigating away mid-generation must not enqueue more work.
    unmount();

    await act(async () => {
      gate.resolve(contextResponse("Explain the evidence gate"));
      await gate.promise.catch(() => undefined);
    });

    expect(generationRequests).toBe(1);
    expect(useRepositoryStore.getState().pollInterval).toBeNull();
  });

  it("cancelling an in-flight generation does not start another generation", async () => {
    const user = userEvent.setup();
    const gate = deferred<AgentContextResponse>();

    const defaultMock = createDefaultMockHandler();
    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "get_agent_context") {
        generationRequests += 1;
        return gate.promise;
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(<ContextStudio />);

    const promptInput = await screen.findByPlaceholderText(TASK_PLACEHOLDER);
    await user.clear(promptInput);
    await user.type(promptInput, "Explain cancellation");

    await user.click(screen.getByRole("button", { name: /Synthesize Context/i }));

    // Both the progress bar and the workbench footer expose a Cancel action.
    const [cancel] = await screen.findAllByRole("button", { name: /^Cancel$/i });
    await user.click(cancel);

    // The UI stops waiting; no replacement request is spawned.
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Synthesize Context/i })).toBeInTheDocument();
    });
    expect(generationRequests).toBe(1);

    await act(async () => {
      gate.resolve(contextResponse("Explain cancellation"));
      await gate.promise.catch(() => undefined);
    });
    expect(generationRequests).toBe(1);
  });

  it("re-mounting after navigation issues at most one new generation", async () => {
    const user = userEvent.setup();

    const first = renderWithProviders(<ContextStudio />);
    const promptInput = await screen.findByPlaceholderText(TASK_PLACEHOLDER);
    await user.clear(promptInput);
    await user.type(promptInput, "Explain remount");
    await user.click(screen.getByRole("button", { name: /Synthesize Context/i }));

    await waitFor(() => {
      expect(generationRequests).toBe(1);
    });
    first.unmount();

    renderWithProviders(<ContextStudio />);
    await screen.findByPlaceholderText(TASK_PLACEHOLDER);

    // Remounting alone must not replay the previous request.
    expect(generationRequests).toBe(1);
  });
});
