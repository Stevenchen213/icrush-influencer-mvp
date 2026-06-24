import { chromium } from "playwright";
import * as fs from "node:fs";
import * as path from "node:path";

const OUTPUT = path.join(process.cwd(), "data", "input_ig_loggedin.txt");
const HASHTAGS = ["schmuckliebe","modeblogger","ootdgermany","berlinfashion","modetrend","aboutyou"];
const SEED_USERS = ["oksana_vibe.de", "wideawakearthquake"];

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// Filter function to remove IG system accounts
function isRealUser(u) {
  return !["explore","accounts","p","reel","stories","direct","popular","about","discover","search","notifications","settings","help","legal","privacy","terms","ads","support","blog","press","api","jobs","location","hashtag","top","suggested","following","followers","igtv","guide","go"].includes(u.toLowerCase());
}

async function main() {
  console.log("=== Connecting to YOUR Chrome (Instagram logged in) ===");

  // Connect to your running Chrome
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  console.log("Connected! Version:", await browser.version());

  // Use your existing context (has IG login cookies!)
  const context = browser.contexts()[0];
  const page = context.pages()[0] || await context.newPage();

  const allUsers = new Set();
  const seenHashtags = new Set();

  // 1. Hashtag search (with login, results will be German-localized!)
  console.log(`\n=== Phase 1: Hashtag Search (${HASHTAGS.length} tags) ===`);
  for (const tag of HASHTAGS) {
    process.stdout.write(`\n#${tag}... `);
    try {
      await page.goto(`https://www.instagram.com/explore/tags/${tag}/`, { waitUntil: "networkidle", timeout: 20000 });
      await sleep(3000);

      // Get page title to confirm it loaded properly
      const title = await page.title();
      process.stdout.write(`(${title.substring(0,20)}) `);

      // Scroll to load more
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await sleep(1500);
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await sleep(1500);

      const links = await page.evaluate(() => {
        const anchors = document.querySelectorAll("a");
        const r = [], s = new Set();
        for (const a of anchors) {
          const m = a.href.match(/https:\/\/www\.instagram\.com\/([a-zA-Z0-9._]+)\/?$/);
          if (m && !s.has(m[1])) { s.add(m[1]); r.push(m[1]); }
        }
        return r;
      });

      let n = 0;
      for (const u of links) {
        if (isRealUser(u) && !allUsers.has(u.toLowerCase())) {
          allUsers.add(u.toLowerCase()); n++;
        }
      }
      console.log(`${links.length} links, ${n} new (total: ${allUsers.size})`);

    } catch (e) { console.log(`Error: ${e.message.substring(0,50)}`); }
  }

  // 2. Related accounts from seed profiles (NEEDS LOGIN!)
  console.log(`\n=== Phase 2: Related Accounts (needs login) ===`);
  for (const seed of SEED_USERS) {
    process.stdout.write(`\n@${seed}... `);
    try {
      await page.goto(`https://www.instagram.com/${seed}/`, { waitUntil: "networkidle", timeout: 20000 });
      await sleep(3000);

      // Look for "More from" / "Suggested" sections
      const data = await page.evaluate((seedName) => {
        const anchors = document.querySelectorAll("a");
        const results = [];
        const seen = new Set();

        for (const a of anchors) {
          const href = a.href;
          const parentDiv = a.closest("div");
          const parentText = (parentDiv?.innerText || "").toLowerCase();

          // Check if this link is in a "suggested" or "more from" section
          const isSuggested = parentText.includes("suggest") ||
                              parentText.includes("more from") ||
                              parentText.includes("ähnlich") ||
                              parentText.includes("vorschlag") ||
                              parentText.includes("you might like") ||
                              parentText.includes("dir gefällt");

          const m = href.match(/https:\/\/www\.instagram\.com\/([a-zA-Z0-9._]+)\/?$/);
          if (m) {
            const uname = m[1].toLowerCase();
            if (!seen.has(uname) && uname !== seedName.toLowerCase()) {
              seen.add(uname);
              results.push({ username: m[1], suggested: isSuggested });
            }
          }
        }

        // Also check for "following" links
        const following = document.querySelectorAll('a[href*="/following/"]');
        console.log(`Following links: ${following.length}`);

        return results;
      }, seed);

      const suggested = data.filter(d => d.suggested).map(d => d.username);
      const other = data.filter(d => !d.suggested).map(d => d.username);

      let n = 0;
      for (const d of data) {
        if (!allUsers.has(d.username.toLowerCase())) {
          allUsers.add(d.username.toLowerCase()); n++;
        }
      }
      console.log(`${data.length} profiles${suggested.length ? ` (${suggested.length} suggested)` : ""}, ${n} new`);

      if (suggested.length > 0) console.log(`  Suggested: ${suggested.slice(0,10).join(", ")}`);

    } catch (e) { console.log(`Error: ${e.message.substring(0,50)}`); }
  }

  // 3. Try the IG search box (only works when logged in)
  console.log(`\n=== Phase 3: IG Search API ===`);
  for (const seed of SEED_USERS.slice(0, 1)) {
    try {
      await page.goto(`https://www.instagram.com/web/search/topsearch/?query=${seed}`, { waitUntil: "domcontentloaded", timeout: 10000 });
      const text = await page.evaluate(() => document.body.innerText.substring(0, 300));
      console.log(`  Search result: ${text.substring(0, 100)}`);
    } catch (e) { console.log(`  Error: ${e.message.substring(0, 40)}`); }
  }

  await browser.close();

  console.log(`\n========================================`);
  console.log(`Total unique: ${allUsers.size}`);
  console.log(`========================================`);

  const output = [...allUsers].map(u => `https://www.instagram.com/${u}/`);
  fs.writeFileSync(OUTPUT, output.join("\n") + "\n", "utf-8");
  console.log(`Saved to ${OUTPUT}`);
  [...allUsers].slice(0, 40).forEach((u, i) => console.log(`  ${i+1}. instagram.com/${u}/`));
}

main().catch(e => { console.error("FAILED:", e.message); process.exit(1); });