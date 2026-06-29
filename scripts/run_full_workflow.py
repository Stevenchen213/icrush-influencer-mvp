"""
End-to-end orchestration: CDP ensure → extract similar → pipeline.
Handles retries, timeouts, and CDP disconnects at each stage.

Usage:
  python scripts/run_full_workflow.py seed1 seed2 seed3
  python scripts/run_full_workflow.py --max-retries 5 seed1 seed2
"""
import subprocess
import sys
import time
import json
import os
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

ROOT = Path(__file__).resolve().parent.parent
PYTHON = os.getenv("PYTHON_EXE") or sys.executable
NODE = "node"
CDP_URL = "http://127.0.0.1:9222"
EXTRACT_SCRIPT = ROOT / "scripts" / "fetch_similar_accounts_v3.mjs"
ENSURE_CDP = ROOT / "scripts" / "ensure_chrome_cdp.py"
RUN_BATCH = ROOT / "scripts" / "run_batch.py"
COMBINED_INPUT = ROOT / "data" / "input_similar_combined.txt"

MAX_RETRIES = 3
RETRY_DELAY_BASE = 5  # seconds, doubles each retry


def log(msg: str):
    print(f"[workflow] {msg}")


def is_cdp_alive() -> bool:
    try:
        req = Request(f"{CDP_URL}/json/version")
        with urlopen(req, timeout=3) as resp:
            return "webSocketDebuggerUrl" in json.loads(resp.read())
    except Exception:
        return False


def step_ensure_cdp() -> bool:
    """Ensure Chrome CDP is running. Retry up to 3 times."""
    for attempt in range(MAX_RETRIES):
        log(f"Ensuring CDP (attempt {attempt + 1}/{MAX_RETRIES})...")
        result = subprocess.run(
            [PYTHON, str(ENSURE_CDP)],
            cwd=str(ROOT), capture_output=True, text=True, timeout=120
        )
        print(result.stdout.strip())
        if result.returncode == 0 and is_cdp_alive():
            log("CDP ready.")
            return True
        delay = RETRY_DELAY_BASE * (2 ** attempt)
        log(f"CDP not ready, retry in {delay}s...")
        time.sleep(delay)
    log("FATAL: CDP unavailable after retries.")
    return False


def step_extract(seeds: list[str]) -> bool:
    """Run similar accounts extraction with retry on failure."""
    for attempt in range(MAX_RETRIES):
        log(f"Extracting similar accounts (attempt {attempt + 1}/{MAX_RETRIES})...")

        # Quick CDP check before running
        if not is_cdp_alive():
            log("CDP lost, re-ensuring...")
            if not step_ensure_cdp():
                return False

        cmd = [NODE, str(EXTRACT_SCRIPT), *seeds]
        result = subprocess.run(
            cmd, cwd=str(ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=7200,
        )
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)

        if result.returncode == 0:
            log("Extraction complete.")

            # Check if we actually got results
            if COMBINED_INPUT.exists():
                lines = COMBINED_INPUT.read_text(encoding="utf-8").strip().split("\n")
                count = len([l for l in lines if l.startswith("http")])
                if count > 0:
                    log(f"Got {count} accounts, proceeding to pipeline.")
                    return True
                else:
                    log("0 accounts extracted (all seeds skipped).")
                    return False  # Not a failure, just no results
            else:
                log(f"Extraction claimed success but {COMBINED_INPUT} not found.")
                return False

        log(f"Extraction failed (exit {result.returncode}), stderr: {result.stderr[:200]}")
        if attempt < MAX_RETRIES - 1:
            delay = RETRY_DELAY_BASE * (2 ** attempt)
            log(f"Retry in {delay}s...")
            time.sleep(delay)

    log("FATAL: Extraction failed after all retries.")
    return False


def step_pipeline() -> bool:
    """Run pipeline on combined input. Retry on Apify failures."""
    if not COMBINED_INPUT.exists():
        log("No combined input file, skipping pipeline.")
        return False

    lines = COMBINED_INPUT.read_text(encoding="utf-8").strip().split("\n")
    count = len([l for l in lines if l.startswith("http")])
    if count == 0:
        log("Combined input is empty, skipping pipeline.")
        return False

    log(f"Running pipeline on {count} accounts...")
    result = subprocess.run(
        [PYTHON, str(RUN_BATCH), str(COMBINED_INPUT)],
        cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=7200,
    )
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)

    if result.returncode == 0:
        log("Pipeline complete.")
        return True
    log(f"Pipeline exited with code {result.returncode}")
    return False


def main():
    # Parse args — separate flags from seed usernames
    args = sys.argv[1:]
    seeds: list[str] = []
    max_retries_override = None
    i = 0
    while i < len(args):
        if args[i] == "--max-retries" and i + 1 < len(args):
            try:
                max_retries_override = int(args[i + 1])
            except ValueError:
                print(f"Invalid --max-retries value: {args[i+1]}")
                sys.exit(1)
            i += 2
        elif not args[i].startswith("--"):
            seeds.append(args[i])
            i += 1
        else:
            i += 1

    global MAX_RETRIES
    if max_retries_override:
        MAX_RETRIES = max_retries_override

    if not seeds:
        print("Usage: python scripts/run_full_workflow.py seed1 [seed2 ...]")
        print("       python scripts/run_full_workflow.py --max-retries 5 seed1 seed2")
        sys.exit(1)

    print("=" * 55)
    print(f"ICRUSH Full Workflow — {len(seeds)} seeds, max {MAX_RETRIES} retries/step")
    print(f"Seeds: {', '.join(seeds)}")
    print("=" * 55)

    t0 = time.time()

    # Stage 1: Ensure CDP
    if not step_ensure_cdp():
        sys.exit(1)

    # Stage 2: Extract similar accounts
    if not step_extract(seeds):
        sys.exit(1)

    # Stage 3: Pipeline
    step_pipeline()

    elapsed = time.time() - t0
    print(f"\n{'=' * 55}")
    print(f"Workflow complete in {elapsed:.0f}s.")
    if COMBINED_INPUT.exists():
        print(f"Next: check results/ for the latest report.")
    print(f"{'=' * 55}")


if __name__ == "__main__":
    main()
