import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { startStubBackend } from "./stub-backend.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const CLI = path.resolve(here, "..", "retrack.mjs");

function runCli(args, { env = {}, timeoutMs = 20_000 } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [CLI, ...args], {
      env: { ...process.env, ...env },
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
    const timer = setTimeout(() => {
      child.kill("SIGKILL");
      reject(new Error(`cli did not exit: ${args.join(" ")}\n${stdout}${stderr}`));
    }, timeoutMs);
    child.on("error", reject);
    child.on("exit", (code) => {
      clearTimeout(timer);
      resolve({ code, stdout, stderr });
    });
  });
}

/** Run a body with a stub backend, an isolated selection file and a CLI runner. */
async function withStub(overrides, body) {
  const stub = await startStubBackend(overrides);
  const dir = mkdtempSync(path.join(os.tmpdir(), "retrack-cli-cmd-"));
  const env = {
    RETRACK_BACKEND_URL: stub.baseUrl,
    RETRACK_CLI_STATE: path.join(dir, "state.json"),
  };
  try {
    await body({
      stub,
      dir,
      env,
      run: (args, extra = {}) => runCli(args, { env: { ...env, ...extra } }),
      routes: () => stub.requests.map((entry) => entry.route),
    });
  } finally {
    await stub.close();
    rmSync(dir, { recursive: true, force: true });
  }
}

describe("cli commands: help and usage", () => {
  it("prints the command tree and per-command help", async () => {
    const main = await runCli(["help"]);
    assert.equal(main.code, 0);
    assert.match(main.stdout, /Usage: retrack <command>/);
    assert.match(main.stdout, /construct "<prompt>" \[<budget>\]/);
    assert.match(main.stdout, /Exit codes:/);

    const construct = await runCli(["help", "construct"]);
    assert.equal(construct.code, 0);
    assert.match(construct.stdout, /retrack construct "<prompt>" \[<budget>\]/);
    assert.match(construct.stdout, /Arguments:/);
    assert.match(construct.stdout, /--output <path>/);
    assert.match(construct.stdout, /retrack construct "Explain how authentication works" 4k/);

    const flagHelp = await runCli(["index", "--help"]);
    assert.equal(flagHelp.code, 0);
    assert.match(flagHelp.stdout, /retrack index \[<path>\]/);

    const unknownTopic = await runCli(["help", "nonsense"]);
    assert.equal(unknownTopic.code, 2);
  });

  it("rejects unknown commands and options with exit code 2", async () => {
    const unknown = await runCli(["frobnicate"]);
    assert.equal(unknown.code, 2);
    assert.match(unknown.stderr, /unknown command: frobnicate/);
    assert.equal(unknown.stdout, "");

    const option = await runCli(["health", "--repo", "/work/alpha"]);
    assert.equal(option.code, 2);
    assert.match(option.stderr, /--repo is not valid for "health"/);

    const typo = await runCli(["health", "--jsn"]);
    assert.equal(typo.code, 2);
    assert.match(typo.stderr, /unknown option: --jsn/);

    const unsafeDelete = await runCli(["delete", "package", "pkg-1"]);
    assert.equal(unsafeDelete.code, 2);
    assert.match(unsafeDelete.stderr, /without --yes/);
  });
});

