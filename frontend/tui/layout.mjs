/**
 * RE:Track TUI layout arithmetic and text fitting.
 *
 * Pure helpers: frame budgets, responsive classes, list scrolling windows, and
 * width-aware text fitting. Nothing here touches the backend or the terminal.
 */

export const MIN_COLS = 48;
export const MIN_ROWS = 12;
export const COMPACT_ROWS = 18;
export const SIDE_BY_SIDE_COLS = 110;

export const NAV_LABELS = Object.freeze(["Repositories", "Code", "Context", "System", "Settings"]);

const LONGEST_NAV_LABEL = NAV_LABELS.reduce((max, label) => Math.max(max, label.length), 0);

export function clamp(value, min, max) {
  if (Number.isNaN(value)) return min;
  return Math.min(Math.max(value, min), max);
}

/** Cyclic step that is safe for negative deltas (list wrap-around). */
export function wrapStep(current, delta, length) {
  if (length <= 0) return 0;
  return (((current + delta) % length) + length) % length;
}

/* ------------------------------- scrolling -------------------------------- */
/*
 * One scrolling model for every surface, in two flavours:
 *
 *   followWindow  cursor-driven lists — the window follows the selection
 *   offsetWindow  offset-driven panes — the window starts at the scroll value
 *
 * Both return the same shape ({ start, end, above, below }) so panes render
 * their slice and their "more content" marker from one calculation. These are
 * pure: state owns the cursor/offset, the renderer owns the geometry.
 */

/** Largest usable offset for a pane of `height` rows showing `total` rows. */
export function scrollMax(total, height) {
  return Math.max(0, Math.floor(total) - Math.max(1, Math.floor(height)));
}

/** Page jump for a pane: a page keeps one row of overlap (Torlink's rule). */
export function pageStep(height) {
  return Math.max(1, Math.floor(height) - 1);
}

/** Cursor-following window: keeps the selection visible and roughly centred. */
export function followWindow(cursor, total, height) {
  const rows = Math.max(1, Math.floor(height));
  const count = Math.max(0, Math.floor(total));
  const start = count <= rows ? 0 : clamp(Math.floor(cursor) - Math.floor(rows / 2), 0, count - rows);
  return { start, end: Math.min(count, start + rows), above: start > 0, below: start + rows < count };
}

/** Offset window: the window starts at the scroll value, clamped to the content. */
export function offsetWindow(offset, total, height) {
  const rows = Math.max(1, Math.floor(height));
  const count = Math.max(0, Math.floor(total));
  const start = clamp(Math.floor(offset) || 0, 0, scrollMax(count, rows));
  return { start, end: Math.min(count, start + rows), above: start > 0, below: start + rows < count };
}

/** First visible row for a cursor inside a window of `height` rows. */
export function windowStart(cursor, total, height) {
  return followWindow(cursor, total, height).start;
}

/**
 * Restrained "more content" marker: shown only on the side that actually has
 * more, and never colour-dependent.
 */
export function moreMarker(window) {
  if (!window) return "";
  if (window.above && window.below) return "↑↓ more";
  if (window.above) return "↑ more";
  if (window.below) return "↓ more";
  return "";
}

export function truncate(text, width, ellipsis = "…") {
  const value = String(text ?? "");
  if (width <= 0) return "";
  if (value.length <= width) return value;
  if (width <= ellipsis.length) return value.slice(0, width);
  return `${value.slice(0, width - ellipsis.length)}${ellipsis}`;
}

/** Right-pad to an exact width (truncating first) so columns line up. */
export function padTo(text, width) {
  const value = truncate(text, width);
  return value + " ".repeat(Math.max(0, width - value.length));
}

/** Left-pad to an exact width (numbers, sizes). */
export function padStart(text, width) {
  const value = truncate(text, width);
  return " ".repeat(Math.max(0, width - value.length)) + value;
}

/** Hard-wrap plain text to `width` columns on whitespace where possible. */
export function wrapToWidth(text, width) {
  const value = String(text ?? "");
  if (width <= 1) return value ? [truncate(value, Math.max(1, width))] : [];
  const lines = [];
  for (const paragraph of value.split("\n")) {
    if (paragraph.length <= width) {
      lines.push(paragraph);
      continue;
    }
    let current = "";
    for (const word of paragraph.split(/\s+/)) {
      if (!current) {
        current = word;
        continue;
      }
      if (current.length + 1 + word.length <= width) {
        current += ` ${word}`;
        continue;
      }
      lines.push(current);
      current = word;
    }
    if (current) lines.push(current);
  }
  return lines;
}

/**
 * Frame budget and responsive class for the current terminal size.
 *
 * Chrome accounting is explicit so degenerate sizes degrade by arithmetic:
 * header (1) + rule (0/1) + operation block (0..2 rows) + footer (1).
 * `operation` accepts the row count the operation block needs (a boolean is
 * still accepted as "one row").
 */
export function layoutFor({ cols, rows, operation = false }) {
  const tooSmall = cols < MIN_COLS || rows < MIN_ROWS;
  const compact = rows < COMPACT_ROWS;
  const showRule = !compact;
  const showBadges = cols >= 72;
  const railWidth = Math.min(22, 2 + LONGEST_NAV_LABEL + (showBadges ? 5 : 0));
  const operationRows = operation === true ? 1 : Math.max(0, Number(operation) || 0);
  const chrome = 1 + (showRule ? 1 : 0) + operationRows + 1;
  const bodyRows = Math.max(4, rows - chrome);
  const sideBySide = cols >= SIDE_BY_SIDE_COLS;
  const available = Math.max(20, cols - railWidth - 2);
  const listWidth = sideBySide ? Math.max(40, Math.round(available * 0.52)) : available;
  const inspectorWidth = sideBySide ? available - listWidth - 1 : available;

  return {
    tooSmall,
    compact,
    showRule,
    showBadges,
    showFooter: true,
    railWidth,
    chrome,
    bodyRows,
    sideBySide,
    listWidth,
    inspectorWidth,
    footerHints: compact ? 3 : 6,
  };
}
