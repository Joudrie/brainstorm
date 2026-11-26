#!/usr/bin/env python3
"""Weazel News preset: put a (graded) clip into the in-universe news broadcast frame.

  python3 scripts/news_style.py IN.mp4 OUT.mp4 --headline "GATOR SPOTTED IN LEONIDA" \
      --place LEONIDA --text "gator just chilling" --emoji "🐊" \
      [--blur X,Y,W,H[,T0,T1]] ... [--text-y Y] [--no-mirror]

--blur boxes and --text-y are in the input video's pixel coordinates (1080x1920).
A blur box with T0,T1 is only blurred between those seconds (for text that pops up mid-clip).
Every creator caption and emoji must be covered by a --blur box; our --text replaces it.
"""
import argparse, json, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ANTON = ROOT / "assets/fonts/Anton-Regular.ttf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
BRAND = ROOT / "assets/brand"
W, H = 1080, 1920
NAVY, RED, BLUE, PAPER = (12, 18, 40, 255), (200, 20, 30, 255), (20, 70, 170, 255), (245, 245, 245, 255)
TOP_BAR = (250, 330)            # BREAKING NEWS banner
LOWER_Y, LH, TICK = 1440, 130, 46
TICKER = "@VICECITYTOP   •   DAILY GTA 6 CLIPS   •   DM ME SUBMISSIONS   •"


def font(s):
    return ImageFont.truetype(str(ANTON), s)


def gameplay_rows(src):
    """First/last rows of the picture (everything that isn't black bars)."""
    tmp = Path(tempfile.mkdtemp()) / "f.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1", "-i", src, "-frames:v", "1", str(tmp)], check=True)
    g = Image.open(tmp).convert("L"); px = g.load()
    rows = [y for y in range(g.height) if sum(1 for x in range(0, g.width, 8) if px[x, y] > 30) > g.width / 8 * 0.15]
    return (rows[0], rows[-1] + 1) if rows else (0, g.height)


def fit_text(d, text, size, max_w):
    while size > 30 and d.textlength(text, font=font(size)) > max_w:
        size -= 2
    return size


def draw_text_emoji(img, cy, text, emoji, size=70):
    d = ImageDraw.Draw(img)
    eh = int(size * 0.95) if emoji else 0
    size = fit_text(d, text, size, W - 80 - (eh + 14 if emoji else 0))
    f = font(size); tw = d.textlength(text, font=f)
    total = tw + (14 + eh if emoji else 0); x0 = (W - total) / 2
    d.text((x0, cy), text, font=f, fill="white", anchor="lm", stroke_width=5, stroke_fill=(10, 10, 15))
    if emoji:
        em = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(em).text((0, 0), emoji, font=ImageFont.truetype(EMOJI, 109), embedded_color=True)
        em = em.crop(em.getbbox()).resize((eh, eh), Image.LANCZOS)
        img.alpha_composite(em, (int(x0 + tw + 14), int(cy - eh / 2)))


def overlay_png(path, a, text_cy):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    d.rectangle((0, TOP_BAR[0], W, TOP_BAR[1]), fill=RED)
    d.text((32, 290), "BREAKING NEWS", font=font(58), fill="white", anchor="lm")
    d.ellipse((910, 276, 938, 304), fill="white"); d.text((950, 290), "LIVE", font=font(40), fill="white", anchor="lm")
    if a.text:
        draw_text_emoji(ov, text_cy, a.text.upper(), a.emoji)
    d.rectangle((0, LOWER_Y, LH, LOWER_Y + LH), fill=NAVY)
    d.rectangle((LH, LOWER_Y, W, LOWER_Y + LH), fill=PAPER); d.rectangle((LH, LOWER_Y, LH + 10, LOWER_Y + LH), fill=RED)
    d.text((LH + 34, LOWER_Y + 34), a.place.upper(), font=font(32), fill=RED, anchor="lm")
    hs = fit_text(d, a.headline.upper(), 58, W - LH - 60)
    d.text((LH + 34, LOWER_Y + 86), a.headline.upper(), font=font(hs), fill=NAVY, anchor="lm")
    d.rectangle((0, LOWER_Y + LH, W, LOWER_Y + LH + TICK), fill=BLUE)
    ov.save(path)


