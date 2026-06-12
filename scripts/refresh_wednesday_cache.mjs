#!/usr/bin/env node
/**
 * Wednesday 缓存刷新脚本
 *
 * 自动启动无头 Chromium，登录 Wednesday，查询所有指定达人的受众数据，
 * 写入 data/wednesday_cache.json。
 *
 * 用法：
 *   node --env-file=.env scripts/refresh_wednesday_cache.mjs username1 username2 ...
 *   node --env-file=.env scripts/refresh_wednesday_cache.mjs data/input.txt   （从文件读URL）
 *   node --env-file=.env scripts/refresh_wednesday_cache.mjs                   （只更新已有缓存里的，补充缺失）
 */

import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const WEDNESDAY_EMAIL = process.env.WEDNESDAY_EMAIL || 'it@icrush.de';
const WEDNESDAY_PASSWORD = process.env.WEDNESDAY_PASSWORD || '';
const CACHE_FILE = path.resolve('./data/wednesday_cache.json');

function loadCache() {
  try { return JSON.parse(fs.readFileSync(CACHE_FILE, 'utf-8')); }
  catch { return {}; }
}

function saveCache(cache) {
  fs.writeFileSync(CACHE_FILE, JSON.stringify(cache, null, 2));
}

// 从 input.txt 提取用户名
function extractUsernames(filePath) {
  const raw = fs.readFileSync(filePath, 'utf-8');
  const users = [];
  for (const line of raw.split('\n')) {
    const u = line.trim();
    if (!u || u.startsWith('#')) continue;
    let m;
    if ((m = u.match(/tiktok\.com\/@([\w._-]+)/))) users.push(m[1]);
    else if ((m = u.match(/instagram\.com\/([\w._-]+)/))) {
      const seg = m[1];
      if (['p', 'reel', 'reels', 'tv', 'stories', 'explore'].includes(seg.toLowerCase())) continue;
      users.push(seg.replace(/\/$/, ''));
    }
  }
  return [...new Set(users)];
}

