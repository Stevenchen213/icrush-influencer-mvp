import { chromium } from "playwright";
import * as fs from "node:fs";
import * as path from "node:path";

// Read the 136 filtered candidates
const content = fs.readFileSync(path.join(process.cwd(), "data", "input_ig_best.txt"), "utf-8");
const urls = content.trim().split("\n").filter(l => l);

// Extract usernames
const candidates = urls.map(u => {
  const m = u.match(/instagram\.com\/([^/?]+)/);
  return m ? m[1] : "";
}).filter(Boolean);

console.log(`Scanning ${candidates.length} candidates...\n`);

async function scanProfiles() {
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

  const results = [];

  for (const username of candidates) {
    process.stdout.write(`@${username}... `);
    try {
      await page.goto(`https://www.instagram.com/${username}/`, {
        waitUntil: "domcontentloaded", timeout: 15000
      });
      await page.waitForTimeout(2000);

      const data = await page.evaluate(() => {
        // Meta description has full info
        const meta = document.querySelector('meta[name="description"]');
        const desc = meta ? meta.getAttribute("content") || "" : "";

        // Page title often has name + follower count
        const title = document.title;

        // Bio from page
        const bioEls = document.querySelectorAll("header section span, div._aa_c, span._aaco");
        let bio = "";
        for (const el of bioEls) {
          bio += (el.textContent || "") + " ";
        }

        // Check if profile exists / is available
        const bodyText = document.body.innerText.substring(0, 200);
        const notAvailable = bodyText.includes("not available") || bodyText.includes("nicht verfügbar");
        const postCount = (bodyText.match(/(\d[\d,.]*)\s*Beiträge|(\d[\d,.]*)\s*posts/i) || [])[0] || "";
        const followerCount = (bodyText.match(/(\d[\d,.]*)\s*Follower|(\d[\d,.]*)\s*follower/i) || [])[0] || "";

        return { desc: desc.substring(0, 500), title, bio: bio.trim().substring(0, 300), notAvailable, postCount, followerCount };
      });

      if (data.notAvailable) {
        console.log("not available");
        continue;
      }

      // Score the candidate
      const combined = (data.desc + " " + data.bio + " " + data.title).toLowerCase();
      let score = 0;

      // German cities (major signal)
      const cities = ["berlin","hamburg","münchen","munich","köln","cologne","frankfurt","stuttgart","düsseldorf","dusseldorf","leipzig","dresden","hannover","bonn","münster","mannheim","freiburg","heidelberg","augsburg","karlsruhe","darmstadt","wiesbaden","potsdam","nürnberg","ulm","bremen"];
      for (const c of cities) {
        if (combined.includes(c)) { score += 3; break; }
      }

      // Country signals
      if (combined.includes("germany") || combined.includes("deutschland") || combined.includes("based in")) score += 3;
      // Austrian cities
      if (combined.includes("wien") || combined.includes("vienna") || combined.includes("salzburg") || combined.includes("graz") || combined.includes("linz")) score += 3;

      // Content type signals
      if (combined.includes("fashion") || combined.includes("mode")) score += 2;
      if (combined.includes("beauty") || combined.includes("schönheit")) score += 1;
      if (combined.includes("lifestyle")) score += 1;
      if (combined.includes("jewelry") || combined.includes("schmuck") || combined.includes("accessoires")) score += 2;
      if (combined.includes("content creator") || combined.includes("ugc")) score += 2;
      if (combined.includes("influencer")) score += 1;

      // Business signals (negative)
      if (combined.includes("shop") || combined.includes("store") || combined.includes("brand") || combined.includes("label")) score -= 2;
      // Travel/food/fitness (negative)
      if (combined.includes("travel") || combined.includes("food") || combined.includes("fitness") || combined.includes("gym")) score -= 1;
      // Male (negative)
      if (combined.includes("her") || combined.includes("ihm") || combined.includes("his")) score -= 2;

      // Agency/management (positive)
      if (combined.includes("@") && (combined.includes("management") || combined.includes("agency") || combined.includes("pr"))) score += 1;

      // Follower count
      let followers = 0;
      const fc = combined.match(/(\d+[\d,.]*)\s*follower/i);
      if (fc) followers = parseInt(fc[1].replace(/[,.]/g, ""));
      if (followers > 1000 && followers < 300000) score += 2;

      const summary = `${data.desc.substring(0, 150)}`;
      console.log(`score:${score} | ${summary.replace(/\n/g, " ").substring(0, 100)}`);

      results.push({ username, score, bio: data.bio.substring(0, 200), desc: data.desc.substring(0, 200), followers });

    } catch (e) {
      console.log(`error: ${e.message.substring(0, 50)}`);
    }
  }

  await browser.close();

  // Sort by score descending
  results.sort((a, b) => b.score - a.score);
  return results;
}

const results = await scanProfiles();

console.log("\n" + "=".repeat(60));
console.log("TOP 20 RECOMMENDED INFLUENCERS");
console.log("=".repeat(60));

const top20 = results.slice(0, 20);
top20.forEach((r, i) => {
  console.log(`\n${i+1}. @${r.username} (score: ${r.score})`);
  console.log(`   https://www.instagram.com/${r.username}/`);
  const bio = r.bio || r.desc;
  if (bio) console.log(`   Bio: ${bio.substring(0, 150).replace(/\n/g, " ")}`);
});

// Save to file
const lines = top20.map(r => `https://www.instagram.com/${r.username}/`);
fs.writeFileSync(path.join(process.cwd(), "data", "input_top20.txt"), lines.join("\n") + "\n", "utf-8");
console.log(`\nSaved to data/input_top20.txt`);