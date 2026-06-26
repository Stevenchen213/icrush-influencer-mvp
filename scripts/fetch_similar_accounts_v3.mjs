/**
 * ICRUSH Similar Accounts Extractor v3
 *
 * Three-step method to extract IG's "Similar Accounts" recommendations:
 *   1. Navigate to seed profile
 *   2. Click "类似账户" / "Similar accounts" button
 *   3. Click "查看全部" / "See all" → full list
 *   4. Scroll with human-like jitter → extract profile links
 *
 * Prerequisites:
 *   - Chrome running with --remote-debugging-port=9222
 *   - Logged into Instagram in that Chrome
 *
 * Usage:
 *   node scripts/fetch_similar_accounts_v3.mjs seed1 [seed2 ...]
 *   node scripts/fetch_similar_accounts_v3.mjs --max-seeds 5 jxlia.albrecht ...
 *   node scripts/fetch_similar_accounts_v3.mjs --fast jxlia.albrecht   (skip safety delays)
 */

import { chromium } from "playwright";
import * as fs from "node:fs";
import * as path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

// Resolve project root relative to this script (works on any machine)
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = process.env.ICRUSH_ROOT || path.resolve(__dirname, "..");
const DATA_DIR = path.join(PROJECT_ROOT, "data");
const SESSION_LOG = path.join(DATA_DIR, "session_log.json");

// ============================================================
// Safety defaults — tuned for 7-8 sessions/day, ~5 seeds each
// ============================================================

const SAFE = {
  seedDelayMin: 30_000,   // 30s between seeds
  seedDelayMax: 90_000,   // 90s max
  scrollCount: 50,        // scroll passes
  scrollAmountBase: 600,  // base px per scroll
  scrollAmountJitter: 400,// random jitter ±400px
  scrollDelayBase: 250,   // base delay between scrolls (ms)
  scrollDelayJitter: 200, // random jitter ±200ms
  clickDelayBase: 1500,   // wait after click before next action
  clickDelayJitter: 1500,
  pageLoadDelay: 3000,
  pageLoadJitter: 2000,
  maxSeedsPerSession: 5,  // ~400 candidates, pipeline filters to ~50-80
};

const FAST = {
  seedDelayMin: 0,
  seedDelayMax: 0,
  scrollCount: 50,
  scrollAmountBase: 1000,
  scrollAmountJitter: 0,
  scrollDelayBase: 300,
  scrollDelayJitter: 0,
  clickDelayBase: 2000,
  clickDelayJitter: 0,
  pageLoadDelay: 3000,
  pageLoadJitter: 0,
  maxSeedsPerSession: 999,
};

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

function rand(min, max) {
  return Math.floor(min + Math.random() * (max - min));
}

function jitter(base, jitterRange) {
  return rand(base, base + jitterRange);
}

// ============================================================
// Session tracking
// ============================================================

function loadSessionLog() {
  try {
    if (fs.existsSync(SESSION_LOG)) {
      return JSON.parse(fs.readFileSync(SESSION_LOG, "utf-8"));
    }
  } catch {}
  return { sessions: [] };
}

function logSession(seedCount, accountCount) {
  const log = loadSessionLog();
  const today = new Date().toISOString().split("T")[0];

  log.sessions.push({
    date: today,
    time: new Date().toISOString(),
    seeds: seedCount,
    accounts: accountCount,
  });

  // Keep only last 30 days
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - 30);
  log.sessions = log.sessions.filter(s => new Date(s.time) > cutoff);

  fs.writeFileSync(SESSION_LOG, JSON.stringify(log, null, 2), "utf-8");

  // Show today's stats
  const todaySessions = log.sessions.filter(s => s.date === today);
  const todaySeeds = todaySessions.reduce((sum, s) => sum + s.seeds, 0);
  const todayAccounts = todaySessions.reduce((sum, s) => sum + s.accounts, 0);
  console.log(`\n  [Session] Today: ${todaySessions.length} runs, ${todaySeeds} seeds, ${todayAccounts} accounts`);
}

// ============================================================
// Core: extract similar accounts from one seed
// ============================================================

/**
 * Sanitize a seed argument (full URL or bare username) to just the username.
 */
