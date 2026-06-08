import fs from 'fs';

// 从 .env 读取，运行方式：node --env-file=.env scripts/fetch_comments.mjs
const TOKEN = process.env.APIFY_TOKEN;
if (!TOKEN) {
  console.error('错误：未设置 APIFY_TOKEN 环境变量。');
  console.error('复制 .env.example 为 .env 并填入 token，然后用 npm run fetch-comments 跑');
  process.exit(1);
}

async function fetchDataset(id, fields, limit = 500) {
  const url = `https://api.apify.com/v2/datasets/${id}/items?token=${TOKEN}&fields=${fields}&limit=${limit}&clean=true`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
  return await r.json();
}

// 用法示例：把要抓的 dataset ID 填到下面
// 这两个 ID 来自 2026-06-08 跑的那一批（评论数据）
const TT_DATASET_ID = process.env.TT_COMMENTS_DATASET || 'IcRisJssubo0vcPwq';
const IG_DATASET_ID = process.env.IG_COMMENTS_DATASET || 'kPJRlgn9GgyJRSccM';

const dataDir = './data';
if (!fs.existsSync(dataDir)) fs.mkdirSync(dataDir, { recursive: true });

console.log('Fetching TT comments...');
const tt = await fetchDataset(TT_DATASET_ID, 'video_url,text,language', 500);
console.log(`TT: ${tt.length} items`);
fs.writeFileSync(`${dataDir}/tt_comments.json`, JSON.stringify(tt));

console.log('Fetching IG comments...');
const ig = await fetchDataset(IG_DATASET_ID, 'postUrl,text', 500);
console.log(`IG: ${ig.length} items`);
fs.writeFileSync(`${dataDir}/ig_comments.json`, JSON.stringify(ig));

console.log('Done. 数据已保存到 ./data/');
