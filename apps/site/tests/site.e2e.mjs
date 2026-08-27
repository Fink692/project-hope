import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
const base = process.env.HOPE_SITE_URL || "http://localhost:5180";
const output = path.resolve("artifacts");
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: process.env.E2E_BROWSER_CHANNEL || (process.platform === "win32" ? "chrome" : undefined), headless: true });
const errors = [];
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
page.on("pageerror", (error) => errors.push(error.message));
async function checkPage(route) {
  const response = await page.goto(base + route, { waitUntil: "networkidle" });
  assert.equal(response.status(), 200, route);
  assert.equal(await page.locator("h1").count(), 1);
  assert.equal(await page.locator('a[href*="github"]').count(), 0);
  assert.equal(await page.locator("[data-nextjs-dialog]").count(), 0);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, route + " must not overflow horizontally");
}
try {
  await checkPage("/");
  await page.screenshot({ path: path.join(output, "desktop-hero.png") });
  await page.getByRole("tab", { name: /Bring your contacts/ }).focus();
  await page.keyboard.press("ArrowRight");
  assert.equal(await page.getByRole("tab", { name: /Tidy up duplicates/ }).getAttribute("aria-selected"), "true");
  assert.match(await page.getByRole("tabpanel").textContent(), /duplicate review/);
  await page.getByRole("button", { name: "Does the AI work immediately?" }).click();
  assert.equal(await page.getByRole("button", { name: "Does the AI work immediately?" }).getAttribute("aria-expanded"), "true");
  await page.getByRole("button", { name: "Pause motion", exact: true }).click();
  assert.equal(await page.locator("html").getAttribute("data-motion"), "paused");
  assert.equal(await page.evaluate(() => document.getAnimations().filter((animation) => animation.playState === "running").length), 0);
  await page.reload({ waitUntil: "networkidle" });
  assert.equal(await page.locator("html").getAttribute("data-motion"), "paused", "motion preference persists");
  await page.getByRole("button", { name: "Motion paused", exact: true }).click();
  await page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name: "A little help" }).click();
  await page.waitForURL("**/guide");
  await page.getByRole("link", { name: "Back to downloads" }).click();
  await page.waitForURL("**/#download");
  await page.locator("#download .download-heading[data-visible=true]").waitFor();
  await page.waitForFunction(() => getComputedStyle(document.querySelector("#download .download-heading")).opacity === "1");
  await page.getByRole("button", { name: "Pause motion", exact: true }).click();
  await page.screenshot({ path: path.join(output, "desktop-downloads.png") });
  for (const route of ["/guide", "/privacy", "/release-notes"]) await checkPage(route);
  const missing = await page.goto(base + "/page-that-does-not-exist");
  assert.equal(missing.status(), 404);
  for (const width of [320, 390, 768, 1024]) {
    await page.setViewportSize({ width, height: 900 });
    await checkPage("/");
    if (width < 800) {
      await page.getByRole("button", { name: "Open navigation" }).click();
      assert.equal(await page.getByRole("button", { name: "Close navigation" }).getAttribute("aria-expanded"), "true");
      await page.keyboard.press("Escape");
      assert.equal(await page.getByRole("button", { name: "Open navigation" }).getAttribute("aria-expanded"), "false");
      assert.equal(await page.getByRole("button", { name: "Open navigation" }).evaluate((element) => element === document.activeElement), true);
      await page.getByRole("button", { name: "Open navigation" }).click();
      await page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name: "A little help" }).click();
      await page.waitForURL("**/guide");
      assert.equal(await page.getByRole("button", { name: "Open navigation" }).getAttribute("aria-expanded"), "false");
    }
    if (width === 390) {
      await checkPage("/");
      await page.screenshot({ path: path.join(output, "mobile-hero.png") });
      await page.locator("#download").scrollIntoViewIfNeeded();
      await page.screenshot({ path: path.join(output, "mobile-downloads.png") });
    }
  }
  const reduced = await browser.newContext({ reducedMotion: "reduce", viewport: { width: 390, height: 844 } });
  const reducedPage = await reduced.newPage();
  await reducedPage.goto(base, { waitUntil: "networkidle" });
  await reducedPage.locator('html[data-motion="paused"]').waitFor();
  assert.equal(await reducedPage.evaluate(() => document.getAnimations().filter((animation) => animation.playState === "running").length), 0);
  assert.equal(await reducedPage.locator("#inside").evaluate((element) => getComputedStyle(element).opacity), "1");
  await reduced.close();
  const noScript = await browser.newContext({ javaScriptEnabled: false });
  const plain = await noScript.newPage();
  await plain.goto(base);
  assert.match(await plain.locator("h1").textContent(), /Less admin/);
  assert.equal(await plain.locator("#inside [data-reveal]").first().evaluate((element) => getComputedStyle(element).opacity), "1");
  await noScript.close();
  assert.deepEqual(errors, []);
  console.log("PASS: desktop, 320/390/768/1024px layouts, keyboard tabs, accordion, persistent motion pause, route-return reveals, reduced motion, no-JS content, on-site guides, 404, and no repository links or browser errors.");
} finally { await browser.close(); }
