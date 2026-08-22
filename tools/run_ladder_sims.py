#!/usr/bin/env python3
"""The slot ladders: each armor slot's workbook candidates, measured.

WHY THIS ROUND EXISTS. The guild lead's derived-orderings ruling of
22 August 2026, data/judgments/derived-orderings.yaml, lets the item pages
sort a slot's candidates by simulated delta and read a denial cost as this
item minus the next best available. Both need the slot's field MEASURED,
not scored: the EP Workbook ranks a slot by static weights, and this round
prices the same ladder on our own profiles.

WHAT ONE RUN IS: THE TIER PROFILE WITH ONE SLOT'S ITEM REPLACED. The tier
anchor is the set the raid is building toward, unconstrained by
progression, so it is where an incoming drop actually lands. Everything
else is held still: the tier anchor's consumables, buffs, seed and
boss armor, so every figure is directly comparable with the spec's tier
figure in sim-figures.yaml and the worn item reproduces it.

THE FIELD is the top of the spec's workbook ladder for that slot, LADDER_DEPTH
rows, plus the worn item where the ladder does not carry it. The ladder is
already cross-armor, which is the point: it is how a mail piece and the
leather piece it competes with land in one table.

DRESSING follows data/judgments/sim-context.yaml, assumed gemmed and
enchanted: the slot keeps its enchant, a candidate another of this spec's
exported profiles wears arrives with that profile's gems, a candidate no
profile wears carries the spec's standard gem in each socket, and the worn
item keeps its own gems exactly, so the self-match stands.

The ten slots here are the single-item slots. Weapons, rings, trinkets and
ranged have their own enumerated rounds in data/facts/variant-sims.yaml
and are not repeated.

Writes data/facts/ladder-sims.yaml and nothing else. Runs the simulator,
so it runs inside `just sim` and `just sim-ladders` and outside
`just regen` and `just check`.

Usage:
    python3 tools/run_ladder_sims.py --iterations 10000
    python3 tools/run_ladder_sims.py --iterations 10000 --spec combat_rogue
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_sims import (  # noqa: E402
    BUFFS, DEFAULT_ARMOR, ENCOUNTER_SECONDS, GEAR, NOT_SIMULATABLE, ROSTER,
    SLOT_ORDER, SPECS, TALENTS, WOWSIMS, build_request, item_names, run,
)
from run_tier_sims import standard_gems, with_item  # noqa: E402
from extract_ladder import SPECS as WORKBOOK_TABS  # noqa: E402
from extract_ladder import read_tab  # noqa: E402

OUT = Path("data/facts/ladder-sims.yaml")
WORKBOOK = Path("data/research/epv-workbook")
TIER_ANCHOR = "tier-hands-and-head"

# Workbook section name -> gear slot key. The single-item slots only:
# weapons, rings, trinkets and ranged have their own enumerated rounds.
SECTIONS = {
    "Head": "head",
    "Neck": "neck",
    "Shoulders": "shoulder",
    "Back": "back",
    "Chest": "chest",
    "Wrist": "wrist",
    "Hands": "hands",
    "Waist": "waist",
    "Legs": "legs",
    "Feet": "feet",
}

# How deep each slot's measured ladder runs. Eight covers the fallback
# question the item pages ask, what a spec takes when the first choice is
# routed away, and then the next, without measuring the tail of a ladder
# nobody reaches.
LADDER_DEPTH = 8


def workbook_ladders(spec: str) -> dict[str, list[dict]]:
    """The spec's workbook rows per gear slot, in the tab's rank order."""
    tab = next((filename for _, (filename, key) in WORKBOOK_TABS.items()
                if key == spec), None)
    if tab is None:
        sys.exit(f"run_ladder_sims.py: {spec} has no workbook tab")
    raw = read_tab(WORKBOOK / tab)
    out: dict[str, list[dict]] = {}
    for section, slot in SECTIONS.items():
        rows = [r for r in raw.get(section, []) if r.get("item_id")]
        out[slot] = rows
    return out


def dressed(spec: str, worn_entry: dict, item_id: int, wardrobe: dict,
            items_csv: dict, gem_ids: dict, gem_names: dict) -> list[int] | None:
    """The gems a candidate arrives with, per the assumed-gemmed ruling."""
    if worn_entry.get("id") == item_id:
        return None  # with_item keeps the worn entry verbatim
    other = wardrobe.get(item_id)
    if other is not None:
        return other.get("gems") or []
    return standard_gems(spec, item_id, items_csv, gem_ids, gem_names)


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
    ap.add_argument("--spec", action="append", default=None,
                    help="Run only this spec's ladders, repeatable. The "
                         "other specs' recorded figures are carried forward "
                         "from the existing output file unchanged.")
    ap.add_argument("--slot", default=None,
                    help="Run only these slots, a comma list of gear slot "
                         "keys. The other slots are carried forward per "
                         "spec.")
    args = ap.parse_args()

    if not args.cli.is_file():
        print(f"error: no simulator at {args.cli}. Run "
              "tools/install_wowsimcli.sh first.", file=sys.stderr)
        return 1

    names = item_names()
    import csv as _csv
    items_csv = {int(r["item_id"]): r for r in _csv.DictReader(
        Path("data/facts/items.csv").open())}
    gem_names = {s: (b.get("gems") or {})
                 for s, b in (yaml.safe_load(
                     Path("data/facts/enchants-by-spec.yaml").read_text()
                 ).get("specs") or {}).items()}
    gem_ids = {g["name"]: g["id"] for g in json.loads(
        (WOWSIMS / "assets/database/db.json").read_text()).get("gems") or []}
    strings = yaml.safe_load(
        TALENTS.read_text())["wowsims_talent_strings"]["strings"]
    buffs = yaml.safe_load(BUFFS.read_text())
    roster = yaml.safe_load(ROSTER.read_text())
    party_of = {}
    for group in roster.get("groups") or []:
        for member in group.get("members") or []:
            party_of.setdefault(member, group["id"])

    simmable = [s for s in SPECS if s not in NOT_SIMULATABLE]
    wanted = simmable
    if args.spec:
        unknown = [s for s in args.spec if s not in simmable]
        if unknown:
            print(f"error: not simmable: {', '.join(unknown)}. "
                  f"Simmable: {', '.join(simmable)}", file=sys.stderr)
            return 1
        wanted = [s for s in simmable if s in args.spec]
    slots_wanted = list(SECTIONS.values())
    if args.slot:
        slots_wanted = [s.strip() for s in args.slot.split(",") if s.strip()]
        unknown = [s for s in slots_wanted if s not in SECTIONS.values()]
        if unknown:
            print(f"error: not a ladder slot: {', '.join(unknown)}",
                  file=sys.stderr)
            return 1

    carried: dict[str, dict] = {}
    if args.out.is_file():
        carried = (yaml.safe_load(args.out.read_text()) or {}).get("specs") \
            or {}

    specs_out: dict[str, dict] = {s: b for s, b in carried.items()}
    total = 0
    for spec in wanted:
        stem = spec.replace("_", "-")
        talents = (strings.get(spec) or {}).get("string")
        tier_path = args.gear / f"{stem}.{TIER_ANCHOR}.gear.json"
        if not tier_path.is_file():
            print(f"error: no profile at {tier_path}. Run `just regen` "
                  "first.", file=sys.stderr)
            return 1
        tier = json.loads(tier_path.read_text())
        # Every dressed slot entry this spec's exported profiles wear, so a
        # candidate a profile wears arrives with that profile's gems.
        wardrobe: dict[int, dict] = {}
        for anchor in ("entry", TIER_ANCHOR, "bis", "bis-no-glaives"):
            path = args.gear / f"{stem}.{anchor}.gear.json"
            if not path.is_file():
                continue
            for entry in json.loads(path.read_text())["items"]:
                if entry.get("id"):
                    wardrobe.setdefault(entry["id"], entry)

        ladders = workbook_ladders(spec)
        prior_slots = (carried.get(spec) or {}).get("slots") or {}
        slots_out: dict[str, list[dict]] = {
            s: rows for s, rows in prior_slots.items()
            if s not in slots_wanted}
        for slot in slots_wanted:
            index = SLOT_ORDER.index(slot)
            worn_entry = tier["items"][index] or {}
            worn_id = worn_entry.get("id")
            field = [r["item_id"] for r in ladders.get(slot, [])
                     [:LADDER_DEPTH]]
            if worn_id and worn_id not in field:
                field.append(worn_id)
            rows: list[dict] = []
            for item_id in field:
                gems = dressed(spec, worn_entry, item_id, wardrobe,
                               items_csv, gem_ids, gem_names)
                gear = with_item(tier, slot, item_id, gems)
                dps, stdev, error = run(args.cli, build_request(
                    spec, gear, talents, args.iterations, args.seed, buffs,
                    party_of, "tier_hands_and_head", args.seconds,
                    args.armor))
                if error:
                    # The binary's item database is narrower than the
                    # checkout's, so an unknown id is skipped loudly rather
                    # than crashing the round, the run_variant_sims rule.
                    print(f"  SKIP {spec} {slot} "
                          f"{names.get(item_id, item_id)}: {error}")
                    continue
                row = {
                    "item": names.get(item_id, str(item_id)),
                    "id": item_id,
                    "dps": round(dps, 1),
                    "standard_error": round(
                        stdev / math.sqrt(args.iterations), 2),
                    "stdev": round(stdev, 1),
                }
                if item_id == worn_id:
                    row["worn"] = True
                rows.append(row)
                total += 1
                print(f"  {spec:22s} {slot:9s} "
                      f"{names.get(item_id, str(item_id)):42s} {dps:9.1f}")
            rows.sort(key=lambda r: -r["dps"])
            slots_out[slot] = rows
        specs_out[spec] = {
            "anchor": TIER_ANCHOR,
            "slots": slots_out,
        }
        _write_document(args, specs_out)
        print(f"{spec}: written ({total} run(s) so far)")

    print(f"{total} run(s) -> {args.out}")
    return 0


def _write_document(args, specs_out: dict) -> None:
    document = {
        "meta": {
            "what": (
                "The slot ladders: each single-item slot's workbook "
                "candidates measured as variants of the spec's TIER "
                "profile, one slot replaced per run, everything else held "
                "still. The worn item reproduces the tier figure in "
                "sim-figures.yaml, so every row is directly comparable "
                "with it and with the other rows of its slot. Replacements "
                "arrive dressed per data/judgments/sim-context.yaml: the "
                "slot keeps its enchant, a candidate a profile of this "
                "spec wears arrives with that profile's gems, and any "
                "other candidate carries the spec's standard gem in each "
                "socket."),
            "why": (
                "The derived-orderings ruling, "
                "data/judgments/derived-orderings.yaml: the item pages "
                "sort a slot's candidates by measured delta and read a "
                "denial cost as this item minus the next best available, "
                "and both need the ladder measured rather than scored. "
                "The field is the top of the spec's EP Workbook ladder "
                "for the slot, already cross-armor, plus the worn item."),
            "boss_armor": args.armor,
            "iterations": args.iterations,
            "seed": args.seed,
            "encounter_seconds": args.seconds,
            "ladder_depth": LADDER_DEPTH,
            "GENERATED": (
                "BY tools/run_ladder_sims.py, which runs the simulator. "
                "Rebuilt by `just sim` and `just sim-ladders`, not by "
                "`just regen`. DO NOT EDIT."),
        },
        "specs": specs_out,
    }
    args.out.write_text(yaml.safe_dump(
        document, sort_keys=False, allow_unicode=True, width=78))


if __name__ == "__main__":
    raise SystemExit(main())