def ensure_assets():
    cube = BRAND / "cube"
    if not (cube / "c0359.png").exists():
        subprocess.run([sys.executable, "-I", str(ROOT / "scripts/make_cube.py"), str(cube)], check=True)
    for name, col, alpha in (("glowA", (80, 150, 255), 120), ("glowB", (60, 220, 255), 95), ("glowC", (150, 90, 255), 85)):
        p = BRAND / f"{name}.png"
        if not p.exists():
            g = Image.new("RGBA", (1000, 1000), (0, 0, 0, 0))
            ImageDraw.Draw(g).ellipse((170, 170, 830, 830), fill=col + (alpha,))
            g.filter(ImageFilter.GaussianBlur(130)).save(p)
    t = BRAND / "ticker.txt"
    t.write_text(TICKER)
    return cube, t


def main():
    p = argparse.ArgumentParser()
    p.add_argument("src"); p.add_argument("out")
    p.add_argument("--headline", required=True); p.add_argument("--place", default="LEONIDA")
    p.add_argument("--text", default=""); p.add_argument("--emoji", default="")
    p.add_argument("--blur", action="append", default=[]); p.add_argument("--text-y", type=int)
    p.add_argument("--no-mirror", action="store_true")
    a = p.parse_args()

    cube, ticker = ensure_assets()
    top, bot = gameplay_rows(a.src)
    gh = bot - top
    avail = LOWER_Y - TOP_BAR[1]
    if gh > avail:                                   # tall clip: keep the middle
        top += (gh - avail) // 2; gh = avail
    gy = TOP_BAR[1] + (avail - gh) // 2              # where the picture sits on the canvas
    text_cy = (a.text_y - top + gy) if a.text_y else gy + 75

    tmp = Path(tempfile.mkdtemp()); ov = tmp / "ov.png"; overlay_png(ov, a, text_cy)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.src],
                         capture_output=True, text=True).stdout.strip()

    chain, last = [], "0:v"
    for i, b in enumerate(a.blur):
        v = [float(x) for x in b.split(",")]
        x, y, w, h = map(int, v[:4])
        when = f":enable='between(t,{v[4]},{v[5]})'" if len(v) == 6 else ""
        chain.append(f"[{last}]split[s{i}a][s{i}b];[s{i}b]crop={w}:{h}:{x}:{y},boxblur=18:3[s{i}c];[s{i}a][s{i}c]overlay={x}:{y}{when}[s{i}]")
        last = f"s{i}"
    flip = "" if a.no_mirror else ",hflip"
    chain.append(f"[{last}]crop=1080:{gh}:0:{top}{flip}[g]")
    chain += [
        "[2:v][3:v]overlay=x='-300+320*sin(t/5)':y='60+180*cos(t/6.5)':shortest=1[b1]",
        "[b1][4:v]overlay=x='420+300*cos(t/7)':y='1000+200*sin(t/4.5)':shortest=1[b2]",
        "[b2][5:v]overlay=x='150+380*sin(t/8+2)':y='500+420*cos(t/9)':shortest=1[b3]",
        f"[b3][g]overlay=0:{gy}:shortest=1[v2]", "[v2][1:v]overlay=0:0:shortest=1[v3]",
        f"[v3][6:v]overlay=x=-30:y={LOWER_Y - 30}:shortest=1[v4]",
        f"[v4]drawtext=fontfile={ANTON}:textfile={ticker}:fontsize=30:fontcolor=white:"
        f"y={LOWER_Y + LH}+({TICK}-th)/2:x=w-mod(t*140\\,w+tw),format=yuv420p[out]",
    ]
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", a.src, "-loop", "1", "-i", str(ov),
           "-f", "lavfi", "-i", "color=c=0x0c1228:s=1080x1920:r=30",
           "-loop", "1", "-i", str(BRAND / "glowA.png"), "-loop", "1", "-i", str(BRAND / "glowB.png"),
           "-loop", "1", "-i", str(BRAND / "glowC.png"),
           "-stream_loop", "-1", "-framerate", "30", "-i", str(cube / "c%04d.png"),
           "-filter_complex", ";".join(chain), "-map", "[out]", "-map", "0:a?",
           "-af", "loudnorm=I=-14:LRA=11:TP=-1.5", "-t", dur,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-maxrate", "5M", "-bufsize", "10M",
           "-c:a", "aac", "-ar", "44100", "-b:a", "128k", "-movflags", "+faststart", a.out]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
