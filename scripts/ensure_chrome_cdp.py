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

# Load from .env or use defaults
import os as _os
from dotenv import load_dotenv
load_dotenv()

CHROME_EXE = _os.getenv("CHROME_EXE", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
CHROME_USER_DATA = _os.getenv("CHROME_USER_DATA", r"C:\Users\yaxua\chrome-debug")
CDP_PORT = int(_os.getenv("CDP_PORT", "9222"))
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"


def is_cdp_alive():
    """Check if Chrome CDP is reachable."""
    try:
        req = Request(f"{CDP_URL}/json/version")
        with urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            return "webSocketDebuggerUrl" in data
    except (URLError, OSError, json.JSONDecodeError):
        return False


def is_ig_logged_in():
    """Check if IG is logged in by looking for session cookie."""
    try:
        req = Request(f"{CDP_URL}/json")
        with urlopen(req, timeout=3) as resp:
            tabs = json.loads(resp.read())
        # Find an IG tab and check its cookies via CDP
        for tab in tabs:
            if "instagram.com" in tab.get("url", ""):
                return True
        return False
    except Exception:
        return False


def kill_chrome():
    """Kill all Chrome processes."""
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
    ok = ensure()
    if ok:
        print("[ensure_chrome] Chrome CDP is ready.")
        sys.exit(0)
    else:
        print("[ensure_chrome] FAILED — manual intervention needed.")
        sys.exit(1)
