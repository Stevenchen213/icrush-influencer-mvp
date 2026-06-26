@echo off
chcp 65001 >nul
echo ==========================================
echo   ICRUSH 首次初始化 — IG 登录
echo ==========================================
echo.
echo 本脚本只需在新电脑上运行一次。
echo.
echo 接下来会打开一个 Chrome 窗口，请：
echo   1. 在 Chrome 里登录 Instagram
echo   2. 确认 IG 主页能正常加载（已登录状态）
echo   3. 关闭 Chrome 窗口
echo   4. 回到这里按任意键完成
echo.
pause

echo.
echo 正在启动 Chrome（带调试端口）...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\chrome-debug"

echo.
echo ==========================================
echo   Chrome 已打开，去登录 IG 吧！
echo   登录成功后关掉 Chrome，回这里按任意键。
echo ==========================================
pause >nul

echo.
echo 验证 Chrome CDP 是否正常...
timeout /t 3 /nobreak >nul
curl -s http://127.0.0.1:9222/json/version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ CDP 端口正常
) else (
    echo ✗ CDP 端口未响应，请重新运行本脚本
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   初始化完成！
echo   以后运行 python scripts/ensure_chrome_cdp.py
echo   即可自动启动 Chrome + 恢复 IG 登录态。
echo ==========================================
pause
