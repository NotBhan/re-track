import { test, expect } from "@playwright/test";
import { TAURI_BRIDGE_INIT_SCRIPT } from "./tauri-bridge";

/**
 * UI-scale regression: the scaled layout must stay exactly viewport-sized at
 * every supported step (80–150%), with dialogs and menus inside the window.
 */
const SCALES = ["80", "90", "100", "110", "125", "140", "150"];

test.describe.configure({ timeout: 300_000 });

test("repository management stays viewport-exact at every supported scale", async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 900 });
  await page.addInitScript(TAURI_BRIDGE_INIT_SCRIPT);

  for (const scale of SCALES) {
    await page.addInitScript(`localStorage.setItem("retrack:ui-scale", "${scale}");`);
    await page.goto("/repositories");
    await expect(page.getByTestId("repository-row").first()).toBeVisible({ timeout: 30000 });

    const metrics = await page.evaluate(() => {
      const de = document.documentElement as any;
      const rect = de.getBoundingClientRect();
      return {
        rectW: Math.round(rect.width),
        rectH: Math.round(rect.height),
        innerW: window.innerWidth,
        innerH: window.innerHeight,
      };
    });

    // No clipping and no dead space: the scaled root fills the window exactly.
    expect(Math.abs(metrics.rectW - metrics.innerW), `width at ${scale}%`).toBeLessThanOrEqual(3);
    expect(Math.abs(metrics.rectH - metrics.innerH), `height at ${scale}%`).toBeLessThanOrEqual(3);
  }
});

test("dialogs, dropdowns and context output stay inside the window at 150%", async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 900 });
  await page.addInitScript(TAURI_BRIDGE_INIT_SCRIPT);
  await page.addInitScript(`localStorage.setItem("retrack:ui-scale", "150");`);

  await page.goto("/repositories");
  await expect(page.getByTestId("repository-row").first()).toBeVisible({ timeout: 30000 });

  // Dialog geometry stays inside the window
  await page.getByRole("button", { name: /^Add Repository$/ }).first().click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  const dialogBox = (await dialog.boundingBox())!;
  expect(dialogBox.x).toBeGreaterThanOrEqual(0);
  expect(dialogBox.x + dialogBox.width).toBeLessThanOrEqual(1601);
  await dialog.getByRole("button", { name: /Cancel/ }).click();

  // Dropdown menu stays inside the window
  await page.getByRole("combobox", { name: "Active repository" }).click();
  const listbox = page.getByRole("listbox", { name: "Active repository" });
  await expect(listbox).toBeVisible();
  const listBox = (await listbox.boundingBox())!;
  expect(listBox.x).toBeGreaterThanOrEqual(0);
  expect(listBox.x + listBox.width).toBeLessThanOrEqual(1601);
  await page.keyboard.press("Escape");

  // Context output remains usable and switchable at the largest scale
  await page.getByRole("link", { name: "Context" }).click();
  await expect(page.getByText(/No repository is active yet/)).toHaveCount(0, { timeout: 20000 });
  await page
    .getByPlaceholder(/Describe your coding task/i)
    .fill("Explain authentication session creation");
  await page.getByRole("button", { name: /Synthesize/ }).click();
  await expect(page.getByTestId("context-rendered-markdown")).toBeVisible({ timeout: 120000 });

  await page.getByRole("tab", { name: /Raw Markdown/ }).click();
  await expect(page.getByTestId("context-raw-markdown")).toBeVisible();
});
