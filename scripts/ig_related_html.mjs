import { chromium } from "playwright";
import * as fs from "node:fs";
import * as path from "node:path";

async function main() {
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const context = browser.contexts()[0];
  const page = await context.newPage();

  await page.goto("https://www.instagram.com/oksana_vibe.de/", { waitUntil: "domcontentloaded", timeout: 15000 });
  await new Promise(r => setTimeout(r, 4000));

  // 1. Get body text lines and find the "类似账户" section
  const bodyText = await page.evaluate(() => document.body.innerText);
  const lines = bodyText.split("\n");

  console.log("=== Full body text around '类似账户' ===");
  const idx = lines.findIndex(l => l.includes("类似账户"));
  if (idx >= 0) {
    for (let i = Math.max(0, idx - 2); i < Math.min(lines.length, idx + 20); i++) {
      console.log(`[${i - idx}] "${lines[i]}"`);
    }
  }

  // 2. Extract ALL text between "类似账户" and the next section header
  const relatedText = lines.slice(idx + 1).filter(l => l.trim());
  const SECTION_HEADERS = ["帖子", "Reels", "标记", "posts", "videos", "tagged", "beiträge", "reels", "markiert"];
  const endIdx = relatedText.findIndex(l => SECTION_HEADERS.some(h => l.includes(h)));
  const accounts = endIdx > 0 ? relatedText.slice(0, endIdx) : relatedText.slice(0, 20);

  console.log("\n=== Extracted related accounts ===");
  accounts.forEach(a => console.log(`  "${a}"`));

  // 3. Also save the raw HTML around that section for analysis
  const htmlSnippet = await page.evaluate(() => {
    const idx2 = document.body.innerText.indexOf("类似账户");
    if (idx2 < 0) return "";
    // Walk the DOM around that text
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    let node;
    while (node = walker.nextNode()) {
      if (node.textContent.includes("类似账户")) {
        const parent = node.parentElement;
        if (parent) return parent.outerHTML.substring(0, 3000);
      }
    }
    return "";
  });
  console.log("\n=== HTML around similar accounts ===");
  console.log(htmlSnippet.substring(0, 2000));

  await page.close();
  await browser.close();
}

main().catch(console.error);