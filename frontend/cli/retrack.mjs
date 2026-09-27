#!/usr/bin/env node
/**
 * RE:Track command-line interface.
 *
 * Explicit commands, predictable arguments, deterministic output. This is a
 * command surface, not an interactive interface: no prompts, no menus, no
 * alternate screen. Backend access goes through the shared interface contract
 * (frontend/shared/backend-client.mjs); backend startup/attachment goes through
 * this tree's lifecycle module.
 *
 * Output contract: human-readable on stdout by default, the raw backend payload
 * under `--json` (valid JSON, no control sequences, safe to pipe), progress and
 * diagnostics on stderr only.
 *
 * Usage:
 *   node frontend/cli/retrack.mjs <command> [arguments] [options]
 *   npm run cli -- <command> [arguments] [options]
 */

import { existsSync, mkdirSync, statSync, writeFileSync } from "node:fs";
import path from "node:path";

import { createBackendClient, BackendRequestError, BackendUnreachableError } from "../shared/backend-client.mjs";
import { parseArgv, parseTokenBudget, assertOptions, UsageError } from "./args.mjs";
import { renderMainHelp, renderCommandHelp, resolveHelpTopic, resolveCommandHelpKey } from "./help.mjs";
import { readSelection, writeSelection, SelectionError } from "./selection.mjs";
import { ensureBackend, BackendStartupError } from "./backend-lifecycle.mjs";

const DEFAULT_BUDGET = 4096;
const GLOBAL_OPTIONS = ["--json", "--url", "--no-start", "--help"];

/** A command that cannot proceed for an actionable reason. Maps to exit code 1. */
class CommandError extends Error {
  constructor(message) {
    super(message);
    this.name = "CommandError";
    this.exitCode = 1;
  }
}

/* --------------------------------- output --------------------------------- */

const out = (text) => process.stdout.write(text);
const err = (text) => process.stderr.write(text);

function printJson(payload) {
  out(`${JSON.stringify(payload, null, 2)}\n`);
}

function printPayload(json, payload, human) {
  if (json) {
    printJson(payload);
    return;
  }
  out(`${human(payload)}\n`);
}

function table(rows, headers) {
  if (rows.length === 0) return "(none)";
  const widths = headers.map((h, i) => Math.max(String(h).length, ...rows.map((r) => String(r[i] ?? "").length)));
  const line = (cells) => cells.map((c, i) => String(c ?? "").padEnd(widths[i])).join("  ");
  return [line(headers), widths.map((w) => "-".repeat(w)).join("  "), ...rows.map(line)].join("\n");
}

function formatList(values) {
  const list = Array.isArray(values) ? values.filter(Boolean) : [];
  return list.length ? list.join(", ") : "none";
}

function formatDuration(ms) {
  const total = Math.max(0, Math.round(ms / 1000));
  const seconds = String(total % 60).padStart(2, "0");
  const minutes = Math.floor(total / 60) % 60;
  const hours = Math.floor(total / 3600);
  if (hours > 0) return `${hours}:${String(minutes).padStart(2, "0")}:${seconds}`;
  return `${String(minutes).padStart(2, "0")}:${seconds}`;
}

function formatBytes(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "unavailable";
  if (value < 1024) return `${value} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let size = value / 1024;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(1)} ${units[index]}`;
}

/** ISO timestamp trimmed to minute precision; absent values stay stated. */
function shortTimestamp(value) {
  if (typeof value !== "string" || value.trim() === "") return "-";
  return value.slice(0, 16).replace("T", " ");
}

function evidenceLabel(state) {
  const labels = { sufficient: "Sufficient", partial: "Partial", none: "No evidence" };
  return labels[state] ?? (typeof state === "string" && state ? state : "unavailable");
}

/** A single stderr line that updates in place — only for an interactive terminal. */
function createProgressLine(enabled) {
  let active = false;
  return {
    update(text) {
      if (!enabled) return;
      process.stderr.write(`\r\u001b[K${text}`);
      active = true;
    },
    clear() {
      if (!active) return;
      process.stderr.write("\r\u001b[K");
      active = false;
    },
  };
}

/* ------------------------------- repositories ------------------------------ */

async function loadRepositories(client) {
  const payload = await client.listRepositories();
  return Array.isArray(payload?.repositories) ? payload.repositories : [];
}

