#!/usr/bin/env python3
"""Add clips to reels.json from pasted text (Instagram, TikTok or Reddit links).

Usage:
  python3 scripts/add_reels.py "Nov 25" < muse_message.txt
  pbpaste | python3 scripts/add_reels.py "Nov 25"
Links already in reels.json are skipped.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "reels.json"

PATTERNS = [
    # (source, regex, id prefix, canonical url)
    ("instagram", r"instagram\.com/(?:reel|reels|p)/([A-Za-z0-9_-]+)", "", "https://www.instagram.com/reel/{}/"),
    ("tiktok", r"tiktok\.com/@[\w.-]+/video/(\d+)", "tt-", None),
    ("tiktok", r"((?:vm|vt)\.tiktok\.com/[A-Za-z0-9]+)", "tts-", "https://{}/"),
    ("reddit", r"reddit\.com/r/\w+/comments/([a-z0-9]+)", "rd-", "https://www.reddit.com/comments/{}/"),
    ("reddit", r"redd\.it/([a-z0-9]+)", "rd-", "https://www.reddit.com/comments/{}/"),
]


def find_links(text):
    found = []
    for source, rx, prefix, canon in PATTERNS:
        for m in re.finditer(rx, text):
            key = m.group(1)
            if source == "tiktok" and canon is None:
                url = re.search(r"https?://(?:www\.)?tiktok\.com/@[\w.-]+/video/" + key, text)
                url = url.group(0) if url else f"https://www.tiktok.com/@_/video/{key}"
            else:
                url = canon.format(key)
            rid = prefix + re.sub(r"[^A-Za-z0-9_-]", "_", key.split("/")[-1])
            found.append((rid, url, source))
    seen, out = set(), []
    for f in found:
        if f[0] not in seen:
            seen.add(f[0]); out.append(f)
    return out


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else "New"
    links = find_links(sys.stdin.read())
    reels = json.loads(DATA.read_text())
    have = {r["id"] for r in reels}
    n = max((r["n"] for r in reels), default=0)
    added = 0
    for rid, url, source in links:
        if rid in have:
            continue
        n += 1; added += 1
        reels.append({"n": n, "id": rid, "url": url, "source": source, "day": day, "posted": False, "file": None})
    DATA.write_text(json.dumps(reels, indent=1) + "\n")
    print(f"Found {len(links)} links, added {added}, skipped {len(links) - added} already in the list.")

if __name__ == "__main__":
    main()
