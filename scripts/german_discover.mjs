import { chromium } from "playwright";
import * as fs from "node:fs";
import * as path from "node:path";

const TAGS = ["schmuckliebe","modeblogger","ootdgermany","berlinfashion","modetrend","aboutyou","liebeskindberlin","thomassabo"];

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function main() {
  console.log("Targeted German Hashtag Search\n");

  const browser = await chromium.launch({
    headless: true,
    args: ["--disable-blink-features=AutomationControlled","--no-sandbox","--lang=de-DE"],
  });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }, locale: "de-DE", timezoneId: "Europe/Berlin",
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
  });
  await context.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => false });
    Object.defineProperty(navigator, "languages", { get: () => ["de-DE", "de"] });
  });
  const page = await context.newPage();
  const all = new Set();

  for (const tag of TAGS) {
    process.stdout.write(`#${tag}... `);
    try {
      await page.goto(`https://www.instagram.com/explore/tags/${tag}/`, { waitUntil: "networkidle", timeout: 20000 });
      await new Promise(r => setTimeout(r, 2000));
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await new Promise(r => setTimeout(r, 1000));
      const links = await page.evaluate(() => {
        const r = [], s = new Set();
        for (const a of document.querySelectorAll("a")) {
          const m = a.href.match(/https:\/\/www\.instagram\.com\/([a-zA-Z0-9._]+)\/?$/);
          if (m && !["explore","accounts","p","reel","stories","direct","popular","about"].includes(m[1]) && !s.has(m[1])) {
            s.add(m[1]); r.push(m[1]);
          }
        }
        return r;
      });
      let n = 0;
      for (const u of links) { if (!all.has(u.toLowerCase())) { all.add(u.toLowerCase()); n++; } }
      console.log(`${links.length} profiles, ${n} new (total ${all.size})`);
    } catch (e) { console.log(`Error: ${e.message.substring(0,40)}`); }
  }

  await browser.close();
  console.log(`\nTotal: ${all.size} profiles`);
  const out = [...all].map(u => `https://www.instagram.com/${u}/`);
  fs.writeFileSync(path.join(process.cwd(), "data", "input_german_tags.txt"), out.join("\n") + "\n", "utf-8");
  console.log(`${out.length} URLs saved to data/input_german_tags.txt`);
}

main().catch(console.error);