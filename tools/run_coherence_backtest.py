#!/usr/bin/env python3
"""The coherence backtest: do the slot ladders compose?

Every denial cost the item pages print is measured ONE SLOT AT A TIME on the
tier profile, everything else held still. A council following those orderings
applies many of them at once, so the orderings are only trustworthy if the
one-slot readings ADD: if the profile that takes five ladder upgrades measures
what the five deltas sum to. Hit ripple is the known way they might not, the
Beast Mastery trinket case in data/judgments/sim-context.yaml.

WHAT ONE RUN IS. Each spec starts at its TIER profile. A full clear supplies
one copy of every Mount Hyjal and Black Temple drop appearing in any measured
ladder; a candidate from outside the raids, crafted, badge, arena or
reputation, is uncontended and always available. Drops are allocated
GREEDILY: at each step the (spec, slot, item) with the largest remaining
ladder gain over that spec's current slot takes the item, consuming the copy
where the item is contested. When no positive gain remains, each spec's end
state is built as gear, dressed exactly the way the ladder round dressed a
candidate, and simmed once. Two figures come out per spec:

  measured    the simulated DPS of the end state
  predicted   the tier anchor plus the sum of the ladder deltas the greedy
              walk banked, which is what a reader adding card figures expects

A CEILING set is built and simmed the same way, every measured slot at its
best ladder row with contention ignored, so the cost of contention and the
additivity error are reported separately rather than blurred.

The verdict is the gap between measured and predicted, read against the
combined standard errors. Small gaps mean the orderings compose and the
derived orderings can be followed; a large gap on a spec names exactly where
a one-slot-at-a-time reading misleads.

Writes data/facts/coherence-backtest.yaml. Runs the simulator, so it runs
outside `just regen` and `just check`, invoked by hand or `just backtest`.

Usage:
    python3 tools/run_coherence_backtest.py --iterations 10000
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
    BUFFS, DEFAULT_ARMOR, ENCOUNTER_SECONDS, GEAR, ROSTER, SLOT_ORDER,
    TALENTS, WOWSIMS, build_request, item_names, run,
)
from run_ladder_sims import TIER_ANCHOR, dressed  # noqa: E402
from run_tier_sims import with_item  # noqa: E402

LADDERS = Path("data/facts/ladder-sims.yaml")
FIGURES = Path("data/facts/sim-figures.yaml")
DROPS = Path("data/facts/drops.csv")
OUT = Path("data/facts/coherence-backtest.yaml")


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

    names = item_names()
    ladders = yaml.safe_load(LADDERS.read_text())
    figures = yaml.safe_load(FIGURES.read_text())["results"]
    tier_anchor = {r["spec"]: r for r in figures
                   if r["anchor"] == TIER_ANCHOR
                   and r.get("boss_armor") == args.armor}
    raid_drops = {int(r["item_id"]) for r in csv.DictReader(DROPS.open())
                  if r["tier"] == "T6"}
    items_csv = {int(r["item_id"]): r for r in csv.DictReader(
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

    specs = sorted(ladders["specs"])

    # THE GREEDY WALK, on the ladder figures alone. State per spec per slot
    # is the dps of the item currently held, seeded from the worn row.
    state: dict[str, dict[str, dict]] = {}
    for spec in specs:
        state[spec] = {}
        for slot, rows in ladders["specs"][spec]["slots"].items():
            worn = next((r for r in rows if r.get("worn")), None)
            if worn is None:
                continue
            state[spec][slot] = {"row": worn, "banked": 0.0, "path": []}
    copies = {i: 1 for i in raid_drops}

    def candidates():
        for spec in specs:
            for slot, held in state[spec].items():
                for row in ladders["specs"][spec]["slots"][slot]:
                    if row["id"] in copies and copies[row["id"]] < 1:
                        continue
                    gain = row["dps"] - held["row"]["dps"]
                    if gain > 0:
                        yield gain, spec, slot, row

    allocations: list[dict] = []
    while True:
        best = max(candidates(), key=lambda c: c[0], default=None)
        if best is None:
            break
        gain, spec, slot, row = best
        held = state[spec][slot]
        if row["id"] in copies:
            copies[row["id"]] -= 1
        allocations.append({
            "item": row["item"], "id": row["id"], "spec": spec,
            "slot": slot, "gain": round(gain, 1),
            "contested": row["id"] in raid_drops,
        })
        held["banked"] += gain
        held["path"].append(row["item"])
        held["row"] = row

    # BUILD, DRESS AND SIM each end state, and the ceiling beside it.
    def measure(spec: str, final_rows: dict[str, dict]) -> tuple[float, float]:
        stem = spec.replace("_", "-")
        tier = json.loads(
            (args.gear / f"{stem}.{TIER_ANCHOR}.gear.json").read_text())
        wardrobe: dict[int, dict] = {}
        for anchor in ("entry", TIER_ANCHOR, "bis", "bis-no-glaives"):
            path = args.gear / f"{stem}.{anchor}.gear.json"
            if not path.is_file():
                continue
            for entry in json.loads(path.read_text())["items"]:
                if entry.get("id"):
                    wardrobe.setdefault(entry["id"], entry)
        gear = tier
        for slot, row in final_rows.items():
            index = SLOT_ORDER.index(slot)
            worn_entry = tier["items"][index] or {}
            if worn_entry.get("id") == row["id"]:
                continue
            gems = dressed(spec, worn_entry, row["id"], wardrobe,
                           items_csv, gem_ids, gem_names)
            gear = with_item(gear, slot, row["id"], gems)
        dps, stdev, error = run(args.cli, build_request(
            spec, gear, (strings.get(spec) or {}).get("string"),
            args.iterations, args.seed, buffs, party_of,
            "tier_hands_and_head", args.seconds, args.armor))
        if error:
            sys.exit(f"run_coherence_backtest.py: {spec}: {error}")
        return dps, stdev / math.sqrt(args.iterations)

    results = []
    for spec in specs:
        anchor = tier_anchor[spec]
        banked = sum(h["banked"] for h in state[spec].values())
        predicted = anchor["dps"] + banked
        measured, se = measure(
            spec, {s: h["row"] for s, h in state[spec].items()})

        ceiling_rows = {s: ladders["specs"][spec]["slots"][s][0]
                        for s in state[spec]}
        ceiling_banked = 0.0
        for s in state[spec]:
            rows = ladders["specs"][spec]["slots"][s]
            worn = next(r for r in rows if r.get("worn"))
            ceiling_banked += rows[0]["dps"] - worn["dps"]
        ceiling_predicted = anchor["dps"] + ceiling_banked
        ceiling_measured, ceiling_se = measure(spec, ceiling_rows)

        gap = measured - predicted
        results.append({
            "spec": spec,
            "tier_anchor": anchor["dps"],
            "upgrades_taken": len(state[spec]),
            "greedy": {
                "predicted": round(predicted, 1),
                "measured": round(measured, 1),
                "standard_error": round(se, 2),
                "gap": round(gap, 1),
            },
            "ceiling": {
                "predicted": round(ceiling_predicted, 1),
                "measured": round(ceiling_measured, 1),
                "standard_error": round(ceiling_se, 2),
                "gap": round(ceiling_measured - ceiling_predicted, 1),
                "contention_cost": round(
                    ceiling_predicted - predicted, 1),
            },
        })
        print(f"{spec:24s} greedy {measured:8.1f} vs predicted "
              f"{predicted:8.1f} ({gap:+.1f})  ceiling "
              f"{ceiling_measured:8.1f} vs {ceiling_predicted:8.1f} "
              f"({ceiling_measured - ceiling_predicted:+.1f})")

    document = {
        "meta": {
            "what": (
                "The coherence backtest: whether the slot ladders COMPOSE. "
                "Each spec starts at its tier profile; a full clear "
                "supplies one copy of every Tier 6 raid drop in any "
                "measured ladder, candidates from outside the raids "
                "uncontended; drops allocate greedily by largest remaining "
                "ladder gain. `predicted` is the tier anchor plus the "
                "banked one-slot deltas, which is what a reader adding "
                "card figures expects; `measured` is the built, dressed "
                "end state simmed once. `gap` is measured minus predicted, "
                "the additivity error; `ceiling` repeats it with "
                "contention ignored, every slot at its best row, and "
                "`contention_cost` is what single copies cost the greedy "
                "raid in predicted DPS."),
            "boss_armor": args.armor,
            "iterations": args.iterations,
            "seed": args.seed,
            "GENERATED": (
                "BY tools/run_coherence_backtest.py, which runs the "
                "simulator. Rebuilt by `just backtest`, not by "
                "`just regen`. DO NOT EDIT."),
        },
        "results": results,
        "allocations": allocations,
    }
    args.out.write_text(yaml.safe_dump(
        document, sort_keys=False, allow_unicode=True, width=78))
    print(f"{len(results)} spec(s), {len(allocations)} allocation(s) "
          f"-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
