"""Run seeds one at a time: extract → pipeline → Feishu sync → next seed."""
import subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

# Read all seeds from file
seeds_file = ROOT / "data" / "batch_72.txt"
seeds = [l.strip() for l in seeds_file.read_text("utf-8").splitlines()
         if l.strip() and not l.strip().startswith("#")]
print(f"Total seeds: {len(seeds)}")
print(f"Mode: one-at-a-time (extract + pipeline + sync)\n")

ok_count = 0
fail_count = 0
skip_count = 0

for i, seed in enumerate(seeds):
    print(f"\n{'='*60}")
    print(f"[{i+1}/{len(seeds)}] {seed}")
    print(f"{'='*60}")
    t0 = time.time()

    # Clean previous combined input so each run is isolated
    combined = ROOT / "data" / "input_similar_combined.txt"
    for f in ROOT.glob("data/similar_*.txt"):
        f.unlink(missing_ok=True)
    combined.unlink(missing_ok=True)

    result = subprocess.run(
        [PYTHON, str(ROOT / "scripts" / "run_full_workflow.py"), seed],
        cwd=str(ROOT),
        encoding="utf-8", errors="replace",
    )
    elapsed = time.time() - t0

    if result.returncode == 0:
        print(f"\n✓ [{i+1}/{len(seeds)}] OK in {elapsed:.0f}s")
        ok_count += 1
    else:
        print(f"\n✗ [{i+1}/{len(seeds)}] FAILED (exit {result.returncode}) in {elapsed:.0f}s")
        fail_count += 1

    print(f"  Progress: {ok_count} ok, {fail_count} fail, {skip_count} skip, {i+1-len(seeds)} remaining")

print(f"\n{'='*60}")
print(f"Done. OK={ok_count} Fail={fail_count} Total={len(seeds)}")
print(f"{'='*60}")