/** Match a repository by resolved path first, then by exact name. */
function findRepository(repositories, selector) {
  const target = String(selector ?? "").trim();
  if (!target) return null;
  const resolved = path.resolve(target);
  const byPath = repositories.filter(
    (repo) => typeof repo.local_path === "string" && path.resolve(repo.local_path) === resolved
  );
  if (byPath.length === 1) return byPath[0];
  const byName = repositories.filter((repo) => repo.name === target);
  if (byName.length > 1) {
    throw new CommandError(`repository name "${target}" is ambiguous (${byName.length} tracked); use the path`);
  }
  return byName[0] ?? null;
}

function requireRepository(repositories, selector) {
  const repo = findRepository(repositories, selector);
  if (!repo) {
    throw new CommandError(`repository not found: ${selector} (run "retrack list repositories" or "retrack index <path>")`);
  }
  return repo;
}

/** The repository a command operates on: positional, then --repo, then the stored selection. */
function targetSelector(options, positional) {
  if (positional) return positional;
  if (options.repo) return options.repo;
  const selection = readSelection();
  if (!selection) {
    throw new CommandError('no repository given or selected: pass a path or --repo, or run "retrack select <path>"');
  }
  return selection.path;
}

/** Register a directory that is not tracked yet, then scan it so its catalog row is real. */
async function ensureTrackedRepository(client, selector) {
  const repoPath = path.resolve(selector);
  if (!existsSync(repoPath) || !statSync(repoPath).isDirectory()) {
    throw new CommandError(
      `repository not found: ${selector} (no tracked repository matches and no directory exists at ${repoPath})`
    );
  }
  const registered = await client.createRepository({ sourceType: "local", localPath: repoPath });
  if (!registered?.id) {
    throw new CommandError(`could not register repository at ${repoPath}`);
  }
  await client.scanRepository(registered.id);
  return registered;
}

async function resolveRepository(client, options, positional) {
  const selector = targetSelector(options, positional);
  const repositories = await loadRepositories(client);
  const found = findRepository(repositories, selector);
  if (found) return found;
  return ensureTrackedRepository(client, selector);
}

/* --------------------------------- writing -------------------------------- */

/** Write exact bytes, never silently destroying an existing file. */
function writeFileExact(target, contents, { force = false } = {}) {
  const resolved = path.resolve(target);
  if (!force && existsSync(resolved)) {
    throw new CommandError(`file already exists: ${resolved} (pass --force to overwrite)`);
  }
  mkdirSync(path.dirname(resolved), { recursive: true });
  writeFileSync(resolved, contents, { encoding: "utf8", flag: force ? "w" : "wx" });
  return { path: resolved, bytes: Buffer.byteLength(contents, "utf8") };
}

/** Turn a 404 into a plain "not found" message instead of an HTTP string. */
function mapNotFound(error, message) {
  if (error instanceof BackendRequestError && error.status === 404) return new CommandError(message);
  return error;
}

/* --------------------------------- commands -------------------------------- */

async function cmdHealth(ctx) {
  const health = await ctx.client.health();
  printPayload(ctx.json, health, (h) =>
    table(
      [
        ["Backend", h.status],
        ["Provider", `${h.provider_identity ?? h.provider ?? "unknown"} (${h.provider_health_state ?? "unknown"})`],
        ["Configured model", h.configured_model ?? "None"],
        ["Verified active model", h.active_model ?? "None verified"],
        ["Cognee", h.cognee_state ?? (h.cognee_initialized ? "healthy" : "unavailable")],
        ["Repositories", h.repository_count ?? 0],
        ["Context packages", h.context_package_count ?? 0],
        ["Concurrency queue depth", `${h.concurrency_queue_depth ?? 0}/${h.concurrency_queue_capacity ?? 0}`],
        ["RAM", h.ram_total_gb ? `${h.ram_used_gb ?? 0}/${h.ram_total_gb} GB` : "Unavailable"],
        ["CPU", h.cpu_percent ?? "Unavailable"],
        ["Execution device", h.execution_device ?? "Unavailable"],
      ],
      ["Metric", "Value"]
    )
  );
  return 0;
}

