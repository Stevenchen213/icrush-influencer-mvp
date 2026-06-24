---
name: cdp-browser-setup-fix
description: web-access CDP 连不上 Chrome 时的修复步骤（Chrome 136+ 默认目录限制 + DevToolsActivePort 同步）
metadata: 
  node_type: memory
  type: reference
  originSessionId: 60df89d7-4acb-48af-8f11-b715ead89b7d
---

web-access skill 的 CDP proxy 连不上 Chrome 时的根因与修复（2026-06-17 实测，Win11 + Chrome 147）。属于 [[tool-stack-installed]] 的运维补充。

## 两个根因
1. **Chrome 136+ 安全限制**：用默认配置目录（`%LOCALAPPDATA%\Google\Chrome\User Data`）时会**忽略** `--remote-debugging-port`。必须指定独立 `--user-data-dir`。
2. **discovery 只读默认目录的 DevToolsActivePort**：`browser-discovery.mjs` 固定读 `%LOCALAPPDATA%\Google\Chrome\User Data\DevToolsActivePort` 拿 wsPath（第2行是 browser GUID）。但调试 Chrome 用了自定义 user-data-dir，文件写在别处，默认目录那个是旧 GUID → proxy 拿旧 GUID 连必然失败（HTTP /json/version 正常但 WS 连不上）。

## 修复步骤
```bash
# 1. 杀掉所有 chrome 和残留后台进程
powershell "Get-Process chrome -EA SilentlyContinue | Stop-Process -Force"
# 2. 用独立 user-data-dir 启动调试 Chrome
powershell "Start-Process 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList '--remote-debugging-port=9222','--user-data-dir=C:\Users\yaxua\chrome-debug'"
# 3. 取 live GUID
curl -s http://127.0.0.1:9222/json/version | grep -o 'devtools/browser/[a-z0-9-]*'
# 4. 把正确 GUID 写进默认目录的 DevToolsActivePort（discovery 会读这个）
printf '9222\n/devtools/browser/<GUID>\n' > "/c/Users/yaxua/AppData/Local/Google/Chrome/User Data/DevToolsActivePort"
# 5. 重启 proxy
pkill -9 -f cdp-proxy.mjs; sleep 2
node "C:/Users/yaxua/.claude/plugins/cache/web-access/web-access/2.5.2/scripts/check-deps.mjs"
```
连上后 `curl -s http://localhost:3456/targets` 应返回 tab 列表。

## 注意
- 调试 Chrome 用的是**全新 chrome-debug 配置**，**没有用户日常 IG/TikTok 登录态**。需要登录态时让用户在该窗口登录一次。
- 截图 `Page.captureScreenshot` 超时：截图前先 `eval window.stop()` 杀掉 IG 未登录的持续加载动画，再截即可。
- 看 IG 未登录主页：`eval` 删除 `div[role=dialog]` 登录弹窗，网格已在 DOM 里，可直接截全貌。og:description 含粉丝/帖数。
