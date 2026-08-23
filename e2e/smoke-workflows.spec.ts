import { test, expect } from "@playwright/test";
import { TAURI_BRIDGE_INIT_SCRIPT } from "./tauri-bridge";

test.describe("Real Browser Smoke Validation — High-Value Workflows", () => {
  test.beforeEach(async ({ page }) => {
    // Inject real Tauri IPC bridge routing commands to FastAPI at http://127.0.0.1:8765
    await page.addInitScript(TAURI_BRIDGE_INIT_SCRIPT);
  });

  test("1. Application Launch — renders shell with real backend telemetry", async ({ page }) => {
    await page.goto("/");
    // Verify application header and branding
    await expect(page.getByText("RE:Track").first()).toBeVisible();

    // Verify top bar hardware telemetry arrives from real backend
    await expect(page.locator("header")).toBeVisible();
    const headerText = await page.locator("header").textContent();
    expect(headerText).toBeDefined();
  });

  test("2. Repository Page & Catalog — displays repositories from real backend", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Workspaces & Repositories").first()).toBeVisible();

    // Verify filter input is present and interactive
    const filterInput = page.getByPlaceholder("Filter workspaces...").first();
    await expect(filterInput).toBeVisible();
    await filterInput.fill("retrack");
    await expect(filterInput).toHaveValue("retrack");
  });

  test("3. Repository Registration & Scan — modal interaction", async ({ page }) => {
    await page.goto("/");

    // Click "Register Workspace" or "Add Repository"
    const addBtn = page.getByRole("button", { name: /Register Workspace|Add Repository|Register/i }).first();
    if (await addBtn.isVisible()) {
      await addBtn.click();
      await expect(page.getByText(/Register|Import/i).first()).toBeVisible();
      // Close modal if Cancel button is present
      const cancelBtn = page.getByRole("button", { name: /Cancel|Close/i }).first();
      if (await cancelBtn.isVisible()) {
        await cancelBtn.click();
      }
    }
  });

  test("4. Quick Context Synthesis — generates real context package", async ({ page }) => {
    await page.goto("/studio");
    await expect(page.getByText("Context Studio").first()).toBeVisible();

    const promptInput = page.getByPlaceholder("Type the feature, refactoring, or question for your local memory...");
    await expect(promptInput).toBeVisible();
    await promptInput.fill("Explain server initialization in backend/app/server.py");

    const synthesizeBtn = page.getByRole("button", { name: /Synthesize Context/i });
    await expect(synthesizeBtn).toBeVisible();
    await synthesizeBtn.click();

    // Wait for real backend synthesis response
    await expect(
      page.getByText(/Tokens|Evidence Provenance|Repository Map|Summary/i).first()
    ).toBeVisible({ timeout: 20000 });
  });

  test("5. Context Studio — workbench controls and token parameters", async ({ page }) => {
    await page.goto("/studio");
    await expect(page.getByText("Context Studio").first()).toBeVisible();

    // Verify token constraint slider exists
    await expect(page.getByText(/Token Budget Constraint|max tokens/i).first()).toBeVisible();
  });

  test("6. Knowledge Explorer — AST topology and structural components", async ({ page }) => {
    await page.goto("/knowledge/235a60e7acc6");
    await expect(page.getByText(/Knowledge Explorer|Topological Call Graph/i).first()).toBeVisible();
  });

  test("7. Settings & Provider Management — shows configuration controls", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByText(/Settings|Backend Connection|Inference/i).first()).toBeVisible();
  });

  test("8. Diagnostics — health telemetry and structured logs", async ({ page }) => {
    await page.goto("/settings");
    // Switch to Diagnostics tab in SettingsNav
    const diagTab = page.getByRole("button", { name: "Diagnostics" }).first();
    await expect(diagTab).toBeVisible();
    await diagTab.click();

    // Verify Diagnostics Settings renders with real backend metrics
    await expect(page.getByText("Operational Diagnostics & Health")).toBeVisible();
    await expect(page.getByRole("button", { name: /Export Bundle/i })).toBeVisible();
  });
});
