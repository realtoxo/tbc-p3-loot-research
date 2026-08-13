#!/usr/bin/env python3
"""Lift the comparison baselines out of the EPV workbook into a table Lua can read.

Every delta on a spec card is measured against something, and which something is
the whole argument. Hand-picking that alternative produced a page where the
Combat Rogue was compared against the ladder's second-ranked head and the Beast
Mastery Hunter against a tier piece the ladder ranks third, with nothing in the
output saying which rule had been applied, because there was not one.

FOUR BASELINES ON A TWO BY TWO, and all four are derived. One axis is the
phase, this phase against the phase before it. The other axis is tier against
off-piece. The four cells are disjoint by construction:

                  tier piece                best off-piece
    this phase    tier6                     phase3
    pre-phase     tier5                     prephase

    tier5     the spec's own Tier 5 piece for that slot, read from
              data/facts/tokens.yaml, block spec_to_set, key 5, then from the
              pieces map of that set. A raider obtains it by raiding, and most
              of the roster wears it into Phase 3.
    tier6     the spec's own Tier 5 set's successor, key 6, read the same way.
              This is the set-progress question.
    phase3    the highest-EPV item for that slot whose workbook Phase column
              reads 3 and which belongs to no tier set. This is the column the
              cards were missing: for six of the seven specs on the worked
              example the best Phase 3 off-piece beats their own tier head, and
              one Black Temple mail helm is contested by three specs at once.
    prephase  the highest-EPV item for that slot whose workbook Phase column
              reads 1 or 2 and which belongs to no tier set. This is the
              off-piece a raider carries into the phase.

WHY THE MIDDLE VIEW WAS SPLIT IN TWO. There used to be one `entry` baseline,
the highest-EPV Phase 1 or 2 item, tier or not. It overlapped `tier5`, because
a Tier 5 piece is a Phase 2 item, and for four of the eight cards on the worked
example the two resolved to the same item and collapsed into one column. Two
categories that are not disjoint produce a collapse that reads as informative
and is a defect. Excluding tier from both off-piece cells makes the four
disjoint, so no derived pair can ever resolve to one item.

TWO OR MORE CANDIDATES ARE EMITTED PER OFF-PIECE CELL, not one, because the
item under discussion is itself frequently the best off-piece in its own slot
and a card must not compare an item with itself. `Cursed Vision of Sargeras` is
the top Phase 3 head on seven of the eight ladders on the worked example, so a
single candidate would drop the whole new column there. The item under
discussion can occupy at most one rank, so two candidates always leave one.

WHY THE ACQUISITION ROUTE IS RECORDED. A baseline used to be emitted with no
statement of how it is obtained, and four of the eight baselines on the worked
example turned out to be gated: the Combat Rogue and the Feral Cat were
compared against `Deathblow X11 Goggles`, which only an engineer wears, the
Beast Mastery Hunter against `Surestrike Goggles v2.0`, the same trap, and the
Survival Hunter against `Merciless Gladiator's Chain Helm`, which is arena gear.
A rogue who is not an engineer was being compared against a helm he cannot get,
and nothing in the output said so. The route is now recorded on EVERY baseline,
tier and off-piece alike, not only on the ones gated today, because the gating
is the fact and a later ladder change must not reintroduce the defect silently.
A tier baseline takes its route from the boss that drops its token, which
tokens.yaml records in boss_by_tier_and_slot.

`theme/filters/delta.lua` renders them. Lua cannot read the workbook CSVs and
must not carry a second parser of them, so the selection happens here, at
`just regen` time, exactly as `tools/extract_conversions.py` lifts the rates out
of the YAML fact files. The output is a build artifact, not a fact: it states
nothing the workbook and tokens.yaml do not already state, `just check`
regenerates it and fails on any drift, and every entry names the tab it was read
from.

TIER MEMBERSHIP IS NOT A NAME TEST. Tier pieces sit in the ladders beside raid
drops, so "the best item that is not tier" cannot be computed by reading names.
Which pieces are tier comes from spec_to_set and the set piece lists, and from
nowhere else. A probe written the other way reported Slayer's Helm as the
Rogue's best non-tier head; it is the Rogue's tier head, and a name filter
returns Cursed Vision of Sargeras, which is the item under discussion.

WHY THE ITEM DATABASE IS READ HERE. `data/facts/items.csv` holds raid drops and
tier pieces. The ladder reaches wider than that: the Rogue's best Phase 1 or 2
head is an engineering goggle and the Survival Hunter's is an arena piece, and
neither is a raid drop. Where items.csv holds the baseline this file names it
and stops, because items.csv is the stat line's one home. Where items.csv does
not hold it, the stat line is read from the same item database that produces
items.csv and carried here, so no baseline is named without the stats needed to
compare against it.

Usage:
    python3 tools/extract_ladder.py --db PATH --out theme/filters/ladder.generated.lua
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import yaml

# The stat and slot vocabularies are the item database's own, transcribed once
# in the extractor that writes items.csv. A second transcription here would be a
# second answer to which index is which stat, and an earlier hand-written map in
# this repository was off by one and filed every belt as a wrist item.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_items import ITEM_TYPE, STAT  # noqa: E402

# The database's own hand vocabulary, matching tools/extract_items.py.
HAND_TYPE = {0: "", 1: "Main Hand", 2: "One Hand", 3: "Off Hand", 4: "Two Hand"}

WORKBOOK = Path("data/research/epv-workbook")
TOKENS = Path("data/facts/tokens.yaml")
ITEMS = Path("data/facts/items.csv")

# Spec identity: which tab holds the ladder, and which key in the spec_to_set
# block of tokens.yaml holds the tier set. Both are explicit, never inferred
# from a file name. Two pairs of tabs carry identical titles and only their tier
# pieces distinguish them, per data/research/epv-workbook/PROVENANCE.md:
# Prot.csv is the Protection WARRIOR and Tank.csv the Protection PALADIN;
# Holy.csv is the PRIEST healer and Heal.csv the PALADIN healer.
#
# The registry covers the twenty-one specs that have both a ladder and a Tier 6
# set. A spec outside it has no derived baseline, and delta.lua fails naming it
# rather than reading a neighboring tab.
SPECS: dict[str, tuple[str, str]] = {
    "Combat Rogue": ("Rog.csv", "combat_rogue"),
    "Arms Warrior": ("Arms.csv", "arms_warrior"),
    "Fury Warrior": ("Fury.csv", "fury_warrior"),
    "Protection Warrior": ("Prot.csv", "protection_warrior"),
    "Retribution Paladin": ("Ret.csv", "retribution_paladin"),
    "Protection Paladin": ("Tank.csv", "protection_paladin"),
    "Holy Paladin": ("Heal.csv", "holy_paladin"),
    "Enhancement Shaman": ("Enh.csv", "enhancement_shaman"),
    "Elemental Shaman": ("Ele.csv", "elemental_shaman"),
    "Restoration Shaman": ("Resto.csv", "restoration_shaman"),
    "Feral Cat": ("Cat.csv", "feral_cat"),
    "Feral Bear": ("Bear.csv", "feral_bear"),
    "Balance Druid": ("Owl.csv", "balance_druid"),
    "Restoration Druid": ("Tree.csv", "restoration_druid"),
    "Beast Mastery Hunter": ("BM.csv", "beast_mastery_hunter"),
    "Survival Hunter": ("SV.csv", "survival_hunter"),
    "Arcane Mage": ("Arc.csv", "arcane_mage"),
    "Shadow Priest": ("Shad.csv", "shadow_priest"),
    "Priest Healer": ("Holy.csv", "priest_healer"),
    "Affliction Warlock": ("Aff.csv", "affliction_warlock"),
    "Destruction Warlock": ("Dest.csv", "destruction_warlock"),
}

# The workbook's slot vocabulary against the one items.csv uses, which is the
# one delta.lua reads off the item under discussion. It is `Shoulders` and
# `Ring` in the sheet and `Shoulder` and `Finger` in the item table, and
# guessing either way round files rings under Waist without erroring.
#
# The weapon sections are absent here and handled by WEAPON_SECTIONS below,
# because items.csv calls every weapon `Weapon` and one name cannot select
# between four ladders. The hand the database records is what selects it.
SECTION_TO_SLOT = {
    "Head": "Head",
    "Neck": "Neck",
    "Shoulders": "Shoulder",
    "Back": "Back",
    "Chest": "Chest",
    "Wrist": "Wrist",
    "Hands": "Hands",
    "Waist": "Waist",
    "Ring": "Finger",
    "Legs": "Legs",
    "Feet": "Feet",
    "Trinket": "Trinket",
    "Ranged": "Ranged",
}

# WHICH WORKBOOK SECTION IS A WEAPON'S LADDER.
#
# items.csv files every weapon under the one slot `Weapon` and records the hand
# the database gives it, `handType` being main hand, one hand, off hand or two
# hand. The workbook files a weapon by the hand a raider puts it in, and its
# section names are not the database's names. So the hand selects the section,
# and the slot key a weapon takes here is `Weapon:` and the hand, which is what
# `delta.lua` rebuilds from the item under discussion.
#
# The sections a tab actually carries decide the rest, in the order written:
#
#   A tab carries EITHER `Main Hand` OR `One Hand`, never both, and both hold
#   database main-hand and one-hand items together. The Fury tab's `Main Hand`
#   holds 6 main-hand and 7 one-hand items; the Arcane tab's `One Hand` holds
#   5 main-hand items and no one-hand ones. So a main-hand item and a one-hand
#   item read the same ladder, whichever of the two names the tab uses.
#
#   An off-hand item takes `Off Hand` where the tab has one. Where it does not,
#   the tab's single-hand section IS its off-hand ladder, and that is the
#   workbook's own filing rather than an inference: the Rogue tab's `Main Hand`
#   holds 3 off-hand items, the Enhancement tab's `One Hand` holds 2, and the
#   Survival tab's `One Hand` holds 2.
#
#   A two-hand item takes `Two Hand`, and there is no fallback. The Fury tab
#   has no `Two Hand` section, and a Fury Warrior comparing a two-hander
#   against a main-hand ladder would be a fabricated comparison, so that card
#   renders no derived view and says why.
WEAPON_SECTIONS = {
    "MainHand": ("Main Hand", "One Hand"),
    "OneHand": ("Main Hand", "One Hand"),
    "OffHand": ("Off Hand", "Main Hand", "One Hand"),
    "TwoHand": ("Two Hand",),
}

# The five slots a Tier 4, Tier 5 or Tier 6 set covers, as tokens.yaml names
# them against the items.csv vocabulary. A Neck, Back, Wrist, Waist, Finger,
# Feet, Trinket or Ranged comparison has no tier baseline in either tier, so a
# card in one of those slots renders the views that exist and no others.
PIECE_TO_SLOT = {
    "head": "Head",
    "shoulder": "Shoulder",
    "chest": "Chest",
    "hands": "Hands",
    "legs": "Legs",
}

# The four acquisition routes that decide whether a raider can obtain an item.
# Four buckets, not one per profession and not one per arena season: the reader
# needs to know whether the baseline is gated and by what kind of gate, and the
# raw Location string is carried beside the bucket so the source stays visible.
#
# `Leather Armor` is the workbook's own label on the three Deathmantle pieces
# and it is read here as the workbook writes it. `Crafted` is the workbook's
# generic label where it names no profession.
CRAFTED_LOCATIONS = {
    "alchemy",
    "blacksmithing",
    "cloth armor",
    "crafted",
    "enchanting",
    "engineering",
    "jewelcrafting",
    "leather armor",
    "leatherworking",
    "mail armor",
    "plate armor",
    "tailoring",
}
ARENA_LOCATIONS = {"season 1", "season 2", "season 3"}
BADGE_LOCATIONS = {"badge of justice"}


def route_of(location: str) -> str:
    """Which of the four acquisition routes one workbook Location names."""
    key = location.strip().lower()
    if key in CRAFTED_LOCATIONS:
        return "crafted"
    if key in ARENA_LOCATIONS:
        return "arena"
    if key in BADGE_LOCATIONS:
        return "badge"
    return "drop"

# Column 1 is the rank, column 2 the name, column 4 the quality. The scoring and
# phase columns move between tabs and are discovered from the label row.
RANK_COL, NAME_COL, QUALITY_COL = 1, 2, 4


class Unreadable(SystemExit):
    """The workbook, the tokens or the database did not answer. The run stops."""


def cell(row: list[str], index: int) -> str:
    return row[index].strip() if index < len(row) else ""


def columns(rows: list[list[str]], tab: Path) -> tuple[int, dict[str, int]]:
    """The label row, and where the scores, the location, the phase and the link sit.

    Column positions are not fixed and must be discovered. The Phase data sits
    one column to the RIGHT of the Phase label, because the boss column between
    Location and Phase carries no label. The Location data sits UNDER its own
    label, so it is read at the label index and not one to the right. The four
    healer tabs have no `If Hit Capped` column, so everything after EPV shifts
    one to the left there, which is why nothing below is counted from the start
    of the row.
    """
    for index, row in enumerate(rows[:10]):
        labels = [c.strip() for c in row]
        if all(name in labels for name in ("Item", "EPV", "Location", "Phase")):
            phase = labels.index("Phase") + 1
            return index, {
                "epv": labels.index("EPV"),
                "location": labels.index("Location"),
                "phase": phase,
                "url": phase + 1,
            }
    raise Unreadable(
        f"extract_ladder.py: no label row in {tab}. Row 2 carries the labels "
        "Item, EPV, Location and Phase, and one of them is absent."
    )


def read_tab(tab: Path) -> dict[str, list[dict]]:
    """Every item row on one tab, in the section it was written under.

    A section header carries the slot name in column 2, nothing through column
    10, AND an empty rank cell. The rank test is what stops the quarantined
    `Yes, its that good.` row, the `0` row below it and the blank row after
    those from being read as three headers in the Head block of the Cat tab,
    which loses that whole section silently.

    A row is an item if it carries a name in column 2 and a quality in column 4.
    A rank number is NOT required: the Ranged section of the Arms tab and the
    tail of the Two Hand section on the Owl and Shadow tabs carry items with an
    empty rank cell, and dropping them is silent data loss.
    """
    rows = list(csv.reader(tab.open(newline="", encoding="utf-8")))
    start, where = columns(rows, tab)

    ladder: dict[str, list[dict]] = {}
    section = None
    for row in rows[start + 1:]:
        name = cell(row, NAME_COL)
        if not name:
            continue
        is_header = (
            not cell(row, RANK_COL)
            and not any(cell(row, n) for n in range(NAME_COL + 1, 11))
        )
        if is_header:
            section = name
            continue
        if not cell(row, QUALITY_COL):
            continue
        # Scores of 1000 and above carry a thousands separator, and a bare
        # float() raises and drops the row without a message.
        try:
            epv = float(cell(row, where["epv"]).replace(",", ""))
        except ValueError:
            continue
        phase = cell(row, where["phase"])
        if not phase.isdigit():
            continue
        # Item ids come from the Wowhead URL, never from the name: the names in
        # the sheet are truncated and occasionally differ from the item's own.
        link = re.search(r"item=(\d+)", cell(row, where["url"]))
        # The route is recorded on every row, not only on a gated one, so that
        # a later ladder change cannot reintroduce an unlabeled gated baseline.
        location = cell(row, where["location"])
        ladder.setdefault(section or "", []).append({
            "item_id": int(link.group(1)) if link else None,
            "epv": epv,
            "phase": int(phase),
            "location": location,
            "route": route_of(location),
        })
    return ladder


# Two candidates per off-piece cell. The item under discussion occupies at most
# one rank, so two always leave one, and a third would be carried on every
# entry of the generated table to answer a case that cannot arise.
CANDIDATES = 2

# How deep the per-spec shortlist runs. Five is the count the compendium shows
# on a spec page and the count that decides which specs earn a card on an item
# page, so the two are the same number on purpose: a spec that would be shown
# the item on its own page is a spec the item page shows as a claimant.
SHORTLIST = 10

# TEN EVERYWHERE, FIFTEEN FOR WEAPONS. Five showed too little of the field, so
# the guild lead raised every slot to ten on 10 August 2026 and weapons to
# fifteen. Weapons earn the wider list because their sections are the densest
# and most contested in the workbook, and because a spec fills two hands from
# one of them. Trinkets sit at ten by the same ruling even though a player
# wears two, so they take the default rather than a constant of their own.
WIDE_SHORTLIST = 15


def select(rows: list[dict], limit: int = SHORTLIST) -> list[dict]:
    """The rows a weapon or armor section shows, best first.

    FIVE OBTAINABLE ITEMS, THEN ANY PVP THAT COMPETES. A straight top five let
    arena weapons take the whole cut: on the Enhancement one-hand section
    fourteen of the twenty-four rows above Syphon of the Nathrezim were arena,
    eight of them Vengeful variants sharing an EPV value to the penny because
    they are ONE stat block in different weapon flavours. Twenty-seven weapon
    sections had Season 3 inside the top five and fifty-three raid items were
    shut out of one.

    Arena weapons are still IN, per the guild lead's ruling that arena armor is
    out and arena weapons are in. What changed on 10 August 2026 is that they no
    longer consume a place: the five best items the raid can obtain are taken
    first, and an arena weapon joins them when its EPV reaches the fifth of
    them. So a competitive arena weapon is still shown and an uncompetitive one
    is not, and neither can push a raid drop off the list.
    """
    pve = [row for row in rows if row["route"] != "arena"]
    picked = pve[:limit]
    if not picked:
        return rows[:limit]
    # THE BAR IS THE LAST OBTAINABLE ITEM SHOWN. It was briefly pinned to the
    # fifth, to stop the arena block bloating the list when the count rose. That
    # reason no longer holds: the clone dedupe below collapses the eight
    # Vengeful rows to two, which fixes the bloat at its cause, while the pin
    # fixed it by hiding weapons the guild lead expected to see. The Merciless
    # Gladiator block sits at 788.73 against an Enhancement fifth of 799.51 and
    # a fifteenth well below it, so the pin was what removed it.
    floor = picked[-1]["epv"]
    # ONE ROW PER ARENA STAT BLOCK. The Vengeful set is six weapon flavours of
    # a single item, which is why eight of them share 844.87 and 844.14 to the
    # penny, and the Merciless set repeats the pattern. Listing each variant
    # separately says a shaman has eight choices where the shaman has one, so
    # variants sharing an EPV collapse to the first and carry the count. Only
    # ARENA rows collapse: two raid drops landing on the same EPV are two
    # different items and both belong on the page.
    seen: dict[float, dict] = {}
    for row in rows:
        if row["route"] != "arena" or row["epv"] < floor:
            continue
        first = seen.get(row["epv"])
        if first is None:
            entry = dict(row)
            entry["variants"] = 1
            seen[row["epv"]] = entry
            picked.append(entry)
        else:
            first["variants"] += 1
    picked.sort(key=lambda row: row["epv"], reverse=True)
    return picked


def shortlist(
    ladder: dict[str, list[dict]],
    section: str,
    tier_ids: set[int],
    world_boss: set[int],
    level_60: frozenset[str],
) -> list[dict]:
    """The best items in one section, best first, across every phase.

    DIFFERENT QUESTION FROM `off_pieces`, which is why it is a different
    function. That one answers "what should this item be compared against",
    so it excludes tier and splits the phases apart. This answers "what does
    this spec want in this slot", so it keeps tier pieces, keeps every phase,
    and marks each row with what it is. An item from an earlier tier appears
    where it still ranks, which is the point: a spec whose best waist is still
    a Tier 5 piece should see that.

    Arena armor is out and arena weapons are in, the same rule and for the same
    reason as the comparison baselines. A WEAPON SLOT NO LONGER USES THIS
    FUNCTION for its card: `weapon_views` builds the seven weapon comparisons
    instead. This still supplies every armor slot and the shortlists.
    """
    arena_allowed = section in WEAPON_SECTION_NAMES
    rows = [
        row for row in ladder.get(section, [])
        if row["item_id"]
        and row["item_id"] not in world_boss
        and row["location"] not in level_60
        and (arena_allowed or row["route"] != "arena")
    ]
    rows.sort(key=lambda row: row["epv"], reverse=True)
    out = []
    limit = WIDE_SHORTLIST if section in WIDE_SECTIONS else SHORTLIST
    for rank, row in enumerate(select(rows, limit), 1):
        entry = dict(row)
        entry["rank"] = rank
        entry["tier"] = row["item_id"] in tier_ids
        out.append(entry)
    return out



# WHAT A WEAPON CARD COMPARES AGAINST, ruled by the guild lead on 12 August
# 2026: the best four weapons that are not PvP, then the Season 3 arena weapon,
# then the Season 2 arena weapon, and the weapon the raider walks into the tier
# holding. Seven comparisons rather than the two an armor slot gets, because a
# weapon is the most contested slot in the tier and the arena seasons are real
# competition a council has to weigh rather than noise to hide.
#
# ARENA IS DEDUPLICATED TO ONE PER SEASON. The Vengeful and Merciless sets are
# one stat block sold in several weapon flavours, so the seasons contribute one
# comparison each and not six.
WEAPON_VIEWS = ("nonpvp1", "nonpvp2", "nonpvp3", "nonpvp4", "season3",
                "season2", "entry")


def entry_weapons(captures: Path) -> dict[str, dict[str, int]]:
    """The weapon each spec walks into the tier holding, per hand.

    Read from the entry anchor of every capture. A spec with no capture, which
    is every healer, contributes nothing and its cards simply carry no entry
    column.
    """
    out: dict[str, dict[str, int]] = {}
    for path in sorted(captures.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text())
        block = (doc.get("anchors") or {}).get("entry") or {}
        slots = block.get("hit_by_slot") or {}
        held = {}
        for hand in ("main_hand", "off_hand"):
            entry = slots.get(hand) or {}
            if entry.get("id"):
                held[hand] = int(entry["id"])
        if held:
            out[doc.get("spec") or path.stem.replace("-", "_")] = held
    return out


def weapon_views(rows: list[dict], hand: str, hand_of: dict[int, str],
                 entry_id: int | None,
                 slot_of: dict[int, str] | None = None,
                 named: dict[int, dict] | None = None) -> dict[str, list[dict]]:
    """The seven weapon comparisons, each as a one-item list.

    A list rather than a bare row so `first_other` in delta.lua can skip the
    item under discussion exactly as it does for an armor cell.
    """
    def fits(row: dict) -> bool:
        # A WEAPON SECTION IS NOT ALWAYS ALL WEAPONS. The Priest Healer tab
        # files Vengeful Gladiator's Baton of Light, a wand, inside Two Hand,
        # and the item database calls it Ranged. Dropping the phase filter
        # surfaced it and the slot check then stopped the build. A row the
        # database files outside the Weapon slot is not a weapon comparison.
        if slot_of is not None:
            named = slot_of.get(row["item_id"])
            if named and named != "Weapon":
                return False
        worn = hand_of.get(row["item_id"], "")
        if not worn:
            return True
        if hand == "OffHand":
            return worn != "Main Hand"
        if hand in ("MainHand", "OneHand"):
            return worn != "Off Hand"
        return True

    named = named or {}
    usable = [r for r in rows if fits(r)]
    views: dict[str, list[dict]] = {}

    # EVERY VIEW CARRIES A FALLBACK, because `first_other` in delta.lua skips
    # the item the card is about. A one-item view yields nothing for the very
    # weapon it names, and the card then states that the weapon does not exist
    # while the reader is looking at its page. The fifth non-PvP weapon is the
    # fallback for all four non-PvP views, so whichever one the card is about,
    # the other three keep their own pick and the fourth shows the fifth.
    nonpvp = [r for r in usable if r["route"] != "arena"][:5]
    spare = [dict(nonpvp[4])] if len(nonpvp) > 4 else []
    for index in range(4):
        if index < len(nonpvp):
            views[f"nonpvp{index + 1}"] = [dict(nonpvp[index])] + spare

    # A season carries its runner-up for the same reason, and for a second one:
    # the single pick can fail the hand check in `fill`, which emptied the
    # Enhancement Shaman Season 2 column even though Merciless Gladiator's
    # Right Ripper sat in the same section and fits the hand.
    for key, season in (("season3", "Season 3"), ("season2", "Season 2")):
        of_season = [dict(r) for r in usable if r["location"] == season][:3]
        if of_season:
            views[key] = of_season

    if entry_id is not None:
        carried = next((r for r in usable if r["item_id"] == entry_id), None)
        if carried:
            views["entry"] = [dict(carried)]
        elif entry_id in named:
            # THE TAB DOES NOT HAVE TO RANK WHAT THE RAIDER CARRIES IN. The
            # Protection Warrior walks in holding Dragonstrike and the Beast
            # Mastery Hunter holds Claw of the Phoenix, and neither is a row of
            # its own spec's weapon section, so the column vanished and the card
            # said nothing was carried in. What the raider holds is a fact about
            # the capture rather than a ranking, so it is taken from items.csv
            # and carries no EPV, because the tab priced none.
            row = named[entry_id]
            views["entry"] = [{
                "item_id": entry_id, "name": row["name"],
                "location": row.get("source", "") or "carried in",
                "route": "drop",
            }]
    return views


def tier_item_ids(tokens: dict) -> set[int]:
    """Every item id that belongs to a recorded tier set, at any tier.

    This is the one test for tier membership. It is a set of ids and never a
    test on a name, per the note at the head of this file. The Sunwell pieces
    listed under out_of_scope_phase_5 are tier as well, so their ids are read
    out of those strings, which are written `Name 34546`.
    """
    ids: set[int] = set()
    for block in tokens["sets"]:
        for piece in block["pieces"].values():
            ids.add(int(piece["item_id"]))
        for named in block.get("out_of_scope_phase_5") or []:
            found = re.search(r"(\d+)\s*$", str(named))
            if found:
                ids.add(int(found.group(1)))
    return ids


# The workbook sections that hold a weapon. Arena gear is excluded from every
# other section and kept in these, per the note in off_pieces.
WEAPON_SECTION_NAMES = frozenset(
    name for names in WEAPON_SECTIONS.values() for name in names)

# The sections that show ten rather than five.
WIDE_SECTIONS = WEAPON_SECTION_NAMES


WORLD_BOSSES = Path("data/facts/world-bosses.yaml")

LEVEL_60 = Path("data/facts/level-60.yaml")


def level_60_locations(path: Path) -> frozenset[str]:
    """The workbook Location strings that name a level-60 raid.

    MATCHED ON LOCATION, not on an id list, because for the ladder the
    exclusion is whole raids rather than a table of drops.

    THIS READ "Naxxramas" AND NOTHING ELSE until 10 August 2026, on a sweep
    that was said to have found exactly one level-60 name in use. There are
    three. Counting the Location column across all eighteen tabs gives
    Naxxramas 97 rows, Blackwing Lair 11 and Ahn'Qiraj 1. Nothing rendered
    wrong, because the eleven and the one score below the shortlist cut, so the
    output was right by luck while the enforcement rested on a false premise.
    Found by an adversarial review that was asked to refute rather than confirm.
    """
    return frozenset(yaml.safe_load(path.read_text())["raids"])


def world_boss_ids(path: Path) -> set[int]:
    """Every item the two outdoor world bosses drop.

    THE WORKBOOK IS NOT EDITED AND NEVER IS. It ranks these items, and it is
    right to: they exist and they score what they score. This filter is applied
    to what WE generate from it, so that nothing the compendium puts in front of
    the council is gear the raid will not go and get.

    Ruled by the guild lead on 9 August 2026, see
    data/judgments/capture-fidelity.yaml raid_scope. The ids live in a fact file
    because check_capture_availability.py needs the same list.
    """
    facts = yaml.safe_load(path.read_text())
    return {
        item_id
        for block in (facts.get("bosses") or {}).values()
        for item_id in (block.get("drops") or {})
    }


def off_pieces(
    ladder: dict[str, list[dict]],
    section: str,
    phases: tuple[int, ...],
    tier_ids: set[int],
    world_boss: set[int],
    level_60: frozenset[str],
    hand: str = "",
    hand_of: dict[int, str] | None = None,
) -> list[dict]:
    """The best non-tier items in one section, in the given phases, best first.

    Tier is excluded by id, so the off-piece cells cannot overlap the tier
    cells and no derived pair can resolve to one item.

    ARENA ARMOR IS EXCLUDED AND ARENA WEAPONS ARE NOT. Ruled by the guild lead
    on 9 August 2026 and recorded at data/judgments/capture-fidelity.yaml
    raid_scope.arena_gear_armor_out_weapons_in, which is where the reasoning
    lives. A resilience-bearing armor piece is not what a raider
    gears into, and measuring a raid drop against one asks the council to
    compare a piece the roster is not assumed to hold and would not want. A
    weapon is the opposite case: an arena weapon is a genuine competitor for a
    raid weapon, it carries no armor to distort the comparison, and for several
    specs it is the best thing available in the slot. The two are therefore
    treated differently, which is a decision and is recorded as one.
    """
    arena_allowed = section in WEAPON_SECTION_NAMES
    eligible = [
        row for row in ladder.get(section, [])
        if row["phase"] in phases
        and row["item_id"]
        and row["item_id"] not in tier_ids
        and row["item_id"] not in world_boss
        and row["location"] not in level_60
        and (arena_allowed or row["route"] != "arena")
    ]
    # THE HAND IS FILTERED BEFORE THE CUT, NOT AFTER. A section fallback puts
    # main-hand weapons in front of an off-hand card: the Rogue tab has no
    # `Off Hand` section, so `Main Hand` is read, and its top rows are main-hand
    # only. Filtering after the cut emptied the card instead of correcting it,
    # because the whole candidate pool was main-hand. The workbook files
    # off-hand items lower in the same section on their own value scale, so the
    # rows that belong on the card are there to be found once the cut stops
    # taking them.
    if hand and hand_of:
        def fits(row: dict) -> bool:
            worn = hand_of.get(row["item_id"], "")
            if not worn:
                return True
            if hand == "OffHand":
                return worn != "Main Hand"
            if hand in ("MainHand", "OneHand"):
                return worn != "Off Hand"
            return True
        eligible = [row for row in eligible if fits(row)]
    eligible.sort(key=lambda row: row["epv"], reverse=True)
    # ONE ARENA STAT BLOCK IS ONE COMPARISON. The Vengeful and Merciless sets
    # are a single item sold in several weapon flavours, which is why their
    # entries share an EPV to the penny. Eleven baseline cells held two of them,
    # so a card offered two comparisons that were the same weapon twice and the
    # second candidate did no work. The second candidate exists so a card never
    # compares an item with itself, which needs it to be a DIFFERENT item.
    #
    # The guild lead ruled on 12 August 2026 that weapons inside the tier are
    # compared, deduplicated, so arena weapons stay and only the duplicates go.
    seen: set[float] = set()
    deduped = []
    for row in eligible:
        if row["route"] == "arena":
            if row["epv"] in seen:
                continue
            seen.add(row["epv"])
        deduped.append(row)
    return deduped[:CANDIDATES]


def tier_pieces(tokens: dict, key: str, tier: int, spec: str) -> dict[str, dict]:
    """One spec's pieces for one tier by slot, from spec_to_set and its set.

    Each piece carries the zone its token drops in, read from
    boss_by_tier_and_slot, so a tier baseline states its acquisition route in
    words exactly as an off-piece baseline does. A tier token is a raid drop, so
    the route bucket is always `drop`.

    Fails naming the spec, the tier and the slot rather than returning a short
    map, because a set silently missing one of its five pieces would drop one
    comparison view off one card and say nothing.
    """
    zones = tokens["boss_by_tier_and_slot"][tier]
    sets = tokens["spec_to_set"].get(key)
    if not sets or tier not in sets:
        raise Unreadable(
            f"extract_ladder.py: {spec} has no Tier {tier} set.\n"
            f"  wanted  {TOKENS}  ::  spec_to_set.{key}.{tier}\n"
            "Every spec in SPECS must name a set at Tier 5 and at Tier 6, "
            "because two of the three comparison views on its cards are "
            "measured against them."
        )
    name = sets[tier]
    for block in tokens["sets"]:
        if block["set_name"] == name and block["tier"] == tier:
            pieces = {
                PIECE_TO_SLOT[slot]: {
                    "item_id": int(piece["item_id"]),
                    "name": piece["name"],
                    "location": zones[slot]["zone"],
                    "route": "drop",
                }
                for slot, piece in block["pieces"].items()
                if slot in PIECE_TO_SLOT
            }
            absent = sorted(set(PIECE_TO_SLOT.values()) - set(pieces))
            if absent:
                raise Unreadable(
                    f"extract_ladder.py: {spec} wears {name!r} at Tier {tier} "
                    f"and that set lists no piece for {', '.join(absent)}.\n"
                    f"  wanted  {TOKENS}  ::  sets  ::  {name}  ::  pieces\n"
                    "A Tier 4 or Tier 5 set is five pieces: head, shoulder, "
                    "chest, hands and legs."
                )
            return pieces
    raise Unreadable(
        f"extract_ladder.py: {spec} wears {name!r} at Tier {tier} and no set of "
        f"that name and tier is in {TOKENS}."
    )


def stat_line(item: dict) -> dict[str, int]:
    """Every stat the database records for one item, by the name items.csv uses."""
    scaling = item.get("scalingOptions", {}).get("0", {})
    return {
        STAT[int(index)]: value
        for index, value in scaling.get("stats", {}).items()
        if value and int(index) in STAT
    }


# --------------------------------------------------------------------- writing


def lua_string(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def lua_number(value: float) -> str:
    return str(int(value)) if float(value) == int(value) else repr(float(value))


HEADER = """\
-- GENERATED BY tools/extract_ladder.py. DO NOT EDIT.
--
-- The four comparison baselines every derived delta is measured against, per
-- spec and per slot. An ARMOR slot carries a two by two of phase against
-- tier. A WEAPON slot carries seven views instead, the four best non-PvP
-- weapons, one Season 3, one Season 2 and the weapon the raider carries
-- into the tier, because no tier set holds a weapon. `delta.lua` reads
-- this table and no other source of baselines. Run `just regen` to rewrite it;
-- `just check` regenerates it and fails if it drifted.
--
--                 tier piece   best off-piece
--   this phase    tier6        phase3
--   pre-phase     tier5        prephase
--
--   tier5     the spec's own Tier 5 piece for that slot, which a raider
--             obtains by raiding and which most of the roster wears in
--   tier6     the spec's own Tier 6 piece for that slot
--   phase3    the best items in that slot whose Phase column reads 3 and which
--             belong to no tier set, best first
--   prephase  the same, for a Phase column reading 1 or 2
--
-- The four cells are disjoint: the phase separates the rows and tier
-- membership separates the columns, so no two of them can resolve to one item.
-- Tier membership is a test on the item ids in tokens.yaml and never on a name.
--
-- An off-piece cell holds two candidates rather than one, because the item
-- under discussion is frequently the best off-piece in its own slot and a card
-- must not compare an item with itself. It occupies at most one rank, so the
-- second candidate is always available to `delta.lua`.
--
-- `location` and `route` appear on EVERY baseline, tier and off-piece alike,
-- because the best item in a slot is frequently one a raider cannot obtain: an
-- engineering goggle, an arena piece or a badge reward. On an off-piece
-- `location` is the workbook Location column verbatim; on a tier piece it is
-- the zone its token drops in. `route` is one of crafted, arena, badge or
-- drop. Both are recorded on every baseline and not only on the gated ones, so
-- a later ladder change cannot reintroduce an unlabeled gated baseline.
--
-- `stats` appears only on a baseline that data/facts/items.csv does not hold,
-- which is every ladder item outside raid loot and the tier sets. Where
-- items.csv holds the item, the stat line is read from there and is not copied
-- here, because a second copy of a stat line is the copy that goes stale.
--
-- Sources:
--   data/research/epv-workbook/*.csv
--   data/facts/tokens.yaml
"""


def render_item(item: dict, indent: str, opener: str = "{") -> list[str]:
    """One baseline as a Lua table constructor, opened by the caller's line."""
    out = [f"{indent}{opener}"]
    out.append(f"{indent}  item_id = {item['item_id']},")
    out.append(f"{indent}  name = {lua_string(item['name'])},")
    out.append(f"{indent}  location = {lua_string(item['location'])},")
    out.append(f"{indent}  route = {lua_string(item['route'])},")
    if "epv" in item:
        out.append(f"{indent}  epv = {lua_number(item['epv'])},")
        out.append(f"{indent}  phase = {item['phase']},")
    if item.get("icon"):
        out.append(f"{indent}  icon = {lua_string(item['icon'])},")
    if "stats" in item:
        out.append(f"{indent}  url = {lua_string(item['url'])},")
        out.append(f"{indent}  stats = {{")
        for stat in sorted(item["stats"]):
            out.append(f"{indent}    {stat} = {lua_number(item['stats'][stat])},")
        out.append(f"{indent}  }},")
    out.append(f"{indent}}},")
    return out


def render(specs: dict[str, dict]) -> str:
    out = [HEADER, "return {", "  specs = {"]
    for name in sorted(specs):
        spec = specs[name]
        out.append(f"    [{lua_string(name.lower())}] = {{")
        out.append(f"      name = {lua_string(name)},")
        out.append(f"      tab = {lua_string(spec['tab'])},")
        out.append(f"      set5 = {lua_string(spec['set5'])},")
        out.append(f"      set6 = {lua_string(spec['set6'])},")
        out.append("      slots = {")
        for slot in sorted(spec["slots"]):
            views = spec["slots"][slot]
            # Bracketed, because a weapon key carries a colon and is not a Lua
            # identifier. Every key takes the same form so one of them cannot
            # quietly stop parsing.
            out.append(f"        [{lua_string(slot)}] = {{")
            # Written in reading order, which is the order the cards print.
            for view in ("tier6", "phase3", "tier5", "prephase") + WEAPON_VIEWS:
                held = views.get(view)
                if not held:
                    continue
                if isinstance(held, list):
                    out.append(f"          {view} = {{")
                    for item in held:
                        out.extend(render_item(item, "            "))
                    out.append("          },")
                else:
                    out.extend(render_item(held, "          ", f"{view} = {{"))
            out.append("        },")
        out.append("      },")

        # The per-spec shortlist, keyed by workbook section, best first. This
        # is what a spec page reads down, and it answers a different question
        # from the four baselines above it: not "what should this item be
        # compared against" but "what does this spec want in this slot".
        out.append("      by_slot = {")
        for section in sorted(spec["by_slot"]):
            out.append(f"        [{lua_string(section)}] = {{")
            for item in spec["by_slot"][section]:
                lines = render_item(item, "          ")
                lines.insert(-1, f"            rank = {item['rank']},")
                lines.insert(-1, f"            tier = {str(item['tier']).lower()},")
                # Collapsed arena variants carry their count so the page can
                # say so. A row standing for six items and not saying so is a
                # silent omission, which is the thing this project treats as a
                # defect rather than a tidy-up.
                if item.get("variants", 1) > 1:
                    lines.insert(-1, f"            variants = {item['variants']},")
                out.extend(lines)
            out.append("        },")
        out.append("      },")
        out.append("    },")
    out.extend(["  },", "}"])
    return "\n".join(out) + "\n"


def referenced_ids(workbook: Path, tokens: dict) -> dict[int, set[str]]:
    """Every item id this ladder names, by the acquisition route that names it.

    THE SCOPE RULE FOR items.csv, factored out here so there is one definition
    of it rather than two. An item the compendium shows is an item the item
    table should hold, and what the compendium shows in a slot is what this
    module selects: the five-deep shortlist a spec page reads down, and the
    off-piece baselines a comparison card measures against. Nothing wider,
    because the workbook lists thousands of rows a council never sees.

    Selection here reads the workbook and tokens.yaml only, never items.csv, so
    the extractor that WRITES items.csv can call this without a cycle.

    One id can arrive by more than one route across twenty-one tabs, which is
    why the value is a set. The routes are route_of's four buckets, and the
    caller writes them into the `source` column beside `raid_drop` and
    `tier_vendor`.
    """
    tier_ids = tier_item_ids(tokens)
    world_boss = world_boss_ids(WORLD_BOSSES)
    level_60 = level_60_locations(LEVEL_60)
    found: dict[int, set[str]] = {}

    def keep(rows: list[dict]) -> None:
        for row in rows:
            if row["item_id"]:
                found.setdefault(row["item_id"], set()).add(row["route"])

    for spec, (tab, _) in SPECS.items():
        path = workbook / tab
        if not path.is_file():
            raise Unreadable(
                f"extract_ladder.py: {spec} names the tab {path}, which is absent.")
        ladder = read_tab(path)
        for section in ladder:
            keep(shortlist(ladder, section, tier_ids, world_boss, level_60))
        sections = list(SECTION_TO_SLOT) + [
            name for names in WEAPON_SECTIONS.values() for name in names]
        for section in sections:
            for phases in ((3,), (1, 2)):
                keep(off_pieces(ladder, section, phases, tier_ids, world_boss, level_60))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True, help="WoWSims db.json")
    parser.add_argument("--workbook", type=Path, default=WORKBOOK)
    parser.add_argument("--tokens", type=Path, default=TOKENS)
    parser.add_argument("--items", type=Path, default=ITEMS)
    parser.add_argument(
        "--out", type=Path, default=Path("theme/filters/ladder.generated.lua"))
    args = parser.parse_args()

    if not args.db.exists():
        raise Unreadable(f"extract_ladder.py: database not found: {args.db}")
    tokens = yaml.safe_load(args.tokens.read_text())
    walked_in = entry_weapons(Path("data/facts/sim-profiles/hit-capture"))
    held, hand_of, slot_of, item_rows = {}, {}, {}, {}
    for row in csv.DictReader(args.items.open()):
        held[int(row["item_id"])] = row["name"]
        hand_of[int(row["item_id"])] = row["hand_type"]
        slot_of[int(row["item_id"])] = row["slot"]
        item_rows[int(row["item_id"])] = row
    tier_ids = tier_item_ids(tokens)
    world_boss = world_boss_ids(WORLD_BOSSES)
    level_60 = level_60_locations(LEVEL_60)

    specs: dict[str, dict] = {}
    wanted: set[int] = set()
    for spec, (tab, key) in SPECS.items():
        path = args.workbook / tab
        if not path.is_file():
            raise Unreadable(
                f"extract_ladder.py: {spec} names the tab {path}, which is absent.")
        ladder = read_tab(path)
        fifth = tier_pieces(tokens, key, 5, spec)
        sixth = tier_pieces(tokens, key, 6, spec)
        slots: dict[str, dict] = {}

        def off_piece_views(section: str, hand: str = "") -> dict[str, list[dict]]:
            views: dict[str, list[dict]] = {}
            for view, phases in (("phase3", (3,)), ("prephase", (1, 2))):
                best = [
                    dict(row) for row in off_pieces(
                        ladder, section, phases, tier_ids, world_boss, level_60,
                        hand, hand_of)]
                if best:
                    views[view] = best
                    wanted.update(row["item_id"] for row in best)
            return views

        for section, slot in SECTION_TO_SLOT.items():
            views: dict[str, dict | list[dict]] = {}
            if slot in sixth:
                views["tier6"] = dict(sixth[slot])
            if slot in fifth:
                views["tier5"] = dict(fifth[slot])
            views.update(off_piece_views(section))
            if views:
                slots[slot] = views

        # No tier view for a weapon. No Tier 4, Tier 5 or Tier 6 set holds one,
        # so a weapon card carries the two off-piece baselines and no others.
        for hand, sections in WEAPON_SECTIONS.items():
            section = next((name for name in sections if name in ladder), None)
            if section is None:
                continue
            # A WEAPON SLOT GETS THE SEVEN COMPARISONS, not the two an armor
            # slot gets. Every phase is kept, because the ruling is to compare
            # weapons inside the tier rather than to split them by phase.
            rows = [
                row for row in ladder.get(section, [])
                if row["item_id"]
                and row["item_id"] not in tier_ids
                and row["item_id"] not in world_boss
                and row["location"] not in level_60
            ]
            rows.sort(key=lambda row: row["epv"], reverse=True)
            slot_hand = "off_hand" if hand == "OffHand" else "main_hand"
            # THE CAPTURES KEY ON THE SNAKE NAME, the loop on the display
            # name. Looking up "Combat Rogue" in a table keyed by
            # "combat_rogue" silently returned nothing, so every card lost its
            # carried-into-the-tier column without any error.
            spec_key = spec.lower().replace(" ", "_")
            views = weapon_views(rows, hand, hand_of,
                                 (walked_in.get(spec_key) or {}).get(slot_hand),
                                 slot_of, item_rows)
            if views:
                for entries in views.values():
                    wanted.update(row["item_id"] for row in entries)
                slots[f"Weapon:{hand}"] = views
        # The per-spec shortlist, one entry per workbook section. Keyed by the
        # section rather than by the items.csv slot, because the sections are
        # what a spec page reads down: `Main Hand` and `Two Hand` are separate
        # questions for a warrior and `Ring` is the workbook's own word.
        by_slot: dict[str, list[dict]] = {}
        for section in ladder:
            best = shortlist(ladder, section, tier_ids, world_boss, level_60)
            if best:
                by_slot[section] = best
                wanted.update(row["item_id"] for row in best)

        specs[spec] = {
            "tab": str(path),
            "by_slot": by_slot,
            "set5": tokens["spec_to_set"][key][5],
            "set6": tokens["spec_to_set"][key][6],
            "slots": slots,
        }

    # Names and stat lines for the baselines items.csv does not hold. The name
    # always comes from a table, never from the sheet, because the sheet
    # truncates. One pass over the database serves every spec.
    outside = {item_id for item_id in wanted if item_id not in held}
    found: dict[int, dict] = {}
    if outside:
        database = json.loads(args.db.read_text())
        for item in database["items"]:
            if item["id"] in outside and item["id"] not in found:
                found[item["id"]] = item

    def hand_ok(where: str, hand: str) -> bool:
        """False where a weapon cannot go in the hand the card compares.

        Not reading the hand put four MAIN HAND weapons into the Combat Rogue
        off-hand baselines: Warglaive of Azzinoth, Vengeful Gladiator's Right
        Ripper, Dragonstrike and Talon of the Phoenix. A rogue holds none of
        those in the off hand, so two off-hand cards measured an item against
        gear the spec cannot wear there. The cause is the fallback in
        WEAPON_SECTIONS: the Rogue tab has no `Off Hand` section, so `Main Hand`
        is read, and the top of that section is main-hand only.
        """
        wanted = where.split(":")[1] if ":" in where else ""
        if not wanted or not hand:
            return True
        if wanted == "OffHand":
            return hand != "Main Hand"
        if wanted in ("MainHand", "OneHand"):
            return hand != "Off Hand"
        return True

    unnameable: list[tuple[str, str, int]] = []

    def fill(entry: dict, spec: str, where: str, check_slot: bool,
             required: bool = True) -> bool:
        """A name, and a stat line where items.csv does not hold one.

        Returns False where neither table can name the item. A COMPARISON
        BASELINE STILL FAILS THE BUILD, because a baseline with no stat line
        cannot be compared against and a card would state a difference it did
        not compute. A shortlist row is a listing rather than a comparison, so
        it is dropped and counted instead: it cannot be named, linked or given a
        tooltip, so there is nothing to show, and failing the whole compendium
        over one crafted wand the simulator database does not model would be the
        wrong trade. The count prints at every regeneration so the omission
        stays visible.
        """
        item_id = entry["item_id"]
        # THE HAND CHECK RUNS BEFORE EITHER NAMING PATH. It used to sit after
        # this early return, which meant it never ran at all for an item
        # items.csv already names, and that is almost every item. The slot check
        # below has the same history and the same excuse.
        if check_slot and not hand_ok(where, hand_of.get(item_id, "")):
            return False
        if item_id in held:
            entry["name"] = held[item_id]
            return True
        item = found.get(item_id)
        if not item:
            if not required:
                unnameable.append((spec, where, item_id))
                return False
            raise Unreadable(
                f"extract_ladder.py: an entry for {spec} in {where} is item "
                f"{item_id}, which is in neither {args.items} nor {args.db}.\n"
                "No item is named without the stat line needed to compare "
                "against it."
            )
        entry["name"] = item["name"]
        entry["url"] = f"https://www.wowhead.com/tbc/item={item_id}"
        entry["icon"] = item.get("icon", "")
        entry["stats"] = stat_line(item)
        if not check_slot:
            return True
        # THE HAND IS CHECKED, NOT ONLY THE SLOT. This used to read the slot
        # alone, on the note that the database vocabulary knows only the slot.
        # It knows the hand too, in `handType`, and not reading it put four MAIN
        # HAND weapons into the Combat Rogue off-hand baselines: Warglaive of
        # Azzinoth, Vengeful Gladiator's Right Ripper, Dragonstrike and Talon of
        # the Phoenix. A rogue cannot hold any of those in the off hand, so two
        # off-hand cards measured an item against gear the spec cannot wear
        # there. The cause is the fallback in WEAPON_SECTIONS: the Rogue tab has
        # no `Off Hand` section, so `Main Hand` is read instead, and the top of
        # that section is main-hand only.
        if not hand_ok(where, HAND_TYPE.get(item.get("handType"), "")):
            return False
        slot_named = ITEM_TYPE.get(item.get("type"), "")
        if slot_named and slot_named != where.split(":")[0]:
            # A WEAPON SECTION IS NOT ALWAYS ALL WEAPONS, and that is the
            # workbook's shape rather than a vocabulary error. The Priest Healer
            # tab files Vengeful Gladiator's Baton of Light, a wand, inside Two
            # Hand. Such a row is dropped from a weapon comparison instead of
            # stopping the build, because it is not a weapon the slot can hold.
            # An ARMOR slot mismatch is still a genuine vocabulary disagreement
            # and still fails.
            if where.startswith("Weapon:"):
                return False
            raise Unreadable(
                f"extract_ladder.py: an off-piece baseline for {spec} in "
                f"{where} is {item['name']!r}, which the database files under "
                f"{slot_named}. One of the two slot vocabularies is wrong."
            )
        return True

    for spec, block in specs.items():
        # The shortlist is not slot-checked. Its key is the workbook's own
        # section name, and the workbook files a Ring under `Ring` where the
        # database calls it a Finger, which is a difference in vocabulary and
        # not a defect.
        for section, rows in block["by_slot"].items():
            block["by_slot"][section] = [
                entry for entry in rows
                if fill(entry, spec, section, check_slot=False, required=False)]
        for slot, views in block["slots"].items():
            for view in ("phase3", "prephase") + WEAPON_VIEWS:
                # THE RETURN IS USED. This called fill and discarded the answer,
                # so a baseline the hand check rejects stayed on the card.
                views[view] = [entry for entry in views.get(view, [])
                               if fill(entry, spec, slot, check_slot=True)]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(specs))
    slots = sum(len(block["slots"]) for block in specs.values())
    print(f"{len(specs)} spec(s), {slots} slot(s) -> {args.out}")
    print(f"  {len(outside)} baseline(s) outside {args.items}, "
          f"stat line carried from {args.db.name}")
    if unnameable:
        print(f"  {len(unnameable)} shortlist row(s) dropped, named by neither "
              f"{args.items} nor {args.db.name}:")
        for spec, where, item_id in unnameable:
            print(f"    {spec} {where}, item {item_id}")
    # The gated count is printed at every regeneration, because it is the figure
    # that says how many cards compare against something a raider cannot obtain.
    routes: dict[str, int] = {}
    for block in specs.values():
        for views in block["slots"].values():
            for view in ("phase3", "prephase"):
                best = views.get(view)
                if best:
                    route = best[0]["route"]
                    routes[route] = routes.get(route, 0) + 1
    summary = ", ".join(f"{routes[r]} {r}" for r in sorted(routes))
    print(f"  leading off-piece baselines by acquisition route: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
