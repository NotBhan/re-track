import { describe, it, before, after } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";

import { BackendRequestError, BackendUnreachableError, ENDPOINTS, createBackendClient } from "../../shared/backend-client.mjs";

/** Minimal stub of the backend HTTP contract: records requests, returns canned JSON. */
function startStub() {
  const seen = [];
  const server = http.createServer((req, res) => {
    const chunks = [];
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("end", () => {
      const body = chunks.length ? JSON.parse(Buffer.concat(chunks).toString("utf8")) : null;
      seen.push({ method: req.method, url: req.url, body });
      res.setHeader("Content-Type", "application/json");
      if (req.url.startsWith("/fail")) {
        res.statusCode = 400;
        res.end(JSON.stringify({ detail: { message: "validation failed" } }));
        return;
      }
      res.end(JSON.stringify({ ok: true, method: req.method, url: req.url, body }));
    });
  });
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      resolve({ server, seen, baseUrl: `http://127.0.0.1:${port}` });
    });
  });
}

describe("shared backend client additions", () => {
  let stub;
  let client;

  before(async () => {
    stub = await startStub();
    client = createBackendClient({ baseUrl: stub.baseUrl });
  });

  after(() => stub.server.close());

  it("exposes the endpoints required by the TUI", () => {
    assert.equal(ENDPOINTS.repositories, "/repos");
    assert.equal(ENDPOINTS.diagnosticsExport, "/diagnostics/export");
    assert.equal(ENDPOINTS.recentLogs, "/logs/recent");
    assert.equal(ENDPOINTS.contextPackages, "/packages");
  });

  it("creates a repository with the backend payload shape", async () => {
    await client.createRepository({ sourceType: "local", localPath: "/tmp/repo", name: "demo" });
    const [request] = stub.seen.slice(-1);
    assert.equal(request.method, "POST");
    assert.equal(request.url, "/repos");
    // Keys whose value is undefined are omitted by JSON, matching "absent"
    // rather than sending an invented null.
    assert.deepEqual(request.body, {
      source_type: "local",
      local_path: "/tmp/repo",
      name: "demo",
    });
  });

  it("creates a github repository with a source url", async () => {
    await client.createRepository({ sourceType: "github", sourceUrl: "https://example.com/x.git" });
    const [request] = stub.seen.slice(-1);
    assert.deepEqual(request.body, {
      source_type: "github",
      source_url: "https://example.com/x.git",
    });
  });

  it("scans, reads progress, and deletes a repository by id", async () => {
    await client.scanRepository("abc 123");
    assert.equal(stub.seen.at(-1).method, "POST");
    assert.equal(stub.seen.at(-1).url, "/repos/abc%20123/scan");
    assert.deepEqual(stub.seen.at(-1).body, {});

    await client.repositoryProgress("abc");
    assert.equal(stub.seen.at(-1).method, "GET");
    assert.equal(stub.seen.at(-1).url, "/repos/abc/progress");

    await client.deleteRepository("abc");
    assert.equal(stub.seen.at(-1).method, "DELETE");
    assert.equal(stub.seen.at(-1).url, "/repos/abc");
  });

  it("reads repository prompts", async () => {
    await client.repositoryPrompts("abc");
    assert.equal(stub.seen.at(-1).url, "/repos/abc/prompts");
  });

  it("reads, saves, and deletes context packages", async () => {
    await client.getContextPackage("pkg 1");
    assert.equal(stub.seen.at(-1).url, "/packages/pkg%201");

    const payload = { name: "demo", markdown: "# hi", token_estimate: 12 };
    await client.saveContextPackage(payload);
    assert.equal(stub.seen.at(-1).method, "POST");
    assert.equal(stub.seen.at(-1).url, "/packages");
    assert.deepEqual(stub.seen.at(-1).body, payload);

    await client.deleteContextPackage("pkg-1");
    assert.equal(stub.seen.at(-1).method, "DELETE");
    assert.equal(stub.seen.at(-1).url, "/packages/pkg-1");
  });

  it("exports diagnostics and reads recent logs with a limit", async () => {
    await client.exportDiagnostics();
    assert.equal(stub.seen.at(-1).method, "POST");
    assert.equal(stub.seen.at(-1).url, "/diagnostics/export");

    await client.recentLogs(20);
    assert.equal(stub.seen.at(-1).url, "/logs/recent?limit=20");
  });

  it("raises BackendRequestError with the backend detail on HTTP errors", async () => {
    const failing = createBackendClient({ baseUrl: `${stub.baseUrl}/fail` });
    await assert.rejects(
      () => failing.listRepositories(),
      (error) => {
        assert.ok(error instanceof BackendRequestError);
        assert.equal(error.status, 400);
        assert.equal(error.detail, "validation failed");
        return true;
      }
    );
  });

  it("raises BackendUnreachableError when nothing is listening", async () => {
    const dead = createBackendClient({ baseUrl: "http://127.0.0.1:9" });
    await assert.rejects(
      () => dead.health(),
      (error) => {
        assert.ok(error instanceof BackendUnreachableError);
        assert.match(error.message, /backend unreachable/i);
        return true;
      }
    );
  });
});
