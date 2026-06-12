#!/usr/bin/env node
/**
 * 完整批量判定流水线（v0.5 Wednesday 集成）
 *
 * 流程：
 *   STAGE 1: profile metadata（IG profile-scraper; TT clockworks resultsPerPage=1）
 *   ↓ 短路淘汰：帖数<150 ❌ / 150-199 reel-heavy 豁免 / 职业=艺术家律师 / 私密 / 粉丝越界
 *   STAGE 1.5: Wednesday/Upfluence 查询（免费）
 *   ├─ ✅ 有数据 → 受众国家#1=DE(>35%) + 城市#1=德城 → 地区确认
 *   │            + 男粉占比 >50%(>100K 时 65%) → ❌
 *   │            两项都通过 → 直接 ✅（跳过语言检测）
 *   └─ ❌ 无数据 → 走原流程
 *   STAGE 2: survivors 抓 20 posts（IG detailedData 含 view count，TT clockworks）
 *   ↓ Wednesday 确认者：仅算 avgViews + 性别判定
 *   ↓ Wednesday 无数据者：caption 语言（① ≥25%）；⚠️ = region 在 DE/AT 但 caption <25%
 *   STAGE 3（仅当有 ⚠️ 时）：⚠️ 用户调评论 API（每视频/帖 10 条，表情不计入）
 *   ↓ 评论 ≥60% → ✅/🟡（看 avgViews+fans）；<60% → ❌；不足 → 还是 ⚠️
 *   输出按用户粘贴顺序，含男粉占比列，存 results/<date>_batch<N>_<seq>.md，末尾打印成本
 *
 * 用法：
 *   node --env-file=.env scripts/run_batch.mjs data/input.txt
 *   或: echo "https://www.instagram.com/x/" | node --env-file=.env scripts/run_batch.mjs -
 */

import fs from 'fs';
import path from 'path';

// === 常量（v0.4 微调） ===
const TOKEN = process.env.APIFY_TOKEN;
if (!TOKEN) throw new Error('APIFY_TOKEN 未设置（用 --env-file=.env）');

const SKIP_COMMENTS = process.env.SKIP_COMMENTS === '1';
const CAPTION_THRESHOLD = 25;
const COMMENT_THRESHOLD = 60;
const POSTS_LIMIT = 20;
const COMMENTS_PER_POST = 10;
const POSTS_MIN = 200;
const FAN_MIN = 1000;
const FAN_MAX = { TT: 500000, IG: 300000 };
const FAN_REPLACE = 10000;
const VIEW_REPLACE = 2000;
const VIEW_OK = 4000;
const THREE_MONTH_MS = 90 * 24 * 60 * 60 * 1000;
const USD_TO_CNY = 7.25;
const WEDNESDAY_TOKEN = process.env.WEDNESDAY_TOKEN || '';
const WEDNESDAY_BASE = 'https://facade.upfluence.co/api/v1';
const GENDER_MALE_MAX = 50;
const GENDER_MALE_MAX_100K = 65;
const WEDNESDAY_COUNTRY_MIN = 35;

const DATA_DIR = path.resolve('./data');
const RESULTS_DIR = path.resolve('./results');
fs.mkdirSync(DATA_DIR, { recursive: true });
fs.mkdirSync(RESULTS_DIR, { recursive: true });

// === URL parsing ===
function parseURL(url) {
  const u = url.trim();
  if (!u || u.startsWith('#')) return null;
  let m;
  if ((m = u.match(/tiktok\.com\/@([\w._-]+)/))) return { platform: 'TT', username: m[1] };
  if ((m = u.match(/instagram\.com\/([\w._-]+)/))) {
    const seg = m[1];
    if (['p', 'reel', 'reels', 'tv', 'stories', 'explore'].includes(seg.toLowerCase())) return null;
    return { platform: 'IG', username: seg.replace(/\/$/, '') };
  }
  return null;
}

// === Apify API（带重试，国内网络抗波动）===
const apifyRuns = [];

async function apiFetch(url, opts = {}, retries = 3) {
  let lastErr;
  for (let i = 0; i < retries; i++) {
    try {
      const r = await fetch(url, opts);
      return r;
    } catch (e) {
      lastErr = e;
      if (i < retries - 1) { console.log(`  ⚡ fetch 重试 ${i + 1}/${retries}: ${e.message}`); await new Promise(r => setTimeout(r, 3000 * (i + 1))); }
    }
  }
  throw lastErr;
}

async function startActor(actor, input) {
  const url = `https://api.apify.com/v2/acts/${actor.replace('/', '~')}/runs?token=${TOKEN}`;
  const r = await apiFetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!r.ok) throw new Error(`startActor(${actor}): HTTP ${r.status}: ${await r.text()}`);
  const data = (await r.json()).data;
  apifyRuns.push({ id: data.id, actor });
  return { runId: data.id, datasetId: data.defaultDatasetId };
}

async function waitForRun(runId, maxWaitSec = 900) {
  const start = Date.now();
  while (Date.now() - start < maxWaitSec * 1000) {
    const r = await apiFetch(`https://api.apify.com/v2/actor-runs/${runId}?token=${TOKEN}`);
    const data = (await r.json()).data;
    if (['SUCCEEDED', 'FAILED', 'ABORTED', 'TIMED-OUT'].includes(data.status)) {
      if (data.status !== 'SUCCEEDED') throw new Error(`Run ${runId} ended with status ${data.status}`);
      return data;
    }
    await new Promise(r => setTimeout(r, 5000));
  }
  throw new Error(`Run ${runId} timed out after ${maxWaitSec}s`);
}

async function fetchDataset(datasetId) {
  const url = `https://api.apify.com/v2/datasets/${datasetId}/items?token=${TOKEN}&clean=true&limit=10000`;
  const r = await apiFetch(url);
  if (!r.ok) throw new Error(`fetchDataset(${datasetId}): HTTP ${r.status}`);
  return await r.json();
}

// === Wednesday/Upfluence 数据 ===
// 注：Upfluence API 仅限浏览器内调用（TLS 指纹保护），Node.js 直连会被拦。
// 主脚本从 data/wednesday_cache.json 读缓存；缓存由 scripts/refresh_wednesday_cache.mjs（Playwright）更新。

let _wednesdayCache = null;
function loadWednesdayCache() {
  if (_wednesdayCache) return _wednesdayCache;
  try {
    _wednesdayCache = JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'wednesday_cache.json'), 'utf-8'));
    return _wednesdayCache;
  } catch { _wednesdayCache = {}; return _wednesdayCache; }
}

function wednesdayLookup(username) {
  const cache = loadWednesdayCache();
  const entry = cache[username];
  if (!entry || !entry.found) return { found: false };
  // 国家+城市+性别三者至少有一个有效数据才算"有数据"
  const hasData = entry.gender || entry.topCountry || entry.topCity;
  if (!hasData) return { found: false };
  return {
    found: true,
    gender: entry.gender || null,
    topCountry: entry.topCountry || null,
    topCity: entry.topCity || null,
  };
}

function isGermanCity(cityName) {
  if (!cityName) return false;
  const lower = cityName.toLowerCase();
  for (const c of germanCityList) if (lower.includes(c)) return true;
  for (const c of austrianCities) if (lower.includes(c)) return true;
  // 检查德语城市缩写 + 常见德国城市格式 ", DE" / ", HH" 等
  for (const c of germanCityAbbr) if (lower.startsWith(c.toLowerCase() + ',')) return true;
  // 检查 ", DE" 结尾
  if (/, de$/.test(lower) || /, at$/.test(lower)) return true;
  return false;
}

