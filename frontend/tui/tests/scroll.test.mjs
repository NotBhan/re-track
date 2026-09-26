/**
 * The scrolling model, end to end.
 *
 * Every surface that can grow past its pane is exercised against content that
 * is deliberately larger than the viewport, at the terminal sizes the interface
 * claims to support. Two properties matter throughout: content is reachable
 * (nothing is silently clipped) and each surface owns its own offset.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { followWindow, offsetWindow, pageStep, scrollMax, moreMarker, wrapStep } from "../layout.mjs";
import { HINTS } from "../keymap.mjs";
import { buildModel, composeLines } from "../render.mjs";
import {
  char,
  key,
  manyPackages,
  manyRepositories,
  manySymbols,
  plain,
  publishViewport,
  settle,
  startApp,
} from "./fixtures.mjs";

const SIZES = [
  [120, 40],
  [90, 24],
  [76, 24],
  [60, 20],
  [48, 16],
];

function frame(app, cols, rows) {
  const model = buildModel(app, { cols, rows, spinnerFrame: 0 });
  publishViewport(app, model);
  return { model, lines: composeLines(model, plain).map((line) => String(line)) };
}

const text = (lines) => lines.join("\n");

/* ------------------------------- the model -------------------------------- */

describe("scroll: window model", () => {
  it("clamps, follows the cursor and reports what is off-screen", () => {
    assert.deepEqual(followWindow(0, 10, 5), { start: 0, end: 5, above: false, below: true });
    assert.deepEqual(followWindow(9, 10, 5), { start: 5, end: 10, above: true, below: false });
    assert.equal(followWindow(5, 10, 5).start, 3, "the selection stays centred where it can");
    assert.deepEqual(followWindow(2, 3, 5), { start: 0, end: 3, above: false, below: false }, "short content never scrolls");
    assert.deepEqual(followWindow(0, 0, 5), { start: 0, end: 0, above: false, below: false });
  });

  it("windows offset panes and clamps the offset to the content", () => {
    assert.equal(offsetWindow(0, 100, 10).start, 0);
    assert.equal(offsetWindow(50, 100, 10).start, 50);
    assert.equal(offsetWindow(500, 100, 10).start, 90, "an over-scrolled offset clamps to the last page");
    assert.equal(offsetWindow(-5, 100, 10).start, 0);
    assert.equal(scrollMax(100, 10), 90);
    assert.equal(scrollMax(4, 10), 0);
    assert.equal(scrollMax(0, 0), 0);
  });

  it("pages with one row of overlap", () => {
    assert.equal(pageStep(10), 9);
    assert.equal(pageStep(1), 1);
    assert.equal(pageStep(0), 1);
  });

  it("marks only the side that has more", () => {
    assert.equal(moreMarker({ above: false, below: false }), "");
    assert.equal(moreMarker({ above: true, below: false }), "↑ more");
    assert.equal(moreMarker({ above: false, below: true }), "↓ more");
    assert.equal(moreMarker({ above: true, below: true }), "↑↓ more");
    assert.equal(moreMarker(null), "");
  });

  it("keeps the wrap-around movement the menus use", () => {
    assert.equal(wrapStep(0, -1, 5), 4);
    assert.equal(wrapStep(4, 1, 5), 0);
    assert.equal(wrapStep(0, 1, 0), 0);
  });
});

/* ------------------------------ list surfaces ------------------------------ */

