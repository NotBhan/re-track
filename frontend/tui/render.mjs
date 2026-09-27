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

import {
  layoutFor,
  padTo,
  padStart,
  truncate,
  wrapToWidth,
  clamp,
  followWindow,
  offsetWindow,
  pageStep,
  scrollMax,
  moreMarker,
} from "./layout.mjs";
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
  progressBar,
  statusStyle,
  summarizeList,
} from "./theme.mjs";

export const HELP_NOTES = Object.freeze([
  "Indexing and synthesis cannot be cancelled: the backend exposes no cancel endpoint.",
  "Provider configuration is editable in Settings (e); storage engines are fixed by the backend.",
  "Code search is unavailable over HTTP; the Code view shows AST metadata only.",
  "All values shown come from backend responses; nothing is estimated.",
]);

const VIEW_TITLES = Object.freeze({
  repositories: "Repositories",
  code: "Code",
  context: "Context",
  system: "System",
  settings: "Settings",
});

/** True when the backend reported a usable file total (0/1048 is real progress). */
const hasFileProgress = (op) =>
  Number.isFinite(op?.processedFiles) && Number.isFinite(op?.totalFiles) && op.totalFiles > 0;
/** True when the backend reported a usable phase index. */
const hasPhaseProgress = (op) =>
  Number.isFinite(op?.stageIndex) && Number.isFinite(op?.stageTotal) && op.stageTotal > 0 && op.stageIndex > 0;

/**
 * Height of the operation block, derived from state before the layout is built.
 * Determinate progress earns a second row for the bar; a failure keeps its
 * error text visible on one.
 */
function operationHeight(state) {
  if (state.operation?.kind === "indexing") {
    return hasFileProgress(state.operation) || hasPhaseProgress(state.operation) ? 2 : 1;
  }
  if (state.operation?.kind === "synthesis") return 1;
  if (state.lastRun) return state.lastRun.status === "error" && state.lastRun.stage ? 2 : 1;
  return 0;
}

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
  const layout = layoutFor({ cols, rows, operation: operationHeight(state) });

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
    operation: buildOperation(state, layout, spinnerFrame, cols),
    footer: buildFooter(state, layout, cols),
    overlay: state.overlay ? buildOverlay(app, state, layout, cols) : null,
    scrollMax: { detail: 0, system: 0, viewer: 0, help: 0, overlay: 0 },
    pageSteps: { detail: 1, system: 1, viewer: 1, help: 1, overlay: 1, model: 1 },
  };

  model.header.noticeText = state.notice
    ? truncate(state.notice.message, Math.max(12, Math.floor(cols * 0.42)))
    : null;

  model.view = buildView(app, state, layout);

  // The pane heights the views actually render determine every scroll bound,
  // so state clamps against what is on screen instead of an estimate.
  const bannerRows = model.view.banner && !model.view.inspector.open ? model.view.banner.lines.length : 0;
  const headerRows = (model.view.list.filterActive || model.view.list.filter ? 1 : 0) + bannerRows;
  model.view.list.height = Math.max(1, layout.bodyRows - 1 - headerRows);
  model.view.inspector.height = Math.max(1, layout.bodyRows - 1);

  const overlayHeight = model.overlay ? Math.max(1, layout.bodyRows - 2) : 0;
  const overlayLines_count = model.overlay?.lines.length ?? 0;
  const kind = model.overlay?.kind ?? null;
  // Form-like overlays that page as a whole (PgUp/PgDn, and Home/End while no
  // text field owns the caret): their content must be able to outgrow the body.
  const formOverlay = [
    "confirm",
    "resetSettings",
    "resynthesize",
    "addRepo",
    "newTask",
    "savePackage",
    "appendPackage",
    "exportPackage",
    "providerSettings",
    "pipelineSettings",
  ].includes(kind);

  model.scrollMax = {
    detail: scrollMax(model.view.inspector.lines.length, model.view.inspector.height),
    system: scrollMax(model.view.list.rows.length, model.view.list.height),
    viewer: kind === "viewPackage" ? scrollMax(overlayLines_count, overlayHeight) : 0,
    help: kind === "help" ? scrollMax(overlayLines_count, overlayHeight) : 0,
    overlay: formOverlay ? scrollMax(overlayLines_count, overlayHeight) : 0,
  };
  model.pageSteps = {
    detail: pageStep(model.view.inspector.height),
    system: pageStep(model.view.list.height),
    viewer: pageStep(overlayHeight),
    help: pageStep(overlayHeight),
    overlay: pageStep(overlayHeight),
    model: pageStep(model.overlay?.list?.height ?? 8),
  };

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
      { key: "settings", label: "Settings", count: null, active: state.view === "settings" },
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
    // Each destination owns its detail offset, so switching views keeps them
    // independent and returning restores the previous position.
    scroll: state.scroll[state.view] ?? 0,
    focused: state.focus === "inspector",
    open: state.inspectorOpen,
    width: layout.sideBySide ? layout.inspectorWidth : layout.listWidth + layout.inspectorWidth + 1,
    height: Math.max(1, layout.bodyRows - 1),
  };

  if (state.view === "repositories") buildRepositories(app, state, layout, list, inspector);
  else if (state.view === "code") buildCode(app, state, layout, list, inspector);
  else if (state.view === "context") buildContext(app, state, layout, list, inspector);
  else if (state.view === "settings") buildSettings(app, state, layout, list, inspector);
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
    const scope = state.packageScope === "packages" ? "catalog: packages" : "catalog: all";
    return [scope, source, budget, graph].filter(Boolean).join(" · ");
  }
  return state.health?.status ? `backend ${state.health.status}` : null;
}

