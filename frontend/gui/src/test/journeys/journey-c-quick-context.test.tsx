import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QuickContextModal } from "@/components/repositories/QuickContextModal";
import {
  renderWithProviders,
  resetAllStores,
  setMockInvokeHandler,
  createDefaultMockHandler,
  mockRepositories,
  mockContextResponse,
} from "@/test/test-utils";

describe("Journey C — Quick Context Synthesis & Export", () => {
  beforeEach(() => {
    resetAllStores();
    setMockInvokeHandler(null);
  });

  it("opens Quick Context modal with selected repository and preset tasks", async () => {
    renderWithProviders(
      <QuickContextModal
        repo={mockRepositories[0]}
        open={true}
        onOpenChange={() => {}}
      />
    );

    // Verify modal title and selected repository tag
    expect(screen.getByText("Quick Context Synthesizer")).toBeInTheDocument();
    expect(screen.getByText("re-track-core")).toBeInTheDocument();

    // Verify preset tasks are rendered
    expect(screen.getByText("OAuth2 Authentication")).toBeInTheDocument();
    expect(screen.getByText("API Endpoint")).toBeInTheDocument();
    expect(screen.getByText("Unit Test Suite")).toBeInTheDocument();
  });

  it("executes context synthesis, renders progress, and displays synthesized results", async () => {
    const user = userEvent.setup();
    let generatedTask: string | null = null;
    const defaultMock = createDefaultMockHandler();

    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "generate_context") {
        const req = (args as { request: { task: string } })?.request;
        generatedTask = req?.task || null;
        return mockContextResponse;
      }
      return defaultMock(cmd, args);
    });

    renderWithProviders(
      <QuickContextModal
        repo={mockRepositories[0]}
        open={true}
        onOpenChange={() => {}}
      />
    );

    // Click Generate Context with default task
    const generateBtn = screen.getByRole("button", { name: /Synthesize Context/i });
    await user.click(generateBtn);

    // Verify synthesis completed and results rendered
    await waitFor(() => {
      expect(generatedTask).toContain("Implement OAuth2 social login");
      expect(screen.getByText("Generated Context Markdown")).toBeInTheDocument();
    });

    // Check token estimate and memories count
    expect(screen.getByText("~420")).toBeInTheDocument();
    expect(screen.getByText("3 facts")).toBeInTheDocument();
  });

  it("copies synthesized context markdown to clipboard", async () => {
    const user = userEvent.setup();

    setMockInvokeHandler(async (cmd: string) => {
      if (cmd === "generate_context") {
        return mockContextResponse;
      }
      return { success: true };
    });

    renderWithProviders(
      <QuickContextModal
        repo={mockRepositories[0]}
        open={true}
        onOpenChange={() => {}}
      />
    );

    // Synthesize
    const generateBtn = screen.getByRole("button", { name: /Synthesize Context/i });
    await user.click(generateBtn);

    await waitFor(() => {
      expect(screen.getByText("Generated Context Markdown")).toBeInTheDocument();
    });

    // Copy to clipboard
    const copyBtn = screen.getByRole("button", { name: /Copy Context/i });
    await user.click(copyBtn);

    // Verify UI feedback
    expect(screen.getByText("Copied!")).toBeInTheDocument();
    const copiedText = await navigator.clipboard.readText();
    expect(copiedText).toBe(mockContextResponse.markdown);
  });

  it("supports user cancellation during active synthesis", async () => {
    const user = userEvent.setup();

    // Create delayed response to simulate in-flight synthesis
    setMockInvokeHandler(async (cmd: string) => {
      if (cmd === "generate_context") {
        await new Promise((resolve) => setTimeout(resolve, 500));
        return mockContextResponse;
      }
      return { success: true };
    });

    renderWithProviders(
      <QuickContextModal
        repo={mockRepositories[0]}
        open={true}
        onOpenChange={() => {}}
      />
    );

    // Start synthesis
    const generateBtn = screen.getByRole("button", { name: /Synthesize Context/i });
    await user.click(generateBtn);

    // Cancel synthesis via any active cancel button
    const cancelButtons = await screen.findAllByRole("button", { name: /Cancel/i });
    expect(cancelButtons.length).toBeGreaterThan(0);
    await user.click(cancelButtons[0]);

    // Button reverts back to Synthesize
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Synthesize Context/i })).toBeInTheDocument();
    });
  });
});