async function cmdStatus(ctx) {
  const status = await ctx.client.status();
  if (ctx.json) {
    printJson(status);
    return 0;
  }
  const body = table(
    [
      ["Status", status.status],
      ["Endpoint", status.llm_endpoint ?? `${status.ollama_host}:${status.ollama_port}`],
      ["LLM model", status.llm_model],
      ["Embedding model", status.embedding_model],
      ["Vector DB", status.vector_db],
      ["Graph DB", status.graph_db],
      ["Relational DB", status.relational_db],
      ["Data root", status.data_root],
      ["System root", status.system_root],
      ["Cognee initialized", status.cognee_initialized],
    ],
    ["Setting", "Value"]
  );
  let selected = "none (retrack select <path>)";
  try {
    const selection = readSelection();
    if (selection) selected = `${selection.name || selection.path} (${selection.path})`;
  } catch (error) {
    selected = `unreadable: ${error.message}`;
  }
  out(`${body}\n\nSelected repository: ${selected}\n`);
  return 0;
}

async function cmdMemory(ctx) {
  const stats = await ctx.client.memoryStats();
  printPayload(ctx.json, stats, (s) =>
    table(
      [
        ["Total size", s.total_size_display ?? "Unavailable"],
        ["Datasets", s.dataset_count ?? 0],
        ["Knowledge graph status", s.knowledge_graph_status ?? "Unavailable"],
        ["Graph nodes", s.graph_nodes ?? "Unavailable"],
        ["Graph edges", s.graph_edges ?? "Unavailable"],
      ],
      ["Metric", "Value"]
    )
  );
  return 0;
}

async function cmdBenchmark(ctx) {
  const result = await ctx.client.runBenchmark();
  printPayload(ctx.json, result, (r) =>
    table(
      (r.results ?? []).map((item) => [
        String(item.question ?? "").slice(0, 48),
        item.context_tokens ?? 0,
        item.compression_ratio ?? 0,
        item.token_savings_percent ?? 0,
        item.total_time_ms ?? item.latency_ms ?? 0,
      ]),
      ["Question", "Ctx tokens", "Ratio", "Savings %", "ms"]
    )
  );
  return 0;
}

async function cmdListRepositories(ctx) {
  const payload = await ctx.client.listRepositories();
  printPayload(ctx.json, payload, (p) =>
    table(
      (p.repositories ?? []).map((repo) => [
        repo.name,
        repo.local_path,
        repo.status,
        repo.file_count ?? 0,
        formatList(repo.languages),
        shortTimestamp(repo.indexed_at),
      ]),
      ["Name", "Path", "Status", "Files", "Languages", "Indexed"]
    )
  );
  return 0;
}

async function cmdListPackages(ctx) {
  const payload = await ctx.client.listContextPackages();
  printPayload(ctx.json, payload, (p) =>
    table(
      (p.packages ?? []).map((pkg) => [
        pkg.id,
        pkg.name,
        pkg.repository_name || "-",
        pkg.token_estimate ?? 0,
        shortTimestamp(pkg.updated_at ?? pkg.created_at),
      ]),
      ["Id", "Name", "Repository", "Tokens", "Updated"]
    )
  );
  return 0;
}

async function cmdSelect(ctx, target) {
  if (!target) {
    // Reporting the stored selection is a local read: it works with no backend.
    const selection = readSelection();
    if (!selection) {
      if (ctx.json) printJson({ selection: null });
      else out("no repository selected\n");
      return 0;
    }
    if (ctx.json) printJson({ selection });
    else out(`selected ${selection.name || selection.path} (${selection.path})\n`);
    return 0;
  }

  const repositories = await loadRepositories(ctx.client);
  const repo = requireRepository(repositories, target);
  writeSelection({ id: repo.id, name: repo.name, path: repo.local_path });
  if (ctx.json) printJson({ selection: { id: repo.id, name: repo.name, path: repo.local_path } });
  else out(`selected ${repo.name} (${repo.local_path})\n`);
  return 0;
}

