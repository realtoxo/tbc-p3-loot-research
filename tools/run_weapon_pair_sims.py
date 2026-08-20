#!/usr/bin/env python3
"""The special Enhancement weapon round: every matched-speed pair, relative.

WHY THIS ROUND EXISTS. The guild lead ruled on 20 August 2026 that an
Enhancement Shaman pairs two weapons of the SAME speed and wants them slow,
and that the captured best-in-slot pair rides on an Orc assumption this
raid's Draenei does not inherit. The EP Workbook cannot answer which pair
wins, because it prices weapons one at a time and prices neither speed nor
the pair, so the answer comes from the simulator. The ruling and its lineage
live in data/judgments/enhancement-weapon-rules.yaml, and docs/kb/DOMAIN.md
named a simulation as the route to settle the speed rule on 10 August 2026.

WHAT ONE RUN IS. The best-in-slot Enhancement profile with ONLY the two
weapon slots replaced, every other slot, consumable, buff and the seed held
still, so the difference between two rows is attributable to the pair alone.
Every candidate arrives BARE, with no enchant and no gems, exactly as
`run_sims.py --swap` runs a candidate, so the rows compare with EACH OTHER
and never with the enchanted anchor figures in sim-figures.yaml. Replacing
an item with itself through a swap read minus 56.1 DPS on the Arms main
hand, and that difference is the Mongoose enchant, not the item.

THE PAIR LIST IS FACTS, NOT A RANKING. It enumerates every matched-speed
pair the slow one-hand field supports, given the hand each weapon fits, plus
the two mismatched pairs the captures wore, kept as reference rows so the
council can see what the rule change is worth. The output records what each
pair measured. Which pair each anchor wears is the council's call.

Writes data/facts/enhancement-weapon-pairs.yaml. Runs the simulator, so it
sits beside `just sim` and outside `just regen` and `just check`.

Usage:
    python3 tools/run_weapon_pair_sims.py --iterations 10000
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

import json

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_sims import (  # noqa: E402
    BUFFS, DEFAULT_ARMOR, ENCOUNTER_SECONDS, GEAR, ITEMS, ROSTER, SLOT_ORDER,
    TALENTS, build_request, item_names, run, swap_into,
)
import os  # noqa: E402

OUT = Path("data/facts/enhancement-weapon-pairs.yaml")

SPEC = "enhancement_shaman"

PROFILE = "enhancement-shaman.bis"

# EVERY MATCHED PAIR THE SLOW FIELD SUPPORTS. The universe is the one-hand
# weapons a shaman can carry above the 2.3 speed floor, read from items.csv,
# and a pair is legal where the off-hand item is not Main Hand only. A pair
# of two copies of one item is legal where the item is not unique, and both
# doubled items here drop from a boss the raid kills weekly, so two copies is
# a question of weeks rather than of possibility. The two `matched: false`
# rows are what the captures wore before the 20 August 2026 ruling, kept so
# the change is priced rather than asserted.
PAIRS: list[dict] = [
    # 2.8 against 2.8. Syphon of the Nathrezim is the only slow one-hander at
    # this speed, so the only matched pair is two of it, both from Supremus.
    {"mh": 32262, "oh": 32262, "speed": 2.8, "matched": True},
    # 2.7 against 2.7. Rod of the Sun King is the ONLY 2.7 weapon that fits
    # the off hand, so every 2.7 pair is a main hand plus the Rod, or two
    # Rods. The five blacksmithing weapons and both fist weapons are Main
    # Hand only.
    {"mh": 28439, "oh": 29996, "speed": 2.7, "matched": True},
    {"mh": 32946, "oh": 29996, "speed": 2.7, "matched": True},
    {"mh": 32944, "oh": 29996, "speed": 2.7, "matched": True},
    {"mh": 28433, "oh": 29996, "speed": 2.7, "matched": True},
    {"mh": 28438, "oh": 29996, "speed": 2.7, "matched": True},
    {"mh": 29996, "oh": 29996, "speed": 2.7, "matched": True},
    # 2.6 against 2.6, the widest field. Rising Tide, Netherbane and the
    # Gladiator Cleavers are One Hand and fit either hand; the Right Ripper
    # is Main Hand only and the Chopper is Off Hand only.
    {"mh": 32236, "oh": 32236, "speed": 2.6, "matched": True},
    {"mh": 32236, "oh": 29924, "speed": 2.6, "matched": True},
    {"mh": 33737, "oh": 33669, "speed": 2.6, "matched": True},
    {"mh": 33669, "oh": 34015, "speed": 2.6, "matched": True},
    {"mh": 29924, "oh": 29924, "speed": 2.6, "matched": True},
    {"mh": 31965, "oh": 31965, "speed": 2.6, "matched": True},
    # The two pairs the captures wore, both mismatched, kept as references.
    {"mh": 33669, "oh": 32262, "speed": None, "matched": False,
     "note": "the pair the best-in-slot capture wore before the ruling"},
    {"mh": 28433, "oh": 31965, "speed": None, "matched": False,
     "note": "the pair the entry and tier anchors wore before the ruling"},
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gear", type=Path, default=GEAR)
    ap.add_argument("--cli", type=Path,
                    default=Path(os.environ.get(
                        "WOWSIMCLI", "vendor/wowsims/wowsimcli")))
    ap.add_argument("--iterations", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--armor", type=int, default=DEFAULT_ARMOR)
    ap.add_argument("--seconds", type=int, default=ENCOUNTER_SECONDS)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if not args.cli.is_file():
        print(f"error: no simulator at {args.cli}. Run "
              "tools/install_wowsimcli.sh first.", file=sys.stderr)
        return 1
    path = args.gear / f"{PROFILE}.gear.json"
    if not path.is_file():
        print(f"error: no profile at {path}. Run `just regen` first.",
              file=sys.stderr)
        return 1

    gear = json.loads(path.read_text())
    names = item_names()
    rows_by_id = {int(r["item_id"]): r for r in csv.DictReader(ITEMS.open())}
    strings = yaml.safe_load(
        TALENTS.read_text())["wowsims_talent_strings"]["strings"]
    talents = (strings.get(SPEC) or {}).get("string")
    buffs = yaml.safe_load(BUFFS.read_text())
    roster = yaml.safe_load(ROSTER.read_text())
    party_of = {}
    for group in roster.get("groups") or []:
        for member in group.get("members") or []:
            party_of.setdefault(member, group["id"])

    def weapon(item_id: int) -> dict:
        row = rows_by_id.get(item_id) or {}
        out = {"id": item_id, "name": names.get(item_id, str(item_id))}
        if row.get("weapon_speed"):
            out["speed"] = float(row["weapon_speed"])
        if row.get("source"):
            out["source"] = row["source"]
        return out

    results = []
    for pair in PAIRS:
        candidate = swap_into(gear, "main_hand", pair["mh"])
        candidate = swap_into(candidate, "off_hand", pair["oh"])
        label = (f"{names.get(pair['mh'], pair['mh'])} + "
                 f"{names.get(pair['oh'], pair['oh'])}")
        dps, stdev, error = run(args.cli, build_request(
            SPEC, candidate, talents, args.iterations, args.seed, buffs,
            party_of, "bis", args.seconds, args.armor))
        if error:
            raise SystemExit(f"run_weapon_pair_sims.py: {label}: {error}")
        entry = {
            "main_hand": weapon(pair["mh"]),
            "off_hand": weapon(pair["oh"]),
            "matched": pair["matched"],
            "dps": round(dps, 1),
            "standard_error": round(stdev / math.sqrt(args.iterations), 1),
            "stdev": round(stdev, 1),
        }
        if pair["speed"] is not None:
            entry["pair_speed"] = pair["speed"]
        if pair.get("note"):
            entry["note"] = pair["note"]
        results.append(entry)
        print(f"  {label:60s} {dps:9.1f}")

    results.sort(key=lambda row: -row["dps"])
    document = {
        "meta": {
            "what": (
                "Every matched-speed Enhancement weapon pair, simulated on "
                "the best-in-slot profile with only the two weapon slots "
                "replaced, plus the two mismatched pairs the captures wore, "
                "as references. Produced by tools/run_weapon_pair_sims.py "
                "under the 20 August 2026 ruling in "
                "data/judgments/enhancement-weapon-rules.yaml."),
            "read_this_first": (
                "EVERY PAIR RUNS BARE, with no weapon enchant and no gems, "
                "so these figures compare with EACH OTHER and never with "
                "the enchanted anchor figures in sim-figures.yaml. The plus "
                "or minus is ONE STANDARD ERROR, not a confidence interval. "
                "NOT A RULING. Which pair each anchor wears is the "
                "council's call."),
            "base_profile": PROFILE,
            "race": "Draenei",
            "weapons_unsynced": (
                "No syncType is sent, per the 15 August 2026 ruling that "
                "the weapons run unsynced. A matched pair is where the "
                "simulator's Auto mode would begin delaying the off hand, "
                "so the absence is load-bearing here and is stated."),
            "iterations": args.iterations,
            "seed": args.seed,
            "boss_armor": args.armor,
            "encounter_seconds": args.seconds,
        },
        "pairs": results,
    }
    args.out.write_text(yaml.safe_dump(
        document, sort_keys=False, allow_unicode=True, width=78))
    print(f"{len(results)} pair(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
