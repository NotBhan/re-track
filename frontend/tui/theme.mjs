/**
 * RE:Track TUI styling, semantic vocabulary, and value formatting.
 *
 * Presentation only: no terminal writes, no backend access, no state. Every
 * helper here is pure so the renderer stays deterministic and testable.
 *
 * Color discipline (DESIGN-vercel.md, terminal translation): the interface is
 * monochrome ink with bold/dim/inverse hierarchy; the only colors are semantic
 * (ok / warn / error). Focus and selection are always expressed with glyphs and
 * emphasis, so they survive NO_COLOR.
 */

export const ESC = "\x1b[";

/** Single-cell glyphs only — no wide or emoji characters. */
export const GLYPH = Object.freeze({
  pointer: "▍",
  bullet: "•",
  dot: "·",
  check: "✓",
  warn: "⚠",
  cross: "✗",
  circle: "○",
  arrow: "→",
  ellipsis: "…",
  rule: "─",
  bar: "▌",
});

export const SPINNER_FRAMES = Object.freeze(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]);

const CODES = Object.freeze({
  bold: "1",
  dim: "2",
  inverse: "7",
  red: "31",
  green: "32",
  yellow: "33",
});

/**
 * Create a styler. `enabled: false` (non-TTY or NO_COLOR) makes every helper an
 * identity function so no escape codes leak into pipes or monochrome terminals.
 */
export function createStyler({ enabled = true } = {}) {
  const wrap = (code, text) => (enabled ? `${ESC}${code}m${text}${ESC}0m` : String(text));
  return {
    enabled,
    bold: (t) => wrap(CODES.bold, t),
    dim: (t) => wrap(CODES.dim, t),
    inverse: (t) => wrap(CODES.inverse, t),
    ok: (t) => wrap(CODES.green, t),
    warn: (t) => wrap(CODES.yellow, t),
    err: (t) => wrap(CODES.red, t),
    rule: (t) => wrap(CODES.dim, t),
  };
}

/** Semantic style for backend-reported states. Unknown states stay neutral. */
export function statusStyle(styler, state) {
  const value = String(state ?? "unknown");
  if (["healthy", "active", "indexed", "ok", "available", "ready", "verified"].includes(value)) {
    return styler.ok(value);
  }
  if (
    ["degraded", "indexing", "scanning", "analyzing", "registered", "partial", "queued", "not_extracted", "loading"].includes(
      value
    )
  ) {
    return styler.warn(value);
  }
  if (["error", "failed", "unavailable", "unreachable", "insufficient", "none", "not_configured", "not_analyzed"].includes(value)) {
    return styler.err(value);
  }
  return value;
}

/** Human label for an evidence state as reported by the engine. */
export function evidenceStateLabel(state) {
  const map = {
    sufficient: "Sufficient",
    partial: "Partial",
    insufficient: "Insufficient",
    none: "No evidence",
    index_unavailable: "Index unavailable",
    verified: "Verified",
  };
  return map[String(state ?? "").toLowerCase()] ?? String(state ?? "unavailable");
}

/**
 * The engine reports confidence as evidence-channel agreement only
 * (1.0 = symbols and snippets, 0.5 = exactly one channel, 0.0 = neither), so it
 * is rendered as a qualitative tier — never as a percentage.
 */
export function confidenceTier(confidence) {
  if (typeof confidence !== "number" || Number.isNaN(confidence)) {
    return { label: "Not computed", detail: "No confidence value returned by the engine" };
  }
  if (confidence >= 0.9) {
    return { label: "Cross-validated", detail: "Symbol and snippet evidence agree" };
  }
  if (confidence > 0) {
    return { label: "Single-channel", detail: "Grounded by one evidence channel" };
  }
  return { label: "Not computed", detail: "No matching symbols or snippets to cross-check" };
}

export const UNAVAILABLE = "unavailable";

export function formatBytes(bytes) {
  if (typeof bytes !== "number" || !Number.isFinite(bytes)) return UNAVAILABLE;
  if (bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const exp = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
  const value = bytes / 1024 ** exp;
  return `${value >= 10 || exp === 0 ? Math.round(value) : value.toFixed(1)} ${units[exp]}`;
}

export function formatCount(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return UNAVAILABLE;
  return String(value);
}

export function formatDuration(ms) {
  if (typeof ms !== "number" || !Number.isFinite(ms) || ms < 0) return UNAVAILABLE;
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

/** Relative time for ISO timestamps; returns `never`/`unavailable` honestly. */
export function formatRelativeTime(iso, nowMs = Date.now()) {
  if (!iso) return "never";
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return String(iso);
  const delta = Math.max(0, nowMs - then);
  const minutes = Math.floor(delta / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}

/** Compact non-numeric summary of a list field (languages, frameworks, …). */
export function summarizeList(values, limit = 3) {
  if (!Array.isArray(values) || values.length === 0) return "none";
  const shown = values.slice(0, limit).join(", ");
  return values.length > limit ? `${shown} +${values.length - limit}` : shown;
}
