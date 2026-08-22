#!/usr/bin/env python3
"""The tier rounds: what breaking an old set bonus costs, measured by subset.

WHY THIS ROUND EXISTS. The guild lead ruled on 20 August 2026 that the center
of gravity for the tier page is "we care about at what point it makes sense to
break a bonus". A raider walks into Phase 3 wearing a Phase 2 set whose old
tier bonuses are live, and every chase piece that lands in one of those slots
cuts the old set by one piece. The EP Workbook prices each piece alone and
prices no bonus, so whether the first chase piece is a gain or a loss, and how
many pieces it takes before breaking the bonus pays, comes from the simulator.

WHAT ONE RUN IS: THE ENTRY PROFILE WITH A SUBSET OF SLOTS REPLACED. Two rounds
run per spec, both on the otherwise-unchanged entry profile with the entry
anchor's own consumables, buffs and seed held still, so every figure is
directly comparable with the spec's entry figure in sim-figures.yaml, and the
empty subset reproduces it.

THE OLD-BONUS ROUND replaces subsets of the entry set's bonus-carrying slots
with what the spec's best-in-slot profile wears in those slots: the chase
targets. The bonus-carrying slots are read from the entry gear itself, grouped
by the item database's own set membership, and a slot where the best-in-slot
profile wears the same item is not a question and is not run. Every subset is
a row, so the table holds the best way to take one chase piece, two, three,
and so on, and whether the old bonus survives each.

THE TIER-SIX ROUND replaces subsets of the five token slots with what the tier
anchor wears where it differs from entry. This prices the Tier 6 two-piece and
four-piece thresholds and the chase order, on the same baseline.

ENCHANTS AND GEMS follow the with_pair rule of tools/run_variant_sims.py: the
slot keeps its enchant, because a raider enchants whatever sits in the slot,
and a replacement arrives ungemmed unless it IS the worn item, because which
gems a chase piece takes is a separate question from what the piece is worth.

Writes data/facts/tier-sims.yaml and nothing else. The page that shows these
figures is docs/tier.md, written by tools/generate_tier_page.py. Runs the
simulator, so it runs inside `just sim` and `just sim-tier` and outside
`just regen` and `just check`.

Usage:
    python3 tools/run_tier_sims.py --iterations 10000
    python3 tools/run_tier_sims.py --iterations 10000 --spec enhancement_shaman
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_sims import (  # noqa: E402
    BUFFS, DEFAULT_ARMOR, ENCOUNTER_SECONDS, GEAR, NOT_SIMULATABLE, ROSTER,
    SLOT_ORDER, SPECS, TALENTS, WOWSIMS, build_request, item_names, run,
)

OUT = Path("data/facts/tier-sims.yaml")
CAPTURES = Path("data/facts/sim-profiles/hit-capture")
TIER_ANCHOR = "tier-hands-and-head"

# The five slots a tier token can fill, in SLOT_ORDER's order.
TOKEN_SLOTS = ["head", "shoulder", "chest", "hands", "legs"]


def set_of(item_id: int | None, db_items: dict) -> str | None:
    """Which item set this item belongs to, per the simulator's own database.

    THE DATABASE IS THE AUTHORITY, not the item name. This project has
    dispositioned an item on its name four times; set membership comes from
    the setName field the binary itself reads, so a "Cataclysm" belt that is
    not a set piece can never be counted as one.
    """
    if not item_id:
        return None
    return (db_items.get(item_id) or {}).get("setName")


def held_sets(gear: dict, db_items: dict) -> dict[str, list[str]]:
    """Every set this gear holds at two or more pieces, with its slots.

    TWO PIECES IS THE THRESHOLD because two is where the first bonus of every
    set in this scope turns on. A single set piece carries no bonus, so a set
    held at one piece poses no breaking question and is not returned.
    """
    counts: Counter = Counter()
    slots_by_set: dict[str, list[str]] = {}
    for slot, entry in zip(SLOT_ORDER, gear["items"]):
        name = set_of((entry or {}).get("id"), db_items)
        if name:
            counts[name] += 1
            slots_by_set.setdefault(name, []).append(slot)
    return {name: slots_by_set[name]
            for name, n in counts.items() if n >= 2}


def with_item(gear: dict, slot: str, item_id: int) -> dict:
    """The gear with one slot's item replaced by id, variant-style: the slot
    keeps its enchant and the replacement arrives ungemmed unless it IS the
    worn item."""
    out = {"items": [dict(e) for e in gear["items"]]}
    index = SLOT_ORDER.index(slot)
    entry = dict(out["items"][index]) or {}
    if entry.get("id") != item_id:
        entry.pop("gems", None)
    entry["id"] = item_id
    out["items"][index] = entry
    return out


def with_slots(gear: dict, other: dict, slots: list[str]) -> dict:
    """The gear wearing another profile's item ids in the named slots.

    THE SLOT KEEPS ITS ENCHANT AND THE GEMS GO WITH THE OLD ITEM, the same
    rule as tools/run_variant_sims.py::with_pair and for the same reason: a
    raider enchants whatever the slot holds, so keeping the enchant makes
    every row comparable with the anchor, while the gems a replacement takes
    are a separate question and it arrives ungemmed. Where the replacement id
    equals the worn id the slot is untouched, gems and all, though the
    callers never ask for such a slot.
    """
    out = {"items": [dict(entry) for entry in gear["items"]]}
    for slot in slots:
        index = SLOT_ORDER.index(slot)
        entry = dict(out["items"][index])
        new_id = (other["items"][index] or {}).get("id")
        if entry.get("id") != new_id:
            entry.pop("gems", None)
            entry["id"] = new_id
            out["items"][index] = entry
    return out


def pieces_after(gear: dict, db_items: dict,
                 watched: list[str]) -> dict[str, int]:
    """How many pieces of each watched set this gear still wears."""
    counts: Counter = Counter()
    for entry in gear["items"]:
        name = set_of((entry or {}).get("id"), db_items)
        if name in watched:
            counts[name] += 1
    return {name: counts.get(name, 0) for name in watched}


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
                    help="Run only this spec's rounds, repeatable. The other "
                         "specs' recorded figures are carried forward from "
                         "the existing output file unchanged, so one spec "
                         "can land without rerunning every other round.")
    args = ap.parse_args()

    if not args.cli.is_file():
        print(f"error: no simulator at {args.cli}. Run "
              "tools/install_wowsimcli.sh first.", file=sys.stderr)
        return 1

    names = item_names()
    tokens_doc = yaml.safe_load(Path("data/facts/tokens.yaml").read_text())
    db_items = {i["id"]: i for i in json.loads(
        (WOWSIMS / "assets/database/db.json").read_text()).get("items") or []}
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
    carried: dict[str, dict] = {}
    if args.spec:
        unknown = [s for s in args.spec if s not in simmable]
        if unknown:
            print(f"error: not simmable: {', '.join(unknown)}. "
                  f"Simmable: {', '.join(simmable)}", file=sys.stderr)
            return 1
        wanted = [s for s in simmable if s in args.spec]
        # THE OTHER SPECS ARE CARRIED, NOT DROPPED, the same rule as
        # tools/run_variant_sims.py: a partial run that wrote only its own
        # spec would delete every other round from the file.
        if args.out.is_file():
            carried = (yaml.safe_load(args.out.read_text())
                       or {}).get("specs") or {}
            carried = {s: block for s, block in carried.items()
                       if s not in wanted}

    specs_out: dict[str, dict] = dict(carried)
    total = 0
    for spec in wanted:
        stem = spec.replace("_", "-")
        talents = (strings.get(spec) or {}).get("string")
        paths = {a: args.gear / f"{stem}.{a}.gear.json"
                 for a in ("entry", TIER_ANCHOR, "bis")}
        missing = [p for p in paths.values() if not p.is_file()]
        if missing:
            print(f"error: no profile at {missing[0]}. Run `just regen` "
                  "first.", file=sys.stderr)
            return 1
        entry = json.loads(paths["entry"].read_text())
        tier = json.loads(paths[TIER_ANCHOR].read_text())
        bis = json.loads(paths["bis"].read_text())
        capture = yaml.safe_load(
            (CAPTURES / f"{stem}.yaml").read_text())
        bonus_texts = (((capture.get("anchors") or {}).get("entry") or {})
                       .get("set_bonuses_held") or [])

        def measure(gear, label, round_name):
            nonlocal total
            dps, stdev, error = run(args.cli, build_request(
                spec, gear, talents, args.iterations, args.seed, buffs,
                party_of, "entry", args.seconds, args.armor))
            if error:
                if "No item with id" in error:
                    # THE BINARY'S DATABASE IS THE AUTHORITY, and a row it
                    # cannot equip is skipped loudly, never fatal, per the
                    # variant runner's precedent.
                    print(f"  SKIPPED, unknown to the binary: {label}")
                    return None
                raise SystemExit(
                    f"run_tier_sims.py: {spec}: {round_name}: "
                    f"{label}: {error}")
            total += 1
            print(f"  {spec:22s} {round_name:10s} {label:52s} {dps:9.1f}")
            return dps, stdev

        def rows_for(base: dict, source: dict, slots: list[str],
                     watched: list[str], round_name: str) -> list[dict]:
            rows = []
            for size in range(len(slots) + 1):
                for combo in itertools.combinations(slots, size):
                    replaced = [s for s in SLOT_ORDER if s in combo]
                    gear = with_slots(base, source, replaced)
                    label = ", ".join(replaced) or "none, the entry set"
                    result = measure(gear, label, round_name)
                    if result is None:
                        continue
                    dps, stdev = result
                    rows.append({
                        "replaced": replaced,
                        "dps": round(dps, 1),
                        "standard_error": round(
                            stdev / math.sqrt(args.iterations), 2),
                        "stdev": round(stdev, 1),
                        "pieces_left": pieces_after(gear, db_items, watched),
                    })
            return rows

        block: dict = {}

        # THE OLD-BONUS ROUND. The bonus-carrying slots are the slots of
        # every set the entry gear holds at two or more pieces, and the
        # replacements are what the best-in-slot profile wears there.
        old = held_sets(entry, db_items)
        old_slots = sorted({s for slots in old.values() for s in slots},
                           key=SLOT_ORDER.index)
        replaceable = [
            s for s in old_slots
            if (entry["items"][SLOT_ORDER.index(s)] or {}).get("id")
            != (bis["items"][SLOT_ORDER.index(s)] or {}).get("id")]
        if not old:
            block["old_bonus"] = {
                "held": "none",
                "note": ("The entry set holds no set at two or more pieces, "
                         "so there is no old bonus to break and nothing to "
                         "measure."),
            }
        else:
            sets_block = {
                name: {
                    "slots": sorted(slots, key=SLOT_ORDER.index),
                    "pieces": len(slots),
                } for name, slots in sorted(old.items())}
            print(f"{spec}: old sets {', '.join(sorted(old))}; "
                  f"replaceable {', '.join(replaceable) or 'none'}; "
                  f"{2 ** len(replaceable)} subset(s)")
            block["old_bonus"] = {
                "held_sets": sets_block,
                "bonuses_held": bonus_texts,
                "replaceable_slots": replaceable,
                "replacements": {
                    s: {"id": (bis["items"][SLOT_ORDER.index(s)]
                               or {}).get("id"),
                        "name": names.get(
                            (bis["items"][SLOT_ORDER.index(s)]
                             or {}).get("id"),
                            str((bis["items"][SLOT_ORDER.index(s)]
                                 or {}).get("id")))}
                    for s in replaceable},
                "rows": rows_for(entry, bis, replaceable, sorted(old),
                                 "old-bonus"),
            }

        # THE TIER-SIX ROUND. The slots are the token slots the tier anchor
        # actually reconsiders, and the replacements are its own pieces.
        t6_slots = [
            s for s in TOKEN_SLOTS
            if (entry["items"][SLOT_ORDER.index(s)] or {}).get("id")
            != (tier["items"][SLOT_ORDER.index(s)] or {}).get("id")]
        watched_t6 = sorted(set(held_sets(tier, db_items))
                            - set(held_sets(entry, db_items)))
        if not t6_slots:
            block["tier_six"] = {
                "slots": [],
                "note": ("The tier anchor wears the entry set unchanged in "
                         "all five token slots, so this spec's Phase 3 list "
                         "keeps no tier piece and the round has nothing to "
                         "measure."),
            }
        else:
            print(f"{spec}: tier-six slots {', '.join(t6_slots)}; "
                  f"{2 ** len(t6_slots)} subset(s)")
            block["tier_six"] = {
                "slots": t6_slots,
                "pieces": {
                    s: {"id": (tier["items"][SLOT_ORDER.index(s)]
                               or {}).get("id"),
                        "name": names.get(
                            (tier["items"][SLOT_ORDER.index(s)]
                             or {}).get("id"),
                            str((tier["items"][SLOT_ORDER.index(s)]
                                 or {}).get("id")))}
                    for s in t6_slots},
                "rows": rows_for(entry, tier, t6_slots, watched_t6,
                                 "tier-six"),
            }

        # THE TOKEN-SINGLES ROUND, ruled by the guild lead: a spec whose
        # list keeps a different item in a token slot is still ranked on the
        # token page, so the TOKEN piece itself is measured alone on the
        # entry set wherever the tier-six round does not already measure it.
        spec_set6 = (tokens_doc["spec_to_set"].get(spec) or {}).get(6)
        set_pieces = {b["set_name"]: b["pieces"]
                      for b in tokens_doc["sets"]}
        singles = {}
        for s in TOKEN_SLOTS:
            token_piece = (set_pieces.get(spec_set6) or {}).get(s) or {}
            token_id = token_piece.get("item_id")
            if not token_id:
                continue
            token_id = int(token_id)
            covered = (s in t6_slots and int(
                (tier["items"][SLOT_ORDER.index(s)] or {}).get("id") or 0)
                == token_id)
            if covered:
                continue
            result = measure(with_item(entry, s, token_id),
                             f"{s}: {token_piece.get('name', token_id)}",
                             "token-single")
            if result is None:
                continue
            dps, stdev = result
            singles[s] = {
                "id": token_id,
                "name": token_piece.get("name", str(token_id)),
                "dps": round(dps, 1),
                "standard_error": round(
                    stdev / math.sqrt(args.iterations), 2),
                "stdev": round(stdev, 1),
            }
        if singles:
            block["token_singles"] = singles

        specs_out[spec] = block
        # WRITE AFTER EVERY SPEC, not once at the end, per the variant
        # runner's precedent: a partial file that carries what ran is
        # strictly better than a clean absence of everything.
        _write_document(args, specs_out)

    # THE FILE KEEPS THE SPEC REGISTRY'S ORDER regardless of which spec a
    # --spec run reran, so a partial run cannot reorder the file.
    specs_out = {s: specs_out[s] for s in simmable if s in specs_out}
    _write_document(args, specs_out)
    print(f"{total} run(s) across {len(wanted)} spec(s) -> {args.out}")
    return 0


def _write_document(args, specs_out: dict) -> None:
    document = {
        "meta": {
            "what": (
                "The tier rounds, two per simmable spec, every row the "
                "spec's ENTRY profile with a subset of slots replaced and "
                "the entry anchor's own consumables, buffs and seed held "
                "still. The old-bonus round replaces subsets of the entry "
                "set's bonus-carrying slots with what the best-in-slot "
                "profile wears there, the chase targets, so the table holds "
                "at what point breaking the old bonus pays. The tier-six "
                "round replaces subsets of the token slots with the tier "
                "anchor's pieces, so it prices the Tier 6 two-piece and "
                "four-piece thresholds and the chase order. A replaced slot "
                "keeps its enchant and a replacement arrives ungemmed, the "
                "same rule as variant-sims.yaml."),
            "read_this_first": (
                "Every row is directly comparable with the spec's entry "
                "figure in sim-figures.yaml, because it is the same request "
                "with only the named slots changed, and the empty subset IS "
                "the entry profile. `pieces_left` counts, per watched set, "
                "the pieces the row still wears: two turns the two-piece "
                "bonus on and four the four-piece. The plus or minus is ONE "
                "STANDARD ERROR, not a confidence interval. NOT A RULING. "
                "In what order the council routes the pieces is the "
                "council's call."),
            "iterations": args.iterations,
            "seed": args.seed,
            "boss_armor": args.armor,
            "encounter_seconds": args.seconds,
        },
        "specs": specs_out,
    }
    args.out.write_text(yaml.safe_dump(
        document, sort_keys=False, allow_unicode=True, width=78))


if __name__ == "__main__":
    raise SystemExit(main())
