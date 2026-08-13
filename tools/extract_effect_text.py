#!/usr/bin/env python3
"""Turn the captured Wowhead tooltips into the effect text a card can print.

WHAT IT READS. The bytes captured by `tools/fetch_effect_text.py` under
`data/research/wowhead-effects/`, which are never edited after capture. Nothing
here reaches the network, so this rerun is deterministic and `just check` can
diff it.

WHAT IT TAKES OUT. Wowhead marks each effect line with a `useText` span holding
a trigger word and the sentence: "Equip", "Use" or "Chance on hit". That triple
is the whole extraction. Everything else in the payload is stats and chrome the
compendium already has from the WoWSims database, and taking it from here as
well would put the same fact at two boundaries.

WHY THE TRIGGER IS KEPT SEPARATE FROM THE SENTENCE. A council asks a different
question of an item it must press than of one that works by being worn, and the
database's own `onUse` and `proc` flags do not exist for these items, which is
why they were captured at all.

Usage:
    python3 tools/extract_effect_text.py --out data/facts/effect-text.csv
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from pathlib import Path

CAPTURES = Path("data/research/wowhead-effects")

FIELDS = ["item_id", "item_name", "trigger", "text", "captured"]

# The span Wowhead wraps every effect line in. There is one per effect, so the
# Netherstrand Longbow yields four and nothing has to guess how many there are.
USE_TEXT = re.compile(r'<span id="useText\d+"[^>]*>(.*?)</span>', re.S)

# The trigger word and the sentence after it. Wowhead writes the sentence
# inside an anchor pointing at the spell, so tags are stripped before this runs.
TRIGGER = re.compile(r"^(Equip|Use|Chance on hit):\s*(.+)$", re.S)


def plain(fragment: str) -> str:
    """The sentence, with Wowhead's comment markers, tags and entities gone."""
    text = re.sub(r"<!--.*?-->", "", fragment, flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    # &nbsp; survives unescape as a non-breaking space and reads as a double
    # space in the rendered card, so it is folded with the rest of the runs.
    return " ".join(html.unescape(text).split())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--captures", type=Path, default=CAPTURES)
    ap.add_argument("--out", type=Path, default=Path("data/facts/effect-text.csv"))
    ap.add_argument("--items", type=Path, default=Path("data/facts/items.csv"))
    args = ap.parse_args()

    # AN ITEM THAT LEFT THE ITEM TABLE LEAVES THIS TABLE WITH IT. Netherstrand
    # Longbow was captured on 13 August 2026 and excluded from the drop table
    # the same day, once the guild lead identified it as one of Kael'thas's
    # encounter weapons rather than loot. The capture is kept, because nothing
    # under data/research/ is edited after the fact, and it is simply not
    # published. A fact table naming an item the item table does not hold is a
    # dangling reference waiting to be cited.
    known = {int(r["item_id"]) for r in csv.DictReader(args.items.open())}

    rows, unparsed, dropped = [], [], []
    for path in sorted(args.captures.glob("*/item-*.json")):
        captured = path.parent.name
        item_id = int(path.stem.split("-")[1])
        payload = json.loads(path.read_text())
        if item_id not in known:
            dropped.append(f"{item_id} {payload.get('name', '')}")
            continue
        found = 0
        for fragment in USE_TEXT.findall(payload.get("tooltip", "")):
            sentence = plain(fragment)
            match = TRIGGER.match(sentence)
            if not match:
                continue
            found += 1
            rows.append({
                "item_id": item_id,
                "item_name": payload.get("name", ""),
                "trigger": match.group(1),
                "text": match.group(2).strip(),
                "captured": captured,
            })
        if not found:
            # A capture that yields nothing is a defect in this parser or a
            # change at Wowhead, and either way it must not pass as an item
            # with no effect. That is the state the capture existed to end.
            unparsed.append(f"{item_id} {payload.get('name', '')}")

    rows.sort(key=lambda r: (r["item_id"], r["trigger"], r["text"]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    items = len({r["item_id"] for r in rows})
    print(f"{len(rows)} effect line(s) across {items} item(s) -> {args.out}")
    for line in dropped:
        print(f"  captured and not published, not in the item table: {line}")
    if unparsed:
        print(f"\n{len(unparsed)} capture(s) yielded no effect line:",
              file=sys.stderr)
        for line in unparsed:
            print(f"  {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
