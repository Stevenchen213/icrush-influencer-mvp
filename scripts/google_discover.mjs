/**
 * Google search for German fashion/beauty influencers
 * Uses Playwright to search Google, extract IG/TT profile links
 */

import { chromium } from "playwright";
import * as fs from "fs";
import * as path from "path";

const OUTPUT = path.join(process.cwd(), "data", "input_google.txt");

const QUERIES = [
  "german fashion instagram blogger 2025 2026",
  "deutsche modeblogger instagram",
  "german jewelry fashion influencer instagram",
  "beste modebloggerinnen deutschland instagram",
  "german lifestyle blogger instagram",
  "deutsche fashion influencer insta",
  "german female fashion blogger instagram",
  "german jewelry blogger instagram",
  "deutsche schmuck bloggerin instagram",
  "german influencer fashion lifestyle deutschland",
  "german ootd blogger instagram",
  "deutsche content creator fashion instagram",
];

async function searchGoogle(page, query) {
  console.log(`\n>> Searching: "${query}"`);
  const url = `https://www.google.com/search?q=${encodeURIComponent(query)}&num=30`;
  await page.goto(url, { waitUntil: "networkidle", timeout: 20000 });
  await page.waitForTimeout(2000);

  // Extract all links
  const links = await page.evaluate(() => {
    const results = document.querySelectorAll("a");
    return Array.from(results).map(a => a.href).filter(h => h && h.startsWith("http"));
  });

  // Find IG and TT profile links
  const igMatches = links.filter(l => /instagram\.com\/([^/?]+)\/?$/.test(l) && !l.includes("/p/") && !l.includes("/reel/") && !l.includes("/explore/"));
  const ttMatches = links.filter(l => /tiktok\.com\/@([^/?]+)/.test(l));

  console.log(`  Found: ${igMatches.length} IG, ${ttMatches.length} TT profiles`);
  return [...igMatches, ...ttMatches];
}

async function main() {
  console.log("===========================================");
  console.log("Google Discovery: German Fashion Influencers");
  console.log("===========================================");

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const allUrls = new Set();

  try {
    for (const q of QUERIES) {
      try {
        const urls = await searchGoogle(page, q);
        urls.forEach(u => allUrls.add(u));
      } catch (e) {
        console.log(`  Error: ${e.message}`);
      }
    }
  } finally {
    await browser.close();
  }

  console.log(`\n==========================================`);
  console.log(`Total unique IG/TT profile URLs: ${allUrls.size}`);
  console.log(`==========================================`);

  const urls = [...allUrls].slice(0, 200);
  urls.forEach((u, i) => console.log(`  ${i+1}. ${u}`));

  fs.writeFileSync(OUTPUT, urls.join("\n") + "\n", "utf-8");
  console.log(`\nSaved to ${OUTPUT}`);
}

main().catch(console.error);