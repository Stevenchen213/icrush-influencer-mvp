"""Run run_full_workflow.py with seeds from a text file."""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
filepath = ROOT / "data" / "batch_72.txt"

seeds = [l.strip() for l in filepath.read_text("utf-8").splitlines()
         if l.strip() and not l.strip().startswith("#")]
print(f"Running {len(seeds)} seeds in SAFE mode...")
print(f"Seeds: {', '.join(seeds[:5])}... (+{len(seeds)-5} more)")
sys.stdout.flush()

result = subprocess.run(
    ["python", str(ROOT / "scripts" / "run_full_workflow.py")] + seeds,
    cwd=str(ROOT),
    encoding="utf-8", errors="replace",
)
sys.exit(result.returncode)
