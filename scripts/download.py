#!/usr/bin/env python3
"""Download every reel in reels.json that has no video yet, into videos/.

Needs yt-dlp (pip install yt-dlp). Instagram blocks anonymous downloads from
most servers, so put an exported Instagram login (Netscape cookies.txt, from a
throwaway account) at the repo root as cookies.txt. It is git-ignored.

Usage:  python3 scripts/download.py [--limit N]
"""
import json, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "reels.json"
VIDEOS = ROOT / "videos"
COOKIES = ROOT / "cookies.txt"

def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    reels = json.loads(DATA.read_text())
    todo = [r for r in reels if not r.get("file")][:limit]
    VIDEOS.mkdir(exist_ok=True)
    ok = fail = 0
    for r in todo:
        out = VIDEOS / f"{r['n']:03d}-{r['id']}.mp4"
        cmd = [sys.executable, "-m", "yt_dlp", "--no-progress", "-f", "mp4/best", "--merge-output-format", "mp4",
               "-o", str(out), r["url"]]
        if COOKIES.exists():
            cmd[3:3] = ["--cookies", str(COOKIES)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and out.exists():
            r["file"] = f"videos/{out.name}"; ok += 1
            print(f"#{r['n']} {r['id']}: saved")
            DATA.write_text(json.dumps(reels, indent=1) + "\n")
        else:
            fail += 1
            err = (res.stderr.strip().splitlines() or ["unknown error"])[-1]
            print(f"#{r['n']} {r['id']}: FAILED - {err}")
        time.sleep(3)  # go easy on Instagram
    print(f"Done: {ok} saved, {fail} failed.")

if __name__ == "__main__":
    main()
