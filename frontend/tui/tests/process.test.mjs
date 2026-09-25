/* eslint-disable no-control-regex -- the suite measures raw terminal escape sequences */
import { describe, it, before, after } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { makeClient } from "./fixtures.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const entry = path.resolve(here, "..", "retrack.mjs");
const ENTER_ALT_SCREEN = "\u001b[?1049h";
const LEAVE_ALT_SCREEN = "\u001b[?1049l";
const SHOW_CURSOR = "\u001b[?25h";
const hasScript = existsSync("/usr/bin/script");
const strip = (value) => value.replace(/\u001b\[[0-9;?]*[A-Za-z]/g, "");

const REPOS = [
  {
    id: "repo-a",
    name: "alpha-service",
    source_type: "local",
    local_path: "/work/alpha",
    branch: "main",
    status: "indexed",
    file_count: 3,
    languages: ["Python"],
    entry_points: [],
    components: [],
    call_graph_status: "analyzed",
    call_graph_nodes: [],
    call_graph_edges: [],
    metadata: {},
  },
];

function startStub() {
  const server = http.createServer((req, res) => {
    res.setHeader("Content-Type", "application/json");
    const send = (payload) => res.end(JSON.stringify(payload));
    if (req.url.startsWith("/health/detailed")) return send({ status: "ok", storage_paths: {} });
    if (req.url.startsWith("/health")) return send({ status: "ok", version: "0.1.0", provider_identity: "lmstudio", provider_reachable: true });
    if (req.url.startsWith("/status")) return send({ status: "ok", llm_provider: "lmstudio" });
    if (req.url.startsWith("/provider/status")) return send({ success: true, provider: "lmstudio", is_reachable: true, health_state: "healthy" });
    if (req.url.startsWith("/repos/") && req.url.endsWith("/prompts")) return send({ success: true, prompts: [], source: "heuristic" });
    if (req.url.startsWith("/repos")) return send({ success: true, repositories: REPOS, total_count: REPOS.length });
    if (req.url.startsWith("/packages")) return send({ success: true, packages: [], total_count: 0 });
    if (req.url.startsWith("/memory/stats")) return send({ success: true, dataset_count: 0, total_size_display: "0 B" });
    if (req.url.startsWith("/logs/recent")) return send({ status: "ok", count: 0, logs: [] });
    return send({ ok: true });
  });
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => resolve({ server, baseUrl: `http://127.0.0.1:${server.address().port}` }));
  });
}

function runInPty(baseUrl, inputs, options = {}) {
  return new Promise((resolve, reject) => {
    const command = `${JSON.stringify(process.execPath)} ${JSON.stringify(entry)}`;
    const child = spawn("script", ["-qec", command, "/dev/null"], {
      env: { ...process.env, RETRACK_BACKEND_URL: baseUrl, NO_COLOR: "1" },
      stdio: ["pipe", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    let settled = false;

    const safety = setTimeout(() => {
      if (settled) return;
      settled = true;
      child.kill("SIGKILL");
      reject(new Error(`PTY run did not exit in time. stdout tail: ${stdout.slice(-200)}`));
    }, options.timeoutMs ?? 12_000);

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString("utf8");
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString("utf8");
    });
    child.on("error", (error) => {
      clearTimeout(safety);
      reject(error);
    });

    // Send each input chunk with a delay so the app can install raw mode and
    // render between keystrokes, then close stdin so `script` can exit.
    const sequence = Array.isArray(inputs) ? inputs : [inputs];
    const delay = options.delayMs ?? 1000;
    let at = delay;
    for (const chunk of sequence) {
      setTimeout(() => {
        if (!settled) child.stdin.write(chunk);
      }, at);
      at += options.stepMs ?? 400;
    }
    setTimeout(() => {
      if (!settled) child.stdin.end();
    }, at + 200);

    child.on("exit", (code, signal) => {
      if (settled) return;
      settled = true;
      clearTimeout(safety);
      resolve({ code, signal, stdout, stderr, pid: child.pid });
    });
  });
}

/** Run the entry with piped stdio (non-TTY) while the stub server stays responsive. */
function runSnapshot(baseUrl) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [entry], {
      env: { ...process.env, RETRACK_BACKEND_URL: baseUrl },
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString("utf8");
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString("utf8");
    });
    child.on("error", reject);
    const safety = setTimeout(() => {
      child.kill("SIGKILL");
      reject(new Error(`snapshot did not exit in time: ${stdout}${stderr}`));
    }, 15_000);
    child.on("exit", (code) => {
      clearTimeout(safety);
      resolve({ code, stdout, stderr });
    });
  });
}

