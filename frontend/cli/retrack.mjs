#!/usr/bin/env node
/**
 * RE:Track command-line interface.
 *
 * Presentation + argument parsing only. All backend access goes through the
 * shared interface contract module (frontend/shared/backend-client.mjs).
 *
 * This entry point must never import React, Tauri APIs, or GUI components.
 *
 * Usage:
 *   node frontend/cli/retrack.mjs <command> [options]
 *   npm run cli -- <command> [options]
 */

import { createBackendClient, BackendRequestError, BackendUnreachableError } from "../shared/backend-client.mjs";

const HELP = `
RE:Track CLI

Usage: retrack <command> [options]

Commands:
  health                     Provider, engine, storage and concurrency health
  status                     Backend configuration and storage roots
  repos                      Registered repositories
  packages                   Saved context packages
  memory                     Memory layer statistics
  context <task>             Synthesize a Context Package for a task
  index <path>               Index a repository directory
  benchmark                  Run the deterministic benchmark suite
  help                       Show this message

Options:
  -r, --repo <path|name>     Repository path (context/index)
  -d, --dataset <name>       Dataset name for memory namespace
  -t, --max-tokens <n>       Token budget for context synthesis (default 8000)
  -k, --top-k <n>            Retrieval depth for context synthesis (default 15)
  -u, --url <base-url>       Backend origin (default $RETRACK_BACKEND_URL or http://127.0.0.1:8765)
      --json                 Emit raw JSON instead of a formatted table
  -h, --help                 Show this message
`.trim();

function parseArgs(argv) {
  const options = { _: [], json: false };
  const withValue = new Set(["-r", "--repo", "-d", "--dataset", "-t", "--max-tokens", "-k", "--top-k", "-u", "--url"]);
  const aliases = {
    "-r": "repo",
    "--repo": "repo",
    "-d": "dataset",
    "--dataset": "dataset",
    "-t": "maxTokens",
    "--max-tokens": "maxTokens",
    "-k": "topK",
    "--top-k": "topK",
    "-u": "url",
    "--url": "url",
  };

  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === "--json") {
      options.json = true;
    } else if (token === "-h" || token === "--help") {
      options.help = true;
    } else if (withValue.has(token)) {
      const value = argv[i + 1];
      if (value === undefined) throw new Error(`Missing value for ${token}`);
      options[aliases[token]] = value;
      i += 1;
    } else if (token.startsWith("--") && token.includes("=")) {
      const [flag, ...rest] = token.split("=");
      options[aliases[flag] ?? flag.replace(/^--/, "")] = rest.join("=");
    } else {
      options._.push(token);
    }
  }
  return options;
}

function table(rows, headers) {
  if (rows.length === 0) return "(none)";
  const widths = headers.map((h, i) =>
    Math.max(String(h).length, ...rows.map((r) => String(r[i] ?? "").length))
  );
  const line = (cells) => cells.map((c, i) => String(c ?? "").padEnd(widths[i])).join("  ");
  return [line(headers), widths.map((w) => "-".repeat(w)).join("  "), ...rows.map(line)].join("\n");
}

function print(payload, options, formatter) {
  if (options.json) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    return;
  }
  process.stdout.write(`${formatter(payload)}\n`);
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const command = options._[0];

  if (!command || command === "help" || options.help) {
    process.stdout.write(`${HELP}\n`);
    return 0;
  }

  const client = createBackendClient({ baseUrl: options.url });

  switch (command) {
    case "health": {
      const health = await client.health();
      print(health, options, (h) =>
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

    case "status": {
      const status = await client.status();
      print(status, options, (s) =>
        table(
          [
            ["Status", s.status],
            ["Endpoint", s.llm_endpoint ?? `${s.ollama_host}:${s.ollama_port}`],
            ["LLM model", s.llm_model],
            ["Embedding model", s.embedding_model],
            ["Vector DB", s.vector_db],
            ["Graph DB", s.graph_db],
            ["Relational DB", s.relational_db],
            ["Data root", s.data_root],
            ["System root", s.system_root],
            ["Cognee initialized", s.cognee_initialized],
          ],
          ["Setting", "Value"]
        )
      );
      return 0;
    }

    case "repos": {
      const result = await client.listRepositories();
      print(result, options, (r) =>
        table(
          (r.repositories ?? []).map((repo) => [
            repo.name,
            repo.status,
            repo.local_path,
            repo.file_count ?? 0,
            repo.call_graph_status ?? "not_analyzed",
          ]),
          ["Name", "Status", "Path", "Files", "AST"]
        )
      );
      return 0;
    }

    case "packages": {
      const result = await client.listContextPackages();
      print(result, options, (r) =>
        table(
          (r.packages ?? []).map((pkg) => [
            pkg.name,
            pkg.repository_name || "-",
            pkg.token_estimate ?? 0,
            pkg.created_at,
          ]),
          ["Name", "Repository", "Tokens", "Created"]
        )
      );
      return 0;
    }

    case "memory": {
      const stats = await client.memoryStats();
      print(stats, options, (s) =>
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

    case "context": {
      const task = options._.slice(1).join(" ");
      if (!task.trim()) throw new Error("Usage: retrack context <task> [-r <repository-path>] [-d <dataset>]");
      if (!options.repo) throw new Error("A repository path is required: retrack context <task> --repo <path>");

      const response = await client.agentContext({
        taskPrompt: task,
        repositoryPath: options.repo,
        datasetName: options.dataset,
        maxTokens: options.maxTokens ? Number(options.maxTokens) : undefined,
      });

      if (options.json) {
        process.stdout.write(`${JSON.stringify(response, null, 2)}\n`);
      } else if (response.success === false) {
        process.stderr.write(`Context synthesis failed [${response.error}]: ${response.message}\n`);
        return 1;
      } else {
        process.stdout.write(`${response.context_markdown ?? ""}\n`);
      }
      return response.success === false ? 1 : 0;
    }

    case "index": {
      const repositoryPath = options.repo ?? options._[1];
      if (!repositoryPath) throw new Error("Usage: retrack index <path> [-d <dataset>]");
      const result = await client.indexRepository({
        repositoryPath,
        datasetName: options.dataset ?? repositoryPath.split(/[\\/]/).filter(Boolean).pop(),
        forceReindex: true,
      });
      print(result, options, (r) =>
        table(
          [
            ["Repository", r.repository_path],
            ["Dataset", r.dataset_name],
            ["Total files", r.total_files],
            ["Processed", r.processed_files],
            ["Failed", r.failed_files],
            ["Summary", r.summary],
          ],
          ["Metric", "Value"]
        )
      );
      return 0;
    }

    case "benchmark": {
      const result = await client.runBenchmark();
      print(result, options, (r) =>
        table(
          (r.results ?? []).map((item) => [
            item.question.slice(0, 48),
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

    default:
      process.stderr.write(`Unknown command: ${command}\n\n${HELP}\n`);
      return 1;
  }
}

main()
  .then((code) => {
    process.exitCode = code ?? 0;
  })
  .catch((error) => {
    if (error instanceof BackendUnreachableError) {
      process.stderr.write(`${error.message}\n`);
    } else if (error instanceof BackendRequestError) {
      process.stderr.write(`${error.message}\n`);
    } else {
      process.stderr.write(`Error: ${error.message}\n`);
    }
    process.exitCode = 1;
  });
