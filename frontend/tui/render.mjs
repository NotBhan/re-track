/* eslint-disable no-control-regex -- ANSI escape sequences are measured and stripped, never matched as text */
/**
 * RE:Track TUI presentation model and frame composition.
 *
 * Two pure stages:
 *   buildModel(app, {cols, rows, spinnerFrame}) → presentation model (plain text + cells)
 *   composeFrame(model, {styler})               → the frame string to write
 *
 * No backend access, no timers, no terminal writes. Every value comes from a
 * backend response; missing data renders as `unavailable`/`none`/`never`.
 */

import { layoutFor, padTo, padStart, truncate, windowStart, wrapToWidth, clamp } from "./layout.mjs";
import { HELP_GROUPS, footerHints } from "./keymap.mjs";
import { formatMarkdown } from "./markdown.mjs";
import {
  GLYPH,
  SPINNER_FRAMES,
  UNAVAILABLE,
  confidenceTier,
  evidenceStateLabel,
  formatBytes,
  formatCount,
  formatDuration,
  formatRelativeTime,
  statusStyle,
  summarizeList,
} from "./theme.mjs";

export const HELP_NOTES = Object.freeze([
  "Indexing and synthesis cannot be cancelled: the backend exposes no cancel endpoint.",
  "Provider switching and settings changes are available in the desktop GUI only.",
  "Code search is unavailable over HTTP; the Code view shows AST metadata only.",
  "All values shown come from backend responses; nothing is estimated.",
]);

const VIEW_TITLES = Object.freeze({
  repositories: "Repositories",
  code: "Code",
  context: "Context",
  system: "System",
});

