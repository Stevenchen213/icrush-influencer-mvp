import { chromium } from "playwright";

async function main() {
  const url = process.argv[2] || "https://www.instagram.com/oksana_vibe.de/";
  console.log(`Connecting to Chrome, going to ${url}...`);
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const context = browser.contexts()[0];
  const page = await context.newPage();

  await page.goto(url, { waitUntil: "networkidle", timeout: 20000 });
  await new Promise(r => setTimeout(r, 3000));

  // Find and click the "类似账户" button
  const similarClicked = await page.evaluate(() => {
    const allDivs = document.querySelectorAll('div');
    for (const div of allDivs) {
      if ((div.textContent || "").trim() === "类似账户") {
        div.click();
        return true;
      }
    }
    return false;
  });
  console.log(`类似账户 button clicked: ${similarClicked}`);
  await new Promise(r => setTimeout(r, 2000));

  // Screenshot after clicking
  await page.screenshot({ path: "C:\\Users\\yaxua\\icrush-influencer-mvp\\data\\similar_accounts.png", fullPage: false });
  console.log("Screenshot saved to similar_accounts.png!");

  // Now dump all visible text and look for account-like content
  const popupInfo = await page.evaluate(() => {
    const results = {};
    
    // Check what's visible near the "类似账户" area
    const allDivs = document.querySelectorAll('div[role="dialog"], div[role="menu"], div[class*="popup"], div[class*="modal"]');
    results.dialogs = [];
    for (const d of allDivs) {
      results.dialogs.push({
        class: Array.from(d.classList).join(" ").substring(0, 80),
        text: (d.textContent || "").trim().substring(0, 200),
        html: d.outerHTML.substring(0, 500)
      });
    }

    // Search for Instagram profile links anywhere on the page
    const allLinks = document.querySelectorAll('a[href*="instagram.com/"]');
    const profileLinks = [];
    const seen = new Set();
    for (const a of allLinks) {
      const m = a.href.match(/instagram\.com\/([a-zA-Z0-9._]+)\/?$/);
      if (m && !["explore","accounts","p","reel","stories","direct","popular","about","discover","search","notifications","settings","help","legal","privacy","terms","ads","support","blog","press","api","jobs","location","hashtag","top","suggested","following","followers","igtv","guide","go"].includes(m[1]) && !seen.has(m[1])) {
        seen.add(m[1]);
        const img = a.querySelector('img');
        profileLinks.push({ username: m[1], hasImg: !!img, alt: img ? (img.alt || "").substring(0, 60) : "" });
      }
    }
    results.profileLinks = profileLinks;

    // Get all text nodes that look like Instagram usernames
    const usernamePattern = /^@?[a-zA-Z][a-zA-Z0-9._]{2,29}$/;
    const allTexts = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    let node;
    while (node = walker.nextNode()) {
      const t = node.textContent.trim();
      if (t && t.length > 0 && t.length < 40 && !t.includes(' ') && usernamePattern.test(t.replace('@', ''))) {
        allTexts.push(t);
      }
    }
    const unique = [...new Set(allTexts)];
    results.usernameTexts = unique.slice(0, 30);

    // Get all visible text
    const visibleTexts = [];
    const allElements = document.querySelectorAll('div, span, a');
    for (const el of allElements) {
      const t = (el.textContent || "").trim();
      if (t && t.length > 0 && t.length < 60) {
        visibleTexts.push(t);
      }
    }
    const uniqueTexts = [...new Set(visibleTexts)];
    results.visibleTexts = uniqueTexts.slice(0, 50);

    return results;
  });

  console.log(`\n=== Dialogs/Popups: ${popupInfo.dialogs.length}`);
  popupInfo.dialogs.forEach((d, i) => {
    console.log(`\n[${i}] class: ${d.class}`);
    console.log(`    text: ${d.text.substring(0, 200)}`);
    console.log(`    html: ${d.html.substring(0, 400)}`);
  });

  console.log(`\n=== Profile links found: ${popupInfo.profileLinks.length}`);
  popupInfo.profileLinks.forEach(p => console.log(`  @${p.username} hasImg=${p.hasImg} alt="${p.alt}"`));

  console.log(`\n=== Username-like text: ${popupInfo.usernameTexts.length}`);
  popupInfo.usernameTexts.forEach(t => console.log(`  ${t}`));

  await page.close();
  await browser.close();
  console.log("\nDone!");
}

main().catch(e => { console.error("FAILED:", e.message); });
