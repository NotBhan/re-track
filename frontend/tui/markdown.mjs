/**
 * RE:Track TUI markdown presentation.
 *
 * Presentation only: the same backend string is either rendered for terminal
 * reading or printed verbatim. This module never rewrites, regenerates, or
 * truncates the source content — only its presentation.
 */

import { wrapToWidth } from "./layout.mjs";
import { truncate } from "./layout.mjs";

const FENCE = /^\s*(```|~~~)(.*)$/;
const HEADING = /^(#{1,6})\s+(.*)$/;
const LIST_ITEM = /^(\s*)([-*+]|\d+\.)\s+(.*)$/;
const QUOTE = /^\s*>\s?(.*)$/;
const RULE = /^\s*(-{3,}|\*{3,}|_{3,})\s*$/;
const TABLE_ROW = /^\s*\|.*\|\s*$/;

function inline(text) {
  // Keep the source characters; only code spans lose their backticks so the
  // rendered view reads like prose. Nothing is invented.
  return String(text).replace(/`([^`]+)`/g, "$1").replace(/\*\*([^*]+)\*\*/g, "$1");
}

/**
 * Format markdown into display lines.
 *
 * @param {string} markdown exact backend markdown
 * @param {{rendered?: boolean, width?: number, styler?: object}} [options]
 * @returns {string[]} lines (unpadded; the renderer fits them to the pane)
 */
export function formatMarkdown(markdown, options = {}) {
  const text = String(markdown ?? "");
  if (options.rendered === false) {
    // Raw mode: byte-exact source, no styling, no wrapping.
    return text.split("\n");
  }

  const width = Math.max(16, options.width ?? 80);
  const styler = options.styler ?? { bold: (t) => t, dim: (t) => t, rule: (t) => t };
  const lines = [];
  let inFence = false;
  let fenceTag = "";

  for (const raw of text.split("\n")) {
    const fence = raw.match(FENCE);
    if (fence) {
      inFence = !inFence;
      if (inFence) {
        fenceTag = fence[2].trim();
        lines.push(styler.dim(`${"─".repeat(3)}${fenceTag ? ` ${fenceTag} ` : " "}`.padEnd(Math.min(24, width), "─")));
      } else {
        lines.push(styler.dim("─".repeat(Math.min(24, width))));
      }
      continue;
    }

    if (inFence) {
      lines.push(`  ${styler.dim(raw)}`);
      continue;
    }

    const heading = raw.match(HEADING);
    if (heading) {
      const level = heading[1].length;
      const title = inline(heading[2]);
      if (level <= 2) {
        lines.push(styler.bold(title));
        lines.push(styler.dim("─".repeat(Math.min(width, Math.max(8, title.length)))));
      } else {
        lines.push(styler.bold(title));
      }
      continue;
    }

    if (RULE.test(raw)) {
      lines.push(styler.dim("─".repeat(Math.min(width, 32))));
      continue;
    }

    const quote = raw.match(QUOTE);
    if (quote) {
      for (const piece of wrapToWidth(inline(quote[1]), width - 2)) {
        lines.push(styler.dim(`▏ ${piece}`));
      }
      continue;
    }

    const item = raw.match(LIST_ITEM);
    if (item) {
      const indent = " ".repeat(Math.min(item[1].length, 6));
      const marker = /^\d/.test(item[2]) ? item[2] : "•";
      const body = wrapToWidth(inline(item[3]), width - indent.length - marker.length - 1);
      lines.push(`${indent}${marker} ${body[0] ?? ""}`);
      for (const extra of body.slice(1)) {
        lines.push(`${indent}${" ".repeat(marker.length + 1)}${extra}`);
      }
      continue;
    }

    if (TABLE_ROW.test(raw)) {
      // Tables are passed through unwrapped; inventing a reflow would change
      // the meaning of the source alignment.
      lines.push(truncate(raw.trim(), width));
      continue;
    }

    if (raw.trim() === "") {
      lines.push("");
      continue;
    }

    for (const piece of wrapToWidth(inline(raw), width)) lines.push(piece);
  }

  return lines;
}
