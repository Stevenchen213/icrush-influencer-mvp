/** 
 * Use Python httpx to directly search Google/Bing
 * No Playwright, no Apify, no Wednesday quota
 */

import { execSync } from "child_process";
import * as fs from "fs";
import * as path from "path";

const OUTPUT = path.join(process.cwd(), "data", "input_httpx.txt");

// Queries in both English and German to maximize results
const QUERIES = [
  "site:instagram.com \"modeblogger\" deutschland",
  "site:instagram.com \"fashion\" \"germany\" blogger",
  "site:instagram.com \"content creator\" \"hamburg\"",
  "site:instagram.com \"lifestyle\" \"berlin\" blogger",
  "site:instagram.com \"schmuck\" \"fashion\" influencer",
  "site:instagram.com \"jewelry\" \"germany\" influencer",
  "site:instagram.com beauty fashion hamburg münchen berlin",
  "site:instagram.com ootd german blogger fashion",
];

const PY = "C:\\Users\\yaxua\\AppData\\Local\\Programs\\Python\\Python312\\python.exe";

// Use Bing search which is less restrictive
async function bingSearch(query) {
  try {
    const pyCode = `
import httpx, sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
url = 'https://www.bing.com/search?q=${encodeURIComponent(query)}&count=30'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0'}
r = httpx.get(url, headers=headers, follow_redirects=True, timeout=10)
links = re.findall(r'https?://[^\\s"\']+(?:instagram\\.com|tiktok\\.com)[^\\s"\']*', r.text)
for l in links[:30]:
    print(l)
`;
    const out = execSync(`"${PY}" -c "${pyCode.replace(/"/g, '\\"')}"`, { encoding: "utf-8", timeout: 15000 });
    return out.trim().split("\n").filter(l => l.includes("instagram.com") || l.includes("tiktok.com"));
  } catch {
    return [];
  }
}

async function main() {
  console.log("======================================");
  console.log("HTTPX Discovery: German Influencers");
  console.log("======================================");

  const all = new Set();

  for (const q of QUERIES) {
    process.stdout.write(`\n>> ${q.slice(0, 50)}... `);
    try {
      const links = await bingSearch(q);
      links.forEach(l => {
        const m = l.match(/instagram\.com\/([^/?]+)/);
        if (m && !m[1].includes("/")) all.add(`https://www.instagram.com/${m[1]}/`);
        const m2 = l.match(/tiktok\.com\/@([^/?]+)/);
        if (m2) all.add(`https://www.tiktok.com/@${m2[1]}/`);
      });
      console.log(`${links.length} links`);
    } catch (e) {
      console.log(`error: ${e.message}`);
    }
  }

  console.log(`\n\nTotal unique IG/TT URLs: ${all.size}`);
  [...all].slice(0, 50).forEach((u, i) => console.log(`  ${i+1}. ${u}`));

  fs.writeFileSync(OUTPUT, [...all].join("\n") + "\n", "utf-8");
  console.log(`\nSaved to ${OUTPUT}`);
}

main().catch(console.error);