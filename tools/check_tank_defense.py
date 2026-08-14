#!/usr/bin/env python3
"""Report every tank anchor against the defense rating crit immunity needs.

THE COMMIT THAT FOUND THIS PROBLEM WAS TITLED "nothing was watching", and
nothing was. Both operands already existed: `set-stats.yaml` publishes defense
rating per spec per anchor, and `crit.yaml` publishes 284 for a plate tank with
Anticipation at five ranks and 154 for a Bear holding Survival of the Fittest.
Nothing joined them, so a repair pass fixed one plate tank and left the other
forty rating below the line, and an audit had to find it.

WHY THIS REPORTS AND DOES NOT FAIL. A tank below the line on ITEMS is not a
tank without crit immunity. Gems, enchants and Flask of Fortification are
excluded from every figure by the same rule that excludes them from the hit
figures, and a tank gems for defense harder than any other role. So a shortfall
here is a finding to be read, not a broken build, and the routes that close it
are enumerated beside the number rather than assumed.

WHAT IT DOES FAIL ON is a shortfall larger than every discretionary route
combined, because that is no longer a gemming question. It means the set cannot
reach the threshold and the gear has to change.

RESILIENCE IS NAMED, NOT ADDED. It is a separate crit-avoidance route at 39.4
rating per percent and the Bear carries it on a permitted arena weapon, but
mixing it into a defense total would combine two mechanisms into one number and
hide which is doing the work.

Usage:
    python3 tools/check_tank_defense.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

STATS = Path("data/facts/set-stats.yaml")
CRIT = Path("data/facts/crit.yaml")

ANCHORS = ("entry", "tier_hands_and_head")

# Defense rating a tank can add without changing an item, from
# enchants-gems.yaml. Named individually so a reader can see which are assumed
# and which are gated, rather than trusting one total.
#
# Enchant Chest - Defense at 15 is DELIBERATELY ABSENT: enchants-gems.yaml
# marks it phase_3_available false, so it cannot close a Phase 3 gap.
DISCRETIONARY = [
    ("Glyph of the Defender, head", 16),
    ("Enchant Bracer - Major Defense", 12),
    ("Greater Inscription of Warding, shoulder", 15),
    ("Tenacious Earthstorm Diamond, meta", 12),
    ("Vindicator's Armor Kit, four slots", 32),
    ("Flask of Fortification", 10),
]
DISCRETIONARY_TOTAL = sum(rating for _, rating in DISCRETIONARY)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stats", type=Path, default=STATS)
    ap.add_argument("--crit", type=Path, default=CRIT)
    args = ap.parse_args()

    thresholds = yaml.safe_load(args.crit.read_text())["tank_defensive_thresholds"]
    plate = thresholds["plate"]["defense_rating_required"]
    bear = thresholds["bear"]["defense_rating_required"]
    required = {
        "protection_warrior": plate,
        "protection_paladin": plate,
        "feral_bear": bear,
    }

    specs = yaml.safe_load(args.stats.read_text())["specs"]
    print(f"{'tank':22} {'needs':>6} " + " ".join(f"{a:>20}" for a in ANCHORS))
    short: list[str] = []
    unreachable: list[str] = []
    for spec, threshold in required.items():
        block = specs.get(spec)
        if block is None:
            unreachable.append(f"{spec} is not in {args.stats}")
            continue
        cells = []
        for anchor in ANCHORS:
            carried = (block.get(anchor) or {}).get("defense", 0)
            gap = threshold - carried
            if gap <= 0:
                cells.append(f"{carried:>5} clear{'':>9}")
                continue
            cells.append(f"{carried:>5} short by {gap:<6}")
            line = (f"{spec} at {anchor} carries {carried} defense rating "
                    f"against {threshold}, short by {gap}")
            if gap > DISCRETIONARY_TOTAL:
                unreachable.append(
                    f"{line}, which is more than the {DISCRETIONARY_TOTAL} "
                    "every discretionary route supplies together")
            else:
                short.append(line)
        print(f"{spec:22} {threshold:>6} " + " ".join(cells))

    if short:
        print(f"\n{len(short)} anchor(s) short on items alone, inside the "
              f"{DISCRETIONARY_TOTAL} rating the discretionary routes supply:")
        for line in short:
            print(f"  {line}")
        for name, rating in DISCRETIONARY:
            print(f"    {rating:>3}  {name}")
        print("  Resilience is a separate route and is not added here.")

    if unreachable:
        print(f"\n{len(unreachable)} anchor(s) cannot reach the threshold:",
              file=sys.stderr)
        for line in unreachable:
            print(f"  {line}", file=sys.stderr)
        print("\nThat is a gear problem rather than a gemming one. Change the "
              "set, not this check.", file=sys.stderr)
        return 1

    print("\nno tank is further from crit immunity than gems and enchants reach")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
