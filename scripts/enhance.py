#!/usr/bin/env python3
"""Apply the house look to a clip: trim black borders, zoom the gameplay in a bit,
and grade it warm/summery (highlights down, saturation up, slightly darker).

  python3 scripts/enhance.py IN.mp4 OUT.mp4
  python3 scripts/enhance.py IN.mp4 OUT.jpg --still 3   # one graded frame at 3s, for previews
"""
import re, subprocess, sys

ZOOM = 1.12
# Roughly the user's photo settings: highlights -44, exposure -11, brilliance -14, saturation +23, warmth +3
GRADE = ("curves=all='0/0 0.25/0.235 0.5/0.47 0.75/0.69 1/0.86',"
         "eq=saturation=1.28:contrast=1.05:gamma=0.98,"
         "colorbalance=rs=0.03:gs=0.01:bs=-0.04:rm=0.04:gm=0.01:bm=-0.04:rh=0.02:bh=-0.03,"
         "unsharp=5:5:0.4")


def crop_of(src):
    out = subprocess.run(["ffmpeg", "-i", src, "-vf", "cropdetect=24:2:0", "-t", "6", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    found = re.findall(r"crop=\d+:\d+:\d+:\d+", out)
    return max(set(found), key=found.count) if found else "crop=iw:ih:0:0"


def vf(src):
    return (f"{crop_of(src)},scale=1080*{ZOOM}:-2,crop=1080:min(ih\\,1920),"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,{GRADE},fps=30,format=yuv420p,setsar=1")


def main():
    src, dst = sys.argv[1], sys.argv[2]
    if "--still" in sys.argv:
        t = sys.argv[sys.argv.index("--still") + 1]
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", t, "-i", src, "-frames:v", "1", "-vf", vf(src), dst]
    else:
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", vf(src), "-c:v", "libx264", "-preset", "veryfast",
               "-crf", "25", "-maxrate", "5M", "-bufsize", "10M", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "128k", "-movflags", "+faststart", dst]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
