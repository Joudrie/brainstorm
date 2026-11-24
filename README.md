# Vice City Reel Queue

A queue for reposting reels from the VICE CITY TOP CLIPS chat to the secondary account.

**Flow:** Muse sends a list of reel links → they go into `reels.json` → each one gets downloaded into `videos/` → open the page, save the video, post it, tap **Posted**.

## The page (`index.html`)

Each reel has three buttons:
- **Copy**: copies the Instagram link.
- **Save video** (once the video is in `videos/`) or **Download** (opens your downloader site with the link filled in; set the site under "Downloader site").
- **Posted**: marks it done. Progress is kept in that browser.

To view it, turn on GitHub Pages (Settings → Pages → deploy from this branch) or run `python3 -m http.server` in the repo and open http://localhost:8000.

## Adding a batch

```
python3 scripts/add_reels.py "Nov 25" < muse_message.txt
```
Paste Muse's whole message; duplicates are skipped. You can also paste it on the page, but that only saves on that device.

## Downloading the videos

```
pip install yt-dlp
python3 scripts/download.py
```
Instagram blocks logged-out downloads from servers, so put a `cookies.txt` (exported Instagram login from a throwaway account) in the repo root first. It's git-ignored and never committed. Each saved video is written to `videos/` and linked in `reels.json`.

## Files

- `index.html`: the queue page
- `reels.json`: the reel list (number, link, day, posted, video file)
- `scripts/add_reels.py`: add links from a Muse message
- `scripts/download.py`: download missing videos
- `videos/`: downloaded reels
