/**
 * 从 TT profile dataset 提取每个达人最新的 N 个视频 URL
 * （用于喂给 thescrapelab/tiktok-comments-scraper）
 *
 * 输入：./data/tt_profiles.json（clockworks 输出）
 * 输出：./data/comment_urls.json（URL 数组）
 *
 * 用法：
 *   node scripts/extract_urls.mjs <username1> <username2> ...
 *   node scripts/extract_urls.mjs sarah.salii enya.elisaa
 */

import fs from 'fs';

const N_PER_USER = 20;
const DATA_DIR = './data';
const inputFile = `${DATA_DIR}/tt_profiles.json`;
const outputFile = `${DATA_DIR}/comment_urls.json`;

const targets = process.argv.slice(2);
if (targets.length === 0) {
  console.error('用法：node scripts/extract_urls.mjs <username1> <username2> ...');
  process.exit(1);
}

const raw = JSON.parse(fs.readFileSync(inputFile, 'utf-8'));
const items = raw.items || raw;

const byUser = {};
for (const t of targets) byUser[t] = [];

for (const v of items) {
  const n = v['authorMeta.name'] || v.authorMeta?.name;
  if (!targets.includes(n)) continue;
  if (v.isPinned) continue; // 置顶视频通常较旧，跳过
  byUser[n].push({
    url: v.webVideoUrl,
    time: v.createTimeISO,
  });
}

const result = [];
for (const t of targets) {
  byUser[t].sort((a, b) => new Date(b.time) - new Date(a.time));
  const top = byUser[t].slice(0, N_PER_USER);
  console.log(`${t}: ${top.length} URLs (newest ${top[0]?.time?.slice(0, 10) || 'N/A'})`);
  result.push(...top.map(x => x.url));
}

console.log(`\n总计 ${result.length} 个 URL`);
fs.writeFileSync(outputFile, JSON.stringify(result, null, 2));
console.log(`保存到 ${outputFile}`);
