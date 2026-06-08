#!/usr/bin/env node
/**
 * 完整批量判定流水线（v0.4 微调阈值 50%/60%）
 *
 * 优化点（vs 手动跑）：
 * 1. profile-first 短路：先抓 profile metadata（cheap），帖数<200 / 职业=艺术家律师 / 私密 直接 PASS，不抓 posts/videos
 * 2. TT 用 clockworks resultsPerPage=1 拿 profile，再 resultsPerPage=20 抓 survivors 的视频
 * 3. IG 直接用 detailedData（含 videoPlayCount），不浪费 basicData 重跑
 * 4. 抓 20 条（符合 v0.4 微调"近 20 条"规则），不是 30
 * 5. 输出按用户粘贴顺序（保留重复行）
 * 6. 自动存 data/ 和 results/<date>_batch<N>_<seq>.md
 * 7. 末尾打印真实 Apify 成本（USD + ¥ ≈）
 *
 * 用法：
 *   node --env-file=.env scripts/run_batch.mjs data/input.txt
 *   或: echo "https://www.instagram.com/x/" | node --env-file=.env scripts/run_batch.mjs -
 *
 * 输入文件格式：每行一个 profile URL
 *   https://www.instagram.com/<username>/
 *   https://www.tiktok.com/@<username>
 */

import fs from 'fs';
import path from 'path';

// === 常量（v0.4 微调） ===
const TOKEN = process.env.APIFY_TOKEN;
if (!TOKEN) throw new Error('APIFY_TOKEN 未设置（用 --env-file=.env）');

const CAPTION_THRESHOLD = 50;
const COMMENT_THRESHOLD = 60;
const POSTS_LIMIT = 20;
const POSTS_MIN = 200;
const FAN_MIN = 1000;
const FAN_MAX = { TT: 500000, IG: 300000 };
const FAN_REPLACE = 10000;
const VIEW_REPLACE = 2000;
const VIEW_OK = 4000;
const THREE_MONTH_MS = 90 * 24 * 60 * 60 * 1000;
const USD_TO_CNY = 7.25;

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

// === Apify API ===
const apifyRuns = []; // 收集所有 runId 用于末尾算成本

