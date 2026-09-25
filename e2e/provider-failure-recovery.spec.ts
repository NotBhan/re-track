import { test, expect } from "@playwright/test";
import { TAURI_BRIDGE_INIT_SCRIPT } from "./tauri-bridge";

test.describe.configure({ timeout: 240000 });

test.describe("Provider Failure & Recovery Real Runtime Smoke Test", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(TAURI_BRIDGE_INIT_SCRIPT);
  });

  test("verifies provider failure degradation and successful retry recovery", async ({ page }) => {
    await page.goto("/context");
    await expect(page.getByText("Context Studio")).toBeVisible();

    const promptInput = page.getByPlaceholder(/Describe your coding task/i);
    await expect(promptInput).toBeVisible();
    // Wait until repository hydration completes before generating context.
    await expect(page.getByText(/No repository is active yet/)).toHaveCount(0, { timeout: 20000 });

    await promptInput.fill("Explain the context engine entry points");

    const synthesizeBtn = page.getByRole("button", { name: /Synthesize/ });
    await expect(synthesizeBtn).toBeVisible();

    // Step 1: Normal execution with the provider available
    const startTime1 = Date.now();
    await synthesizeBtn.click();
    await expect(page.getByTestId("context-rendered-markdown")).toBeVisible({ timeout: 120000 });
    console.log(`[Recovery Test] Initial synthesis successful in ${Date.now() - startTime1}ms`);

    // Step 2: Inject a provider failure
    await page.evaluate(() => {
      (window as any).__RETRACK_FAULT_INJECTION__.failNextContext = true;
    });

    // Step 3: Trigger another request while the provider is failing
    await promptInput.fill("Explain background worker queue");
    await synthesizeBtn.click();

    // Step 4: The failure is captured and rendered instead of silently stalling
    await expect(
      page.getByText(/504 Gateway Timeout|Simulated LLM provider timeout|Synthesis failed/i).first()
    ).toBeVisible({ timeout: 30000 });
    console.log("[Recovery Test] Error state correctly captured and displayed in UI");

    // Step 5/6: The fault is one-shot, so retrying recovers
    const retryStart = Date.now();
    await synthesizeBtn.click();

    await expect(page.getByTestId("context-rendered-markdown")).toBeVisible({ timeout: 120000 });
    console.log(
      `[Recovery Test] Recovery retry successfully rendered in ${Date.now() - retryStart}ms`
    );
  });
});