async function cmdIndex(ctx, positional) {
  const repo = await resolveRepository(ctx.client, ctx.options, positional);
  const startedAt = Date.now();
  const progress = createProgressLine(Boolean(process.stderr.isTTY) && !ctx.json);

  let polling = false;
  const poll = async () => {
    if (polling) return;
    polling = true;
    try {
      const payload = await ctx.client.repositoryProgress(repo.id);
      const elapsed = formatDuration(Date.now() - startedAt);
      if (typeof payload?.stage_index === "number" && typeof payload?.stage_total === "number") {
        progress.update(`indexing ${repo.name} · phase ${payload.stage_index}/${payload.stage_total} · ${payload.stage ?? "working"} · elapsed ${elapsed}`);
      } else if (payload?.stage) {
        progress.update(`indexing ${repo.name} · ${payload.stage} · elapsed ${elapsed}`);
      } else {
        progress.update(`indexing ${repo.name} · elapsed ${elapsed}`);
      }
    } catch {
      // Progress is a courtesy; a failed poll must never fail the indexing run.
    } finally {
      polling = false;
    }
  };

  const timer = setInterval(() => void poll(), 1000);
  let result;
  try {
    result = await ctx.client.indexRepository({
      repositoryPath: repo.local_path,
      datasetName: ctx.options.dataset ?? repo.name,
      forceReindex: true,
    });
  } finally {
    clearInterval(timer);
    progress.clear();
  }

  const elapsed = formatDuration(Date.now() - startedAt);
  if (ctx.json) {
    printJson(result);
  } else {
    out(`indexed ${repo.name}\n`);
    out(`files: ${result?.processed_files ?? "unavailable"}/${result?.total_files ?? "unavailable"} processed · ${result?.failed_files ?? "unavailable"} failed\n`);
    out(`elapsed ${elapsed}\n`);
  }
  return result?.success === false ? 1 : 0;
}

async function cmdScan(ctx, positional) {
  const repo = await resolveRepository(ctx.client, ctx.options, positional);
  const result = await ctx.client.scanRepository(repo.id);
  printPayload(ctx.json, result, (r) =>
    [
      `scanned ${repo.name}`,
      `files: ${r.file_count ?? "unavailable"}`,
      `size: ${formatBytes(r.size_bytes)}`,
      `languages: ${formatList(r.languages)}`,
      `frameworks: ${formatList(r.frameworks)}`,
    ].join("\n")
  );
  return 0;
}

async function cmdConstruct(ctx, prompt, budget) {
  const repo = requireRepository(await loadRepositories(ctx.client), targetSelector(ctx.options, undefined));
  const maxTokens = budget;
  const includeStructuralGraph = ctx.flags.graph ?? true;

  if (!ctx.json) err(`synthesizing context for ${repo.name} (budget ${maxTokens})…\n`);
  const response = await ctx.client.agentContext({
    taskPrompt: prompt,
    repositoryPath: repo.local_path,
    datasetName: ctx.options.dataset ?? repo.name,
    maxTokens,
    includeStructuralGraph,
  });

  if (response?.success === false) {
    if (ctx.json) printJson(response);
    else {
      err(`context generation failed: ${response.message ?? response.error ?? "no detail provided"}\n`);
    }
    return 1;
  }

  const markdown = typeof response?.context_markdown === "string" ? response.context_markdown : "";
  if (ctx.options.output) {
    const written = writeFileExact(ctx.options.output, markdown, { force: Boolean(ctx.flags.force) });
    if (ctx.json) printJson({ repository: repo.name, budget: maxTokens, path: written.path, bytes: written.bytes });
    else out(`wrote ${written.path} (${written.bytes} bytes)\n`);
    return 0;
  }

  if (ctx.json) {
    printJson(response);
    return 0;
  }
  const strength =
    typeof response?.evidence_score === "number" ? `${Math.round(Math.min(1, Math.max(0, response.evidence_score)) * 100)}%` : "unavailable";
  const header = [
    `repository: ${repo.name}`,
    `budget: ${maxTokens}`,
    `evidence: ${evidenceLabel(response?.evidence_state)} (${strength})`,
    `tokens: ${response?.estimated_tokens ?? "unavailable"}`,
  ];
  if (response?.abstained) header.push("engine abstained from unsupported claims");
  out(`${header.join("\n")}\n\n${markdown}\n`);
  return 0;
}

