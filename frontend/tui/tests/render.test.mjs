import { describe, it } from "node:test";
import assert from "node:assert/strict";

/* eslint-disable no-control-regex -- frames embed ANSI escapes that the tests measure and strip */
import { buildModel, composeFrame, composeLines, createPlainStyler, HELP_NOTES } from "../render.mjs";
import { createStyler } from "../theme.mjs";
import { layoutFor, windowStart, wrapStep, truncate } from "../layout.mjs";
import { formatMarkdown } from "../markdown.mjs";
import { char, key, plain, settle, startApp } from "./fixtures.mjs";

const ANSI = /\u001b\[[0-9;]*m/g;
const strip = (text) => String(text).replace(ANSI, "");

function frame(app, cols, rows, options = {}) {
  const model = buildModel(app, { cols, rows, spinnerFrame: options.spinnerFrame ?? 0 });
  // Mirror the entry point: scroll bounds are published from the built model.
  app.setViewport({
    pageSize: Math.max(3, model.view.list.height - 1),
    inspectorMax: model.scrollMax.inspector,
    systemMax: model.scrollMax.system,
    viewerMax: model.scrollMax.viewer,
  });
  return {
    model,
    lines: composeLines(model, options.styler ?? plain).map(strip),
    raw: composeFrame(model, { styler: options.styler ?? plain }),
  };
}

const text = (lines) => lines.join("\n");

describe("render: shell", () => {
  it("renders the header, rail, list, inspector and footer", async () => {
    const { app } = await startApp();
    const { lines } = frame(app, 120, 30);
    const body = text(lines);

    assert.match(lines[0], /RE:Track/);
    assert.match(lines[0], /alpha-service/);
    assert.match(body, /Workspace/);
    assert.match(body, /Repositories/);
    assert.match(body, /Repo|alpha-service/);
    assert.match(body, /path|branch|status/);
    assert.match(lines.at(-1), /move|inspect|quit|keys|add/);
  });

  it("marks the active view and the focused pane without relying on color", async () => {
    const { app } = await startApp();
    const lines = frame(app, 120, 30).lines;
    const body = text(lines);

    // Active rail entry and the focused pane title both carry a glyph marker.
    assert.match(body, /▍ Repositories \(2\)/);
    assert.match(body, /▍ Repositories · 2 tracked/);
    assert.match(body, /\n  Code/);
  });

  it("keeps the frame inside the requested dimensions", async () => {
    const { app } = await startApp();
    for (const [cols, rows] of [[120, 40], [90, 24], [76, 24], [60, 20], [48, 16]]) {
      const { lines } = frame(app, cols, rows);
      assert.equal(lines.length, rows, `rows at ${cols}x${rows}`);
      for (const line of lines) assert.ok(line.length <= cols, `line width at ${cols}x${rows}: ${line.length}`);
    }
  });

  it("shows a dedicated too-small state at 40x10", async () => {
    const { app } = await startApp();
    const { lines } = frame(app, 40, 10);
    const body = text(lines);
    assert.match(body, /terminal too small/);
    assert.match(body, /48 columns and 12 rows/);
    assert.match(body, /backend: ok/);
    assert.match(body, /repository: alpha-service/);
    assert.equal(lines.length, 10);
  });

  it("stacks the inspector as a mode below the wide breakpoint", async () => {
    const { app } = await startApp();
    const narrow = frame(app, 90, 24);
    assert.equal(narrow.model.layout.sideBySide, false);

    app.openInspector();
    const { lines } = frame(app, 90, 24);
    const body = text(lines);
    assert.match(body, /alpha-service/, "the inspector mode shows the selected repository detail");
    assert.match(body, /path\s+\/work\/alpha/);
    assert.doesNotMatch(body.split("\n")[3], /▍ alpha-service/, "list rows are replaced by the inspector mode");

    const wide = frame(app, 120, 24);
    assert.equal(wide.model.layout.sideBySide, true);
  });
});

describe("render: truthfulness", () => {
  it("renders empty, loading and error states explicitly", async () => {
    const failure = () => Promise.reject(new Error("ECONNREFUSED"));
    const { app } = await startApp({
      health: failure,
      status: failure,
      providerStatus: failure,
      listRepositories: failure,
      listContextPackages: failure,
      memoryStats: failure,
    });
    const offline = frame(app, 100, 24);
    assert.match(text(offline.lines), /backend unavailable/);
    assert.match(text(offline.lines), /no repositories tracked/);

    const empty = await startApp({ listRepositories: { success: true, repositories: [], total_count: 0 } });
    assert.match(text(frame(empty.app, 100, 24).lines), /no repositories tracked · press a to add one/);
  });

  it("never renders a percentage while indexing", async () => {
    let release;
    const pending = new Promise((resolve) => {
      release = resolve;
    });
    const { app } = await startApp({
      indexRepository: async () => {
        await pending;
        return { success: true, total_files: 10, processed_files: 10, failed_files: 0, summary: "done" };
      },
    });

    app.dispatch(char("i"));
    await settle(2);
    await app.tick(Date.now() + 1000);
    const { lines } = frame(app, 120, 24);
    const operationLine = lines.find((line) => line.includes("indexing alpha-service"));

    assert.ok(operationLine, "operation line is present while indexing");
    assert.match(operationLine, /phase 2\/5/);
    assert.doesNotMatch(operationLine, /%/);
    assert.match(operationLine, /Extracting AST call graphs/);

    release();
    await settle();
  });

  it("renders the completion line with real counts and no percentage", async () => {
    const { app } = await startApp();
    app.dispatch(char("i"));
    await settle();
    const { lines } = frame(app, 120, 24);
    const operationLine = lines.find((line) => line.includes("indexed alpha-service"));

    assert.ok(operationLine);
    assert.match(operationLine, /10\/10 files/);
    assert.doesNotMatch(operationLine, /%/);
  });

  it("renders confidence as a tier and never as a percentage", async () => {
    const { app } = await startApp();
    app.dispatch(char("3"));
    app.dispatch(char("n"));
    for (const value of "task") app.dispatch(char(value));
    app.dispatch(key("enter"));
    await settle(4);

    const { lines } = frame(app, 120, 30);
    const body = text(lines);
    assert.match(body, /confidence: Single-channel/);
    assert.match(body, /state: Partial/);
    assert.match(body, /strength: 42%/);
    assert.doesNotMatch(body, /confidence: \d+/);
    assert.doesNotMatch(body, /50% confidence/);
  });

  it("renders unavailable values instead of zeros", async () => {
    const { app } = await startApp();
    app.dispatch(key("down")); // beta-service: no languages, frameworks, commit or indexing
    const body = text(frame(app, 120, 40).lines);
    assert.match(body, /languages\s+none/);
    assert.match(body, /frameworks\s+none/);
    assert.match(body, /entry points\s+none/);
    assert.match(body, /commit\s+unavailable/);
    assert.match(body, /indexed\s+never/);
    assert.match(body, /error\s+unavailable/);
  });

  it("states capabilities the backend does not provide", async () => {
    const { app } = await startApp();
    const { lines } = frame(app, 120, 24);
    assert.match(text(lines), /automatic updates: not available/);
    assert.match(text(lines), /cancellation: not supported by the backend/);

    app.dispatch(char("?"));
    const help = text(frame(app, 120, 46).lines);
    for (const note of HELP_NOTES) assert.match(help, new RegExp(note.slice(0, 24).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  });

  it("renders the code view states for an unanalyzed repository", async () => {
    const { app } = await startApp();
    // Repository selection happens in the Repositories view; Code is scoped to it.
    app.dispatch(key("down"));
    app.dispatch(char("2"));
    const body = text(frame(app, 120, 24).lines);
    assert.match(body, /beta-service · call graph not_analyzed/);
    assert.match(body, /call graph not analyzed/);
    assert.match(body, /no components, entry points or symbols indexed yet/);
  });
});

describe("render: context output", () => {
  it("switches between rendered and raw markdown without changing the source", async () => {
    const { app } = await startApp();
    app.dispatch(char("3"));
    app.dispatch(char("n"));
    for (const value of "task") app.dispatch(char(value));
    app.dispatch(key("enter"));
    await settle(4);

    const rendered = text(frame(app, 120, 60).lines);
    assert.match(rendered, /Task Context/);
    assert.doesNotMatch(rendered, /```/, "code fences are presented, not echoed");

    app.dispatch(char("m"));
    assert.equal(app.getState().markdownView, "raw");
    const raw = text(frame(app, 120, 60).lines);
    assert.match(raw, /```python/, "raw mode shows the exact markdown fences");
    assert.match(raw, /output · raw/);
  });

  it("keeps the package viewer presentation-only", async () => {
    const { app } = await startApp();
    app.dispatch(char("3"));
    app.openPackageViewer("pkg-1");
    await settle(3);

    const rendered = text(frame(app, 100, 24).lines);
    assert.match(rendered, /Auth context/);
    assert.match(rendered, /rendered/);

    app.toggleMarkdown();
    const raw = text(frame(app, 100, 24).lines);
    assert.match(raw, /# Auth/);
    assert.match(raw, /raw/);
  });
});

describe("render: overlays and layout helpers", () => {
  it("renders each required overlay", async () => {
    const { app } = await startApp();

    app.dispatch(char("a"));
    assert.match(text(frame(app, 100, 24).lines), /Add repository/);
    app.dispatch(key("escape"));

    app.dispatch(char("d"));
    assert.match(text(frame(app, 100, 24).lines), /Delete repository/);
    app.dispatch(key("escape"));

    app.dispatch(char("3"));
    app.dispatch(char("n"));
    assert.match(text(frame(app, 100, 24).lines), /New task/);
    app.dispatch(key("escape"));

    app.dispatch(char("?"));
    const help = text(frame(app, 100, 30).lines);
    assert.match(help, /Keyboard/);
    assert.match(help, /Navigate/);
  });

  it("strips all escape codes when color is disabled", async () => {
    const { app } = await startApp();
    const { raw } = frame(app, 100, 24, { styler: plain });
    // Only the frame control sequences remain (cursor home + clear to end).
    const withoutFrameControl = raw.replace(/\u001b\[H/g, "").replace(/\u001b\[J/g, "");
    assert.ok(!withoutFrameControl.includes("\u001b"), "no styling escapes when color is disabled");
    assert.ok(!/\u001b\[[0-9;]*m/.test(raw), "no SGR sequences when color is disabled");
  });

  it("measures styled strings by visible width (colored output matches monochrome)", async () => {
    const { app } = await startApp();
    const colored = createStyler({ enabled: true });
    const model = buildModel(app, { cols: 120, rows: 40 });
    const withColor = composeLines(model, colored);
    const withoutColor = composeLines(model, plain);

    // Every line must be exactly the terminal width once escapes are stripped…
    for (const line of withColor) assert.equal(strip(line).length, 120);
    // …and styling must never change the text that is displayed, which is what
    // an ANSI-aware width budget guarantees (regression: pane rows used to be
    // truncated as soon as color was enabled).
    assert.deepEqual(withColor.map(strip), withoutColor);
    assert.match(withColor.map(strip)[3], /path\s+\/work\/alpha/);
    assert.doesNotMatch(withColor.map(strip)[3], /indexed…/);
  });

  it("emits SGR styling only when color is enabled", async () => {
    const { app } = await startApp();
    const colored = composeFrame(buildModel(app, { cols: 100, rows: 24 }), { styler: createStyler({ enabled: true }) });
    assert.match(colored, /\u001b\[1m/);
    const monochrome = createStyler({ enabled: false });
    assert.equal(monochrome.bold("x"), "x");
    assert.equal(monochrome.dim("x"), "x");
  });

  it("wraps the cursor window and clamps scroll offsets", () => {
    assert.equal(windowStart(0, 100, 10), 0);
    assert.equal(windowStart(50, 100, 10), 45);
    assert.equal(windowStart(99, 100, 10), 90);
    assert.equal(windowStart(3, 4, 10), 0);
    assert.equal(wrapStep(0, -1, 4), 3);
    assert.equal(wrapStep(3, 1, 4), 0);
    assert.equal(truncate("abcdef", 4), "abc…");
  });

  it("degrades the footer hints on compact terminals", () => {
    const compact = layoutFor({ cols: 60, rows: 20, operation: false });
    assert.equal(compact.compact, false);
    assert.equal(compact.sideBySide, false);
    assert.equal(compact.footerHints, 6);

    const tiny = layoutFor({ cols: 60, rows: 14, operation: true });
    assert.equal(tiny.compact, true);
    assert.equal(tiny.footerHints, 3);
    assert.equal(tiny.showRule, false);
  });

  it("formats markdown deterministically for both modes", () => {
    const source = "# Title\n\n- item\n\n```js\ncode()\n```";
    const rendered = formatMarkdown(source, { rendered: true, width: 40, styler: createPlainStyler() });
    assert.ok(rendered.some((line) => line.includes("Title")));
    assert.ok(rendered.some((line) => line.includes("• item")));
    assert.ok(!rendered.some((line) => line.startsWith("# Title")));

    const raw = formatMarkdown(source, { rendered: false });
    assert.deepEqual(raw, source.split("\n"));
  });
});

describe("render: system view", () => {
  it("shows provider, engine, hardware and limits from backend data", async () => {
    const { app } = await startApp();
    app.dispatch(char("4"));
    await settle(3);
    frame(app, 120, 44); // publishes the scroll bounds
    const top = text(frame(app, 120, 44).lines);
    assert.match(top, /Provider/);
    assert.match(top, /lmstudio/);
    assert.match(top, /Engine/);
    assert.match(top, /Hardware/);

    app.dispatch(key("end")); // scroll to the end of the report
    const bottom = text(frame(app, 120, 44).lines);
    assert.match(bottom, /Storage|Diagnostics/);
    assert.match(bottom, /provider switching: GUI only/);
    assert.match(bottom, /settings mutation: GUI only/);
    assert.match(bottom, /cancellation: not supported by the backend/);
  });

  it("exports diagnostics and reports the returned path", async () => {
    const { app, client } = await startApp();
    app.dispatch(char("4"));
    await settle(2);
    app.dispatch(char("e"));
    await settle(3);

    assert.ok(client.calls.some((call) => call.name === "exportDiagnostics"));
    assert.match(app.getState().notice.message, /re-track-diagnostics\.json/);
  });
});

describe("render: filtering", () => {
  it("shows the filter row and the filtered count", async () => {
    const { app } = await startApp();
    app.dispatch(char("/"));
    for (const value of "beta") app.dispatch(char(value));

    const { lines } = frame(app, 110, 24);
    const body = text(lines);
    assert.match(body, /▍ beta/);
    assert.match(body, /Repositories · 1 of 2 matching/);
    assert.doesNotMatch(body, /alpha-service/);

    app.dispatch(key("escape"));
    assert.match(text(frame(app, 110, 24).lines), /2 tracked/);
  });
});
