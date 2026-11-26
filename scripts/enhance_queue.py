#!/usr/bin/env python3
"""Make the graded/zoomed version (videos/edited/) of every unposted clip that lacks one."""
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "reels.json"
reels = json.loads(DATA.read_text())
(ROOT / "videos" / "edited").mkdir(parents=True, exist_ok=True)
done = 0
for r in reels:
    if r.get("posted") or not r.get("file") or r.get("edited") or r.get("source") == "comp":
        continue
    out = f"videos/edited/{Path(r['file']).name}"
    subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "enhance.py"), str(ROOT / r["file"]), str(ROOT / out)], check=True)
    r["edited"] = out; done += 1
    DATA.write_text(json.dumps(reels, indent=1) + "\n")
print(f"Edited {done} clips.")