async function cmdShowPackage(ctx, id) {
  let pkg;
  try {
    pkg = await ctx.client.getContextPackage(id);
  } catch (error) {
    throw mapNotFound(error, `package not found: ${id}`);
  }
  if (!pkg?.id) throw new CommandError(`package not found: ${id}`);
  if (ctx.json) {
    printJson(pkg);
    return 0;
  }
  const header = [
    `package: ${pkg.name || id} (${pkg.id})`,
    `repository: ${pkg.repository_name || "unavailable"}`,
    `task: ${pkg.task || pkg.objective || "unavailable"}`,
    `tokens: ${pkg.token_estimate ?? "unavailable"} · sections: ${pkg.section_count ?? "unavailable"}`,
    `updated: ${shortTimestamp(pkg.updated_at ?? pkg.created_at)}`,
  ];
  out(`${header.join("\n")}\n\n${pkg.markdown ?? ""}\n`);
  return 0;
}

async function cmdAppendPackage(ctx, id, text) {
  let updated;
  try {
    // The backend contract is explicit: `additional_task` becomes the package's
    // task metadata and `additional_markdown` is what extends the stored
    // Markdown (after a separator). The note is user content, so it is sent as
    // both — sending an empty Markdown field is what made the append invisible.
    updated = await ctx.client.appendContextPackage(id, { task: text, markdown: text });
  } catch (error) {
    throw mapNotFound(error, `package not found: ${id}`);
  }
  if (ctx.json) printJson(updated);
  else out(`appended to ${updated?.name ?? id} (${id}) · tokens ${updated?.token_estimate ?? "unavailable"} · updated ${shortTimestamp(updated?.updated_at)}\n`);
  return 0;
}

async function cmdDeletePackage(ctx, id) {
  try {
    await ctx.client.deleteContextPackage(id);
  } catch (error) {
    throw mapNotFound(error, `package not found: ${id}`);
  }
  if (ctx.json) printJson({ deleted: id });
  else out(`deleted package ${id}\n`);
  return 0;
}

async function cmdExportPackage(ctx, id, target) {
  let pkg;
  try {
    pkg = await ctx.client.getContextPackage(id);
  } catch (error) {
    throw mapNotFound(error, `package not found: ${id}`);
  }
  const markdown = typeof pkg?.markdown === "string" ? pkg.markdown : "";
  if (!markdown) throw new CommandError(`package ${id} stores no Markdown to export`);
  const written = writeFileExact(target, markdown, { force: Boolean(ctx.flags.force) });
  if (ctx.json) printJson({ package_id: id, path: written.path, bytes: written.bytes });
  else out(`exported ${id} → ${written.path} (${written.bytes} bytes)\n`);
  return 0;
}

async function cmdResynthesizePackage(ctx, id, budget) {
  let pkg;
  try {
    pkg = await ctx.client.getContextPackage(id);
  } catch (error) {
    throw mapNotFound(error, `package not found: ${id}`);
  }
  const task = String(pkg?.task || pkg?.objective || "").trim();
  if (!task) throw new CommandError(`${pkg?.name ?? id}: the package stores no task to regenerate`);
  const repositories = await loadRepositories(ctx.client);
  const repo =
    repositories.find((item) => item.id === pkg.repository_id) ??
    repositories.find((item) => item.name === pkg.repository_name);
  if (!repo) {
    throw new CommandError(
      `${pkg.name ?? id}: repository ${pkg.repository_name || pkg.repository_id || "unknown"} is not registered here`
    );
  }

  const maxTokens = budget;
  const includeStructuralGraph = ctx.flags.graph ?? true;
  if (!ctx.json) err(`regenerating ${pkg.name ?? id} from its stored task (budget ${maxTokens})…\n`);
  const response = await ctx.client.agentContext({
    taskPrompt: task,
    repositoryPath: repo.local_path,
    datasetName: repo.name,
    maxTokens,
    includeStructuralGraph,
  });
  const markdown = typeof response?.context_markdown === "string" ? response.context_markdown : "";
  if (response?.success === false || markdown.trim() === "") {
    throw new CommandError(`the regeneration returned no context; ${id} is unchanged`);
  }

  await ctx.client.replaceContextPackage(id, {
    markdown,
    objective: response.task_summary || undefined,
    token_estimate: response.estimated_tokens ?? undefined,
    total_time_ms: response.generation_time_ms ?? response.total_time_ms ?? undefined,
    repository_commit: repo.commit_hash || undefined,
  });
  const updated = await ctx.client.getContextPackage(id);
  if (ctx.json) printJson(updated);
  else out(`re-synthesized ${updated?.name ?? id} (${id}) · tokens ${updated?.token_estimate ?? "unavailable"} · updated ${shortTimestamp(updated?.updated_at)}\n`);
  return 0;
}