async function startActor(actor, input) {
  const url = `https://api.apify.com/v2/acts/${actor.replace('/', '~')}/runs?token=${TOKEN}`;
  const r = await fetch(url, {
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
    const r = await fetch(`https://api.apify.com/v2/actor-runs/${runId}?token=${TOKEN}`);
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
  const r = await fetch(url);
  if (!r.ok) throw new Error(`fetchDataset(${datasetId}): HTTP ${r.status}`);
  return await r.json();
}

// === 语言检测（与 analyze.mjs 同步） ===
const germanWords = new Set('ich,ist,das,die,der,den,dem,des,mit,und,auf,ein,eine,einen,oder,was,wie,sind,haben,aber,auch,nicht,nur,wenn,sich,dass,sie,für,mein,meine,meinen,kann,mehr,noch,mal,so,aus,zu,von,als,bei,zur,beim,ihr,euch,wir,heute,immer,ihre,ihren,wer,wo,warum,wieso,vom,zum,dich,nichts,etwas,keine,wird,würde,schon,dann,jetzt,wieder,sehr,viel,viele,vielen,danke,liebe,herz,leben,alle,allen,allem,alles,man,mir,dir,bin,bist,war,waren,am,im,um,wegen,ohne,nach,vor,ganz,kein,damit,weil,denn,seid,seit,dabei,dazu,hier,dort,einmal,zwischen,endlich,während,solange,obwohl,trotzdem,vielleicht,gerne,genau,wirklich,niemals,morgen,gestern,übermorgen,gut,besser,beste,schön,schöne,toll,super,prima,klasse,okay,euer,eure,mädchen,jungs,frauen,männer,leute,menschen,freunde,familie,mama,papa,tochter,sohn,schwester,bruder,neu,neue,neues,alt,alte,altes,jung,junge,erste,zweite,dritte,letzte,geht,kommt,machen,machte,gemacht,tun,tat,getan,sagen,sagte,gesagt,sehen,sah,gesehen,wollen,wollte,gewollt,müssen,musste,gemusst,sollen,sollte,gesollt,dürfen,durfte,gedurft,hätte,könnte,wäre,würde,willst,wirst,werden,werde,wurde,ihm,ihn,ihnen,ihres,ihrer,seine,seiner,seines,unser,unsere,mode,schmuck,outfit,look,herzlich,liebsten,aknesafe,akne,abspeichern,kanzlei,notar,notarin,rechtswahl,testament,beitrag,infos,rechtlichen,wusstet,jedem,tag,chance,schönste,lebens,girlie,girl,schauspielerin,willkommen,probiert,prinzessin,königin'.split(','));

const englishWords = new Set('the,and,you,with,is,of,for,it,this,that,have,are,was,were,my,be,on,at,in,to,a,an,me,we,they,their,them,these,those,just,so,what,where,when,why,how,do,does,did,can,could,should,would,will,today,always,never,very,much,many,about,out,over,under,from,some,any,all,no,yes,one,two,three,your,his,her,its,him,she,he,i,love,like,life,girl,boy,people,friend,family,mom,dad,sister,brother,new,old,young,first,last,make,said,say,see,want,need,must,should,happy,sad,beautiful,cute,amazing,perfect,best,better,good,great,nice,really,actually,definitely,probably,maybe,sometimes,recipe,dress,jewelry,look,feel,feeling,tips,outfits,content,sharing,wearing,things,agenda,cleaning,streets,viennese,baby,girls,boys,women,men'.split(','));

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

// === 短路（profile-only 数据足够判定的条件） ===
function shortCircuit(platform, p) {
  if (p.occupation) return { fail: true, reason: `职业=${p.occupation === 'Lawyer' ? '律师' : '艺术家'}（直接 PASS）` };
  if (p.private) return { fail: true, reason: '私密账户' };
  if (p.posts < POSTS_MIN) return { fail: true, reason: `帖数 ${p.posts}<${POSTS_MIN}` };
  if (p.fans < FAN_MIN) return { fail: true, reason: `粉丝 ${p.fans}<1K` };
  if (p.fans > FAN_MAX[platform]) return { fail: true, reason: `粉丝 ${p.fans.toLocaleString()}>${FAN_MAX[platform].toLocaleString()}` };
  if (p.region && p.region.region !== 'DE' && p.region.region !== 'AT') {
    return { fail: true, reason: `bio 地区 ${p.region.region} 非 DE/AT` };
  }
  return { fail: false };
}

// === 完整判定（含 caption + avgViews）===
function judge(platform, p, dePct, avgViews) {
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
    if (dePct !== null && dePct >= CAPTION_THRESHOLD) langStatus = 'pass';
    else return { verdict: '❌ 否', reason: `bio 无地区 + 语言 ${dePct ?? '?'}%<${CAPTION_THRESHOLD}%`, regionAccurate };
  }
  if (langStatus === 'need-comments') {
    const extra = isReplaceByFans ? `；粉丝 ${p.fans}<10K（如评论通过则置换组）` : '';
    return { verdict: '⚠️ 需人工核查', reason: `caption ${dePct}%<${CAPTION_THRESHOLD}% 但 bio 在 ${p.region.region} → 需调评论 API${extra}`, regionAccurate };
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
      const r = await fetch(`https://api.apify.com/v2/actor-runs/${id}?token=${TOKEN}`);
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

  // === STAGE 1: profile metadata ===
  console.log('\n=== STAGE 1: profile metadata（短路用）===');
  const stage1 = [];
  if (uniqueTT.length > 0) {
    console.log(`  → TT clockworks profile-only (resultsPerPage=1) ×${uniqueTT.length}`);
    stage1.push(startActor('clockworks/tiktok-profile-scraper', {
      profiles: uniqueTT,
      profileScrapeSections: ['videos'],
      profileSorting: 'latest',
      resultsPerPage: 1,
      shouldDownloadAvatars: false, shouldDownloadCovers: false,
      shouldDownloadSlideshowImages: false, shouldDownloadVideos: false,
    }).then(async ({ runId, datasetId }) => {
      await waitForRun(runId);
      return { kind: 'tt-profile', items: await fetchDataset(datasetId) };
    }));
  }
  if (uniqueIG.length > 0) {
    console.log(`  → IG profile-scraper ×${uniqueIG.length}`);
    stage1.push(startActor('apify/instagram-profile-scraper', { usernames: uniqueIG }).then(async ({ runId, datasetId }) => {
      await waitForRun(runId);
      return { kind: 'ig-profile', items: await fetchDataset(datasetId) };
    }));
  }
  const stage1Results = await Promise.all(stage1);

  // 解析 profile
  const ttProfiles = {}, igProfiles = {};
  for (const { kind, items } of stage1Results) {
    if (kind === 'tt-profile') {
      for (const v of items) {
        const name = v['authorMeta.name'] || v.authorMeta?.name;
        if (!name || ttProfiles[name]) continue;
        const bio = v['authorMeta.signature'] || v.authorMeta?.signature || '';
        const category = v['authorMeta.commerceUserInfo.category'] || v.authorMeta?.commerceUserInfo?.category || null;
        ttProfiles[name] = {
          name,
          fans: v['authorMeta.fans'] || v.authorMeta?.fans || 0,
          posts: v['authorMeta.video'] || v.authorMeta?.video || 0,
          bio, category,
          private: v['authorMeta.privateAccount'] || v.authorMeta?.privateAccount || false,
          region: detectRegion(bio),
          occupation: detectOccupation(bio, category),
        };
      }
    } else {
      for (const p of items) {
        igProfiles[p.username] = {
          name: p.username,
          fans: p.followersCount || 0,
          posts: p.postsCount || 0,
          bio: p.biography || '',
          category: p.businessCategoryName || null,
          private: p.private || false,
          region: detectRegion(p.biography || ''),
          occupation: detectOccupation(p.biography || '', p.businessCategoryName),
        };
      }
    }
  }

  // === 短路过滤 ===
  const results = {};
  const ttSurvivors = [], igSurvivors = [];
  for (const u of uniqueTT) {
    const p = ttProfiles[u];
    if (!p) { results[`TT:${u}`] = { platform: 'TT', name: u, fans: 0, posts: 0, regionAccurate: '-', avgViews: 0, verdict: '⚠️ 抓取失败', reason: 'TT profile 抓取无返回' }; continue; }
    const sc = shortCircuit('TT', p);
    if (sc.fail) results[`TT:${u}`] = { platform: 'TT', name: u, fans: p.fans, posts: p.posts, regionAccurate: p.region ? '是' : '-', avgViews: 0, verdict: '❌ 否', reason: sc.reason };
    else ttSurvivors.push(u);
  }
  for (const u of uniqueIG) {
    const p = igProfiles[u];
    if (!p) { results[`IG:${u}`] = { platform: 'IG', name: u, fans: 0, posts: 0, regionAccurate: '-', avgViews: 0, verdict: '⚠️ 抓取失败', reason: 'IG profile 抓取无返回' }; continue; }
    const sc = shortCircuit('IG', p);
    if (sc.fail) results[`IG:${u}`] = { platform: 'IG', name: u, fans: p.fans, posts: p.posts, regionAccurate: p.region ? '是' : '-', avgViews: 0, verdict: '❌ 否', reason: sc.reason };
    else igSurvivors.push(u);
  }
  console.log(`\n⚡ 短路淘汰: TT ${uniqueTT.length - ttSurvivors.length}/${uniqueTT.length}, IG ${uniqueIG.length - igSurvivors.length}/${uniqueIG.length}`);
  console.log(`   TT 存活: [${ttSurvivors.join(', ') || '无'}]`);
  console.log(`   IG 存活: [${igSurvivors.join(', ') || '无'}]`);

  // === STAGE 2: 仅 survivors 抓 posts ===
  if (ttSurvivors.length + igSurvivors.length > 0) {
    console.log(`\n=== STAGE 2: 抓 survivors 的 posts/videos（${POSTS_LIMIT} 条/人）===`);
    const stage2 = [];
    if (ttSurvivors.length > 0) {
      console.log(`  → TT clockworks ${POSTS_LIMIT} videos ×${ttSurvivors.length}`);
      stage2.push(startActor('clockworks/tiktok-profile-scraper', {
        profiles: ttSurvivors,
        profileScrapeSections: ['videos'],
        profileSorting: 'latest',
        resultsPerPage: POSTS_LIMIT,
        excludePinnedPosts: true,
        shouldDownloadAvatars: false, shouldDownloadCovers: false,
        shouldDownloadSlideshowImages: false, shouldDownloadVideos: false,
      }).then(async ({ runId, datasetId }) => {
        await waitForRun(runId);
        return { kind: 'tt-posts', items: await fetchDataset(datasetId) };
      }));
    }
    if (igSurvivors.length > 0) {
      console.log(`  → IG post-scraper detailedData, ${POSTS_LIMIT} posts ×${igSurvivors.length}`);
      stage2.push(startActor('apify/instagram-post-scraper', {
        username: igSurvivors,
        dataDetailLevel: 'detailedData',
        resultsLimit: POSTS_LIMIT,
        skipPinnedPosts: false,
      }).then(async ({ runId, datasetId }) => {
        await waitForRun(runId);
        return { kind: 'ig-posts', items: await fetchDataset(datasetId) };
      }));
    }
    const stage2Results = await Promise.all(stage2);

    const ttPostsByUser = {}, igPostsByUser = {};
    for (const { kind, items } of stage2Results) {
      if (kind === 'tt-posts') {
        for (const v of items) {
          const name = v['authorMeta.name'] || v.authorMeta?.name;
          if (!name) continue;
          (ttPostsByUser[name] = ttPostsByUser[name] || []).push({
            lang: v.textLanguage,
            createTime: v.createTimeISO,
            playCount: v.playCount || 0,
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
      const de = posts.filter(x => x.lang === 'de').length;
      const en = posts.filter(x => x.lang === 'en').length;
      const dePct = (de + en) > 0 ? Math.round(de * 100 / (de + en)) : null;
      const recent = posts.filter(x => new Date(x.createTime) > threeMonthsAgo);
      const avgViews = recent.length > 0 ? Math.round(recent.reduce((s, x) => s + x.playCount, 0) / recent.length) : 0;
      const j = judge('TT', p, dePct, avgViews);
      results[`TT:${u}`] = { platform: 'TT', name: u, fans: p.fans, posts: p.posts, ...j, avgViews };
    }
    for (const u of igSurvivors) {
      const p = igProfiles[u];
      const posts = igPostsByUser[u] || [];
      const captions = posts.filter(x => x.caption && x.caption.trim().length > 5);
      let g = 0, e = 0;
      for (const post of captions) {
        const lang = detectLang(post.caption);
        if (lang === 'de') g++; else if (lang === 'en') e++;
      }
      const dePct = (g + e) > 0 ? Math.round(g * 100 / (g + e)) : null;
      const recentVideos = posts.filter(x =>
        (x.type === 'Video' || (x.videoPlayCount && x.videoPlayCount > 0)) &&
        x.timestamp && new Date(x.timestamp) > threeMonthsAgo
      );
      let avgViews = 0;
      if (recentVideos.length > 0) {
        const views = recentVideos.map(x => x.videoPlayCount || x.videoViewCount || 0);
        avgViews = Math.round(views.reduce((s, v) => s + v, 0) / views.length);
      }
      const j = judge('IG', p, dePct, avgViews);
      results[`IG:${u}`] = { platform: 'IG', name: u, fans: p.fans, posts: p.posts, ...j, avgViews };
    }

    // 持久化 raw 数据
    const map = { 'tt-profile': 'tt_profiles_stage1.json', 'tt-posts': 'tt_profiles.json', 'ig-profile': 'ig_profiles.json', 'ig-posts': 'ig_posts.json' };
    for (const { kind, items } of [...stage1Results, ...stage2Results]) {
      fs.writeFileSync(path.join(DATA_DIR, map[kind]), JSON.stringify(items));
    }
  }

  // === 输出表 ===
  console.log('\n=== 最终判定（按粘贴顺序）===\n');
  const header = '| # | 平台 | 用户名 | 粉丝数量 | 帖数 | 地区是否准确 | 近三月平均浏览量 | 是否合适 | 原因 |';
  const sep = '|---|------|--------|---------|------|-------------|-----------------|---------|------|';
  const rows = inputOrder.map((u, i) => {
    const r = results[`${u.platform}:${u.username}`];
    if (!r) return `| ${i + 1} | ${u.platform} | ${u.username} | - | - | - | - | ⚠️ 抓取失败 | - |`;
    return `| ${i + 1} | ${r.platform} | ${r.name} | ${(r.fans || 0).toLocaleString()} | ${r.posts || '?'} | ${r.regionAccurate} | ${(r.avgViews || 0).toLocaleString()} | ${r.verdict} | ${r.reason} |`;
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
    `> 规则: v0.4 微调 (caption ${CAPTION_THRESHOLD}% / 评论 ${COMMENT_THRESHOLD}%)`,
    `> 抓取量: ${POSTS_LIMIT} posts/videos per survivor (短路淘汰 ${uniqueTT.length - ttSurvivors.length + uniqueIG.length - igSurvivors.length}/${uniqueTT.length + uniqueIG.length})`,
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
