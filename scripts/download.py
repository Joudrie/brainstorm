#!/usr/bin/env python3
"""Download reels in reels.json that have no video yet, and record each one's
creator and engagement numbers (views, likes, comments, upload date).

Needs yt-dlp (pip install yt-dlp) and an Instagram login cookie.
  python3 scripts/download.py --sessionid-file PATH   # file holding the sessionid value
  python3 scripts/download.py --cookies PATH          # or a Netscape cookies.txt
  add --stats-only to refresh numbers without downloading videos
The cookie is never written inside the repo.
"""
import json, os, random, re, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "reels.json"
VIDEOS = ROOT / "videos"


def logins(text):
    """The doc holds one login per line: the Instagram sessionid (has %3A in it) and
    optionally the Reddit reddit_session (a long eyJ... token), with or without a label."""
    out = {}
    for line in text.splitlines():
        v = re.sub(r"\s+", "", re.sub(r"^\s*(instagram|reddit)\s*:", "", line, flags=re.I))
        if not v:
            continue
        if v.startswith("eyJ") and v.count(".") == 2:
            out["reddit"] = v
        elif "%3A" in v:
            out["instagram"] = v
    return out


def instagram_session(text):
    v = logins(text).get("instagram")
    if not v:
        sys.exit("No Instagram sessionid found in the login file")
    return v


def cookie_file(args):
    if "--cookies" in args:
        return args[args.index("--cookies") + 1]
    if "--sessionid-file" in args:
        v = instagram_session(Path(args[args.index("--sessionid-file") + 1]).read_text(encoding="utf-8-sig"))
        uid = v.split("%3A")[0]
        fd, p = tempfile.mkstemp(prefix="igc-", suffix=".txt")
        with os.fdopen(fd, "w") as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write(f".instagram.com\tTRUE\t/\tTRUE\t1830000000\tsessionid\t{v}\n")
            f.write(f".instagram.com\tTRUE\t/\tTRUE\t1830000000\tds_user_id\t{uid}\n")
        return p
    sys.exit("Pass --cookies or --sessionid-file")


def fetch(url, out, cookies, stats_only):
    cmd = ["yt-dlp", "--no-progress", "--cookies", cookies, "-j", "--no-simulate" if not stats_only else "--skip-download",
           "-f", "mp4/best", "--merge-output-format", "mp4", "--no-overwrites", "-o", str(out), url]
    if stats_only:
        cmd.remove("-f"); cmd.remove("mp4/best"); cmd.remove("--merge-output-format"); cmd.remove("mp4")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError((res.stderr.strip().splitlines() or ["unknown error"])[-1][:200])
    return json.loads(res.stdout.strip().splitlines()[-1])


def main():
    args = sys.argv[1:]
    stats_only = "--stats-only" in args
    cookies = cookie_file(args)
    reels = json.loads(DATA.read_text())
    VIDEOS.mkdir(exist_ok=True)
    todo = [r for r in reels if (stats_only and not r.get("posted")) or (not stats_only and not r.get("file"))]
    ok = fail = 0
    for r in todo:
        out = VIDEOS / f"{r['n']:03d}-{r['id']}.mp4"
        try:
            m = fetch(r["url"], out, cookies, stats_only)
        except RuntimeError as e:
            fail += 1; r["error"] = str(e); print(f"#{r['n']} FAILED: {e}")
        else:
            r.pop("error", None)
            if not stats_only and out.exists():
                r["file"] = f"videos/{out.name}"
            r["creator"] = m.get("channel") or m.get("uploader_id") or r.get("creator")
            r["stats"] = {k: m.get(k) for k in ("view_count", "like_count", "comment_count", "timestamp")}
            ok += 1; print(f"#{r['n']} ok @{r['creator']} {r['stats']}")
        DATA.write_text(json.dumps(reels, indent=1) + "\n")
        time.sleep(random.uniform(5, 10))   # go easy on Instagram
    print(f"Done: {ok} ok, {fail} failed.")


if __name__ == "__main__":
    main()
