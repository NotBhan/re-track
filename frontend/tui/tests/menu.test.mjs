/**
 * Menu control suite: Torlink-style navigation, input precedence, focus rules
 * and the footer/help rendering contract.
 *
 * The control map (keymap.mjs) is the single source of truth: every hint the
 * footer shows must exist in the `?` sheet, movement wraps like the reference
 * implementation, and an overlay or text field owns the keyboard outright.
 */

/* eslint-disable no-control-regex -- the suite measures the ANSI escapes frames embed */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { buildModel, composeFrame, composeLines, createPlainStyler } from "../render.mjs";
import { createStyler } from "../theme.mjs";
import { CONTEXTS, HELP_GROUPS, HINTS, footerHints } from "../keymap.mjs";
import { char, key, plain, settle, startApp } from "./fixtures.mjs";

const ANSI = /\u001b\[[0-9;]*m/g;
const strip = (text) => String(text).replace(ANSI, "");
const text = (lines) => lines.join("\n");

function frame(app, cols, rows, options = {}) {
  const styler = options.styler ?? plain;
  const model = buildModel(app, { cols, rows, spinnerFrame: options.spinnerFrame ?? 0 });
  // Mirror the entry point: the layout facts the state layer needs are published here.
  app.setViewport({
    pageSize: Math.max(3, model.view.list.height - 1),
    inspectorMax: model.scrollMax.inspector,
    systemMax: model.scrollMax.system,
    viewerMax: model.scrollMax.viewer,
    sideBySide: model.layout.sideBySide,
  });
  return { model, lines: composeLines(model, styler).map(strip) };
}

const footerOf = (app, cols, rows = 30) => frame(app, cols, rows).lines.at(-1);

describe("menu: navigation", () => {
  it("moves the active destination with ↑↓ and wraps at both ends", async () => {
    const { app } = await startApp();
    app.dispatch(key("tab"));
    assert.equal(app.getState().focus, "rail");

    app.dispatch(key("down"));
    assert.equal(app.getState().view, "code");
    app.dispatch(key("down"));
    assert.equal(app.getState().view, "context");

    app.dispatch(key("up"));
    assert.equal(app.getState().view, "code");

    // Wrapping matches the reference movement helper (wrapStep).
    app.dispatch(key("up"));
    app.dispatch(key("up"));
    assert.equal(app.getState().view, "settings", "wraps past the first entry");
    app.dispatch(key("down"));
    assert.equal(app.getState().view, "repositories", "wraps past the last entry");
    await settle();
  });

  it("activates the selection with enter by moving focus into the list", async () => {
    const { app } = await startApp();
    app.dispatch(key("tab"));
    app.dispatch(key("down"));
    assert.equal(app.getState().view, "code");
    assert.equal(app.getState().focus, "rail");

    app.dispatch(key("enter"));
    assert.equal(app.getState().focus, "list", "enter activates the destination");
    assert.equal(app.getState().view, "code", "activation does not change the destination");

    app.dispatch(key("down"));
    assert.equal(app.getState().cursors.code !== undefined, true);
  });

  it("supports vim movement aliases for the menu and the list", async () => {
    const { app } = await startApp();
    app.dispatch(key("tab"));
    app.dispatch(char("j"));
    assert.equal(app.getState().view, "code");
    app.dispatch(char("k"));
    assert.equal(app.getState().view, "repositories");

    app.dispatch(key("enter"));
    app.dispatch(char("j"));
    assert.equal(app.getState().cursors.repositories, 1);
    app.dispatch(char("k"));
    assert.equal(app.getState().cursors.repositories, 0);
  });

  it("moves between panes with ←→ and h l", async () => {
    const { app } = await startApp();
    app.dispatch(char("h"));
    assert.equal(app.getState().focus, "rail");
    app.dispatch(char("l"));
    assert.equal(app.getState().focus, "list");
    app.dispatch(key("left"));
    assert.equal(app.getState().focus, "rail");
    app.dispatch(key("right"));
    assert.equal(app.getState().focus, "list");
  });

  it("keeps numeric shortcuts as fast access", async () => {
    const { app } = await startApp();
    for (const [digit, view] of [
      ["2", "code"],
      ["3", "context"],
      ["4", "system"],
      ["5", "settings"],
      ["1", "repositories"],
    ]) {
      app.dispatch(char(digit));
      assert.equal(app.getState().view, view);
    }
    await settle();
  });

  it("preserves each destination's cursor and scroll state across menu switches", async () => {
    const { app } = await startApp();
    app.dispatch(key("down"));
    assert.equal(app.getState().cursors.repositories, 1);

    app.dispatch(key("tab"));
    app.dispatch(key("down"));
    app.dispatch(key("down"));
    app.dispatch(key("enter"));
    assert.equal(app.getState().view, "context");
    assert.equal(app.getState().cursors.repositories, 1, "the repository cursor is not reset by menu movement");

    app.dispatch(key("tab"));
    app.dispatch(key("up"));
    app.dispatch(key("enter"));
    assert.equal(app.getState().view, "code");
    assert.equal(app.getState().cursors.repositories, 1);
  });
});

describe("menu: input precedence", () => {
  it("lets an open overlay own the keyboard without leaking to the view", async () => {
    const { app } = await startApp();
    app.dispatch(char("a"));
    assert.equal(app.getState().overlay.kind, "addRepo");

    app.dispatch(char("3"));
    app.dispatch(char("q"));
    assert.equal(app.getState().view, "repositories", "digits do not switch views");
    assert.equal(app.getState().overlay.kind, "addRepo", "q does not quit");
    assert.equal(app.getState().overlay.values.path, "3q");

    app.dispatch(key("escape"));
    assert.equal(app.getState().overlay, null);
  });

  it("keeps the arrow keys inside a form field", async () => {
    const { app } = await startApp();
    app.dispatch(char("a"));
    for (const value of "abc") app.dispatch(char(value));
    assert.equal(app.getState().overlay.values.path, "abc");

    app.dispatch(key("left"));
    app.dispatch(char("X"));
    assert.equal(app.getState().overlay.values.path, "abXc");
    assert.equal(app.getState().overlay.cursors.path, 3);

    app.dispatch(key("up"));
    assert.equal(app.getState().overlay.field, "name", "↑↓ moves between fields");
    assert.equal(app.getState().cursors.repositories, 0, "the list cursor never moved");
  });

  it("lets the filter capture input and leave the field on ↓", async () => {
    const { app } = await startApp();
    app.dispatch(char("/"));
    for (const value of "service") app.dispatch(char(value));
    assert.equal(app.getState().view, "repositories");
    assert.equal(app.getState().filter, "service");

    app.dispatch(key("left"));
    app.dispatch(char("X"));
    assert.equal(app.getState().filter, "servicXe", "the cursor is real, not end-anchored");
    app.dispatch(key("backspace"));
    assert.equal(app.getState().filter, "service");

    assert.equal(app.getState().focus, "list");
    app.dispatch(key("down"));
    assert.equal(app.getState().filterActive, false, "↓ leaves the field for the list");
    assert.equal(app.getState().filter, "service", "the filter stays applied");

    app.dispatch(key("down"));
    assert.equal(app.getState().cursors.repositories, 1, "↓ now moves the list selection");
  });

  it("gives the help sheet the next key, except while scrolling it", async () => {
    const { app } = await startApp();
    app.dispatch(char("?"));
    assert.equal(app.getState().overlay.kind, "help");

    app.setViewport({ viewerMax: 12 });
    app.dispatch(key("down"));
    assert.equal(app.getState().overlay.kind, "help", "scroll keys do not dismiss the sheet");
    assert.equal(app.getState().scroll.viewer, 1);

    app.dispatch(char("x"));
    assert.equal(app.getState().overlay, null, "any other key closes the sheet");
  });

  it("runs global keys when nothing higher owns input", async () => {
    const { app, client } = await startApp();
    const before = client.calls.length;
    app.dispatch(char("r"));
    await settle();
    assert.ok(client.calls.length > before, "r refreshed from the backend");

    app.dispatch(char("?"));
    assert.equal(app.getState().overlay.kind, "help");
  });
});

describe("menu: focus", () => {
  it("enters the detail mode and restores the list focus deterministically", async () => {
    const { app } = await startApp();
    app.setViewport({ sideBySide: false });

    app.dispatch(key("enter"));
    assert.equal(app.getState().inspectorOpen, true);
    assert.equal(app.getState().focus, "inspector", "the detail owns the keyboard while open");

    app.dispatch(key("escape"));
    assert.equal(app.getState().inspectorOpen, false);
    assert.equal(app.getState().focus, "list");
  });

  it("closes the mode when focus leaves it below the breakpoint and keeps it above", async () => {
    const medium = await startApp();
    medium.app.setViewport({ sideBySide: false });
    medium.app.dispatch(key("enter"));
    medium.app.dispatch(key("tab"));
    assert.equal(medium.app.getState().focus, "rail");
    assert.equal(medium.app.getState().inspectorOpen, false, "the medium detail mode closes on focus loss");

    const wide = await startApp();
    wide.app.setViewport({ sideBySide: true });
    wide.app.dispatch(key("enter"));
    assert.equal(wide.app.getState().focus, "inspector");
    wide.app.dispatch(key("tab"));
    assert.equal(wide.app.getState().focus, "rail");
    assert.equal(wide.app.getState().inspectorOpen, true, "the wide inspector is a pane, not a mode");
  });

  it("never focuses a hidden inspector", async () => {
    const { app } = await startApp();
    app.setViewport({ sideBySide: true });
    assert.equal(app.getState().inspectorOpen, false);
    for (let step = 0; step < 5; step += 1) {
      app.dispatch(key("tab"));
      assert.notEqual(app.getState().focus, "inspector");
    }
  });

  it("closes an open detail when the destination changes below the breakpoint", async () => {
    const { app } = await startApp();
    app.setViewport({ sideBySide: false });
    app.dispatch(key("enter"));
    assert.equal(app.getState().inspectorOpen, true);

    app.dispatch(key("tab"));
    app.dispatch(key("down"));
    assert.equal(app.getState().view, "code");
    assert.equal(app.getState().inspectorOpen, false, "the detail never covers the new list");
    assert.equal(app.getState().focus, "rail");
  });

  it("walks back with escape: detail → list → menu", async () => {
    const { app } = await startApp();
    app.setViewport({ sideBySide: true });
    app.dispatch(key("enter"));
    assert.equal(app.getState().focus, "inspector");

    app.dispatch(key("escape"));
    assert.equal(app.getState().focus, "list");
    app.dispatch(key("escape"));
    assert.equal(app.getState().focus, "rail");
    app.dispatch(key("escape"));
    assert.equal(app.getState().focus, "rail", "the menu is the top of the chain");
  });

  it("clears an applied filter before walking back to the menu", async () => {
    const { app } = await startApp();
    app.dispatch(char("/"));
    app.dispatch(char("alpha"));
    app.dispatch(key("enter"));
    assert.equal(app.getState().filterActive, false);
    assert.equal(app.getState().filter, "alpha");

    app.dispatch(key("escape"));
    assert.equal(app.getState().filter, "", "escape clears the applied filter first");
    assert.equal(app.getState().focus, "list");
    app.dispatch(key("escape"));
    assert.equal(app.getState().focus, "rail");
  });
});

describe("menu: rendering", () => {
  it("marks the focused menu without color while the active destination stays marked", async () => {
    const { app } = await startApp();
    const listFocused = text(frame(app, 120, 30).lines);
    assert.doesNotMatch(listFocused, /▍ Workspace/);
    assert.match(listFocused, /▍ Repositories \(2\)/, "the active destination keeps its marker");

    app.dispatch(key("tab"));
    const railFocused = text(frame(app, 120, 30).lines);
    assert.match(railFocused, /▍ Workspace/, "focus is visible without color");
    assert.match(railFocused, /▍ Repositories \(2\)/);
  });

  it("shows the contextual footer and keeps every hint whole", async () => {
    const { app } = await startApp();
    const wide = footerOf(app, 120);
    assert.match(wide, /↑↓ move/);
    assert.match(wide, /enter open/);
    assert.match(wide, /\? keys/);

    // A hint is either shown whole or not shown at all — never cut mid-label.
    const shown = (footer, hint) => {
      const keys = hint.keys.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const present = new RegExp(`(^|\\s)${keys}(\\s|$)`).test(footer);
      return present ? footer.includes(`${hint.keys} ${hint.label}`) : null;
    };

    for (const cols of [48, 60, 90, 120]) {
      const footer = footerOf(app, cols);
      assert.equal(footer.length, cols, `footer width at ${cols}`);
      for (const hint of footerHints("repositories", app.getState())) {
        assert.notEqual(
          shown(footer, hint),
          false,
          `hint "${hint.keys} ${hint.label}" is clipped at ${cols} columns`
        );
      }
      assert.match(footer, /\? keys/, `the help affordance survives ${cols} columns`);
    }

    // Narrow terminals show fewer hints rather than wrapping or clipping.
    const countAt = (cols) =>
      footerHints("repositories", app.getState()).filter((hint) => shown(footerOf(app, cols), hint) === true).length;
    assert.ok(countAt(48) < countAt(120), "the hint count shrinks with the terminal");

    app.dispatch(key("tab"));
    assert.match(footerOf(app, 120), /↑↓ view/, "the rail advertises menu movement");
    assert.match(footerOf(app, 120), /q quit/, "the rail advertises quitting");
    app.dispatch(key("enter"));
    app.dispatch(char("/"));
    assert.match(footerOf(app, 120), /enter apply/, "the filter advertises its own controls");
  });

  it("derives the footer and the help sheet from the same control map", () => {
    for (const [id, hint] of Object.entries(HINTS)) {
      const listed = HELP_GROUPS.some((group) =>
        group.hints.some(([keys, label]) => keys === hint.keys && label === hint.help)
      );
      assert.ok(listed, `${id} is advertised but missing from the help sheet`);
    }
    for (const context of Object.keys(CONTEXTS)) {
      for (const hint of footerHints(context, { markdownView: "rendered" })) {
        const known = Object.values(HINTS).some((candidate) => {
          const label = typeof candidate.footer === "function" ? candidate.footer({ markdownView: "rendered" }) : candidate.footer;
          return candidate.keys === hint.keys && label === hint.label;
        });
        assert.ok(known, `${context}: "${hint.keys} ${hint.label}" is not in the control map`);
      }
    }
  });

  it("lists every help group in the ? sheet and scrolls it on short terminals", async () => {
    const { app } = await startApp();
    app.dispatch(char("?"));
    // A tall terminal shows the complete reference in one frame; a shorter one
    // scrolls (checked below) instead of dropping entries.
    const wide = text(frame(app, 120, 84).lines);
    for (const group of HELP_GROUPS) assert.match(wide, new RegExp(group.title));
    assert.match(wide, /Indexing and synthesis/, "the reference keeps its notes when it fits");

    frame(app, 48, 16); // publishes the scroll bound for a short terminal
    app.dispatch(key("end"));
    assert.ok(app.getState().scroll.viewer > 0, "the sheet scrolls instead of being truncated");
  });

  it("renders an obvious input cursor in both styling modes", async () => {
    const { app } = await startApp();
    app.dispatch(char("3"));
    app.dispatch(char("n"));
    for (const value of "abc") app.dispatch(char(value));
    app.dispatch(key("left"));

    const monochrome = text(frame(app, 100, 24).lines);
    assert.match(monochrome, /▏/, "the caret marks the insertion point without color");

    const styled = composeLines(buildModel(app, { cols: 100, rows: 24 }), createStyler({ enabled: true })).join("\n");
    assert.match(styled, /\u001b\[7m/, "the cursor cell inverts when styling is available");

    const raw = composeFrame(buildModel(app, { cols: 100, rows: 24 }), { styler: plain });
    assert.ok(!/\u001b\[[0-9;]*m/.test(raw), "NO_COLOR output stays free of escapes");
  });

  it("keeps the plain styler's frames escape-free after the menu changes", async () => {
    const { app } = await startApp();
    app.dispatch(key("tab"));
    const model = buildModel(app, { cols: 120, rows: 30 });
    const lines = composeLines(model, createPlainStyler()).join("\n");
    assert.ok(!lines.includes("\u001b"), "no styling escapes in monochrome output");
    assert.match(lines, /▍ Workspace/);
  });
});
