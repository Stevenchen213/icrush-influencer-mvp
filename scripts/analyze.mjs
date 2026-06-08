/**
 * ICRUSH 达人筛选 v0.4 主分析脚本
 *
 * 输入（放在 ./data/）：
 *   - tt_profiles.json   clockworks/tiktok-profile-scraper 输出（数组形式 items[]）
 *   - ig_profiles.json   apify/instagram-profile-scraper 输出（数组形式 items[]）
 *   - ig_posts.json      apify/instagram-post-scraper 输出（数组形式 items[]）
 *
 * 输出：stdout 打印 markdown 表 + 统计
 *
 * 运行：node scripts/analyze.mjs
 */

import fs from 'fs';

const DATA_DIR = './data';
const ttFile = `${DATA_DIR}/tt_profiles.json`;
const igProfilesFile = `${DATA_DIR}/ig_profiles.json`;
const igPostsFile = `${DATA_DIR}/ig_posts.json`;

// 3 个月前作为"近三月"边界 —— 跑时改成今天往前 90 天
const threeMonthsAgo = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000);

// === 德语启发式检测（用于 IG caption，TT 用 actor 自带 textLanguage 字段）===
const germanWords = new Set([
  'ich','ist','das','die','der','den','dem','des','mit','und','auf','ein','eine','einen','oder','was','wie',
  'sind','haben','aber','auch','nicht','nur','wenn','sich','dass','sie','für','mein','meine','meinen','kann',
  'mehr','noch','mal','so','aus','zu','von','als','bei','zur','beim','ihr','euch','wir','heute','immer','ihre',
  'ihren','wer','wo','warum','wieso','vom','zum','dich','nichts','etwas','keine','wird','würde','schon','dann',
  'jetzt','wieder','sehr','viel','viele','vielen','danke','liebe','herz','leben','alle','allen','allem','alles',
  'man','mir','dir','bin','bist','war','waren','am','im','um','wegen','ohne','nach','vor','ganz','kein','damit',
  'weil','denn','seid','seit','dabei','dazu','hier','dort','einmal','zwischen','endlich','während','solange',
  'obwohl','trotzdem','vielleicht','gerne','genau','wirklich','niemals','morgen','gestern','übermorgen',
  'gut','besser','beste','schön','schöne','toll','super','prima','klasse','okay','euer','eure','mädchen','jungs',
  'frauen','männer','leute','menschen','freunde','familie','mama','papa','tochter','sohn','schwester','bruder',
  'neu','neue','neues','alt','alte','altes','jung','junge','erste','zweite','dritte','letzte','geht','kommt',
  'machen','machte','gemacht','tun','tat','getan','sagen','sagte','gesagt','sehen','sah','gesehen','wollen',
  'wollte','gewollt','müssen','musste','gemusst','sollen','sollte','gesollt','dürfen','durfte','gedurft',
  'hätte','könnte','wäre','würde','willst','wirst','werden','werde','wurde','ihm','ihn','ihnen','ihres','ihrer',
  'seine','seiner','seines','unser','unsere','mode','schmuck','outfit','look','herzlich','liebsten','aknesafe',
  'akne','abspeichern','kanzlei','notar','notarin','rechtswahl','testament','beitrag','infos','rechtlichen',
  'wusstet','jedem','tag','chance','schönste','lebens','girlie','girl','schauspielerin','willkommen','probiert',
  'prinzessin','königin'
]);

const englishWords = new Set([
  'the','and','you','with','is','of','for','it','this','that','have','are','was','were','my','be','on','at','in',
  'to','a','an','me','we','they','their','them','these','those','just','so','what','where','when','why','how',
  'do','does','did','can','could','should','would','will','today','always','never','very','much','many','about',
  'out','over','under','from','some','any','all','no','yes','one','two','three','your','his','her','its','him',
  'she','he','i','love','like','life','girl','boy','people','friend','family','mom','dad','sister','brother',
  'new','old','young','first','last','make','said','say','see','want','need','must','should','happy','sad',
  'beautiful','cute','amazing','perfect','best','better','good','great','nice','really','actually','definitely',
  'probably','maybe','sometimes','recipe','dress','jewelry','look','feel','feeling','tips','outfits','content',
  'sharing','wearing','things','agenda','cleaning','streets','viennese','baby','girls','boys','women','men'
]);

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

// === 地区检测（DE/AT 城市）===
const austrianCities = ['wien','vienna','salzburg','graz','innsbruck','linz','klagenfurt','tirol','tyrol','österreich','austria'];
const germanCityList = ['berlin','münchen','munich','hamburg','köln','cologne','frankfurt','stuttgart','düsseldorf','dusseldorf','dortmund','bremen','hannover','hanover','leipzig','dresden','nürnberg','nuremberg','duisburg','bochum','wuppertal','bielefeld','mannheim','karlsruhe','wiesbaden','bonn','münster','augsburg','aachen','germany','deutschland'];
const germanCityAbbr = ['cgn','muc','ber','fra','dus'];

