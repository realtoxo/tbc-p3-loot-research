#!/usr/bin/env python3
"""Roll the per-spec hit captures up into one table the compendium can read.

WHY THIS IS A SEPARATE FILE FROM hit.yaml. hit.yaml is hand-authored and
PROVENANCE.md records that nothing overwrites it. Its supplied figures come from
a rule applied to the EP Workbook: gear greedily by the primary EPV column, then
for the tier anchor swap in all five Tier 6 pieces. The guild lead ruled on
9 August 2026 that no spec wears five Tier 6 pieces four to six weeks in, which
is what this file answers instead, from published gear lists captured per spec.

TWO RULES, TWO FILES, NEITHER PRETENDING TO BE THE OTHER. The workbook rule is
reproducible and is an upper bound, because a column that already prices hit
over-collects it. The captured rule describes what a player wears and is not
reproducible, because it depends on which list was published. Keeping both, each
labelled, is the only honest arrangement: collapsing them into one number would
hide which question was asked.

WHAT `short` MEANS HERE, AND WHAT IT DOES NOT. Every figure counts ITEM hit
only. Gems and enchants are excluded, per the assumption set hit.yaml records,
and published lists assume the player gems for hit. So a spec reading short here
is short ON ITEMS, not short in play, and the gap is expressed in hit gems
beside it so the two are never confused. hit.yaml.discretionary_hit_budget is
where that route is quantified.

Usage:
    python3 tools/extract_hit_captures.py --out data/facts/hit-captured.yaml
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import yaml

HIT = Path("data/facts/hit.yaml")
CAPTURES = Path("data/facts/sim-profiles/hit-capture")
ITEMS = Path("data/facts/items.csv")

# The three states every capture reports, and the name each carries here.
ANCHORS = (
    ("entry", "entry"),
    ("tier_hands_and_head", "tier_hands_and_head"),
)

# One hit gem is 10 rating at epic quality in Phase 3, per
# hit.yaml.discretionary_hit_budget. The rare fallback is 8, which would make
# the gem counts here optimistic, so the figure is named rather than assumed.
RATING_PER_GEM = 10

ANCHOR_NAMES = ("entry", "tier_hands_and_head")

# Specs where the token arithmetic records a collision with the configuration
# these captures wear. THE STRINGS ARE MECHANICAL, not verdicts: each names the
# EP figures or the slot count that a reader can check in
# token-arithmetic.yaml. What those add up to is a reading, and readings live
# in data/judgments/token-verdicts.yaml, which no generated file quotes.
#
# Transcribed rather than pattern-matched, so a reworded fact cannot silently
# drop a spec from the list.
#
# EVERY PIECE COUNT, SLOT AND ITEM NAME IS A PLACEHOLDER FILLED FROM THE SPEC'S
# OWN CAPTURE. `fill_contested` below supplies them. THE FULLY HARDCODED
# VERSION WENT STALE THE MOMENT tools/rebuild_tier_sets.py CHANGED WHAT A TIER
# SET IS, and because the sentence never touched token-arithmetic.yaml it
# bypassed tools/check_token_arithmetic.py, so a claim already retracted there
# kept printing on a card. Three of the six were wrong when they were found:
# the Arms Warrior said the head token cost a Destroyer four-piece against a
# capture holding two Destroyer pieces, the Feral Cat said the hands token left
# one Tier 6 piece against a set holding two and no hands tier at all, and the
# Balance Druid described a Tier 5 four-piece the tier set no longer wears.
#
# WHAT IS STILL TRANSCRIBED AND WHY. An EP figure and a quotation from a
# published guide cannot be derived from a capture, because a capture records
# gear rather than item value or source wording. Both are checked instead:
# tools/check_token_arithmetic.py reproduces every figure below on the spec's
# own workbook tab. A set-bonus trade cannot be checked at all, because no fact
# table prices a set bonus, so no sentence below asserts one is worth more than
# another.
TOKEN_CONFIGURATION_CONTESTED = {
    "feral_cat": (
        "the head slot is {tier_head} and the hands slot is {tier_hands}, and "
        "neither is a tier piece, so this set takes neither token; it holds "
        "{tier6}"),
    "feral_bear": (
        "a druid has five tier slots, so the Nordrassil four-piece and the "
        "Thunderheart two-piece need six between them and cannot both be "
        "worn; this set wears {tier_sets}, which leaves it no Nordrassil "
        "piece"),
    "enhancement_shaman": (
        "the published guide states in its own words that neither Tier 6 set "
        "bonus is worth chasing for this spec, and this set holds {tier6}"),
    "retribution_paladin": (
        "Lightbringer Gauntlets 56.46 EPV against Gloves of the Searing Grip "
        "65.57, and no Retribution set bonus in either tier is a damage "
        "bonus; this set holds {tier6} and keeps {tier_hands} at the hands"),
    "balance_druid": (
        "the entry set holds {entry_tier5}, which is the Tier 5 four-piece, "
        "so either token breaks it; both tokens are raw EPV gains, and this "
        "set trades those four for {tier6}"),
    "arms_warrior": (
        "Onslaught Gauntlets 87.78 EPV against Grips of Silent Justice "
        "101.88 from Shade of Akama, and the entry set holds {entry_tier5}, "
        "so the head token costs the Destroyer two-piece and not the "
        "four-piece; this set holds {tier6}"),
}

# Slot order for a piece list, so two sentences never name the same set in two
# orders. It is the order tokens.yaml records the five tier slots in.
PIECE_ORDER = ("head", "shoulder", "chest", "hands", "legs")

# Counts run from zero to the five tier slots a class has, so no phrase below
# ever needs a sixth word.
COUNT_WORDS = ("no", "one", "two", "three", "four", "five")


def joined(parts: list[str]) -> str:
    """Name a list in prose, with `and` before the last part and no comma."""
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def pieces_phrase(slots: list[str], tier: str) -> str:
    """Say how many pieces of one tier a set holds, and in which slots.

    A COUNT ALONE IS WHAT WENT WRONG BEFORE, so the slots are named beside it.
    A reader who sees "two Tier 6 pieces, at the shoulder and the legs" can
    check the claim against the set printed on the same card; a reader who saw
    only "one Tier 6 piece" could not, and did not.
    """
    held = [slot for slot in PIECE_ORDER if slot in slots]
    count = COUNT_WORDS[len(held)] if len(held) < len(COUNT_WORDS) else str(
        len(held))
    if not held:
        return f"no {tier} piece"
    noun = "piece" if len(held) == 1 else "pieces"
    return (f"{count} {tier} {noun}, at "
            + joined([f"the {slot}" for slot in held]))


def fill_contested(template: str, data: dict) -> str:
    """Fill a contested sentence from the capture it describes.

    Only the placeholders a template uses are read, so a spec whose capture
    lacks a field is only affected if its own sentence names that field.
    """
    anchors = data.get("anchors") or {}
    entry = anchors.get("entry") or {}
    tier = anchors.get("tier_hands_and_head") or {}
    tier_rows = tier.get("hit_by_slot") or {}

    def item(slot: str) -> str:
        row = tier_rows.get(slot)
        return row.get("item") if isinstance(row, dict) else str(row)

    sets = tier.get("set_pieces_held") or {}
    return template.format(
        tier_head=item("head"),
        tier_hands=item("hands"),
        tier6=pieces_phrase(tier.get("tier6_pieces_held") or [], "Tier 6"),
        # `tier_pieces_held` on an entry anchor means TIER 5 pieces, which is
        # how this file has always consumed it. It is not every tier piece.
        entry_tier5=pieces_phrase(
            entry.get("tier5_pieces_held") or entry.get("tier_pieces_held")
            or [], "Tier 5"),
        tier_sets=joined([
            f"{COUNT_WORDS[count] if count < len(COUNT_WORDS) else count} "
            f"{'piece' if count == 1 else 'pieces'} of {name}"
            for name, count in sorted(sets.items())]),
    )


BANNER = """\
# GENERATED BY tools/extract_hit_captures.py. DO NOT EDIT.
#
# Rolled up from data/facts/sim-profiles/hit-capture, one file per spec, each
# collected by hand from that spec's published gear lists. To change a figure
# here, change the capture it came from.
#
# READ data/facts/hit.yaml FIRST. It holds the caps, the talents, the assumed
# buffs and the discretionary gem budget, none of which are restated here.
# This file holds one thing: what ITEM hit a realistic set carries, at three
# points in the tier.
"""


def gems(gap: float) -> int:
    """How many hit gems close a gap, rounded up."""
    return int(-(-gap // RATING_PER_GEM)) if gap > 0 else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hit", type=Path, default=HIT)
    ap.add_argument("--captures", type=Path, default=CAPTURES)
    ap.add_argument("--items", type=Path, default=ITEMS)
    ap.add_argument("--out", type=Path,
                    default=Path("data/facts/hit-captured.yaml"))
    args = ap.parse_args()

    # Socket colours per item, so a gem count can be checked against somewhere
    # to put the gems. A gap of fifteen gems in a set with fourteen sockets is
    # not a gemming question, and the card used to call it one.
    # ONLY RED AND YELLOW SOCKETS CAN TAKE A HIT GEM. hit.yaml names the hit
    # gems as Rigid and Great Lionseye, which are yellow, and the red-or-yellow
    # hybrids, and it states plainly that no meta gem grants hit. Counting
    # every colour inflated every set by at least the one meta socket it
    # carries, and it inflated the Protection Paladin enough to hide that its
    # spell gap is not closeable by gemming at all.
    sockets_by_id = {
        int(row["item_id"]): len([
            c for c in (row.get("sockets") or "").split("|")
            if c in ("Red", "Yellow")])
        for row in csv.DictReader(args.items.open())}

    hit = yaml.safe_load(args.hit.read_text())
    recorded = {spec["id"]: spec for spec in hit["specs"]}

    # The assumed debuff, by what it supplies rather than by a spec list, so the
    # correction that casters get nothing from Improved Faerie Fire travels with
    # the buff exactly as it does in hit.yaml.
    supplies = {
        "melee_special": "melee_and_ranged_hit",
        "ranged": "melee_and_ranged_hit",
        "melee_special_and_spell": "melee_and_ranged_hit",
        "spell": "spell_hit",
    }
    buff_by_kind = {buff.get("supplies"): float(buff["rating_equivalent"])
                    for buff in hit.get("assumed_buffs") or []}

    # The two hit enchants each school has, which hit.yaml already totals.
    budget = hit.get("discretionary_hit_budget") or {}
    enchant_total = {
        "physical": (budget.get("physical") or {}).get("enchant_total", 0),
        "spell": (budget.get("spell") or {}).get("enchant_total", 0),
    }

    out: dict[str, dict] = {}
    problems: list[str] = []
    for path in sorted(args.captures.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        # A CAPTURE IS A FILE WITH ANCHORS. Anything else in this directory is
        # skipped rather than read as a gear set: a review file written beside
        # the captures broke `just regen` the moment it appeared, because every
        # extractor globs the directory.
        if not isinstance(data, dict) or "anchors" not in data:
            continue
        spec = data.get("spec")
        if spec not in recorded:
            problems.append(f"{path}: spec {spec!r} is not in {args.hit}")
            continue
        cap = recorded[spec].get("cap")
        target = recorded[spec].get("net_target_rating")
        debuff = buff_by_kind.get(supplies.get(cap), 0.0)
        kind = "spell" if cap == "spell" else "physical"

        entry: dict = {
            "cap": cap,
            "net_target_rating": target,
            "assumed_debuff_rating": debuff,
            "capture": str(path),
        }
        # WHAT THE SET WAS ACTUALLY BUILT FROM, carried up so a reader does
        # not have to open the capture to learn that a Wowhead URL beside it
        # was attempted and not read. Seven of seventeen sets were built from
        # the in-repo workbook or from simulator presets rather than from a
        # published gear list, and the rollup used to describe all seventeen as
        # published-list work.
        sources = data.get("sources") or {}
        basis = []
        for key, block in sources.items():
            if not isinstance(block, dict):
                continue
            if block.get("outcome", "").startswith("NOT READ"):
                basis.append(f"{key}: attempted, not read")
            elif key.endswith("basis") or key == "basis":
                basis.append(f"{key}: {block.get('path') or block.get('url')}")
        if basis:
            entry["basis"] = basis
        if spec in TOKEN_CONFIGURATION_CONTESTED:
            entry["token_configuration_contested"] = fill_contested(
                TOKEN_CONFIGURATION_CONTESTED[spec], data)
        for anchor, name in ANCHORS:
            block = (data.get("anchors") or {}).get(anchor) or {}
            supplied = block.get("total_item_hit")
            if supplied is None:
                problems.append(f"{path}: {anchor} states no total_item_hit")
                continue
            gap = max(0.0, target - (supplied + debuff))
            rows = block.get("hit_by_slot") or {}
            sockets = sum(
                sockets_by_id.get(row.get("id"), 0)
                for row in rows.values() if isinstance(row, dict))

            # GEMS COME OUT OF THE GAP BEFORE ENCHANTS DO. RULED BY THE GUILD
            # LEAD ON 10 AUGUST 2026, and it reverses what this file did.
            #
            # It used to spend enchants first, reasoning that a hit enchant
            # costs no socket. That reasoning was backwards for this raid. The
            # throughput enchant a hit enchant would displace is worth more than
            # the throughput gem a hit gem displaces, so the cheaper thing to
            # give up is the gem. This guild does not take hit enchants.
            #
            # A GEM ONLY HELPS IF THERE IS A SOCKET FOR IT, which is why the
            # count is capped at the sockets the set actually carries. A gap
            # larger than the sockets can close is the interesting case, and it
            # is what `gap_after_gems` reports rather than hiding.
            gem_rating = float(sockets) * RATING_PER_GEM
            need_gems = min(gems(gap), sockets)
            supplied_by_gems = float(need_gems) * RATING_PER_GEM
            after_gems = max(0.0, gap - supplied_by_gems)
            enchants = float(enchant_total.get(kind, 0))
            after_enchants = max(0.0, after_gems - enchants)
            entry[name] = {
                "gem_sockets": sockets,
                "item_hit": int(supplied),
                "state": "full" if gap <= 0 else "short",
                "gap_rating": int(gap),
                "gems_needed": need_gems,
                "gem_rating_available": int(gem_rating),
                "gap_after_gems": int(after_gems),
                "enchant_rating_available": int(enchants),
                "gap_after_enchants": int(after_enchants),
                "gems_after_enchants": gems(after_enchants),
                "tier6_pieces_held": block.get("tier6_pieces_held") or [],
                "tier5_pieces_held": block.get("tier5_pieces_held")
                or block.get("tier_pieces_held") or [],
            }
            # THE PROTECTION PALADIN HOLDS TWO CAPS AND A BARE NUMBER IS WORSE
            # THAN NO NUMBER. This used to publish item_spell_hit beside the
            # MELEE target, so a reader comparing 38 against the only target in
            # the block read a 40 percent shortfall where the real one is 77.
            # The spell half now carries its own target, state and gap, read
            # from the spell fields hit.yaml already holds.
            if "total_item_spell_hit" in block:
                supplied_spell = int(block["total_item_spell_hit"])
                spell_target = recorded[spec].get("net_spell_target_rating")
                entry[name]["item_spell_hit"] = supplied_spell
                if spell_target is not None:
                    # Improved Faerie Fire supplies no spell hit in 2.4.3, so
                    # nothing is added on this half for any spec.
                    spell_gap = max(0.0, spell_target - supplied_spell)
                    after = max(0.0, spell_gap - float(enchant_total["spell"]))
                    entry[name]["net_spell_target_rating"] = spell_target
                    entry[name]["spell_state"] = (
                        "full" if spell_gap <= 0 else "short")
                    entry[name]["spell_gap_rating"] = int(spell_gap)
                    entry[name]["spell_enchant_rating_available"] = int(
                        enchant_total["spell"])
                    entry[name]["spell_gap_after_enchants"] = int(after)
                    entry[name]["spell_gems_after_enchants"] = gems(after)

        # What the retired rule said, kept beside the new figure rather than
        # deleted, because the size of the correction is itself worth seeing.
        entry["workbook_greedy_reference"] = {
            "entry": recorded[spec].get("supplied_at_p3_entry"),
            "tier_five_piece_swap": recorded[spec].get("supplied_at_tier_anchor"),
            "note": "The retired rule. See hit.yaml.method.tier_anchor_rule_RETIRED.",
        }
        out[spec] = entry

    if problems:
        print(f"{len(problems)} problem(s):", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1

    document = {
        "meta": {
            "generated_by": "tools/extract_hit_captures.py",
            "rule": (
                "per-spec gear sets, each sourced individually and downgraded "
                "to four to six weeks in. NOT uniformly published gear lists: "
                "Wowhead's guide pages render client-side and were unreadable "
                "for several specs, which fell back to the in-repo EP Workbook, "
                "to simulator presets, to an archive snapshot or to a secondary "
                "site. Each spec's `basis` field and its capture's `sources` "
                "block say which."),
            "counts": "item hit only",
            "excludes": "gems, enchants, consumables, talents, racials",
            "rating_per_hit_gem": RATING_PER_GEM,
            "specs_captured": len(out),
            "sibling_files": ["data/facts/hit.yaml",
                              "data/facts/progression.yaml",
                              "data/facts/sim-profiles/token-arithmetic.yaml"],
            "which_tier_slots_are_worn_was_ASSUMED_not_derived": (
                "READ THIS BEFORE QUOTING A TIER FIGURE. The two states below "
                "hold the hands token, then the hands and head tokens, because "
                "the capture brief SAID SO. Nothing here worked out whether a "
                "spec should accept a token it can reach. That is a different "
                "question and token-arithmetic.yaml already answers it, per "
                "spec, from set bonuses and item value.\n"
                "THE TWO FILES DISAGREE FOR SIX SPECS. token-arithmetic records "
                "a collision for the Feral Cat, the Feral Bear, the "
                "Enhancement Shaman, the Retribution Paladin, the Balance "
                "Druid and the Arms Warrior. Each spec below carries the "
                "mechanical fact under token_configuration_contested; what it "
                "adds up to is a reading, and readings live in "
                "data/judgments/token-verdicts.yaml. All six wear both tokens "
                "below anyway.\n"
                "Only the Arcane Mage declined a token, and only because its "
                "source guide named the refusal explicitly.\n"
                "SO A TIER FIGURE BELOW ANSWERS: what item hit would this spec "
                "carry IF it wore both reachable tokens. For eleven specs that "
                "is a reasonable reading. For the six named above it prices a "
                "set the spec would not assemble, and the hit figure should not "
                "be quoted for them without saying so."),
        },
        "specs": out,
    }
    args.out.write_text(
        BANNER + "\n" + yaml.safe_dump(document, sort_keys=True, width=78))
    short = sum(
        1 for spec in out.values() for name in ANCHOR_NAMES
        if isinstance(spec.get(name), dict) and spec[name]["state"] == "short")
    needs_gems = sum(
        1 for spec in out.values() for name in ANCHOR_NAMES
        if isinstance(spec.get(name), dict)
        and spec[name].get("gems_after_enchants"))
    print(f"{len(out)} spec(s) -> {args.out}")
    print(f"  {short} anchor reading(s) short on items alone, "
          f"{needs_gems} of them still short after the hit enchants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
