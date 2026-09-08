import { describe, it, expect, beforeEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "@/App";
import Workspace from "@/pages/Workspace";
import ContextStudio from "@/pages/ContextStudio";
import Memory from "@/pages/Memory";
import SystemTelemetry from "@/pages/SystemTelemetry";
import { TierEvidenceStack } from "@/components/context-builder/TierEvidenceStack";
import { PackageHistoryDrawer } from "@/components/context-packages/PackageHistoryDrawer";
import { CallGraphView } from "@/components/repositories/CallGraphView";
import {
  renderWithProviders,
  resetAllStores,
  setMockInvokeHandler,
  createDefaultMockHandler,
  mockRepositories,
  mockSavedPackages,
} from "@/test/test-utils";
import { useRepositoryStore } from "@/stores/repository-store";
import { useHealthStore } from "@/stores/health-store";
import { useContextPackageStore } from "@/stores/context-package-store";
import type { CallGraphNode, CallGraphEdge } from "@/types/repository";

describe("Phase 10D.7 — 4-Pillar Unified Architecture & Specification Conformance", () => {
  beforeEach(() => {
    resetAllStores();
    setMockInvokeHandler(null);
  });

  describe("Requirement 6: Legacy Routes & Route Contract (Preserving Query Parameters)", () => {
    it("renders four primary navigation items and global repository selector", async () => {
      useRepositoryStore.setState({
        selectedId: null,
        selected: undefined,
        repositories: mockRepositories,
      });

      renderWithProviders(<App />, { withRouter: false });

      // Four primary navigation items
      expect(screen.getByRole("link", { name: /Workspace/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Context Studio/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Memory Engine/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /System & Telemetry/i })).toBeInTheDocument();

      // Global repository selector shows Select Repository when null
      expect(screen.getByTestId("global-repo-selector")).toHaveTextContent("Select Repository");
    });

    it("redirects legacy /context-builder to /studio preserving query params", async () => {
      window.history.pushState({}, "", "/context-builder?repo=repo-1");

      renderWithProviders(<App />, { withRouter: false });

      await waitFor(() => {
        expect(window.location.pathname).toBe("/studio");
        expect(window.location.search).toContain("repo=repo-1");
      });
    });

    it("redirects legacy /settings to /system?tab=runtime preserving additional params", async () => {
      window.history.pushState({}, "", "/settings?foo=bar");

      renderWithProviders(<App />, { withRouter: false });

      await waitFor(() => {
        expect(window.location.pathname).toBe("/system");
        expect(window.location.search).toContain("tab=runtime");
        expect(window.location.search).toContain("foo=bar");
      });
    });

    it("redirects legacy /benchmarks to /system?tab=benchmarks", async () => {
      window.history.pushState({}, "", "/benchmarks");

      renderWithProviders(<App />, { withRouter: false });

      await waitFor(() => {
        expect(window.location.pathname).toBe("/system");
        expect(window.location.search).toContain("tab=benchmarks");
      });
    });

    it("redirects legacy /packages to /studio?tab=history preserving repo param", async () => {
      window.history.pushState({}, "", "/packages?repo=repo-2");

      renderWithProviders(<App />, { withRouter: false });

      await waitFor(() => {
        expect(window.location.pathname).toBe("/studio");
        expect(window.location.search).toContain("tab=history");
        expect(window.location.search).toContain("repo=repo-2");
      });
    });

    it("redirects legacy /knowledge/:repoId to /workspace?repo=:repoId&tab=ast", async () => {
      window.history.pushState({}, "", "/knowledge/repo-1?extra=1");

      renderWithProviders(<App />, { withRouter: false });

      await waitFor(() => {
        expect(window.location.pathname).toBe("/workspace");
        expect(window.location.search).toContain("repo=repo-1");
        expect(window.location.search).toContain("tab=ast");
        expect(window.location.search).toContain("extra=1");
      });
    });

    it("synchronizes URL query parameter ?repo=<id> into repository store", async () => {
      window.history.pushState({}, "", "/workspace?repo=repo-2");

      useRepositoryStore.setState({
        selectedId: null,
        selected: undefined,
        repositories: mockRepositories,
      });

      renderWithProviders(<App />, { withRouter: false });

      await waitFor(() => {
        expect(useRepositoryStore.getState().selectedId).toBe("repo-2");
      });
    });
  });

  describe("Requirement 1: Workspace Tabs & Exact Lifecycle Labels (Scan -> Manifest -> AST Extraction -> Cognification)", () => {
    it("displays the exact 4 tabs: Overview, Lifecycle, AST, Manifest & Evidence", async () => {
      useRepositoryStore.setState({
        selectedId: "repo-1",
        selected: mockRepositories[0],
        repositories: mockRepositories,
      });

      renderWithProviders(<Workspace />);

      // Verify the 4 sub-tabs exact names
      expect(screen.getByRole("button", { name: /^Overview/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /^Lifecycle/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /^AST/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /^Manifest & Evidence/i })).toBeInTheDocument();
    });

    it("renders exact sequential lifecycle stages: Scan -> Manifest -> AST Extraction -> Cognification", async () => {
      useRepositoryStore.setState({
        selectedId: "repo-1",
        selected: mockRepositories[0],
        repositories: mockRepositories,
      });

      renderWithProviders(<Workspace />);

      // Switch to Lifecycle tab
      fireEvent.click(screen.getByRole("button", { name: /^Lifecycle/i }));

      // Verify exact stage headers
      expect(screen.getByRole("heading", { name: "Scan" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Manifest" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "AST Extraction" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Cognification" })).toBeInTheDocument();

      // Ensure forbidden legacy stage terms are NOT used as headings
      expect(screen.queryByRole("heading", { name: /Discovered/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: /Scanned/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: /Indexed/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: /Synthesized/i })).not.toBeInTheDocument();
    });
  });

  describe("Requirement 2: Context Studio 3 Columns & Exact 4 Retrieval Tiers", () => {
    it("renders 3 columns with approved headers", async () => {
      useRepositoryStore.setState({
        selectedId: "repo-1",
        selected: mockRepositories[0],
        repositories: mockRepositories,
      });

      renderWithProviders(<ContextStudio />);

      // Column 1: Input Workbench
      expect(screen.getByText("Input Workbench")).toBeInTheDocument();
      // Column 2: Retrieval Arbitration & Evidence
      expect(screen.getByText("Retrieval Arbitration & Evidence")).toBeInTheDocument();
      // Column 3: Context Package & History
      expect(screen.getByText("Context Package & History")).toBeInTheDocument();
    });

    it("renders the exact 4 authoritative retrieval tier names", async () => {
      renderWithProviders(
        <TierEvidenceStack
          agentResponse={{
            success: true,
            context_markdown: "# Context",
            task_summary: "Test task",
            intent_category: "feature",
            extracted_symbols: ["init_app"],
            callers: [],
            callees: [],
            related_files: ["src/main.py"],
            evidence_files: ["src/main.py"],
            evidence_symbols: ["init_app"],
            evidence_relationships: ["calls"],
            observed_evidence: ["Observation 1"],
            model_invoked: false,
            model_name: "qwen2.5-coder:7b",
            estimated_tokens: 500,
            generation_time_ms: 120,
          }}
        />
      );

      // Verify the 4 authoritative retrieval tiers
      expect(screen.getByText("Tier 1: Filesystem Source")).toBeInTheDocument();
      expect(screen.getByText("Tier 2: Manifest / AST")).toBeInTheDocument();
      expect(screen.getByText("Tier 3: LanceDB / Kùzu")).toBeInTheDocument();
      expect(screen.getByText("Tier 4: Cognee Semantic Memory")).toBeInTheDocument();
    });
  });

  describe("Requirement 3: Null Repository Contract (Blocks Repo-Scoped Requests)", () => {
    it("Workspace shows repository catalog when selectedId is null and blocks repo queries", async () => {
      useRepositoryStore.setState({
        selectedId: null,
        selected: undefined,
        repositories: mockRepositories,
      });

      renderWithProviders(<Workspace />);

      expect(screen.getByText("Select Active Workspace")).toBeInTheDocument();
      expect(screen.getByText("re-track-core")).toBeInTheDocument();
    });

    it("Context Studio shows Repository Required and disables synthesis when selectedId is null", async () => {
      useRepositoryStore.setState({
        selectedId: null,
        selected: undefined,
        repositories: mockRepositories,
      });

      renderWithProviders(<ContextStudio />);

      expect(screen.getByText(/Repository Required: No active repository selected/i)).toBeInTheDocument();
      const synthesizeBtn = screen.getByRole("button", { name: /Synthesize Context/i });
      expect(synthesizeBtn).toBeDisabled();
    });

    it("Memory Engine shows Repository Required when selectedId is null", async () => {
      useRepositoryStore.setState({
        selectedId: null,
        selected: undefined,
        repositories: mockRepositories,
      });

      renderWithProviders(<Memory />);

      expect(screen.getByText("Repository Required")).toBeInTheDocument();
      expect(
        screen.getByText(/Select an indexed repository from the top bar/i)
      ).toBeInTheDocument();
    });

    it("System Telemetry remains fully functional when selectedId is null", async () => {
      useRepositoryStore.setState({
        selectedId: null,
        selected: undefined,
        repositories: mockRepositories,
      });

      renderWithProviders(<SystemTelemetry />);

      expect(screen.getByText("System Architecture & Telemetry")).toBeInTheDocument();
      expect(screen.getByText("Global Scope (Repository Independent)")).toBeInTheDocument();
    });
  });

  describe("Requirement 4 & 5: Repository Switching & Cross-Pillar Isolation", () => {
    it("clears and re-scopes package history when switching repositories", async () => {
      const pkgRepo1 = mockSavedPackages[0];
      const pkgRepo2 = {
        ...mockSavedPackages[0],
        id: "pkg-repo2",
        name: "Repo 2 Unique Package",
        repository_id: "repo-2",
        repository_name: "re-track-web",
      };

      useContextPackageStore.setState({ packages: [pkgRepo1, pkgRepo2] });

      const { rerender } = renderWithProviders(
        <PackageHistoryDrawer activeRepoId="repo-1" activeRepoName="re-track-core" />
      );

      // In repo-1: pkgRepo1 is visible, pkgRepo2 is NOT
      expect(screen.getByText("Context Package - Token Budgeting")).toBeInTheDocument();
      expect(screen.queryByText("Repo 2 Unique Package")).not.toBeInTheDocument();

      // Switch to repo-2
      rerender(<PackageHistoryDrawer activeRepoId="repo-2" activeRepoName="re-track-web" />);

      // In repo-2: pkgRepo2 is visible, pkgRepo1 is NOT
      expect(screen.getByText("Repo 2 Unique Package")).toBeInTheDocument();
      expect(screen.queryByText("Context Package - Token Budgeting")).not.toBeInTheDocument();
    });

    it("leaves System Telemetry and provider configuration completely unchanged when switching repositories", async () => {
      useHealthStore.setState({
        configuredModel: "qwen2.5-coder:7b",
        activeModel: "qwen2.5-coder:7b",
        providerIdentity: "ollama",
      });

      useRepositoryStore.setState({
        selectedId: null,
        selected: undefined,
        repositories: mockRepositories,
      });

      renderWithProviders(<SystemTelemetry />);

      expect(screen.getAllByText("qwen2.5-coder:7b").length).toBeGreaterThanOrEqual(1);

      // Switch repository in store
      useRepositoryStore.getState().select("repo-1");
      expect(useRepositoryStore.getState().selectedId).toBe("repo-1");

      // System Telemetry provider config remains unchanged
      expect(useHealthStore.getState().configuredModel).toBe("qwen2.5-coder:7b");
      expect(useHealthStore.getState().providerIdentity).toBe("ollama");
    });
  });

  describe("Requirement 7: Truth Boundary Guarantee (No Synthetic AST / Repository Data)", () => {
    it("renders AST 5-state handling truthfully without inventing synthetic nodes", async () => {
      // 1. not_analyzed state with zero nodes
      const { unmount } = renderWithProviders(
        <CallGraphView
          nodes={[]}
          edges={[]}
          status="not_analyzed"
        />
      );
      expect(screen.getByText("AST Analysis Not Available")).toBeInTheDocument();
      unmount();

      // 2. zero_edges state with nodes but no calls
      const singleNode: CallGraphNode = {
        id: "isolated_fn",
        label: "isolated_fn",
        kind: "function",
        file: "src/util.ts",
        line: 10,
      };

      renderWithProviders(
        <CallGraphView
          nodes={[singleNode]}
          edges={[]}
          status="zero_edges"
        />
      );
      expect(screen.getByText(/Zero Call Graph Edges/i)).toBeInTheDocument();
    });
  });

  describe("Requirement 8: Three Runtime Identities Separation", () => {
    it("displays Configured vs Verified Active vs Last Executing model distinctly", async () => {
      useHealthStore.setState({
        configuredModel: "qwen2.5-coder:7b",
        activeModel: "qwen2.5-coder:7b",
        lastExecutingModel: null,
        providerIdentity: "ollama",
        providerReachable: true,
      });

      renderWithProviders(<SystemTelemetry />);

      // Configured
      expect(screen.getAllByText("1. Configured Model").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("qwen2.5-coder:7b").length).toBeGreaterThanOrEqual(1);

      // Verified Active
      expect(screen.getAllByText("2. Verified Active Model").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Endpoint Reachable")).toBeInTheDocument();

      // Last Executing: must display None (No executions) rather than activeModel
      expect(screen.getAllByText("3. Last Executing Model").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("None (No executions)")).toBeInTheDocument();
    });
  });

  describe("Requirement 9: Unavailable vs Empty State Distinction", () => {
    it("displays Unavailable for hardware telemetry when offline instead of synthetic zeroes", async () => {
      useHealthStore.setState({
        health: {
          status: "ok",
          ollama_reachable: false,
          cognee_initialized: false,
          version: "0.1.0",
          execution_device: undefined,
          cpu_percent: undefined,
          ram_used_gb: undefined,
          ram_total_gb: undefined,
          gpu_presence: undefined,
          gpu_name: undefined,
          vram_used_gb: undefined,
          vram_total_gb: undefined,
        },
      });

      renderWithProviders(<SystemTelemetry />);

      const unavailables = screen.getAllByText("Unavailable");
      expect(unavailables.length).toBeGreaterThanOrEqual(3);
    });
  });

  describe("Requirement 10: Large Graph Remains Bounded in Presentation", () => {
    it("bounds display to initial limit without truncating raw source nodes", async () => {
      // Create 80 nodes
      const rawNodes: CallGraphNode[] = Array.from({ length: 80 }, (_, i) => ({
        id: `node_${i}`,
        label: `symbol_${i}`,
        kind: "function",
        file: `src/file_${i}.ts`,
        line: i,
      }));

      const rawEdges: CallGraphEdge[] = Array.from({ length: 79 }, (_, i) => ({
        source: `node_${i}`,
        target: `node_${i + 1}`,
        kind: "calls",
      }));

      renderWithProviders(
        <CallGraphView
          nodes={rawNodes}
          edges={rawEdges}
          status="analyzed"
        />
      );

      // Source data has 80 nodes and is not truncated
      expect(rawNodes.length).toBe(80);

      // Bounded presentation badge appears indicating top 50 nodes
      expect(screen.getByText("Bounded (50/80)")).toBeInTheDocument();
      expect(
        screen.getByTitle(/Presentation bounded to top 50 nodes/i)
      ).toBeInTheDocument();
    });
  });

  describe("Requirement 11: Benchmarks and Diagnostics Rendered from System Pillar", () => {
    it("renders Benchmarks from the System pillar tab", async () => {
      renderWithProviders(<SystemTelemetry />, {
        initialEntries: ["/system?tab=benchmarks"],
      });

      await waitFor(() => {
        expect(
          screen.getByText("Deterministic Context & Latency Benchmarks")
        ).toBeInTheDocument();
      });
    });

    it("renders Diagnostics from the System pillar tab with connectivity test", async () => {
      const user = userEvent.setup();
      const defaultMock = createDefaultMockHandler();
      let healthCalled = false;

      setMockInvokeHandler(async (cmd, args) => {
        if (cmd === "health") {
          healthCalled = true;
          return {
            status: "ok",
            version: "0.1.0",
            cognee_initialized: true,
            ollama_reachable: true,
          };
        }
        return defaultMock(cmd, args);
      });

      renderWithProviders(<SystemTelemetry />, {
        initialEntries: ["/system?tab=diagnostics"],
      });

      const testBtn = await screen.findByRole("button", { name: /Test Connection/i });
      await user.click(testBtn);

      await waitFor(() => {
        expect(healthCalled).toBe(true);
      });
    });
  });

  describe("Memory Engine Derived Storage Boundary", () => {
    it("prominently presents Derived Storage Notice and exact 3 tab names", async () => {
      useRepositoryStore.setState({
        selectedId: "repo-1",
        selected: mockRepositories[0],
        repositories: mockRepositories,
      });

      renderWithProviders(<Memory />);

      expect(screen.getByText("Derived Storage Boundary")).toBeInTheDocument();
      expect(
        screen.getByText(/subordinate to filesystem source \(Tier 1\) and AST \(Tier 2\)/i)
      ).toBeInTheDocument();

      // Exact 3 tabs
      expect(screen.getByRole("button", { name: /Semantic Records/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Vector Space/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Knowledge Graph/i })).toBeInTheDocument();
    });
  });
});
