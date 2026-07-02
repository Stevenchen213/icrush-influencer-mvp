"""Diagnose why these 8 accounts slipped through short_circuit."""
import asyncio, sys, re, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ACCOUNTS = [
    "createdbytaavi",       # supposedly male
    "besenbinder",          # performance/brand account
    "gcg_baunatal",         # official account
    "gymnasiummellendorf",  # school official account
    "jeannetteharttung",    # no real commercial posts?
    "rufjugendreisen",      # travel company
    "bv_tuntenhausen",      # official sports club
    "sveintrachtgroebers",  # sports official account
]


def parse_follower_count(raw: str) -> int:
    raw = raw.strip().replace(",", "")
    m = re.match(r"([\d.]+)\s*([KkMm]?)", raw)
    if not m:
        return 0
    num = float(m.group(1))
    unit = m.group(2).upper()
    if unit == "K": return int(num * 1_000)
    if unit == "M": return int(num * 1_000_000)
    return int(num)


async def scrape_ig_profile(username: str) -> dict | None:
    from playwright.async_api import async_playwright

    print(f"\n{'='*60}")
    print(f"🔍 @{username}")
    print(f"{'='*60}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(f"https://www.instagram.com/{username}/",
                            wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(5000)
            try:
                await page.wait_for_selector('meta[name="description"]', timeout=8000)
            except Exception:
                pass

            meta = await page.evaluate("""() => {
                const m = document.querySelector('meta[name="description"]');
                return m ? m.getAttribute('content') : '';
            }""")

            if not meta or len(meta) < 20:
                print(f"  ❌ meta too short ({len(meta)} chars)")
                return None

            followers = 0
            fm = re.search(r"([\d.,]+[KkMm]?)\s*(?:位粉丝|Followers?)", meta)
            if fm:
                followers = parse_follower_count(fm.group(1))

            posts = 0
            pm = re.search(r"(\d[\d,]*)\s*(?:篇帖子|Posts?)", meta)
            if pm:
                posts = int(pm.group(1).replace(",", ""))

            title = await page.title()
            full_name = username
            tm = re.match(r"(.+?) \(@", title)
            if tm:
                full_name = tm.group(1).strip()

            nm = re.search(r"(?:Instagram 用户 |on Instagram: )(.+?) \(@", meta)
            if nm:
                full_name = nm.group(1).strip()

            bio = ""
            bm = re.search(r'\s[："]([^"]+)"$', meta)
            if bm:
                bio = bm.group(1).replace("\\n", "\n")

            # Try to get business category
            category = None
            try:
                cat_raw = await page.evaluate("""() => {
                    const divs = document.querySelectorAll('div');
                    for (const d of divs) {
                        const t = d.textContent.trim();
                        if (['Blogger','Artist','Musician','Brand','Shopping & retail',
                             'Product/service','Clothing','Health/beauty','Personal blog',
                             'Gym/Physical fitness center','Sports team','School',
                             'Travel company','Nonprofit organization','Restaurant',
                             'Doctor','Coach','Digital creator','Video creator'].includes(t)) {
                            return t;
                        }
                    }
                    return null;
                }""")
                if cat_raw:
                    category = cat_raw
            except Exception:
                pass

            print(f"  📛 Full name: {full_name}")
            print(f"  📝 Bio: {repr(bio[:300])}")
            print(f"  🏷️  Category: {category}")
            print(f"  👥 {followers:,} followers, {posts} posts")

            return {
                "username": username,
                "fullName": full_name,
                "followersCount": followers,
                "postsCount": posts,
                "biography": bio,
                "businessCategoryName": category,
                "private": False,
                "latestPosts": [],
            }
        finally:
            await browser.close()


def diagnose(profile: dict):
    """Run each short_circuit check step-by-step and print results."""
    from icrush.judges import is_wrong_category, is_brand_account
    from icrush.language import detect_male_by_name
    from icrush.wordlists import BIO_CATEGORY_BLOCKLIST

    # FASHION_SAFE_WORDS is defined inside is_wrong_category, reproduce here for diagnosis
    FASHION_SAFE_WORDS = {
        "fashion", "beauty", "makeup", "make-up", "skincare", "hautpflege",
        "outfit", "outfits", "ootd",
        "mode", "style", "styling", "lookbook", "streetstyle",
        "nagel", "nails", "nägel", "friseur", "friseurin", "haare", "hair",
        "cosmetic", "kosmetik", "parfüm", "duft", "fragrance",
        "lippenstift", "mascara", "foundation", "nagellack",
        "augenbrauen", "brows", "lashes", "haircare",
    }

    p = {
        "name": profile["username"],
        "fullName": profile.get("fullName", ""),
        "fans": profile.get("followersCount", 0),
        "posts": profile.get("postsCount", 0),
        "bio": profile.get("biography", ""),
        "category": profile.get("businessCategoryName"),
        "private": profile.get("private", False),
        "latestPosts": profile.get("latestPosts", []),
    }

    # 1. Male check
    male_reason = detect_male_by_name(p['fullName'], p['bio'], p['name'])
    print(f"\n  👨 Male check: {'❌ ' + male_reason if male_reason else '✅ pass'}")

    # 2. Fashion whitelist check
    bio = p['bio'].lower()
    full_name = p['fullName'].lower()
    username = p['name'].lower()
    combined = bio + " " + full_name + " " + username
    fashion_tokens = set(combined.replace(",", " ").replace(".", " ").replace("|", " ")
                         .replace("/", " ").split())
    fashion_hits = fashion_tokens & FASHION_SAFE_WORDS
    print(f"  👗 Fashion whitelist: {'✅ HIT: ' + str(fashion_hits) if fashion_hits else '❌ no match'}")

    # 3. Category check — which keywords match which categories
    # (reproduced from is_wrong_category in judges.py)
    HIGH_SPECIFICITY: set[str] = {
        "psycholog", "therapeut", "paartherap", "narzissmus",
        "hebamme", "stillberatung", "familienbett", "wochenbett",
        "drilling", "adoption",
        "gospel", "pastor", "predigt", "evangelium",
        "booking@", "bookings@",
        "vanlife", "wohnmobil",
        "grundschullehrerin",
        "tierschutz", "tierheim",
        "zahnarzt", "zahnärztin", "zahnaerztin",
        "ärztin", "aerztin", "arzt",
        "heilpraktiker", "heilpraktikerin",
        "autoimmun", "chronisch krank",
        "grundschullehrerin", "klassenlehrerin",
        "energetiker", "energetikerin",
        "humanenergetiker", "humanenergetikerin",
        "tierkommunikator", "tierkommunikatorin",
        "endometriose", "adenomyose",
        "lipödem",
        "darmerkrankung",
    }
    AGGRESSIVE_CATEGORIES = {
        "心理/咨询/治疗", "音乐/演出", "宗教/教会",
        "医疗/健康", "家居/DIY/清洁",
        "教育/知识付费", "美食/烹饪",
        "宠物/动物",
    }
    _IG_CATEGORY_MAP = {
        "restaurant": "美食/烹饪", "food": "美食/烹饪", "chef": "美食/烹饪",
        "kitchen": "美食/烹饪", "grocery": "美食/烹饪",
        "doctor": "医疗/健康", "medical": "医疗/健康", "health": "医疗/健康",
        "hospital": "医疗/健康", "clinic": "医疗/健康", "dentist": "医疗/健康",
        "pharmacy": "医疗/健康", "physiotherapist": "医疗/健康",
        "psychologist": "心理/咨询/治疗", "therapist": "心理/咨询/治疗",
        "mental health": "心理/咨询/治疗", "counselor": "心理/咨询/治疗",
        "coach": "心理/咨询/治疗",
        "musician": "音乐/演出", "band": "音乐/演出", "dj": "音乐/演出",
        "festival": "音乐/演出", "concert": "音乐/演出",
        "church": "宗教/教会", "religious": "宗教/教会",
        "nonprofit": "宗教/教会", "charity": "宗教/教会",
        "school": "教育/知识付费", "teacher": "教育/知识付费",
        "education": "教育/知识付费", "tutor": "教育/知识付费",
        "university": "教育/知识付费", "college": "教育/知识付费",
        "pet": "宠物/动物", "animal": "宠物/动物",
        "veterinarian": "宠物/动物", "vet": "宠物/动物",
        "home": "家居/DIY/清洁", "interior": "家居/DIY/清洁",
        "cleaning": "家居/DIY/清洁", "gardener": "家居/DIY/清洁",
        "pregnancy": "母婴/育儿", "parenting": "母婴/育儿",
        "baby": "母婴/育儿", "child": "母婴/育儿",
    }
    ig_category = (p.get("category") or "").lower()
    ig_cat_hit = None
    for sig, cat in _IG_CATEGORY_MAP.items():
        if sig in ig_category:
            ig_cat_hit = cat
            break
    if ig_cat_hit:
        print(f"  🏷️  IG Category match: {ig_category} → {ig_cat_hit} (+3 pts)")

    cat_tokens = set(combined.replace(",", " ").replace(".", " ").replace("|", " ")
                     .replace("/", " ").replace("-", " ").replace("&", " ").split())

    for category, keywords in BIO_CATEGORY_BLOCKLIST.items():
        hits = 0
        matched_kws = []
        threshold = 1 if category in AGGRESSIVE_CATEGORIES else 2
        if ig_cat_hit == category:
            hits += 3
            matched_kws.append(f"IG_CAT:{ig_category}")
        for kw in keywords:
            matched = False
            if kw in HIGH_SPECIFICITY:
                matched = kw in combined
            elif len(kw) <= 5:
                matched = kw in cat_tokens
            else:
                matched = kw in combined
            if matched:
                if kw in HIGH_SPECIFICITY:
                    hits += 3
                else:
                    hits += 1
                matched_kws.append(kw)
        if matched_kws:
            status = "🛑 BLOCK" if hits >= threshold else f"⚠️  {hits}/{threshold}"
            print(f"  📂 {category} [{status}]: {matched_kws}")

    is_wrong, cat_reason = is_wrong_category(p)
    print(f"\n  🏁 Category verdict: {'❌ ' + cat_reason if is_wrong else '✅ pass'}")

    # 4. Brand check
    is_brand = is_brand_account(p)
    print(f"  🏁 Brand verdict: {'❌ BRAND' if is_brand else '✅ pass'}")

    # 5. Overall short_circuit
    from icrush.judges import short_circuit
    sc = short_circuit("IG", p)
    print(f"  🏁 SHORT CIRCUIT: {'❌ ' + sc['reason'] if sc['fail'] else '✅ PASSED (should have been blocked!)'}")


async def main():
    for username in ACCOUNTS:
        profile = await scrape_ig_profile(username)
        if profile:
            diagnose(profile)
        await asyncio.sleep(2)  # polite delay

    print(f"\n{'='*60}")
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
