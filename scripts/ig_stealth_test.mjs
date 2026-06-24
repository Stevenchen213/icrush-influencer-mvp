import { chromium } from "playwright";
import * as fs from "node:fs";
import * as path from "node:path";

async function main() {
  console.log("=== Instagram Stealth Search (headless Chromium) ===");

  const browser = await chromium.launch({
    headless: true,
    args: [
      "--disable-blink-features=AutomationControlled",
      "--no-sandbox",
      "--disable-web-security",
      "--disable-features=IsolateOrigins,site-per-process",
      "--window-size=1280,800",
      "--lang=de-DE",
      '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ],
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    locale: "de-DE",
    timezoneId: "Europe/Berlin",
  });

  // Inject script to hide automation
  await context.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => false });
    // @ts-ignore
    window.chrome = { runtime: {} };
    Object.defineProperty(navigator, "plugins", { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, "languages", { get: () => ["de-DE", "de", "en"] });
  });

  const page = await context.newPage();

  // Try visiting the hashtag page directly first
  const testTag = "schmuckliebe";
  console.log(`\n>> Navigating to #${testTag}...`);

  try {
    await page.goto(`https://www.instagram.com/explore/tags/${testTag}/`, {
      waitUntil: "networkidle",
      timeout: 30000,
    });
    await page.waitForTimeout(3000);

    const pageTitle = await page.title();
    const pageUrl = page.url();
    console.log(`Title: "${pageTitle}"`);
    console.log(`URL: ${pageUrl}`);

    // Check for login wall
    const hasLoginForm = await page.evaluate(() => {
      return document.title.includes("Login") ||
             document.body.innerText.includes("Log in") ||
             document.querySelector('form input[name="username"]') !== null;
    });
    console.log(`Login wall detected: ${hasLoginForm}`);

    // Extract any profile links
    const links = await page.evaluate(() => {
      const anchors = document.querySelectorAll("a");
      const results = [];
      const seen = new Set();
      for (const a of anchors) {
        const m = a.href.match(/https:\/\/www\.instagram\.com\/([a-zA-Z0-9._]+)\/?$/);
        if (m && !["explore","accounts","p","reel","stories","direct"].includes(m[1])) {
          if (!seen.has(m[1])) {
            seen.add(m[1]);
            results.push(m[1]);
          }
        }
      }
      return results;
    });
    console.log(`Profile links found: ${links.length}`);
    links.slice(0, 10).forEach(u => console.log(`  instagram.com/${u}/`));

    // Try to get page content
    const bodyText = await page.evaluate(() => document.body.innerText.substring(0, 500));
    console.log(`\nPage text preview:\n${bodyText}`);

  } catch (e) {
    console.log(`Navigation error: ${e.message}`);
  }

  await browser.close();
}

main().catch(e => { console.error("FAILED:", e.message); process.exit(1); });