import { chromium } from "playwright";
import * as fs from "node:fs";
import * as path from "node:path";

async function main() {
  console.log("=== Connecting to your Chrome via CDP ===");

  // Try to connect to your running Chrome
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  console.log("Connected! Browser version:", await browser.version());

  // Use the default page or create a new one
  const context = browser.contexts()[0];
  const page = context.pages()[0] || await context.newPage();

  const hashtags = [
    "schmuckliebe",
    "modeblogger",
    "fashionbloggerde",
    "ootdgermany",
    "styleblogger_de",
    "beautydeutschland",
    "germanfashionblogger",
    "berlinfashion",
  ];

  const allUsernames = new Set();

  for (const tag of hashtags) {
    const url = `https://www.instagram.com/explore/tags/${tag}/`;
    console.log(`\n>> Searching #${tag}...`);
    try {
      await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForTimeout(2000);

      // Scroll to load more
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(1000);

      const links = await page.evaluate(() => {
        const anchors = document.querySelectorAll("a");
        const results = [];
        const seen = new Set();
        for (const a of anchors) {
          const href = a.href;
          const m = href.match(/https:\/\/www\.instagram\.com\/([a-zA-Z0-9._]+)\/?$/);
          if (m && !m[1].includes("explore") && !m[1].includes("accounts") && !m[1].includes("p/") && !m[1].includes("reel/") && !m[1].includes("stories")) {
            if (!seen.has(m[1])) {
              seen.add(m[1]);
              results.push(m[1]);
            }
          }
        }
        return results;
      });

      let newCount = 0;
      for (const u of links) {
        if (!allUsernames.has(u)) {
          allUsernames.add(u);
          newCount++;
        }
      }
      console.log(`  Found ${links.length} profiles, ${newCount} new`);

      const show = [...allUsernames].slice(-Math.min(5, Math.max(1, newCount)));
      show.forEach(u => console.log(`    instagram.com/${u}/`));

    } catch (e) {
      console.log(`  Error: ${e.message}`);
    }
  }

  console.log(`\n========================================`);
  console.log(`Total unique IG profiles: ${allUsernames.size}`);
  console.log(`========================================`);

  const output = [...allUsernames].map(u => `https://www.instagram.com/${u}/`);
  const outPath = path.join(process.cwd(), "data", "input_ig_cdp.txt");
  fs.writeFileSync(outPath, output.join("\n") + "\n", "utf-8");
  console.log(`Saved ${allUsernames.size} URLs to data/input_ig_cdp.txt`);

  [...allUsernames].slice(0, 30).forEach((u, i) => console.log(`  ${i+1}. instagram.com/${u}/`));

  await browser.close();
}

main().catch(e => { console.error("FAILED:", e.message); process.exit(1); });