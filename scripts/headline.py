#!/usr/bin/env python3
"""Pick a fallback news headline for a clip when we can't tell what's happening.
Never repeats one (used lines are tracked in assets/used_headlines.json). Seasonal
lines are preferred while they're in season.

  python3 scripts/headline.py            # prints a headline and marks it used
  python3 scripts/headline.py --peek     # prints one without marking it
"""
import json, random, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "assets/fallback_headlines.json"
USED = ROOT / "assets/used_headlines.json"


def in_season(rng, today):
    md = today.strftime("%m-%d")
    a, b = rng["from"], rng["to"]
    return a <= md <= b if a <= b else (md >= a or md <= b)


def main():
    bank = json.loads(BANK.read_text())
    used = set(json.loads(USED.read_text())) if USED.exists() else set()
    today = date.today()
    seasonal = [l for s in bank["seasonal"] if in_season(s, today) for l in s["lines"] if l not in used]
    always = [l for l in bank["always"] if l not in used]
    # roughly 1 in 3 picks is seasonal while a season is on
    pool = seasonal if seasonal and (not always or random.random() < 0.34) else always
    if not pool:
        sys.exit("All fallback headlines are used. Add more to assets/fallback_headlines.json")
    line = random.choice(pool)
    if "--peek" not in sys.argv:
        used.add(line); USED.write_text(json.dumps(sorted(used), indent=1) + "\n")
    print(line)


if __name__ == "__main__":
    main()