function buildBanner(app, state) {
  if (state.view === "settings" && state.settingsError) {
    return { level: "warn", lines: [`settings unavailable: ${state.settingsError}`] };
  }
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

/** Width the symbol name gets in the code list: the file column goes first. */
function symbolLabelWidth(layout) {
  const fileWidth = layout.listWidth >= 56 ? 20 : 0;
  return Math.max(12, layout.listWidth - 4 - 10 - fileWidth);
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
        // The symbol name is the point of the row: it keeps its room and the
        // file column is what narrow terminals drop.
        cell(truncate(node.label ?? node.id ?? `symbol ${index + 1}`, symbolLabelWidth(layout)), (text, styler) => styler.bold(text)),
        cell(` ${truncate(node.kind ?? "symbol", 10)}`, (text, styler) => styler.dim(text)),
        ...(layout.listWidth >= 56 ? [cell(` ${truncate(node.file ?? UNAVAILABLE, 20)}`, (text, styler) => styler.dim(text))] : []),
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

  list.rows = rows.map((row) => {
    if (row.kind === "task") {
      return {
        kind: "task",
        cells: [
          cell(truncate(row.label, Math.max(12, layout.listWidth - 16)), (text, styler) => styler.bold(text)),
          cell(" prompt", (text, styler) => styler.dim(text)),
        ],
      };
    }
    return row.kind === "suggestion"
      ? {
          kind: "suggestion",
          cells: [cell(truncate(row.label ?? row.prompt, layout.listWidth - 16), (text, styler) => styler.bold(text)), cell(" task", (text, styler) => styler.dim(text))],
        }
      : {
          kind: "package",
          id: row.id,
          cells: [
            cell(
              truncate(row.label ?? row.id, Math.max(12, layout.listWidth - 4 - (layout.listWidth >= 54 ? 18 : 0) - (layout.listWidth >= 44 ? 10 : 0) - (layout.listWidth >= 66 ? 10 : 0) - 5)),
              (text, styler) => styler.bold(text)
            ),
            ...(layout.listWidth >= 54 ? [cell(` ${truncate(row.repository ?? UNAVAILABLE, 16)}`, (text, styler) => styler.dim(text))] : []),
            ...(layout.listWidth >= 44 ? [cell(` ${truncate(formatCount(row.tokens), 8)} tok`, (text, styler) => styler.dim(text))] : []),
            ...(layout.listWidth >= 66 ? [cell(` ${truncate(formatRelativeTime(row.created, state.nowMs), 8)}`, (text, styler) => styler.dim(text))] : []),
            cell(" pkg", (text, styler) => styler.dim(text)),
          ],
        };
  });
  // The catalog is empty only in the packages-only scope; the default scope
  // always leads with the "Run new task" action row.
  if (list.rows.length === 0) {
    list.empty = "no saved packages yet · generate context (n) and press S to save one";
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
    if (selected.kind === "task") {
      const others = rows.filter((row) => row.kind !== "task").length;
      const status =
        state.prompts.state === "loading"
          ? "loading suggested tasks…"
          : state.prompts.state === "error"
            ? "suggested tasks unavailable"
            : others === 0
              ? "no suggested tasks or packages yet"
              : null;
      inspector.lines = [
        cell("New task", (text, styler) => styler.dim(text)),
        cell("Describe a task in your own words.", (text, styler) => styler.bold(text)),
        cell(""),
        cell("Press enter to write a new task prompt.", (text, styler) => styler.dim(text)),
        ...(status ? [cell(""), cell(status, (text, styler) => styler.dim(text))] : []),
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
      cell(
        `${formatCount(pkg?.token_estimate)} tokens · ${formatCount(pkg?.section_count)} sections · saved ${formatRelativeTime(pkg?.created_at, state.nowMs)}`,
        (text, styler) => styler.dim(text)
      ),
      cell(
        `repository: ${pkg?.repository_name || UNAVAILABLE}${pkg?.repository_branch ? ` · ${pkg.repository_branch}` : ""}`,
        (text, styler) => styler.dim(text)
      ),
      pkg?.updated_at && pkg.updated_at !== pkg.created_at
        ? cell(`updated ${formatRelativeTime(pkg.updated_at, state.nowMs)}`, (text, styler) => styler.dim(text))
        : cell(""),
      cell(""),
      ...wrapToWidth(pkg?.task ?? "", Math.max(20, inspector.width - 2)).map((piece) => cell(piece)),
      cell(""),
      cell("enter opens the package · R re-synthesizes it · A appends · e exports", (text, styler) => styler.dim(text)),
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
  lines.push(cell(`output · ${state.markdownView === "rendered" ? "rendered" : "raw"} (m toggles) · c copies the markdown`, (text, styler) => styler.dim(text)));

  const markdownLines = formatMarkdown(result.context_markdown ?? "", {
    rendered: state.markdownView === "rendered",
    width: Math.max(20, inspector.width - 2),
  });
  for (const piece of markdownLines) lines.push(cell(piece));

  inspector.title = "Evidence & output";
  inspector.lines = lines;
}

/** A label/value row for detail panes (repository, symbol, settings). */
function detailRow(label, value, width, labelWidth = 22) {
  return cell(
    joinCells(
      [
        cell(padTo(label, labelWidth), (text, styler) => styler.dim(text)),
        cell(value === null || value === undefined || value === "" ? UNAVAILABLE : String(value)),
      ],
      { dim: identity },
      Math.max(20, width)
    )
  );
}

const CAPABILITIES = Object.freeze([
  ["repository management", "available (a / s / i / d)"],
  ["context synthesis", "available (Context · n)"],
  ["package viewer", "available (Context · enter)"],
  ["package save", "available (Context · S)"],
  ["package append", "available (POST /packages/{id}/append)"],
  ["package re-synthesis", "available (PUT /packages/{id}) · viewer r"],
  ["package export", "local file export (no backend endpoint)"],
  ["clipboard copy", "terminal clipboard (native utility or OSC 52)"],
  ["settings auto-save", "available (no save step: toggle, choose, or leave the field)"],
  ["settings reset", "available (POST /settings/reset) · Settings · R"],
  ["diagnostics export", "available (System · e)"],
  ["pipeline toggles", "editable here (t)"],
  ["provider configuration", "editable here (e)"],
  ["model discovery", "available (ctrl+p in the provider editor)"],
  ["storage engine selection", "fixed by the backend (single engine each)"],
  ["display scaling", "GUI only (desktop window property)"],
  ["cancellation", "not supported by the backend"],
  ["code search", "not available over HTTP"],
  ["automatic updates", "not available"],
]);

/**
 * Settings answers "what is RE:Track configured to use?" — the persisted
 * application settings plus the runtime facts that qualify them. Every value is
 * a backend field; missing fields render as unavailable, and capabilities that
 * exist only in the desktop GUI say so instead of offering a dead control.
 */
function buildSettings(app, state, layout, list, inspector) {
  const settings = state.appSettings ?? {};
  const health = state.health ?? {};
  const status = state.status ?? {};
  const provider = state.providerStatus ?? {};
  const detailed = state.detailedHealth ?? {};
  const paths = detailed.storage_paths ?? {};
  const memory = state.memoryStats ?? {};
  const width = Math.max(20, inspector.width - 2);
  const sections = app.settingsRows();
  const selected = app.selectedSettingsSection();

  const summaries = {
    provider: provider.provider ?? health.provider_identity ?? status.llm_provider ?? null,
    storage: settings.vector_db ? `${settings.vector_db} · ${settings.graph_db ?? UNAVAILABLE}` : null,
    hardware: health.execution_device ?? null,
    capabilities: `${CAPABILITIES.length} entries · read-only`,
  };
  list.rows = sections.map((section) => ({
    key: section.key,
    cells: [
      cell(section.label, (text, styler) => styler.bold(text)),
      cell(` ${summaries[section.key] ?? UNAVAILABLE}`, (text, styler) => styler.dim(text)),
    ],
  }));
  list.subtitle = state.settingsBusy ? "applying…" : null;

  const loadedModels = Array.isArray(provider.loaded_models)
    ? provider.loaded_models.map((model) => model?.model_id ?? model?.name).filter(Boolean)
    : [];

  if (!selected || selected.key === "provider") {
    inspector.title = "Provider";
    inspector.lines = [
      detailRow("provider", provider.provider ?? health.provider_identity ?? status.llm_provider, width),
      detailRow("endpoint", provider.base_url ?? health.provider_base_url ?? status.llm_endpoint ?? settings.llm_endpoint, width),
      detailRow("configured model", health.configured_model ?? status.configured_model ?? settings.llm_model, width),
      detailRow("verified active", health.active_model ?? status.active_model ?? "none verified", width),
      detailRow("active model state", health.active_model_state, width),
      detailRow("reachable", provider.is_reachable ?? health.provider_reachable, width),
      detailRow("health state", provider.health_state ?? health.provider_health_state, width),
      detailRow("loaded models", loadedModels.length > 0 ? summarizeList(loadedModels, 3) : null, width),
      detailRow("api key", settings.api_key_masked ?? (settings.api_key_configured ? "configured" : null), width),
      cell(""),
      cell("Embedding", (text, styler) => styler.dim(text)),
      detailRow("provider", health.embedding_provider ?? status.embedding_provider, width),
      detailRow("model", health.embedding_model ?? status.embedding_model, width),
      detailRow("state", health.embedding_state ?? status.embedding_state, width),
      cell(""),
      cell("Semantic memory", (text, styler) => styler.dim(text)),
      detailRow("provider", health.semantic_memory_provider ?? status.semantic_memory_provider ?? settings.semantic_memory_provider, width),
      detailRow("model", health.semantic_memory_model ?? status.semantic_memory_model ?? settings.memory_model, width),
      detailRow("state", health.semantic_memory_state ?? status.semantic_memory_state, width),
      cell(""),
      cell("changes save automatically: e edits the provider, model and API key", (text, styler) => styler.dim(text)),
      cell("R restores the mutable settings to the backend's application defaults", (text, styler) => styler.dim(text)),
    ];
    return;
  }

  if (selected.key === "storage") {
    const toggle = (key) => {
      const value = settings[key];
      if (value === undefined || value === null) return null;
      return `${value ? "enabled" : "disabled"} (t toggles · saved immediately)`;
    };
    inspector.title = "Storage & pipeline";
    inspector.lines = [
      detailRow("data root", settings.data_root ?? paths.canonical_root, width),
      detailRow("system root", settings.system_root, width),
      detailRow("logs directory", paths.logs_directory, width),
      detailRow("cache directory", paths.cache_directory, width),
      detailRow("canonical storage", health.storage_canonical_exists === undefined ? null : health.storage_canonical_exists ? "present" : "missing", width),
      detailRow("writable", health.storage_canonical_writable, width),
      detailRow("legacy storage detected", health.legacy_storage_detected, width),
      cell(""),
      cell("Engines", (text, styler) => styler.dim(text)),
      detailRow("vector db", settings.vector_db, width),
      detailRow("graph db", settings.graph_db, width),
      detailRow("relational db", settings.relational_db, width),
      cell("storage engines are fixed by the backend (single engine each)", (text, styler) => styler.dim(text)),
      cell(""),
      cell("Pipeline", (text, styler) => styler.dim(text)),
      detailRow("knowledge graph", toggle("enable_kg_extraction"), width),
      detailRow("auto-link entities", toggle("auto_link_entities"), width),
      detailRow("ingestion caching", toggle("caching"), width),
      cell("pipeline changes are written on the toggle — there is no save step", (text, styler) => styler.dim(text)),
    ];
    return;
  }

  if (selected.key === "hardware") {
    inspector.title = "Hardware & runtime";
    inspector.lines = [
      detailRow("ram", health.ram_total_gb !== undefined ? `${health.ram_used_gb ?? 0} / ${health.ram_total_gb} GB` : null, width),
      detailRow("cpu", health.cpu_percent !== undefined ? `${health.cpu_percent}%` : null, width),
      detailRow("gpu", health.gpu_name ?? health.gpu_presence, width),
      detailRow("vram", health.vram_total_gb !== undefined ? `${health.vram_used_gb ?? 0} / ${health.vram_total_gb} GB` : null, width),
      detailRow("execution device", health.execution_device, width),
      detailRow("memory pressure", health.high_memory_pressure === undefined ? null : health.high_memory_pressure ? "high" : "normal", width),
      cell(""),
      cell("Runtime", (text, styler) => styler.dim(text)),
      detailRow("engine state", health.engine_state, width),
      detailRow("engine reason", health.engine_reason, width),
      detailRow("cognee state", health.cognee_state ?? (health.cognee_initialized ? "initialized" : null), width),
      detailRow("cognee reason", health.cognee_reason, width),
      detailRow("mcp ready", health.mcp_server_ready, width),
      detailRow("concurrency", health.concurrency_queue_capacity !== undefined ? `${formatCount(health.concurrency_queue_depth)} queued · ${formatCount(health.concurrency_available_slots)} slots free` : null, width),
      detailRow("datasets", memory.dataset_count, width),
      detailRow("memory size", memory.total_size_display, width),
      detailRow("knowledge graph", memory.knowledge_graph_status, width),
    ];
    return;
  }

  inspector.title = "Capabilities";
  inspector.lines = [
    cell("What this terminal interface can do, and what stays in the GUI:", (text, styler) => styler.dim(text)),
    cell(""),
    ...CAPABILITIES.map(([label, value]) =>
      cell(
        joinCells(
          [cell(padTo(label, 30), (text, styler) => styler.dim(text)), cell(value)],
          { dim: identity },
          width
        )
      )
    ),
    cell(""),
    cell("Pipeline toggles and the provider configuration are saved automatically.", (text, styler) => styler.dim(text)),
    cell("R restores the mutable settings to the application defaults (configuration only).", (text, styler) => styler.dim(text)),
    cell("Everything else configured in the desktop GUI has no terminal mutation surface.", (text, styler) => styler.dim(text)),
  ];
}

function buildSystem(app, state, layout, list, inspector) {
  const health = state.health ?? {};
  const status = state.status ?? {};
  const provider = state.providerStatus ?? {};
  const memory = state.memoryStats ?? {};
  const rows = [];
  const section = (title) => rows.push({ section: title });
  const entry = (label, value) => rows.push({ label, value });

  section("Provider");
  entry("identity", provider.provider ?? health.provider_identity ?? status.llm_provider);
  entry("reachable", provider.is_reachable ?? health.provider_reachable);
  entry("health state", provider.health_state ?? health.provider_health_state);
  entry("active model", health.active_model ?? status.active_model ?? "none verified");
  entry("embedding state", health.embedding_state);
  entry("semantic mem state", health.semantic_memory_state);
  entry("configuration", "Settings view");

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
  entry("canonical", health.storage_canonical_exists === undefined ? null : health.storage_canonical_exists ? "present" : "missing");
  entry("writable", health.storage_canonical_writable);
  entry("legacy detected", health.legacy_storage_detected);
  entry("paths", "Settings view");

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
  rows.push({ note: "cancellation: not supported by the backend" });
  rows.push({ note: "configuration: Settings view" });

  list.rows = rows;
  list.offsetMode = true;
  list.cursor = state.scroll.system ?? 0;
  list.empty = state.error ? "backend unavailable · press r to retry" : null;
  inspector.lines = [cell("System information is read-only.", (text, styler) => styler.dim(text))];
}

/**
 * Sticky operation block: obvious activity, obvious completion, obvious
 * failure. Determinate bars are only drawn from backend-reported file or phase
 * counts; everything else is indeterminate and says so.
 */
function buildOperation(state, layout, spinnerFrame, cols) {
  const spinner = layout.compact ? "" : `${SPINNER_FRAMES[spinnerFrame % SPINNER_FRAMES.length]} `;
  const barWidth = clamp(Math.floor(cols * 0.22), 10, 24);

  if (state.operation?.kind === "indexing") {
    const op = state.operation;
    const elapsed = formatDuration(op.elapsedMs ?? state.nowMs - op.startedAt);
    const lines = [`${spinner}Indexing ${op.repoName ?? op.repoId} · ${op.stage ?? "working"}`];
    if (hasFileProgress(op)) {
      const phase = hasPhaseProgress(op) ? ` · phase ${op.stageIndex}/${op.stageTotal}` : "";
      lines.push(
        `${progressBar(op.processedFiles / op.totalFiles, barWidth)}  ${formatCount(op.processedFiles)} / ${formatCount(op.totalFiles)} files${phase} · ${elapsed}`
      );
    } else if (hasPhaseProgress(op)) {
      lines.push(
        `${progressBar(op.stageIndex / op.stageTotal, barWidth)}  phase ${op.stageIndex}/${op.stageTotal} · ${elapsed}`
      );
    }
    return { level: "warn", lines };
  }

  if (state.operation?.kind === "synthesis") {
    const op = state.operation;
    const elapsed = formatDuration(state.nowMs - op.startedAt);
    return {
      level: "warn",
      lines: [`${spinner}Synthesizing ${op.repoName ?? op.repoId} · elapsed ${elapsed} · runtime ${op.runtimeState ?? "unknown"}`],
    };
  }

  if (state.lastRun) {
    const run = state.lastRun;
    const name = run.repoName ?? run.repoId;
    if (run.status === "indexed") {
      const detail = [
        Number.isFinite(run.totalFiles) ? `${formatCount(run.totalFiles)} files` : null,
        Number.isFinite(run.failedFiles) && run.failedFiles > 0 ? `${formatCount(run.failedFiles)} failed` : null,
        Number.isFinite(run.elapsedMs) ? formatDuration(run.elapsedMs) : null,
      ]
        .filter(Boolean)
        .join(" · ");
      return { level: "ok", lines: [`${GLYPH.check} Indexed ${name}${detail ? ` · ${detail}` : ""}`] };
    }
    const lines = [`${GLYPH.cross} Indexing failed · ${name}`];
    if (run.stage) lines.push(run.stage);
    return { level: "error", lines };
  }

  return null;
}

/** Which contextual hint set owns the footer (same precedence as input dispatch). */
function footerContext(state) {
  if (state.overlay) {
    if (state.overlay.kind === "help") return "help";
    if (state.overlay.kind === "confirm") return "confirm";
    if (state.overlay.kind === "resetSettings") return "confirm";
    if (state.overlay.kind === "resynthesize") return "confirm";
    if (state.overlay.kind === "addRepo") return "addRepo";
    if (state.overlay.kind === "viewPackage") return "viewer";
    if (state.overlay.kind === "pipelineSettings") return "pipeline";
    if (state.overlay.kind === "providerSettings") return "provider";
    if (state.overlay.kind === "modelSelect") return "modelSelect";
    return "editor";
  }
  if (state.filterActive) return "filter";
  if (state.focus === "rail") return "rail";
  // The generated output has its own actions; every other detail pane scrolls.
  if (state.focus === "inspector") return state.view === "context" ? "contextInspector" : "inspector";
  if (state.view === "repositories") return "repositories";
  if (state.view === "context") return "context";
  if (state.view === "system") return "system";
  if (state.view === "settings") return "settings";
  return "list";
}

/**
 * Terse contextual hints from the shared control map (keymap.mjs). Hints that
 * would overflow the row are dropped whole — never wrapped or clipped — and the
 * `?` affordance is kept whenever the context advertises it.
 */
function buildFooter(state, layout, cols) {
  // Compact terminals keep the short list; otherwise width decides how many
  // whole hints fit, so a wide terminal shows every relevant control. The `?`
  // affordance is part of the contract, so it survives the compact cut.
  const all = footerHints(footerContext(state), state);
  const keysHint = all.find((hint) => hint.keys === "?");
  const primary = all.filter((hint) => hint.keys !== "?");
  const cap = layout.compact ? Math.max(0, layout.footerHints - (keysHint ? 1 : 0)) : primary.length;
  const hints = [...primary.slice(0, cap), ...(keysHint ? [keysHint] : [])];
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

/**
 * What the model list currently holds, in one line: the discovery fetch state
 * plus the backend's own status/message. Providers that cannot enumerate their
 * models say so here instead of offering a dead selector.
 */
function modelStatusText(models) {
  const state_ = models?.state ?? "idle";
  if (state_ === "loading") return "loading models…";
  if (state_ === "ready") return `${formatCount(models.items.length)} models · enter selects and saves`;
  if (state_ === "empty") return `no models available${models.message ? ` · ${models.message}` : ""}`;
  if (state_ === "failed") {
    const detail = [models.message, models.errorDetails].filter(Boolean).join(" · ");
    return `model selection: unavailable${detail ? ` · ${detail}` : ""}`;
  }
  return "not read yet · ctrl+p reads the endpoint";
}

function buildOverlay(app, state, layout, cols) {
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
    return { kind: "help", title: "Keyboard", lines, width, height, scroll: state.scroll.help ?? 0 };
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
      scroll: state.scroll.overlay ?? 0,
    };
  }

  if (overlay.kind === "resetSettings") {
    const lines = [
      { text: "Reset settings?", style: "bold" },
      { text: "" },
      { text: "This restores mutable RE:Track settings to their application defaults:", style: "dim" },
      { text: "· pipeline toggles, provider, endpoint, model and API key", style: "dim" },
      { text: "· resolved by the backend from its own configuration source", style: "dim" },
      { text: "" },
      { text: "Repositories, packages, memory and indexed data are not touched.", style: "dim" },
    ];
    if (overlay.error) lines.push({ text: "" }, { text: overlay.error, style: "error" });
    if (overlay.busy) lines.push({ text: "" }, { text: "resetting…", style: "dim" });
    return { kind: "resetSettings", title: "Reset settings", lines, width, height, scroll: state.scroll.overlay ?? 0 };
  }

  if (overlay.kind === "resynthesize") {
    const plan = overlay.plan ?? {};
    const lines = [
      { text: `Re-synthesize “${plan.name ?? UNAVAILABLE}”?`, style: "bold" },
      { text: "" },
      { text: "Regenerates this package's context from its stored definition:", style: "dim" },
      { text: `  task        ${plan.task ?? UNAVAILABLE}` },
      { text: `  repository  ${plan.repository ?? UNAVAILABLE}` },
      { text: `  options     ${Math.round((plan.maxTokens ?? 0) / 1024)}K budget · AST graph ${plan.includeStructuralGraph ? "on" : "off"} (current Context settings)`, style: "dim" },
      { text: "" },
      { text: "The stored markdown is replaced, never appended to. If generation or", style: "dim" },
      { text: "persistence fails, the package stays exactly as it is now.", style: "dim" },
    ];
    if (overlay.error) lines.push({ text: "" }, { text: overlay.error, style: "error" });
    if (overlay.busy) lines.push({ text: "" }, { text: "synthesizing…", style: "dim" });
    return { kind: "resynthesize", title: "Re-synthesize package", lines, width, height, scroll: state.scroll.overlay ?? 0 };
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
    return { kind: "addRepo", title: "Add repository", lines, width, height, scroll: state.scroll.overlay ?? 0 };
  }

  if (overlay.kind === "newTask") {
    const lines = [
      { text: "Describe the coding task for grounded context:", style: "dim" },
      { text: "" },
      { prefix: `${GLYPH.pointer} `, value: overlay.value, cursor: overlay.cursor, placeholder: "(required)" },
    ];
    if (overlay.error) lines.push({ text: overlay.error, style: "error" });
    return { kind: "newTask", title: `New task · ${Math.round(state.tokenBudget / 1024)}K budget${state.includeGraph ? " · AST graph" : ""}`, lines, width, height, scroll: state.scroll.overlay ?? 0 };
  }

  if (overlay.kind === "savePackage") {
    const lines = [
      { text: "Package name:", style: "dim" },
      { text: "" },
      { prefix: `${GLYPH.pointer} `, value: overlay.value, cursor: overlay.cursor, placeholder: "(required)" },
    ];
    if (overlay.error) lines.push({ text: overlay.error, style: "error" });
    return { kind: "savePackage", title: "Save context package", lines, width, height, scroll: state.scroll.overlay ?? 0 };
  }

  if (overlay.kind === "appendPackage") {
    const lines = [
      { text: `Append an iterative task or note to “${overlay.label}”.`, style: "dim" },
      { text: "It is sent as additional_task through POST /packages/{id}/append.", style: "dim" },
      { text: "" },
      { prefix: `${GLYPH.pointer} `, value: overlay.value, cursor: overlay.cursor, placeholder: "(required)" },
    ];
    if (overlay.error) lines.push({ text: overlay.error, style: "error" });
    if (overlay.busy) lines.push({ text: "appending…", style: "dim" });
    return { kind: "appendPackage", title: "Append to package", lines, width, height, scroll: state.scroll.overlay ?? 0 };
  }

  if (overlay.kind === "exportPackage") {
    const lines = [
      { text: `Write the stored markdown of “${overlay.label}” to a local file.`, style: "dim" },
      { text: "Nothing is regenerated and no backend export endpoint exists.", style: "dim" },
      { text: "" },
      { prefix: `${GLYPH.pointer} `, value: overlay.value, cursor: overlay.cursor, placeholder: "(required)" },
      { text: "" },
      { text: "relative paths resolve against the working directory; ~ expands to home", style: "dim" },
    ];
    if (overlay.error) lines.push({ text: overlay.error, style: "error" });
    if (overlay.busy) lines.push({ text: "writing…", style: "dim" });
    return { kind: "exportPackage", title: "Export package", lines, width, height, scroll: state.scroll.overlay ?? 0 };
  }

  if (overlay.kind === "providerSettings") {
    const draft = state.providerDraft;
    // The draft belongs to the overlay; without it there is nothing to edit.
    if (!draft) return null;
    const values = draft.values;
    const field = draft.field;
    const options = Array.isArray(draft.options) ? draft.options : [];
    const selected = draft.selected?.label ?? null;
    // One label column for every row so the values line up under each other.
    const describe = (...parts) => `${padTo(parts[0], 11)}${parts.slice(1).filter(Boolean).join(" · ")}`;
    const providerLine =
      field === "provider"
        ? { text: `${GLYPH.pointer} ${describe("provider:", values.provider, `(enter or tab: ${options.join(" · ")})`)}`, style: "bold" }
        : { text: `  ${describe("provider:", values.provider)}`, style: "dim" };
    const modelLine = field === "model"
      ? { text: `${GLYPH.pointer} ${describe("model:", selected ?? "none selected", "(enter opens the provider's list)")}`, style: "bold" }
      : { text: `  ${describe("model:", selected ?? "none selected")}`, style: "dim" };
    const models = state.models ?? {};
    const lines = [
      { text: "Saved automatically through POST /provider/update — there is no separate save step.", style: "dim" },
      { text: "Changing the provider re-reads its models; choosing one writes the whole configuration.", style: "dim" },
      { text: "" },
      providerLine,
      fieldLine("endpoint", values.endpoint, draft.cursors.endpoint, field === "endpoint", "(required)"),
      fieldLine("api key", values.apiKey, draft.cursors.apiKey, field === "apiKey", "local · openai-compatible only"),
      modelLine,
      { text: "" },
      { text: `  ${describe("saved:", draft.saved?.provider ?? UNAVAILABLE, draft.saved?.model ?? "no model recorded")}`, style: "dim" },
      { text: `  ${describe("available:", modelStatusText(models))}`, style: models.state === "failed" ? "error" : "dim" },
      { text: "" },
      { text: "enter saves this configuration · ctrl+p re-reads the endpoint (changes nothing)", style: "dim" },
      { text: "the model is chosen from the provider's list, never typed", style: "dim" },
    ];
    if (draft.error) lines.push({ text: "", style: "dim" }, { text: draft.error, style: "error" });
    if (draft.busy) lines.push({ text: "applying…", style: "dim" });
    return { kind: "providerSettings", title: "Provider configuration", lines, width, height, scroll: state.scroll.overlay ?? 0 };
  }

  if (overlay.kind === "modelSelect") {
    const draft = state.providerDraft ?? {};
    const models = state.models ?? {};
    const filter = String(overlay.filter ?? "");
    const rows = app.visibleModels();
    const cursor = clamp(overlay.cursor ?? 0, 0, Math.max(0, rows.length - 1));
    const header = [
      { text: `provider ${draft.values?.provider ?? UNAVAILABLE} · ${draft.values?.endpoint || UNAVAILABLE}`, style: "dim" },
      { text: modelStatusText(models), style: models.state === "failed" ? "error" : "dim" },
      { text: "" },
    ];
    if (overlay.filterActive || filter) {
      header.push({ prefix: `${GLYPH.pointer} `, value: filter, cursor: overlay.filterCursor ?? filter.length, placeholder: "filter models…" });
    }
    // The list follows the highlight, exactly like every other list pane.
    const listHeight = Math.max(1, height - header.length - 1);
    const window = followWindow(cursor, rows.length, listHeight);
    const body = [];
    if (window.above || window.below) {
      body.push({ text: moreMarker(window), style: "dim" });
    }
    if (rows.length === 0) {
      body.push({
        text: models.state === "ready" ? "no model matches the filter" : "no models to show",
        style: "dim",
      });
    }
    for (let index = window.start; index < window.end; index += 1) {
      const model = rows[index];
      const here = index === cursor;
      const marks = [
        draft.saved?.model && model.label === draft.saved.model ? "saved" : null,
        draft.selected?.label === model.label ? "selected" : null,
      ].filter(Boolean);
      const quantization = model.quantization && model.quantization !== "unknown" ? ` ${model.quantization}` : "";
      const label = truncate(`${model.label}${quantization}`, Math.max(12, width - 16 - marks.join(" · ").length));
      body.push({
        text: `${here ? GLYPH.pointer : " "} ${label}${marks.length ? `  (${marks.join(" · ")})` : ""}`,
        style: here ? "bold" : "dim",
      });
    }
    const current = rows[cursor];
    if (current?.warning) {
      for (const piece of wrapToWidth(current.warning, Math.max(20, width - 2))) body.push({ text: piece, style: "dim" });
    }
    if (models.state === "failed" && models.errorDetails) {
      for (const piece of wrapToWidth(models.errorDetails, Math.max(20, width - 2))) body.push({ text: piece, style: "dim" });
    }
    return {
      kind: "modelSelect",
      title: `Select model · ${rows.length} available`,
      lines: [...header, ...body],
      width,
      height,
      list: { height: listHeight },
      scroll: state.scroll.overlay ?? 0,
    };
  }

  if (overlay.kind === "pipelineSettings") {
    const settings = state.appSettings ?? {};
    const cursor = overlay.cursor ?? 0;
    const items = Array.isArray(overlay.items) ? overlay.items : [];
    const lines = [
      { text: "Changes are saved automatically through POST /settings/cognee, then re-read.", style: "dim" },
      { text: "" },
    ];
    items.forEach((setting, index) => {
      const value = settings[setting.key];
      const state_ = value === undefined || value === null ? UNAVAILABLE : value ? "enabled" : "disabled";
      lines.push({
        text: `${index === cursor ? GLYPH.pointer : " "} ${padTo(setting.label, 28)}${state_}`,
        style: index === cursor ? "bold" : "dim",
      });
      lines.push({ text: `    ${setting.help}`, style: "dim" });
    });
    lines.push({ text: "" });
    if (state.settingsBusy) lines.push({ text: "saving…", style: "dim" });
    if (state.settingsError) lines.push({ text: state.settingsError, style: "error" });
    lines.push({ text: "provider and model are editable with e in Settings · storage engines are fixed by the backend", style: "dim" });
    return { kind: "pipelineSettings", title: "Pipeline settings", lines, width, height, scroll: state.scroll.overlay ?? 0 };
  }

  const pkg = overlay.package ?? {};
  const meta = [
    `repository: ${pkg.repository_name || UNAVAILABLE}${pkg.repository_branch ? ` · ${pkg.repository_branch}` : ""}${pkg.repository_commit ? ` @ ${String(pkg.repository_commit).slice(0, 8)}` : ""}`,
    `task: ${pkg.task || pkg.objective || UNAVAILABLE}`,
    `${formatCount(pkg.token_estimate)} tokens · ${formatCount(pkg.section_count)} sections · saved ${formatRelativeTime(pkg.created_at, state.nowMs)}`,
    pkg.updated_at && pkg.updated_at !== pkg.created_at ? `updated ${formatRelativeTime(pkg.updated_at, state.nowMs)}` : null,
    `id: ${pkg.id ?? UNAVAILABLE}`,
  ].filter(Boolean);
  const markdownLines = formatMarkdown(pkg.markdown ?? "", {
    rendered: state.markdownView === "rendered",
    width: Math.max(20, width - 2),
  });
  const actions =
    "c copies this markdown · r re-synthesizes it · a appends · e exports · esc closes · d deletes from the Context list";
  const lines = [
    ...meta.map((text) => ({ text, style: "dim" })),
    { text: "" },
    { text: GLYPH.rule.repeat(Math.max(10, Math.min(width - 2, cols - 2))), style: "dim" },
    { text: "" },
    ...markdownLines.map((text) => ({ text })),
    { text: "" },
    { text: actions, style: "dim" },
  ];
  return {
    kind: "viewPackage",
    // The presentation mode leads the title so it survives title truncation.
    title: `${state.markdownView} · ${pkg.name ?? "package"}`,
    lines,
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
    for (const line of model.operation.lines) lines.push(fit(paint(line), model.cols));
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
  const header = [];

  if (list.filterActive || list.filter) {
    const prefix = list.filterActive ? `${GLYPH.pointer} ` : "filter: ";
    const body = list.filterActive
      ? editorText(list.filter, list.filterCursor, styler, "type to filter…")
      : truncate(list.filter, Math.max(4, width - prefix.length));
    header.push(fit(`${styler.dim(prefix)}${body}`, width));
  }

  if (model.view.banner && !model.view.inspector.open) {
    for (const line of model.view.banner.lines) {
      const paint = model.view.banner.level === "error" ? styler.err : styler.warn;
      header.push(fit(paint(truncate(line, width)), width));
    }
  }

  // The height was fixed when the view was built, so the published scroll
  // bound and this window always agree.
  const height = list.height;
  // Cursor-driven lists follow the selection; the system report is a plain
  // offset pane (its "cursor" is the scroll position itself).
  const window = list.offsetMode
    ? offsetWindow(list.cursor, list.rows.length, height)
    : followWindow(list.cursor, list.rows.length, height);
  const lines = [titleRule(list.title, list.subtitle, width, styler, list.focused, moreMarker(window)), ...header];

  if (list.rows.length === 0) {
    lines.push(fit(styler.dim(list.empty ?? "nothing to show"), width));
    return lines;
  }

  for (let index = window.start; index < window.end; index += 1) {
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
  const height = Math.max(1, model.layout.bodyRows - 1);
  const window = offsetWindow(inspector.scroll ?? 0, inspector.lines.length, height);
  const lines = [titleRule(inspector.title, null, width, styler, inspector.focused, moreMarker(window))];
  for (let index = window.start; index < window.end; index += 1) {
    const entry = inspector.lines[index];
    const text = entry.cells ? joinCells(entry.cells, styler, width) : String(entry.text ?? "");
    lines.push(fit(text, width));
  }
  return lines;
}

/**
 * A pane title with its rule. `more` is the restrained scroll marker
 * (`↑ more` / `↓ more` / `↑↓ more`), drawn right-aligned inside the rule and
 * only when the pane actually has content beyond the window.
 */
function titleRule(title, subtitle, width, styler, focused, more = "") {
  const label = subtitle ? `${title} · ${subtitle}` : title;
  const marker = focused ? `${GLYPH.pointer} ` : "";
  const tail = more ? `${more} ` : "";
  const head = truncate(`${marker}${label} `, Math.max(4, width - 2 - tail.length));
  const rule = GLYPH.rule.repeat(Math.max(0, width - head.length - tail.length - 1));
  const styled = focused ? styler.bold(head) : styler.dim(head);
  const suffix = tail ? styler.dim(tail) : "";
  return `${styled}${suffix}${styler.rule(rule)}`;
}

function overlayLines(model, styler) {
  const overlay = model.overlay;
  const height = Math.max(1, model.layout.bodyRows - 2);
  const window = offsetWindow(overlay.scroll ?? 0, overlay.lines.length, height);
  const lines = [titleRule(overlay.title, null, model.cols, styler, true, moreMarker(window)), ""];
  const start = window.start;
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
