import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Routes, Route } from "react-router-dom";
import Workspace from "@/pages/Workspace";
import {
  renderWithProviders,
  resetAllStores,
  setMockInvokeHandler,
  mockRepositories,
} from "@/test/test-utils";
import { useRepositoryStore } from "@/stores/repository-store";
import type { Repository } from "@/types/repository";

function renderExplorer() {
  return renderWithProviders(
    <Routes>
      <Route path="/workspace" element={<Workspace />} />
    </Routes>,
    {
      initialEntries: ["/workspace?repo=repo-1&tab=ast"],
    }
  );
}

describe("Journey E — AST Call Graph Topology & 5-State Handling", () => {
  beforeEach(() => {
    resetAllStores();
    setMockInvokeHandler(null);
  });

  it("renders AST Analysis Not Available when repository is not analyzed", async () => {
    const unanalyzedRepo: Repository = {
      ...mockRepositories[0],
      call_graph_status: "not_analyzed",
      call_graph_nodes: [],
      call_graph_edges: [],
    };
    useRepositoryStore.setState({
      repositories: [unanalyzedRepo],
      selectedId: "repo-1",
      selected: unanalyzedRepo,
    });

    renderExplorer();

    await waitFor(() => {
      expect(screen.getByText("AST Analysis Not Available")).toBeInTheDocument();
    });
  });

  it("renders Analyzing AST Call Graph spinner when indexing is in progress", async () => {
    const analyzingRepo: Repository = {
      ...mockRepositories[0],
      call_graph_status: "analyzing",
      status: "indexing",
      call_graph_nodes: [],
      call_graph_edges: [],
    };
    useRepositoryStore.setState({
      repositories: [analyzingRepo],
      selectedId: "repo-1",
      selected: analyzingRepo,
    });

    renderExplorer();

    await waitFor(() => {
      expect(screen.getByText("Analyzing AST Call Graph")).toBeInTheDocument();
    });
  });

  it("renders Zero Call Graph Edges warning banner when nodes have no links", async () => {
    const singleFileRepo: Repository = {
      ...mockRepositories[0],
      call_graph_status: "zero_edges",
      call_graph_nodes: [
        { id: "standalone", label: "main", file: "main.py", kind: "function", line: 1 },
      ],
      call_graph_edges: [],
    };
    useRepositoryStore.setState({
      repositories: [singleFileRepo],
      selectedId: "repo-1",
      selected: singleFileRepo,
    });

    renderExplorer();

    await waitFor(() => {
      expect(screen.getByText(/Zero Call Graph Edges/i)).toBeInTheDocument();
    });
  });

  it("renders AST Analysis Failed error state when analysis failed", async () => {
    const failedRepo: Repository = {
      ...mockRepositories[0],
      call_graph_status: "failed",
      call_graph_error: "Tree-sitter syntax error parsing src/invalid.rs",
      call_graph_nodes: [],
      call_graph_edges: [],
    };
    useRepositoryStore.setState({
      repositories: [failedRepo],
      selectedId: "repo-1",
      selected: failedRepo,
    });

    renderExplorer();

    await waitFor(() => {
      expect(screen.getByText("AST Analysis Failed")).toBeInTheDocument();
      expect(screen.getByText(/Tree-sitter syntax error/i)).toBeInTheDocument();
    });
  });

  it("renders interactive CallGraphView with nodes, filter controls, and bounded view", async () => {
    const user = userEvent.setup();
    useRepositoryStore.setState({
      repositories: mockRepositories,
      selectedId: "repo-1",
      selected: mockRepositories[0],
    });

    renderExplorer();

    // Wait for CallGraphView to render with search input
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Search symbols/i)).toBeInTheDocument();
    });

    // Verify kind filter buttons exist
    expect(screen.getByRole("button", { name: "class" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "function" })).toBeInTheDocument();

    // Type in search filter
    const searchInput = screen.getByPlaceholderText(/Search symbols/i);
    await user.type(searchInput, "generate_context");

    expect(searchInput).toHaveValue("generate_context");
  });
});
