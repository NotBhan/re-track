import { describe, it } from "node:test";
import assert from "node:assert/strict";

/* eslint-disable no-control-regex -- frames embed ANSI escapes that the tests measure and strip */
import { buildModel, composeFrame, composeLines, createPlainStyler, HELP_NOTES } from "../render.mjs";
import { createStyler } from "../theme.mjs";
import { layoutFor, windowStart, wrapStep, truncate } from "../layout.mjs";
import { formatMarkdown } from "../markdown.mjs";
import { CONTEXT_OK, PACKAGES, char, key, plain, publishViewport, settle, startApp } from "./fixtures.mjs";

const ANSI = /\u001b\[[0-9;]*m/g;
const strip = (text) => String(text).replace(ANSI, "");

function frame(app, cols, rows, options = {}) {
  const model = buildModel(app, { cols, rows, spinnerFrame: options.spinnerFrame ?? 0 });
  // Mirror the entry point: scroll bounds are published from the built model.
  publishViewport(app, model);
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
    const stageLine = lines.find((line) => line.includes("Indexing alpha-service"));

    assert.ok(stageLine, "the staging line is present while indexing");
    assert.match(stageLine, /Extracting AST call graphs/);

    // The backend reports processed/total files, so the bar is determinate and
    // the counts are shown exactly as reported — never converted to a percent.
    const progressLine = lines.find((line) => /[█░]/.test(line));
    assert.ok(progressLine, "determinate progress is rendered when the backend reports files");
    assert.match(progressLine, /0 \/ 10 files/);
    assert.match(progressLine, /phase 2\/5/, "the phase index is shown alongside file progress");
    assert.match(progressLine, /[█░]/);
    assert.doesNotMatch(`${stageLine}\n${progressLine}`, /%/);
    // There is no backend cancel contract, so no control offers one.
    assert.doesNotMatch(lines.at(-1), /cancel/i, "the footer offers no cancellation while a run is active");

    release();
    await settle();
  });

  it("keeps indexing indeterminate when the backend reports no counts", async () => {
    let release;
    const pending = new Promise((resolve) => {
      release = resolve;
    });
    const { app } = await startApp({
      indexRepository: async () => {
        await pending;
        return { success: true, total_files: 0, processed_files: 0, failed_files: 0, summary: "done" };
      },
      repositoryProgress: {
        success: true,
        status: "indexing",
        stage: "Embedding chunks",
        stage_index: null,
        stage_total: null,
        processed_files: null,
        total_files: null,
        elapsed_ms: 0,
      },
    });

    app.dispatch(char("i"));
    await settle(2);
    await app.tick(Date.now() + 1000);
    const { lines } = frame(app, 120, 24);
    const stageLine = lines.find((line) => line.includes("Indexing alpha-service"));

    assert.ok(stageLine);
    assert.match(stageLine, /Embedding chunks/);
    assert.ok(!lines.some((line) => /[█░]/.test(line)), "no bar is drawn without backend counts");
    assert.doesNotMatch(stageLine, /%/);

    release();
    await settle();
  });

  it("renders the completion line with real counts and no percentage", async () => {
    const { app } = await startApp();
    app.dispatch(char("i"));
    await settle();
    const { lines } = frame(app, 120, 24);
    const operationLine = lines.find((line) => line.includes("Indexed alpha-service"));

    assert.ok(operationLine, "the completion line persists after the run");
    assert.match(operationLine, /10 files/);
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
    const help = text(frame(app, 120, 84).lines);
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

describe("render: context evidence", () => {
  /** Run a manually typed task through the same path the `n` dialog uses. */
  const manualTask = async (agentContext, prompt) => {
    const started = await startApp({ agentContext });
    started.app.dispatch(char("3"));
    started.app.dispatch(char("n"));
    for (const value of prompt) started.app.dispatch(char(value));
    started.app.dispatch(key("enter"));
    await settle(4);
    return started;
  };

  it("renders the evidence the engine gathered for a custom prompt", async () => {
    const files = ["backend/app/services/evidence_service.py", "backend/app/application/use_cases/context.py"];
    const { app, client } = await manualTask(
      {
        ...CONTEXT_OK,
        evidence_state: "sufficient",
        evidence_score: 0.502,
        evidence_confidence: 0.5,
        extracted_symbols: [],
        evidence_symbols: [],
        related_files: files,
        evidence_files: files,
        missing_evidence: [],
        abstained: false,
      },
      "how does the evidence service assess evidence"
    );

    assert.equal(
      client.calls.find((entry) => entry.name === "agentContext").args[0].taskPrompt,
      "how does the evidence service assess evidence",
      "the custom prompt reaches the backend verbatim"
    );

    const body = text(frame(app, 120, 60).lines);
    assert.match(body, /state: Sufficient\s+strength: 50%/);
    assert.match(body, /confidence: Single-channel/);
    assert.match(body, /files \(2\): backend\/app\/services\/evidence_servi/, "the evidence files the engine verified are shown");
    assert.doesNotMatch(body, /engine abstained/);
  });

  it("shows the no-evidence state and the engine's reason for a manual task that matches nothing", async () => {
    const { app } = await manualTask(
      {
        ...CONTEXT_OK,
        evidence_state: "none",
        evidence_score: 0.003,
        evidence_confidence: 0,
        extracted_symbols: [],
        evidence_symbols: [],
        evidence_files: [],
        evidence_relationships: [],
        related_files: [],
        observed_evidence: ["Indexed repository files: 576 files analyzed."],
        missing_evidence: ["Concrete code implementations or symbol definitions matching the task"],
        abstained: true,
        abstention_reason:
          "Filesystem path references without matched code content or symbol definitions do not constitute sufficient repository evidence.",
        model_claims_allowed: false,
      },
      "write a haiku about the ocean"
    );

    const body = text(frame(app, 120, 60).lines);
    assert.match(body, /state: No evidence\s+strength: 0%/);
    assert.match(body, /confidence: Not computed/);
    assert.match(body, /engine abstained from unsupported claims/);
    assert.match(body, /Filesystem\s+path\s+references\s+without\s+matched\s+code\s+content/);
    assert.match(body, /missing evidence/);
    assert.match(body, /Concrete\s+code\s+implementations\s+or\s+symbol\s+definitions\s+matching\s+the\s+task/);
    assert.match(body, /symbols \(0\): none/, "no symbol evidence is invented");
    assert.match(body, /files \(0\): none/, "no file evidence is invented");
    assert.doesNotMatch(body, /state: Sufficient/);
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
    assert.match(bottom, /configuration\s+Settings view/);
    assert.match(bottom, /configuration: Settings view/);
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

describe("render: settings view", () => {
  it("renders the persisted configuration sections and provider detail", async () => {
    const { app } = await startApp();
    app.dispatch(char("5"));
    await settle();

    const body = text(frame(app, 120, 34).lines);
    assert.match(body, /Storage & pipeline/);
    assert.match(body, /Hardware & runtime/);
    assert.match(body, /Capabilities/);
    // Provider detail comes from the settings and health payloads, not invented.
    assert.match(body, /configured model\s+phi3:mini/);
    assert.match(body, /endpoint\s+http:\/\/127\.0\.0\.1:1234/);
    assert.match(body, /changes save automatically/);
    assert.match(body, /R restores the mutable settings/);

    app.dispatch(key("down")); // Storage & pipeline
    const storage = text(frame(app, 120, 34).lines);
    assert.match(storage, /vector db\s+lancedb/);
    assert.match(storage, /knowledge graph\s+enabled \(t toggles/);
    assert.match(storage, /auto-link entities\s+disabled \(t toggles/);
    assert.match(storage, /ingestion caching\s+enabled/);
    assert.match(storage, /pipeline changes are written on the toggle/);
    assert.match(storage, /storage engines are fixed by the backend/);
  });

  it("renders the provider editor, its model selector and its footer", async () => {
    const { app } = await startApp();
    app.dispatch(char("5"));
    await settle();
    app.dispatch(char("e"));
    await settle();

    let lines = frame(app, 120, 34).lines;
    let body = text(lines);
    assert.match(body, /Provider configuration/);
    assert.match(body, /POST \/provider\/update/);
    assert.match(body, /provider:\s+lmstudio/);
    assert.match(body, /enter or tab: lmstudio · ollama · openai_compatible/);
    assert.match(body, /available:\s+1 models · enter selects and saves/, "the editor reports the provider's list");
    assert.match(body, /the model is chosen from the provider's list, never typed/);
    assert.doesNotMatch(body, /model:\s+\S+\s+\(required\)/, "the model is not a text field");
    assert.match(lines.at(-1), /enter save now/, "the footer says what enter does on each row");
    assert.match(lines.at(-1), /ctrl\+p probe/);
    assert.match(lines.at(-1), /esc cancel/);

    // The model row opens the selector, which lists exactly what the endpoint
    // reported — name, quantization and the saved/selected markers.
    app.dispatch(key("down"));
    app.dispatch(key("down"));
    app.dispatch(key("down"));
    app.dispatch(key("enter"));
    assert.equal(app.getState().overlay.kind, "modelSelect");
    lines = frame(app, 120, 34).lines;
    body = text(lines);
    assert.match(body, /Select model · 1 available/);
    assert.match(body, /qwen2\.5-7b\s+Q4_K_M/);
    assert.match(body, /provider lmstudio · http:\/\/127\.0\.0\.1:1234\/v1/, "the list names the endpoint it read");
    assert.match(lines.at(-1), /enter select/);
  });

  it("marks the saved model and commits when one is chosen", async () => {
    const { app, client } = await startApp({
      discoverProvider: {
        success: true,
        status: "available",
        models: [
          { model_id: "phi3:mini", name: "phi3:mini", quantization: "unknown" },
          { model_id: "qwen2.5-7b", name: "qwen2.5-7b", quantization: "Q4_K_M" },
        ],
        message: "",
      },
    });
    app.dispatch(char("5"));
    await settle();
    app.dispatch(char("e"));
    await settle();

    app.dispatch(key("down"));
    app.dispatch(key("down"));
    app.dispatch(key("down"));
    app.dispatch(key("enter"));
    const before = text(frame(app, 120, 34).lines);
    assert.match(before, /▍ phi3:mini\s+\(saved\)/, "the authoritative model is marked as saved");

    // Highlighting is not selecting: the marker stays put and nothing is written.
    app.dispatch(key("down"));
    const highlighted = text(frame(app, 120, 34).lines);
    assert.match(highlighted, /▍ qwen2\.5-7b Q4_K_M/, "the highlight is visible without color");
    assert.match(highlighted, /phi3:mini\s+\(saved\)/, "the highlight alone changes no selection");
    assert.equal(client.calls.filter((call) => call.name === "updateProvider").length, 0);

    // Choosing is committing: the model is saved through POST /provider/update
    // (there is no separate save step) and the editor closes on the write.
    app.dispatch(key("enter"));
    await settle(14);
    const updates = client.calls.filter((call) => call.name === "updateProvider");
    assert.equal(updates.length, 1, "choosing a model is the commit");
    assert.equal(updates[0].args[0].provider, "lmstudio");
    assert.equal(updates[0].args[0].model, "qwen2.5-7b");
    assert.equal(app.getState().overlay, null, "the saved configuration closes the editor");
    assert.match(app.getState().notice.message, /✓ provider updated · lmstudio · qwen2\.5-7b/);

    // Reopening shows the model that is now actually configured as saved.
    app.dispatch(char("e"));
    await settle();
    app.dispatch(key("down"));
    app.dispatch(key("down"));
    app.dispatch(key("down"));
    app.dispatch(key("enter"));
    const saved = text(frame(app, 120, 34).lines);
    assert.match(saved, /▍ qwen2\.5-7b Q4_K_M\s+\(saved\)/, "the new authoritative model leads the list");
    assert.doesNotMatch(saved, /phi3:mini\s+\(saved\)/, "the superseded model is no longer marked");
  });

  it("renders a failed settings read as a warning instead of stale values", async () => {
    const { app } = await startApp({ appSettings: () => Promise.reject(new Error("ECONNRESET")) });
    app.dispatch(char("5"));
    await settle();

    const body = text(frame(app, 120, 34).lines);
    assert.match(body, /settings unavailable: ECONNRESET/);
    assert.doesNotMatch(body, /lancedb/, "no stale configuration is rendered as current");
  });

  it("renders the pipeline overlay from the payload the backend persists", async () => {
    const { app } = await startApp();
    app.dispatch(char("5"));
    await settle();
    app.dispatch(char("t"));
    assert.equal(app.getState().overlay.kind, "pipelineSettings");

    const body = text(frame(app, 120, 34).lines);
    assert.match(body, /Pipeline settings/);
    assert.match(body, /Knowledge graph extraction\s+enabled/);
    assert.match(body, /Auto-link entities\s+disabled/);
    assert.match(body, /saved automatically through POST \/settings\/cognee/);

    app.dispatch(key("escape"));
    assert.equal(app.getState().overlay, null);
  });
});

describe("render: package catalog and package actions", () => {
  it("scopes the catalog and renders package metadata from the record", async () => {
    const { app } = await startApp();
    await app.loadPrompts();
    app.dispatch(char("3"));
    await settle();

    let body = text(frame(app, 120, 30).lines);
    assert.match(body, /Auth flow/, "suggestions are listed by default");
    assert.match(body, /catalog: all/);

    app.dispatch(char("p"));
    body = text(frame(app, 120, 30).lines);
    assert.doesNotMatch(body, /Auth flow/, "the packages-only catalog hides suggestions");
    assert.match(body, /catalog: packages/);

    // The repository column only earns its width on a wide terminal.
    body = text(frame(app, 140, 30).lines);
    assert.match(body, /alpha-service/, "the repository column comes from the package record");
  });

  it("renders the append and export dialogs against the selected package", async () => {
    const { app } = await startApp(
      {},
      { exportMarkdown: async () => ({ path: "/tmp/auth-context.md" }), exportFileName: () => "auth-context.md" }
    );
    app.dispatch(char("3"));
    app.dispatch(char("p"));

    app.dispatch(char("A"));
    let body = text(frame(app, 120, 30).lines);
    assert.match(body, /Append to package/);
    assert.match(body, /Auth context/);
    assert.match(body, /POST \/packages\/\{id\}\/append/);

    app.dispatch(key("escape"));
    app.dispatch(char("e"));
    body = text(frame(app, 120, 30).lines);
    assert.match(body, /Export package/);
    assert.match(body, /auth-context\.md/, "the dialog is prefilled with the derived file name");
    assert.match(body, /no backend export endpoint exists/);
  });
});

describe("render: responsive new surfaces", () => {
  const SIZES = [
    [120, 40],
    [90, 24],
    [60, 20],
    [48, 16],
  ];

  it("keeps the indexing bar readable at every supported size", async () => {
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

    for (const [cols, rows] of SIZES) {
      const { lines } = frame(app, cols, rows);
      const bar = lines.find((line) => /[█░]/.test(line));
      assert.ok(bar, `bar present at ${cols}x${rows}`);
      assert.match(bar, /0 \/ 10 files/);
      assert.match(bar, /phase 2\/5/);
      assert.doesNotMatch(bar, /%/);
      assert.equal(lines.length, rows, `frame height at ${cols}x${rows}`);
      for (const line of lines) assert.equal(strip(line).length, cols, `frame width at ${cols}x${rows}`);
    }

    release();
    await settle();
  });

  it("keeps the package viewer scrollable and the settings navigable at every size", async () => {
    const longMarkdown = Array.from({ length: 60 }, (_, index) => `## Section ${index}\n\n- item ${index}`).join("\n\n");
    const { app } = await startApp({ getContextPackage: () => ({ ...PACKAGES[0], markdown: longMarkdown }) });

    app.dispatch(char("3"));
    app.dispatch(char("p"));
    app.dispatch(key("enter"));
    await settle();
    assert.equal(app.getState().overlay.kind, "viewPackage");

    for (const [cols, rows] of SIZES) {
      frame(app, cols, rows); // publishes the scroll bound for this size
      assert.ok(app.getState().viewport.viewerMax > 0, `viewer scrolls at ${cols}x${rows}`);
      const before = app.getState().scroll.viewer;
      app.dispatch(key("pageDown"));
      assert.ok(app.getState().scroll.viewer > before, `viewer paged at ${cols}x${rows}`);
      const { lines } = frame(app, cols, rows);
      assert.equal(lines.length, rows);
      assert.match(text(lines), /rendered · Auth context/);
    }

    app.dispatch(key("escape"));
    app.dispatch(char("5"));
    await settle();
    for (const [cols, rows] of SIZES) {
      frame(app, cols, rows);
      app.dispatch(key("home"));
      app.dispatch(key("down"));
      assert.equal(app.getState().cursors.settings, 1, `settings navigable at ${cols}x${rows}`);
      const footer = frame(app, cols, rows).lines.at(-1);
      assert.match(footer, /\? keys/, `help affordance survives ${cols}x${rows}`);
    }
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
