import { execSync, spawn } from "node:child_process";

const args = process.argv.slice(2);
const cleanIndex = args.indexOf("--clean");

if (cleanIndex !== -1) {
  args.splice(cleanIndex, 1);
  console.log("[RE:Track] Cleaning Rust build artifacts (`cargo clean`)...");
  try {
    execSync("cargo clean --manifest-path src-tauri/Cargo.toml", { stdio: "inherit" });
  } catch (err) {
    console.error("Failed to run cargo clean:", err);
    process.exit(1);
  }
}

// Reset terminal settings on exit so escape codes and raw tty modes do not leak into the shell
function restoreTerminal() {
  try {
    if (process.stdin.isTTY && typeof process.stdin.setRawMode === "function") {
      process.stdin.setRawMode(false);
    }
  } catch (_) {}
  try {
    execSync("stty sane 2>/dev/null || true");
  } catch (_) {}
}

const child = spawn("npx", ["--no-install", "tauri", ...args], {
  stdio: "inherit",
});

const handleTermination = (signal) => {
  if (child && !child.killed) {
    try {
      child.kill(signal);
    } catch (_) {}
  }
  restoreTerminal();
};

process.on("SIGINT", () => handleTermination("SIGINT"));
process.on("SIGTERM", () => handleTermination("SIGTERM"));
process.on("exit", () => {
  restoreTerminal();
});

child.on("exit", (code) => {
  restoreTerminal();
  process.exit(code ?? 0);
});
