#!/usr/bin/env python3
"""Fetch each item's icon once, into the repository.

An item is recognized by its icon long before its name is read, and a council
scanning a page of claimants is doing exactly that kind of recognition.

THE BYTES LIVE HERE, NOT ON SOMEONE ELSE'S SERVER. The same reasoning that
rejected Wowhead's tooltip script applies: this site is read locally, frequently
from `file://`, and a page that needs a network round trip to show what an item
looks like is a page that is blank on a laptop at a raid night with bad wifi.
445 icons at 56 pixels is about 640 kilobytes, which is a fraction of the "few
megabytes of binary" the repository rules draw the line at, so the icons are
committed and the site is self-contained.

NOT PART OF `just regen`. This reaches the network, and `just regen` must run
offline and produce the same output every time. An icon never changes once
fetched, so this is a one-time cost per new item: it skips everything already on
disk and reports only what it had to add.

Source: Wowhead's icon CDN, which is where the wowsims client this project reads
its item database from points its own icons.

Usage:
    python3 tools/fetch_icons.py --db PATH --out theme/icons
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ITEMS = Path("data/facts/items.csv")
LADDER = Path("theme/filters/ladder.generated.lua")

# 56 pixels. `medium` is 36 and looks soft on a retina display for the sake of
# 200 kilobytes; `large` is the smallest size that stays crisp at the 32 pixels
# the cards draw it at.
SIZE = "large"
CDN = "https://wow.zamimg.com/images/wow/icons/{size}/{icon}.jpg"

# Wowhead is being asked for a few hundred small files. This is not a scrape of
# anything but public static assets, and the pause keeps it neighbourly.
PAUSE_SECONDS = 0.05


def wanted(db: dict, items: Path, ladder: Path) -> dict[str, str]:
    """Every icon the compendium can render, by icon name.

    Two sources, because the pages reach wider than the item table: a card's
    comparison baseline is frequently a crafted or badge item that items.csv
    does not hold, and it is drawn with the same tooltip.
    """
    icon = {row["id"]: row.get("icon", "") for row in db["items"]}
    ids: set[int] = set()
    if items.exists():
        ids |= {int(r["item_id"]) for r in csv.DictReader(items.open())}
    if ladder.exists():
        ids |= {int(n) for n in re.findall(r"item_id = (\d+),", ladder.read_text())}
    out = {}
    for item_id in ids:
        name = icon.get(item_id)
        if name:
            out[name] = name
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--items", type=Path, default=ITEMS)
    ap.add_argument("--ladder", type=Path, default=LADDER)
    ap.add_argument("--out", type=Path, default=Path("theme/icons"))
    args = ap.parse_args()

    if not args.db.exists():
        print(f"error: database not found: {args.db}", file=sys.stderr)
        return 2

    db = json.loads(args.db.read_text())
    icons = sorted(wanted(db, args.items, args.ladder))
    args.out.mkdir(parents=True, exist_ok=True)

    have = {p.stem for p in args.out.glob("*.jpg")}
    missing = [name for name in icons if name not in have]
    print(f"{len(icons)} icon(s) needed, {len(icons) - len(missing)} already here")
    if not missing:
        # An icon nothing references any more is left alone. It costs a
        # kilobyte and deleting it would churn the repository every time the
        # drop table moves.
        return 0

    added, failed = 0, []
    for name in missing:
        url = CDN.format(size=SIZE, icon=name)
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                if response.status != 200:
                    failed.append((name, f"HTTP {response.status}"))
                    continue
                (args.out / f"{name}.jpg").write_bytes(response.read())
                added += 1
        except (urllib.error.URLError, TimeoutError) as error:
            failed.append((name, str(error)))
        time.sleep(PAUSE_SECONDS)

    total = sum(p.stat().st_size for p in args.out.glob("*.jpg"))
    print(f"  {added} fetched -> {args.out}  ({total / 1024:.0f} KB total)")
    if failed:
        # A missing icon is not a build failure. The card renders without it,
        # and saying which ones are absent is more useful than refusing to run.
        print(f"  {len(failed)} could not be fetched:")
        for name, why in failed[:10]:
            print(f"    {name}: {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
