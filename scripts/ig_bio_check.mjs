import { chromium } from "playwright";

// Pick the most German-looking profiles to verify
const CANDIDATES = [
  "emmaleinswelt", "annamariadamm", "diekleinebeautyfee",
  "meinekette", "nettiweber", "alicia.andrich",
  "juliaschwab", "clairesulmers", "ellabekind",
  "funda.kocak_", "kyla_estelle_", "emmasedition",
  "marc.gebauer", "janabofficial", "laura_mertens",
  "stylebyjessy", "lisaunddavid", "annalena_style",
  "fashioninfluencerin", "marlenelifestyle",
];

async function main() {
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

  console.log("Profile Bio Check");
  console.log("=".repeat(50));

  const germanCities = ["berlin","hamburg","münchen","munich","köln","cologne","frankfurt","stuttgart","düsseldorf","dusseldorf","leipzig","dresden","hannover","nürnberg","nuremberg","bremen","bonn","aachen","bielefeld","mannheim","freiburg","heidelberg","karlsruhe","augsburg","wiesbaden","münster","kiel","potsdam","darmstadt","ulm","bamberg","mainz","würzburg","germany","deutschland","österreich","austria","wien","vienna","salzburg","graz","linz","zürich","zurich","bern","basel"];

  for (const username of CANDIDATES) {
    process.stdout.write(`@${username}: `);
    try {
      await page.goto(`https://www.instagram.com/${username}/`, { waitUntil: "networkidle", timeout: 15000 });
      await page.waitForTimeout(2000);

      // Extract bio text
      const bio = await page.evaluate(() => {
        // Try various selectors for bio
        const selectors = [
          "header section span",
          'div[class*="biography"]',
          'div._aa_c',
          'span._aaco',
          'meta[name="description"]',
        ];
        for (const sel of selectors) {
          const el = document.querySelector(sel);
          if (el) return el.textContent || el.getAttribute("content") || "";
        }
        return document.body.innerText.substring(0, 300);
      });

      const lower = bio.toLowerCase();
      const isGerman = germanCities.some(c => lower.includes(c)) ||
                       lower.includes("deutschland") ||
                       lower.includes("germany") ||
                       lower.includes("based in");

      const follower = bio.match(/[\d,.]+[kKmM]?.*follower/i);
      console.log(`${isGerman ? "🇩🇪" : "❓"} ${bio.substring(0, 120).replace(/\n/g, " ")}`);

    } catch (e) {
      console.log(`❌ Error: ${e.message.substring(0, 50)}`);
    }
  }

  await browser.close();
}

main().catch(console.error);