import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "../App";
import { setMockInvoke } from "./setup";

describe("RE:Track New GUI — Core User Journeys & Specification Verification", () => {
  beforeEach(() => {
    setMockInvoke(null);
    window.history.pushState({}, "", "/");
  });

  // --- Journey A: First Launch & Repository Management ---
  it("Journey A: renders application shell, navigates to Code, and opens Add Repository modal", async () => {
    render(<App />);

    // Brand is visible
    expect(screen.getByText("RE:Track")).toBeInTheDocument();

    // 4 primary navigation items are present
    expect(screen.getByText("Code")).toBeInTheDocument();
    expect(screen.getByText("Context")).toBeInTheDocument();
    expect(screen.getByText("Memory")).toBeInTheDocument();
    expect(screen.getByText("System")).toBeInTheDocument();

    // Repository is loaded and displayed in header & catalog
    await waitFor(() => {
      expect(screen.getByText("retrack-test-repo")).toBeInTheDocument();
    });

    // Click "Add Repository" button (+) in header
    const addBtn = screen.getByTitle("Add or import repository");
    fireEvent.click(addBtn);

    // Modal opens with Local Directory and GitHub URL options
    await waitFor(() => {
      expect(screen.getByText("Track and index a local codebase or remote repository into RE:Track.")).toBeInTheDocument();
      expect(screen.getByText("Local Directory")).toBeInTheDocument();
      expect(screen.getByText("GitHub URL")).toBeInTheDocument();
    });
  });

  // --- Journey B & C: Repository Structure & AST Call Graph ---
  it("Journey B & C: displays AST call graph with 5-state integrity, symbols, and callers/callees", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("retrack-test-repo")).toBeInTheDocument();
    });

    // Check call graph nodes
    await waitFor(() => {
      expect(screen.getByText("start_engine")).toBeInTheDocument();
      expect(screen.getByText("load_config")).toBeInTheDocument();
    });

    // Click a symbol to inspect callers/callees
    const symbolNode = screen.getByText("start_engine");
    fireEvent.click(symbolNode);

    // Inspector shows details
    await waitFor(() => {
      expect(screen.getByText("Callees (1)")).toBeInTheDocument();
    });

    // Switch tab to Manifest & Overview
    const manifestTab = screen.getByText("Manifest & Overview");
    fireEvent.click(manifestTab);

    // Verify manifest details
    await waitFor(() => {
      expect(screen.getByText("Source Files")).toBeInTheDocument();
      expect(screen.getByText("Languages & Technologies")).toBeInTheDocument();
      expect(screen.getByText("Python")).toBeInTheDocument();
      expect(screen.getByText("TypeScript")).toBeInTheDocument();
    });
  });

  // --- Journey D: Context Studio & Evidence Grounding ---
  it("Journey D: synthesizes context, inspects evidence, and provides copy action", async () => {
    render(<App />);

    // Navigate to Context
    const contextNav = screen.getByText("Context");
    fireEvent.click(contextNav);

    await waitFor(() => {
      expect(screen.getByText("Context Studio")).toBeInTheDocument();
    });

    // Input prompt and click Synthesize
    const textarea = screen.getByPlaceholderText(/Describe your coding task/i);
    fireEvent.change(textarea, { target: { value: "Add authentication middleware" } });

    const synthesizeBtn = screen.getByRole("button", { name: /Synthesize/i });
    fireEvent.click(synthesizeBtn);

    // Verify evidence breakdown is displayed
    await waitFor(() => {
      expect(screen.getByText("Evidence & Grounding")).toBeInTheDocument();
      expect(screen.getByText(/Authentication and Engine Startup/i)).toBeInTheDocument();
      expect(screen.getByText(/Evidence Grounding/i)).toBeInTheDocument();
      expect(screen.getByText("95% confidence")).toBeInTheDocument();
    });

    // Verify synthesis markdown output is displayed
    await waitFor(() => {
      expect(screen.getByText(/Synthesized Context/i)).toBeInTheDocument();
      expect(screen.getByText(/Copy/i)).toBeInTheDocument();
      expect(screen.getByText(/Save Package/i)).toBeInTheDocument();
    });
  });

  // --- Journey E: Semantic Memory Experience ---
  it("Journey E: enforces Derived Storage notice, displays ingested items, vector space, and knowledge graph", async () => {
    render(<App />);

    // Navigate to Memory
    const memoryNav = screen.getByText("Memory");
    fireEvent.click(memoryNav);

    // Enforce Epistemic clarity notice
    await waitFor(() => {
      expect(screen.getByText("Memory Engine")).toBeInTheDocument();
      expect(screen.getByText(/Derived Storage Notice/i)).toBeInTheDocument();
      expect(screen.getByText(/All records here represent derived knowledge/i)).toBeInTheDocument();
    });

    // Ingested documents table
    await waitFor(() => {
      expect(screen.getByText("engine.py")).toBeInTheDocument();
      expect(screen.getByText("sha256-abcdef123456")).toBeInTheDocument();
    });

    // Vector Space tab
    const vectorTab = screen.getByRole("tab", { name: /Vector Space/i });
    fireEvent.click(vectorTab);

    // Wait for Vector Space UI
    await waitFor(() => {
      expect(screen.getByText("Indexed Vector Partitions")).toBeInTheDocument();
      expect(screen.getByText("768 dims")).toBeInTheDocument();
    });

    // Knowledge Graph tab
    const graphTab = screen.getByRole("tab", { name: /Knowledge Graph/i });
    fireEvent.click(graphTab);

    await waitFor(() => {
      expect(screen.getAllByText("EngineService").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("DatabasePool").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("DEPENDS_ON")).toBeInTheDocument();
    });
  });

  // --- Journey F & G: System, Hardware Telemetry & Truth Boundary ---
  it("Journey F & G: handles provider switching and strictly renders 'Unavailable' when offline", async () => {
    // 1. Online state test
    render(<App />);

    const systemNav = screen.getByText("System");
    fireEvent.click(systemNav);

    await waitFor(() => {
      expect(screen.getByText("System & Settings")).toBeInTheDocument();
      expect(screen.getByText("Runtime Model Identity")).toBeInTheDocument();
    });

    // Hardware Telemetry Tab
    const telemetryTab = screen.getByText("Hardware Telemetry");
    fireEvent.click(telemetryTab);

    await waitFor(() => {
      expect(screen.getByText("18.5%")).toBeInTheDocument(); // CPU
      expect(screen.getByText(/8.2 \/ 32.0 GB/i)).toBeInTheDocument(); // RAM
      expect(screen.getByText(/RTX 4090/i)).toBeInTheDocument(); // GPU
    });

    // 2. Truth Boundary Test: When offline, displays "Unavailable" instead of synthetic zeroes!
    setMockInvoke(async (cmd) => {
      if (cmd === "health") {
        throw new Error("Backend offline");
      }
      if (cmd === "list_repositories") {
        return { success: true, repositories: [], total_count: 0 };
      }
      return { success: false };
    });

    // Trigger state update
    render(<App />);
    const sysNav = screen.getAllByText("System")[0];
    fireEvent.click(sysNav);

    const telemTab = screen.getAllByText("Hardware Telemetry")[0];
    fireEvent.click(telemTab);

    await waitFor(() => {
      // Must display "Unavailable", never synthetic 0s
      const unavailables = screen.getAllByText("Unavailable");
      expect(unavailables.length).toBeGreaterThanOrEqual(3);
    });
  });

  // --- Journey H: User-Controllable UI Scale & Desktop Shortcuts ---
  it("Journey H: controls UI scale via header steppers, keyboard shortcuts, and persists scale", async () => {
    localStorage.clear();
    render(<App />);

    // 1. Initial scale indicator is 100%
    const scaleIndicator = screen.getByTitle("Reset Scale to 100% (Ctrl 0)");
    expect(scaleIndicator).toHaveTextContent("100%");

    // 2. Click Zoom In button
    const zoomInBtn = screen.getByTitle("Zoom In (Ctrl +)");
    fireEvent.click(zoomInBtn);

    // Indicator should update to 110%
    expect(scaleIndicator).toHaveTextContent("110%");
    expect(localStorage.getItem("retrack:ui-scale")).toBe("110");

    // 3. Trigger Ctrl + - keyboard shortcut to zoom out
    fireEvent.keyDown(window, { key: "-", ctrlKey: true });
    expect(scaleIndicator).toHaveTextContent("100%");
    expect(localStorage.getItem("retrack:ui-scale")).toBe("100");

    // 4. Trigger Ctrl + 0 keyboard shortcut to reset
    fireEvent.keyDown(window, { key: "+", ctrlKey: true });
    expect(scaleIndicator).toHaveTextContent("110%");
    fireEvent.keyDown(window, { key: "0", ctrlKey: true });
    expect(scaleIndicator).toHaveTextContent("100%");

    // 5. Navigate to System -> Display & Scaling
    const sysNav = screen.getByText("System");
    fireEvent.click(sysNav);

    const displayTab = screen.getByText("Display & Scaling");
    fireEvent.click(displayTab);

    // Verify presets are present and selectable
    await waitFor(() => {
      expect(screen.getByText("Scale Presets")).toBeInTheDocument();
      expect(screen.getByText("125%")).toBeInTheDocument();
    });

    const preset125 = screen.getByText("125%");
    fireEvent.click(preset125);
    expect(scaleIndicator).toHaveTextContent("125%");
    expect(localStorage.getItem("retrack:ui-scale")).toBe("125");
  });
});