async function cmdDeleteRepository(ctx, target) {
  const repositories = await loadRepositories(ctx.client);
  const repo = requireRepository(repositories, target);
  await ctx.client.deleteRepository(repo.id);
  if (ctx.json) printJson({ deleted: repo.id, name: repo.name, path: repo.local_path });
  else out(`deleted repository ${repo.name} (${repo.local_path})\n`);
  return 0;
}

async function cmdSettings(ctx) {
  const settings = await ctx.client.appSettings();
  printPayload(ctx.json, settings, (s) =>
    table(
      [
        ["Provider", s.llm_provider],
        ["Endpoint", s.llm_endpoint],
        ["Model", s.llm_model],
        ["Embedding model", s.embedding_model],
        ["Semantic memory provider", s.semantic_memory_provider || "unavailable"],
        ["Semantic memory model", s.memory_model || "unavailable"],
        ["Vector DB", s.vector_db],
        ["Graph DB", s.graph_db],
        ["Relational DB", s.relational_db],
        ["Knowledge graph extraction", s.enable_kg_extraction],
        ["Entity auto-linking", s.auto_link_entities],
        ["Ingestion caching", s.caching],
        ["Data root", s.data_root],
        ["System root", s.system_root],
        ["API key configured", s.api_key_configured],
      ],
      ["Setting", "Value"]
    )
  );
  return 0;
}

async function cmdProvider(ctx) {
  const status = await ctx.client.providerStatus();
  printPayload(ctx.json, status, (s) =>
    table(
      [
        ["Provider", s.provider],
        ["Endpoint", s.base_url],
        ["Reachable", s.is_reachable],
        ["Health", s.health_state],
        ["Active model", s.active_model ?? "None verified"],
        ["Discovery", s.discovery_status],
        ["Models reported", (s.loaded_models ?? []).length],
      ],
      ["Setting", "Value"]
    )
  );
  return 0;
}

async function cmdProviderModels(ctx) {
  const status = await ctx.client.providerStatus();
  const discovery = await ctx.client.discoverProvider({ provider: status.provider, base_url: status.base_url });
  if (ctx.json) {
    printJson(discovery);
    return 0;
  }
  const lines = [`provider: ${discovery.provider} · ${discovery.base_url}`, `status: ${discovery.status}`];
  if (discovery.status === "available") {
    const models = discovery.models ?? [];
    lines.push(`models: ${models.length}`);
    for (const model of models) {
      const markers = [model.quantization && model.quantization !== "unknown" ? model.quantization : null, model.model_id === status.active_model ? "active" : null]
        .filter(Boolean)
        .join(" · ");
      lines.push(`  ${model.model_id}${markers ? `  ${markers}` : ""}`);
      if (model.warning) lines.push(`    ${model.warning}`);
    }
  } else {
    lines.push(`message: ${discovery.message || "no detail provided"}`);
    if (discovery.error_details) lines.push(`detail: ${discovery.error_details}`);
  }
  out(`${lines.join("\n")}\n`);
  return 0;
}

/* --------------------------------- routing -------------------------------- */

