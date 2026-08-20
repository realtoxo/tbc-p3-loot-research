#!/usr/bin/env python3
"""Weapon pair variants: matched pairs on each anchor profile, per spec.

WHY THIS ROUND EXISTS. The guild lead ruled on 20 August 2026 that an
Enhancement Shaman pairs two weapons of the SAME speed and wants them slow,
and that the captured best-in-slot pair rides on an Orc assumption this
raid's Draenei does not inherit. The EP Workbook cannot answer which pair
wins, because it prices weapons one at a time and prices neither speed nor
the pair, so the answer comes from the simulator. The ruling and its lineage
live in data/judgments/enhancement-weapon-rules.yaml. The registry below is
keyed by spec because the guild lead said the same day to expect more
classes to carry a weapon pair round.

WHAT ONE RUN IS: A VARIANT OF AN EXISTING ANCHOR, ruled by the guild lead on
20 August 2026, "our weapons analysis should simply be variants on our
existing entry, tier, and bis profile sims". Each run is that anchor's own
exported profile with ONLY the two weapon ids replaced. THE SLOT KEEPS ITS
ENCHANT, the opposite choice from run_sims.py --swap and deliberate: a
variant models the raider enchanting whatever pair is worn, so every variant
is directly comparable with the anchor figure in sim-figures.yaml, produced
from the same request at the same seed. The captured pair needs no variant
row of its own, because the anchor figure IS that pair.

WHICH PAIRS RUN WHERE. The entry anchor is worn before Phase 3, so a pair
marked `phase3` is skipped there: no Black Temple drop and no Season 3
weapon. The tier and best-in-slot anchors take the whole field, because the
tier anchor is not constrained by progression, per the guild lead's 14
August 2026 ruling. The pair list is facts, not a ranking; which pair each
anchor wears is the council's call.

Writes data/facts/weapon-pair-sims.yaml and nothing else. The pages that
show these figures are written by tools/generate_sim_pages.py, the same
generator that owns every other sim page. Runs the simulator, so it runs
inside `just sim` and `just sim-weapons` and outside `just regen` and
`just check`.

Usage:
    python3 tools/run_weapon_pair_sims.py --iterations 10000
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_sims import (  # noqa: E402
    BUFFS, DEFAULT_ARMOR, ENCOUNTER_SECONDS, GEAR, ITEMS, ROSTER, SLOT_ORDER,
    TALENTS, build_request, item_names, run,
)

OUT = Path("data/facts/weapon-pair-sims.yaml")

# The anchors the variants run on, as the gear stems and page slugs spell
# them. Hyphens, because that is the naming scheme of data/sim/gear and of
# the page slugs in generate_sim_pages.py; the consumable key converts back
# to underscores inside build_request's caller.
ANCHORS = ("entry", "tier-hands-and-head", "bis")

# ONE ENTRY PER SPEC THAT RUNS A WEAPON PAIR ROUND. `pairs` is every pair
# the round measures, `phase3` marks a pair the entry anchor cannot reach,
# and `why` is the paragraph the anchor pages print above the table, so the
# reasoning lives beside the pair list it explains.
#
# ENHANCEMENT: every matched-speed pair the slow one-hand field supports.
# The universe is the one-hand weapons a shaman can carry above the 2.3
# speed floor, and a pair is legal where the off-hand item is not Main Hand
# only. Rod of the Sun King is the ONLY 2.7 weapon that fits the off hand,
# so every 2.7 pair is a main hand plus the Rod, or two Rods. A pair of two
# copies of one item is legal where the item is not unique, and every
# doubled item here drops from a boss the raid kills weekly or sells for
# arena points, so two copies is a question of weeks rather than of
# possibility.
ROUNDS: dict[str, dict] = {
    "enhancement_shaman": {
        "why": (
            "An Enhancement Shaman carries a Windfury imbue in each hand, "
            "pairs two weapons of the same speed, and wants them slow, per "
            "the 20 August 2026 ruling in the judgment store. The set above "
            "wears the pair its published source ranked, so each row below "
            "is THIS PROFILE with only the two weapon ids replaced: the "
            "slot keeps its Mongoose, and the consumables, buffs and seed "
            "hold still, so every figure is directly comparable with the "
            "one at the top of this page. The character is a Draenei, so no "
            "row inherits the Orc axe privilege the published lists assume. "
            "The weapons run unsynced, per the 15 August 2026 ruling."),
        "pairs": [
            # 2.8 against 2.8. Syphon of the Nathrezim is the only slow
            # one-hander at this speed, so the only matched pair is two of
            # it, from Supremus.
            {"mh": 32262, "oh": 32262, "speed": 2.8, "phase3": True},
            # 2.7 against 2.7.
            {"mh": 28439, "oh": 29996, "speed": 2.7, "phase3": False},
            {"mh": 28437, "oh": 29996, "speed": 2.7, "phase3": False},
            {"mh": 28438, "oh": 29996, "speed": 2.7, "phase3": False},
            {"mh": 28433, "oh": 29996, "speed": 2.7, "phase3": False},
            {"mh": 28432, "oh": 29996, "speed": 2.7, "phase3": False},
            {"mh": 32944, "oh": 29996, "speed": 2.7, "phase3": False},
            {"mh": 32946, "oh": 29996, "speed": 2.7, "phase3": True},
            {"mh": 29996, "oh": 29996, "speed": 2.7, "phase3": False},
            # 2.6 against 2.6, the widest field. Rising Tide, Netherbane and
            # the Gladiator Cleavers are One Hand and fit either hand; the
            # Right Ripper is Main Hand only and the Chopper is Off Hand
            # only.
            {"mh": 32236, "oh": 32236, "speed": 2.6, "phase3": True},
            {"mh": 32236, "oh": 29924, "speed": 2.6, "phase3": True},
            {"mh": 29924, "oh": 29924, "speed": 2.6, "phase3": False},
            {"mh": 31965, "oh": 31965, "speed": 2.6, "phase3": False},
            {"mh": 33737, "oh": 33669, "speed": 2.6, "phase3": True},
            {"mh": 33669, "oh": 34015, "speed": 2.6, "phase3": True},
        ],
    },
}


def with_pair(gear: dict, mh: int, oh: int) -> dict:
    """The gear wearing one candidate pair, each slot keeping its enchant.

    THE GEMS GO WITH THE OLD ITEM and the enchant stays with the slot. No
    candidate here carries a socket, so dropping the gems loses nothing, and
    the weapon slots wear the same enchant at every anchor, so keeping the
    slot's enchant is what a raider would do rather than a modelling
    shortcut.
    """
    out = {"items": [dict(entry) for entry in gear["items"]]}
    for slot, item_id in (("main_hand", mh), ("off_hand", oh)):
        index = SLOT_ORDER.index(slot)
        entry = dict(out["items"][index])
        entry["id"] = item_id
        entry.pop("gems", None)
        out["items"][index] = entry
    return out


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

    names = item_names()
    rows_by_id = {int(r["item_id"]): r for r in csv.DictReader(ITEMS.open())}
    strings = yaml.safe_load(
        TALENTS.read_text())["wowsims_talent_strings"]["strings"]
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

    specs_out: dict[str, dict] = {}
    total = 0
    for spec, round_ in ROUNDS.items():
        talents = (strings.get(spec) or {}).get("string")
        stem = spec.replace("_", "-")
        anchors: dict[str, list[dict]] = {}
        for anchor in ANCHORS:
            path = args.gear / f"{stem}.{anchor}.gear.json"
            if not path.is_file():
                print(f"error: no profile at {path}. Run `just regen` first.",
                      file=sys.stderr)
                return 1
            gear = json.loads(path.read_text())
            results = []
            for pair in round_["pairs"]:
                if anchor == "entry" and pair["phase3"]:
                    continue
                label = (f"{names.get(pair['mh'], pair['mh'])} + "
                         f"{names.get(pair['oh'], pair['oh'])}")
                dps, stdev, error = run(args.cli, build_request(
                    spec, with_pair(gear, pair["mh"], pair["oh"]), talents,
                    args.iterations, args.seed, buffs, party_of,
                    anchor.replace("-", "_"), args.seconds, args.armor))
                if error:
                    raise SystemExit(f"run_weapon_pair_sims.py: {spec}: "
                                     f"{anchor}: {label}: {error}")
                results.append({
                    "main_hand": weapon(pair["mh"]),
                    "off_hand": weapon(pair["oh"]),
                    "pair_speed": pair["speed"],
                    "dps": round(dps, 1),
                    "standard_error": round(
                        stdev / math.sqrt(args.iterations), 2),
                    "stdev": round(stdev, 1),
                })
                total += 1
                print(f"  {spec:22s} {anchor:20s} {label:56s} {dps:9.1f}")
            results.sort(key=lambda row: -row["dps"])
            anchors[anchor] = results
        specs_out[spec] = {"why": round_["why"], "anchors": anchors}

    document = {
        "meta": {
            "what": (
                "Weapon pair rounds, one per spec in the registry of "
                "tools/run_weapon_pair_sims.py, each pair run as a VARIANT "
                "of that spec's anchor profiles: the exported gear with only "
                "the two weapon ids replaced, each slot keeping its enchant, "
                "the anchor's own consumables, buffs and seed held still. "
                "The Enhancement round is ruled in "
                "data/judgments/enhancement-weapon-rules.yaml."),
            "read_this_first": (
                "Every variant is directly comparable with its anchor's "
                "figure in sim-figures.yaml, because it is the same request "
                "with two item ids changed, and the anchor figure IS the "
                "captured pair. The plus or minus is ONE STANDARD ERROR, not "
                "a confidence interval. NOT A RULING. Which pair each anchor "
                "wears is the council's call."),
            "entry_scope": (
                "The entry anchor is worn before Phase 3, so its variants "
                "hold no Black Temple drop and no Season 3 weapon. The tier "
                "and best-in-slot anchors take the whole field, because the "
                "tier anchor is not constrained by progression, per the 14 "
                "August 2026 ruling."),
            "weapons_unsynced": (
                "The Enhancement runs send no syncType, per the 15 August "
                "2026 ruling that its weapons run unsynced. A matched pair "
                "is where the simulator's Auto mode would begin delaying "
                "the off hand, so the absence is load-bearing here and is "
                "stated."),
            "iterations": args.iterations,
            "seed": args.seed,
            "boss_armor": args.armor,
            "encounter_seconds": args.seconds,
        },
        "specs": specs_out,
    }
    args.out.write_text(yaml.safe_dump(
        document, sort_keys=False, allow_unicode=True, width=78))
    print(f"{total} variant(s) across {len(specs_out)} spec(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
