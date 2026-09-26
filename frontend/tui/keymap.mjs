/**
 * RE:Track TUI control map.
 *
 * The single source of truth for every control the interface advertises: the
 * footer renders the terse hints of the active context and the `?` sheet
 * renders the complete reference, both derived from HINTS/CONTEXTS here, so the
 * two can never disagree.
 *
 * Context resolution follows the interaction precedence (an open overlay owns
 * input before the focused region does). Hint order is priority order: the
 * footer stops adding hints when its row is full instead of wrapping or
 * clipping them.
 *
 * Navigation semantics mirror the Torlink interaction model: ↑↓ (or j k) move
 * the selection with wrap-around, enter activates, esc walks back one level,
 * tab cycles focus, and text capture owns the arrow keys while a field is live.
 */

const NAVIGATE = "Navigate";
const REPOSITORIES = "Repositories";
const CONTEXT = "Context";
const SYSTEM = "System";
const TEXT_INPUT = "Text input";
const DIALOGS = "Dialogs";

/** Every advertised control. `footer` is terse (or a function of state); `help` is descriptive. */
export const HINTS = Object.freeze({
  menuMove: { keys: "↑↓", footer: "view", help: "Move the menu selection (wraps)", group: NAVIGATE },
  listMove: { keys: "↑↓", footer: "move", help: "Move the selection (wraps)", group: NAVIGATE },
  scroll: { keys: "↑↓", footer: "scroll", help: "Scroll (page with PgUp/PgDn)", group: NAVIGATE },
  paneMove: { keys: "←→", footer: "pane", help: "Move between panes (← → or h l)", group: NAVIGATE },
  railOpen: { keys: "enter", footer: "open", help: "Move into the list for the destination", group: NAVIGATE },
  activate: { keys: "enter", footer: "open", help: "Open the detail for the selection", group: NAVIGATE },
  back: { keys: "esc", footer: "back", help: "Back one level: detail → list → menu", group: NAVIGATE },
  switchPane: { keys: "tab", footer: "pane", help: "Cycle focus: menu → list → detail", group: NAVIGATE },
  views: { keys: "1-4", footer: "views", help: "Jump to a destination (menu shortcut)", group: NAVIGATE },
  keys: { keys: "?", footer: "keys", help: "Show this control reference", group: NAVIGATE },
  quit: { keys: "q", footer: "quit", help: "Quit (terminal restored, backend stopped)", group: NAVIGATE },

  filter: { keys: "/", footer: "filter", help: "Filter the repository list", group: REPOSITORIES },
  add: { keys: "a", footer: "add", help: "Add a repository (path or GitHub URL)", group: REPOSITORIES },
  scan: { keys: "s", footer: "scan", help: "Scan the selected repository", group: REPOSITORIES },
  index: { keys: "i", footer: "index", help: "Index / re-index the selected repository", group: REPOSITORIES },
  deleteRepo: { keys: "d", footer: "delete", help: "Delete the repository (confirmation)", group: REPOSITORIES },

  newTask: { keys: "n", footer: "new task", help: "Describe a task and synthesize context", group: CONTEXT },
  contextOpen: { keys: "enter", footer: "open", help: "Open a package or prefill a task", group: CONTEXT },
  budget: { keys: "b", footer: "budget", help: "Cycle the token budget (2K / 4K / 8K)", group: CONTEXT },
  graph: { keys: "g", footer: "graph", help: "Toggle the AST graph in the request", group: CONTEXT },
  markdown: {
    keys: "m",
    footer: (state) => (state.markdownView === "rendered" ? "raw" : "rendered"),
    help: "Toggle rendered / raw markdown",
    group: CONTEXT,
  },
  savePackage: { keys: "S", footer: "save", help: "Save the context as a package", group: CONTEXT },
  deletePackage: { keys: "d", footer: "delete", help: "Delete the package (confirmation)", group: CONTEXT },

  exportDiagnostics: { keys: "e", footer: "export", help: "Export a diagnostics bundle", group: SYSTEM },
  refresh: { keys: "r", footer: "refresh", help: "Refresh every pane from the backend", group: SYSTEM },

  cursorMove: { keys: "←→", footer: "cursor", help: "Move the text cursor (home / end)", group: TEXT_INPUT },
  fieldExit: { keys: "↓", help: "Leave the field for the list", group: TEXT_INPUT },
  backspace: { keys: "backspace", help: "Delete before the cursor", group: TEXT_INPUT },
  ctrlEdits: { keys: "ctrl+u w k a e", help: "Clear · delete word · kill · home · end", group: TEXT_INPUT },

  submit: { keys: "enter", footer: "submit", help: "Submit the field or form", group: DIALOGS },
  cancel: { keys: "esc", footer: "cancel", help: "Cancel and close", group: DIALOGS },
  confirm: { keys: "enter", footer: "confirm", help: "Confirm the action", group: DIALOGS },
  sourceToggle: { keys: "tab", footer: "source", help: "Switch source (local / GitHub)", group: DIALOGS },
  fieldMove: { keys: "↑↓", footer: "field", help: "Move between fields", group: DIALOGS },
  filterApply: { keys: "enter", footer: "apply", help: "Keep the filter and return", group: DIALOGS },
  filterCancel: { keys: "esc", footer: "clear", help: "Clear the filter", group: DIALOGS },
  helpClose: { keys: "esc", footer: "close", help: "Close (any other key closes too)", group: DIALOGS },
  viewerClose: { keys: "esc", footer: "close", help: "Close the viewer", group: DIALOGS },
});

/** Footer hint ids per interaction context, in display priority order. */
export const CONTEXTS = Object.freeze({
  rail: ["menuMove", "railOpen", "switchPane", "keys", "quit"],
  list: ["listMove", "activate", "switchPane", "keys"],
  repositories: ["listMove", "activate", "add", "index", "deleteRepo", "filter", "keys"],
  context: ["listMove", "newTask", "contextOpen", "markdown", "savePackage", "keys"],
  system: ["scroll", "exportDiagnostics", "refresh", "keys"],
  inspector: ["scroll", "back", "switchPane", "keys"],
  filter: ["filterApply", "filterCancel", "cursorMove"],
  help: ["scroll", "helpClose"],
  confirm: ["confirm", "cancel"],
  // Submit and cancel lead every dialog: narrower terminals drop the secondary
  // field/source keys rather than the way out.
  addRepo: ["submit", "cancel", "sourceToggle", "fieldMove"],
  editor: ["submit", "cancel"],
  viewer: ["scroll", "markdown", "viewerClose"],
});

const GROUP_ORDER = Object.freeze([NAVIGATE, REPOSITORIES, CONTEXT, SYSTEM, TEXT_INPUT, DIALOGS]);

/** The `?` sheet: every hint, grouped for reference. Derived from HINTS. */
export const HELP_GROUPS = Object.freeze(
  GROUP_ORDER.map((title) => ({
    title,
    hints: Object.values(HINTS)
      .filter((hint) => hint.group === title)
      .map((hint) => [hint.keys, hint.help]),
  })).filter((group) => group.hints.length > 0)
);

/** Resolve the terse footer hints for a context. Help-only hints never appear here. */
export function footerHints(context, state = {}) {
  const ids = CONTEXTS[context] ?? CONTEXTS.list;
  return ids
    .map((id) => HINTS[id])
    .filter((hint) => hint.footer !== undefined)
    .map((hint) => ({
      keys: hint.keys,
      label: typeof hint.footer === "function" ? hint.footer(state) : hint.footer,
    }));
}
