"""Run seeds one at a time through the full pipeline, with cost tracking.

Usage:
  python scripts/run_batch_seeds.py <seed_file> [--budget 40]

seed_file: one Instagram URL per line
--budget: stop when Apify spend reaches this (default $40)
"""
import os, subprocess, sys, time, json, urllib.request
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Parse args
args = sys.argv[1:]
budget = 40.0
seed_file = None
i = 0
while i < len(args):
    if args[i] == '--budget' and i + 1 < len(args):
        budget = float(args[i + 1]); i += 2
    elif not args[i].startswith('--'):
        seed_file = Path(args[i]); i += 1
    else:
        i += 1

if not seed_file or not seed_file.exists():
    print(f"Usage: python scripts/run_batch_seeds.py <seed_file> [--budget 40]")
    print(f"File not found: {seed_file}")
    sys.exit(1)

APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")

seeds = [l.strip() for l in seed_file.read_text("utf-8").splitlines()
         if l.strip() and not l.strip().startswith("#")]

# ── 种子去重 ──
# 同一批次内去重
seeds = list(dict.fromkeys(seeds))

# 跨批次去重
SEEDS_PROCESSED = ROOT / "data" / "seeds_processed.txt"
if SEEDS_PROCESSED.exists():
    processed = set(
        line.strip() for line in SEEDS_PROCESSED.read_text("utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    )
    skipped = [s for s in seeds if s in processed]
    seeds = [s for s in seeds if s not in processed]
    if skipped:
        print(f"⏭️  跳过 {len(skipped)} 个已处理种子: {', '.join(skipped)}")
else:
    processed = set()

if not seeds:
    print("✅ 所有种子均已处理过，无需重复运行。")
    sys.exit(0)

print(f"Seeds: {len(seeds)} | Budget: ${budget:.0f} | File: {seed_file.name}\n")


def get_today_spend():
    if not APIFY_TOKEN:
        return 0
    try:
        url = f"https://api.apify.com/v2/actor-runs?token={APIFY_TOKEN}&limit=100&desc=true"
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
        today = time.strftime("%Y-%m-%d")
        return sum(i.get("usageTotalUsd", 0) for i in data["data"]["items"]
                   if (i.get("startedAt", "")[:10] == today))
    except Exception:
        return 0


ok = fail = 0
start = get_today_spend()
print(f"Today's spend before: ${start:.2f}\n")

for i, seed in enumerate(seeds):
    current = get_today_spend()
    if current >= budget:
        print(f"\n*** BUDGET: ${current:.2f} >= ${budget:.0f} — stopping ***")
        break

    print(f"{'='*60}")
    print(f"[{i+1}/{len(seeds)}] {seed}  (${current:.2f} / ${budget:.0f})")
    print(f"{'='*60}")
    t0 = time.time()

    # Clean previous input files
    for f in ROOT.glob("data/similar_*.txt"):
        f.unlink(missing_ok=True)
    (ROOT / "data" / "input_similar_combined.txt").unlink(missing_ok=True)

    result = subprocess.run(
        [PYTHON, str(ROOT / "scripts" / "run_full_workflow.py"), seed],
        cwd=str(ROOT), encoding="utf-8", errors="replace",
    )
    elapsed = time.time() - t0

    if result.returncode == 0:
        print(f"\n  OK [{i+1}/{len(seeds)}] {elapsed:.0f}s")
        ok += 1
    else:
        print(f"\n  FAIL [{i+1}/{len(seeds)}] exit={result.returncode} {elapsed:.0f}s")
        fail += 1

    after = get_today_spend()
    delta = after - current
    print(f"  $ ~${delta:.3f} | today: ${after:.2f}")

final = get_today_spend()
print(f"\n{'='*60}")
print(f"Done. OK={ok} Fail={fail} Skipped={len(seeds)-ok-fail} | Spend: ${final:.2f}")
if final >= budget:
    print(f"*** Budget ${budget:.0f} reached ***")
print(f"{'='*60}")