function judgeWednesdayRegion(wd) {
  // 国家#1 必须是 DE 且 >35%
  if (!wd.topCountry || wd.topCountry.code !== 'DE') {
    return { pass: false, reason: `受众国家#1=${wd.topCountry?.code || '?'} 非 DE` };
  }
  if (wd.topCountry.pct < WEDNESDAY_COUNTRY_MIN) {
    return { pass: false, reason: `受众 DE 仅 ${wd.topCountry.pct}%<${WEDNESDAY_COUNTRY_MIN}%` };
  }
  // 城市#1 必须是德国城市
  if (!wd.topCity || !isGermanCity(wd.topCity.name)) {
    return { pass: false, reason: `受众城市#1=${wd.topCity?.name || '?'} 非德城` };
  }
  return { pass: true };
}

function judgeGender(wd, fans) {
  if (!wd.gender) return { pass: true, malePct: null }; // 没性别数据不卡
  const male = wd.gender.male;
  const maxMale = fans > 100000 ? GENDER_MALE_MAX_100K : GENDER_MALE_MAX;
  if (male > maxMale) {
    return { pass: false, malePct: wd.gender.female, reason: `男粉 ${male}%>${maxMale}%` };
  }
  return { pass: true, malePct: wd.gender.female };
}

// === 语言检测（与 analyze.mjs 同步） ===
const germanWords = new Set('ich,ist,das,die,der,den,dem,des,mit,und,auf,ein,eine,einen,oder,was,wie,sind,haben,aber,auch,nicht,nur,wenn,sich,dass,sie,für,mein,meine,meinen,kann,mehr,noch,mal,so,aus,zu,von,als,bei,zur,beim,ihr,euch,wir,heute,immer,ihre,ihren,wer,wo,warum,wieso,vom,zum,dich,nichts,etwas,keine,wird,würde,schon,dann,jetzt,wieder,sehr,viel,viele,vielen,danke,liebe,herz,leben,alle,allen,allem,alles,man,mir,dir,bin,bist,war,waren,am,im,um,wegen,ohne,nach,vor,ganz,kein,damit,weil,denn,seid,seit,dabei,dazu,hier,dort,einmal,zwischen,endlich,während,solange,obwohl,trotzdem,vielleicht,gerne,genau,wirklich,niemals,morgen,gestern,übermorgen,gut,besser,beste,schön,schöne,toll,super,prima,klasse,okay,euer,eure,mädchen,jungs,frauen,männer,leute,menschen,freunde,familie,mama,papa,tochter,sohn,schwester,bruder,neu,neue,neues,alt,alte,altes,jung,junge,erste,zweite,dritte,letzte,geht,kommt,machen,machte,gemacht,tun,tat,getan,sagen,sagte,gesagt,sehen,sah,gesehen,wollen,wollte,gewollt,müssen,musste,gemusst,sollen,sollte,gesollt,dürfen,durfte,gedurft,hätte,könnte,wäre,würde,willst,wirst,werden,werde,wurde,ihm,ihn,ihnen,ihres,ihrer,seine,seiner,seines,unser,unsere,mode,schmuck,outfit,look,herzlich,liebsten,aknesafe,akne,abspeichern,kanzlei,notar,notarin,rechtswahl,testament,beitrag,infos,rechtlichen,wusstet,jedem,tag,chance,schönste,lebens,girlie,girl,schauspielerin,willkommen,probiert,prinzessin,königin,wunderschön,wunderschöne,wunderschönen,wunderschönes,glückwunsch,geburtstag,natürlich,traum,süß,hübsch,wahnsinn,mega,geil,wow,steht'.split(','));

const englishWords = new Set('the,and,you,with,is,of,for,it,this,that,have,are,was,were,my,be,on,at,in,to,a,an,me,we,they,their,them,these,those,just,so,what,where,when,why,how,do,does,did,can,could,should,would,will,today,always,never,very,much,many,about,out,over,under,from,some,any,all,no,yes,one,two,three,your,his,her,its,him,she,he,i,love,like,life,girl,boy,people,friend,family,mom,dad,sister,brother,new,old,young,first,last,make,said,say,see,want,need,must,should,happy,sad,beautiful,cute,amazing,perfect,best,better,good,great,nice,really,actually,definitely,probably,maybe,sometimes,recipe,dress,jewelry,look,feel,feeling,tips,outfits,content,sharing,wearing,things,agenda,cleaning,streets,viennese,baby,girls,boys,women,men,wow,omg,queen,king,vibes,aesthetic,iconic,obsessed,gorgeous,stunning,adore,fabulous,pretty,lovely'.split(','));