describe("scroll: lists", () => {
  it("requires no scrolling when everything fits", async () => {
    const { app } = await startApp();
    const { model } = frame(app, 120, 40);
    assert.equal(model.scrollMax.detail > 0, false, "the short detail has nothing to scroll");
    assert.equal(model.scrollMax.system, 0);
  });

  it("scrolls a long repository list and keeps the selection visible", async () => {
    const repos = manyRepositories(40);
    const { app } = await startApp({ listRepositories: { success: true, repositories: repos, total_count: repos.length } });
    frame(app, 90, 24);

    const visible = (rows) => text(frame(app, 90, 24).lines.slice(0, rows));
    assert.match(visible(24), /service-00/, "the first rows are shown at the top");

    for (let step = 0; step < 39; step += 1) app.dispatch(key("down"));
    assert.equal(app.getState().cursors.repositories, 39);
    const bottom = text(frame(app, 90, 24).lines);
    assert.match(bottom, /service-39/, "the selected row is inside the window");
    assert.doesNotMatch(bottom, /service-00/, "the window followed the selection");

    app.dispatch(key("home"));
    assert.equal(app.getState().cursors.repositories, 0);
    assert.match(text(frame(app, 90, 24).lines), /service-00/);

    app.dispatch(key("end"));
    assert.equal(app.getState().cursors.repositories, 39);

    app.dispatch(key("pageUp"));
    const pageSize = app.getState().viewport.pageSize;
    assert.equal(app.getState().cursors.repositories, 39 - pageSize, "PgUp moves a page, not a row");
    app.dispatch(key("pageDown"));
    assert.equal(app.getState().cursors.repositories, 39, "PgDn returns without wrapping past the end");
  });

  it("windows a long symbol list at every supported size", async () => {
    const repos = manyRepositories(3);
    const symbols = manySymbols(120);
    const client = {
      listRepositories: { success: true, repositories: [{ ...repos[0], call_graph_nodes: symbols }], total_count: 1 },
    };
    for (const [cols, rows] of SIZES) {
      const { app } = await startApp(client);
      app.dispatch(char("2"));
      frame(app, cols, rows);
      for (let step = 0; step < 119; step += 1) app.dispatch(key("down"));
      const { model, lines } = frame(app, cols, rows);
      assert.equal(app.getState().cursors.code, 119, `${cols}x${rows} reaches the last symbol`);
      const selectedRow = model.view.list.rows[model.view.list.cursor];
      const label = String(selectedRow?.cells?.[0]?.text ?? "").trim();
      assert.ok(label.length > 0, `${cols}x${rows} has a selected row`);
      assert.ok(
        text(lines).includes(`▍ ${label}`),
        `${cols}x${rows} renders the selected row inside the window (${label})`
      );
      assert.equal(lines.length, rows, `${cols}x${rows} keeps the frame inside the terminal`);
      assert.equal(model.scrollMax.detail >= 0, true);
    }
  });

  it("shows the more marker only while there is content beyond the window", async () => {
    const repos = manyRepositories(40);
    const { app } = await startApp({ listRepositories: { success: true, repositories: repos, total_count: repos.length } });

    const top = text(frame(app, 90, 24).lines);
    assert.match(top, /↓ more/, "rows below the window are marked");
    assert.doesNotMatch(top, /↑ more/);

    app.dispatch(key("end"));
    const bottom = text(frame(app, 90, 24).lines);
    assert.match(bottom, /↑ more/, "rows above the window are marked");
    assert.doesNotMatch(bottom, /↓ more/);

    const short = await startApp();
    assert.doesNotMatch(text(frame(short.app, 90, 24).lines), /more/, "no marker when everything fits");
  });
});

/* ----------------------------- detail surfaces ---------------------------- */

