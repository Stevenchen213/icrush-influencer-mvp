/**
 * 输出最终判定表（markdown 格式，方便复制回飞书）
 *
 * 当前是 2026-06-08 那次 23 人测试的硬编码结果。
 * 后续可以改成从 results/<date>.json 加载，统一表格输出。
 *
 * 运行：node scripts/final_table.mjs
 */

// 2026-06-08 batch23 最终判定（v0.4）
const results = [
  // ✅ 是
  { platform: 'IG', name: 'laura.jungen', fans: 142783, posts: 570, region: '-', avgViews: 306314, verdict: '✅ 是', reason: '-' },
  { platform: 'IG', name: 'eva_soellner', fans: 207415, posts: 1158, region: '是', avgViews: 92700, verdict: '✅ 是', reason: '-' },
  { platform: 'IG', name: 'jxlia.albrecht', fans: 99745, posts: 258, region: '是', avgViews: 9563, verdict: '✅ 是', reason: '② 评论 77% 德语 → 通过' },

  // 🟡 置换组
  { platform: 'TT', name: 'sarah.salii', fans: 5650, posts: 316, region: '-', avgViews: 5459, verdict: '🟡 置换组', reason: '粉丝 5650<10K（② 评论 72% 德语 → 通过）' },

  // ⚠️ 需人工核查
  { platform: 'TT', name: 'enya.elisaa', fans: 72800, posts: 367, region: '-', avgViews: 12723, verdict: '⚠️ 需人工核查', reason: 'caption 57% < 70% + 评论数据不足（13 条全表情，TT 提前 abort）' },
  { platform: 'TT', name: 'iamleohehe', fans: 13100, posts: 207, region: '-', avgViews: 8176, verdict: '⚠️ 需人工核查', reason: 'caption 62% < 70% + 评论 API 未抓到（TT abort 在 sarah.salii 后）' },
  { platform: 'TT', name: 'smillamalou', fans: 25900, posts: 305, region: '-', avgViews: 168700, verdict: '⚠️ 需人工核查', reason: 'caption 57% < 70% + 评论 API 未抓到（TT abort 在 sarah.salii 后）' },

  // ❌ 否
  { platform: 'TT', name: 'linabxckes', fans: 80600, posts: 49, region: '-', avgViews: 6639, verdict: '❌ 否', reason: '帖数 49<200' },
  { platform: 'TT', name: 'lavicyish', fans: 14100, posts: 146, region: '-', avgViews: 908, verdict: '❌ 否', reason: '帖数 146<200' },
  { platform: 'TT', name: 'jasminpris_', fans: 12000, posts: 68, region: '-', avgViews: 0, verdict: '❌ 否', reason: '帖数 68<200' },
  { platform: 'TT', name: 'lauralousebald', fans: 22400, posts: 144, region: '-', avgViews: 124066, verdict: '❌ 否', reason: '帖数 144<200' },
  { platform: 'TT', name: 'fashion.xxxx', fans: 11700, posts: 95, region: '-', avgViews: 3222, verdict: '❌ 否', reason: '帖数 95<200' },
  { platform: 'TT', name: 'marthavillwock0', fans: 9018, posts: 83, region: '-', avgViews: 3306, verdict: '❌ 否', reason: '帖数 83<200' },
  { platform: 'IG', name: 'emiliajoyyy', fans: 51582, posts: 383, region: '是', avgViews: 273899, verdict: '❌ 否', reason: 'caption 8% + ② 评论仅 22% 德语 → 不通过' },
  { platform: 'IG', name: 'fraunotarin', fans: 12194, posts: 137, region: '-', avgViews: 36780, verdict: '❌ 否', reason: '职业=律师（直接PASS）' },
  { platform: 'IG', name: 'marianamskiiii', fans: 57037, posts: 68, region: '-', avgViews: 92841, verdict: '❌ 否', reason: '帖数 68<200' },
  { platform: 'IG', name: 'eileen_frm', fans: 30469, posts: 95, region: '-', avgViews: 28682, verdict: '❌ 否', reason: '帖数 95<200' },
  { platform: 'IG', name: 'celinealbar', fans: 67168, posts: 141, region: '-', avgViews: 308438, verdict: '❌ 否', reason: '帖数 141<200' },
  { platform: 'IG', name: 'didemercin_', fans: 101103, posts: 170, region: '-', avgViews: 11951, verdict: '❌ 否', reason: '职业=艺术家（直接PASS）' },
  { platform: 'IG', name: 'lilly.wls', fans: 14211, posts: 130, region: '-', avgViews: 50261, verdict: '❌ 否', reason: '帖数 130<200' },
  { platform: 'IG', name: 'alenaarosalie', fans: 140551, posts: 305, region: '-', avgViews: 136934, verdict: '❌ 否', reason: 'caption 0% + bio 无地区' },
  { platform: 'IG', name: 'missaljel', fans: 92213, posts: 1363, region: '-', avgViews: 11103, verdict: '❌ 否', reason: 'caption 0% + bio 无地区' },
];

console.log('| 平台 | 用户名 | 粉丝数量 | 帖数 | 地区是否准确 | 近三月平均浏览量 | 是否合适 | 原因 |');
console.log('|------|--------|---------|------|-------------|-----------------|---------|------|');
for (const r of results) {
  console.log(`| ${r.platform} | ${r.name} | ${r.fans.toLocaleString()} | ${r.posts} | ${r.region} | ${r.avgViews.toLocaleString()} | ${r.verdict} | ${r.reason} |`);
}

const stats = {};
for (const r of results) stats[r.verdict] = (stats[r.verdict] || 0) + 1;
console.log('\n=== 统计 ===');
console.log(JSON.stringify(stats, null, 2));