async function main() {
  // 确定要查的用户列表
  let users = [];
  const arg = process.argv[2];
  if (arg) {
    if (arg.endsWith('.txt')) {
      users = extractUsernames(arg);
    } else {
      users = process.argv.slice(2);
    }
  }
  if (users.length === 0) {
    // 没给参数：查缓存里缺失的那些
    const cache = loadCache();
    // 查不到缺失列表，直接报 usage
    console.log('用法: node --env-file=.env scripts/refresh_wednesday_cache.mjs <usernames...>');
    console.log('  或: node --env-file=.env scripts/refresh_wednesday_cache.mjs data/input.txt');
    process.exit(1);
  }

  console.log(`🔍 准备查询 ${users.length} 个达人: ${users.join(', ')}`);

  const cache = loadCache();
  const toQuery = users.filter(u => {
    const e = cache[u];
    if (!e || !e.found) return true;
    // 已有数据的不重复查
    if (e.gender || e.topCountry) return false;
    return true;
  });

  if (toQuery.length === 0) {
    console.log('✅ 所有达人已缓存，无需查询');
    return;
  }

  console.log(`   需查询 ${toQuery.length} 人（${users.length - toQuery.length} 人已有缓存）`);

  // 启动无头浏览器
  console.log('\n🚀 启动无头浏览器...');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    // 登录
    console.log('🔑 登录 Wednesday...');
    await page.goto('https://user.wednesday.app/login', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(5000);

    let token = null;

    // 检查是否自动跳转（cookie 还有效）
    if (page.url().includes('hq.wednesday.app')) {
      console.log('   ✅ Cookie 有效，自动登录');
    } else {
      // 等待 Ember 表单渲染完成
      await page.waitForSelector('input[placeholder*="email"], input[id*="ember"]', { timeout: 10000 }).catch(() => {});
      await page.waitForTimeout(2000);

      const formExists = await page.evaluate(() => {
        const ins = document.querySelectorAll('input:not([type="hidden"])');
        return ins.length >= 2;
      });

      if (!formExists) {
        console.error('❌ 登录表单未加载，可能是网络问题');
        console.log('   页面 URL:', page.url());
        await browser.close();
        process.exit(1);
      }

      // 用 placeholder 填表单
      await page.fill('input[placeholder*="email"]', WEDNESDAY_EMAIL);
      await page.fill('input[placeholder*="password"]', WEDNESDAY_PASSWORD);
      await page.click('button:has-text("Log in")');
      console.log('   ℹ️  等待登录跳转...');
      await page.waitForTimeout(5000);

      // 检查跳转
      for (let i = 0; i < 6; i++) {
        if (page.url().includes('hq.wednesday.app')) break;
        await page.waitForTimeout(2000);
      }
      if (!page.url().includes('hq.wednesday.app')) {
        console.error('❌ 登录失败，URL:', page.url());
        await browser.close();
        process.exit(1);
      }
      console.log('   ✅ 登录成功');
    }

    // 提取 token
    token = await page.evaluate(() => {
      const m = document.cookie.match(/wednesday-production-auth=([^;]+)/);
      if (!m) return null;
      return JSON.parse(decodeURIComponent(m[1])).authenticated.access_token;
    });

    if (!token) {
      console.error('❌ 无法提取 token');
      await browser.close();
      process.exit(1);
    }

    // 逐个查询
    console.log(`\n🔎 查询 ${toQuery.length} 个达人...`);
    for (const username of toQuery) {
      process.stdout.write(`  → ${username} ... `);
      try {
        const result = await page.evaluate(async ({ username, token }) => {
          // Search
          const sr = await fetch('https://facade.upfluence.co/api/v1/matches?page=1&per_page=10&offset=0', {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', Accept: 'application/json' },
            body: JSON.stringify({ current_list: '389827', criterias: [{ value: username, weight: 1, field: 'all', type: 'should' }], filters: [], audience_filters: [], social_media_matching_operator: 'or', should_save: false, track_hits_results: 10000, score_model: 'default' }),
          });
          const sd = await sr.json();
          const infs = sd.influencers || [];

          // 策略：对每个候选调详情 API，比对 IG/TT username 精确匹配
          const candidates = infs.slice(0, 5);
          for (const inf of candidates) {
            try {
              const dr = await fetch(`https://facade.upfluence.co/api/v1/influencers/${inf.id || inf.influencer_id}`, {
                headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
              });
              const dd = await dr.json();
              const igs = dd.instagrams || [];
              const tts = dd.tiktoks || [];

              // 精确匹配 social media username
              const igMatch = igs.find(m => m.username?.toLowerCase() === username.toLowerCase());
              const ttMatch = tts.find(m => m.username?.toLowerCase() === username.toLowerCase());

              if (igMatch || ttMatch) {
                const med = igMatch || ttMatch;
                const aud = med?.audience || {};
                const g = aud?.gender_image_extractor?.values || null;
                const c = aud?.country_last_picture?.values || null;
                const ci = aud?.city_last_picture?.values || null;
                let tc = null, tcp = 0; if (c) Object.entries(c).forEach(([k, v]) => { if (v > tcp) { tcp = v; tc = k; } });
                let tci = null, tcip = 0; if (ci) Object.entries(ci).forEach(([k, v]) => { if (v > tcip) { tcip = v; tci = k; } });
                return {
                  found: true,
                  gender: g ? { female: Math.round(g.female * 10000) / 100, male: Math.round(g.male * 10000) / 100 } : null,
                  topCountry: tc ? { code: tc, pct: Math.round(tcp * 10000) / 100 } : null,
                  topCity: tci ? { name: tci, pct: Math.round(tcip * 10000) / 100 } : null,
                  _matchedName: inf.name,
                  _matchedVia: igMatch ? 'IG' : 'TT',
                };
              }
            } catch (e) { /* 跳过此候选 */ }
          }
          return { found: false, _debug: { searched: candidates.length } };
        }, { username, token });

        cache[username] = result;
        if (result.found) {
          const g = result.gender ? `女${result.gender.female}%` : '无性别';
          const c = result.topCountry ? ` ${result.topCountry.code} ${result.topCountry.pct}%` : '';
          console.log(`✅ ${g}${c} (${result._matchedVia}:${result._matchedName})`);
        } else {
          console.log('❌ 无匹配');
        }
      } catch (e) {
        cache[username] = { found: false, error: e.message };
        console.log(`⚠️ 异常: ${e.message}`);
      }
    }

    saveCache(cache);
    console.log(`\n💾 缓存已保存: ${CACHE_FILE}`);
    console.log(`   共 ${Object.keys(cache).length} 条记录`);

  } finally {
    await browser.close();
  }
}

main().catch(e => {
  console.error('\n❌ 错误:', e.message);
  process.exit(1);
});