describe("scroll: detail panes", () => {
  it("scrolls the repository detail with every control and clamps at the end", async () => {
    const repos = manyRepositories(6);
    const long = { ...repos[0], summary: Array.from({ length: 60 }, (_, line) => `Detail line ${line}.`).join(" ") };
    const { app } = await startApp({ listRepositories: { success: true, repositories: [long, ...repos.slice(1)], total_count: 6 } });

    frame(app, 120, 40);
    app.dispatch(key("enter")); // into the detail
    assert.equal(app.getState().focus, "inspector");

    const max = app.getState().viewport.detailMax;
    assert.ok(max > 0, "the detail is longer than its pane");

    app.dispatch(key("down"));
    assert.equal(app.getState().scroll.repositories, 1);
    app.dispatch(char("j"));
    assert.equal(app.getState().scroll.repositories, 2, "j scrolls the detail too");

    app.dispatch(key("pageDown"));
    assert.equal(
      app.getState().scroll.repositories,
      Math.min(2 + app.getState().viewport.detailPage, max),
      "PgDn moves a page and stops at the content"
    );
    app.dispatch(key("home"));
    assert.equal(app.getState().scroll.repositories, 0);
    app.dispatch(key("end"));
    assert.equal(app.getState().scroll.repositories, max);
    for (let step = 0; step < 5; step += 1) app.dispatch(key("down"));
    assert.equal(app.getState().scroll.repositories, max, "the offset never runs past the content");

    const { model, lines } = frame(app, 120, 40);
    assert.equal(model.scrollMax.detail, max, "the published bound matches the rendered pane");
    // The summary wraps, so the tail is the line that ends the last sentence.
    // Lines are padded to the pane width, so allow the trailing spaces.
    assert.match(text(lines), /59\.\s*(\n|$)/, "the end of the detail is reachable");
    assert.equal(lines.length, 40);
  });

  it("keeps one offset per destination and restores it on return", async () => {
    const repos = manyRepositories(6);
    const long = { ...repos[0], summary: Array.from({ length: 60 }, (_, line) => `Detail line ${line}.`).join(" ") };
    const { app } = await startApp({ listRepositories: { success: true, repositories: [long, ...repos.slice(1)], total_count: 6 } });

    frame(app, 120, 40);
    app.dispatch(key("enter"));
    app.dispatch(key("end"));
    const repoOffset = app.getState().scroll.repositories;
    assert.ok(repoOffset > 0);

    app.dispatch(char("5")); // Settings has its own detail
    frame(app, 120, 40);
    assert.equal(app.getState().scroll.settings, 0, "a fresh destination starts at the top");
    assert.equal(app.getState().scroll.repositories, repoOffset, "and does not disturb the other pane");

    app.dispatch(char("1")); // back to Repositories
    frame(app, 120, 40);
    assert.equal(app.getState().scroll.repositories, repoOffset, "the position is still there");
    assert.equal(app.getState().focus, "inspector", "focus follows the destination's own state");
  });

  it("scrolls independently in the detail mode below the breakpoint", async () => {
    const repos = manyRepositories(6);
    const long = { ...repos[0], summary: Array.from({ length: 60 }, (_, line) => `Detail line ${line}.`).join(" ") };
    const { app } = await startApp({ listRepositories: { success: true, repositories: [long, ...repos.slice(1)], total_count: 6 } });

    frame(app, 90, 24);
    app.dispatch(key("down"));
    const listCursor = app.getState().cursors.repositories;
    app.dispatch(key("enter")); // opens the mode
    assert.equal(app.getState().inspectorOpen, true);

    const max = app.getState().viewport.detailMax;
    assert.ok(max > 0);
    app.dispatch(key("end"));
    assert.equal(app.getState().scroll.repositories, max);

    app.dispatch(key("escape"));
    assert.equal(app.getState().inspectorOpen, false, "esc closes the mode");
    assert.equal(app.getState().cursors.repositories, listCursor, "the list cursor is exactly where it was");
    assert.equal(app.getState().focus, "list");
  });

  it("never leaves focus on a pane the destination does not show", async () => {
    const { app } = await startApp();
    frame(app, 120, 40);
    app.dispatch(key("enter")); // focus the repository detail
    assert.equal(app.getState().focus, "inspector");

    app.dispatch(char("4")); // System is one full-width report
    assert.equal(app.getState().view, "system");
    assert.equal(app.getState().focus, "list", "the report owns the keyboard");
    assert.equal(app.getState().inspectorOpen, false);

    // And the report is what the movement keys scroll (the frame publishes the
    // report's own bound, exactly as the entry point does on every repaint).
    frame(app, 120, 40);
    app.dispatch(key("pageDown"));
    assert.ok(app.getState().scroll.system > 0, "the report scrolls with the focus it kept");
  });

  it("scrolls the system report and keeps it reachable at every size", async () => {
    for (const [cols, rows] of SIZES) {
      const { app } = await startApp();
      app.dispatch(char("4"));
      await settle();
      frame(app, cols, rows);

      const max = app.getState().viewport.systemMax;
      app.dispatch(key("end"));
      assert.equal(app.getState().scroll.system, max, `${cols}x${rows} reaches the end of the report`);
      const { model, lines } = frame(app, cols, rows);
      assert.equal(lines.length, rows, `${cols}x${rows} keeps the frame inside the terminal`);
      assert.equal(model.scrollMax.system, max);
      if (max > 0) assert.match(text(lines), /↑ more/, `${cols}x${rows} marks the content above`);
      assert.match(lines.at(-1), /keys/, `${cols}x${rows} keeps the footer in the frame`);
    }
  });
});

/* ------------------------------- overlays --------------------------------- */

