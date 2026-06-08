// 拉 3 个 dataset，存 ./data/
// 用法: node --env-file=.env scripts/fetch_batch.mjs <TT_ID> <IG_PROFILE_ID> <IG_POSTS_ID>

import fs from 'fs';

const TOKEN = process.env.APIFY_TOKEN;
if (!TOKEN) throw new Error('APIFY_TOKEN missing');

const [tt, igp, igp2] = process.argv.slice(2);
if (!tt || !igp || !igp2) {
  console.error('用法: node scripts/fetch_batch.mjs <TT_ID> <IG_PROFILE_ID> <IG_POSTS_ID>');
  process.exit(1);
}

async function fetchAll(id) {
  const url = `https://api.apify.com/v2/datasets/${id}/items?token=${TOKEN}&clean=true&limit=1000`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${id}: ${await r.text()}`);
  return await r.json();
}

const dataDir = './data';
if (!fs.existsSync(dataDir)) fs.mkdirSync(dataDir, { recursive: true });

console.log('Fetching TT profiles...');
const ttData = await fetchAll(tt);
fs.writeFileSync(`${dataDir}/tt_profiles.json`, JSON.stringify(ttData));
console.log(`  ${ttData.length} items → tt_profiles.json`);

console.log('Fetching IG profiles...');
const igProfileData = await fetchAll(igp);
fs.writeFileSync(`${dataDir}/ig_profiles.json`, JSON.stringify(igProfileData));
console.log(`  ${igProfileData.length} items → ig_profiles.json`);

console.log('Fetching IG posts...');
const igPostsData = await fetchAll(igp2);
fs.writeFileSync(`${dataDir}/ig_posts.json`, JSON.stringify(igPostsData));
console.log(`  ${igPostsData.length} items → ig_posts.json`);

// 抽样检查 IG posts 是否含 view count 字段
const sampleVid = igPostsData.find(p => p.type === 'Video' || p.productType === 'clips');
if (sampleVid) {
  const viewKeys = Object.keys(sampleVid).filter(k => /view|play/i.test(k));
  console.log(`\nIG video sample fields with view/play: ${viewKeys.length ? viewKeys.join(', ') : '⚠️ NONE (need detailedData)'}`);
  console.log(`Sample: ${JSON.stringify({type: sampleVid.type, productType: sampleVid.productType, ...Object.fromEntries(viewKeys.map(k => [k, sampleVid[k]]))}, null, 2)}`);
}