function detectRegion(bioText) {
  if (!bioText) return null;
  const lower = bioText.toLowerCase();
  for (const c of austrianCities) {
    if (new RegExp('\\b' + c + '\\b').test(lower)) return { region: 'AT', city: c };
  }
  for (const c of germanCityList) {
    if (new RegExp('\\b' + c + '\\b').test(lower)) return { region: 'DE', city: c };
  }
  for (const c of germanCityAbbr) {
    if (new RegExp('\\b' + c + '\\b').test(lower)) return { region: 'DE', city: c };
  }
  return null;
}

// === 职业检测（v0.4 新增 - 规则 5）===
function detectOccupation(bio, category) {
  const text = ((bio || '') + ' ' + (category || '')).toLowerCase();
  // Lawyer 信号
  if (/\b(lawyer|attorney|anwalt|anwältin|anwalts|notar|notarin|rechtsanwalt|rechtsanwältin|kanzlei|advokat)\b/.test(text)) return 'Lawyer';
  // Artist 信号
  if (/(category|categoryname).*artist/.test(text)) return 'Artist';
  if (/,artist|^artist|\bartist\b/.test(text)) {
    if ((category || '').toLowerCase().split(/[,\s]+/).includes('artist')) return 'Artist';
  }
  if (/\b(künstler|künstlerin|maler|malerin|bildhauer|skulptur|schauspielerin|schauspieler)\b/.test(text)) return 'Artist';
  return null;
}

// === 加载数据 ===
function loadJSON(path) {
  if (!fs.existsSync(path)) {
    console.error(`错误：找不到 ${path}`);
    console.error('请先用 Apify 抓数据放到 data/ 目录');
    process.exit(1);
  }
  const raw = JSON.parse(fs.readFileSync(path, 'utf-8'));
  return raw.items || raw;  // 兼容 {items:[]} 和直接的数组
}

// === 处理 TT ===
const ttItems = loadJSON(ttFile);
const ttProfiles = {};
for (const v of ttItems) {
  const name = v['authorMeta.name'] || v.authorMeta?.name;
  if (!name) continue;
  if (!ttProfiles[name]) {
    ttProfiles[name] = {
      name,
      fans: v['authorMeta.fans'] || v.authorMeta?.fans,
      videos: v['authorMeta.video'] || v.authorMeta?.video,
      bio: v['authorMeta.signature'] || v.authorMeta?.signature || '',
      private: v['authorMeta.privateAccount'] || v.authorMeta?.privateAccount,
      category: v['authorMeta.commerceUserInfo.category'] || v.authorMeta?.commerceUserInfo?.category || null,
      posts: []
    };
  }
  ttProfiles[name].posts.push({
    lang: v.textLanguage,
    createTime: v.createTimeISO,
    playCount: v.playCount || 0,
  });
}

const ttResults = Object.values(ttProfiles).map(p => {
  const total = p.posts.length;
  // ⚠️ 关键 bug 修复：只算 de+en 作为分母，排除 un/无文字 emoji 视频
  const deCount = p.posts.filter(x => x.lang === 'de').length;
  const enCount = p.posts.filter(x => x.lang === 'en').length;
  const langDenom = deCount + enCount;
  const dePct = langDenom > 0 ? Math.round(deCount * 100 / langDenom) : null;
  const recent = p.posts.filter(x => new Date(x.createTime) > threeMonthsAgo);
  const avgViews = recent.length > 0 ? Math.round(recent.reduce((s, x) => s + x.playCount, 0) / recent.length) : 0;
  return {
    platform: 'TT', name: p.name, fans: p.fans, posts: p.videos,
    dePct, avgViews,
    region: detectRegion(p.bio),
    occupation: detectOccupation(p.bio, p.category),
    private: p.private
  };
});

// === 处理 IG ===
const igProfiles = loadJSON(igProfilesFile);
const igPostItems = loadJSON(igPostsFile);

// 把 IG 帖子按 owner 分组
const igPostsByUser = {};
for (const post of igPostItems) {
  const name = post.ownerUsername;
  if (!name) continue;
  if (!igPostsByUser[name]) igPostsByUser[name] = [];
  igPostsByUser[name].push(post);
}

const igResults = igProfiles.map(profile => {
  const username = profile.username;
  const posts = igPostsByUser[username] || [];

  // 语言判定（启发式：apify IG actor 不返回 textLanguage 字段）
  const captions = posts.filter(p => p.caption && p.caption.trim().length > 5);
  let g = 0, e = 0;
  for (const post of captions) {
    const lang = detectLang(post.caption);
    if (lang === 'de') g++;
    else if (lang === 'en') e++;
  }
  const analyzed = g + e;
  const dePct = analyzed > 0 ? Math.round(g * 100 / analyzed) : null;

  // 近 3 月视频平均浏览
  const recentVideos = posts.filter(p =>
    (p.type === 'Video' || (p.videoPlayCount && p.videoPlayCount > 0)) &&
    p.timestamp && new Date(p.timestamp) > threeMonthsAgo
  );
  let avgViews = 0;
  if (recentVideos.length > 0) {
    const views = recentVideos.map(p => p.videoPlayCount || p.videoViewCount || 0);
    avgViews = Math.round(views.reduce((s, v) => s + v, 0) / views.length);
  }

  return {
    platform: 'IG', name: username,
    fans: profile.followersCount,
    posts: profile.postsCount,
    dePct, avgViews,
    region: detectRegion(profile.biography || ''),
    occupation: detectOccupation(profile.biography || '', profile.businessCategoryName),
    private: profile.private
  };
});