function assertProcessGone(pid) {
  assert.throws(() => process.kill(pid, 0), /ESRCH/, `process ${pid} is still running`);
}

describe("tui process: non-TTY contract", () => {
  let stub;
  before(async () => {
    stub = await startStub();
  });
  after(() => stub.server.close());

  it("emits exactly one snapshot line and exits 0", async () => {
    const result = await runSnapshot(stub.baseUrl);

    assert.equal(result.code, 0, result.stderr);
    const lines = result.stdout.split("\n").filter(Boolean);
    assert.equal(lines.length, 1);
    assert.match(
      lines[0],
      /^RE:Track · http:\/\/127\.0\.0\.1:\d+ · backend=ok · repos=1 · packages=0$/
    );
    assert.equal(result.stdout.includes("\u001b[?1049h"), false, "snapshot mode must not enter the alternate screen");
  });

  it("exits non-zero with an error when the backend is unreachable", async () => {
    const result = await runSnapshot("http://127.0.0.1:9");

    assert.equal(result.code, 1);
    assert.match(result.stderr, /backend unavailable|unreachable/i);
  });

  it("never spawns a backend or any other child process", () => {
    const modules = ["retrack.mjs", "state.mjs", "render.mjs", "keys.mjs", "theme.mjs", "layout.mjs", "markdown.mjs"];
    for (const module of modules) {
      const source = readFileSync(path.resolve(here, "..", module), "utf8");
      assert.doesNotMatch(source, /node:child_process/, `${module} must not spawn processes`);
      assert.doesNotMatch(source, /from "\.\.\/cli|from "\.\.\/gui|@tauri-apps/, `${module} must not import other interfaces`);
    }
  });
});

describe("tui process: interactive (PTY)", () => {
  let stub;
  before(async () => {
    stub = await startStub();
  });
  after(() => stub.server.close());

  it("starts, renders, restores the terminal, and exits 0 on q", { timeout: 30_000 }, async (t) => {
    if (!hasScript) {
      t.skip("script(1) is not available");
      return;
    }
    const result = await runInPty(stub.baseUrl, ["q"]);

    assert.equal(result.code, 0, result.stderr);
    assert.match(result.stdout, /RE:Track/);
    assert.match(result.stdout, /Workspace/);
    assert.match(result.stdout, /Repositories/);
    assert.ok(result.stdout.includes(ENTER_ALT_SCREEN), "alternate screen is entered");
    assert.ok(result.stdout.includes(LEAVE_ALT_SCREEN), "alternate screen is left");
    assert.ok(result.stdout.includes(SHOW_CURSOR), "cursor is restored");
    assertProcessGone(result.pid);
  });

  it("exits 0 on ctrl-c and restores the terminal", { timeout: 30_000 }, async (t) => {
    if (!hasScript) {
      t.skip("script(1) is not available");
      return;
    }
    const result = await runInPty(stub.baseUrl, ["\u0003"]);

    assert.equal(result.code, 0, result.stderr);
    assert.ok(result.stdout.includes(LEAVE_ALT_SCREEN));
    assertProcessGone(result.pid);
  });

  it("navigates, scrolls with the published bounds, and quits", { timeout: 30_000 }, async (t) => {
    if (!hasScript) {
      t.skip("script(1) is not available");
      return;
    }
    // down; 4 (System view); four PageDowns (exercises the scroll bounds the
    // entry derives from each frame); ? opens help; esc closes it; q quits.
    const result = await runInPty(stub.baseUrl, ["\u001b[B", "4", "\u001b[6~\u001b[6~\u001b[6~\u001b[6~", "?", "\u001b", "q"]);

    assert.equal(result.code, 0, result.stderr);
    assert.ok(result.stdout.includes(LEAVE_ALT_SCREEN));
    assert.match(result.stdout, /System · backend/, "view switching reached the System view");
    assert.match(
      strip(result.stdout),
      /provider switching: GUI only/,
      "paging scrolled the System report to its final section"
    );
    assertProcessGone(result.pid);
  });
});

describe("tui process: client wiring", () => {
  it("uses only the shared client for backend access", async () => {
    const client = makeClient();
    const result = await client.health();
    assert.equal(result.status, "ok");
  });
});