function routeCommand(positionals, { flags, options }) {
  const [verb, ...rest] = positionals;
  const noExtra = (args) => {
    if (args.length > 0) throw new UsageError(`unexpected argument "${args[0]}" for "${verb}"`);
  };

  switch (verb) {
    case "health":
      noExtra(rest);
      return { key: "health", options: [], run: cmdHealth };
    case "status":
      noExtra(rest);
      return { key: "status", options: [], run: cmdStatus };
    case "memory":
      noExtra(rest);
      return { key: "memory", options: [], run: cmdMemory };
    case "benchmark":
      noExtra(rest);
      return { key: "benchmark", options: [], run: cmdBenchmark };
    case "settings":
      noExtra(rest);
      return { key: "settings", options: [], run: cmdSettings };
    case "provider": {
      if (rest.length === 0) return { key: "provider", options: [], run: cmdProvider };
      if (rest.length === 1 && rest[0] === "models") return { key: "provider", options: [], run: cmdProviderModels };
      throw new UsageError(`unknown provider target: ${rest.join(" ") || "(none)"} (expected "models")`);
    }
    case "list": {
      const what = rest[0];
      if (what === "repositories") {
        noExtra(rest.slice(1));
        return { key: "list-repositories", options: [], run: cmdListRepositories };
      }
      if (what === "packages") {
        noExtra(rest.slice(1));
        return { key: "list-packages", options: [], run: cmdListPackages };
      }
      throw new UsageError(`unknown list target: ${what ?? "(none)"} (expected "repositories" or "packages")`);
    }
    case "select": {
      if (rest.length > 1) throw new UsageError(`unexpected argument "${rest[1]}" for "select"`);
      // `select` with no argument only reports local state; no backend needed.
      return { key: "select", options: [], local: !rest[0], run: (ctx) => cmdSelect(ctx, rest[0]) };
    }
    case "index": {
      if (rest.length > 1) throw new UsageError(`unexpected argument "${rest[1]}" for "index"`);
      return { key: "index", options: ["--repo", "--dataset"], run: (ctx) => cmdIndex(ctx, rest[0]) };
    }
    case "scan": {
      if (rest.length > 1) throw new UsageError(`unexpected argument "${rest[1]}" for "scan"`);
      return { key: "scan", options: ["--repo"], run: (ctx) => cmdScan(ctx, rest[0]) };
    }
    case "construct": {
      const prompt = rest[0];
      if (!prompt || prompt.trim() === "") {
        throw new UsageError('usage: retrack construct "<prompt>" [<budget>]');
      }
      if (rest.length > 2) throw new UsageError(`unexpected argument "${rest[2]}" for "construct"`);
      const positional = rest[1] !== undefined ? parseTokenBudget(rest[1]) : undefined;
      const flagged = options.budget !== undefined ? parseTokenBudget(options.budget) : undefined;
      if (positional !== undefined && flagged !== undefined) {
        throw new UsageError("the token budget was given twice (positional and --budget); pass one");
      }
      if (flags.json && options.output !== undefined) {
        throw new UsageError("--json and --output are mutually exclusive: JSON goes to stdout, Markdown to a file");
      }
      return {
        key: "construct",
        options: ["--repo", "--dataset", "--budget", "--output", "--force", "--graph", "--no-graph"],
        run: (ctx) => cmdConstruct(ctx, prompt, positional ?? flagged ?? DEFAULT_BUDGET),
      };
    }
    case "show": {
      if (rest[0] !== "package") throw new UsageError(`unknown show target: ${rest[0] ?? "(none)"} (expected "package")`);
      if (!rest[1]) throw new UsageError("usage: retrack show package <id>");
      if (rest.length > 2) throw new UsageError(`unexpected argument "${rest[2]}" for "show package"`);
      return { key: "show-package", options: [], run: (ctx) => cmdShowPackage(ctx, rest[1]) };
    }
    case "append": {
      if (rest[0] !== "package") throw new UsageError(`unknown append target: ${rest[0] ?? "(none)"} (expected "package")`);
      if (!rest[1]) throw new UsageError('usage: retrack append package <id> "<text>"');
      const text = rest.slice(2).join(" ").trim();
      if (!text) throw new UsageError('usage: retrack append package <id> "<text>"');
      return { key: "append-package", options: [], run: (ctx) => cmdAppendPackage(ctx, rest[1], text) };
    }
    case "delete": {
      const what = rest[0];
      if (what === "package") {
        if (!rest[1]) throw new UsageError("usage: retrack delete package <id> --yes");
        if (rest.length > 2) throw new UsageError(`unexpected argument "${rest[2]}" for "delete package"`);
        if (!flags.yes) throw new UsageError(`refusing to delete package ${rest[1]} without --yes`);
        return { key: "delete-package", options: ["--yes"], run: (ctx) => cmdDeletePackage(ctx, rest[1]) };
      }
      if (what === "repository") {
        if (!rest[1]) throw new UsageError("usage: retrack delete repository <path|name> --yes");
        if (rest.length > 2) throw new UsageError(`unexpected argument "${rest[2]}" for "delete repository"`);
        if (!flags.yes) throw new UsageError(`refusing to delete repository ${rest[1]} without --yes`);
        return { key: "delete-repository", options: ["--yes"], run: (ctx) => cmdDeleteRepository(ctx, rest[1]) };
      }
      throw new UsageError(`unknown delete target: ${what ?? "(none)"} (expected "package" or "repository")`);
    }
    case "export": {
      if (rest[0] !== "package") throw new UsageError(`unknown export target: ${rest[0] ?? "(none)"} (expected "package")`);
      if (!rest[1]) throw new UsageError("usage: retrack export package <id> <path>");
      if (!rest[2]) throw new UsageError("usage: retrack export package <id> <path>");
      if (rest.length > 3) throw new UsageError(`unexpected argument "${rest[3]}" for "export package"`);
      return { key: "export-package", options: ["--force"], run: (ctx) => cmdExportPackage(ctx, rest[1], rest[2]) };
    }
    case "resynthesize": {
      if (rest[0] !== "package") {
        throw new UsageError(`unknown resynthesize target: ${rest[0] ?? "(none)"} (expected "package")`);
      }
      if (!rest[1]) throw new UsageError("usage: retrack resynthesize package <id> --yes");
      if (rest.length > 2) throw new UsageError(`unexpected argument "${rest[2]}" for "resynthesize package"`);
      if (!flags.yes) throw new UsageError(`refusing to replace package ${rest[1]} without --yes`);
      const budget = options.budget !== undefined ? parseTokenBudget(options.budget) : DEFAULT_BUDGET;
      return {
        key: "resynthesize-package",
        options: ["--yes", "--budget", "--graph", "--no-graph"],
        run: (ctx) => cmdResynthesizePackage(ctx, rest[1], budget),
      };
    }
    default:
      throw new UsageError(`unknown command: ${verb ?? "(none)"}`);
  }
}

