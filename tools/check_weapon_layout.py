#!/usr/bin/env python3
"""Check every captured set holds a weapon layout the spec could equip.

WHY THIS EXISTS. Nothing checked it. This project has already shipped one
dual-wield error, recorded as task 13, and a capture is edited by hand often
enough that a two-hander landing beside an off-hand is a matter of time rather
than of luck. When it happens the set still parses, still sums, and still
prints a hit figure, so it fails the way this project's defects usually fail:
quietly and with a plausible number.

WHAT IT CHECKS, per spec and per anchor:

  1. A two-hand main hand forbids an off-hand item. The captures spell this out
     as "none, two-hand weapon equipped" rather than omitting the slot, which is
     better, because an absent key cannot be told apart from a forgotten one.
  2. An off-hand item requires a one-hand main hand. The reverse of rule 1, and
     it catches a main hand quietly upgraded to a two-hander.
  3. A shield sits only on a spec whose class can hold one. A Druid cannot, and
     a Druid holding a shield is the shape of error rule 1 produces.
  4. Every weapon names an id that resolves in items.csv, so a layout cannot be
     judged correct on a name alone.

WHAT IT DOES NOT CHECK. Class weapon proficiency, which needs a table this
project does not hold: whether a Rogue may wield an axe is not answerable from
items.csv. Rule 3 is the one proficiency case hard-coded, because a shield is
recorded in the slot rather than the weapon type and is the case that has a
plausible way of going wrong.

Usage:
    python3 tools/check_weapon_layout.py
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import yaml

CAPTURES = Path("data/facts/sim-profiles/hit-capture")
ITEMS = Path("data/facts/items.csv")

# AN EMPTY SLOT IS ONE WITH NO ID, not one whose text starts with a word. The
# captures write the reason in prose and do not agree on the wording: the
# two-hand specs say "none, two-hand weapon equipped" and the Survival Hunter
# says "(two-handed weapon equipped; off hand empty)". Matching on a prefix
# reported both Survival anchors as unresolvable, which is a defect in the
# check rather than in the capture. The id is the field that means something.
EMPTY_WORDS = ("none", "empty", "two-hand", "two hand", "n/a")

# Classes that can hold a shield in 2.4.3. A Druid cannot, which is the case
# this exists to catch.
SHIELD_CLASSES = {"warrior", "paladin", "shaman"}


# A spec name does not always contain its class. feral-bear and feral-cat are
# Druids and say so nowhere, which made the shield message read "which a
# cannot equip" the first time it fired.
EXTRA_CLASS = {"feral-bear": "druid", "feral-cat": "druid",
               "balance-druid": "druid", "restoration-druid": "druid"}


def spec_class(spec: str) -> str:
    if spec in EXTRA_CLASS:
        return EXTRA_CLASS[spec]
    for name in ("warrior", "paladin", "shaman", "druid", "priest", "mage",
                 "warlock", "hunter", "rogue"):
        if name in spec:
            return name
    return "spec with no class recorded"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--captures", type=Path, default=CAPTURES)
    args = ap.parse_args()

    items = {r["item_id"]: r for r in csv.DictReader(ITEMS.open())}
    problems: list[str] = []
    checked = 0

    for path in sorted(args.captures.glob("*.yaml")):
        spec = path.stem
        doc = yaml.safe_load(path.read_text())
        for anchor, block in (doc.get("anchors") or {}).items():
            slots = block.get("hit_by_slot") or {}
            main, off = slots.get("main_hand") or {}, slots.get("off_hand") or {}
            if not main:
                continue
            checked += 1
            where = f"{spec} at {anchor}"

            def resolve(entry: dict, slot: str) -> dict | None:
                name = str(entry.get("item") or "")
                if entry.get("id") in (None, "", 0):
                    # No id means the slot is empty, and the prose should say
                    # so. If it does not, the slot names an item nobody
                    # resolved, which is worth a line of its own.
                    if name and not any(w in name.lower() for w in EMPTY_WORDS):
                        problems.append(
                            f"{where}: {slot} names {name!r} and carries no "
                            "id, so it is neither an item nor an empty slot")
                    return None
                row = items.get(str(entry["id"]))
                if row is None:
                    problems.append(
                        f"{where}: {slot} names {name!r} with id "
                        f"{entry['id']!r}, which is not in items.csv, so "
                        "the layout cannot be checked")
                return row

            main_row, off_row = resolve(main, "main hand"), resolve(off, "off hand")
            if main_row is None:
                continue

            two_handed = main_row["hand_type"] == "Two Hand"
            if two_handed and off_row is not None:
                problems.append(
                    f"{where}: main hand {main_row['name']!r} is a two-hander "
                    f"and the off hand holds {off_row['name']!r}. A spec cannot "
                    "wear both")
            # A SHIELD IS weapon_type, NOT slot. items.csv files every
            # weapon under slot "Weapon", so a rule reading slot == "Shield"
            # matches nothing and passes everything. It did, until a negative
            # test put a shield on the Bear and the check said the set was fine.
            if off_row is not None and off_row["weapon_type"] == "Shield":
                if spec_class(spec) not in SHIELD_CLASSES:
                    problems.append(
                        f"{where}: off hand holds the shield "
                        f"{off_row['name']!r}, which a {spec_class(spec)} "
                        "cannot equip")

    print(f"{checked} weapon layout(s) checked across "
          f"{len(list(args.captures.glob('*.yaml')))} captured spec(s)")
    if problems:
        print(f"\n{len(problems)} problem(s):", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    print("every set holds a layout its spec could equip: no two-hander beside "
          "an off hand, and no shield on a class that cannot hold one")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
