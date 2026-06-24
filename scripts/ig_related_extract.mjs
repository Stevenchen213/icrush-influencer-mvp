import { chromium } from "playwright";
import * as fs from "node:fs";
import * as path from "node:path";

async function main() {
  console.log("Connecting to your Chrome...");
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const context = browser.contexts()[0];
  const page = await context.newPage();

  // Known good influencers (from taste profile)
  const SEEDS = [
    "oksana_vibe.de", "emmaleinswelt", "wideawakearthquake",
    "clarafelinee", "finjamartha", "leonie_bartsch"
  ];

  const allUsers = new Set();

  for (const seed of SEEDS) {
    console.log(`\n>> @${seed}...`);
    try {
      await page.goto(`https://www.instagram.com/${seed}/`, { waitUntil: "domcontentloaded", timeout: 15000 });
      await new Promise(r => setTimeout(r, 4000));

      // Find the "Similar accounts" section and extract its elements
      const profiles = await page.evaluate(() => {
        const results = [];

        // Look for divs containing "similar" or "ähnlich" or "类似"
        const allDivs = document.querySelectorAll("div");
        for (const div of allDivs) {
          const text = (div.textContent || "").trim();
          if (/similar|ähnlich|类似|suggest/i.test(text) && text.length < 20) {
            // Found the section header - now get siblings/children
            const parent = div.parentElement;
            if (parent) {
              const links = parent.querySelectorAll("a");
              for (const a of links) {
                const href = a.href;
                const m = href.match(/https:\/\/www\.instagram\.com\/([a-zA-Z0-9._]+)\/?$/);
                if (m) {
                  const uname = m[1];
                  if (!["explore","accounts","p","reel","stories","direct","popular","about"].includes(uname.toLowerCase())) {
                    results.push(uname);
                  }
                }
              }
            }
          }
        }

        // Also look for the specific section by finding the header text
        const headers = ["类似账户", "Ähnlich", "Similar", "Suggested", "More from"];
        for (const h of headers) {
          const xpath = `//span[contains(text(), '${h}')] | //div[contains(text(), '${h}')] | //h2[contains(text(), '${h}')]`;
          const elements = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
          for (let i = 0; i < elements.snapshotLength; i++) {
            const el = elements.snapshotItem(i);
            const parent = el.parentElement;
            if (parent) {
              const links = parent.querySelectorAll("a");
              for (const a of links) {
                const href = a.href;
                const m = href.match(/https:\/\/www\.instagram\.com\/([a-zA-Z0-9._]+)\/?$/);
                if (m && !["explore","accounts","p","reel","stories","direct","popular","about"].includes(m[1].toLowerCase())) {
                  results.push(m[1]);
                }
              }
            }
          }
        }

        return [...new Set(results)];
      });

      // Also try a simpler approach - get all profile links from the page body
      // and filter to only ones near the "similar accounts" section
      const allLinks = await page.evaluate((seedName) => {
        const body = document.body.innerText;
        const lines = body.split("\n");
        const result = [];
        const seen = new Set();

        // Find the "similar" section
        const simIdx = lines.findIndex(l => /类似|ähnlich|similar|suggest/i.test(l));
        if (simIdx >= 0) {
          // Take next 20 lines after the header
          for (let i = simIdx + 1; i < Math.min(simIdx + 30, lines.length); i++) {
            const line = lines[i].trim();
            // IG usernames are usually short and don't have spaces
            if (line && line.length < 40 && !line.includes(" ") && !line.match(/[0-9]{3,}/)) {
              result.push(line);
            }
          }
        }

        return result;
      }, seed);

      profiles.forEach(u => allUsers.add(u.toLowerCase()));
      allLinks.forEach(u => allUsers.add(u.toLowerCase()));

      console.log(`  Found: ${profiles.length} link-based, ${allLinks.length} text-based (total unique: ${allUsers.size})`);
      if (allLinks.length > 0) console.log(`  Sample: ${allLinks.slice(0, 10).join(", ")}`);

    } catch (e) {
      console.log(`  Error: ${e.message.substring(0, 50)}`);
    }
  }

  await page.close();
  await browser.close();

  console.log(`\n========================================`);
  console.log(`Total unique: ${allUsers.size}`);
  console.log(`========================================`);

  const output = [...allUsers].map(u => `https://www.instagram.com/${u}/`);
  const outPath = path.join(process.cwd(), "data", "input_related_accounts.txt");
  fs.writeFileSync(outPath, output.join("\n") + "\n", "utf-8");

  [...allUsers].slice(0, 30).forEach((u, i) => console.log(`  ${i+1}. instagram.com/${u}/`));
}

main().catch(e => { console.error("FAILED:", e.message); });