// === 应用规则 v0.4 ===
function judge(r) {
  const isTT = r.platform === 'TT';

  // Step 1: 职业（直接 PASS）
  if (r.occupation) {
    return { verdict: '❌ 否', reason: `职业=${r.occupation}（直接PASS）`, regionAccurate: r.region ? '是' : '-' };
  }

  // Step 2: 私密
  if (r.private) {
    return { verdict: '❌ 否', reason: '私密账户', regionAccurate: '-' };
  }

  // Step 3: 帖数
  if (r.posts < 200) {
    return { verdict: '❌ 否', reason: `帖数${r.posts}<200`, regionAccurate: r.region ? '是' : '-' };
  }

  // Step 4: 粉丝边界
  const fanMax = isTT ? 500000 : 300000;
  if (r.fans < 1000) {
    return { verdict: '❌ 否', reason: `粉丝${r.fans}<1K`, regionAccurate: r.region ? '是' : '-' };
  }
  if (r.fans > fanMax) {
    return { verdict: '❌ 否', reason: `粉丝${r.fans}>${fanMax}`, regionAccurate: r.region ? '是' : '-' };
  }
  const isReplaceByFans = r.fans < 10000;

  // Step 5: 地区 + 语言
  let regionAccurate;
  let langStatus;
  if (r.region) {
    if (r.region.region === 'DE' || r.region.region === 'AT') {
      regionAccurate = '是';
      const langPass = r.dePct !== null && r.dePct >= 70;
      langStatus = langPass ? 'pass' : 'need-comments';
    } else {
      return { verdict: '❌ 否', reason: `bio地区${r.region.region}非DE/AT`, regionAccurate: '否' };
    }
  } else {
    regionAccurate = '-';
    const langPass = r.dePct !== null && r.dePct >= 70;
    if (langPass) {
      langStatus = 'pass';
    } else {
      return { verdict: '❌ 否', reason: `bio无地区+语言${r.dePct ?? '?'}%<70%`, regionAccurate: '-' };
    }
  }

  if (langStatus === 'need-comments') {
    const extra = isReplaceByFans ? `；粉丝${r.fans}<10K（如评论通过则置换组）` : '';
    return { verdict: '⚠️ 需人工核查', reason: `语言${r.dePct ?? '?'}%<70% 但bio在${r.region.region} → 需调评论API${extra}`, regionAccurate };
  }

  // Step 6: 平均浏览
  let viewStatus;
  if (r.avgViews >= 4000) viewStatus = 'pass';
  else if (r.avgViews >= 2000) viewStatus = 'replace';
  else viewStatus = 'fail';

  if (viewStatus === 'fail') {
    return { verdict: '❌ 否', reason: `近3月平均浏览${r.avgViews.toLocaleString()}<2000`, regionAccurate };
  }

  if (isReplaceByFans || viewStatus === 'replace') {
    const r1 = [];
    if (isReplaceByFans) r1.push(`粉丝${r.fans}<10K`);
    if (viewStatus === 'replace') r1.push(`平均浏览${r.avgViews.toLocaleString()}在2000-4000`);
    return { verdict: '🟡 置换组', reason: r1.join('; '), regionAccurate };
  }

  return { verdict: '✅ 是', reason: '-', regionAccurate };
}

// === 输出 ===
const allResults = [...ttResults, ...igResults].map(r => ({ ...r, ...judge(r) }));
const order = { '✅ 是': 1, '⚠️ 需人工核查': 2, '🟡 置换组': 3, '❌ 否': 4 };
allResults.sort((a, b) => order[a.verdict] - order[b.verdict]);

console.log('| 平台 | 用户名 | 粉丝数量 | 帖数 | 地区是否准确 | 近三月平均浏览量 | 是否合适 | 原因 |');
console.log('|------|--------|---------|------|-------------|-----------------|---------|------|');
for (const r of allResults) {
  console.log(`| ${r.platform} | ${r.name} | ${(r.fans || 0).toLocaleString()} | ${r.posts || '?'} | ${r.regionAccurate} | ${r.avgViews.toLocaleString()} | ${r.verdict} | ${r.reason} |`);
}

const stats = {};
for (const r of allResults) {
  stats[r.verdict] = (stats[r.verdict] || 0) + 1;
}
console.log('\n=== 统计 ===');
console.log(JSON.stringify(stats, null, 2));
