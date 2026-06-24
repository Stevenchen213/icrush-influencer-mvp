/**
 * ICRUSH Snowball Discovery - Playwright-based
 *
 * From seed IG profiles, extracts bio hashtags and searches for similar creators.
 * No Apify quota consumed - runs in your own browser.
 *
 * Usage:
 *   node scripts/snowball.mjs https://www.instagram.com/oksana_vibe.de/
 *   node scripts/snowball.mjs --max-posts 20 --max-results 50 < seed_urls.txt
 */

import { chromium } from "playwright";

const SEED_URLS = process.argv.slice(2).filter(a => !a.startsWith("--"));
const MAX_POSTS = parseInt(process.argv.find(a => a.startsWith("--max-posts="))?.split("=")[1] || "15", 10);
const MAX_RESULTS = parseInt(process.argv.find(a => a.startsWith("--max-results="))?.split("=")[1] || "100", 10);

const GENERIC_TAGS = new Set([
  "love", "instagood", "fashion", "beautiful", "photooftheday",
  "happy", "cute", "tbt", "follow", "like", "style", "me",
  "photography", "art", "fitness", "travel", "food", "music",
  "model", "beauty", "nature", "life", "smile", "fun",
  "summer", "makeup", "hair", "germany", "deutschland",
  "lifestyle", "ootd", "outfit", "jewelry",
]);

function extractHashtags(text) {
  const matches = text.match(/#(\w+)/g) || [];
  return [...new Set(matches.map(t => t.slice(1).toLowerCase()))];
}

async function extractFromProfile(page, url) {
  console.log(`\n>> Navigating to ${url}...`);
  await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
  await page.waitForTimeout(3000);

  // Try to close login popup if it appears
  try {
    const closeBtn = page.locator('div[role="dialog"] button, [aria-label="Close"]').first();
    if (await closeBtn.isVisible({ timeout: 2000 })) {
      await closeBtn.click();
      await page.waitForTimeout(1000);
    }
  } catch {}

  // Extract bio text
  let bio = "";
  try {
    bio = await page.locator("header section span, .x1lliihq .x1plvlek, ._aa_c").first().innerText({ timeout: 3000 });
  } catch {
    try {
      const metaDesc = await page.locator('meta[name="description"]').getAttribute("content");
      if (metaDesc) bio = metaDesc;
    } catch {}
  }

  const bioTags = extractHashtags(bio);
  console.log(`  Bio hashtags: ${bioTags.join(", ") || "(none)"}`);

  // Extract post captions for more hashtags
  const postTags = new Set();
  try {
    const posts = page.locator("article a[href*='/p/'], article a[href*='/reel/']");
    const count = Math.min(await posts.count(), MAX_POSTS);
    console.log(`  Posts found: ${count}`);

    for (let i = 0; i < count; i++) {
      try {
        await posts.nth(i).click();
        await page.waitForTimeout(1000);
        const captionEl = page.locator("article div[role='button'] ~ span, ._a9zr, ._a9zs").first();
        if (await captionEl.isVisible({ timeout: 2000 })) {
          const capText = await captionEl.innerText();
          extractHashtags(capText).forEach(t => postTags.add(t));
        }
        // Close the post
        await page.keyboard.press("Escape");
        await page.waitForTimeout(500);
      } catch {}
    }
  } catch {}

  console.log(`  Post hashtags (${postTags.size}): ${[...postTags].slice(0, 10).join(", ")}`);

  // Combine and rank
  const combined = {};
  for (const t of bioTags) combined[t] = (combined[t] || 0) + 3;
  for (const t of postTags) combined[t] = (combined[t] || 0) + 1;

  const ranked = Object.entries(combined)
    .filter(([t]) => !GENERIC_TAGS.has(t))
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20)
    .map(([t]) => t);

  console.log(`  Top hashtags: ${ranked.slice(0, 10).join(", ")}`);
  return ranked;
}

async function searchIG(page, hashtag) {
  console.log(`\n>> Searching #${hashtag}...`);
  const searchUrl = `https://www.instagram.com/explore/tags/${hashtag}/`;
  await page.goto(searchUrl, { waitUntil: "networkidle", timeout: 30000 });
  await page.waitForTimeout(3000);

  const usernames = new Set();
  try {
    // Get profile links from the tag page
    const links = page.locator("a[href^='/'][href*='/']");
    const count = await links.count();
    for (let i = 0; i < Math.min(count, 50); i++) {
      const href = await links.nth(i).getAttribute("href");
      if (href) {
        const match = href.match(/^\/([\w.]+)\/?$/);
        if (match && !match[1].includes("/")) {
          usernames.add(match[1]);
        }
      }
    }
  } catch {}

  console.log(`  Found ${usernames.size} usernames`);
  return [...usernames];
}

async function main() {
  if (SEED_URLS.length === 0) {
    console.error("Usage: node snowball.mjs <seed_ig_url> [more_urls...]");
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Step 1: Extract hashtags from seed profiles
    console.log("=== Step 1: Extract hashtags from seed profiles ===");
    let allHashtags = [];
    for (const url of SEED_URLS) {
      if (url.includes("instagram.com")) {
        const tags = await extractFromProfile(page, url);
        allHashtags.push(...tags);
      }
    }

    const uniqueTags = [...new Set(allHashtags)].slice(0, 20);
    if (uniqueTags.length === 0) {
      console.log("\nNo hashtags extracted. Try different seed URLs.");
      return;
    }

    // Step 2: Search each hashtag and collect usernames
    console.log(`\n=== Step 2: Search ${uniqueTags.length} hashtags ===`);
    const allUsers = new Set();
    for (const tag of uniqueTags) {
      const users = await searchIG(page, tag);
      users.forEach(u => allUsers.add(u));
    }

    // Remove seed usernames
    const seedUsers = new Set();
    for (const url of SEED_URLS) {
      const m = url.match(/instagram\.com\/([^/?]+)/);
      if (m) seedUsers.add(m[1].toLowerCase());
    }
    const filtered = [...allUsers].filter(u => !seedUsers.has(u.toLowerCase()));

    console.log(`\n=== Results ===`);
    console.log(`Total unique: ${allUsers.size}`);
    console.log(`New (after removing seeds): ${filtered.length}`);
    console.log(`\nTop new creators:`);
    filtered.slice(0, 30).forEach((u, i) => console.log(`  ${i+1}. https://www.instagram.com/${u}/`));

    // Output to file
    const fs = await import("fs");
    const path = await import("path");
    const outputPath = path.join(process.cwd(), "data", "input_snowball_pw.txt");
    fs.writeFileSync(outputPath, filtered.map(u => `https://www.instagram.com/${u}/`).join("\n") + "\n", "utf-8");
    console.log(`\nSaved ${filtered.length} URLs to ${outputPath}`);

  } finally {
    await browser.close();
  }
}

main().catch(console.error);