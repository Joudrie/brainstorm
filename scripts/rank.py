#!/usr/bin/env python3
"""Give each unposted reel a rough 1-10 score and set the posting queue.

Favors: fresh clips, lots of comments per like, mid-size reach (proven but not
already seen by everyone). Penalizes mega-viral clips. Missing numbers = 6.5.
Manual moves win: a reel's "queue" set by hand ("manualQueue": true) is kept.
"""
import json, time
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "reels.json"


def score(r, now):
    s = r.get("stats") or {}
    likes, comments, ts = s.get("like_count"), s.get("comment_count"), s.get("timestamp")
    if not likes:
        return 6.5
    pts = 6.0
    age = (now - ts) / 86400 if ts else 5
    pts += 1.5 if age < 2 else 1.0 if age < 3 else 0.5 if age < 4 else 0
    ratio = (comments or 0) / likes * 100
    pts += 1.0 if ratio > 0.8 else 0.5 if ratio > 0.4 else 0
    pts += 1.0 if 10_000 <= likes <= 200_000 else -2.0 if likes > 500_000 else -0.5 if likes < 5_000 else 0
    return round(max(1, min(10, pts)), 1)


def main():
    reels = json.loads(DATA.read_text())
    now = time.time()
    for r in reels:
        if not r.get("posted"):
            r["score"] = score(r, now)
    pinned = sorted([r for r in reels if not r.get("posted") and r.get("manualQueue")], key=lambda r: r["queue"])
    auto = sorted([r for r in reels if not r.get("posted") and not r.get("manualQueue")],
                  key=lambda r: (-r["score"], r["n"]))
    order = pinned + auto
    for i, r in enumerate(order, 1):
        r["queue"] = i
    for r in reels:
        if r.get("posted"):
            r.pop("queue", None)
    DATA.write_text(json.dumps(reels, indent=1) + "\n")
    for r in order[:8]:
        print(f"queue {r['queue']}: #{r['n']} @{r.get('creator')} score {r['score']}")


if __name__ == "__main__":
    main()
