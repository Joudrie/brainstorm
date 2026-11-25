#!/usr/bin/env python3
"""Pull likes/comments for everything posted to @vicecitytop and report which
posting hours (Eastern) do best. Saves each reel's numbers into reels.json.

  python3 scripts/stats.py
The token is injected by the network proxy for graph.facebook.com.
"""
import json, urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "reels.json"
IG_USER = "17841466601675122"
URL = (f"https://graph.facebook.com/v21.0/{IG_USER}/media"
       "?fields=permalink,like_count,comments_count,timestamp,media_product_type&limit=100")


def eastern(ts):
    t = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z").astimezone(timezone.utc)
    # US Eastern: UTC-5 in winter, UTC-4 from 2nd Sunday of March to 1st Sunday of November
    y = t.year
    start = datetime(y, 3, 8, 7, tzinfo=timezone.utc); start += timedelta(days=(6 - start.weekday()) % 7)
    end = datetime(y, 11, 1, 6, tzinfo=timezone.utc); end += timedelta(days=(6 - end.weekday()) % 7)
    return t + timedelta(hours=-4 if start <= t < end else -5)


def main():
    media, url = [], URL
    while url:
        with urllib.request.urlopen(url, timeout=60) as r:
            d = json.load(r)
        media += d.get("data", [])
        url = d.get("paging", {}).get("next")
    reels = json.loads(DATA.read_text())
    by_link = {r.get("postUrl"): r for r in reels if r.get("postUrl")}
    now = datetime.now(timezone.utc)
    slots = defaultdict(list)
    for m in media:
        age_h = (now - datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")).total_seconds() / 3600
        score = (m.get("like_count") or 0) + 3 * (m.get("comments_count") or 0)
        r = by_link.get(m.get("permalink"))
        if r is not None:
            r["postStats"] = {"likes": m.get("like_count"), "comments": m.get("comments_count"),
                              "checkedAt": now.isoformat(timespec="minutes"), "ageHours": round(age_h, 1)}
        if age_h >= 24:                      # only judge posts that have had a full day
            et = eastern(m["timestamp"])
            slots[(et.strftime("%a") in ("Sat", "Sun"), et.hour)].append(score)
    DATA.write_text(json.dumps(reels, indent=1) + "\n")
    print(f"{len(media)} posts on the account. Engagement (likes + 3x comments) by posting hour, posts at least 24h old:")
    for (weekend, hour), v in sorted(slots.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])):
        print(f"  {'weekend' if weekend else 'weekday'} {hour:02d}:00 ET  avg {sum(v)/len(v):.1f}  ({len(v)} posts)")


if __name__ == "__main__":
    main()
