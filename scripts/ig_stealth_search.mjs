import { chromium } from "playwright";
import * as fs from "node:fs";
import * as path from "node:path";

const HASHTAGS = [
  "schmuckliebe",
  "modeblogger",
  "fashionbloggerde",
  "ootdgermany",
  "styleblogger_de",
  "beautydeutschland",
  "germanfashionblogger",
  "berlinfashion",
  "hamburgfashion",
  "schmuck",
  "jewelrygermany",
  "fashiongermany",
  "modetrend",
  "outfitinspiration",
  "munichstyle",
  "fashiondeutschland",
  "beautyblogger",
  "fashionblogger",
  "styleinspo",
  "deutschebloggerin",
];

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function searchHashtag(page, tag) {
  const url = `https://www.instagram.com/explore/tags/${tag}/`;
  console.log(`\n>> #${tag}...`);

  try {
    await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
    await sleep(3000);

    // Scroll to load more
    for (let s = 0; s < 3; s++) {
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await sleep(1500);
    }

    const links = await page.evaluate(() => {
      const anchors = document.querySelectorAll("a");
      const results = [];
      const seen = new Set();
      for (const a of anchors) {
        const m = a.href.match(/https:\/\/www\.instagram\.com\/([a-zA-Z0-9._]+)\/?$/);
        if (m && !["explore","accounts","p","reel","stories","direct","popular"].includes(m[1])) {
          if (!seen.has(m[1])) {
            seen.add(m[1]);
            results.push(m[1]);
          }
        }
      }
      return results;
    });

    console.log(`  Found ${links.length} profiles`);
    return links;
  } catch (e) {
    console.log(`  Error: ${e.message}`);
    return [];
  }
}

async function main() {
  console.log("==========================================");
  console.log("Playwright IG Hashtag Discovery (Stealth)");
  console.log(`Searching ${HASHTAGS.length} hashtags`);
  console.log("==========================================");

  const browser = await chromium.launch({
    headless: true,
    args: [
      "--disable-blink-features=AutomationControlled",
      "--no-sandbox",
      "--disable-web-security",
      "--disable-features=IsolateOrigins,site-per-process",
      "--window-size=1280,800",
      "--lang=de-DE",
    ],
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    locale: "de-DE",
    timezoneId: "Europe/Berlin",
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  });

  await context.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => false });
    Object.defineProperty(navigator, "plugins", { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, "languages", { get: () => ["de-DE", "de", "en"] });
    (window.chrome).runtime = {};
  });

  const page = await context.newPage();
  const all = new Set();

  try {
    for (const tag of HASHTAGS) {
      const links = await searchHashtag(page, tag);
      let n = 0;
      for (const u of links) {
        if (!all.has(u)) { all.add(u); n++; }
      }
      console.log(`  (${n} new, ${all.size} total)`);
      await sleep(1000);
    }
  } finally {
    await browser.close();
  }

  console.log(`\n========================================`);
  console.log(`Total unique IG profiles: ${all.size}`);
  console.log(`========================================`);

  const output = [...all].map(u => `https://www.instagram.com/${u}/`);
  const outPath = path.join(process.cwd(), "data", "input_ig_stealth.txt");
  fs.writeFileSync(outPath, output.join("\n") + "\n", "utf-8");
  console.log(`Saved to: data/input_ig_stealth.txt`);

  [...all].slice(0, 40).forEach((u, i) => console.log(`  ${i+1}. instagram.com/${u}/`));
}

main().catch(e => { console.error("FAILED:", e.message); process.exit(1); });