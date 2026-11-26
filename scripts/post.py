#!/usr/bin/env python3
"""Post reels from reels.json to @vicecitytop through the Instagram Graph API.

The access token is never in this repo: the session's network proxy adds it to
requests to graph.facebook.com.

Usage:
  python3 scripts/post.py --next 1        # post the next unposted reel(s), oldest first
  python3 scripts/post.py --n 7           # post reel #7
  python3 scripts/post.py --n 7 --dry-run # show what would be posted
Videos must already be pushed, so GitHub Pages can serve them to Instagram.
"""
import json, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "reels.json"
IG_USER = "17841466601675122"          # @vicecitytop
API = "https://graph.facebook.com/v21.0"
SITE = "https://joudrie.github.io/brainstorm/"
DEFAULT_TAGS = "#gta6 #gtavi #vicecity #gta #gaming"


def caption_for(r):
    if r.get("caption"):
        return r["caption"]
    credit = f"🎥 @{r['creator']}" if r.get("creator") else ""
    return "\n\n".join(x for x in [credit, DEFAULT_TAGS] if x)


def call(method, path, params=None):
    url = f"{API}/{path}"
    data = None
    if method == "GET" and params:
        url += "?" + urllib.parse.urlencode(params)
    elif params:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode()[:400]) from None


def post(r, dry=False):
    video_url = SITE + (r.get("edited") or r["file"])   # graded/zoomed version when available
    cap = caption_for(r)
    print(f"#{r['n']} -> {video_url}\n--- caption ---\n{cap}\n---------------")
    if dry:
        return None
    c = call("POST", f"{IG_USER}/media", {"media_type": "REELS", "video_url": video_url,
                                          "caption": cap, "share_to_feed": "true"})
    cid = c["id"]
    for _ in range(60):                      # wait up to ~5 min for Instagram to process
        s = call("GET", cid, {"fields": "status_code,status"})
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram couldn't process the video: {s}")
        time.sleep(5)
    else:
        raise RuntimeError("Timed out waiting for Instagram to process the video")
    p = call("POST", f"{IG_USER}/media_publish", {"creation_id": cid})
    info = call("GET", p["id"], {"fields": "permalink"})
    return info.get("permalink")


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    reels = json.loads(DATA.read_text())
    if "--n" in args:
        n = int(args[args.index("--n") + 1])
        targets = [r for r in reels if r["n"] == n]
    else:
        k = int(args[args.index("--next") + 1]) if "--next" in args else 1
        queue = sorted([r for r in reels if not r.get("posted") and r.get("file") and not r.get("flag")],
                       key=lambda r: (r.get("queue", 10**6), r["n"]))
        targets = queue[:k]
    if not targets:
        print("Nothing to post."); return
    for r in targets:
        if not r.get("file"):
            print(f"#{r['n']}: no video downloaded yet, skipping"); continue
        try:
            link = post(r, dry)
        except Exception as e:
            r["postError"] = str(e)[:300]
            DATA.write_text(json.dumps(reels, indent=1) + "\n")
            print(f"#{r['n']} FAILED: {e}"); continue
        if not dry:
            r.pop("postError", None)
            r["posted"] = True
            r["postedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            r["postUrl"] = link
            DATA.write_text(json.dumps(reels, indent=1) + "\n")
            print(f"#{r['n']} posted: {link}")


if __name__ == "__main__":
    main()
