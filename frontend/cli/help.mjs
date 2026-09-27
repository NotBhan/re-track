/**
 * RE:Track CLI help system.
 *
 * One data table drives both `retrack help` and `retrack <command> --help`, so
 * the command tree and the per-command reference can never disagree. The text
 * describes what a developer wants to do, not which use case executes.
 */

export const GLOBAL_OPTIONS = [
  ["--url <base-url>", "Backend origin (default $RETRACK_BACKEND_URL, else http://127.0.0.1:8765)"],
  ["--json", "Machine-readable output: the raw backend payload, no progress noise"],
  ["--no-start", "Never start a backend; fail if none is reachable"],
  ["-h, --help", "Show help (with a command: that command's help)"],
];

export const COMMANDS = {
  help: {
    usage: "retrack help [command]",
    summary: "Show this help, or one command's help",
    description: [
      "With no argument, prints the command tree. With a command name, prints that",
      "command's arguments, options and examples.",
    ],
    args: [["[command]", "Command to describe (health, index, construct, ...)"]],
    options: [],
    examples: ["retrack help", "retrack help construct"],
  },
  health: {
    usage: "retrack health",
    summary: "Backend, provider, engine and concurrency health",
    description: [
      "Answers: is RE:Track operational? Reports the backend status, the active",
      "provider and its health, engine state, counts, concurrency guard and hardware",
      "facts as the backend reports them.",
    ],
    args: [],
    options: [],
    examples: ["retrack health", "retrack health --json"],
  },
  status: {
    usage: "retrack status",
    summary: "Backend configuration and storage roots",
    description: [
      "Answers: what is RE:Track configured with? Shows the active databases, models,",
      "endpoints and storage roots from GET /status, plus the CLI's selected repository.",
    ],
    args: [],
    options: [],
    examples: ["retrack status", "retrack status --json"],
  },
  list: {
    usage: "retrack list <repositories|packages>",
    summary: "List tracked repositories or saved context packages",
    description: [
      "Lists the resources the backend reports. Both targets have their own reference:",
      "`retrack help list repositories` and `retrack help list packages`.",
    ],
    args: [
      ["repositories", "Tracked repositories (name, path, status, files, languages, indexed time)"],
      ["packages", "Saved context packages (id, name, repository, tokens, updated)"],
    ],
    options: [],
    examples: ["retrack list repositories", "retrack list packages", "retrack list packages --json"],
  },
  delete: {
    usage: "retrack delete <package|repository> <target> --yes",
    summary: "Delete a stored package or a managed repository",
    description: [
      "Destructive: both forms require --yes and the CLI never prompts. Deleting a",
      "repository also clears its indexed memory. Each target has its own reference:",
      "`retrack help delete package` and `retrack help delete repository`.",
    ],
    args: [
      ["package <id>", "Stored context package id from `retrack list packages`"],
      ["repository <path|name>", "Repository path or name from `retrack list repositories`"],
    ],
    options: [["--yes", "Confirm the deletion (required)"]],
    examples: ["retrack delete package 5f3a9c2b1d --yes", "retrack delete repository ~/Projects/old --yes"],
  },
  "list-repositories": {
    usage: "retrack list repositories",
    summary: "Tracked repositories",
    description: ["Lists every repository the backend manages, with the fields the backend reports."],
    args: [],
    options: [],
    examples: ["retrack list repositories", "retrack list repositories --json"],
  },
  "list-packages": {
    usage: "retrack list packages",
    summary: "Saved context packages",
    description: ["Lists saved context packages with the id needed by show/append/export/delete."],
    args: [],
    options: [],
    examples: ["retrack list packages", "retrack list packages --json"],
  },
  select: {
    usage: "retrack select [<path|name>]",
    summary: "Set (or show) the CLI's default repository",
    description: [
      "Establishes the repository later commands operate on, persisted at",
      "~/.retrack/cli-state.json (override with RETRACK_CLI_STATE). With no argument it",
      "reports the current selection. `--repo` on another command overrides the",
      "selection for that invocation only and never changes what is stored here.",
    ],
    args: [["[path|name]", "Repository path or name, as shown by `retrack list repositories`"]],
    options: [],
    examples: ["retrack select ~/Projects/my-project", "retrack select", "retrack select my-project"],
  },
  index: {
    usage: "retrack index [<path>]",
    summary: "Index a repository, registering and scanning it first when needed",
    description: [
      "Runs the application's indexing operation against a repository. A path that is",
      "not tracked yet is registered and scanned first, so the repository catalog stays",
      "truthful. Live phase progress (from the backend's own progress record) is written",
      "to stderr; results go to stdout.",
    ],
    args: [["[path]", "Repository directory (defaults to --repo, else the selected repository)"]],
    options: [
      ["--repo <path|name>", "Repository to index, overriding the selected repository"],
      ["--dataset <name>", "Memory dataset name (defaults to the repository's name)"],
    ],
    examples: ["retrack index ~/Projects/my-project", "retrack select ~/Projects/my-project && retrack index"],
  },
  scan: {
    usage: "retrack scan [<path>]",
    summary: "Rescan a repository's languages, frameworks and size",
    description: [
      "Refreshes the repository's scan metadata (languages, frameworks, file count, size,",
      "components) without indexing. A path that is not tracked yet is registered first.",
    ],
    args: [["[path]", "Repository directory (defaults to --repo, else the selected repository)"]],
    options: [["--repo <path|name>", "Repository to scan, overriding the selected repository"]],
    examples: ["retrack scan", "retrack scan ~/Projects/my-project"],
  },
  construct: {
    usage: 'retrack construct "<prompt>" [<budget>]',
    summary: "Generate a context package for a task",
    description: [
      "Synthesizes a context package for a prompt against a repository and prints the",
      "generated Markdown with a small metadata header. The budget accepts 4k, 8k, 16k,",
      "32k (k = 1024) or a plain token count >= 100; it defaults to 4k.",
    ],
    args: [
      ["<prompt>", "The task to synthesize context for (quote it)"],
      ["[budget]", "Token budget (4k, 8k, 16k, 32k, or an integer >= 100); default 4k"],
    ],
    options: [
      ["--repo <path|name>", "Repository, overriding the selected one"],
      ["--budget <value>", "Token budget, for scripts that prefer a flag"],
      ["--dataset <name>", "Memory dataset name (defaults to the repository's name)"],
      ["--no-graph", "Exclude the structural call graph from synthesis"],
      ["--output <path>", "Write the generated Markdown to a file (exact bytes)"],
      ["--force", "With --output: overwrite an existing file"],
    ],
    examples: [
      'retrack construct "Explain how authentication works" 4k',
      'retrack construct "Trace the evidence gate" --repo re-track --json | jq .evidence_state',
      'retrack construct "Summarize the indexing pipeline" 8k --output context.md',
    ],
  },
  "show-package": {
    usage: "retrack show package <id>",
    summary: "Print a stored package and its Markdown",
    description: ["Reads one stored package and prints its metadata plus the stored Markdown exactly as saved."],
    args: [["<id>", "Package id from `retrack list packages`"]],
    options: [],
    examples: ["retrack show package 5f3a9c2b1d", "retrack show package 5f3a9c2b1d --json"],
  },
  "append-package": {
    usage: 'retrack append package <id> "<text>"',
    summary: "Append a task/note to a stored package",
    description: [
      "Appends the note to an existing package (POST /packages/{id}/append): the note",
      "becomes the package's task and is added to the stored Markdown after a",
      "separator, so it stays visible in the package content. This is not",
      "re-synthesis: append never regenerates content and invokes no model.",
    ],
    args: [
      ["<id>", "Package id"],
      ["<text>", "Additional task or note (quote it)"],
    ],
    options: [],
    examples: ['retrack append package 5f3a9c2b1d "Include deployment considerations"'],
  },
  "delete-package": {
    usage: "retrack delete package <id> --yes",
    summary: "Delete a stored package",
    description: ["Deletes a stored package. Requires --yes: the CLI never prompts interactively."],
    args: [["<id>", "Package id"]],
    options: [["--yes", "Confirm the deletion"]],
    examples: ["retrack delete package 5f3a9c2b1d --yes"],
  },
  "export-package": {
    usage: "retrack export package <id> <path>",
    summary: "Write a stored package's Markdown to a file",
    description: [
      "Writes the already-stored Markdown byte for byte to an explicit path and reports",
      "the path it wrote. An existing file is never overwritten unless --force is given.",
    ],
    args: [
      ["<id>", "Package id"],
      ["<path>", "Destination file path"],
    ],
    options: [["--force", "Overwrite the destination if it exists"]],
    examples: ["retrack export package 5f3a9c2b1d ./context.md", "retrack export package 5f3a9c2b1d ./context.md --force"],
  },
  "resynthesize-package": {
    usage: "retrack resynthesize package <id> --yes",
    summary: "Regenerate a stored package in place",
    description: [
      "Regenerates the package from its own stored task against its repository, then",
      "replaces the stored Markdown in place (one PUT /packages/{id}, never a second",
      "package). Generation runs first: if it returns nothing, the stored package is",
      "left exactly as it was. Requires --yes.",
    ],
    args: [["<id>", "Package id"]],
    options: [
      ["--yes", "Confirm replacing the stored Markdown"],
      ["--budget <value>", "Token budget for the regeneration (default 4k)"],
      ["--no-graph", "Exclude the structural call graph from the regeneration"],
    ],
    examples: ["retrack resynthesize package 5f3a9c2b1d --yes", "retrack resynthesize package 5f3a9c2b1d --budget 8k --yes"],
  },
  "delete-repository": {
    usage: "retrack delete repository <path|name> --yes",
    summary: "Delete a repository and its indexed memory",
    description: [
      "Deletes a managed repository and clears its indexed memory from the backend.",
      "Requires --yes: the CLI never prompts interactively.",
    ],
    args: [["<path|name>", "Repository path or name"]],
    options: [["--yes", "Confirm the deletion"]],
    examples: ["retrack delete repository ~/Projects/old-project --yes", "retrack delete repository old-project --yes"],
  },
  settings: {
    usage: "retrack settings",
    summary: "Persisted application configuration",
    description: ["Prints the stored configuration (providers, models, pipeline toggles, storage roots). Read-only."],
    args: [],
    options: [],
    examples: ["retrack settings", "retrack settings --json"],
  },
  provider: {
    usage: "retrack provider [models]",
    summary: "Active inference provider, or its discovered models",
    description: [
      "`provider` shows the authoritative active provider status. `provider models`",
      "probes the active endpoint (POST /provider/discover, non-mutating) and lists the",
      "models it actually returned. Configuration changes stay in the TUI/GUI.",
    ],
    args: [["[models]", "List the models the active endpoint offers"]],
    options: [],
    examples: ["retrack provider", "retrack provider models", "retrack provider models --json"],
  },
  memory: {
    usage: "retrack memory",
    summary: "Memory layer statistics",
    description: ["Prints dataset count, storage size and knowledge-graph status from GET /memory/stats."],
    args: [],
    options: [],
    examples: ["retrack memory"],
  },
  benchmark: {
    usage: "retrack benchmark",
    summary: "Run the deterministic benchmark suite",
    description: ["Runs the backend's benchmark suite and prints one row per question. Long-running."],
    args: [],
    options: [],
    examples: ["retrack benchmark", "retrack benchmark --json"],
  },
};