/* ---------------------------------- entry --------------------------------- */

async function main(argv) {
  const { flags, options, positionals, used } = parseArgv(argv);
  const [verb] = positionals;

  if (!verb) {
    out(`${renderMainHelp()}\n`);
    return 0;
  }
  if (verb === "help") {
    const topic = resolveHelpTopic(positionals[1]);
    if (positionals[1] && !topic) throw new UsageError(`unknown command: ${positionals[1]}`);
    if (positionals[2]) throw new UsageError(`unexpected argument "${positionals[2]}" for "help"`);
    out(`${topic ? renderCommandHelp(topic) : renderMainHelp()}\n`);
    return 0;
  }

  // Command-level help is resolved before routing: `retrack construct --help`
  // and `retrack delete --help` must work without the arguments those commands
  // require, and without a backend, a selection or any filesystem access.
  if (flags.help) {
    const helpKey = resolveCommandHelpKey(positionals);
    if (helpKey) {
      out(`${renderCommandHelp(helpKey)}\n`);
      return 0;
    }
  }

  const command = routeCommand(positionals, { flags, options });
  assertOptions(used, [...GLOBAL_OPTIONS, ...command.options], verb);

  const context = { client: null, json: Boolean(flags.json), flags, options };
  if (command.local) return (await command.run(context)) ?? 0;

  const backend = await ensureBackend({
    baseUrl: options.url,
    autoStart: !flags.noStart,
    onStatus: (text) => {
      if (!flags.json) err(`${text}\n`);
    },
  });
  const client = createBackendClient({ baseUrl: backend.baseUrl });

  const onSignal = (signal, code) => {
    process.once(signal, () => {
      void backend.stop().finally(() => process.exit(code));
    });
  };
  onSignal("SIGINT", 130);
  onSignal("SIGTERM", 143);

  try {
    context.client = client;
    return await command.run(context);
  } finally {
    await backend.stop();
  }
}

main(process.argv.slice(2))
  .then((code) => {
    process.exitCode = code ?? 0;
  })
  .catch((error) => {
    if (error instanceof UsageError) {
      err(`error: ${error.message}\n`);
      err('run "retrack help" for the command tree\n');
      process.exitCode = 2;
      return;
    }
    if (error instanceof BackendStartupError) {
      err(`error: ${error.message}\n`);
      process.exitCode = 1;
      return;
    }
    if (error instanceof BackendUnreachableError) {
      err(`error: backend unavailable at ${error.baseUrl}\n`);
      process.exitCode = 1;
      return;
    }
    if (error instanceof BackendRequestError) {
      err(`error: ${error.message}\n`);
      process.exitCode = 1;
      return;
    }
    if (error instanceof SelectionError) {
      err(`error: ${error.message}\n`);
      process.exitCode = 1;
      return;
    }
    err(`error: ${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = error?.exitCode ?? 1;
  });
