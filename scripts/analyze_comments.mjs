/**
 * 评论语言占比分析（v0.4 规则 ②）
 *
 * 输入（放在 ./data/）：
 *   - tt_comments.json   thescrapelab/tiktok-comments-scraper 输出
 *   - ig_comments.json   apify/instagram-comment-scraper 输出
 *   - ig_posts.json      apify/instagram-post-scraper 输出（用来映射 postUrl → ownerUsername）
 *
 * 输出：每个达人的评论 de/en/un 分布 + 德语占比
 *
 * 运行：node scripts/analyze_comments.mjs
 */

import fs from 'fs';

const DATA_DIR = './data';

// === 德语启发式（用于 IG 评论。TT 评论用 actor 自带 language 字段）===
const germanWords = new Set([
  'ich','ist','das','die','der','den','dem','des','mit','und','auf','ein','eine','einen','oder','was','wie',
  'sind','haben','aber','auch','nicht','nur','wenn','sich','dass','sie','für','mein','meine','meinen','kann',
  'mehr','noch','mal','so','aus','zu','von','als','bei','zur','beim','ihr','euch','wir','heute','immer','ihre',
  'wer','wo','warum','wieso','vom','zum','dich','wird','schon','dann','jetzt','wieder','sehr','viel','danke',
  'liebe','herz','leben','alle','allen','alles','man','mir','dir','bin','bist','war','am','im','um','ohne',
  'nach','vor','ganz','kein','damit','weil','denn','seid','seit','dabei','hier','dort','schön','gut','toll',
  'super','prima','wow','wunderschön','klasse','geil','mega','traum','süß','hübsch','wahnsinn','schöne','schönen',
  'steht','liebs','hübsche','herzlichen','glückwunsch','geburtstag','herzlich','liebsten','gerne','wirklich',
  'natürlich','sicher','definitiv','wunder','girlie','girls','freue','meine','seine','keine','keinen','keiner',
  'manche','viele','wenige','letzte','letzten','erste','ersten','zweite','dritte','morgen','gestern','vorhin',
  'damals','niemals','sofort','manchmal','irgendwann','niemand','jemand','etwas','nichts','etwa','ungefähr',
  'sogar','jedoch','trotzdem','obwohl','während','wegen','aufgrund','außer','außerdem','allerdings','dennoch',
  'demnach','folglich','schließlich','endlich','vielen','vielleicht','klar','sicherlich','garantiert',
  'wahrscheinlich','möglicherweise','eventuell','daß','falls','wann','weshalb','wozu','wofür','womit','wodurch',
  'wieviel','sympathischer','wunderwunderwunderschön','allahumma','barik','mashalla','mashallah','engelchen',
  'wunderschönes','wunderschöne','wunderschönen','barfuß'
]);

const englishWords = new Set([
  'the','and','you','with','is','of','for','it','this','that','have','are','was','were','my','be','on','at','in',
  'to','a','an','me','we','they','their','them','these','those','just','so','what','where','when','why','how',
  'do','does','did','can','could','should','would','will','today','always','never','very','much','many','about',
  'out','over','under','from','some','any','all','no','yes','one','two','three','your','his','her','its','him',
  'she','he','i','love','like','life','girl','boy','people','friend','family','mom','dad','sister','brother',
  'new','old','look','feel','feeling','wow','omg','queen','king','vibes','aesthetic','iconic','obsessed','beautiful',
  'gorgeous','cute','amazing','perfect','best','nice','really','actually','probably','maybe','sweet','beauty','dream',
  'dreamy','stunning','adore','adorable','fabulous','peace','peaceful','angel','paradise','found','keep','taking',
  'heart','word','same','yesss','outfit','style','fit','obsess','pretty','prettyy','loveee','lovely','beauté',
  'magnifique','please'
]);

function detectLang(text) {
  if (!text) return 'unknown';
  const t = text.trim();
  if (t.length < 2) return 'unknown';
  const lower = t.toLowerCase();
  if (/^[\W_\s]+$/.test(lower)) return 'unknown'; // emoji/symbol only
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

function loadJSON(path) {
  if (!fs.existsSync(path)) {
    console.warn(`(跳过) 找不到 ${path}`);
    return null;
  }
  const raw = JSON.parse(fs.readFileSync(path, 'utf-8'));
  return raw.items || raw;
}

// === 处理 TT 评论（actor 自带 language 字段）===
const ttData = loadJSON(`${DATA_DIR}/tt_comments.json`);
if (ttData) {
  const ttCommentsByUser = {};
  for (const c of ttData) {
    if (!c.video_url || !c.text || c.text.trim().length < 2) continue;
    const m = c.video_url.match(/@([^/]+)\//);
    if (!m) continue;
    const user = m[1];
    if (!ttCommentsByUser[user]) ttCommentsByUser[user] = { de: 0, en: 0, un: 0, other: 0, total: 0 };
    ttCommentsByUser[user].total++;
    const lang = c.language;
    if (lang === 'de') ttCommentsByUser[user].de++;
    else if (lang === 'en') ttCommentsByUser[user].en++;
    else if (!lang || lang === 'un') ttCommentsByUser[user].un++;
    else ttCommentsByUser[user].other++;
  }

  console.log('=== TT 评论分布 ===');
  for (const [user, s] of Object.entries(ttCommentsByUser)) {
    const denom = s.de + s.en;
    const dePct = denom > 0 ? Math.round(s.de * 100 / denom) : null;
    const pass = dePct !== null && dePct >= 60 ? '✅' : (dePct === null ? '⚠️ 无定论' : '❌');
    console.log(`${user}: total=${s.total}, de=${s.de}, en=${s.en}, un=${s.un}, other=${s.other} → 德语%=${dePct}% ${pass}`);
  }
}

// === 处理 IG 评论（用 ig_posts.json 映射 postUrl → ownerUsername）===
const igComments = loadJSON(`${DATA_DIR}/ig_comments.json`);
const igPosts = loadJSON(`${DATA_DIR}/ig_posts.json`);
if (igComments && igPosts) {
  // 映射：postUrl → ownerUsername
  const urlToOwner = {};
  for (const post of igPosts) {
    if (post.url) urlToOwner[post.url] = post.ownerUsername;
  }

  const igCommentsByUser = {};
  for (const c of igComments) {
    if (!c.postUrl || !c.text) continue;
    const user = urlToOwner[c.postUrl];
    if (!user) continue;
    if (!igCommentsByUser[user]) igCommentsByUser[user] = { de: 0, en: 0, un: 0, total: 0 };
    igCommentsByUser[user].total++;
    const lang = detectLang(c.text);
    if (lang === 'de') igCommentsByUser[user].de++;
    else if (lang === 'en') igCommentsByUser[user].en++;
    else igCommentsByUser[user].un++;
  }

  console.log('\n=== IG 评论分布 ===');
  for (const [user, s] of Object.entries(igCommentsByUser)) {
    const denom = s.de + s.en;
    const dePct = denom > 0 ? Math.round(s.de * 100 / denom) : null;
    const pass = dePct !== null && dePct >= 60 ? '✅' : (dePct === null ? '⚠️ 无定论' : '❌');
    console.log(`${user}: total=${s.total}, de=${s.de}, en=${s.en}, un=${s.un} → 德语%=${dePct}% ${pass}`);
  }
}
