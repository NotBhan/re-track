import { test, expect } from "@playwright/test";
import { TAURI_BRIDGE_INIT_SCRIPT } from "./tauri-bridge";

/**
 * Real browser smoke validation of the high-value workflows against the live
 * backend on http://127.0.0.1:8765 (see e2e/tauri-bridge.ts).
 */
test.describe.configure({ timeout: 240000 });

test.describe("Real Browser Smoke Validation — High-Value Workflows", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(TAURI_BRIDGE_INIT_SCRIPT);
  });

  test("1. Application launch renders the shell and hydrates repositories", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("RE:Track").first()).toBeVisible();
    await expect(page.locator("header")).toBeVisible();
    await expect(page.getByText("Repository Management")).toBeVisible();
    await expect(page.getByTestId("repository-row").first()).toBeVisible({ timeout: 15000 });
  });

  test("2. Repository Management lists tracked repositories with a real summary", async ({
    page,
  }) => {
    await page.goto("/repositories");
    await expect(page.getByTestId("repository-list")).toBeVisible();
    expect(await page.getByTestId("repository-row").count()).toBeGreaterThan(0);

    await page.getByTestId("repository-row").first().click();
    await expect(page.getByText("Source files")).toBeVisible();
    await expect(page.getByText("Index state")).toBeVisible();
    await expect(page.getByRole("button", { name: /^Open$/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /^(Re-index|Index)$/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /^Delete$/ })).toBeVisible();
  });

  test("3. Repository switching from the header dropdown", async ({ page }) => {
    await page.goto("/repositories");
    const rows = page.getByTestId("repository-row");
    await expect(rows.first()).toBeVisible({ timeout: 15000 });
    const total = await rows.count();

    if (total > 1) {
      const secondName = await rows.nth(1).locator("span").first().textContent();
      const switcher = page.getByRole("combobox", { name: "Active repository" });
      await switcher.click();
      await page.getByRole("option").nth(1).click();
      await expect(switcher).toContainText((secondName || "").trim());
    }
  });

  test("4. Add Repository modal opens from the labelled action", async ({ page }) => {
    await page.goto("/repositories");
    await page.getByRole("button", { name: /^Add Repository$/ }).first().click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText("Local Directory")).toBeVisible();
    await expect(dialog.getByText("GitHub URL")).toBeVisible();

    await dialog.getByRole("button", { name: /Cancel/ }).click();
    await expect(dialog).toBeHidden();
  });

  test("5. Context Studio synthesizes against the live backend", async ({ page }) => {
    await page.goto("/context");
    await expect(page.getByText("Context Studio")).toBeVisible();

    // Wait until repository hydration completes before generating context.
    await expect(page.getByText(/No repository is active yet/)).toHaveCount(0, { timeout: 20000 });

    await page.getByPlaceholder(/Describe your coding task/i).fill(
      "Explain the context engine entry points"
    );
    await page.getByRole("button", { name: /Synthesize/ }).click();

    // If the processing panel is still on screen it must contain no invented percentage.
    const panel = page.getByTestId("model-processing-panel");
    if (await panel.isVisible().catch(() => false)) {
      expect(await panel.textContent()).not.toMatch(/%/);
    }
    await expect(page.getByTestId("context-rendered-markdown")).toBeVisible({ timeout: 120000 });
    await expect(page.getByText("Evidence & Grounding")).toBeVisible();
    await expect(page.getByText("Evidence strength")).toBeVisible();
  });

  test("6. Context output switches between rendered and raw markdown", async ({ page }) => {
    await page.goto("/context");
    // Wait until repository hydration completes before generating context.
    await expect(page.getByText(/No repository is active yet/)).toHaveCount(0, { timeout: 20000 });

    await page.getByPlaceholder(/Describe your coding task/i).fill("Summarize the repository layout");
    await page.getByRole("button", { name: /Synthesize/ }).click();

    await expect(page.getByTestId("context-rendered-markdown")).toBeVisible({ timeout: 120000 });
    const renderedHeadings = await page
      .getByTestId("context-rendered-markdown")
      .locator("h1, h2")
      .count();
    expect(renderedHeadings).toBeGreaterThan(0);

    await page.getByRole("tab", { name: /Raw Markdown/ }).click();
    const raw = page.getByTestId("context-raw-markdown");
    await expect(raw).toBeVisible();
    expect(await raw.textContent()).toContain("#");
  });

  test("7. Memory hub renders the derived-storage notice", async ({ page }) => {
    await page.goto("/memory");
    await expect(page.getByText("Memory Engine").first()).toBeVisible();
    await expect(page.getByText(/Derived Storage Notice/)).toBeVisible();
  });

  test("8. System settings render provider identity and telemetry", async ({ page }) => {
    await page.goto("/system");
    await expect(page.getByText("System & Settings")).toBeVisible();
    await expect(page.getByText("Runtime Model Identity")).toBeVisible();

    await page.getByRole("tab", { name: /Hardware Telemetry/ }).click();
    await expect(page.getByText("Runtime Health")).toBeVisible();
    await expect(page.getByText("Hardware & Resource Telemetry")).toBeVisible();
  });
});