function sanitizeSeed(raw) {
  // Strip protocol + domain if present
  let s = raw.replace(/^https?:\/\//i, "").replace(/^www\./i, "");
  // instagram.com/username/... → username
  const m = s.match(/^instagram\.com\/([a-zA-Z0-9._-]{2,30})/i);
  if (m) return m[1];
  // tiktok.com/@username/... → username (keep @ if present)
  const ttm = s.match(/^tiktok\.com\/@?([a-zA-Z0-9._-]{2,30})/i);
  if (ttm) return ttm[1];
  // Remove trailing slashes/reels/posts
  s = s.replace(/\/.*$/, "");
  // Remove leading @ if present
  s = s.replace(/^@/, "");
  return s;
}

async function extractSimilarAccounts(page, seed, cfg) {
  const username = sanitizeSeed(seed);
  const t0 = Date.now();
  console.log(`\n=== @${seed} ===`);

  // Step 1: Navigate to profile (with retry)
  console.log("  [1/4] Loading profile...");
  let loaded = false;
  for (let retry = 0; retry < 3; retry++) {
    try {
      await page.goto(`https://www.instagram.com/${username}/`, {
        waitUntil: "networkidle",
        timeout: 25000,
      });
      loaded = true;
      break;
    } catch (e) {
      if (retry < 2) {
        console.log(`    Retry ${retry + 1}/2: ${e.message.slice(0, 60)}...`);
        await sleep(3000);
      }
    }
  }
  if (!loaded) {
    console.log("  [!] Page failed to load after 3 retries — skipping seed");
    return [];
  }
  await sleep(jitter(cfg.pageLoadDelay, cfg.pageLoadJitter));

  // Step 2: Click "类似账户" / "Similar accounts"
  console.log("  [2/4] Clicking 'Similar accounts'...");
  const btn = page.locator('[role="button"]').filter({
    hasText: /类似账户|Similar accounts|Ähnliche Konten/i,
  }).first();

  if ((await btn.count()) === 0) {
    console.log("  [!] No 'Similar accounts' button — not logged in or private account");
    return [];
  }

  await btn.click({ timeout: 10000 });
  await sleep(jitter(cfg.clickDelayBase, cfg.clickDelayJitter));

  // Step 3: Click "查看全部" / "See all"
  // Search within the dialog/modal that appeared after clicking Similar accounts
  console.log("  [3/4] Clicking 'See all'...");
  // Try multiple strategies to find the right "See all" link
  let seeAll = page.locator('[role="dialog"] a, [role="dialog"] span').filter({
    hasText: /^查看全部$|^See [Aa]ll$|^View [Aa]ll$/,
  });
  if ((await seeAll.count()) === 0) {
    // Fallback: look for any short-text element with the target text
    seeAll = page.locator("a, span, button").filter({
      hasText: /^查看全部$|^See\s*[Aa]ll$|^View\s*[Aa]ll$/,
    });
  }
  if ((await seeAll.count()) === 0) {
    // Last resort: broader match but filter out huge text blobs
    seeAll = page.locator("a, span, div, button").filter({
      hasText: /查看全部|See\s*[Aa]ll|View\s*[Aa]ll/,
    }).filter({
      hasNotText: /帖子|Reels|粉丝|followers|关注|following|创建|消息|通知|搜索|首页|Meta|Threads|Afrikaans/i,
    });
  }
  seeAll = seeAll.first();

  let hasSeeAll = true;
  if ((await seeAll.count()) > 0) {
    await seeAll.click({ timeout: 10000 });
    await sleep(jitter(cfg.clickDelayBase, cfg.clickDelayJitter));
  } else {
    console.log("  [!] No 'See all' link — modal preview only, will quick-check then skip if empty");
    hasSeeAll = false;
  }

  // Step 4: Scroll with human-like jitter — target the correct container
  console.log(`  [4/4] Scrolling (max ${cfg.scrollCount} passes, stops when no new links)...`);
  let prevLinkCount = 0;
  let noNewLinksStreak = 0;
  for (let i = 0; i < cfg.scrollCount; i++) {
    const amount = jitter(cfg.scrollAmountBase, cfg.scrollAmountJitter);
    await page.evaluate((px) => {
      // Find ALL scrollable containers (not just inline-style ones)
      const all = document.querySelectorAll('*');
      for (const el of all) {
        if (el.scrollHeight > el.clientHeight && el.clientHeight > 0) {
          el.scrollTop += px;
        }
      }
      window.scrollBy(0, px);
    }, amount);
    await sleep(jitter(cfg.scrollDelayBase, cfg.scrollDelayJitter));

    // Check link count to decide if we should stop
    const currentCount = await page.evaluate(() => {
      const s = new Set();
      const ex = new Set(["explore","accounts","p","reel","stories","direct","about","popular","reels","search","meta","api","threads","instagram"]);
      document.querySelectorAll('a[href^="/"]').forEach(a => {
        const m = a.href.match(/instagram\.com\/([a-zA-Z0-9._-]{2,30})\/?$/);
        if (m && !ex.has(m[1].toLowerCase())) s.add(m[1].toLowerCase());
      });
      return s.size;
    });

    if (currentCount === prevLinkCount) {
      noNewLinksStreak++;
      if (noNewLinksStreak >= 4 && currentCount > 10) {
        console.log(`    No new links after ${i + 1} scrolls (${currentCount} total), done.`);
        break;
      }
    } else {
      noNewLinksStreak = 0;
    }
    prevLinkCount = currentCount;

    // Quick abandon: no See all + very few accounts → skip this seed
    if (!hasSeeAll && i >= 5 && currentCount <= 3) {
      console.log(`    Only ${currentCount} accounts, no See all — skipping seed.`);
      return [];
    }

    // Occasional micro-pause (human behaviour)
    if (Math.random() < 0.05) {
      await sleep(rand(500, 2000));
    }
  }
  await sleep(1500);

  // Detect logged-in user to exclude (multiple fallback methods)
  const loggedInUser = await page.evaluate(() => {
    // Method 1: IG's own window.__INITIAL_STATE__ or similar
    try {
      const scripts = document.querySelectorAll('script[type="application/json"]');
      for (const s of scripts) {
        const data = JSON.parse(s.textContent || '{}');
        const viewer = data?.config?.viewer || data?.viewer;
        if (viewer?.username) return viewer.username.toLowerCase();
      }
    } catch {}
    // Method 2: Look for "Profile" link in nav/sidebar
    const links = document.querySelectorAll('a[href^="/"]');
    for (const a of links) {
      const href = a.getAttribute('href');
      if (!href) continue;
      const parent = a.closest('nav, [role="navigation"], div[role="tablist"]');
      if (!parent) continue;
      const m = href.match(/^\/([a-zA-Z0-9._-]{2,30})\/?$/);
      if (m) return m[1].toLowerCase();
    }
    // Method 3: Look for the "Profile" button text in sidebar
    for (const a of links) {
      if (a.textContent?.trim() === 'Profile' || a.textContent?.trim() === '个人主页') {
        const m = a.getAttribute('href')?.match(/^\/([a-zA-Z0-9._-]{2,30})\/?$/);
        if (m) return m[1].toLowerCase();
      }
    }
    return null;
  });

  // Extract
  const links = await page.evaluate(() => {
    const found = new Set();
    const EXCLUDE = new Set([
      "explore", "accounts", "p", "reel", "stories", "direct",
      "about", "popular", "reels", "search",
      "meta", "api", "threads", "instagram",
    ]);

    document.querySelectorAll('a[href^="/"]').forEach(a => {
      const m = a.href.match(/instagram\.com\/([a-zA-Z0-9._-]{2,30})\/?$/);
      if (m) {
        const u = m[1].toLowerCase();
        if (!EXCLUDE.has(u)) found.add(u);
      }
    });
    return [...found];
  });

  let clean = links.filter(u => u !== username.toLowerCase());
  if (loggedInUser) {
    clean = clean.filter(u => u !== loggedInUser);
  }
  const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`  => ${clean.length} accounts (${elapsed}s)`);
  return clean;
}

