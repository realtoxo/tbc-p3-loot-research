#!/usr/bin/env python3
"""Build the BIS gear anchor from the Phase 3 captures and the weapon routing.

WHAT THE THIRD ANCHOR IS FOR. ENTRY is a Phase 2 best-in-slot set. TIER is that
same set with only the five token slots reconsidered, so at the tier anchor the
other twelve slots still hold Phase 2 gear and six specs still swing Season 2
arena weapons. Every figure this project has published therefore answers "what
do the tier tokens alone do to a Phase 2 raider", which is narrow. BIS answers
what a Phase 3 geared spec does, and separating those two readings is the whole
reason this anchor exists.

WHY THIS IS A BUILD STEP AND NOT AN EDIT. `data/research/wowhead-phase3-bis-full/`
is a capture, and AGENTS.md forbids editing anything under `data/research/`
after capture, because citations point at those bytes. The guild lead's weapon
routing is a JUDGMENT about who receives a contested weapon and lives in
`data/judgments/weapon-routing.yaml`. This tool is where the two meet: the
capture keeps saying what the page said, the judgment keeps saying what the raid
will do, and the profile that comes out says both.

THE ROUTING IS TRANSCRIBED HERE AND CHECKED AGAINST THE JUDGMENT FILE. It is
transcribed because the rulings are prose and no parser should be asked to infer
"goes to the warlocks, the Balance Druid, the Elemental Shaman and the Shadow
Priest" from a sentence. It is CHECKED because a transcription drifts: every id
below must appear in the judgment file's rulings, and the run stops if one does
not. That check is not hypothetical. The judgment file recorded Tempest of Chaos
as 32943, which is Swiftsteel Bludgeon; the weapon is 30910.

Usage:
    python3 tools/build_bis_capture.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import yaml

RESEARCH = Path("data/research/wowhead-phase3-bis-full")
ROUTING = Path("data/judgments/weapon-routing.yaml")
# Trinket routing, plus the content this guild does not run. It is a second file
# rather than a section of the first because the two answer different questions:
# one settles who receives a contested weapon, the other settles that an item is
# not obtainable at all. Both are decisions about how this guild raids.
TRINKETS = Path("data/judgments/trinket-routing.yaml")
RINGS = Path("data/judgments/ring-routing.yaml")
ENTRY_CAPTURES = Path("data/facts/sim-profiles/hit-capture")
ITEMS = Path("data/facts/items.csv")
HIT = Path("data/facts/hit.yaml")
OUT = Path("data/facts/sim-profiles/bis-capture")
DB = Path(os.path.expanduser(os.environ.get(
    "WOWSIMS_TBC",
    "../tbc-phase-research-recovered/data/raw/vendor/wowsims-tbc-new-master",
))) / "assets/database/db.json"

SLOT_ORDER = [
    "head", "neck", "shoulder", "back", "chest", "wrist", "hands", "waist",
    "legs", "feet", "ring_1", "ring_2", "trinket_1", "trinket_2", "main_hand",
    "off_hand", "ranged",
]

# proto/common.proto :: the stat index each hit kind occupies in a db.json stat
# array. The same two indices tools/extract_items.py::STAT uses, transcribed
# from the same place, because three BiS items sit outside items.csv: it is
# scoped to Phase 3 and pre-phase gear, and Badge of the Swarmguard is an AQ40
# trinket. Being outside the compendium's scope does not make an item
# unsimulatable, and reading its hit from the simulator's own database is the
# only way to count it.
STAT_INDEX = {"spell_hit": 12, "melee_hit": 20}

# ONE HIT GEM IS 10 RATING, the same constant and the same source as
# tools/extract_hit_captures.py::RATING_PER_GEM, which is
# hit.yaml.discretionary_hit_budget. It is restated rather than imported because
# importing a sibling tool would make this file fail on that tool's unrelated
# breakage; it is checked against that file below instead.
RATING_PER_GEM = 10

# ---------------------------------------------------------------------------
# THE ROUTING, TRANSCRIBED FROM data/judgments/weapon-routing.yaml.
#
# Each entry names the ruling it implements. Nothing here decides anything: the
# guild lead ruled on 15 August 2026 and these are the mechanical consequences
# of those words for a seventeen-slot profile.
# ---------------------------------------------------------------------------

ZHARDOOM = 32374          # Zhar'doom, Greatstaff of the Devourer. Two Hand.
TEMPEST_OF_CHAOS = 30910  # Tempest of Chaos. Main Hand sword.
CATACLYSMS_EDGE = 30902   # Cataclysm's Edge. Two Hand.
WARGLAIVES = (32837, 32838)

# "zhardooms to warlocks boomkins and elementals", plus "spriest wears zhardoom".
# A two-handed staff occupies both hands, so the off hand is EMPTIED: "Zhardoom
# users should not have offhands also". The captures list an off-hand for all
# five, and it is discarded here rather than carried.
ZHARDOOM_SPECS = ("affliction_warlock", "destruction_warlock", "balance_druid",
                  "elemental_shaman", "shadow_priest")

# "arcane mage will get tempest of chaos first". Its capture ranks Zhar'doom and
# ALSO lists an off hand, which cannot both be worn; this resolves that
# contradiction the other way, to a one hand plus the captured off hand.
TEMPEST_SPECS = ("arcane_mage",)

# "arms warrior will never get warglaives" and "yes arms take cataclysm edge".
# The Arms page ranks only dual Warglaives for Phase 3 and its two-hand table is
# headed PHASE 2, so this spec had no Phase 3 two-hander of its own and the
# choice could not be read off the page. A two-hander empties the off hand, and
# that is a different BUILD from the dual-wield the page describes, not a stat
# swap.
CATACLYSM_SPECS = ("arms_warrior",)

# "no crafted weapons on hunter for bis" and "yes rerun the hunter sim",
# 20 August 2026. Each hunter's best-in-slot profile wears a single two-hander
# in place of the captured dual pair, per the weapon rounds' measurement that
# every two-hander beats every dual pair for both hunters. A two-hander
# empties the off hand.
HUNTER_TWO_HANDERS = {
    "beast_mastery_hunter": 33670,  # Vengeful Gladiator's Decapitator
    "survival_hunter": 32248,       # Halberd of Desolation
}

# TRINKETS ARE ROUTED FROM THE JUDGMENT FILE RATHER THAN TRANSCRIBED HERE,
# because unlike the weapon rulings each one is a plain slot and item pair with
# an explicit spec list, and nothing has to be inferred from prose. The file is
# read and applied; adding a ruling there needs no change to this tool.
#
# THE CONSTRAINT BEHIND THE FIRST RULING is that this guild does not run
# Ahn'Qiraj, so Badge of the Swarmguard is not a weaker pick, it is not a pick.
# It was the only item in any profile predating The Burning Crusade and no check
# looked for it.


# THE ONE SLOT WITH NO PHASE 3 SOURCE AT ALL. The Wowhead Phase 3 Retribution
# page carries no Relic section, which is the same cause as the finding already
# recorded in docs/kb/OPEN-FINDINGS.md: eleven of the twenty-one workbook tabs
# have no Ranged section, and they are exactly the classes whose relic slot
# holds an idol, a totem or a libram.
#
# RULED BY THE GUILD LEAD, 15 August 2026: fill it from the entry capture rather
# than leave it empty or pick a new one. So this spec's BiS set carries one item
# chosen from a PHASE 2 page, and that is the reason the divergence is written
# into the output rather than only printed here.
CARRY_FORWARD_FROM_ENTRY = {"retribution_paladin": ["ranged"]}

# THE SAME SPEC WITHOUT THE WARGLAIVES, as a second best-in-slot profile.
#
# WHY IT EXISTS. Both Warglaives of Azzinoth are ranked by the Combat Rogue's
# and the Fury Warrior's published Phase 3 lists, and there is ONE pair in the
# raid. So at most one of those two characters can be the profile the compendium
# already carries, and the other one is this. Without it the council has a
# figure for the winner and nothing at all for the loser.
#
# THE PAIRS WERE MEASURED, not chosen. Every one-hand, main-hand and off-hand
# weapon in items.csv that a warrior or a rogue could hold and that Phase 3 can
# supply, 33 candidates, was run in a two-pass search: vary the main hand
# against a fixed off hand, then vary the off hand against the winner. 4000
# iterations per candidate, confirmed at 10000, armor 6193, 150 seconds.
#
# NO DUPLICATE ITEM IS USED, deliberately. The best Fury pair by raw damage is
# two copies of Vengeful Gladiator's Slicer at 2609.9, and the pair below is
# 2606.1, which is 3.8 DPS behind and inside two standard errors. A profile
# whose whole purpose is to answer "what if this spec does not win the contested
# weapon" should not answer it by assuming the spec wins two of something else.
# The guild lead can overturn that: the figure for the duplicate pair is
# recorded here so the trade is visible rather than hidden.
NO_GLAIVE_ALTERNATIVE = {
    "fury_warrior": {
        "main_hand": 33762,   # Vengeful Gladiator's Slicer, One Hand sword
        "off_hand": 34015,    # Vengeful Gladiator's Chopper, Off Hand axe
        "measured": "2606.1 bare against 2727.4 for the bare Warglaives, so the "
                    "pair costs this spec 121.3. Two Slicers measure 2609.9 and "
                    "need two copies of one arena weapon.",
    },
    "combat_rogue": {
        "main_hand": 33762,   # Vengeful Gladiator's Slicer, One Hand sword
        "off_hand": 32369,    # Blade of Savagery, One Hand sword
        "measured": "2552.4 bare against 2745.3 for the bare Warglaives, so the "
                    "pair costs this spec 192.9. Both are swords, which the "
                    "rogue's shipped rotation and the Human sword specialization "
                    "both want.",
    },
}


def routed_ids(doc: dict) -> set[int]:
    """Every item id the judgment file routes, so a transcription can be checked."""
    out: set[int] = set()
    for ruling in doc.get("rulings") or []:
        for item_id in ruling.get("ids") or []:
            out.add(int(item_id))
    return out


def hit_of(item_id, kind: str, items_csv: dict, db_stats: dict) -> int:
    """The hit rating one item carries, in the school this spec is capped on.

    items.csv FIRST, because it is the table the compendium reads and a figure
    that disagrees with it would be a second truth. The simulator database is
    the fallback and not the default, for the three BiS items that sit outside
    the compendium's Phase 3 scope.
    """
    if not item_id:
        return 0
    row = items_csv.get(item_id)
    if row is not None:
        return int(float(row.get(kind) or 0))
    stats = db_stats.get(item_id)
    if stats is None:
        return 0
    index = STAT_INDEX[kind]
    return int(stats[index]) if index < len(stats) else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--research", type=Path, default=RESEARCH)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    routing = yaml.safe_load(ROUTING.read_text())
    trinkets = yaml.safe_load(TRINKETS.read_text())
    rings = yaml.safe_load(RINGS.read_text())
    known = routed_ids(routing)
    transcribed = {ZHARDOOM, TEMPEST_OF_CHAOS, CATACLYSMS_EDGE, *WARGLAIVES,
               *HUNTER_TWO_HANDERS.values()}
    stray = transcribed - known
    if stray:
        print(f"error: {sorted(stray)} is routed by this tool and appears in no "
              f"ruling in {ROUTING}. The transcription and the judgment have "
              "drifted, and the judgment wins.", file=sys.stderr)
        return 1

    items_csv = {int(r["item_id"]): r for r in csv.DictReader(ITEMS.open())}
    db = json.loads(DB.read_text())
    db_names = {i["id"]: i["name"] for i in db["items"]}
    db_stats = {i["id"]: i.get("stats") or [] for i in db["items"]}

    hit = yaml.safe_load(HIT.read_text())
    caps = {s["id"]: s.get("cap") for s in hit["specs"]}
    targets = {s["id"]: s.get("net_target_rating") for s in hit["specs"]}
    supplies = {
        "melee_special": "melee_and_ranged_hit",
        "ranged": "melee_and_ranged_hit",
        "melee_special_and_spell": "melee_and_ranged_hit",
        "spell": "spell_hit",
    }
    buff_by_kind = {b.get("supplies"): float(b["rating_equivalent"])
                    for b in hit.get("assumed_buffs") or []}
    budget = hit.get("discretionary_hit_budget") or {}
    if int((budget.get("physical") or {}).get("rating_per_gem", RATING_PER_GEM)
           or RATING_PER_GEM) != RATING_PER_GEM:
        print(f"error: {HIT} no longer prices a hit gem at {RATING_PER_GEM} "
              "rating, so every gem count this tool produces is wrong.",
              file=sys.stderr)
        return 1

    # A tier piece is a set piece bought from the token vendor, and BOTH tests
    # have to pass: the `tier` column names the raid an item DROPS in, so an
    # ordinary Black Temple off-piece also reads T6. Same rule as
    # tools/extract_hit_captures.py.
    tier_of = {
        i: r["tier"] for i, r in items_csv.items()
        if r.get("set_name") and r.get("source") == "tier_vendor"}
    set_of = {i: r["set_name"] for i, r in items_csv.items()
              if r.get("set_name") and r.get("source") == "tier_vendor"}

    args.out.mkdir(parents=True, exist_ok=True)
    for stale in args.out.glob("*.yaml"):
        stale.unlink()

    written, divergences, problems = 0, [], []
    for path in sorted(args.research.glob("*.json")):
        capture = json.loads(path.read_text())
        spec = capture["spec"]
        if spec not in caps:
            problems.append(f"{path}: spec {spec!r} is not in {HIT}")
            continue
        slots = {k: dict(v) for k, v in capture["slots"].items()}
        applied: list[str] = []

        def put(slot: str, item_id, why: str):
            was = (slots.get(slot) or {}).get("id")
            name = (items_csv.get(item_id) or {}).get("name") \
                or db_names.get(item_id)
            slots[slot] = {"item": name, "id": item_id} if item_id else \
                {"item": None, "id": None}
            applied.append(
                f"{slot}: {(slots.get(slot) or {}).get('item') or 'EMPTY'} "
                f"replaces {db_names.get(was, was) if was else 'nothing'}. {why}")

        if spec in ZHARDOOM_SPECS:
            if (slots.get("main_hand") or {}).get("id") != ZHARDOOM:
                put("main_hand", ZHARDOOM,
                    "Routed by the guild lead, 15 August 2026: Zhar'doom goes "
                    "to the warlocks, the Balance Druid, the Elemental Shaman "
                    "and the Shadow Priest.")
            if (slots.get("off_hand") or {}).get("id"):
                put("off_hand", None,
                    "Zhar'doom is a two-handed staff and the guild lead ruled "
                    "that its users hold no off hand. The captured off hand is "
                    "discarded, not carried.")
        if spec in TEMPEST_SPECS:
            if (slots.get("main_hand") or {}).get("id") != TEMPEST_OF_CHAOS:
                put("main_hand", TEMPEST_OF_CHAOS,
                    "Routed by the guild lead, 15 August 2026: the Arcane Mage "
                    "takes Tempest of Chaos first. Its capture ranks Zhar'doom "
                    "and also lists an off hand, which cannot both be worn; a "
                    "one hand resolves that and keeps the captured off hand.")
        if spec in CATACLYSM_SPECS:
            if (slots.get("main_hand") or {}).get("id") != CATACLYSMS_EDGE:
                put("main_hand", CATACLYSMS_EDGE,
                    "Routed by the guild lead, 15 August 2026: the Arms Warrior "
                    "will never receive the Warglaives, and takes Cataclysm's "
                    "Edge. This changes the BUILD from dual wield to a "
                    "two-hander, which is not a stat swap.")
            if (slots.get("off_hand") or {}).get("id"):
                put("off_hand", None,
                    "Cataclysm's Edge is two-handed, so the off hand the "
                    "capture lists is displaced rather than kept.")
        if spec in HUNTER_TWO_HANDERS:
            two_hander = HUNTER_TWO_HANDERS[spec]
            if (slots.get("main_hand") or {}).get("id") != two_hander:
                put("main_hand", two_hander,
                    "Routed by the guild lead, 20 August 2026: the hunters "
                    "re-anchor on a two-hander, every two-hander having "
                    "measured above every dual pair, with crafted weapons "
                    "barred from hunter consideration. This changes the BUILD "
                    "from dual wield to a two-hander, which is not a stat "
                    "swap.")
            if (slots.get("off_hand") or {}).get("id"):
                put("off_hand", None,
                    "A two-hander occupies both hands, so the off hand the "
                    "capture lists is displaced rather than kept.")
        for ruling in trinkets.get("rulings") or []:
            if spec not in (ruling.get("specs") or []):
                continue
            item_id = int((ruling.get("ids") or [None])[0])
            if (slots.get(ruling["slot"]) or {}).get("id") == item_id:
                continue
            put(ruling["slot"], item_id,
                f"Routed by the guild lead, {trinkets['meta']['ruled']}: "
                + ruling["ruling"])
        for ruling in rings.get("rulings") or []:
            if spec not in (ruling.get("specs") or []):
                continue
            item_id = int((ruling.get("ids") or [None])[0])
            if (slots.get(ruling["slot"]) or {}).get("id") == item_id:
                continue
            put(ruling["slot"], item_id,
                f"Routed by the guild lead, {rings['meta']['ruled']}: "
                + ruling["ruling"])

        for slot in CARRY_FORWARD_FROM_ENTRY.get(spec, []):
            if (slots.get(slot) or {}).get("id"):
                continue
            entry_path = ENTRY_CAPTURES / f"{spec.replace('_', '-')}.yaml"
            rows = ((yaml.safe_load(entry_path.read_text()).get("anchors")
                     or {}).get("entry") or {}).get("hit_by_slot") or {}
            row = rows.get(slot) or rows.get("relic") or {}
            if not row.get("id"):
                problems.append(
                    f"{spec}: {slot} is empty in the Phase 3 capture and the "
                    f"entry capture has nothing to carry forward")
                continue
            put(slot, row["id"],
                "THE PHASE 3 PAGE RANKS NOTHING IN THIS SLOT. Ruled by the "
                "guild lead, 15 August 2026: carry the entry capture's pick "
                "forward. So one slot of this otherwise Phase 3 set is sourced "
                f"from a PHASE 2 page, {entry_path}.")

        barred = {int(item["id"]): (block["content"], item["item"])
                  for block in trinkets.get("unavailable_content") or []
                  for item in block.get("barred_items") or []}
        for slot in SLOT_ORDER:
            item_id = (slots.get(slot) or {}).get("id")
            if item_id in barred:
                content, name = barred[item_id]
                problems.append(
                    f"{spec}: {slot} still holds {name} after routing, and "
                    f"{content} is content this guild does not run. A ruling in "
                    f"{TRINKETS} has to fill this slot with something reachable.")

        for bar in WARGLAIVES:
            if spec == "arms_warrior" and bar in {
                    (slots.get(s) or {}).get("id") for s in SLOT_ORDER}:
                problems.append(
                    f"{spec}: still holds Warglaive {bar} after routing, which "
                    "the guild lead barred outright")

        kind = "spell_hit" if caps.get(spec) == "spell" else "melee_hit"
        rows, total, unresolved = {}, 0, []
        for slot in SLOT_ORDER:
            row = slots.get(slot) or {}
            item_id = row.get("id")
            value = hit_of(item_id, kind, items_csv, db_stats)
            total += value
            entry = {"item": row.get("item"), "id": item_id, "hit": value}
            if item_id and item_id not in items_csv:
                entry["outside_items_csv"] = (
                    f"{db_names.get(item_id, 'unknown')} is not in "
                    "data/facts/items.csv, which is scoped to Phase 3 and "
                    "pre-phase gear. Its hit is read from the simulator "
                    "database instead. It simulates normally.")
                unresolved.append(f"{slot}: {item_id} {db_names.get(item_id)}")
            if row.get("note"):
                entry["capture_note"] = row["note"]
            rows[slot] = entry

        held = [s for s in SLOT_ORDER
                if tier_of.get((slots.get(s) or {}).get("id"))]
        by_tier: dict[str, list[str]] = {}
        for slot in held:
            by_tier.setdefault(
                tier_of[(slots.get(slot) or {}).get("id")], []).append(slot)
        set_names: dict[str, int] = {}
        for slot in held:
            name = set_of[(slots.get(slot) or {}).get("id")]
            set_names[name] = set_names.get(name, 0) + 1

        target = targets.get(spec) or 0
        debuff = buff_by_kind.get(supplies.get(caps.get(spec)), 0.0)
        gap = max(0.0, target - (total + debuff))
        sockets = sum(
            len([c for c in ((items_csv.get(r["id"]) or {}).get("sockets")
                             or "").split("|") if c in ("Red", "Yellow")])
            for r in rows.values() if r.get("id"))
        need = min(int(-(-gap // RATING_PER_GEM)) if gap > 0 else 0, sockets)

        document = {
            "spec": spec,
            "anchor_built": "bis",
            "built_on": "2026-08-15",
            "GENERATED": (
                "BY tools/build_bis_capture.py. DO NOT EDIT. It is rebuilt from "
                f"{path}, which is a capture and is never edited, plus the "
                f"weapon routing in {ROUTING}, which is a judgment. To change "
                "a slot here, change one of those two."),
            "sources": {
                "bis": {
                    "url": capture["url"],
                    "title": capture["title"],
                    "observed": capture["captured"],
                },
            },
            "anchors": {
                "bis": {
                    "hit_by_slot": rows,
                    "total_item_hit": total,
                    "tier6_pieces_held": by_tier.get("T6", []),
                    "tier5_pieces_held": by_tier.get("T5", []),
                    "tier4_pieces_held": by_tier.get("T4", []),
                    "set_pieces_held": set_names,
                    # WHY THE HIT STATE IS COMPUTED HERE AND NOT IN
                    # hit-captured.yaml. That file is the compendium's rollup
                    # and knows two anchors; giving it a third would move every
                    # card that quotes it, and the tier-set rebuild of 14 August
                    # 2026 is the record of what happens when data moves and the
                    # prose does not. This anchor is SIM SCOPE ONLY, so its hit
                    # state travels with the profile instead. The arithmetic is
                    # the same: gap is the net target less item hit and the
                    # assumed debuff, gems close it at 10 rating each, and the
                    # count is capped at the red and yellow sockets the set has.
                    "hit_state": {
                        "cap": caps.get(spec),
                        "net_target_rating": target,
                        "assumed_debuff_rating": debuff,
                        "item_hit": total,
                        "state": "full" if gap <= 0 else "short",
                        "gap_rating": int(gap),
                        "gem_sockets": sockets,
                        "gems_needed": need,
                    },
                },
            },
        }
        if applied:
            document["routing_applied"] = applied
        if unresolved:
            document["outside_items_csv"] = unresolved
        # A SECOND ANCHOR FOR THE TWO SPECS THAT CONTEST THE WARGLAIVES. It is
        # the same set in every other slot, so a reader comparing the two rows
        # is reading the weapons and nothing else.
        alt = NO_GLAIVE_ALTERNATIVE.get(spec)
        if alt:
            rows_alt = {k: dict(v) for k, v in rows.items()}
            for slot in ("main_hand", "off_hand"):
                item_id = alt[slot]
                rows_alt[slot] = {
                    "item": (items_csv.get(item_id) or {}).get("name")
                            or db_names.get(item_id),
                    "id": item_id,
                    "hit": hit_of(item_id, kind, items_csv, db_stats),
                }
            total_alt = sum(r["hit"] for r in rows_alt.values())
            gap_alt = max(0.0, target - (total_alt + debuff))
            document["anchors"]["bis_no_glaives"] = {
                "hit_by_slot": rows_alt,
                "total_item_hit": total_alt,
                "tier6_pieces_held": by_tier.get("T6", []),
                "tier5_pieces_held": by_tier.get("T5", []),
                "tier4_pieces_held": by_tier.get("T4", []),
                "set_pieces_held": set_names,
                "why_this_anchor_exists": (
                    "The Warglaives of Azzinoth are ranked by BOTH this spec's "
                    "published Phase 3 list and the other contender's, and the "
                    "raid holds one pair. This is the same best-in-slot set "
                    "with the next best weapons this spec can actually get. "
                    + alt["measured"]),
                "hit_state": {
                    "cap": caps.get(spec),
                    "net_target_rating": target,
                    "assumed_debuff_rating": debuff,
                    "item_hit": total_alt,
                    "state": "full" if gap_alt <= 0 else "short",
                    "gap_rating": int(gap_alt),
                    "gem_sockets": sockets,
                    "gems_needed": min(
                        int(-(-gap_alt // RATING_PER_GEM)) if gap_alt > 0 else 0,
                        sockets),
                },
            }
        (args.out / f"{spec.replace('_', '-')}.yaml").write_text(
            yaml.safe_dump(document, sort_keys=False, width=78,
                           allow_unicode=True))
        written += 1
        for line in applied:
            divergences.append(f"{spec} {line}")

    print(f"{written} best-in-slot capture(s) -> {args.out}")
    if divergences:
        print(f"\n  {len(divergences)} slot(s) where the profile differs from "
              "the page, every one of them a guild lead ruling:")
        for line in divergences:
            print(f"    {line}")
    if problems:
        print(f"\n{len(problems)} problem(s):", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