describe("cli commands: repositories", () => {
  it("lists repositories with backend fields and raw JSON", async () => {
    await withStub({}, async ({ run, stub }) => {
      const human = await run(["list", "repositories"]);
      assert.equal(human.code, 0);
      assert.match(human.stdout, /Name\s+Path\s+Status\s+Files\s+Languages\s+Indexed/);
      assert.match(human.stdout, /alpha\s+\/work\/alpha\s+indexed\s+12\s+Python, Markdown\s+2026-09-20 10:00/);
      assert.match(human.stdout, /beta\s+\/work\/beta\s+registered\s+0\s+none\s+-/);

      const json = await run(["list", "repositories", "--json"]);
      assert.equal(json.code, 0);
      const payload = JSON.parse(json.stdout);
      assert.equal(payload.total_count, 2);
      assert.equal(payload.repositories[0].local_path, "/work/alpha");
      assert.equal(stub.requests.every((entry) => entry.method === "GET"), true);
    });
  });

  it("lists packages with the ids later commands need", async () => {
    await withStub({}, async ({ run }) => {
      const result = await run(["list", "packages"]);
      assert.equal(result.code, 0);
      assert.match(result.stdout, /Id\s+Name\s+Repository\s+Tokens\s+Updated/);
      assert.match(result.stdout, /pkg-1\s+Auth context\s+alpha\s+256/);
    });
  });

  it("persists a selection and uses it for later commands", async () => {
    await withStub({}, async ({ run, stub, dir }) => {
      const empty = await run(["select"]);
      assert.equal(empty.code, 0);
      assert.match(empty.stdout, /no repository selected/);
      assert.equal(stub.requests.length, 0, "reporting the selection needs no backend");

      const selected = await run(["select", "/work/alpha"]);
      assert.equal(selected.code, 0);
      assert.match(selected.stdout, /selected alpha \(\/work\/alpha\)/);
      const stored = JSON.parse(readFileSync(path.join(dir, "state.json"), "utf8"));
      assert.deepEqual(stored.repository, { id: "repo-a", name: "alpha", path: "/work/alpha" });

      const report = await run(["select"]);
      assert.match(report.stdout, /selected alpha \(\/work\/alpha\)/);

      // `index` with no path and `construct` with no --repo both use the selection.
      const index = await run(["index"]);
      assert.equal(index.code, 0);
      assert.match(index.stdout, /indexed alpha/);
      const call = stub.requests.find((entry) => entry.route === "POST /index");
      assert.deepEqual(call.body, { repository_path: "/work/alpha", dataset_name: "alpha", force_reindex: true });
    });
  });

  it("selects by name and rejects unknown or ambiguous names", async () => {
    await withStub({}, async ({ run }) => {
      const byName = await run(["select", "beta"]);
      assert.equal(byName.code, 0);
      assert.match(byName.stdout, /selected beta \(\/work\/beta\)/);

      const missing = await run(["select", "/work/nope"]);
      assert.equal(missing.code, 1);
      assert.match(missing.stderr, /repository not found: \/work\/nope/);
    });

    await withStub(
      {
        repositories: [
          { id: "repo-a", name: "dup", local_path: "/work/one", status: "registered" },
          { id: "repo-b", name: "dup", local_path: "/work/two", status: "registered" },
        ],
      },
      async ({ run }) => {
        const ambiguous = await run(["select", "dup"]);
        assert.equal(ambiguous.code, 1);
        assert.match(ambiguous.stderr, /ambiguous/);
      }
    );
  });

  it("registers and scans a path before indexing it", async () => {
    await withStub({}, async ({ run, dir, routes, stub }) => {
      const fresh = path.join(dir, "fresh-project");
      const { mkdirSync } = await import("node:fs");
      mkdirSync(fresh);
      const result = await run(["index", fresh]);
      assert.equal(result.code, 0);
      assert.deepEqual(
        routes().filter((route) => route !== "GET /repos" && route !== "GET /health"),
        ["POST /repos", "POST /repos/repo-new/scan", "POST /index"],
        "an untracked path is registered and scanned before indexing"
      );
      const registered = stub.requests.find((entry) => entry.route === "POST /repos");
      assert.equal(registered.body.local_path, fresh);
      const index = stub.requests.find((entry) => entry.route === "POST /index");
      assert.equal(index.body.repository_path, fresh);
    });
  });

  it("fails an indexing run whose backend result reports failures", async () => {
    await withStub(
      { indexResult: { success: false, repository_path: "/work/alpha", dataset_name: "alpha", total_files: 12, processed_files: 10, failed_files: 2, total_batches: 2, failed_paths: ["a.py"], summary: "Indexed 10/12 files" } },
      async ({ run }) => {
        const result = await run(["index", "/work/alpha"]);
        assert.equal(result.code, 1);
        assert.match(result.stdout, /files: 10\/12 processed · 2 failed/);
      }
    );
  });

  it("reports an untracked path that does not exist without registering it", async () => {
    await withStub({}, async ({ run, routes }) => {
      const result = await run(["index", "/work/definitely-missing"]);
      assert.equal(result.code, 1);
      assert.match(result.stderr, /repository not found: \/work\/definitely-missing/);
      assert.equal(routes().includes("POST /repos"), false);
    });
  });

  it("scans a tracked repository and prints what the backend detected", async () => {
    await withStub({}, async ({ run, stub }) => {
      const result = await run(["scan", "/work/alpha"]);
      assert.equal(result.code, 0);
      assert.match(result.stdout, /scanned alpha/);
      assert.match(result.stdout, /languages: Python/);
      assert.match(result.stdout, /frameworks: FastAPI/);
      assert.equal(stub.requests.some((entry) => entry.route === "POST /repos/repo-a/scan"), true);
    });
  });

  it("deletes a repository only with --yes", async () => {
    await withStub({}, async ({ run, stub }) => {
      const refused = await run(["delete", "repository", "beta"]);
      assert.equal(refused.code, 2);
      assert.equal(stub.requests.length, 0, "a refused deletion never reaches the backend");

      const deleted = await run(["delete", "repository", "/work/beta", "--yes"]);
      assert.equal(deleted.code, 0);
      assert.match(deleted.stdout, /deleted repository beta \(\/work\/beta\)/);
      assert.equal(stub.requests.some((entry) => entry.route === "DELETE /repos/repo-b"), true);
    });
  });
});

