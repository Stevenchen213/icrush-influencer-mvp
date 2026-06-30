"""
Ensure Chrome CDP is running with IG logged in.
Used by: pipeline trigger (manual / Feishu webhook / cron)
"""
import subprocess
import json
import time
import os
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

from dotenv import load_dotenv
load_dotenv()

CHROME_EXE = os.getenv("CHROME_EXE", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
CHROME_USER_DATA = os.getenv("CHROME_USER_DATA") or os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "chrome-debug")
CDP_PORT = int(os.getenv("CDP_PORT", "9222"))
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"


def is_cdp_alive():
    """Check if Chrome CDP is fully operational (not just HTTP-alive).

    Does two checks:
    1. /json/version — basic reachability
    2. PUT /json/new — actually opens a tab (exercises full CDP stack)
    """
    try:
        req = Request(f"{CDP_URL}/json/version")
        with urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            if "webSocketDebuggerUrl" not in data:
                return False
        # Try opening a test tab — confirms CDP isn't zombie
        req2 = Request(f"{CDP_URL}/json/new?test_cdp", method="PUT")
        with urlopen(req2, timeout=5) as resp2:
            tab = json.loads(resp2.read())
            if tab.get("id"):
                # Close it immediately
                try:
                    req3 = Request(f"{CDP_URL}/json/close/{tab['id']}")
                    urlopen(req3, timeout=2)
                except Exception:
                    pass
                return True
        return False
    except (URLError, OSError, json.JSONDecodeError, Exception):
        return False


def kill_chrome():
    """Kill all Chrome processes.

    WARNING: This kills ALL Chrome windows, including normal browsing sessions.
    On Windows there is no clean way to kill only the CDP instance via taskkill.
    TODO: Use CDP's /json endpoint to find the CDP Chrome PID and kill only that.
    """
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "chrome.exe"],
            capture_output=True, timeout=10
        )
    except Exception:
        pass
    time.sleep(3)


def start_chrome():
    """Start Chrome with CDP enabled."""
    args = [
        CHROME_EXE,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={CHROME_USER_DATA}",
    ]
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(4)


def ensure():
    """
    Ensure Chrome CDP is ready. Returns True if ready, False if needs manual login.
    Call this before any CDP-dependent script.
    """
    if is_cdp_alive():
        print(f"[ensure_chrome] CDP already alive on port {CDP_PORT}")
        return True

    print("[ensure_chrome] CDP not responding, restarting Chrome...")

    # Kill any existing Chrome
    kill_chrome()

    # Wait for crash recovery to expire
    time.sleep(8)

    # Start fresh
    start_chrome()

    # Wait and verify
    for attempt in range(10):
        if is_cdp_alive():
            print(f"[ensure_chrome] CDP ready on port {CDP_PORT}")
            return True
        time.sleep(2)

    print("[ensure_chrome] ERROR: CDP still not responding after restart!")
    return False


if __name__ == "__main__":
    if "--restart" in sys.argv:
        print("[ensure_chrome] Forcing restart...")
        kill_chrome()
        time.sleep(5)
        start_chrome()
        for _ in range(10):
            if is_cdp_alive():
                print("[ensure_chrome] CDP restarted on port", CDP_PORT)
                sys.exit(0)
            time.sleep(2)
        print("[ensure_chrome] FAILED to restart")
        sys.exit(1)

    ok = ensure()
    if ok:
        print("[ensure_chrome] Chrome CDP is ready.")
        sys.exit(0)
    else:
        print("[ensure_chrome] FAILED — manual intervention needed.")
        sys.exit(1)