const identity = (text) => text;
const ANSI = /\u001b\[[0-9;]*m/g;
const ANSI_AT = /^\u001b\[[0-9;]*m/;
const ANSI_ANY = /\u001b\[[0-9;]*m/;
const plainLength = (text) => String(text ?? "").replace(ANSI, "").length;

/**
 * Truncate by *visible* width, preserving the ANSI escapes that precede the
 * cut. Styled strings must never be measured with raw string length.
 */
function truncateVisible(text, width, ellipsis = "…") {
  const value = String(text ?? "");
  if (width <= 0) return "";
  if (plainLength(value) <= width) return value;
  const keep = Math.max(0, width - ellipsis.length);
  let output = "";
  let visible = 0;
  let index = 0;
  while (index < value.length && visible < keep) {
    const escape = value.slice(index).match(ANSI_AT);
    if (escape) {
      output += escape[0];
      index += escape[0].length;
      continue;
    }
    output += value[index];
    index += 1;
    visible += 1;
  }
  // Only close a style when the truncated text actually carried one; plain
  // (NO_COLOR) output must stay completely free of escape sequences.
  return ANSI_ANY.test(value) ? `${output}${ellipsis}\u001b[0m` : `${output}${ellipsis}`;
}

/** Pad a possibly-styled string to an exact visible width. */
function fit(styled, width) {
  const truncated = truncateVisible(styled, width);
  return truncated + " ".repeat(Math.max(0, width - plainLength(truncated)));
}

/**
 * A live text field: the value with a visible cursor. Styling inverts the cell
 * under the cursor; without styling (NO_COLOR) the caret glyph keeps the
 * insertion point visible, because no escape sequence may be emitted.
 */
function editorText(value, cursor, styler, placeholder = "") {
  const text = String(value ?? "");
  if (text.length === 0) {
    const head = placeholder ? placeholder[0] : " ";
    const tail = placeholder.slice(1);
    return styler.enabled ? `${styler.inverse(head)}${styler.dim(tail)}` : `${GLYPH.caret}${tail}`;
  }
  const at = clamp(cursor ?? text.length, 0, text.length);
  const before = text.slice(0, at);
  const cell = text[at] ?? " ";
  const after = text.slice(at + 1);
  if (styler.enabled) return `${before}${styler.inverse(cell)}${after}`;
  return `${before}${GLYPH.caret}${cell === " " ? "" : cell}${after}`;
}

/** A form field line: the focused field owns the cursor and the pointer marker. */
function fieldLine(label, value, cursor, focused, placeholder) {
  const text = String(value ?? "");
  if (!focused) return { text: `  ${label}: ${text || placeholder}`, style: "dim" };
  return { prefix: `${GLYPH.pointer} ${label}: `, value: text, cursor: cursor ?? text.length, placeholder };
}

function cell(text, style = identity) {
  return { text: String(text ?? ""), style };
}

function joinCells(cells, styler, width) {
  let remaining = Math.max(0, width);
  let output = "";
  for (const item of cells) {
    if (remaining <= 0) break;
    // Cells may already carry ANSI escapes (pre-composed pane lines), so every
    // measurement here is by visible width, never by raw string length.
    const prepared = plainLength(item.text) > remaining ? truncateVisible(item.text, remaining) : item.text;
    const styled = item.style(prepared, styler);
    const emitted = plainLength(styled) > remaining ? truncateVisible(styled, remaining) : styled;
    output += emitted;
    remaining -= plainLength(emitted);
  }
  return output + " ".repeat(Math.max(0, remaining));
}

/* ------------------------------ build model ------------------------------ */

export function buildModel(app, options = {}) {
  const state = app.getState();
  const cols = Math.max(20, options.cols ?? 80);
  const rows = Math.max(6, options.rows ?? 24);
  const spinnerFrame = Math.max(0, options.spinnerFrame ?? 0);
  const layout = layoutFor({ cols, rows, operation: Boolean(state.operation) });

  const model = {
    cols,
    rows,
    layout,
    spinner: SPINNER_FRAMES[spinnerFrame % SPINNER_FRAMES.length],
    tooSmall: layout.tooSmall,
    shortcut: null,
    header: buildHeader(app, state),
    rail: buildRail(state, layout),
    view: null,
    operation: buildOperation(state, layout, spinnerFrame),
    footer: buildFooter(state, layout, cols),
    overlay: state.overlay ? buildOverlay(state, layout, cols) : null,
    scrollMax: { inspector: 0, system: 0, viewer: 0 },
  };

  model.header.noticeText = state.notice
    ? truncate(state.notice.message, Math.max(12, Math.floor(cols * 0.42)))
    : null;

  model.view = buildView(app, state, layout);
  model.scrollMax.inspector = Math.max(0, model.view.inspector.lines.length - (model.layout.bodyRows - 2));
  model.scrollMax.system = Math.max(0, model.view.list.rows.length - model.view.list.height);
  model.scrollMax.viewer = model.overlay && (model.overlay.kind === "viewPackage" || model.overlay.kind === "help")
    ? Math.max(0, model.overlay.lines.length - (model.layout.bodyRows - 2))
    : 0;

  return model;
}

function buildHeader(app, state) {
  const repo = app.selectedRepository();
  const backend = state.error
    ? { label: "backend unavailable", level: "error" }
    : state.degraded.length > 0
      ? { label: `degraded (${state.degraded.length})`, level: "warn" }
      : { label: state.health?.status ?? "unknown", level: "ok" };
  return {
    repo: repo ? repo.name : "no repository selected",
    repoStatus: repo?.status ?? null,
    backend,
    notice: state.notice,
    noticeText: null,
  };
}

function buildRail(state, layout) {
  return {
    focused: state.focus === "rail",
    items: [
      { key: "repositories", label: "Repositories", count: state.repositories.length, active: state.view === "repositories" },
      { key: "code", label: "Code", count: null, active: state.view === "code" },
      { key: "context", label: "Context", count: state.packages.length, active: state.view === "context" },
      { key: "system", label: "System", count: null, active: state.view === "system" },
    ],
    width: layout.railWidth,
  };
}

function buildView(app, state, layout) {
  const title = VIEW_TITLES[state.view];
  const list = {
    title,
    subtitle: buildSubtitle(app, state),
    rows: [],
    cursor: state.cursors[state.view] ?? 0,
    offset: 0,
    offsetMode: false,
    focused: state.focus === "list",
    filterActive: state.filterActive,
    filter: state.filter,
    filterCursor: state.filterCursor ?? (state.filter ?? "").length,
    empty: null,
    height: Math.max(1, layout.bodyRows - 2),
    width: layout.listWidth,
  };
  const inspector = {
    title: "Inspector",
    lines: [],
    scroll: state.scroll.inspector ?? 0,
    focused: state.focus === "inspector",
    open: state.inspectorOpen,
    width: layout.sideBySide ? layout.inspectorWidth : layout.listWidth + layout.inspectorWidth + 1,
  };

  if (state.view === "repositories") buildRepositories(app, state, layout, list, inspector);
  else if (state.view === "code") buildCode(app, state, layout, list, inspector);
  else if (state.view === "context") buildContext(app, state, layout, list, inspector);
  else buildSystem(app, state, layout, list, inspector);

  return {
    key: state.view,
    title,
    banner: buildBanner(app, state),
    list,
    inspector,
    // System is one continuous read-only report: a second pane would sit empty.
    fullWidth: state.view === "system",
  };
}

function buildSubtitle(app, state) {
  if (state.view === "repositories") {
    const total = state.repositories.length;
    if (total === 0) return state.loading ? "loading" : null;
    const visible = app.visibleRepositories().length;
    return state.filter ? `${visible} of ${total} matching “${state.filter}”` : `${total} tracked`;
  }
  if (state.view === "code") {
    const repo = app.selectedRepository();
    return repo ? `${repo.name} · call graph ${repo.call_graph_status ?? "not_analyzed"}` : null;
  }
  if (state.view === "context") {
    const budget = `${Math.round(state.tokenBudget / 1024)}K budget`;
    const graph = state.includeGraph ? "AST graph on" : "AST graph off";
    const source = state.prompts.source ? `suggestions ${state.prompts.source}` : null;
    return [source, budget, graph].filter(Boolean).join(" · ");
  }
  return state.health?.status ? `backend ${state.health.status}` : null;
}

function buildBanner(app, state) {
  if (state.view === "context" && state.prompts.state === "error") {
    return { level: "warn", lines: [`suggested tasks unavailable: ${state.prompts.error}`] };
  }
  if (state.view === "repositories" && state.contextError) {
    return { level: "error", lines: [`last synthesis failed: ${state.contextError}`] };
  }
  if (state.view === "code") {
    const repo = app.selectedRepository();
    if (!repo) return null;
    const status = repo.call_graph_status ?? "not_analyzed";
    if (status === "failed") {
      return { level: "error", lines: [`call graph failed: ${repo.call_graph_error ?? "no error detail"}`] };
    }
    if (status === "analyzing") {
      return { level: "warn", lines: ["call graph analyzing · extraction runs during indexing"] };
    }
    if (status === "not_analyzed") {
      return { level: "warn", lines: ["call graph not analyzed · run indexing (i in Repositories) to extract it"] };
    }
    if (status === "zero_edges") {
      return { level: "warn", lines: ["call graph analyzed · no deterministic call edges found"] };
    }
  }
  return null;
}

function buildRepositories(app, state, layout, list, inspector) {
  const repos = app.visibleRepositories();
  if (state.repositories.length === 0) {
    list.empty = state.loading ? "loading repositories…" : "no repositories tracked · press a to add one";
  } else if (repos.length === 0) {
    list.empty = `no repository matches “${state.filter}”`;
  }

  const showFiles = layout.listWidth >= 44;
  const showLanguages = layout.listWidth >= 60;
  const showIndexed = layout.listWidth >= 78;
  const nameWidth = Math.max(
    12,
    layout.listWidth - 4 - (showFiles ? 6 : 0) - (showLanguages ? 16 : 0) - (showIndexed ? 9 : 0) - 12
  );

  for (const repo of repos) {
    const cells = [cell(truncate(repo.name, nameWidth), (text, styler) => styler.bold(text))];
    if (showFiles) cells.push(cell(` ${padStart(formatCount(repo.file_count), 5)}`, (text, styler) => styler.dim(text)));
    if (showLanguages) cells.push(cell(` ${truncate(summarizeList(repo.languages, 2), 14)}`, (text, styler) => styler.dim(text)));
    if (showIndexed) cells.push(cell(` ${truncate(formatRelativeTime(repo.indexed_at, state.nowMs), 8)}`, (text, styler) => styler.dim(text)));
    cells.push(cell(` ${String(repo.status ?? "unknown")}`, (text, styler) => ` ${statusStyle(styler, repo.status)}`));
    list.rows.push({ id: repo.id, cells });
  }

  const repo = app.selectedRepository();
  if (!repo) {
    inspector.title = "Repository";
    inspector.lines = [cell("No repository selected."), cell(""), cell("Press a to add one.")];
    return;
  }
  inspector.title = repo.name;
  const row = (label, value) =>
    cell(
      joinCells(
        [cell(padTo(label, 17), (text, styler) => styler.dim(text)), cell(value === null || value === undefined || value === "" ? UNAVAILABLE : String(value))],
        { dim: identity },
        Math.max(20, inspector.width - 2)
      )
    );
  inspector.lines = [
    row("path", repo.local_path),
    row("source", repo.source_type === "github" ? repo.source_url ?? UNAVAILABLE : "local directory"),
    row("branch", repo.branch),
    row("commit", repo.commit_hash ? String(repo.commit_hash).slice(0, 12) : null),
    row("status", repo.status),
    row("files", formatCount(repo.file_count)),
    row("size", formatBytes(repo.size_bytes)),
    row("languages", summarizeList(repo.languages, 4)),
    row("frameworks", summarizeList(repo.frameworks, 4)),
    row("architecture", repo.architecture),
    row("entry points", summarizeList(repo.entry_points, 3)),
    row("components", summarizeList(repo.components, 4)),
    row("call graph", `${repo.call_graph_status ?? "not_analyzed"} · ${formatCount((repo.call_graph_nodes ?? []).length)} nodes · ${formatCount((repo.call_graph_edges ?? []).length)} edges`),
    row("indexed", repo.indexed_at ? formatRelativeTime(repo.indexed_at, state.nowMs) : "never"),
    row("error", repo.error_message ?? null),
    cell(""),
    cell("automatic updates: not available", (text, styler) => styler.dim(text)),
    cell("cancellation: not supported by the backend", (text, styler) => styler.dim(text)),
  ];
  if (repo.summary) {
    inspector.lines.push(cell(""), cell("summary", (text, styler) => styler.dim(text)));
    for (const piece of wrapToWidth(repo.summary, Math.max(20, inspector.width - 2))) inspector.lines.push(cell(piece));
  }
}

function buildCode(app, state, layout, list, inspector) {
  const repo = app.selectedRepository();
  if (!repo) {
    list.empty = "no repository selected";
    inspector.lines = [cell("Select a repository in the Repositories view.")];
    return;
  }
  const components = Array.isArray(repo.components) ? repo.components : [];
  const entryPoints = Array.isArray(repo.entry_points) ? repo.entry_points : [];
  const symbols = app.codeSymbols();

  list.rows = [
    ...components.map((name) => ({
      group: "components",
      cells: [cell(truncate(name, layout.listWidth - 16), (text, styler) => styler.bold(text)), cell(" component", (text, styler) => styler.dim(text))],
    })),
    ...entryPoints.map((name) => ({
      group: "entry points",
      cells: [cell(truncate(name, layout.listWidth - 18), identity), cell(" entry point", (text, styler) => styler.dim(text))],
    })),
    ...symbols.map((node, index) => ({
      group: "symbols",
      node,
      cells: [
        cell(truncate(node.label ?? node.id ?? `symbol ${index + 1}`, layout.listWidth - 34), (text, styler) => styler.bold(text)),
        cell(` ${truncate(node.kind ?? "symbol", 10)}`, (text, styler) => styler.dim(text)),
        cell(` ${truncate(node.file ?? UNAVAILABLE, 20)}`, (text, styler) => styler.dim(text)),
      ],
    })),
  ];
  if (list.rows.length === 0) list.empty = "no components, entry points or symbols indexed yet";

  const selected = list.rows[clamp(list.cursor, 0, Math.max(0, list.rows.length - 1))];
  if (!selected) {
    inspector.lines = [cell("Nothing selected.")];
    return;
  }
  if (selected.group !== "symbols") {
    inspector.title = selected.group === "components" ? "Component" : "Entry point";
    inspector.lines = [
      cell(truncate(selected.cells[0].text, Math.max(20, inspector.width - 2)), (text, styler) => styler.bold(text)),
      cell(""),
      cell("Derived from the repository summary written during indexing.", (text, styler) => styler.dim(text)),
    ];
    return;
  }

  const node = selected.node;
  const edges = Array.isArray(repo.call_graph_edges) ? repo.call_graph_edges : [];
  const byId = new Map(symbols.map((item) => [item.id, item]));
  const label = (id) => byId.get(id)?.label ?? id;
  const callers = edges.filter((edge) => edge.target === node?.id).map((edge) => label(edge.source));
  const callees = edges.filter((edge) => edge.source === node?.id).map((edge) => label(edge.target));

  inspector.title = "Symbol";
  inspector.lines = [
    cell(node?.label ?? UNAVAILABLE, (text, styler) => styler.bold(text)),
    cell(`${node?.kind ?? "symbol"} · ${node?.file ?? UNAVAILABLE}${node?.line ? `:${node.line}` : ""}`, (text, styler) => styler.dim(text)),
    cell(""),
    cell(`callers (${callers.length})`, (text, styler) => styler.dim(text)),
    ...(callers.length ? callers.map((name) => cell(truncate(name, Math.max(10, inspector.width - 2)))) : [cell("none detected", (text, styler) => styler.dim(text))]),
    cell(""),
    cell(`callees (${callees.length})`, (text, styler) => styler.dim(text)),
    ...(callees.length ? callees.map((name) => cell(truncate(name, Math.max(10, inspector.width - 2)))) : [cell("none detected", (text, styler) => styler.dim(text))]),
    cell(""),
    cell("Relationships come from deterministic AST edges reported by the backend.", (text, styler) => styler.dim(text)),
    cell("Call-graph extraction runs during indexing.", (text, styler) => styler.dim(text)),
  ];
}

function buildContext(app, state, layout, list, inspector) {
  const repo = app.selectedRepository();
  const rows = app.contextRows();
  if (!repo) {
    list.empty = "no repository selected";
    inspector.lines = [cell("Select a repository in the Repositories view.")];
    return;
  }

  list.rows = rows.map((row) =>
    row.kind === "suggestion"
      ? {
          kind: "suggestion",
          cells: [cell(truncate(row.label ?? row.prompt, layout.listWidth - 16), (text, styler) => styler.bold(text)), cell(" task", (text, styler) => styler.dim(text))],
        }
      : {
          kind: "package",
          id: row.id,
          cells: [
            cell(truncate(row.label ?? row.id, layout.listWidth - 24), identity),
            cell(` ${truncate(formatCount(row.tokens), 8)} tok`, (text, styler) => styler.dim(text)),
            cell(" pkg", (text, styler) => styler.dim(text)),
          ],
        }
  );
  if (list.rows.length === 0) {
    list.empty = state.prompts.state === "loading" ? "loading suggested tasks…" : "no suggestions or packages · press n for a task";
  }

  if (state.operation?.kind === "synthesis") {
    inspector.title = "Synthesizing";
    inspector.lines = [
      cell("Generating context", (text, styler) => styler.bold(text)),
      cell(""),
      cell(`elapsed ${formatDuration(state.nowMs - state.operation.startedAt)}`, (text, styler) => styler.dim(text)),
      cell(`runtime: ${state.operation.runtimeState ?? "unknown"}`, (text, styler) => styler.dim(text)),
      cell(""),
      cell("No token-level progress is exposed by the provider.", (text, styler) => styler.dim(text)),
      cell("Cancellation is not supported by the backend.", (text, styler) => styler.dim(text)),
    ];
    return;
  }

  if (state.contextError && !state.context) {
    inspector.title = "Synthesis failed";
    inspector.lines = [cell(state.contextError, (text, styler) => styler.err(text)), cell(""), cell("Press n to try another task, or r to reconcile.", (text, styler) => styler.dim(text))];
    return;
  }

  const result = state.context;
  if (!result) {
    const selected = app.selectedContextRow();
    inspector.title = "Evidence & output";
    if (!selected) {
      inspector.lines = [
        cell("No task or package selected.", (text, styler) => styler.dim(text)),
        cell("Press n to describe a task, or select a suggestion with ↑↓.", (text, styler) => styler.dim(text)),
      ];
      return;
    }
    if (selected.kind === "suggestion") {
      inspector.lines = [
        cell("Suggested task", (text, styler) => styler.dim(text)),
        cell(selected.label ?? "", (text, styler) => styler.bold(text)),
        cell(""),
        ...wrapToWidth(selected.prompt ?? "", Math.max(20, inspector.width - 2)).map((piece) => cell(piece)),
        cell(""),
        cell(`source: ${state.prompts.source ?? UNAVAILABLE}`, (text, styler) => styler.dim(text)),
        cell("Press enter to prefill a new task with this prompt.", (text, styler) => styler.dim(text)),
      ];
      return;
    }
    const pkg = state.packages.find((item) => item.id === selected.id);
    inspector.lines = [
      cell(pkg?.name ?? selected.label, (text, styler) => styler.bold(text)),
      cell(`${formatCount(pkg?.token_estimate)} tokens · saved ${formatRelativeTime(pkg?.created_at, state.nowMs)}`, (text, styler) => styler.dim(text)),
      cell(""),
      ...wrapToWidth(pkg?.task ?? "", Math.max(20, inspector.width - 2)).map((piece) => cell(piece)),
      cell(""),
      cell("Press enter to open the saved markdown.", (text, styler) => styler.dim(text)),
    ];
    return;
  }

  const tier = confidenceTier(result.evidence_confidence);
  const strength = typeof result.evidence_score === "number" ? `${Math.round(clamp(result.evidence_score, 0, 1) * 100)}%` : UNAVAILABLE;
  const lines = [
    cell(`task: ${result.task_summary ?? UNAVAILABLE}`, (text, styler) => styler.bold(text)),
    cell(`intent: ${result.intent_category ?? UNAVAILABLE}`, (text, styler) => styler.dim(text)),
    cell(""),
    cell("Evidence", (text, styler) => styler.dim(text)),
    cell(`state: ${evidenceStateLabel(result.evidence_state)}   strength: ${strength}`),
    cell(`confidence: ${tier.label}`),
    cell(`  ${tier.detail}`, (text, styler) => styler.dim(text)),
    cell(""),
    cell(`symbols (${(result.extracted_symbols ?? []).length}): ${summarizeList(result.extracted_symbols, 4)}`),
    cell(`callers (${(result.callers ?? []).length}): ${summarizeList(result.callers, 3)}`),
    cell(`callees (${(result.callees ?? []).length}): ${summarizeList(result.callees, 3)}`),
    cell(`files (${(result.related_files ?? []).length}): ${summarizeList(result.related_files, 3)}`),
  ];

  if (result.abstained) {
    lines.push(cell(""), cell("engine abstained from unsupported claims", (text, styler) => styler.warn(text)));
    for (const piece of wrapToWidth(result.abstention_reason ?? "", Math.max(20, inspector.width - 2))) lines.push(cell(piece, (text, styler) => styler.dim(text)));
  }
  if (Array.isArray(result.missing_evidence) && result.missing_evidence.length > 0) {
    lines.push(cell(""), cell("missing evidence", (text, styler) => styler.dim(text)));
    for (const item of result.missing_evidence.slice(0, 4)) {
      for (const piece of wrapToWidth(`· ${item}`, Math.max(20, inspector.width - 2))) lines.push(cell(piece, (text, styler) => styler.dim(text)));
    }
  }

  lines.push(cell(""));
  lines.push(cell(`model: ${result.model_name ?? UNAVAILABLE} · invoked: ${result.model_invoked ? "yes" : "no"}${result.fallback_used ? " (deterministic fallback)" : ""}`, (text, styler) => styler.dim(text)));
  lines.push(cell(`inference status: ${result.inference_status ?? UNAVAILABLE}`, (text, styler) => styler.dim(text)));
  const phases = [
    ["retrieval", result.retrieval_time_ms],
    ["ranking", result.ranking_time_ms],
    ["synthesis", result.synthesis_time_ms],
    ["inference", result.inference_time_ms],
  ].filter(([, value]) => typeof value === "number" && value > 0);
  if (phases.length > 0) {
    lines.push(cell(`phases: ${phases.map(([name, value]) => `${name} ${formatDuration(value)}`).join(" · ")}`, (text, styler) => styler.dim(text)));
  }
  lines.push(cell(`tokens: ${formatCount(result.estimated_tokens)} · generation ${formatDuration(result.generation_time_ms)}`, (text, styler) => styler.dim(text)));
  lines.push(cell(""));
  lines.push(cell(`output · ${state.markdownView === "rendered" ? "rendered" : "raw"} (m toggles)`, (text, styler) => styler.dim(text)));

  const markdownLines = formatMarkdown(result.context_markdown ?? "", {
    rendered: state.markdownView === "rendered",
    width: Math.max(20, inspector.width - 2),
  });
  for (const piece of markdownLines) lines.push(cell(piece));

  inspector.title = "Evidence & output";
  inspector.lines = lines;
}

function buildSystem(app, state, layout, list, inspector) {
  const health = state.health ?? {};
  const status = state.status ?? {};
  const provider = state.providerStatus ?? {};
  const memory = state.memoryStats ?? {};
  const detailed = state.detailedHealth ?? {};
  const rows = [];
  const section = (title) => rows.push({ section: title });
  const entry = (label, value) => rows.push({ label, value });

  section("Provider");
  entry("identity", provider.provider ?? health.provider_identity ?? status.llm_provider);
  entry("reachable", provider.is_reachable ?? health.provider_reachable);
  entry("health state", provider.health_state ?? health.provider_health_state);
  entry("endpoint", provider.base_url ?? health.provider_base_url ?? status.llm_endpoint);
  entry("configured model", health.configured_model ?? status.configured_model);
  entry("verified active", health.active_model ?? status.active_model ?? "none verified");
  entry("embedding state", health.embedding_state);
  entry("embedding model", health.embedding_model);
  entry("semantic mem state", health.semantic_memory_state);
  entry("semantic mem model", health.semantic_memory_model);

  section("Engine");
  entry("engine state", health.engine_state);
  entry("engine reason", health.engine_reason);
  entry("cognee state", health.cognee_state ?? (health.cognee_initialized ? "healthy" : "unavailable"));
  entry("mcp ready", health.mcp_server_ready);
  entry("queue / capacity", `${formatCount(health.concurrency_queue_depth)} / ${formatCount(health.concurrency_queue_capacity)}`);
  entry("available slots", health.concurrency_available_slots);

  section("Hardware");
  entry("ram", health.ram_used_gb !== undefined && health.ram_total_gb !== undefined ? `${health.ram_used_gb} / ${health.ram_total_gb} GB` : null);
  entry("cpu", health.cpu_percent !== undefined ? `${health.cpu_percent}%` : null);
  entry("gpu", health.gpu_name ?? health.gpu_presence);
  entry("vram", health.vram_total_gb !== undefined ? `${health.vram_used_gb ?? 0} / ${health.vram_total_gb} GB` : null);
  entry("execution device", health.execution_device);

  section("Counts");
  entry("repositories", state.repositories.length);
  entry("packages", state.packages.length);
  entry("recent errors", health.recent_errors_count);
  entry("cache files", health.cache_files_count);

  section("Memory (derived)");
  entry("datasets", memory.dataset_count);
  entry("total size", memory.total_size_display);
  entry("knowledge graph", memory.knowledge_graph_status);
  entry("graph nodes/edges", memory.graph_nodes !== undefined || memory.graph_edges !== undefined ? `${formatCount(memory.graph_nodes)} / ${formatCount(memory.graph_edges)}` : null);

  section("Storage");
  entry("canonical root", detailed.storage_paths?.canonical_root);
  entry("logs directory", detailed.storage_paths?.logs_directory);
  entry("cache directory", detailed.storage_paths?.cache_directory);

  section("Diagnostics");
  entry("version", health.version);
  entry("log records", Array.isArray(state.logs) ? state.logs.length : null);
  for (const record of (Array.isArray(state.logs) ? state.logs.slice(-8) : [])) {
    const when = record.timestamp ? String(record.timestamp).slice(11, 19) : "--:--:--";
    const level = String(record.level ?? record.levelname ?? "info").toLowerCase();
    const message = record.message ?? record.event ?? record.msg ?? "";
    rows.push({ log: `${when} ${level} ${message}` });
  }

  section("Limits");
  rows.push({ note: "provider switching: GUI only" });
  rows.push({ note: "settings mutation: GUI only" });
  rows.push({ note: "cancellation: not supported by the backend" });

  list.rows = rows;
  list.offsetMode = true;
  list.cursor = state.scroll.system ?? 0;
  list.empty = state.error ? "backend unavailable · press r to retry" : null;
  inspector.lines = [cell("System information is read-only.", (text, styler) => styler.dim(text))];
}

function buildOperation(state, layout, spinnerFrame) {
  if (state.operation?.kind === "indexing") {
    const op = state.operation;
    const phase = op.stageIndex && op.stageTotal ? `phase ${op.stageIndex}/${op.stageTotal}` : "indeterminate";
    const spinner = layout.compact ? "" : `${SPINNER_FRAMES[spinnerFrame % SPINNER_FRAMES.length]} `;
    return {
      level: "warn",
      text: `${spinner}indexing ${op.repoName ?? op.repoId} · ${phase} · ${op.stage ?? "working"} · elapsed ${formatDuration(state.nowMs - op.startedAt)}`,
    };
  }
  if (state.operation?.kind === "synthesis") {
    const op = state.operation;
    const spinner = layout.compact ? "" : `${SPINNER_FRAMES[spinnerFrame % SPINNER_FRAMES.length]} `;
    return {
      level: "warn",
      text: `${spinner}synthesizing · elapsed ${formatDuration(state.nowMs - op.startedAt)} · runtime ${op.runtimeState ?? "unknown"}`,
    };
  }
  if (state.lastRun) {
    const run = state.lastRun;
    const outcome =
      run.status === "indexed"
        ? `indexed ${run.repoName} · ${formatCount(run.processedFiles)}/${formatCount(run.totalFiles)} files`
        : `indexing failed · ${run.repoName} · ${run.stage}`;
    return { level: run.status === "indexed" ? "ok" : "error", text: outcome };
  }
  return null;
}

/** Which contextual hint set owns the footer (same precedence as input dispatch). */
function footerContext(state) {
  if (state.overlay) {
    if (state.overlay.kind === "help") return "help";
    if (state.overlay.kind === "confirm") return "confirm";
    if (state.overlay.kind === "addRepo") return "addRepo";
    if (state.overlay.kind === "viewPackage") return "viewer";
    return "editor";
  }
  if (state.filterActive) return "filter";
  if (state.focus === "rail") return "rail";
  if (state.focus === "inspector") return "inspector";
  if (state.view === "repositories") return "repositories";
  if (state.view === "context") return "context";
  if (state.view === "system") return "system";
  return "list";
}

/**
 * Terse contextual hints from the shared control map (keymap.mjs). Hints that
 * would overflow the row are dropped whole — never wrapped or clipped — and the
 * `?` affordance is kept whenever the context advertises it.
 */
function buildFooter(state, layout, cols) {
  // Compact terminals keep the short list; otherwise width decides how many
  // whole hints fit, so a wide terminal shows every relevant control.
  const cap = layout.compact ? layout.footerHints : Number.POSITIVE_INFINITY;
  const hints = footerHints(footerContext(state), state).slice(0, cap);
  const right = state.lastRefreshAt ? `updated ${new Date(state.lastRefreshAt).toLocaleTimeString()}` : null;
  const budget = Math.max(0, cols - (right ? plainLength(right) + 2 : 0));
  const keysIndex = hints.findIndex((hint) => hint.keys === "?");
  const reserved = keysIndex >= 0 ? plainLength(`${hints[keysIndex].keys} ${hints[keysIndex].label}`) + 2 : 0;
  const primaryBudget = Math.max(0, budget - reserved);

  const shown = [];
  let used = 0;
  for (const hint of hints) {
    if (hint.keys === "?") continue;
    const cost = plainLength(`${hint.keys} ${hint.label}`) + (shown.length > 0 ? 2 : 0);
    if (shown.length > 0 && used + cost > primaryBudget) break;
    shown.push(hint);
    used += cost;
  }
  if (keysIndex >= 0) shown.push(hints[keysIndex]);

  return { hints: shown, right };
}

/**
 * The `?` reference sheet. Groups are laid out in two columns when both fit the
 * terminal (Torlink's card does the same) and stacked otherwise, so a wide
 * terminal shows the complete control list without scrolling. The sheet is
 * scrollable because no terminal promises to be tall enough for it.
 */
function helpLines(cols) {
  const blocks = HELP_GROUPS.map((group) => {
    const keyWidth = Math.max(...group.hints.map(([keys]) => keys.length));
    return {
      title: group.title,
      lines: group.hints.map(([keys, label]) => `${padTo(keys, keyWidth)}  ${label}`),
    };
  });
  const render = (block) => [block.title, ...block.lines, ""];
  const height = (list) => list.reduce((total, block) => total + block.lines.length + 2, 0);

  // Balance the columns by line count, then keep them only if they fit.
  let split = blocks.length;
  let best = Infinity;
  for (let index = 1; index < blocks.length; index += 1) {
    const diff = Math.abs(height(blocks.slice(0, index)) - height(blocks.slice(index)));
    if (diff < best) {
      best = diff;
      split = index;
    }
  }
  const left = blocks.slice(0, split).flatMap(render);
  const right = blocks.slice(split).flatMap(render);
  const widthOf = (list) => list.reduce((max, line) => Math.max(max, line.length), 0);
  const leftWidth = widthOf(left);
  const gap = 2;

  const body = [];
  if (right.length > 0 && leftWidth + gap + widthOf(right) <= cols) {
    const rows = Math.max(left.length, right.length);
    for (let index = 0; index < rows; index += 1) {
      body.push(`${padTo(left[index] ?? "", leftWidth + gap)}${right[index] ?? ""}`.trimEnd());
    }
  } else {
    body.push(...blocks.flatMap(render));
  }

  return [...body, "", ...HELP_NOTES];
}

function buildOverlay(state, layout, cols) {
  const overlay = state.overlay;
  const width = Math.max(24, Math.min(cols, 76));
  const height = Math.max(1, layout.bodyRows - 2);

  if (overlay.kind === "help") {
    const lines = helpLines(cols).map((text) => ({ text }));
    for (const group of HELP_GROUPS) {
      const index = lines.findIndex((line) => line.text === group.title);
      if (index >= 0) lines[index].style = "bold";
    }
    for (const line of lines) {
      if (line.style === undefined && line.text !== "") line.style = "dim";
    }
    return { kind: "help", title: "Keyboard", lines, width, height, scroll: state.scroll.viewer ?? 0 };
  }

  if (overlay.kind === "confirm") {
    return {
      kind: "confirm",
      title: overlay.target.type === "deleteRepository" ? "Delete repository" : "Delete package",
      lines: [
        { text: overlay.target.label, style: "bold" },
        { text: "" },
        {
          text:
            overlay.target.type === "deleteRepository"
              ? "Removes the repository from RE:Track and clears its derived memory records. Source files on disk are not touched."
              : "Removes the saved context package. Repositories and source files are untouched.",
          style: "dim",
        },
      ],
      width,
      height,
      scroll: 0,
    };
  }

  if (overlay.kind === "addRepo") {
    const pathLabel = overlay.source === "local" ? "path" : "url";
    const lines = [
      { text: `source: ${overlay.source === "local" ? "Local directory" : "GitHub URL"}   (tab switches)`, style: "dim" },
      { text: "" },
      fieldLine(pathLabel, overlay.values.path, overlay.cursors.path, overlay.field === "path", "(required)"),
      fieldLine("name", overlay.values.name, overlay.cursors.name, overlay.field === "name", "(optional)"),
    ];
    if (overlay.error) lines.push({ text: overlay.error, style: "error" });
    return { kind: "addRepo", title: "Add repository", lines, width, height, scroll: 0 };
  }

  if (overlay.kind === "newTask") {
    const lines = [
      { text: "Describe the coding task for grounded context:", style: "dim" },
      { text: "" },
      { prefix: `${GLYPH.pointer} `, value: overlay.value, cursor: overlay.cursor, placeholder: "(required)" },
    ];
    if (overlay.error) lines.push({ text: overlay.error, style: "error" });
    return { kind: "newTask", title: `New task · ${Math.round(state.tokenBudget / 1024)}K budget${state.includeGraph ? " · AST graph" : ""}`, lines, width, height, scroll: 0 };
  }

  if (overlay.kind === "savePackage") {
    const lines = [
      { text: "Package name:", style: "dim" },
      { text: "" },
      { prefix: `${GLYPH.pointer} `, value: overlay.value, cursor: overlay.cursor, placeholder: "(required)" },
    ];
    if (overlay.error) lines.push({ text: overlay.error, style: "error" });
    return { kind: "savePackage", title: "Save context package", lines, width, height, scroll: 0 };
  }

  const markdown = overlay.package?.markdown ?? "";
  const lines = formatMarkdown(markdown, { rendered: state.markdownView === "rendered", width: Math.max(20, width - 2) });
  return {
    kind: "viewPackage",
    // The presentation mode leads the title so it survives title truncation.
    title: `${state.markdownView} · ${overlay.package?.name ?? "package"}`,
    lines: lines.map((text) => ({ text })),
    width,
    height,
    scroll: state.scroll.viewer ?? 0,
  };
}

/* ----------------------------- compose frame ----------------------------- */

export function composeLines(model, styler) {
  const lines = [];
  if (model.tooSmall) return fitLines(tooSmallLines(model, styler), model);

  lines.push(headerLine(model, styler));
  if (model.layout.showRule) lines.push(styler.rule(GLYPH.rule.repeat(model.cols)));

  const body = model.overlay ? overlayLines(model, styler) : bodyLines(model, styler);
  const bodyRows = model.layout.bodyRows;
  for (let index = 0; index < bodyRows; index += 1) lines.push(body[index] ?? "");

  if (model.operation) {
    const paint = model.operation.level === "error" ? styler.err : model.operation.level === "ok" ? styler.ok : styler.warn;
    lines.push(fit(paint(model.operation.text), model.cols));
  }
  lines.push(footerLine(model, styler));
  return fitLines(lines, model);
}

export function composeFrame(model, options = {}) {
  const styler = options.styler ?? createPlainStyler();
  return `\x1b[H${composeLines(model, styler).join("\n")}\x1b[J`;
}

export function createPlainStyler() {
  return { enabled: false, bold: identity, dim: identity, inverse: identity, ok: identity, warn: identity, err: identity, rule: identity };
}

function fitLines(lines, model) {
  const out = [];
  for (let index = 0; index < model.rows; index += 1) out.push(fit(lines[index] ?? "", model.cols));
  return out;
}

function headerLine(model, styler) {
  const backend = model.header.backend;
  const backendStyled = backend.level === "error" ? styler.err(backend.label) : backend.level === "warn" ? styler.warn(backend.label) : styler.dim(backend.label);
  const notice = model.header.noticeText
    ? model.header.notice?.level === "error"
      ? styler.err(model.header.noticeText)
      : model.header.notice?.level === "warn"
        ? styler.warn(model.header.noticeText)
        : styler.dim(model.header.noticeText)
    : null;

  const leftCells = [
    cell(styler.bold("RE:Track")),
    cell(styler.dim(" · ")),
    cell(model.header.repo),
    model.header.repoStatus && model.header.repoStatus !== "indexed" ? cell(` (${model.header.repoStatus})`, (text, s) => s.warn(text)) : cell(""),
    cell(styler.dim(" · ")),
    cell(backendStyled),
  ];
  const budget = notice ? Math.max(16, model.cols - plainLength(notice) - 2) : model.cols;
  const left = joinCells(leftCells, styler, budget);
  if (!notice) return left;
  return `${left}${" ".repeat(Math.max(1, model.cols - plainLength(left) - plainLength(notice)))}${notice}`;
}

function bodyLines(model, styler) {
  const lines = [];
  const { layout, view } = model;
  const rail = railContent(model, styler);
  const list = listContent(model, styler);
  const inspector = inspectorContent(model, styler);
  const mode = view.inspector.open && !layout.sideBySide;
  const modeWidth = layout.listWidth + layout.inspectorWidth + 1;

  for (let index = 0; index < layout.bodyRows; index += 1) {
    const cells = [cell(fit(rail[index] ?? "", layout.railWidth)), cell(" ")];
    if (layout.sideBySide && !view.fullWidth) {
      cells.push(cell(fit(list[index] ?? "", layout.listWidth)), cell(" "), cell(fit(inspector[index] ?? "", layout.inspectorWidth)));
    } else if (mode) {
      cells.push(cell(fit(inspector[index] ?? "", modeWidth)));
    } else {
      cells.push(cell(fit(list[index] ?? "", modeWidth)));
    }
    lines.push(joinCells(cells, styler, model.cols));
  }
  return lines;
}

function railContent(model, styler) {
  const width = model.layout.railWidth;
  // Same focus language as the pane titles: the marker is the no-color signal
  // that the menu owns the keyboard, while the active destination keeps its own
  // marker when focus is elsewhere.
  const lines = [titleRule("Workspace", null, width, styler, model.rail.focused)];
  for (const item of model.rail.items) {
    const count = model.layout.showBadges && item.count !== null ? ` (${item.count})` : "";
    const marker = item.active ? GLYPH.pointer : " ";
    const text = truncate(`${marker} ${item.label}${count}`, width);
    const emphasized = item.active && model.rail.focused;
    const styled = item.active
      ? (emphasized ? styler.bold(text) : text)
      : styler.dim(text);
    lines.push(fit(styled, width));
  }
  return lines;
}

function listContent(model, styler) {
  const list = model.view.list;
  const width = model.layout.sideBySide && !model.view.fullWidth
    ? model.layout.listWidth
    : model.layout.listWidth + model.layout.inspectorWidth + 1;
  const lines = [titleRule(list.title, list.subtitle, width, styler, list.focused)];

  if (list.filterActive || list.filter) {
    const prefix = list.filterActive ? `${GLYPH.pointer} ` : "filter: ";
    const body = list.filterActive
      ? editorText(list.filter, list.filterCursor, styler, "type to filter…")
      : truncate(list.filter, Math.max(4, width - prefix.length));
    lines.push(fit(`${styler.dim(prefix)}${body}`, width));
  }

  if (model.view.banner && !model.view.inspector.open) {
    for (const line of model.view.banner.lines) {
      const paint = model.view.banner.level === "error" ? styler.err : styler.warn;
      lines.push(fit(paint(truncate(line, width)), width));
    }
  }

  const height = Math.max(1, model.layout.bodyRows - lines.length);
  if (list.rows.length === 0) {
    lines.push(fit(styler.dim(list.empty ?? "nothing to show"), width));
    return lines;
  }

  const start = list.offsetMode
    ? clamp(list.cursor, 0, Math.max(0, list.rows.length - height))
    : windowStart(list.cursor, list.rows.length, height);

  for (let index = start; index < Math.min(list.rows.length, start + height); index += 1) {
    const row = list.rows[index];
    const selected = index === list.cursor;
    const marker = selected ? GLYPH.pointer : " ";
    const text = renderRow(row, styler, width - 2);
    const combined = `${marker} ${text}`;
    lines.push(selected ? styler.inverse(fit(combined, width)) : fit(combined, width));
  }
  return lines;
}

function renderRow(row, styler, width) {
  if (row.section) return styler.bold(truncate(row.section, width));
  if (row.note) return styler.dim(truncate(row.note, width));
  if (row.log) return styler.dim(truncate(row.log, width));
  if (row.cells) return joinCells(row.cells, styler, width);
  if (row.label !== undefined) {
    const value = row.value === null || row.value === undefined || row.value === "" ? UNAVAILABLE : row.value;
    return joinCells([cell(padTo(row.label, 24), (text, s) => s.dim(text)), cell(value)], styler, width);
  }
  return "";
}

function inspectorContent(model, styler) {
  const inspector = model.view.inspector;
  const width = model.layout.sideBySide ? model.layout.inspectorWidth : model.layout.listWidth + model.layout.inspectorWidth + 1;
  const lines = [titleRule(inspector.title, null, width, styler, inspector.focused)];
  const height = Math.max(1, model.layout.bodyRows - 1);
  const start = clamp(inspector.scroll ?? 0, 0, Math.max(0, inspector.lines.length - height));
  for (let index = start; index < Math.min(inspector.lines.length, start + height); index += 1) {
    const entry = inspector.lines[index];
    const text = entry.cells ? joinCells(entry.cells, styler, width) : String(entry.text ?? "");
    lines.push(fit(text, width));
  }
  return lines;
}

function titleRule(title, subtitle, width, styler, focused) {
  const label = subtitle ? `${title} · ${subtitle}` : title;
  const marker = focused ? `${GLYPH.pointer} ` : "";
  const head = truncate(`${marker}${label} `, Math.max(4, width - 2));
  const rule = GLYPH.rule.repeat(Math.max(0, width - head.length - 1));
  const styled = focused ? styler.bold(head) : styler.dim(head);
  return `${styled}${styler.rule(rule)}`;
}

function overlayLines(model, styler) {
  const overlay = model.overlay;
  const lines = [titleRule(overlay.title, null, model.cols, styler, true), ""];
  const height = Math.max(1, model.layout.bodyRows - 2);
  const start = clamp(overlay.scroll ?? 0, 0, Math.max(0, overlay.lines.length - height));
  for (let index = start; index < Math.min(overlay.lines.length, start + height); index += 1) {
    const line = overlay.lines[index];
    const text = String(line.text ?? "");
    const styled =
      line.prefix !== undefined
        ? `${styler.dim(line.prefix)}${editorText(line.value, line.cursor, styler, line.placeholder ?? "")}`
        : line.style === "bold"
          ? styler.bold(text)
          : line.style === "error"
            ? styler.err(text)
            : line.style === "dim"
              ? styler.dim(text)
              : text;
    lines.push(fit(styled, model.cols));
  }
  return lines;
}

function footerLine(model, styler) {
  const { hints, right } = model.footer;
  const left = hints.map((hint) => `${styler.bold(hint.keys)}${styler.dim(` ${hint.label}`)}`).join(styler.dim("  "));
  if (!right) return left;
  const gap = model.cols - plainLength(left) - plainLength(right) - 1;
  if (gap < 2) return left;
  return `${left}${" ".repeat(gap)}${styler.dim(right)}`;
}

function tooSmallLines(model, styler) {
  return [
    headerLine(model, styler),
    "",
    styler.bold("terminal too small"),
    styler.dim(`need at least 48 columns and 12 rows — current ${model.cols}×${model.rows}`),
    "",
    styler.dim(`backend: ${model.header.backend.label}`),
    styler.dim(`repository: ${model.header.repo}`),
    "",
    styler.dim("resize the terminal, or press q to quit"),
  ];
}