describe("cli commands: construct", () => {
  it("prints a small metadata header and the generated Markdown", async () => {
    await withStub({}, async ({ run, stub }) => {
      const result = await run(["construct", "Explain auth", "8k", "--repo", "/work/alpha"]);
      assert.equal(result.code, 0);
      assert.match(result.stdout, /^repository: alpha\nbudget: 8192\nevidence: Sufficient \(50%\)\ntokens: 120\n\n# Task Context/m);
      const call = stub.requests.find((entry) => entry.route === "POST /api/v1/context");
      assert.equal(call.body.task_prompt, "Explain auth");
      assert.equal(call.body.repository_path, "/work/alpha");
      assert.equal(call.body.max_tokens, 8192);
      assert.equal(call.body.include_structural_graph, true);
    });
  });

  it("defaults to a 4k budget and honors --budget and --no-graph", async () => {
    await withStub({}, async ({ run, stub }) => {
      await run(["construct", "Explain auth", "--repo", "alpha"]);
      let call = stub.requests.find((entry) => entry.route === "POST /api/v1/context");
      assert.equal(call.body.max_tokens, 4096);

      stub.requests.length = 0;
      await run(["construct", "Explain auth", "--repo", "alpha", "--budget", "16k", "--no-graph"]);
      call = stub.requests.find((entry) => entry.route === "POST /api/v1/context");
      assert.equal(call.body.max_tokens, 16384);
      assert.equal(call.body.include_structural_graph, false);
    });
  });

  it("emits the raw payload as pure JSON", async () => {
    await withStub({}, async ({ run, stub }) => {
      const result = await run(["construct", "Explain auth", "--repo", "/work/alpha", "--json"]);
      assert.equal(result.code, 0);
      assert.equal(result.stdout.includes("\u001b"), false, "no escape sequences on stdout");
      assert.equal(result.stdout.includes("synthesizing"), false, "no human progress noise in JSON mode");
      const payload = JSON.parse(result.stdout);
      assert.equal(payload.context_markdown, stub.state.context.context_markdown);
      assert.equal(payload.evidence_state, "sufficient");
    });
  });

  it("rejects a doubled budget and --json with --output", async () => {
    const doubled = await runCli(["construct", "x", "4k", "--budget", "8k"]);
    assert.equal(doubled.code, 2);
    assert.match(doubled.stderr, /token budget was given twice/);

    const conflict = await runCli(["construct", "x", "--json", "--output", "out.md"]);
    assert.equal(conflict.code, 2);
    assert.match(conflict.stderr, /--json and --output are mutually exclusive/);
  });

  it("fails non-zero when the backend reports a failed generation", async () => {
    await withStub(
      { context: { success: false, context_markdown: "", message: "provider unavailable", evidence_state: "none" } },
      async ({ run }) => {
        const human = await run(["construct", "Explain auth", "--repo", "/work/alpha"]);
        assert.equal(human.code, 1);
        assert.match(human.stderr, /context generation failed: provider unavailable/);

        const json = await run(["construct", "Explain auth", "--repo", "/work/alpha", "--json"]);
        assert.equal(json.code, 1);
        assert.equal(JSON.parse(json.stdout).success, false, "the payload is still emitted for automation");
      }
    );
  });

  it("writes the exact Markdown with --output and never overwrites silently", async () => {
    await withStub({}, async ({ run, dir, stub }) => {
      const target = path.join(dir, "context.md");
      const written = await run(["construct", "Explain auth", "--repo", "alpha", "--output", target]);
      assert.equal(written.code, 0);
      assert.match(written.stdout, /wrote .*context\.md \(\d+ bytes\)/);
      assert.equal(readFileSync(target, "utf8"), stub.state.context.context_markdown);

      const again = await run(["construct", "Explain auth", "--repo", "alpha", "--output", target]);
      assert.equal(again.code, 1);
      assert.match(again.stderr, /file already exists/);
      assert.equal(readFileSync(target, "utf8"), stub.state.context.context_markdown);

      const forced = await run(["construct", "Explain auth", "--repo", "alpha", "--output", target, "--force"]);
      assert.equal(forced.code, 0);
    });
  });

  it("refuses to construct without a repository", async () => {
    await withStub({}, async ({ run }) => {
      const result = await run(["construct", "Explain auth"]);
      assert.equal(result.code, 1);
      assert.match(result.stderr, /no repository given or selected/);
    });
  });
});

describe("cli commands: packages", () => {
  it("shows a stored package with its Markdown intact", async () => {
    await withStub({}, async ({ run }) => {
      const result = await run(["show", "package", "pkg-1"]);
      assert.equal(result.code, 0);
      assert.match(result.stdout, /package: Auth context \(pkg-1\)/);
      assert.match(result.stdout, /repository: alpha/);
      assert.match(result.stdout, /task: Explain auth/);
      assert.match(result.stdout, /# Auth context\n\n- `create_session`/);

      const missing = await run(["show", "package", "pkg-404"]);
      assert.equal(missing.code, 1);
      assert.match(missing.stderr, /package not found: pkg-404/);
    });
  });

  it("appends a task without regenerating anything", async () => {
    await withStub({}, async ({ run, stub }) => {
      const result = await run(["append", "package", "pkg-1", "Include deployment considerations"]);
      assert.equal(result.code, 0);
      assert.match(result.stdout, /appended to Auth context \(pkg-1\)/);
      const call = stub.requests.find((entry) => entry.route === "POST /packages/pkg-1/append");
      assert.equal(call.body.additional_task, "Include deployment considerations");
      assert.equal(stub.requests.some((entry) => entry.route === "POST /api/v1/context"), false, "append never regenerates");
    });
  });

  it("deletes a package only with --yes", async () => {
    await withStub({}, async ({ run, stub }) => {
      const refused = await run(["delete", "package", "pkg-1"]);
      assert.equal(refused.code, 2);

      const deleted = await run(["delete", "package", "pkg-1", "--yes"]);
      assert.equal(deleted.code, 0);
      assert.match(deleted.stdout, /deleted package pkg-1/);
      assert.equal(stub.requests.some((entry) => entry.route === "DELETE /packages/pkg-1"), true);
    });
  });

  it("exports the stored Markdown byte for byte and respects --force", async () => {
    await withStub({}, async ({ run, dir, stub }) => {
      const target = path.join(dir, "nested", "context.md");
      const result = await run(["export", "package", "pkg-1", target, "--json"]);
      assert.equal(result.code, 0);
      const report = JSON.parse(result.stdout);
      assert.equal(report.path, target);
      assert.equal(readFileSync(target, "utf8"), stub.state.packages[0].markdown);

      const again = await run(["export", "package", "pkg-1", target]);
      assert.equal(again.code, 1);
      assert.match(again.stderr, /file already exists/);

      const forced = await run(["export", "package", "pkg-1", target, "--force"]);
      assert.equal(forced.code, 0);
      assert.equal(readFileSync(target, "utf8"), stub.state.packages[0].markdown);
    });
  });

  it("re-synthesizes in place: one generation, one replacement, no second package", async () => {
    await withStub({}, async ({ run, stub }) => {
      const refused = await run(["resynthesize", "package", "pkg-1"]);
      assert.equal(refused.code, 2, "replacing stored content needs --yes");

      const result = await run(["resynthesize", "package", "pkg-1", "--yes", "--budget", "8k"]);
      assert.equal(result.code, 0);
      assert.match(result.stdout, /re-synthesized Auth context \(pkg-1\)/);
      const generation = stub.requests.filter((entry) => entry.route === "POST /api/v1/context");
      assert.equal(generation.length, 1);
      assert.equal(generation[0].body.task_prompt, "Explain auth");
      assert.equal(generation[0].body.max_tokens, 8192);
      const replacement = stub.requests.filter((entry) => entry.route === "PUT /packages/pkg-1");
      assert.equal(replacement.length, 1);
      assert.equal(replacement[0].body.markdown, stub.state.context.context_markdown);
      assert.equal(stub.requests.some((entry) => entry.route === "POST /packages"), false, "no second package is created");
    });
  });

  it("leaves the stored package untouched when regeneration returns nothing", async () => {
    const original = "# Auth context\n\n- `create_session`\n";
    await withStub(
      { context: { success: true, context_markdown: "   ", task_summary: "Explain auth", evidence_state: "none" } },
      async ({ run, stub }) => {
        const result = await run(["resynthesize", "package", "pkg-1", "--yes"]);
        assert.equal(result.code, 1);
        assert.match(result.stderr, /the regeneration returned no context; pkg-1 is unchanged/);
        assert.equal(stub.requests.some((entry) => entry.route === "PUT /packages/pkg-1"), false);
        assert.equal(stub.state.packages[0].markdown, original);
      }
    );
  });

  it("refuses to re-synthesize a package whose repository is not registered", async () => {
    await withStub(
      { packages: [{ ...(await import("./stub-backend.mjs")).defaultPackages()[0], repository_id: "repo-gone", repository_name: "gone" }] },
      async ({ run }) => {
        const result = await run(["resynthesize", "package", "pkg-1", "--yes"]);
        assert.equal(result.code, 1);
        assert.match(result.stderr, /repository gone is not registered here/);
      }
    );
  });
});

describe("cli commands: provider and operational reads", () => {
  it("reports provider status and discovered models", async () => {
    await withStub({}, async ({ run, stub }) => {
      const status = await run(["provider"]);
      assert.equal(status.code, 0);
      assert.match(status.stdout, /lmstudio/);
      assert.match(status.stdout, /Active model\s+phi3:mini/);

      const models = await run(["provider", "models"]);
      assert.equal(models.code, 0);
      assert.match(models.stdout, /status: available/);
      assert.match(models.stdout, /phi3:mini {2}active/);
      assert.match(models.stdout, /qwen2\.5-7b {2}Q4_K_M/);
      assert.equal(stub.requests.some((entry) => entry.route === "POST /provider/discover"), true);
    });
  });

  it("renders an unavailable model list with the backend's own reason", async () => {
    await withStub(
      { discovery: { success: true, provider: "lmstudio", base_url: "http://127.0.0.1:1234/v1", is_reachable: false, status: "unreachable", models: [], message: "connection refused" } },
      async ({ run }) => {
        const result = await run(["provider", "models"]);
        assert.equal(result.code, 0);
        assert.match(result.stdout, /status: unreachable/);
        assert.match(result.stdout, /message: connection refused/);
      }
    );
  });

  it("prints status with the selected repository, plus settings, memory and benchmark", async () => {
    await withStub({}, async ({ run }) => {
      await run(["select", "/work/alpha"]);
      const status = await run(["status"]);
      assert.equal(status.code, 0);
      assert.match(status.stdout, /Selected repository: alpha \(\/work\/alpha\)/);

      const settings = await run(["settings"]);
      assert.equal(settings.code, 0);
      assert.match(settings.stdout, /lancedb/);

      const memory = await run(["memory"]);
      assert.equal(memory.code, 0);
      assert.match(memory.stdout, /1\.2 MB/);

      const benchmark = await run(["benchmark"]);
      assert.equal(benchmark.code, 0);
      assert.match(benchmark.stdout, /How does auth work/);
    });
  });
});

describe("cli commands: errors and machine output", () => {
  it("reports an unreachable backend without starting one under --no-start", async () => {
    const result = await runCli(["health", "--no-start", "--url", "http://127.0.0.1:65531"]);
    assert.equal(result.code, 1);
    assert.match(result.stderr, /backend unavailable at http:\/\/127\.0\.0\.1:65531/);
    assert.equal(result.stdout, "");
  });

  it("keeps JSON output free of progress noise and ANSI escapes", async () => {
    await withStub({}, async ({ run }) => {
      const result = await run(["index", "/work/alpha", "--json"]);
      assert.equal(result.code, 0);
      assert.equal(result.stdout.includes("\u001b"), false);
      assert.equal(result.stdout.includes("starting backend"), false);
      const payload = JSON.parse(result.stdout);
      assert.equal(payload.processed_files, 12);
    });
  });

  it("never claims success for a package operation that failed", async () => {
    await withStub({}, async ({ run }) => {
      const missing = await run(["append", "package", "pkg-404", "more"]);
      assert.equal(missing.code, 1);
      assert.match(missing.stderr, /package not found: pkg-404/);
    });
  });
});
