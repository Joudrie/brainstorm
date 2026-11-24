#!/usr/bin/env python3
"""Add reels to reels.json from pasted text (e.g. a Muse message).

Usage:
  python3 scripts/add_reels.py "Nov 25" < muse_message.txt
  pbpaste | python3 scripts/add_reels.py "Nov 25"
Links already in reels.json are skipped.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "reels.json"

def main():
    day = sys.argv[1] if len(sys.argv) > 1 else "New"
    text = sys.stdin.read()
    ids = list(dict.fromkeys(re.findall(r"instagram\.com/(?:reel|reels|p)/([A-Za-z0-9_-]+)", text)))
    reels = json.loads(DATA.read_text())
    have = {r["id"] for r in reels}
    n = max((r["n"] for r in reels), default=0)
    added = 0
    for i in ids:
        if i in have:
            continue
        n += 1; added += 1
        reels.append({"n": n, "id": i, "url": f"https://www.instagram.com/reel/{i}/", "day": day, "posted": False, "file": None})
    DATA.write_text(json.dumps(reels, indent=1) + "\n")
    print(f"Found {len(ids)} links, added {added}, skipped {len(ids) - added} already in the list.")

if __name__ == "__main__":
    main()