describe("scroll: overlays", () => {
  it("scrolls the help sheet and the package viewer with independent offsets", async () => {
    const packages = manyPackages(4, 200);
    const { app } = await startApp({
      listContextPackages: { success: true, packages, total_count: packages.length },
      getContextPackage: (id) => packages.find((pkg) => pkg.id === id),
    });
    frame(app, 60, 20);

    app.dispatch(char("?"));
    frame(app, 60, 20); // the bound is published by the frame that renders the sheet
    const helpMax = app.getState().viewport.helpMax;
    assert.ok(helpMax > 0, "the reference sheet is longer than a short terminal");
    app.dispatch(key("end"));
    assert.equal(app.getState().scroll.help, helpMax);
    assert.match(text(frame(app, 60, 20).lines), /Indexing and synthesis/, "the notes at the end are reachable");
    app.dispatch(key("escape"));

    app.dispatch(char("3"));
    await settle();
    await app.openPackageViewer("pkg-0");
    frame(app, 60, 20);
    const viewerMax = app.getState().viewport.viewerMax;
    assert.ok(viewerMax > 0, "the package is longer than the viewer");

    assert.equal(app.getState().scroll.viewer, 0, "the viewer opens at the top of the package");
    app.dispatch(key("pageDown"));
    assert.equal(app.getState().scroll.viewer, app.getState().viewport.viewerPage, "PgDn pages by the viewer height");
    assert.notEqual(app.getState().scroll.help, app.getState().scroll.viewer, "the two overlays keep separate offsets");

    // Rendered/raw keeps the reader's place instead of throwing them to the top.
    const before = app.getState().scroll.viewer;
    app.dispatch(char("m"));
    frame(app, 60, 20);
    assert.equal(app.getState().scroll.viewer, before, "the toggle preserves the offset");

    app.dispatch(key("end"));
    assert.equal(app.getState().scroll.viewer, app.getState().viewport.viewerMax, "the end of the package is reachable");
    app.dispatch(key("escape"));
    assert.equal(app.getState().overlay, null);
  });

  it("pages a form overlay whose content outgrows a short terminal", async () => {
    const { app } = await startApp();
    app.dispatch(char("?"));
    frame(app, 48, 16);
    app.dispatch(key("escape"));

    app.dispatch(char("a")); // add repository dialog
    frame(app, 48, 16);
    const { model } = frame(app, 48, 16);
    const max = model.scrollMax.overlay;
    app.dispatch(key("pageDown"));
    assert.equal(app.getState().scroll.overlay, Math.min(app.getState().viewport.overlayPage, max));
    app.dispatch(key("home"));
    assert.equal(app.getState().scroll.overlay, 0);
    app.dispatch(key("escape"));
  });

  it("keeps the model selector's list scrollable and the frame intact", async () => {
    const models = Array.from({ length: 50 }, (_, index) => ({ model_id: `model-${index}`, name: `model-${index}`, quantization: "unknown" }));
    const { app } = await startApp({ discoverProvider: { success: true, status: "available", models, message: "" } });
    frame(app, 60, 20);
    app.dispatch(char("5"));
    await settle();
    app.dispatch(char("e"));
    await settle();
    for (const _ of [0, 1, 2]) app.dispatch(key("down"));
    app.dispatch(key("enter"));
    assert.equal(app.getState().overlay.kind, "modelSelect");

    const { lines } = frame(app, 60, 20);
    assert.equal(lines.length, 20);
    assert.match(text(lines), /↓ more/, "a long model list is marked, not clipped");
    app.dispatch(key("end"));
    const { lines: atEnd } = frame(app, 60, 20);
    assert.match(text(atEnd), /model-49/, "the last model is reachable");
    assert.match(atEnd.at(-1), /enter select/, "the selector keeps its usable footer");
  });
});

/* ------------------------------ the whole shell ---------------------------- */

describe("scroll: frames stay inside the terminal", () => {
  it("keeps the footer in the frame with oversized content at every size", async () => {
    const repos = manyRepositories(40);
    const packages = manyPackages(30, 300);
    const overrides = {
      listRepositories: { success: true, repositories: repos, total_count: repos.length },
      listContextPackages: { success: true, packages, total_count: packages.length },
    };

    for (const [cols, rows] of SIZES) {
      const { app } = await startApp(overrides);
      app.dispatch(key("end"));
      frame(app, cols, rows);

      // Every destination, with the longest content each one can show.
      for (const view of ["1", "2", "3", "4", "5"]) {
        app.dispatch(char(view));
        if (view === "3") await settle();
        const { lines } = frame(app, cols, rows);
        assert.equal(lines.length, rows, `${cols}x${rows} view ${view} fills exactly the terminal`);
        assert.ok(lines.every((line) => line.length <= cols), `${cols}x${rows} view ${view} never exceeds the width`);
        assert.match(lines.at(-1), /\? keys/, `${cols}x${rows} view ${view} keeps the ? affordance`);
      }

      app.dispatch(char("?"));
      const help = frame(app, cols, rows);
      assert.equal(help.lines.length, rows);
      assert.match(help.lines.at(-1), /close/, `${cols}x${rows} help keeps its dismissal hint`);
      app.dispatch(key("escape"));
    }
  });

  it("keeps the small-terminal gate and stays colour-free", async () => {
    const { app } = await startApp();
    const small = frame(app, 40, 10);
    assert.equal(small.model.tooSmall, true, "40x10 keeps the too-small gate");
    assert.match(text(small.lines), /terminal too small/);

    const { lines } = frame(app, 90, 24);
    assert.ok(!text(lines).includes("\u001b"), "NO_COLOR output stays free of escapes with markers on screen");
    assert.match(text(lines), /Repositories/);
  });
});

/* ---------------------------- control coverage ---------------------------- */

describe("scroll: advertised controls", () => {
  it("advertises the scrolling controls in the reference sheet", () => {
    assert.match(HINTS.scroll.help, /PgUp\/PgDn/);
    assert.match(HINTS.modelMove.help, /wraps/);
    assert.match(HINTS.modelFilter.help, /never a model name field/);
  });
});
