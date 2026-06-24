import { chromium } from "playwright";

async function main() {
  console.log("Connecting to your Chrome...");
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const context = browser.contexts()[0];
  const page = await context.newPage();  // New tab (keeps IG login)

  console.log("Going to @oksana_vibe.de...");
  await page.goto("https://www.instagram.com/oksana_vibe.de/", { waitUntil: "domcontentloaded", timeout: 15000 });
  await new Promise(r => setTimeout(r, 4000));

  // Screenshot
  await page.screenshot({ path: "C:\\Users\\yaxua\\icrush-influencer-mvp\\data\\profile_view.png", fullPage: false });
  console.log("Screenshot saved!");

  // Find all sections on the page
  const structure = await page.evaluate(() => {
    const results = [];
    // Get all text that looks like section headers
    const allDivs = document.querySelectorAll("div[class]");
    for (const div of allDivs) {
      const text = (div.textContent || "").trim();
      const cls = Array.from(div.classList).join(" ");
      if (text && text.length > 0 && text.length < 60 && !results.some(r => r.text === text)) {
        results.push({ text, class: cls.substring(0, 40) });
      }
    }
    return results.slice(0, 50);
  });
  console.log("\nPage text sections:");
  structure.forEach(s => console.log(`  "${s.text.substring(0, 50)}"`));

  // Extract profile links with their context
  const profiles = await page.evaluate(() => {
    const anchors = document.querySelectorAll("a");
    const results = [];
    const seen = new Set();
    for (const a of anchors) {
      const href = a.href;
      const m = href.match(/https:\/\/www\.instagram\.com\/([a-zA-Z0-9._]+)\/?$/);
      if (m) {
        const uname = m[1].toLowerCase();
        if (!["explore","accounts","p","reel","stories","direct","popular","about","discover","search","notifications","settings","help","legal","privacy","terms","ads","support","blog","press","api","jobs","location","hashtag","top","suggested","following","followers","igtv","guide","go"].includes(uname) && !seen.has(uname)) {
          seen.add(uname);
          // Get surrounding text for context
          const parent = a.closest("div");
          const parentText = parent ? parent.innerText.substring(0, 80) : "";
          const grandparent = a.closest("section") || a.closest("article") || a.closest("main");
          const sectionText = grandparent ? grandparent.querySelector("h1, h2, h3")?.textContent || "" : "";
          results.push({ username: m[1], parentText, sectionText });
        }
      }
    }
    return results;
  });

  console.log(`\nProfile links found: ${profiles.length}`);
  for (const p of profiles.slice(0, 30)) {
    console.log(`  @${p.username.padEnd(25)} | section: "${p.sectionText.substring(0, 30)}" | parent: "${p.parentText.substring(0, 40)}"`);
  }

  await page.close();
  await browser.close();
  console.log("\nDone!");
}

main().catch(e => { console.error("FAILED:", e.message); });