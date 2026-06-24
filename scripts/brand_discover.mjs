import { chromium } from "playwright";
import * as fs from "node:fs";
import * as path from "node:path";

// Brand hashtags - these attract real German fashion influencers
const BRAND_TAGS = [
  "purelei",           // German jewelry brand
  "bijoubrigitte",     // German jewelry
  "claideschmuck",     // German jewelry
  "nkd",               // NA-KD fashion
  "thomassabo",        // German jewelry
  "liebeskindberlin",  // German jewelry/accessories
  "maje",              // Fashion brand popular in DE
  "sandromaje",        // Fashion
  "mango",             // Fast fashion
  "zara",              // Fast fashion
  "onlyfashion",       // Fashion
  "aboutyou",          // German fashion platform
  "aokina_kleidung",   // German brand
  "shein_de",          // SHEIN DE specific
  "boss",              // Hugo Boss - German brand
  "adidas",            // German brand
  "puma",              // German brand
  "birkenstock",       // German brand
];

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function main() {
  console.log("==========================================");
  console.log("Brand Hashtag Discovery");
  console.log(`Searching ${BRAND_TAGS.length} brand tags`);
  console.log("==========================================");

  const browser = await chromium.launch({
    headless: true,
    args: ["--disable-blink-features=AutomationControlled", "--no-sandbox", "--lang=de-DE"],
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    locale: "de-DE",
    timezoneId: "Europe/Berlin",
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
  });

  await context.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => false });
    Object.defineProperty(navigator, "languages", { get: () => ["de-DE", "de"] });
  });

  const page = await context.newPage();
  const allUsers = new Set();

  try {
    for (const tag of BRAND_TAGS) {
      console.log(`\n>> #${tag}...`);
      try {
        await page.goto(`https://www.instagram.com/explore/tags/${tag}/`, {
          waitUntil: "networkidle", timeout: 15000
        });
        await sleep(2000);

        // Scroll a bit
        for (let s = 0; s < 2; s++) {
          await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
          await sleep(1000);
        }

        const links = await page.evaluate(() => {
          const anchors = document.querySelectorAll("a");
          const results = [];
          const seen = new Set();
          for (const a of anchors) {
            const m = a.href.match(/https:\/\/www\.instagram\.com\/([a-zA-Z0-9._]+)\/?$/);
            if (m && !["explore","accounts","p","reel","stories","direct","popular","about"].includes(m[1])) {
              if (!seen.has(m[1])) { seen.add(m[1]); results.push(m[1]); }
            }
          }
          return results;
        });

        let n = 0;
        for (const u of links) {
          if (!allUsers.has(u.toLowerCase())) { allUsers.add(u.toLowerCase()); n++; }
        }
        console.log(`  ${links.length} profiles, ${n} new (total: ${allUsers.size})`);

      } catch (e) {
        console.log(`  Error: ${e.message.substring(0, 50)}`);
      }
    }
  } finally {
    await browser.close();
  }

  console.log(`\n========================================`);
  console.log(`Total unique profiles: ${allUsers.size}`);
  console.log(`========================================`);

  const output = [...allUsers].map(u => `https://www.instagram.com/${u}/`);
  const outPath = path.join(process.cwd(), "data", "input_brand_tags.txt");
  fs.writeFileSync(outPath, output.join("\n") + "\n", "utf-8");
  console.log(`Saved to data/input_brand_tags.txt`);

  [...allUsers].slice(0, 30).forEach((u, i) => console.log(`  ${i+1}. instagram.com/${u}/`));
}

main().catch(e => { console.error("FAILED:", e.message); process.exit(1); });