const ENTRY_ORDER = [
  "help",
  "health",
  "status",
  "list-repositories",
  "list-packages",
  "select",
  "index",
  "scan",
  "construct",
  "show-package",
  "append-package",
  "delete-package",
  "export-package",
  "resynthesize-package",
  "delete-repository",
  "settings",
  "provider",
  "memory",
  "benchmark",
];

/** Command name aliases accepted in help topics. */
const TOPIC_ALIASES = {
  repository: "list-repositories",
  repositories: "list-repositories",
  package: "list-packages",
  packages: "list-packages",
};

export function resolveHelpTopic(value) {
  if (!value) return null;
  if (COMMANDS[value]) return value;
  const alias = TOPIC_ALIASES[value];
  return alias ?? null;
}

/**
 * The help page a command line should show under `--help` / `-h`, resolved
 * without validating the command's arguments: `retrack construct --help` must
 * work even though the prompt is missing, and `retrack delete --help` must
 * work without a target. Returns null for verbs that name no command.
 */
export function resolveCommandHelpKey(positionals) {
  const [verb, noun] = positionals;
  if (!verb) return null;

  if (verb === "list") {
    if (noun === undefined) return "list";
    if (noun === "repositories") return "list-repositories";
    if (noun === "packages") return "list-packages";
    return null;
  }
  if (verb === "delete") {
    if (noun === undefined) return "delete";
    if (noun === "package") return "delete-package";
    if (noun === "repository") return "delete-repository";
    return null;
  }

  const singleNoun = {
    show: ["package", "show-package"],
    append: ["package", "append-package"],
    export: ["package", "export-package"],
    resynthesize: ["package", "resynthesize-package"],
  };
  if (singleNoun[verb]) {
    const [expected, key] = singleNoun[verb];
    return noun === undefined || noun === expected ? key : null;
  }

  const plain = {
    help: "help",
    health: "health",
    status: "status",
    memory: "memory",
    benchmark: "benchmark",
    settings: "settings",
    provider: "provider",
    select: "select",
    index: "index",
    scan: "scan",
    construct: "construct",
  };
  return plain[verb] ?? null;
}