function detectLang(text) {
  if (!text || text.trim().length < 5) return 'unknown';
  const lower = text.toLowerCase();
  const clean = lower.replace(/https?:\/\/\S+/g, '').replace(/[@#]\w+/g, '');
  let germanCharBoost = 0;
  if (/[äöüß]/.test(clean)) germanCharBoost = 3;
  const words = clean.split(/[\s\W]+/).filter(w => w.length >= 2);
  if (words.length < 2 && germanCharBoost < 2) return 'unknown';
  let g = 0, e = 0;
  for (const w of words) {
    if (germanWords.has(w)) g++;
    if (englishWords.has(w)) e++;
  }
  g += germanCharBoost;
  if (g === 0 && e === 0) return 'unknown';
  if (g > e * 1.5) return 'de';
  if (e > g * 1.5) return 'en';
  if (g > e) return 'de';
  return 'en';
}

// 简化版（用于短评论 IG）
function detectCommentLang(text) {
  if (!text) return 'unknown';
  const t = text.trim();
  if (t.length < 2) return 'unknown';
  if (/^[\W_\s]+$/.test(t)) return 'unknown'; // emoji 纯符号
  const lower = t.toLowerCase();
  const clean = lower.replace(/https?:\/\/\S+/g, '').replace(/[@#]\w+/g, '');
  if (/[äöüß]/.test(clean)) return 'de';
  const words = clean.split(/[\s\W]+/).filter(w => w.length >= 2);
  if (words.length < 1) return 'unknown';
  let g = 0, e = 0;
  for (const w of words) {
    if (germanWords.has(w)) g++;
    if (englishWords.has(w)) e++;
  }
  if (g === 0 && e === 0) return 'unknown';
  if (g >= e * 1.2) return 'de';
  if (e > g * 1.2) return 'en';
  return g > 0 ? 'de' : 'en';
}

const austrianCities = ['wien','vienna','salzburg','graz','innsbruck','linz','klagenfurt','tirol','tyrol','österreich','austria'];
const germanCityList = ['berlin','münchen','munich','hamburg','köln','cologne','frankfurt','stuttgart','düsseldorf','dusseldorf','dortmund','bremen','hannover','hanover','leipzig','dresden','nürnberg','nuremberg','duisburg','bochum','wuppertal','bielefeld','mannheim','karlsruhe','wiesbaden','bonn','münster','augsburg','aachen','germany','deutschland'];
const germanCityAbbr = ['cgn','muc','ber','fra','dus'];

function detectRegion(bioText) {
  if (!bioText) return null;
  const lower = bioText.toLowerCase();
  for (const c of austrianCities) if (new RegExp('\\b' + c + '\\b').test(lower)) return { region: 'AT', city: c };
  for (const c of germanCityList) if (new RegExp('\\b' + c + '\\b').test(lower)) return { region: 'DE', city: c };
  for (const c of germanCityAbbr) if (new RegExp('\\b' + c + '\\b').test(lower)) return { region: 'DE', city: c };
  return null;
}

function detectOccupation(bio, category) {
  const text = ((bio || '') + ' ' + (category || '')).toLowerCase();
  if (/\b(lawyer|attorney|anwalt|anwältin|anwalts|notar|notarin|rechtsanwalt|rechtsanwältin|kanzlei|advokat)\b/.test(text)) return 'Lawyer';
  if (/(category|categoryname).*artist/.test(text)) return 'Artist';
  if ((category || '').toLowerCase().split(/[,\s]+/).includes('artist')) return 'Artist';
  if (/\b(künstler|künstlerin|maler|malerin|bildhauer|skulptur|schauspielerin|schauspieler)\b/.test(text)) return 'Artist';
  return null;
}

function shortCircuit(platform, p) {
  if (p.occupation) return { fail: true, reason: `职业=${p.occupation === 'Lawyer' ? '律师' : '艺术家'}（直接 PASS）` };
  if (p.private) return { fail: true, reason: '私密账户' };
  if (p.posts < POSTS_MIN) {
    // IG: postsCount 不含"不同步到主页网格"的 reels，150-199 区间用 latestPosts 探测 reel-heavy 避免误杀
    if (platform === 'IG' && p.posts >= 150 && p.latestPosts && p.latestPosts.length > 0) {
      const reelsCount = p.latestPosts.filter(x => x.type === 'Video').length;
      const reelsRatio = reelsCount / p.latestPosts.length;
      if (reelsRatio < 0.5) {
        return { fail: true, reason: `帖数 ${p.posts}<${POSTS_MIN}` };
      }
      // reel-heavy: 大量内容没计入 postsCount，放行进 STAGE 2
    } else {
      return { fail: true, reason: `帖数 ${p.posts}<${POSTS_MIN}` };
    }
  }
  if (p.fans === 0 && p.posts > 0) return { fail: true, reason: '粉丝数据抓取异常（fans=0）' };
  if (p.fans < FAN_MIN) return { fail: true, reason: `粉丝 ${p.fans}<1K` };
  if (p.fans > FAN_MAX[platform]) return { fail: true, reason: `粉丝 ${p.fans.toLocaleString()}>${FAN_MAX[platform].toLocaleString()}` };
  return { fail: false };
}

// === 商单检测与分类 ===
const COMMERCIAL_SIGNALS = [
  'ad', 'anzeige', 'werbung', 'sponsored', 'gifted', 'collab', 'collaboration',
  'paid', 'partner', 'partnership', 'kooperation', 'reklame', 'geschenkt',
  'presssample', 'prsample', 'pr-sample', 'unbezahlt', 'unbezahlte',
];

const CATEGORY_KEYWORDS = {
  food: {
    brands: ['lieferando', 'hellofresh', 'foodspring', 'koRo', 'yfood', 'huel', 'myprotein', 'more nutrition', 'dm', 'rewe', 'edeka', 'aldi', 'lidl', 'netto', 'penny', 'kaufland', 'foodpanda', 'wolt', 'flink', 'gorillas', 'getir', 'milka', 'kinder', 'ferrero', 'haribo', 'nimm2', 'rittersport', 'lindt', 'knoppers', 'bahlsen'],
    keywords: ['food', 'foodie', 'foodblog', 'foodporn', 'essen', 'lecker', 'kochen', 'rezept', 'backen', 'frühstück', 'breakfast', 'lunch', 'dinner', 'restaurant', 'café', 'kaffee', 'coffee', 'smoothie', 'bowl', 'salat', 'vegan', 'vegetarisch', 'bio', 'organic'],
  },
  tech: {
    brands: ['apple', 'samsung', 'huawei', 'xiaomi', 'google', 'microsoft', 'sony', 'dell', 'hp', 'lenovo', 'logitech', 'amazon', 'otto', 'saturn', 'mediamarkt', 'cyberport', 'alternate', 'mindfactory', 'caseking', 'bequiet', 'corsair', 'razer', 'logitech', 'nvidia', 'amd', 'intel', 'oneplus', 'nothing', 'bose', 'sonos', 'jbl', 'marshall', 'sennheiser', 'telekom', 'vodafone', 'o2', 'congstar'],
    keywords: ['tech', 'technology', 'technik', 'gadget', 'smartphone', 'handy', 'laptop', 'tablet', 'pc', 'computer', 'gaming', 'zocken', 'setup', 'unboxing', 'review', 'test', 'testbericht', 'kopfhörer', 'headphones'],
  },
  beauty: {
    brands: ['douglas', 'sephora', 'dm', 'rossmann', 'müller', 'bipa', 'essence', 'catrice', 'maybelline', "l'oréal", 'loreal', 'nivea', 'balea', 'rituals', 'kiehls', 'laneige', 'glossier', 'fenty', 'kylie', 'nyx', 'mac', 'clinique', 'esteelauder', 'shiseido', 'neutrogena', 'garnier', 'babor', 'drhauschka', 'lavera', 'weleda'],
    keywords: ['beauty', 'makeup', 'make-up', 'skincare', 'skincareroutine', 'kosmetik', 'pflege', 'hautpflege', 'gesichtspflege', 'lippenstift', 'mascara', 'foundation', 'nagellack', 'nails', 'nägel', 'augenbrauen', 'brows', 'lashes', 'haare', 'hair', 'haircare', 'frisur', 'friseur', 'parfüm', 'duft'],
  },
  fashion: {
    brands: ['hm', 'h&m', 'zara', 'mango', 'bershka', 'pullandbear', 'stradivarius', 'asos', 'aboutyou', 'zalando', 'uniqlo', 'cos', 'arket', 'otherstories', 'massimodutti', 'adidas', 'nike', 'puma', 'reebok', 'levis', 'levi', 'tommyhilfiger', 'calvinklein', 'esprit', 's.Oliver', 'only', 'veroModa', 'newyorker', 'primark', 'cunda', 'peekcloppenburg', 'breuninger', 'mytheresa', 'farfetch', 'shein', 'cider', 'nakdfashion'],
    keywords: ['fashion', 'mode', 'outfit', 'outfits', 'ootd', 'style', 'streetstyle', 'look', 'lookbook', 'kleidung', 'klamotten', 'kombi', 'styling', 'haul', 'tryon', 'anprobe', 'passform', 'fit', 'trend', 'trends', 'kollektion', 'collection'],
  },
  jewelry: {
    brands: ['pandora', 'swarovski', 'thomassabo', 'christ', 'bijoubrigitte', 'douglas', 'swatch', 'fossil', 'michaelkors', 'tiffany', 'cartier', 'bulgari', 'apmmonaco', 'lucardi', 'siegel', 'engelsrufer', 'nomination', 'sogniadoro', 'lesgeorgettes', 'anschmuck', 'newbielovers', 'arshajewellery', 'marenjewelry', 'pukka', 'akind', 'purelei'],
    keywords: ['jewelry', 'jewellery', 'schmuck', 'schmuckstück', 'kette', 'halskette', 'ring', 'ringe', 'ohrringe', 'earrings', 'armband', 'armreif', 'bracelet', 'bangle', 'anhänger', 'pendant', 'gold', 'silber', 'sterling', 'vergoldet', 'goldplated', 'versilbert', 'edelstein', 'diamant', 'perlen', 'statement', 'minimal', 'layering'],
  },
};

function isCommercial(text, hashtagsRaw, isAd, isSponsored) {
  if (isAd || isSponsored) return true;
  // TT hashtags 可能是 [{name:'...'}] 格式，统一转字符串数组
  const hashtags = (hashtagsRaw || []).map(h => typeof h === 'string' ? h : (h.name || '')).filter(Boolean);
  const combined = ((text || '') + ' ' + hashtags.join(' ')).toLowerCase();
  return COMMERCIAL_SIGNALS.some(s => {
    if (s.length <= 4) {
      const re = new RegExp('(?:^|[#\\s])' + s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?:$|[\\s.,!?])', 'i');
      return re.test(combined);
    }
    return combined.includes(s);
  });
}

function classifyCommercial(text, hashtagsRaw, mentionsRaw, taggedUsers) {
  const hashtags = (hashtagsRaw || []).map(h => typeof h === 'string' ? h : (h.name || '')).filter(Boolean);
  const mentions = (mentionsRaw || []).map(m => typeof m === 'string' ? m : (m.name || '')).filter(Boolean);
  const combined = [
    (text || '').toLowerCase(),
    hashtags.join(' ').toLowerCase(),
    mentions.join(' ').toLowerCase(),
    (taggedUsers || []).map(t => (t.username || t.full_name || '').toLowerCase()).join(' '),
  ].join(' ');

  const scores = {};
  for (const [cat, data] of Object.entries(CATEGORY_KEYWORDS)) {
    let score = 0;
    for (const b of data.brands) { if (combined.includes(b.toLowerCase())) score += 3; }
    for (const k of data.keywords) { if (combined.includes(k.toLowerCase())) score += 1; }
    scores[cat] = score;
  }

  const entries = Object.entries(scores).filter(([, s]) => s > 0).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) return '其他';
  // 取 top 2，score 差距不大说明跨类
  const top = entries.slice(0, 2);
  if (top.length === 2 && top[0][1] >= 3 && top[0][1] >= top[1][1] * 2) return top[0][0];
  if (top.length === 2 && top[0][1] <= top[1][1] * 1.5) return `${top[0][0]}+${top[1][0]}`;
  return top[0][0];
}

const CAT_LABELS = { food: '食品', tech: '科技', beauty: '美妆', fashion: '服饰', jewelry: '珠宝' };
function formatCommercialStats(stats) {
  if (!stats) return '-';
  if (stats.total === 0) return '无';
  const parts = [];
  for (const [cat, label] of Object.entries(CAT_LABELS)) {
    if (stats[cat] > 0) parts.push(`${label}×${stats[cat]}`);
  }
  if (stats.其他 > 0) parts.push(`其他×${stats.其他}`);
  return `${parts.join(', ')} | 共${stats.total}条`;
}

function analyzeCommercial(posts, platform, threeMonthsAgo) {
  const recent = posts.filter(x => {
    let ts = x.timestamp || x.createTime || x.createTimeRaw;
    if (!ts) return false;
    // TT createTimeRaw 是 Unix 秒，JS new Date 需要毫秒
    if (typeof ts === 'number' && ts < 10000000000) ts = ts * 1000;
    return new Date(ts) > threeMonthsAgo;
  });
  const stats = { total: 0, food: 0, tech: 0, beauty: 0, fashion: 0, jewelry: 0, 其他: 0 };
  for (const p of recent) {
    const text = p.caption || p.text || '';
    const hashtags = p.hashtags || [];
    const isAd = p.isAd || false;
    const isSponsored = p.isSponsored || false;
    const mentions = p.mentions || (p.detailedMentions || []).map(m => m.name || '').filter(Boolean);
    const taggedUsers = p.taggedUsers || [];
    if (!isCommercial(text, hashtags, isAd, isSponsored)) continue;
    stats.total++;
    const cat = classifyCommercial(text, hashtags, mentions, taggedUsers);
    if (stats[cat] !== undefined) stats[cat]++;
    else stats['其他']++;
  }
  return stats;
}

// 仅 caption 判定（STAGE 2 之后；返回 ⚠️ 的会进 STAGE 3）
function judgeFromCaption(platform, p, dePct, avgViews) {
  const sc = shortCircuit(platform, p);
  if (sc.fail) return { verdict: '❌ 否', reason: sc.reason, regionAccurate: p.region ? '是' : '-' };
  const isReplaceByFans = p.fans < FAN_REPLACE;
  let regionAccurate, langStatus;
  if (p.region) {
    regionAccurate = '是';
    const pass = dePct !== null && dePct >= CAPTION_THRESHOLD;
    langStatus = pass ? 'pass' : 'need-comments';
  } else {
    regionAccurate = '-';
    if (dePct !== null && dePct >= CAPTION_THRESHOLD) { langStatus = 'pass'; regionAccurate = '是 (语言)'; }
    else return { verdict: '❌ 否', reason: `bio 无地区 + 语言 ${dePct ?? '?'}%<${CAPTION_THRESHOLD}%`, regionAccurate };
  }
  if (langStatus === 'need-comments') {
    const extra = isReplaceByFans ? `；粉丝 ${p.fans}<10K（如评论通过则置换组）` : '';
    return { verdict: '⚠️ 需人工核查', reason: `caption ${dePct}%<${CAPTION_THRESHOLD}% 但 bio 在 ${p.region.region} → 待 STAGE 3 调评论 API${extra}`, regionAccurate, _pendingComments: true };
  }
  let viewStatus;
  if (avgViews >= VIEW_OK) viewStatus = 'pass';
  else if (avgViews >= VIEW_REPLACE) viewStatus = 'replace';
  else viewStatus = 'fail';
  if (viewStatus === 'fail') return { verdict: '❌ 否', reason: `近 3 月平均浏览 ${avgViews.toLocaleString()}<${VIEW_REPLACE}`, regionAccurate };
  if (isReplaceByFans || viewStatus === 'replace') {
    const rs = [];
    if (isReplaceByFans) rs.push(`粉丝 ${p.fans}<10K`);
    if (viewStatus === 'replace') rs.push(`平均浏览 ${avgViews.toLocaleString()} 在 2000-4000`);
    return { verdict: '🟡 置换组', reason: rs.join('; '), regionAccurate };
  }
  return { verdict: '✅ 是', reason: '-', regionAccurate };
}

// STAGE 3 后的最终判定：根据评论 dePct + 已有 avgViews 拍板
function finalizeWithComments(p, avgViews, dePctComments) {
  if (dePctComments === null) {
    return { verdict: '⚠️ 需人工核查', reason: '评论数据不足（de+en 评论太少无法判定）', regionAccurate: '是 (评论)' };
  }
  if (dePctComments < COMMENT_THRESHOLD) {
    return { verdict: '❌ 否', reason: `② 评论 ${dePctComments}%<${COMMENT_THRESHOLD}%`, regionAccurate: '是 (评论)' };
  }
  const isReplaceByFans = p.fans < FAN_REPLACE;
  let viewStatus;
  if (avgViews >= VIEW_OK) viewStatus = 'pass';
  else if (avgViews >= VIEW_REPLACE) viewStatus = 'replace';
  else viewStatus = 'fail';
  if (viewStatus === 'fail') return { verdict: '❌ 否', reason: `② 评论 ${dePctComments}% 通过 但近 3 月平均浏览 ${avgViews.toLocaleString()}<${VIEW_REPLACE}`, regionAccurate: '是 (评论)' };
  if (isReplaceByFans || viewStatus === 'replace') {
    const rs = [];
    if (isReplaceByFans) rs.push(`粉丝 ${p.fans}<10K`);
    if (viewStatus === 'replace') rs.push(`平均浏览 ${avgViews.toLocaleString()} 在 2000-4000`);
    return { verdict: '🟡 置换组', reason: `② 评论 ${dePctComments}% 通过；${rs.join('; ')}`, regionAccurate: '是 (评论)' };
  }
  return { verdict: '✅ 是', reason: '-', regionAccurate: '是 (评论)' };
}

// === 主流程 ===
async function readInput() {
  const arg = process.argv[2];
  if (arg && arg !== '-') return fs.readFileSync(arg, 'utf-8');
  let data = '';
  for await (const chunk of process.stdin) data += chunk;
  return data;
}

async function reportCost() {
  let total = 0;
  const lines = [];
  for (const { id, actor } of apifyRuns) {
    try {
      const r = await apiFetch(`https://api.apify.com/v2/actor-runs/${id}?token=${TOKEN}`);
      const data = (await r.json()).data;
      const usd = data.usageTotalUsd || 0;
      total += usd;
      lines.push(`  ${actor}: $${usd.toFixed(4)}`);
    } catch (e) { lines.push(`  ${actor}: ?`); }
  }
  console.log('\n💰 Apify 成本：');
  for (const l of lines) console.log(l);
  console.log(`  ─────────`);
  console.log(`  TOTAL: $${total.toFixed(4)}  (~¥${(total * USD_TO_CNY).toFixed(2)})`);
  return total;
}

async function main() {
  const raw = await readInput();
  const inputOrder = raw.split('\n').map(parseURL).filter(Boolean);
  if (inputOrder.length === 0) {
    console.error('❌ 没解析到任何 profile URL。格式应为 https://www.instagram.com/<user>/ 或 https://www.tiktok.com/@<user>');
    process.exit(1);
  }
  console.log(`📥 输入 ${inputOrder.length} 条 URL（含重复）`);
  const uniqueTT = [...new Set(inputOrder.filter(x => x.platform === 'TT').map(x => x.username))];
  const uniqueIG = [...new Set(inputOrder.filter(x => x.platform === 'IG').map(x => x.username))];
  console.log(`🔢 去重 TT=${uniqueTT.length}, IG=${uniqueIG.length}`);

  // === STAGE 1 ===
  console.log('\n=== STAGE 1: profile metadata（短路用）===');
  const stage1 = [];
  if (uniqueTT.length > 0) {
    console.log(`  → TT clockworks profile-only (resultsPerPage=1) ×${uniqueTT.length}`);
    stage1.push(startActor('clockworks/tiktok-profile-scraper', {
      profiles: uniqueTT, profileScrapeSections: ['videos'], profileSorting: 'latest', resultsPerPage: 1,
      shouldDownloadAvatars: false, shouldDownloadCovers: false, shouldDownloadSlideshowImages: false, shouldDownloadVideos: false,
    }).then(async ({ runId, datasetId }) => ({ kind: 'tt-profile', items: (await waitForRun(runId), await fetchDataset(datasetId)) })));
  }
  if (uniqueIG.length > 0) {
    console.log(`  → IG profile-scraper ×${uniqueIG.length}`);
    stage1.push(startActor('apify/instagram-profile-scraper', { usernames: uniqueIG, includeAboutSection: true })
      .then(async ({ runId, datasetId }) => ({ kind: 'ig-profile', items: (await waitForRun(runId), await fetchDataset(datasetId)) })));
  }
  const stage1Results = await Promise.all(stage1);

  const ttProfiles = {}, igProfiles = {};
  for (const { kind, items } of stage1Results) {
    if (kind === 'tt-profile') {
      for (const v of items) {
        const name = v['authorMeta.name'] || v.authorMeta?.name;
        if (!name || ttProfiles[name]) continue;
        const bio = v['authorMeta.signature'] || v.authorMeta?.signature || '';
        const category = v['authorMeta.commerceUserInfo.category'] || v.authorMeta?.commerceUserInfo?.category || null;
        ttProfiles[name] = {
          name, fans: v['authorMeta.fans'] || v.authorMeta?.fans || 0,
          posts: v['authorMeta.video'] || v.authorMeta?.video || 0,
          bio, category,
          private: v['authorMeta.privateAccount'] || v.authorMeta?.privateAccount || false,
          region: detectRegion(bio), occupation: detectOccupation(bio, category),
        };
      }
    } else {
      for (const p of items) {
        // 优先读 about.country（IG 账号设置里的地区），次选 bio 城市匹配
        let region = null;
        const aboutCountry = (p.about && p.about.country) || '';
        if (aboutCountry === 'Germany') region = { region: 'DE', city: 'about.country' };
        else if (aboutCountry === 'Austria') region = { region: 'AT', city: 'about.country' };
        else region = detectRegion(p.biography || '');
        igProfiles[p.username] = {
          name: p.username, fans: p.followersCount || 0, posts: p.postsCount || 0,
          bio: p.biography || '', category: p.businessCategoryName || null, private: p.private || false,
          region, occupation: detectOccupation(p.biography || '', p.businessCategoryName),
          latestPosts: p.latestPosts || [],
        };
      }
    }
  }

  // === 短路过滤 ===
  const results = {};        // 'TT:user'/'IG:user' → 最终判定
  const survivorMeta = {};   // 'TT:user'/'IG:user' → { avgViews, urls } 给 STAGE 3 用
  const ttSurvivors = [], igSurvivors = [];
  for (const u of uniqueTT) {
    const p = ttProfiles[u];
    if (!p) { results[`TT:${u}`] = { platform: 'TT', name: u, fans: null, posts: null, regionAccurate: '-', avgViews: null, genderFemale: null, verdict: '⚠️ 抓取失败', commercialStats: null, reason: 'TT profile 抓取无返回' }; continue; }
    const sc = shortCircuit('TT', p);
    if (sc.fail) results[`TT:${u}`] = { platform: 'TT', name: u, fans: p.fans, posts: p.posts, regionAccurate: p.region ? '是' : '-', avgViews: null, genderFemale: null, commercialStats: null, verdict: '❌ 否', reason: sc.reason };
    else ttSurvivors.push(u);
  }
  for (const u of uniqueIG) {
    const p = igProfiles[u];
    if (!p) { results[`IG:${u}`] = { platform: 'IG', name: u, fans: null, posts: null, regionAccurate: '-', avgViews: null, genderFemale: null, verdict: '⚠️ 抓取失败', commercialStats: null, reason: 'IG profile 抓取无返回' }; continue; }
    const sc = shortCircuit('IG', p);
    if (sc.fail) results[`IG:${u}`] = { platform: 'IG', name: u, fans: p.fans, posts: p.posts, regionAccurate: p.region ? '是' : '-', avgViews: null, genderFemale: null, commercialStats: null, verdict: '❌ 否', reason: sc.reason };
    else igSurvivors.push(u);
  }
  console.log(`\n⚡ 短路淘汰: TT ${uniqueTT.length - ttSurvivors.length}/${uniqueTT.length}, IG ${uniqueIG.length - igSurvivors.length}/${uniqueIG.length}`);
  console.log(`   TT 存活: [${ttSurvivors.join(', ') || '无'}]`);
  console.log(`   IG 存活: [${igSurvivors.join(', ') || '无'}]`);

  // === STAGE 1.5: Wednesday 缓存查询（免费）===
  // 对所有有 profile 的用户查 Wednesday（含短路淘汰的），
  // 短路淘汰的仅补全性别/地区信息；存活者正常做硬性判定
  const wednesdayData = {};   // 'IG:user'/'TT:user' → { found, regionPass, genderPass, genderFemale, ... }
  const allQueried = [...new Set([...uniqueTT, ...uniqueIG])]; // 所有人（含短路的）
  if (allQueried.length > 0) {
    const wdCount = [...ttSurvivors, ...igSurvivors].length;
    console.log(`\n=== STAGE 1.5: Wednesday 地区+性别查询（${allQueried.length} 人，${wdCount} 存活 + ${allQueried.length - wdCount} 已淘汰）===`);
    const cache = loadWednesdayCache();
    for (const u of allQueried) {
      const platform = (uniqueTT.includes(u) && !uniqueIG.includes(u)) ? 'TT' : (ttProfiles[u] ? 'TT' : 'IG');
      const p = platform === 'TT' ? ttProfiles[u] : igProfiles[u];
      if (!p) continue;
      const key = `${platform}:${u}`;
      const isShortCircuited = results[key] && results[key].verdict === '❌ 否';
      const detail = wednesdayLookup(u);
      if (!detail.found) {
        if (!isShortCircuited) {
          console.log(`  → ${key}: ❌ 无缓存 → 走原流程`);
          wednesdayData[key] = { found: false };
        }
        continue;
      }
      // 地区判定
      const regionR = judgeWednesdayRegion(detail);
      // 性别判定
      const genderR = judgeGender(detail, p.fans);
      const femaleStr = detail.gender ? `${detail.gender.female}%` : '无信息';
      wednesdayData[key] = {
        found: true,
        regionPass: regionR.pass,
        genderPass: genderR.pass,
        genderFemale: detail.gender?.female ?? null,
        topCountry: detail.topCountry,
        topCity: detail.topCity,
      };

      if (isShortCircuited) {
        // 已短路淘汰：只补全性别/地区数据，不改变判定
        const existing = results[key];
        existing.genderFemale = detail.gender?.female ?? null;
        // 若原地区判断是 "是" 且 Wednesday 也通过了，升级为 "是 (Wednesday)"
        if (existing.regionAccurate === '是' && regionR.pass) {
          existing.regionAccurate = '是 (Wednesday)';
        }
        console.log(`     ${key}: 已淘汰但补全数据 → 女粉 ${femaleStr}`);
        continue;
      }

      if (!regionR.pass) {
        // 地区不通过 → ❌
        results[key] = { platform, name: u, fans: p.fans, posts: p.posts, regionAccurate: '否 (Wednesday)', avgViews: null, genderFemale: detail.gender?.female ?? null, commercialStats: null, verdict: '❌ 否', reason: regionR.reason };
        console.log(`     ❌ 地区不通过: ${regionR.reason}`);
        // 从 survivor 列表中移除
        if (platform === 'TT') ttSurvivors.splice(ttSurvivors.indexOf(u), 1);
        else igSurvivors.splice(igSurvivors.indexOf(u), 1);
      } else if (!genderR.pass) {
        // 性别不通过 → ❌
        results[key] = { platform, name: u, fans: p.fans, posts: p.posts, regionAccurate: '是 (Wednesday)', avgViews: null, genderFemale: detail.gender?.female ?? null, commercialStats: null, verdict: '❌ 否', reason: genderR.reason };
        console.log(`     ❌ 性别不通过: ${genderR.reason} (女粉 ${femaleStr})`);
        if (platform === 'TT') ttSurvivors.splice(ttSurvivors.indexOf(u), 1);
        else igSurvivors.splice(igSurvivors.indexOf(u), 1);
      } else {
        console.log(`     ✅ 地区=DE ${detail.topCountry?.pct}% + 城市=${detail.topCity?.name} + 女粉 ${femaleStr}`);
      }
    }
    if (Object.keys(cache).length === 0) {
      console.log(`   💡 提示: 缓存为空。运行 scripts/refresh_wednesday_cache.mjs 更新 Wednesday 数据`);
    }
  }

  // === STAGE 2 ===
  const stage2DatasetMap = {};
  if (ttSurvivors.length + igSurvivors.length > 0) {
    console.log(`\n=== STAGE 2: 抓 survivors 的 posts/videos（${POSTS_LIMIT} 条/人）===`);
    const stage2 = [];
    if (ttSurvivors.length > 0) {
      console.log(`  → TT clockworks ${POSTS_LIMIT} videos ×${ttSurvivors.length}`);
      stage2.push(startActor('clockworks/tiktok-profile-scraper', {
        profiles: ttSurvivors, profileScrapeSections: ['videos'], profileSorting: 'latest', resultsPerPage: POSTS_LIMIT,
        excludePinnedPosts: true,
        shouldDownloadAvatars: false, shouldDownloadCovers: false, shouldDownloadSlideshowImages: false, shouldDownloadVideos: false,
      }).then(async ({ runId, datasetId }) => ({ kind: 'tt-posts', items: (await waitForRun(runId), await fetchDataset(datasetId)) })));
    }
    if (igSurvivors.length > 0) {
      console.log(`  → IG post-scraper detailedData, ${POSTS_LIMIT} posts ×${igSurvivors.length}`);
      stage2.push(startActor('apify/instagram-post-scraper', {
        username: igSurvivors, dataDetailLevel: 'detailedData', resultsLimit: POSTS_LIMIT, skipPinnedPosts: false,
      }).then(async ({ runId, datasetId }) => ({ kind: 'ig-posts', items: (await waitForRun(runId), await fetchDataset(datasetId)) })));
    }
    const stage2Results = await Promise.all(stage2);

    const ttPostsByUser = {}, igPostsByUser = {};
    for (const { kind, items } of stage2Results) {
      if (kind === 'tt-posts') {
        for (const v of items) {
          const name = v['authorMeta.name'] || v.authorMeta?.name;
          if (!name) continue;
          (ttPostsByUser[name] = ttPostsByUser[name] || []).push({
            lang: v.textLanguage, createTime: v.createTimeISO, createTimeRaw: v.createTime,
            playCount: v.playCount || 0, url: v.webVideoUrl,
            text: v.text || '', hashtags: v.hashtags || [],
            isAd: v.isAd || false, isSponsored: v.isSponsored || false,
            mentions: v.mentions || [], detailedMentions: v.detailedMentions || [],
          });
        }
      } else {
        for (const p of items) {
          if (!p.ownerUsername) continue;
          (igPostsByUser[p.ownerUsername] = igPostsByUser[p.ownerUsername] || []).push(p);
        }
      }
    }

    const threeMonthsAgo = new Date(Date.now() - THREE_MONTH_MS);
    for (const u of ttSurvivors) {
      const p = ttProfiles[u];
      const posts = ttPostsByUser[u] || [];
      const wdKey = `TT:${u}`;
      const wd = wednesdayData[wdKey];
      const recent = posts.filter(x => new Date(x.createTime) > threeMonthsAgo);
      const avgViews = recent.length > 0 ? Math.round(recent.reduce((s, x) => s + x.playCount, 0) / recent.length) : 0;
      const genderFemale = wd?.genderFemale ?? null;
      const commercialStats = analyzeCommercial(posts, 'TT', threeMonthsAgo);

      if (wd?.found && wd.regionPass && wd.genderPass) {
        // Wednesday 确认 → 跳过语言检测，只判定 avgViews + fans
        const regionAccurate = '是 (Wednesday)';
        const isReplaceByFans = p.fans < FAN_REPLACE;
        let viewStatus;
        if (avgViews >= VIEW_OK) viewStatus = 'pass';
        else if (avgViews >= VIEW_REPLACE) viewStatus = 'replace';
        else viewStatus = 'fail';
        if (viewStatus === 'fail') {
          results[wdKey] = { platform: 'TT', name: u, fans: p.fans, posts: p.posts, regionAccurate, avgViews, genderFemale, commercialStats, verdict: '❌ 否', reason: `近 3 月平均浏览 ${avgViews.toLocaleString()}<${VIEW_REPLACE}` };
        } else if (isReplaceByFans || viewStatus === 'replace') {
          const rs = []; if (isReplaceByFans) rs.push(`粉丝 ${p.fans}<10K`); if (viewStatus === 'replace') rs.push(`平均浏览 ${avgViews.toLocaleString()} 在 2000-4000`);
          results[wdKey] = { platform: 'TT', name: u, fans: p.fans, posts: p.posts, regionAccurate, avgViews, genderFemale, commercialStats, verdict: '🟡 置换组', reason: rs.join('; ') };
        } else {
          results[wdKey] = { platform: 'TT', name: u, fans: p.fans, posts: p.posts, regionAccurate, avgViews, genderFemale, commercialStats, verdict: '✅ 是', reason: '-' };
        }
      } else {
        // 无 Wednesday 数据 → 原流程
        const de = posts.filter(x => x.lang === 'de').length;
        const en = posts.filter(x => x.lang === 'en').length;
        const dePct = (de + en) > 0 ? Math.round(de * 100 / (de + en)) : null;
        const j = judgeFromCaption('TT', p, dePct, avgViews);
        results[wdKey] = { platform: 'TT', name: u, fans: p.fans, posts: p.posts, ...j, avgViews, genderFemale, commercialStats };
      }
      survivorMeta[wdKey] = { avgViews, urls: posts.map(x => x.url).filter(Boolean) };
    }
    for (const u of igSurvivors) {
      const p = igProfiles[u];
      const posts = igPostsByUser[u] || [];
      const wdKey = `IG:${u}`;
      const wd = wednesdayData[wdKey];
      const recentVideos = posts.filter(x =>
        (x.type === 'Video' || (x.videoPlayCount && x.videoPlayCount > 0)) &&
        x.timestamp && new Date(x.timestamp) > threeMonthsAgo
      );
      let avgViews = 0;
      if (recentVideos.length > 0) {
        const views = recentVideos.map(x => x.videoPlayCount || x.videoViewCount || 0);
        avgViews = Math.round(views.reduce((s, v) => s + v, 0) / views.length);
      }
      const genderFemale = wd?.genderFemale ?? null;
      const commercialStats = analyzeCommercial(posts, 'IG', threeMonthsAgo);

      if (wd?.found && wd.regionPass && wd.genderPass) {
        // Wednesday 确认 → 跳过语言检测，只判定 avgViews + fans
        const regionAccurate = '是 (Wednesday)';
        const isReplaceByFans = p.fans < FAN_REPLACE;
        let viewStatus;
        if (avgViews >= VIEW_OK) viewStatus = 'pass';
        else if (avgViews >= VIEW_REPLACE) viewStatus = 'replace';
        else viewStatus = 'fail';
        if (viewStatus === 'fail') {
          results[wdKey] = { platform: 'IG', name: u, fans: p.fans, posts: p.posts, regionAccurate, avgViews, genderFemale, commercialStats, verdict: '❌ 否', reason: `近 3 月平均浏览 ${avgViews.toLocaleString()}<${VIEW_REPLACE}` };
        } else if (isReplaceByFans || viewStatus === 'replace') {
          const rs = []; if (isReplaceByFans) rs.push(`粉丝 ${p.fans}<10K`); if (viewStatus === 'replace') rs.push(`平均浏览 ${avgViews.toLocaleString()} 在 2000-4000`);
          results[wdKey] = { platform: 'IG', name: u, fans: p.fans, posts: p.posts, regionAccurate, avgViews, genderFemale, commercialStats, verdict: '🟡 置换组', reason: rs.join('; ') };
        } else {
          results[wdKey] = { platform: 'IG', name: u, fans: p.fans, posts: p.posts, regionAccurate, avgViews, genderFemale, commercialStats, verdict: '✅ 是', reason: '-' };
        }
      } else {
        // 无 Wednesday 数据 → 原流程
        const captions = posts.filter(x => x.caption && x.caption.trim().length > 5);
        let g = 0, e = 0;
        for (const post of captions) {
          const lang = detectLang(post.caption);
          if (lang === 'de') g++; else if (lang === 'en') e++;
        }
        const dePct = (g + e) > 0 ? Math.round(g * 100 / (g + e)) : null;
        const j = judgeFromCaption('IG', p, dePct, avgViews);
        results[wdKey] = { platform: 'IG', name: u, fans: p.fans, posts: p.posts, ...j, avgViews, genderFemale, commercialStats };
      }
      survivorMeta[wdKey] = { avgViews, urls: posts.map(x => x.url).filter(Boolean) };
    }

    const map = { 'tt-profile': 'tt_profiles_stage1.json', 'tt-posts': 'tt_profiles.json', 'ig-profile': 'ig_profiles.json', 'ig-posts': 'ig_posts.json' };
    for (const { kind, items } of [...stage1Results, ...stage2Results]) {
      fs.writeFileSync(path.join(DATA_DIR, map[kind]), JSON.stringify(items));
      stage2DatasetMap[kind] = items;
    }
  }

  // === STAGE 3: ⚠️ 评论检查 ===
  const warnList = Object.entries(results).filter(([, r]) => r._pendingComments).map(([k]) => k);
  if (SKIP_COMMENTS) {
    for (const k of warnList) {
      results[k].verdict = '⚠️ 需人工核查';
      results[k].reason = '跳过评论检查（需人工判定地区）';
    }
  }
  if (warnList.length > 0 && !SKIP_COMMENTS) {
    console.log(`\n=== STAGE 3: ⚠️ 评论检查（${warnList.length} 人）===`);
    const ttWarn = warnList.filter(k => k.startsWith('TT:')).map(k => k.slice(3));
    const igWarn = warnList.filter(k => k.startsWith('IG:')).map(k => k.slice(3));
    const stage3 = [];
    if (ttWarn.length > 0) {
      const urls = ttWarn.flatMap(u => (survivorMeta[`TT:${u}`]?.urls || []).slice(0, POSTS_LIMIT));
      console.log(`  → TT thescrapelab ${urls.length} videos × ${COMMENTS_PER_POST} 评论 (${ttWarn.length} 人)`);
      stage3.push(startActor('thescrapelab/tiktok-comments-scraper', {
        videoUrls: urls, maxCommentsPerVideo: COMMENTS_PER_POST, includeReplies: false,
      }).then(async ({ runId, datasetId }) => ({ kind: 'tt-comments', items: (await waitForRun(runId), await fetchDataset(datasetId)) })));
    }
    if (igWarn.length > 0) {
      const urls = igWarn.flatMap(u => (survivorMeta[`IG:${u}`]?.urls || []).slice(0, POSTS_LIMIT));
      console.log(`  → IG instagram-comment-scraper ${urls.length} posts × ${COMMENTS_PER_POST} 评论 (${igWarn.length} 人)`);
      stage3.push(startActor('apify/instagram-comment-scraper', {
        directUrls: urls, resultsLimit: COMMENTS_PER_POST,
      }).then(async ({ runId, datasetId }) => ({ kind: 'ig-comments', items: (await waitForRun(runId), await fetchDataset(datasetId)) })));
    }
    const stage3Results = await Promise.all(stage3);

    // 分析评论
    const ttCommentsByUser = {}, igCommentsByUser = {};
    for (const { kind, items } of stage3Results) {
      fs.writeFileSync(path.join(DATA_DIR, kind === 'tt-comments' ? 'tt_comments.json' : 'ig_comments.json'), JSON.stringify(items));
      if (kind === 'tt-comments') {
        // 用 thescrapelab 自带 language 字段（如果有）；没有的回退到 detectCommentLang
        for (const c of items) {
          if (!c.video_url || !c.text) continue;
          const m = c.video_url.match(/@([^/]+)\//);
          if (!m) continue;
          const user = m[1];
          if (!ttWarn.includes(user)) continue;
          const s = ttCommentsByUser[user] = ttCommentsByUser[user] || { de: 0, en: 0, total: 0 };
          s.total++;
          const lang = c.language || detectCommentLang(c.text);
          if (lang === 'de') s.de++;
          else if (lang === 'en') s.en++;
        }
      } else {
        // 用 ig_posts.json url→ownerUsername 映射
        const urlToOwner = {};
        const igPosts = stage2DatasetMap['ig-posts'] || [];
        for (const p of igPosts) if (p.url) urlToOwner[p.url] = p.ownerUsername;
        for (const c of items) {
          if (!c.postUrl || !c.text) continue;
          const user = urlToOwner[c.postUrl];
          if (!user || !igWarn.includes(user)) continue;
          const s = igCommentsByUser[user] = igCommentsByUser[user] || { de: 0, en: 0, total: 0 };
          s.total++;
          const lang = detectCommentLang(c.text);
          if (lang === 'de') s.de++;
          else if (lang === 'en') s.en++;
        }
      }
    }

    // 用评论结果二次判定
    for (const k of warnList) {
      const platform = k.slice(0, 2);
      const user = k.slice(3);
      const p = platform === 'TT' ? ttProfiles[user] : igProfiles[user];
      const stats = platform === 'TT' ? ttCommentsByUser[user] : igCommentsByUser[user];
      const meta = survivorMeta[k];
      const dePct = stats && (stats.de + stats.en) > 0 ? Math.round(stats.de * 100 / (stats.de + stats.en)) : null;
      const j = finalizeWithComments(p, meta.avgViews, dePct);
      const existing = results[k];
      results[k] = { platform, name: user, fans: p.fans, posts: p.posts, ...j, avgViews: meta.avgViews, genderFemale: existing?.genderFemale ?? null, commercialStats: existing?.commercialStats ?? null };
      const statSummary = stats ? `(de=${stats.de}, en=${stats.en}, total=${stats.total})` : '(无评论数据)';
      console.log(`   ${k}: 评论 ${dePct ?? '?'}% ${statSummary} → ${j.verdict}`);
    }
  }

  // 清掉 _pendingComments 标记（如果还有）
  for (const k of Object.keys(results)) delete results[k]._pendingComments;

  // 商单复查：✅ 但近3月无商单 → 改为 🟡 复查
  for (const k of Object.keys(results)) {
    const r = results[k];
    if (r.verdict === '✅ 是' && r.commercialStats && r.commercialStats.total === 0) {
      r.verdict = '🟡 复查';
      r.reason = '其他条件通过但近3月无商单';
    }
  }

  // === 输出表 ===
  console.log('\n=== 最终判定（按粘贴顺序）===\n');
  const header = '| # | 平台 | 用户名 | 粉丝数量 | 帖数 | 地区是否准确 | 近三月平均浏览量 | 女粉占比 | 近3月商单 | 是否合适 | 原因 |';
  const sep = '|---|------|--------|---------|------|-------------|-----------------|---------|---------|---------|------|';
  const rows = inputOrder.map((u, i) => {
    const r = results[`${u.platform}:${u.username}`];
    if (!r) return `| ${i + 1} | ${u.platform} | ${u.username} | - | - | - | - | - | - | ⚠️ 抓取失败 | - |`;
    const fansStr = r.fans == null ? '-' : r.fans.toLocaleString();
    const postsStr = r.posts == null ? '-' : r.posts;
    const viewsStr = r.avgViews == null ? '-' : r.avgViews.toLocaleString();
    const genderStr = r.genderFemale != null ? `${r.genderFemale}%` : '无信息';
    const commercialStr = formatCommercialStats(r.commercialStats);
    return `| ${i + 1} | ${r.platform} | ${r.name} | ${fansStr} | ${postsStr} | ${r.regionAccurate} | ${viewsStr} | ${genderStr} | ${commercialStr} | ${r.verdict} | ${r.reason} |`;
  });
  const stats = {};
  for (const k of Object.keys(results)) stats[results[k].verdict] = (stats[results[k].verdict] || 0) + 1;
  const statsLines = Object.entries(stats).map(([k, v]) => `- ${k}: ${v}`);

  const table = [header, sep, ...rows].join('\n');
  console.log(table);
  console.log('\n=== 统计 ===');
  for (const l of statsLines) console.log(l);

  // === 存档 ===
  const datestamp = new Date().toISOString().slice(0, 10);
  let fileNum = 1, filePath;
  while (true) {
    filePath = path.join(RESULTS_DIR, `${datestamp}_batch${inputOrder.length}_${fileNum}.md`);
    if (!fs.existsSync(filePath)) break;
    fileNum++;
  }
  const totalUsd = await reportCost();
  const fileContent = [
    `# ${datestamp} 批次 (${inputOrder.length} URL / 去重 ${uniqueTT.length}TT+${uniqueIG.length}IG)`,
    '',
    `> 规则: v0.5 Wednesday 集成 (caption ${CAPTION_THRESHOLD}% / 评论 ${COMMENT_THRESHOLD}% / 男粉≤${GENDER_MALE_MAX}% or >100K≤${GENDER_MALE_MAX_100K}%)`,
    `> 抓取量: ${POSTS_LIMIT} posts/videos per survivor (短路淘汰 ${uniqueTT.length - ttSurvivors.length + uniqueIG.length - igSurvivors.length}/${uniqueTT.length + uniqueIG.length})`,
    warnList.length > 0 ? `> STAGE 3 评论检查: ${warnList.length} 人` : `> STAGE 3 评论检查: 无 ⚠️，跳过`,
    `> Apify 成本: $${totalUsd.toFixed(4)} (~¥${(totalUsd * USD_TO_CNY).toFixed(2)})`,
    '',
    '## 最终判定表',
    '',
    table,
    '',
    '## 统计',
    '',
    ...statsLines,
  ].join('\n') + '\n';
  fs.writeFileSync(filePath, fileContent);
  console.log(`\n✓ 存档到 ${filePath}`);
}

main().catch(e => {
  console.error('\n❌ 错误:', e.message);
  process.exit(1);
});
