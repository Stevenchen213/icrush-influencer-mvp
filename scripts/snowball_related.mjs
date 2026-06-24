import { chromium } from "playwright";
import * as fs from "node:fs";
import * as path from "node:path";

// Known good influencers from the taste profile
const SEEDS = [
  "oksana_vibe.de",
  "clarafelinee",
  "finjamartha",
  "leonie_bartsch",
  "christinexxe",
];

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function extractRelatedAccounts(page, username) {
  console.log(`\n>> @${username}...`);

  try {
    // Go to profile page
    await page.goto(`https://www.instagram.com/${username}/`, {
      waitUntil: "networkidle", timeout: 20000
    });
    await sleep(3000);

    // Get all "following" / follower links and suggested accounts
    const data = await page.evaluate((seed) => {
      const anchors = document.querySelectorAll("a");
      const results = [];
      const seen = new Set();

      for (const a of anchors) {
        const href = a.href;

        // Check for "Suggested" / "Related" sections
        const parentText = (a.closest("div")?.innerText || "").toLowerCase();
        const isSuggested = parentText.includes("suggested") ||
                           parentText.includes("recommended") ||
                           parentText.includes("more from") ||
                           parentText.includes("ähnlich") ||
                           parentText.includes("vorschläge");

        // Check for "following" list links
        const isFollowing = href.includes("/following/") || href.includes("/followers/");

        // Extract profile links
        const m = href.match(/https:\/\/www\.instagram\.com\/([a-zA-Z0-9._]+)\/?$/);
        if (m) {
          const uname = m[1].toLowerCase();
          if (!["explore","accounts","p","reel","stories","direct","popular","about"].includes(uname) &&
              uname !== seed.toLowerCase() && !seen.has(uname)) {
            seen.add(uname);
            results.push({
              username: m[1],
              type: isSuggested ? "suggested" : (isFollowing ? "following" : "unknown"),
              foundIn: parentText.substring(0, 60),
            });
          }
        }
      }
      return results;
    }, username);

    console.log(`  Found ${data.length} profile links`);
    const suggested = data.filter(d => d.type === "suggested");
    const following = data.filter(d => d.type === "following");
    if (suggested.length > 0) console.log(`  Suggested: ${suggested.slice(0, 5).map(d => "@"+d.username).join(", ")}${suggested.length > 5 ? "..." : ""}`);
    if (following.length > 0) console.log(`  Following: ${following.slice(0, 3).map(d => "@"+d.username).join(", ")}${following.length > 3 ? "..." : ""}`);

    // If no suggested/following found, try browsing the explore page which shows recommendations
    if (data.length < 5) {
      console.log(`  Low results - trying explore page...`);
      await page.goto("https://www.instagram.com/explore/", { waitUntil: "networkidle", timeout: 15000 });
      await sleep(2000);

      const exploreData = await page.evaluate((seed) => {
        const anchors = document.querySelectorAll("a");
        const results = [];
        const seen = new Set();
        for (const a of anchors) {
          const m = a.href.match(/https:\/\/www\.instagram\.com\/([a-zA-Z0-9._]+)\/?$/);
          if (m) {
            const uname = m[1].toLowerCase();
            if (!["explore","accounts","p","reel","stories","direct","popular"].includes(uname) && uname !== seed.toLowerCase() && !seen.has(uname)) {
              seen.add(uname);
              results.push(m[1]);
            }
          }
        }
        return results;
      }, username);

      console.log(`  Explore page: ${exploreData.length} profiles`);
      return exploreData.slice(0, 30);
    }

    return data.map(d => d.username).slice(0, 30);
  } catch (e) {
    console.log(`  Error: ${e.message.substring(0, 60)}`);
    return [];
  }
}

async function main() {
  console.log("==========================================");
  console.log("Snowball: Related Accounts from Seed Profiles");
  console.log(`Seeds: ${SEEDS.length} known good influencers`);
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
    Object.defineProperty(navigator, "plugins", { get: () => [1, 2, 3, 4, 5] });
  });

  const page = await context.newPage();
  const allUsers = new Set();

  try {
    for (const seed of SEEDS) {
      const users = await extractRelatedAccounts(page, seed);
      let n = 0;
      for (const u of users) {
        if (!allUsers.has(u.toLowerCase())) {
          allUsers.add(u.toLowerCase());
          n++;
        }
      }
      console.log(`  (${n} new, ${allUsers.size} total)`);
    }

    // Also try from Instagram's search suggestions
    console.log(`\n>> Trying IG search suggestions...`);
    for (const seed of SEEDS.slice(0, 2)) {
      try {
        await page.goto(`https://www.instagram.com/web/search/topsearch/?query=${seed}`, {
          waitUntil: "networkidle", timeout: 10000
        });
        const body = await page.evaluate(() => document.body.innerText.substring(0, 500));
        console.log(`  Search API for ${seed}: ${body.substring(0, 100)}`);
      } catch (e) {
        console.log(`  Search error: ${e.message.substring(0, 40)}`);
      }
    }

  } finally {
    await browser.close();
  }

  console.log(`\n========================================`);
  console.log(`Total unique accounts found: ${allUsers.size}`);
  console.log(`========================================`);

  const output = [...allUsers].map(u => `https://www.instagram.com/${u}/`);
  const outPath = path.join(process.cwd(), "data", "input_snowball_pw.txt");
  fs.writeFileSync(outPath, output.join("\n") + "\n", "utf-8");
  console.log(`Saved to data/input_snowball_pw.txt`);

  [...allUsers].slice(0, 30).forEach((u, i) => console.log(`  ${i+1}. instagram.com/${u}/`));
}

main().catch(e => { console.error("FAILED:", e.message); process.exit(1); });