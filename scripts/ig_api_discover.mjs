import { chromium } from "playwright";
import * as path from "node:path";
import * as fs from "node:fs";

const DATA_DIR = "C:\\Users\\yaxua\\icrush-influencer-mvp\\data";
const LOG_PATH = path.join(DATA_DIR, "api_log.txt");
const RESULT_PATH = path.join(DATA_DIR, "input_api_discovered.txt");

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function main() {
  const seed = process.argv[2] || "oksana_vibe.de";
  const lines = [];

  console.log("Connecting to Chrome (CDP 9222)...");
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const ctx = browser.contexts()[0];
  const page = await ctx.newPage();
  page.setDefaultTimeout(15000);

  // Intercept GraphQL responses
  const apiResponses = [];
  const seenUrls = new Set();

  page.on("response", async (response) => {
    const url = response.url();
    if (!url.includes("graphql") && !url.includes("/api/")) return;
    if (seenUrls.has(url)) return;
    seenUrls.add(url);
    
    try {
      const text = await response.text();
      if (text.length > 500 && text.length < 500000) {
        apiResponses.push({ url: url.substring(0, 120), size: text.length });
        
        // Try to parse and extract usernames
        try {
          const json = JSON.parse(text);
          if (json?.data?.user?.edge_related_profiles) {
            apiResponses.push({ type: "edge_related_profiles", count: json.data.user.edge_related_profiles.edges?.length || 0 });
          }
          // Extract all usernames from any response
          const usernames = new Set();
          const str = JSON.stringify(json);
          const matches = str.match(/"username":"([a-zA-Z0-9._-]+)"/g);
          if (matches) {
            matches.forEach(m => {
              try { usernames.add(JSON.parse("{" + m + "}").username); } catch {}
            });
          }
          if (usernames.size > 3) {
            apiResponses.push({ type: "usernames_in_response", usernames: [...usernames].slice(0, 20) });
          }
        } catch {}
      }
    } catch {}
  });

  console.log(`Going to @${seed}...`);
  await page.goto(`https://www.instagram.com/${seed}/`, {
    waitUntil: "networkidle", timeout: 20000
  });
  await sleep(3000);

  // Scroll to trigger lazy loads
  for (let s = 0; s < 5; s++) {
    await page.evaluate(() => window.scrollBy(0, 500));
    await sleep(1000);
  }
  await sleep(2000);

  console.log(`\n=== API Responses (${apiResponses.length}) ===`);
  apiResponses.forEach(r => {
    if (r.url) console.log(`  ${r.size}B: ${r.url}`);
    if (r.type) console.log(`  >> ${r.type}: ${r.count || r.usernames?.length}`);
    if (r.usernames) console.log(`     ${r.usernames.slice(0, 10).join(", ")}`);
  });

  // Look for any profile links in the full page
  const profileLinks = await page.evaluate(() => {
    const links = new Set();
    document.querySelectorAll('a[href^="/"]').forEach(a => {
      const m = a.href.match(/instagram\.com\/([a-zA-Z0-9._-]+)\/?$/);
      if (m && !["explore","accounts","p","reel","stories","direct","popular","about","search","notifications","settings","help","legal","privacy","terms","ads","support","blog","press","api","jobs","location","hashtag","top","suggested","following","followers","igtv","guide","go"].includes(m[1].toLowerCase())) {
        links.add(m[1]);
      }
    });
    // Also check role="link" elements
    document.querySelectorAll('[role="link"]').forEach(a => {
      const href = a.getAttribute("href") || "";
      const m = href.match(/^\/([a-zA-Z0-9._-]+)\/?$/);
      if (m && !["explore","accounts","p","reel","stories","direct","popular","about","search","notifications","settings","help","legal","privacy","terms","ads","support","blog","press","api","jobs","location","hashtag","top","suggested","following","followers","igtv","guide","go"].includes(m[1].toLowerCase())) {
        links.add(m[1]);
      }
    });
    return [...links];
  });

  console.log(`\n=== Profile links from page: ${profileLinks.length} ===`);
  if (profileLinks.length > 0) {
    console.log(profileLinks.slice(0, 30).join("\n"));
    
    // Save for pipeline
    const urls = profileLinks.map(u => `https://www.instagram.com/${u}/`);
    fs.writeFileSync(RESULT_PATH, urls.join("\n") + "\n", "utf-8");
    console.log(`\nSaved ${urls.length} URLs to ${RESULT_PATH}`);
  } else {
    // Try finding profile links via images
    const imgs = await page.evaluate(() => {
      return Array.from(document.querySelectorAll("img[alt]"))
        .filter(i => i.alt && (i.alt.includes("@") || (i.alt.endsWith("的头像") || i.alt.endsWith("'s profile picture") || i.alt.endsWith("profile photo")) && i.width > 30))
        .slice(0, 30)
        .map(i => ({ alt: i.getAttribute("alt")?.substring(0, 80), x: i.x, y: i.y }));
    });
    console.log(`\n=== Profile images: ${imgs.length} ===`);
    imgs.forEach(i => console.log(`  "${i.alt}"`));
    
    // Extract usernames from alt text
    const usernames = imgs.map(i => {
      const m = i.alt.match(/@([a-zA-Z0-9._-]+)/) || i.alt.match(/^([a-zA-Z0-9._-]+)的头像/) || i.alt.match(/^([a-zA-Z0-9._-]+)'s profile/);
      return m ? m[1] : null;
    }).filter(Boolean);
    
    console.log(`\n=== Extracted usernames from alt text ===`);
    console.log(usernames.slice(0, 30).join("\n"));
    
    if (usernames.length > 0) {
      const urls = [...new Set(usernames)].map(u => `https://www.instagram.com/${u}/`);
      fs.writeFileSync(RESULT_PATH, urls.join("\n") + "\n", "utf-8");
      console.log(`\nSaved ${urls.length} URLs to ${RESULT_PATH}`);
    }
  }

  // Save API log
  const log = apiResponses.map(r => JSON.stringify(r)).join("\n");
  fs.writeFileSync(LOG_PATH, log, "utf-8");
  console.log(`\nAPI log saved to ${LOG_PATH}`);

  await page.close();
  await browser.close();
  console.log("\nDone!");
}

main().catch(e => { console.error("FAILED:", e.message, e.stack); });
