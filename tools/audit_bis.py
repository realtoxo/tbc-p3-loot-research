#!/usr/bin/env python3
"""Report every anchor whose worn combination is not its measured best.

THE DETECTION HALF OF THE REVISION LOOP. The standings derive from the
best-in-slot captures and cannot drift, but new figures can show a worn
piece beaten in its own table, and that finding must be seen before it can
be ruled on. This prints the gaps and changes nothing: a gap becomes a
capture change only through a recorded ruling and a profile-level
confirmation, per data/judgments/sim-context.yaml.

Usage:
    python3 tools/audit_bis.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

VARIANTS = Path("data/facts/variant-sims.yaml")
FIGURES = Path("data/facts/sim-figures.yaml")

PASSES = (("weapons", "anchors"), ("ranged", "ranged_anchors"),
          ("trinkets", "trinket_anchors"), ("rings", "ring_anchors"))


def label(row: dict) -> str:
    if "trinket_1" in row:
        return f"{row['trinket_1']['name']} + {row['trinket_2']['name']}"
    if "ring_1" in row:
        return f"{row['ring_1']['name']} + {row['ring_2']['name']}"
    if "ranged" in row:
        return row["ranged"]["name"]
    mh = row["main_hand"]["name"]
    if row.get("off_hand"):
        return f"{mh} + {row['off_hand']['name']}"
    return f"{mh} alone"


def main() -> int:
    variants = yaml.safe_load(VARIANTS.read_text())
    figures = yaml.safe_load(FIGURES.read_text())
    tier = max(r.get("boss_armor", 0) for r in figures["results"])
    anchor_dps = {(r["spec"], r["anchor"]): r["dps"]
                  for r in figures["results"]
                  if r.get("boss_armor") == tier}
    gaps = 0
    print(f"worn against best, armor {tier}; a positive gap is the best "
          "row's lead over the anchor")
    for spec, block in variants["specs"].items():
        for anchor in ("bis", "bis-no-glaives"):
            base = anchor_dps.get((spec, anchor))
            if base is None:
                continue
            for name, key in PASSES:
                rows = (block.get(key) or {}).get(anchor)
                if not rows:
                    continue
                gap = rows[0]["dps"] - base
                if gap > 2.0:
                    gaps += 1
                    print(f"  {spec:24s} {anchor:15s} {name:9s} "
                          f"{gap:+7.1f}  {label(rows[0])}")
    if not gaps:
        print("  every profile wears its measured best in every table")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