function renderOptionLines(options) {
  const all = [...options, ...GLOBAL_OPTIONS];
  const width = Math.max(...all.map(([flag]) => flag.length));
  return all.map(([flag, text]) => `  ${flag.padEnd(width)}  ${text}`);
}

function renderSection(title, lines) {
  if (lines.length === 0) return [];
  return ["", `${title}:`, ...lines];
}

export function renderMainHelp() {
  const rows = ENTRY_ORDER.map((key) => [COMMANDS[key].usage.replace(/^retrack /, ""), COMMANDS[key].summary]);
  const width = Math.max(...rows.map(([usage]) => usage.length));
  return [
    "RE:Track CLI",
    "",
    "Usage: retrack <command> [arguments] [options]",
    "",
    "Commands:",
    ...rows.map(([usage, summary]) => `  ${usage.padEnd(width)}  ${summary}`),
    "",
    "Global options:",
    ...GLOBAL_OPTIONS.map(([flag, text]) => `  ${flag.padEnd(20)}  ${text}`),
    "",
    "Exit codes:",
    "  0  success",
    "  1  command failed (backend error, missing resource, failed generation)",
    "  2  usage error (unknown command, bad arguments, missing --yes)",
    "",
    'Run "retrack help <command>" for a command\'s arguments, options and examples.',
  ].join("\n");
}

export function renderCommandHelp(key) {
  const command = COMMANDS[key];
  if (!command) return renderMainHelp();
  return [
    command.usage,
    "",
    ...command.description,
    ...renderSection(
      "Arguments",
      command.args.map(([name, text]) => `  ${name.padEnd(18)}  ${text}`)
    ),
    ...renderSection("Options", renderOptionLines(command.options)),
    ...renderSection("Examples", command.examples.map((example) => `  ${example}`)),
  ].join("\n");
}
