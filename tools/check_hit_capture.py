#!/usr/bin/env python3
"""Check each captured hit set against itself, and against hit.yaml.

WHY A CHECK AND NOT A TRANSFORM. These files are collected by hand from
published gear lists, so nothing regenerates them and `just check` cannot catch
a hand edit by diffing. What CAN be caught is a file disagreeing with itself:
every anchor states a total AND the per-slot rows it was summed from, so the sum
is verifiable without trusting either. A capture whose stated total does not
match its own rows is the one kind of error a reader would never find, because
both numbers look authoritative.

THE SECOND CHECK IS THE POINT OF THE WHOLE EXERCISE. hit.yaml holds
supplied_at_tier_anchor figures derived from a rule that swapped in all five
Tier 6 pieces, and the guild lead ruled on 9 August 2026 that no spec wears
five. So every captured figure is expected to disagree with the recorded one.
This script prints the disagreement per spec rather than hiding it, and it flags
the cases that MATTER: where the captured figure crosses the spec's target and
the recorded one does not, or the reverse, because that is a cap state changing
rather than a number moving.

IMPROVED FAERIE FIRE IS NOT INSIDE THE SUPPLY FIGURE AND IS NOT INSIDE THE
TARGET. hit.yaml counts gear in `supplied_*` and keeps the assumed raid debuff
beside it under `assumed_buffs`, which is why a spec can read full while its
gear alone is under the target. The state test is therefore supply PLUS the
assumed debuff against the target, exactly as extract_constraints.py does it, and
the captures were briefed to report raw item hit with no debuff applied. Getting
this wrong understates every physical spec by 48 rating.

Usage:
    python3 tools/check_hit_capture.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

HIT = Path("data/facts/hit.yaml")
CAPTURES = Path("data/facts/sim-profiles/hit-capture")
PROGRESSION = Path("data/facts/progression.yaml")
DROPS = Path("data/facts/drops.csv")
TOKENS = Path("data/facts/tokens.yaml")
ITEMS = Path("data/facts/items.csv")

# The three anchors every capture states. `entry` is the Tier 5 best-in-slot
# set. The two tier states exist because Archimonde is the tier's first wall and
# it drops the head token, so whether a raid has cleared it is the difference
# between one reachable Tier 6 piece and two.
ANCHORS = ("entry", "tier_hands_only", "tier_hands_and_head")

# Spell hit is a separate stat from melee hit in 2.4.3 and one spec needs both.
TOTALS = {"total_item_hit": "hit", "total_item_spell_hit": "spell_hit"}


# Which assumed buff each cap receives. Improved Faerie Fire supplies melee and
# ranged hit only in 2.4.3, so a caster gets nothing from it, and the fact file
# carries that correction on the buff itself rather than in a spec list.
SUPPLIES = {
    "melee_special": "melee_and_ranged_hit",
    "ranged": "melee_and_ranged_hit",
    "melee_special_and_spell": "melee_and_ranged_hit",
    "spell": "spell_hit",
}



# The slot vocabulary, which every capture states in exactly these words.
#
# IT WAS THREE VOCABULARIES UNTIL 9 AUGUST 2026 AND NOTHING NOTICED. Four
# captures wrote `ring1` and `trinket1`, twelve wrote `ring_1` and `trinket_1`,
# and the Protection Paladin alone wrote `finger_1`. Two more names described a
# weapon configuration rather than a slot: `weapon` for a two-hander, in four
# captures, and `shield` for the Protection Warrior off-hand. Nothing broke,
# because all five consumers of `hit_by_slot` walk the dictionary rather than
# ask for a slot by name. What broke was reading ACROSS captures: an off-piece
# audit compared each capture to the workbook slot by slot, and the rows it
# could not match went unexamined instead of reported.
#
# The two configuration names were retired rather than kept, because they said
# nothing the item id does not. `items.csv` carries `hand_type`, which reads
# `Two Hand` for Merciless Gladiator's Maul (32014) and `Off Hand` for Aldori
# Legacy Defender (28825), so a two-hander sits in `main_hand` with no
# `off_hand` beside it and a shield sits in `off_hand`, and both are recoverable
# from the id. That is the project's own rule: only the id settles it.
SLOTS = {
    "head", "neck", "shoulder", "back", "chest", "wrist", "hands", "waist",
    "legs", "feet", "ring_1", "ring_2", "trinket_1", "trinket_2", "main_hand",
    "off_hand", "ranged", "relic",
}

# The sixteen every anchor carries. `ranged` and `relic` are the exception and
# are handled by RANGED_OR_RELIC below, because a spec holds one or the other.
#
# off_hand IS IN HERE, AND THAT IS THE POINT. Twelve anchors used to omit the
# key when the spec held a two-hander, and six recorded an explicit empty one,
# so absence meant either "two-hander" or "somebody forgot" and nothing could
# tell them apart. All fifty-four now record it explicitly, which is what makes
# the completeness check below able to mean anything.
ALWAYS = SLOTS - {"ranged", "relic"}

# Every anchor carries exactly one of these: a hunter and a caster hold a
# ranged weapon or a wand, a shaman, paladin and druid hold a relic instead.
RANGED_OR_RELIC = {"ranged", "relic"}

def assumed(hit: dict, cap: str) -> float:
    """The assumed raid debuff this cap gets, as rating."""
    wants = SUPPLIES.get(cap)
    for buff in hit.get("assumed_buffs") or []:
        if buff.get("supplies") == wants:
            return float(buff["rating_equivalent"])
    return 0.0


def state(supplied: float, target: float) -> str:
    """Full or short, on the same test extract_constraints.py applies."""
    return "full" if supplied >= target else "short"


def check_against_items(captures: Path, items_csv: Path,
                        recorded_caps: dict) -> list[str]:
    """Every hit a capture claims for an item, against what the item carries.

    THE CAPTURES ARE TRANSCRIBED BY HAND AND items.csv IS GENERATED, so where
    the two disagree the table wins. This caught three rows the sum check could
    not: a capture can agree with itself perfectly while stating the wrong hit
    for an item, because the total was summed from the same wrong number.

    All three misses ran the same way, a hit-bearing item recorded at zero: the
    warlock wand at 11 spell hit on two captures, and an arena off-hand at 10 on
    a third. A miss in that direction understates supply and would have made a
    spec look shorter of its cap than it is.
    """
    import csv

    table = {int(row["item_id"]): row for row in csv.DictReader(items_csv.open())}
    problems: list[str] = []
    for path in sorted(captures.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        # Which column a bare `hit` means depends on the spec's cap, and a
        # caster's is spell hit.
        caster = (recorded_caps.get(data.get("spec")) == "spell")
        seen: set[tuple[int, int]] = set()
        for anchor in (data.get("anchors") or {}).values():
            if not isinstance(anchor, dict):
                continue
            rows = anchor.get("hit_by_slot")
            if not isinstance(rows, dict):
                continue
            for slot, row in rows.items():
                if not isinstance(row, dict):
                    continue
                item_id = row.get("id")
                record = table.get(item_id) if isinstance(item_id, int) else None
                if record is None:
                    continue
                # COMPARED COLUMN BY COLUMN, NOT AS A SUM. Summing the two
                # passed a row claiming 15 MELEE hit for an item carrying 15
                # SPELL hit, which is the next transcription error waiting to
                # happen on the one spec that reports both.
                melee = int(float(record.get("melee_hit") or 0))
                spell = int(float(record.get("spell_hit") or 0))
                # A capture reporting one kind only puts it in `hit`, and which
                # kind that is comes from the spec's cap, so a caster's `hit` is
                # spell hit. Where a capture reports both, `hit` is the melee
                # one and `spell_hit` the other.
                if "spell_hit" in row:
                    pairs = [("hit", melee), ("spell_hit", spell)]
                else:
                    pairs = [("hit", spell if caster else melee)]
                bad = [(key, int(row.get(key) or 0), value)
                       for key, value in pairs
                       if int(row.get(key) or 0) != value]
                claimed = tuple(sorted(bad))
                if not bad or (item_id, claimed) in seen:
                    continue
                seen.add((item_id, claimed))
                for key, said, value in bad:
                    problems.append(
                        f"{path}: {slot} states {key}={said} for "
                        f"{record['name']!r} ({item_id}) and {items_csv} "
                        f"carries {value}")
    return problems


def check_progression(progression: Path, drops: Path, tokens: Path) -> list[str]:
    """The premise every tier figure rests on, checked against the drop table.

    THIS IS THE CLAIM THAT USED TO BE MADE NOWHERE. Which bosses are reachable
    four to six weeks in decides which Tier 6 tokens a tier anchor may hold, and
    until progression.yaml was written that claim lived only in the wording of
    briefs. A boss list that drifts from drops.csv, or a token attributed to the
    wrong encounter, would move every tier figure silently.

    Three things are checked: that each zone names exactly the bosses the drop
    table records for it, that the positions run 1..n with no gap or repeat, and
    that every token slot named here agrees with tokens.yaml on which boss
    supplies it.
    """
    import csv

    problems: list[str] = []
    if not progression.exists():
        return [f"{progression} is absent, so no tier figure has a stated premise"]
    facts = yaml.safe_load(progression.read_text())

    by_zone: dict[str, set[str]] = {}
    for row in csv.DictReader(drops.open()):
        by_zone.setdefault(row["zone"], set()).add(row["boss"])

    for zone, block in (facts.get("zones") or {}).items():
        bosses = block.get("bosses") or []
        named = {entry["name"] for entry in bosses}
        # Trash is a real row in the drop table and is not an encounter.
        actual = {name for name in by_zone.get(zone, set())
                  if name != "Trash / zone drop"}
        if not actual:
            problems.append(f"{progression}: zone {zone!r} is not in {drops}")
            continue
        for missing in sorted(actual - named):
            problems.append(
                f"{progression}: {zone} omits {missing!r}, which {drops} records")
        for extra in sorted(named - actual):
            problems.append(
                f"{progression}: {zone} names {extra!r}, which {drops} does not")
        if len(bosses) != block.get("encounters"):
            problems.append(
                f"{progression}: {zone} states {block.get('encounters')} "
                f"encounters and lists {len(bosses)}")
        positions = [entry["position"] for entry in bosses]
        if positions != list(range(1, len(positions) + 1)):
            problems.append(
                f"{progression}: {zone} positions are {positions}, which is not "
                "1 to n without a gap")

    # Which boss supplies which token, against the file that owns that fact.
    claimed = {entry["token"]: entry["name"]
               for block in (facts.get("zones") or {}).values()
               for entry in block.get("bosses") or []
               if entry.get("token")}
    owned = yaml.safe_load(tokens.read_text()).get("boss_by_tier_and_slot") or {}
    sixth = owned.get(6) or owned.get("6") or {}
    for slot, boss in claimed.items():
        recorded = sixth.get(slot)
        if isinstance(recorded, dict):
            recorded = recorded.get("boss")
        if recorded and recorded != boss:
            problems.append(
                f"{progression}: says the {slot} token comes from {boss!r} and "
                f"{tokens} says {recorded!r}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hit", type=Path, default=HIT)
    ap.add_argument("--captures", type=Path, default=CAPTURES)
    args = ap.parse_args()

    hit = yaml.safe_load(args.hit.read_text())
    recorded = {spec["id"]: spec for spec in hit["specs"]}

    premise = check_progression(PROGRESSION, DROPS, TOKENS)
    if premise:
        print(f"{len(premise)} problem(s) in the progression premise:",
              file=sys.stderr)
        for line in premise:
            print(f"  {line}", file=sys.stderr)
        return 1
    print(f"{PROGRESSION} agrees with {DROPS} and {TOKENS}")

    mismatched = check_against_items(
        args.captures, ITEMS,
        {spec_id: spec.get('cap') for spec_id, spec in recorded.items()})
    if mismatched:
        print(f"{len(mismatched)} capture row(s) disagree with {ITEMS}:",
              file=sys.stderr)
        for line in mismatched:
            print(f"  {line}", file=sys.stderr)
        print("\nitems.csv is generated and the captures are transcribed, so "
              "the table wins. Correct the capture.", file=sys.stderr)
        return 1
    print(f"every capture row agrees with {ITEMS} on what its items carry")
    files = sorted(args.captures.glob("*.yaml"))
    if not files:
        print(f"no captures under {args.captures}")
        return 0

    problems: list[str] = []
    print(f"{'spec':24} {'anchor':22} {'sum':>5} {'stated':>6} {'buff':>4} "
          f"{'target':>6} {'state':6}  was")
    for path in files:
        data = yaml.safe_load(path.read_text())
        # Only files carrying anchors are captures. See extract_hit_captures.
        if not isinstance(data, dict) or "anchors" not in data:
            continue
        spec = data.get("spec")
        if spec not in recorded:
            problems.append(f"{path}: spec {spec!r} is not in {args.hit}")
            continue
        target = recorded[spec].get("net_target_rating")
        old_tier = recorded[spec].get("supplied_at_tier_anchor")
        old_entry = recorded[spec].get("supplied_at_p3_entry")
        debuff = assumed(hit, recorded[spec].get("cap"))

        for anchor in ANCHORS:
            block = (data.get("anchors") or {}).get(anchor)
            if block is None:
                problems.append(f"{path}: no anchor {anchor!r}")
                continue
            rows = block.get("hit_by_slot") or {}
            if not rows:
                problems.append(f"{path}: {anchor} states no hit_by_slot rows")
                continue
            for slot in sorted(set(rows) - SLOTS):
                problems.append(
                    f"{path}: {anchor} names a slot {slot!r} that is not in the "
                    "vocabulary. A shield is off_hand, and a two-hander is "
                    "main_hand with an empty off_hand beside it; items.csv "
                    "hand_type says which")
            # COMPLETENESS, NOT ONLY SPELLING. The vocabulary check above only
            # asked whether a slot NAME was known, so a slot could vanish
            # entirely and every gate still passed. An adversarial review proved
            # it by deleting a zero-hit head slot: rc=0, no message, and the
            # generated table regenerated identically. A capture that quietly
            # loses a slot understates the set it describes.
            for slot in sorted(ALWAYS - set(rows)):
                problems.append(
                    f"{path}: {anchor} has no {slot!r} row. Every anchor carries "
                    "all of them, and a two-hander records an EXPLICIT empty "
                    "off_hand rather than omitting the key, so that an absent "
                    "slot always means a mistake and never a weapon choice")
            held = set(rows) & RANGED_OR_RELIC
            if len(held) != 1:
                problems.append(
                    f"{path}: {anchor} holds {sorted(held) or 'neither'} where "
                    "every anchor holds exactly one of ranged or relic")
            for total_key, row_key in TOTALS.items():
                if total_key not in block:
                    continue
                # The row key is absent on specs that carry only one kind of
                # hit, which is every spec but the Protection Paladin.
                summed = sum(int(row.get(row_key) or 0) for row in rows.values())
                stated = int(block[total_key])
                if summed != stated:
                    problems.append(
                        f"{path}: {anchor}.{total_key} states {stated} but its "
                        f"own rows sum to {summed}")
                if total_key != "total_item_hit":
                    continue
                was = old_entry if anchor == "entry" else old_tier
                now = state(stated + debuff, target) if target is not None else "?"
                before = state(was + debuff, target) if (
                    target is not None and was is not None) else "?"
                moved = "  <-- STATE MOVES" if now != before else ""
                plus = f"+{debuff:g}" if debuff else "  "
                print(f"{spec:24} {anchor:22} {summed:5} {stated:6} {plus:>4} "
                      f"{str(target):>6} {now:6}  was {was} ({before}){moved}")

    print(f"\n{len(files)} capture(s) checked")
    if problems:
        print(f"\n{len(problems)} problem(s):", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    print("every capture agrees with its own per-slot rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
