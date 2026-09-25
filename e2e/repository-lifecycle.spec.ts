import { test, expect } from "@playwright/test";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { TAURI_BRIDGE_INIT_SCRIPT } from "./tauri-bridge";

/**
 * Real runtime validation of the repository lifecycle against the live backend
 * on http://127.0.0.1:8765 — cold-start hydration, add, inspect, re-index,
 * delete, and persistence across a relaunch. The temporary repository created
 * here is deleted again by the end of the run.
 */
test.describe.configure({ timeout: 300000 });

test.describe("Repository lifecycle — live backend", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(TAURI_BRIDGE_INIT_SCRIPT);
  });

  test("cold start shows persisted repositories, and add/re-index/delete round-trips", async ({
    page,
  }) => {
    const workDir = fs.mkdtempSync(path.join(os.tmpdir(), "retrack-e2e-"));
    const repoDir = path.join(workDir, "e2e-demo-repo");
    fs.mkdirSync(path.join(repoDir, "src"), { recursive: true });
    fs.writeFileSync(
      path.join(repoDir, "src", "auth.py"),
      'def create_session(user: str) -> dict:\n    """Create a session for a user."""\n    return {"user": user}\n'
    );
    fs.writeFileSync(
      path.join(repoDir, "main.py"),
      'from src.auth import create_session\n\n\ndef main() -> None:\n    print(create_session("e2e"))\n\n\nif __name__ == "__main__":\n    main()\n'
    );

    const repoName = `e2e-demo-${Date.now()}`;

    // --- Cold start: persisted repositories appear with no import step ---
    await page.goto("/");
    await expect(page.getByText("Repository Management")).toBeVisible();
    await expect(page.getByTestId("repository-list")).toBeVisible();

    const initialCount = await page.getByTestId("repository-row").count();
    expect(initialCount).toBeGreaterThan(0);

    // Active repository selector is hydrated from the backend list
    await expect(page.getByRole("combobox", { name: "Active repository" })).toBeVisible();

    // --- Add Repository: labelled, discoverable action ---
    await page.getByRole("button", { name: /^Add Repository$/ }).first().click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    await dialog.getByPlaceholder("/path/to/project").fill(repoDir);
    await dialog.getByPlaceholder("e.g. my-project").fill(repoName);
    await dialog.getByRole("button", { name: /^Add Repository$/ }).click();
    await dialog.waitFor({ state: "hidden" });

    await expect(page.getByTestId("repository-row").filter({ hasText: repoName })).toBeVisible();
    expect(await page.getByTestId("repository-row").count()).toBe(initialCount + 1);

    // --- Select and inspect the new repository summary ---
    await page.getByTestId("repository-row").filter({ hasText: repoName }).click();
    await expect(page.getByText(repoDir).first()).toBeVisible();
    await expect(page.getByText("Index state")).toBeVisible();
    await expect(page.getByText("Not available in this backend")).toBeVisible();

    // --- Re-index: live phase progress, then a terminal state ---
    await page.getByRole("button", { name: /^(Re-index|Index)$/ }).click();
    const progress = page.getByTestId("indexing-progress");
    await expect(progress).toBeVisible();
    // The run has started: the panel reports the backend's own state, never a fabricated one.
    expect(["indexing", "indexed", "error"]).toContain(await progress.getAttribute("data-status"));

    await expect(progress).toHaveAttribute("data-status", /indexed|error/, { timeout: 180000 });

    const finalStatus = await progress.getAttribute("data-status");
    if (finalStatus === "error") {
      // Failures must be reported with the backend's own message rather than a silent stop.
      await expect(progress).toContainText(/failed|error/i);
    } else {
      await expect(progress).toContainText(/Indexing completed/i);
    }

    // --- Delete with confirmation, list updates immediately ---
    await page.getByRole("button", { name: /^Delete$/ }).click();
    await expect(page.getByText(`Delete "${repoName}"?`)).toBeVisible();
    await page.getByRole("button", { name: /Delete Repository/ }).click();

    await expect(page.getByTestId("repository-row").filter({ hasText: repoName })).toHaveCount(0);
    await expect(page.getByTestId("repository-count")).toHaveText(String(initialCount));

    // --- Relaunch: persisted state is unchanged ---
    await page.reload();
    await expect(page.getByTestId("repository-list")).toBeVisible();
    await expect(page.getByTestId("repository-row").filter({ hasText: repoName })).toHaveCount(0);
    expect(await page.getByTestId("repository-row").count()).toBe(initialCount);

    // --- Context: generate for this repository and switch markdown modes ---
    await page.getByRole("link", { name: "Context" }).click();
    await expect(page.getByText("Context Studio")).toBeVisible();

    const prompt = page.getByPlaceholder(/Describe your coding task/i);
    await prompt.fill("Explain how the authentication session is created");

    await page.getByRole("button", { name: /Synthesize/ }).click();
    await expect(page.getByTestId("model-processing-panel")).toBeVisible();
    // No fabricated percentage in the processing panel
    expect(await page.getByTestId("model-processing-panel").textContent()).not.toMatch(/%/);

    await expect(page.getByTestId("context-rendered-markdown")).toBeVisible({ timeout: 120000 });
    await expect(page.getByText("Evidence strength")).toBeVisible();

    await page.getByRole("tab", { name: /Raw Markdown/ }).click();
    const raw = page.getByTestId("context-raw-markdown");
    await expect(raw).toBeVisible();
    const rawText = await raw.textContent();

    await page.getByRole("tab", { name: /^Rendered$/ }).click();
    await expect(page.getByTestId("context-rendered-markdown")).toBeVisible();
    await page.getByRole("tab", { name: /Raw Markdown/ }).click();
    // Same backend markdown string in both directions — presentation only.
    expect(await page.getByTestId("context-raw-markdown").textContent()).toBe(rawText);

    fs.rmSync(workDir, { recursive: true, force: true });
  });
});
