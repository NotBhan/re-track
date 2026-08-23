import { test, expect } from "@playwright/test";
import { TAURI_BRIDGE_INIT_SCRIPT } from "./tauri-bridge";

test.describe("Provider Failure & Recovery Real Runtime Smoke Test", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(TAURI_BRIDGE_INIT_SCRIPT);
  });

  test("verifies provider failure degradation and successful retry recovery", async ({ page }) => {
    await page.goto("/studio");
    await expect(page.getByText("Context Studio").first()).toBeVisible();

    const promptInput = page.getByPlaceholder("Type the feature, refactoring, or question for your local memory...");
    await expect(promptInput).toBeVisible();
    await promptInput.fill("Explain FastAPI lifespan handler in backend/app/server.py");

    const synthesizeBtn = page.getByRole("button", { name: /Synthesize Context/i });
    await expect(synthesizeBtn).toBeVisible();

    // Step 1: Normal execution with provider available
    const startTime1 = Date.now();
    await synthesizeBtn.click();
    await expect(
      page.getByText(/Tokens|Evidence Provenance|Repository Map|Summary/i).first()
    ).toBeVisible({ timeout: 25000 });
    const duration1 = Date.now() - startTime1;
    console.log(`[Recovery Test] Initial synthesis successful in ${duration1}ms`);

    // Step 2: Inject provider failure
    await page.evaluate(() => {
      (window as any).__RETRACK_FAULT_INJECTION__.failNextContext = true;
    });

    // Step 3: Trigger context request while provider is failing
    await promptInput.fill("Explain background worker queue");
    await synthesizeBtn.click();

    // Step 4: Verify frontend captures and renders error state
    await expect(
      page.getByText(/504 Gateway Timeout|Simulated LLM provider timeout|Synthesis failed|Error/i).first()
    ).toBeVisible({ timeout: 10000 });
    console.log("[Recovery Test] Error state correctly captured and displayed in UI");

    // Step 5: Provider restored (failNextContext reset to false)
    // Step 6: Retry synthesis and verify successful recovery
    const retryStart = Date.now();
    const retryBtn = page.getByRole("button", { name: /Retry|Synthesize Context/i }).first();
    await retryBtn.click();

    await expect(
      page.getByText(/Tokens|Evidence Provenance|Repository Map|Summary/i).first()
    ).toBeVisible({ timeout: 25000 });
    const recoveryDuration = Date.now() - retryStart;
    console.log(`[Recovery Test] Recovery retry successfully rendered in ${recoveryDuration}ms`);
    expect(recoveryDuration).toBeGreaterThan(0);
  });
});