// ============================================================
// Main
// ============================================================

async function main() {
  // Parse args
  const args = process.argv.slice(2);
  let cfg = { ...SAFE };
  let seeds = [];
  let autoPipeline = false;

  let i = 0;
  while (i < args.length) {
    if (args[i] === "--fast") {
      cfg = { ...FAST };
      console.log("[!] FAST mode — safety delays disabled");
    } else if (args[i] === "--auto-pipeline") {
      autoPipeline = true;
    } else if (args[i] === "--max-seeds" && i + 1 < args.length) {
      cfg.maxSeedsPerSession = parseInt(args[i + 1]);
      i++;
    } else if (!args[i].startsWith("--")) {
      seeds.push(args[i]);
    }
    i++;
  }

  if (seeds.length === 0) {
    console.log("Usage: node fetch_similar_accounts_v3.mjs [--fast] [--auto-pipeline] [--max-seeds N] <username1> [username2 ...]");
    console.log("");
    console.log("Options:");
    console.log("  --fast            Skip safety delays (debug only)");
    console.log("  --auto-pipeline   Auto-run pipeline after extraction");
    console.log("  --max-seeds N     Override max seeds per session");
    console.log("");
    console.log("Safety defaults:");
    console.log(`  Seed delay: ${SAFE.seedDelayMin / 1000}-${SAFE.seedDelayMax / 1000}s random`);
    console.log(`  Max seeds/session: ${SAFE.maxSeedsPerSession}`);
    console.log(`  Scroll: ${SAFE.scrollCount} passes with random jitter`);
    console.log("  Session log: data/session_log.json");
    process.exit(1);
  }

  // Enforce max seeds per session
  if (seeds.length > cfg.maxSeedsPerSession) {
    console.log(`[!] Limiting to ${cfg.maxSeedsPerSession} seeds (${seeds.length} requested)`);
    console.log(`    Run another session later for the remaining ${seeds.length - cfg.maxSeedsPerSession}`);
    seeds = seeds.slice(0, cfg.maxSeedsPerSession);
  }

  const isSafe = cfg.seedDelayMin > 0;
  const estTime = seeds.length * (cfg.seedDelayMax + 45000) / 1000 / 60;

  console.log(`ICRUSH Similar Accounts v3`);
  console.log(`Mode: ${isSafe ? "SAFE (human-like)" : "FAST (no delays)"}`);
  console.log(`Seeds: ${seeds.length} | Est. time: ~${estTime.toFixed(0)} min`);
  console.log(`${"=".repeat(50)}`);

  // Ensure session log dir
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });

  // Connect to Chrome
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const ctx = browser.contexts()[0];
  const page = await ctx.newPage();

  const allAccounts = new Set();
  const results = {};

  for (let si = 0; si < seeds.length; si++) {
    const seed = seeds[si];
    const accounts = await extractSimilarAccounts(page, seed, cfg);
    results[seed] = accounts;
    accounts.forEach(a => allAccounts.add(a.toLowerCase()));

    // Random delay between seeds (skip for last)
    if (si < seeds.length - 1 && cfg.seedDelayMax > 0) {
      const delay = rand(cfg.seedDelayMin, cfg.seedDelayMax);
      console.log(`\n  ⏳ Cooling down ${(delay / 1000).toFixed(0)}s before next seed...`);
      await sleep(delay);
    }
  }

  await page.close();
  await browser.close();  // Disconnect CDP WebSocket so Node exits cleanly

  // Summary
  const total = [...allAccounts].length;
  console.log(`\n${"=".repeat(50)}`);
  console.log(`Total unique accounts: ${total}`);
  console.log(`${"=".repeat(50)}`);

  // Save per-seed
  for (const [seed, accounts] of Object.entries(results)) {
    if (accounts.length > 0) {
      const safeName = sanitizeSeed(seed);
      const outPath = path.join(DATA_DIR, `similar_${safeName}.txt`);
      const urls = accounts.map(u => `https://www.instagram.com/${u}/`);
      fs.writeFileSync(outPath, urls.join("\n") + "\n", "utf-8");
      console.log(`  ${safeName}: ${accounts.length} → similar_${safeName}.txt`);
    }
  }

  // Save combined
  if (total > 0) {
    const combinedPath = path.join(DATA_DIR, "input_similar_combined.txt");
    const allUrls = [...allAccounts].map(u => `https://www.instagram.com/${u}/`);
    fs.writeFileSync(combinedPath, allUrls.join("\n") + "\n", "utf-8");
    console.log(`  Combined (${total}) → input_similar_combined.txt`);
  }

  // Session stats
  logSession(seeds.length, total);

  if (total === 0) {
    console.log("\n⚠️  0 accounts found — skipping pipeline");
    return;
  }

  const combinedPath = path.join(DATA_DIR, "input_similar_combined.txt");

  if (autoPipeline) {
    console.log(`\n${"=".repeat(50)}`);
    console.log("Auto-pipeline: feeding into run_batch.py...");
    console.log(`${"=".repeat(50)}`);

    const pythonPath = process.env.PYTHON_EXE || "python";
    const proc = spawn(pythonPath, ["scripts/run_batch.py", combinedPath], {
      cwd: PROJECT_ROOT,
      stdio: "inherit",
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    });

    await new Promise((resolve, reject) => {
      proc.on("close", (code) => {
        if (code === 0) console.log("\n✅ Pipeline complete!");
        else console.log(`\n⚠️  Pipeline exited with code ${code}`);
        resolve();
      });
      proc.on("error", (err) => {
        console.error(`\n❌ Failed to start pipeline: ${err.message}`);
        resolve();
      });
    });
  } else {
    console.log(`\nNext step: python scripts/run_batch.py ${combinedPath}`);
  }
}

main().catch(e => {
  console.error("FAILED:", e.message);
  process.exit(1);
});
