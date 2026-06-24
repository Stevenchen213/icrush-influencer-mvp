import { chromium } from "playwright";
import * as fs from "node:fs";
import * as path from "node:path";

const OUTPUT = path.join(process.cwd(), "data", "input_ig_searchapi.txt");

// Search queries that will find German fashion influencers
const SEARCHES = [
  "fashion blogger berlin",
  "mode blogger hamburg",
  "german fashion influencer",
  "mode influencer deutschland",
  "fashion & lifestyle berlin",
  "content creator fashion münchen",
  "beauty blogger deutschland",
  "schmuck influencer",
  "fashion stylist germany",
  "jewelry blogger germany",
  "lifestyle blogger berlin",
  "fashion blogger köln",
  "outfit blogger düsseldorf",
  "modedesignerin deutschland",
];

async function main() {
  console.log("=== IG Search API Discovery (logged in) ===\n");

  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const context = browser.contexts()[0];
  const page = context.pages()[0] || await context.newPage();

  const allUsers = new Set();

  for (const query of SEARCHES) {
    process.stdout.write(`"${query}"... `);
    try {
      // Use IG's search API - returns JSON when logged in
      await page.goto(
        `https://www.instagram.com/web/search/topsearch/?query=${encodeURIComponent(query)}`,
        { waitUntil: "domcontentloaded", timeout: 10000 }
      );
      await new Promise(r => setTimeout(r, 1000));

      // Parse the JSON response
      const data = await page.evaluate(() => {
        const pre = document.querySelector("pre");
        if (pre) {
          try { return JSON.parse(pre.innerText); } catch { return null; }
        }
        const body = document.body.innerText;
        try { return JSON.parse(body); } catch { return null; }
      });

      let n = 0;
      if (data && data.users) {
        for (const entry of data.users) {
          const user = entry.user;
          if (user && user.username) {
            const uname = user.username.toLowerCase();
            if (!["explore","accounts","p","reel","stories","direct","popular","about"].includes(uname) &&
                !allUsers.has(uname)) {
              allUsers.add(uname);
              n++;
            }
          }
        }
        console.log(`${n} new (total: ${allUsers.size})`);
      } else {
        console.log("no users in response");
      }
    } catch (e) {
      console.log(`error: ${e.message.substring(0,40)}`);
    }
  }

  await browser.close();

  console.log(`\n========================================`);
  console.log(`Total unique: ${allUsers.size}`);
  console.log(`========================================`);

  const output = [...allUsers].map(u => `https://www.instagram.com/${u}/`);
  fs.writeFileSync(OUTPUT, output.join("\n") + "\n", "utf-8");
  [...allUsers].slice(0, 40).forEach((u, i) => console.log(`  ${i+1}. instagram.com/${u}/`));
}

main().catch(e => { console.error("FAILED:", e.message); process.exit(1); });