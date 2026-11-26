#!/usr/bin/env python3
"""Render the rotating logo cube for the news style as a 12-second looping PNG sequence:
hold 5.4s, quarter-turn 0.6s (with perspective), hold, turn... faces alternate
Weazel News / @VICECITYTOP.   python3 scripts/make_cube.py OUT_DIR"""
import math, sys
from pathlib import Path
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
S, C, FPS = 130, 190, 30            # face size, canvas size, frame rate
D = 3.2                              # camera distance (cube side = 1)
f = (S / 2) * (D - 0.5) / 0.5        # so the front face is exactly S px wide when facing us

weazel = Image.open(ROOT / "assets/brand/weazel-news.jpg").convert("RGBA").resize((S, S))
tag = Image.new("RGBA", (S, S), (20, 70, 170, 255)); d = ImageDraw.Draw(tag)
A = ImageFont.truetype(str(ROOT / "assets/fonts/Anton-Regular.ttf"), 34)
d.text((S // 2, 46), "@VICE", font=A, fill="white", anchor="mm"); d.text((S // 2, 88), "CITYTOP", font=A, fill="white", anchor="mm")
faces = [np.array(weazel), np.array(tag)]

def project(p):
    x, y, z = p
    k = f / (D - z)
    return [C / 2 + x * k, C / 2 - y * k]

def rot(p, a):
    x, y, z = p
    return (x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a))

def frame(angle, front_idx):
    canvas = np.zeros((C, C, 4), np.uint8)
    h = 0.5
    # front face (normal +z) and right face (normal +x), cube rotating left by `angle`
    quads = {
        "front": [(-h, h, h), (h, h, h), (h, -h, h), (-h, -h, h)],
        "right": [(h, h, h), (h, h, -h), (h, -h, -h), (h, -h, h)],
    }
    order = []
    for name, pts in quads.items():
        rp = [rot(p, -angle) for p in pts]
        n = (0, 0, 1) if name == "front" else (1, 0, 0)
        nz = rot(n, -angle)[2]
        if nz > 0.01:
            order.append((nz, name, rp))
    for nz, name, rp in sorted(order):
        img = faces[front_idx % 2] if name == "front" else faces[(front_idx + 1) % 2]
        src = np.float32([[0, 0], [S, 0], [S, S], [0, S]])
        dst = np.float32([project(p) for p in rp])
        M = cv2.getPerspectiveTransform(src, dst)
        warped = cv2.warpPerspective(img, M, (C, C), flags=cv2.INTER_LINEAR)
        shade = 0.55 + 0.45 * nz                      # side in shadow as it turns away
        warped[..., :3] = (warped[..., :3] * shade).astype(np.uint8)
        a = warped[..., 3:4] / 255.0
        canvas[..., :3] = (warped[..., :3] * a + canvas[..., :3] * (1 - a)).astype(np.uint8)
        canvas[..., 3] = np.maximum(canvas[..., 3], warped[..., 3])
    return Image.fromarray(canvas)

ease = lambda u: u * u * (3 - 2 * u)
n = 0
for step in range(2):                    # two turns = 12s loop, faces A,B,A
    for i in range(int(5.4 * FPS)):
        frame(0, step).save(OUT / f"c{n:04d}.png"); n += 1
    for i in range(int(0.6 * FPS)):
        frame(ease((i + 1) / (0.6 * FPS)) * math.pi / 2, step).save(OUT / f"c{n:04d}.png"); n += 1
print(n, "frames")
