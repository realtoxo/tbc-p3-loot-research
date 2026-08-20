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

# ONE ENTRY PER SPEC THAT RUNS A WEAPON PAIR ROUND. `pairs` is every
# combination the round measures, `phase3` marks one the entry anchor cannot
# reach, and `why` is the paragraph the anchor pages print above the table,
# so the reasoning lives beside the list it explains.
#
# A COMBINATION IS A ROW SHAPED BY ITS SPEC'S STYLES, ruled in
# data/judgments/weapon-styles.yaml: `oh: null` is a two-hander row and the
# off hand runs EMPTY; `mh` with `oh` is a pair. A spec whose styles allow
# both puts both in the SAME table, per the guild lead. `pair_speed` is
# optional and Enhancement's alone, per its matched-speed rule. A spec with
# more profiles than the standard three, which today is the two Warglaive
# specs and their bis_no_glaives, lists its anchors under `anchors`.
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
    # RETRIBUTION: two-handers only, per the 20 August 2026 ruling. The
    # candidates are the top of the workbook's Two Hand ladder for this spec,
    # filtered to weapon classes a paladin wields: swords, maces, axes and
    # polearms, never a staff or a fist weapon. Every row runs the off hand
    # EMPTY. The two worn weapons are rows on purpose: their variants must
    # reproduce the anchor figures to the digit, which is the same
    # verification the Enhancement round carries.
    "retribution_paladin": {
        "why": (
            "A Retribution Paladin always carries a two-hander, per the 20 "
            "August 2026 ruling in data/judgments/weapon-styles.yaml, so "
            "every row below is a single weapon and the off hand runs "
            "empty. Each row is THIS PROFILE with only the main hand id "
            "replaced: the slot keeps its Mongoose, and the consumables, "
            "buffs and seed hold still, so every figure is directly "
            "comparable with the one at the top of this page. The "
            "candidates are the top of the EP Workbook's Two Hand ladder "
            "for this spec, kept to the weapon classes a paladin wields. "
            "Cataclysm's Edge appears as a measurement only: the guild "
            "lead routed it to the Arms Warrior and kept Torch of the "
            "Damned with this spec, per "
            "data/judgments/weapon-routing.yaml."),
        "pairs": [
            # Phase 3 raid drops: Torch of the Damned from the Reliquary
            # of Souls is the worn best-in-slot weapon and the workbook's
            # rank one; Cataclysm's Edge from Archimonde is routed to the
            # Arms Warrior; Soul Cleaver from Teron Gorefiend and the
            # Halberd of Desolation from High Warlord Naj'entus are the
            # other Black Temple two-handers on the ladder.
            {"mh": 32332, "oh": None, "phase3": True},
            {"mh": 30902, "oh": None, "phase3": True},
            {"mh": 32348, "oh": None, "phase3": True},
            {"mh": 32248, "oh": None, "phase3": True},
            # Season 3 arena, sold for points once the season runs.
            {"mh": 33663, "oh": None, "phase3": True},
            # Reachable before Phase 3: Lionheart Executioner is the worn
            # entry and tier weapon, crafted by Blacksmithing; Twinblade
            # of the Phoenix drops from Kael'thas Sunstrider; the
            # Merciless Gladiator's Bonegrinder is Season 2 arena.
            {"mh": 28430, "oh": None, "phase3": False},
            {"mh": 29993, "oh": None, "phase3": False},
            {"mh": 31959, "oh": None, "phase3": False},
        ],
    },
    # FURY: one-handers and main handers only, per the 20 August 2026 ruling
    # in data/judgments/weapon-styles.yaml, so every row is a main hand with
    # an off hand and no row is a two-hander. The candidates are the top of
    # the Fury workbook tab, which splits Main Hand from Off Hand unlike the
    # Enhancement tab's combined pool, kept to the weapon classes a warrior
    # dual-wields: swords, maces, axes and fist weapons. A Main Hand item
    # fits only the main hand, an Off Hand item only the off hand, and a One
    # Hand item fits either. Fury carries FOUR anchors, because the
    # Warglaives of Azzinoth are ranked first by this spec's published list
    # AND the Combat Rogue's, the raid holds one pair, and the guild lead
    # has not routed it, so a with-Warglaives and a without-Warglaives
    # best-in-slot set both exist. Each anchor's worn pair is a row on
    # purpose: its variant must reproduce the anchor figure to the digit,
    # the same verification the other rounds carry. No candidate in this
    # list carries a socket, so no figure here is understated against a
    # gemmed worn weapon.
    "fury_warrior": {
        "anchors": ("entry", "tier-hands-and-head", "bis",
                    "bis-no-glaives"),
        "why": (
            "A Fury Warrior considers only one-handers and main handers, "
            "per the 20 August 2026 ruling in "
            "data/judgments/weapon-styles.yaml, so every row below is a "
            "main hand with an off hand and no row is a two-hander. Each "
            "row is THIS PROFILE with only the two weapon ids replaced: "
            "each slot keeps its Mongoose, and the consumables, buffs and "
            "seed hold still, so every figure is directly comparable with "
            "the one at the top of this page. The candidates are the top "
            "of the EP Workbook's Main Hand and Off Hand ladders for this "
            "spec, kept to the weapon classes a warrior dual-wields. A "
            "row of two copies of one item needs both copies before it is "
            "wearable. The Warglaives of Azzinoth are ranked first by "
            "this spec's published Phase 3 list and by the Combat "
            "Rogue's, the raid holds one pair, and which of the two "
            "receives it is open council business, per "
            "data/judgments/weapon-routing.yaml, which is why this spec "
            "carries a best-in-slot set both with and without them."),
        "pairs": [
            # Phase 3 raid drops and Season 3 arena. The Warglaive pair,
            # from Illidan Stormrage, is the worn best-in-slot pair and
            # the workbook's rank one in both hands; the Vengeful
            # Gladiator's Slicer with the Chopper is the worn
            # bis-no-glaives pair, per the capture in
            # data/facts/sim-profiles/bis-capture/fury-warrior.yaml.
            {"mh": 32837, "oh": 32838, "phase3": True},
            {"mh": 33762, "oh": 34015, "phase3": True},
            # Two Slicers, the doubled-arena alternative the capture
            # measured bare at 2609.9; the Right Ripper is the Season 3
            # fist main hand, Main Hand only, with the Chopper behind it.
            {"mh": 33762, "oh": 33762, "phase3": True},
            {"mh": 33737, "oh": 34015, "phase3": True},
            # The raid-drop field: Syphon of the Nathrezim from Supremus
            # is the workbook's rank two main hand and its rank one off
            # hand, Blade of Infamy from Anetheron is the highest Hyjal
            # one-hander, and neither is unique, so the doubled rows are
            # a question of weeks rather than of possibility. Claw of
            # Molten Fury drops from Hyjal Summit trash.
            {"mh": 32262, "oh": 32262, "phase3": True},
            {"mh": 32262, "oh": 30881, "phase3": True},
            {"mh": 30881, "oh": 30881, "phase3": True},
            {"mh": 30881, "oh": 30082, "phase3": True},
            {"mh": 32946, "oh": 30082, "phase3": True},
            # Reachable before Phase 3: Dragonstrike, crafted by
            # Blacksmithing, with Talon of Azshara from Morogrim
            # Tidewalker is the worn entry AND tier pair; Rod of the Sun
            # King drops from Kael'thas Sunstrider and Talon of the
            # Phoenix from Al'ar, both Tempest Keep.
            {"mh": 28439, "oh": 30082, "phase3": False},
            {"mh": 28439, "oh": 29996, "phase3": False},
            {"mh": 32944, "oh": 30082, "phase3": False},
        ],
    },
    # COMBAT ROGUE: dual wield only, per the 20 August 2026 ruling in
    # data/judgments/weapon-styles.yaml. The build is Combat Swords, 20/41/0
    # as the guide labels it and 19/42/0 as its calculator string sums, per
    # data/facts/talents.yaml, and its combat segment decodes to Sword
    # Specialization 5/5; the rotation is the simulator's swords APL, built
    # on Sinister Strike. A dagger main hand changes the rotation entirely,
    # so no dagger is a row. The fist and mace rows are measured with the
    # caveat the why paragraph states: Sword Specialization does not benefit
    # them. The candidates are the top of the Rogue workbook tab, which
    # splits Main Hand from Off Hand like the Fury tab and unlike the
    # Enhancement tab's combined pool. Combat carries FOUR anchors for the
    # same reason Fury does: the Warglaives of Azzinoth are ranked first by
    # both specs' published lists, the raid holds one pair, and the guild
    # lead has not routed it. Each anchor's worn pair is a row on purpose:
    # its variant must reproduce the anchor figure to the digit, the same
    # verification the other rounds carry. No candidate in this list
    # carries a socket, so no figure here is understated against a gemmed
    # worn weapon.
    "combat_rogue": {
        "anchors": ("entry", "tier-hands-and-head", "bis",
                    "bis-no-glaives"),
        "why": (
            "A Combat Rogue carries two one-handers, per the 20 August "
            "2026 ruling in data/judgments/weapon-styles.yaml, so every "
            "row below is a main hand with an off hand and no row is a "
            "two-hander. Each row is THIS PROFILE with only the two "
            "weapon ids replaced: each slot keeps its Mongoose, and the "
            "consumables, buffs and seed hold still, so every figure is "
            "directly comparable with the one at the top of this page. "
            "The build is Combat Swords and the rotation is built on "
            "Sinister Strike, so no dagger is a row, because a dagger "
            "main hand changes the rotation entirely rather than the "
            "weapon alone, and the fist and mace rows carry a stated "
            "caveat: the build's Sword Specialization talent procs only "
            "on sword strikes and does not benefit them. The candidates "
            "are the top of the EP Workbook's Main Hand and Off Hand "
            "ladders for this spec. A row of two copies of one item "
            "needs both copies before it is wearable. The Warglaives of "
            "Azzinoth are ranked first by this spec's published Phase 3 "
            "list and by the Fury Warrior's, the raid holds one pair, "
            "and which of the two receives it is open council business, "
            "per data/judgments/weapon-routing.yaml, which is why this "
            "spec carries a best-in-slot set both with and without "
            "them."),
        "pairs": [
            # Phase 3 raid drops and Season 3 arena. The Warglaive pair,
            # from Illidan Stormrage, is the worn best-in-slot pair and
            # the workbook's rank one in both hands; the Vengeful
            # Gladiator's Slicer with Blade of Savagery, from Mother
            # Shahraz, is the worn bis-no-glaives pair, per the capture
            # in data/facts/sim-profiles/bis-capture/combat-rogue.yaml.
            {"mh": 32837, "oh": 32838, "phase3": True},
            {"mh": 33762, "oh": 32369, "phase3": True},
            # The sword field: Blade of Infamy from Anetheron is the
            # highest Hyjal one-hander on the tab and is not unique, so
            # its doubled row is a question of weeks; the Vengeful
            # Gladiator's Quickblade is the Season 3 Off Hand sword and
            # two Slicers is the doubled-arena alternative the Fury
            # round also measures.
            {"mh": 30881, "oh": 32369, "phase3": True},
            {"mh": 33762, "oh": 33734, "phase3": True},
            {"mh": 30881, "oh": 33734, "phase3": True},
            {"mh": 33762, "oh": 33762, "phase3": True},
            {"mh": 30881, "oh": 30881, "phase3": True},
            # Off-class rows, measured under the stated caveat that
            # Sword Specialization does not benefit them: Swiftsteel
            # Bludgeon, from Black Temple trash, is the workbook's rank
            # two off hand, and the Season 3 fist pair is the Right
            # Ripper, Main Hand only, with the Left Ripper, Off Hand
            # only.
            {"mh": 30881, "oh": 32943, "phase3": True},
            {"mh": 33737, "oh": 33705, "phase3": True},
            # Reachable before Phase 3: Talon of Azshara from Morogrim
            # Tidewalker with the Merciless Gladiator's Quickblade,
            # Season 2 arena, is the worn entry AND tier pair, per the
            # capture in data/facts/sim-profiles/hit-capture/
            # combat-rogue.yaml; the Merciless Gladiator's Slicer is the
            # Season 2 One Hand sword above it on the tab.
            {"mh": 30082, "oh": 32027, "phase3": False},
            {"mh": 32052, "oh": 32027, "phase3": False},
            {"mh": 30082, "oh": 32052, "phase3": False},
        ],
    },
    # ARMS: two-handers only, per the 20 August 2026 ruling. The published
    # Phase 3 page ranks only dual Warglaives, which the guild lead routed
    # away from this spec, and the workbook tab's two-hand table is headed
    # PHASE 2, so the Phase 3 field is read from items.csv instead: every
    # Mount Hyjal, Black Temple or Season 3 two-hander a warrior wields,
    # which is swords, maces, axes and polearms, never a staff. The
    # pre-Phase 3 rows are the top of the Arms workbook tab's Two Hand
    # ladder. The worn weapons are rows on purpose: their variants must
    # reproduce the anchor figures to the digit, the same verification the
    # other rounds carry, and the entry and tier anchors wear a socketed
    # Twinblade whose gems with_pair keeps for that row alone.
    "arms_warrior": {
        "why": (
            "An Arms Warrior considers only two-handers, per the 20 August "
            "2026 ruling in data/judgments/weapon-styles.yaml, so every row "
            "below is a single weapon and the off hand runs empty. Each row "
            "is THIS PROFILE with only the main hand id replaced: the slot "
            "keeps its Mongoose, and the consumables, buffs and seed hold "
            "still, so every figure is directly comparable with the one at "
            "the top of this page. The published Phase 3 page ranks only "
            "dual Warglaives, which the guild lead routed away from this "
            "spec, so the Phase 3 candidates are the drop table's "
            "two-handers in the weapon classes a warrior wields, and the "
            "earlier candidates are the top of the EP Workbook's Two Hand "
            "ladder for this spec. The guild lead ruled that this spec "
            "takes Cataclysm's Edge. Torch of the Damned appears as a "
            "measurement only: the guild lead kept it with the Retribution "
            "Paladin, per data/judgments/weapon-routing.yaml."),
        "pairs": [
            # Phase 3 raid drops: Cataclysm's Edge from Archimonde is the
            # worn best-in-slot weapon, the workbook's rank one and the
            # guild lead's routing; Torch of the Damned from the Reliquary
            # of Souls is measured as informative and routed to the
            # Retribution Paladin; Soul Cleaver from Teron Gorefiend and
            # the Halberd of Desolation from High Warlord Naj'entus are
            # the other Black Temple two-handers on the ladder.
            {"mh": 30902, "oh": None, "phase3": True},
            {"mh": 32332, "oh": None, "phase3": True},
            {"mh": 32348, "oh": None, "phase3": True},
            {"mh": 32248, "oh": None, "phase3": True},
            # Season 3 arena, sold for points once the season runs. The
            # workbook ranks the Bonegrinder, the Greatsword and the
            # Decapitator within five DPS of one another, so the
            # Bonegrinder stands for all three.
            {"mh": 33663, "oh": None, "phase3": True},
            # Reachable before Phase 3: Twinblade of the Phoenix, from
            # Kael'thas Sunstrider, is the worn entry and tier weapon;
            # Lionheart Executioner is crafted by Blacksmithing; the
            # Merciless Gladiator's Bonegrinder is Season 2 arena.
            {"mh": 29993, "oh": None, "phase3": False},
            {"mh": 28430, "oh": None, "phase3": False},
            {"mh": 31959, "oh": None, "phase3": False},
        ],
    },
}


def with_pair(gear: dict, mh: int, oh: int | None) -> dict:
    """The gear wearing one candidate combination, slots keeping enchants.

    THE GEMS GO WITH THE OLD ITEM and the enchant stays with the slot. A
    candidate arrives ungemmed, and a weapon slot wears the same enchant at
    every anchor, so keeping the slot's enchant is what a raider would do
    rather than a modelling shortcut. THE ONE EXCEPTION IS THE WORN ITEM
    ITSELF: where the candidate id equals the id already in the slot, the
    slot keeps its gems, because that row exists to reproduce the anchor
    figure to the digit, and the Arms entry and tier anchors wear a socketed
    Twinblade of the Phoenix whose three gems are part of the anchor.

    AN `oh` OF None EMPTIES THE OFF HAND, enchant and all, which is what a
    two-hander row needs: the item it displaces cannot stay, and neither can
    the enchant that belonged to it.
    """
    out = {"items": [dict(entry) for entry in gear["items"]]}
    mh_index = SLOT_ORDER.index("main_hand")
    entry = dict(out["items"][mh_index])
    if entry.get("id") != mh:
        entry.pop("gems", None)
    entry["id"] = mh
    out["items"][mh_index] = entry
    oh_index = SLOT_ORDER.index("off_hand")
    if oh is None:
        out["items"][oh_index] = {}
    else:
        entry = dict(out["items"][oh_index]) or {}
        if entry.get("id") != oh:
            entry.pop("gems", None)
        entry["id"] = oh
        out["items"][oh_index] = entry
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
    ap.add_argument("--spec", action="append", default=None,
                    help="Run only this spec's round, repeatable. The other "
                         "specs' recorded figures are carried forward from "
                         "the existing output file unchanged, so one spec "
                         "can land without rerunning every other round.")
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

    rounds = ROUNDS
    carried: dict[str, dict] = {}
    if args.spec:
        unknown = [s for s in args.spec if s not in ROUNDS]
        if unknown:
            print(f"error: not in the registry: {', '.join(unknown)}. "
                  f"Registered: {', '.join(ROUNDS)}", file=sys.stderr)
            return 1
        rounds = {s: ROUNDS[s] for s in args.spec}
        # THE OTHER SPECS ARE CARRIED, NOT DROPPED. A partial run that wrote
        # only its own spec would delete every other round from the file,
        # which is the sim-figures hand-merge trap all over again.
        if args.out.is_file():
            carried = (yaml.safe_load(args.out.read_text())
                       or {}).get("specs") or {}
            carried = {s: block for s, block in carried.items()
                       if s not in rounds}

    specs_out: dict[str, dict] = dict(carried)
    total = 0
    for spec, round_ in rounds.items():
        talents = (strings.get(spec) or {}).get("string")
        stem = spec.replace("_", "-")
        anchors: dict[str, list[dict]] = {}
        for anchor in round_.get("anchors", ANCHORS):
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
                oh = pair.get("oh")
                label = names.get(pair["mh"], str(pair["mh"])) + (
                    f" + {names.get(oh, oh)}" if oh else ", two-hander")
                dps, stdev, error = run(args.cli, build_request(
                    spec, with_pair(gear, pair["mh"], oh), talents,
                    args.iterations, args.seed, buffs, party_of,
                    anchor.replace("-", "_"), args.seconds, args.armor))
                if error:
                    raise SystemExit(f"run_weapon_pair_sims.py: {spec}: "
                                     f"{anchor}: {label}: {error}")
                entry = {"main_hand": weapon(pair["mh"])}
                if oh:
                    entry["off_hand"] = weapon(oh)
                if pair.get("speed") is not None:
                    entry["pair_speed"] = pair["speed"]
                entry.update({
                    "dps": round(dps, 1),
                    "standard_error": round(
                        stdev / math.sqrt(args.iterations), 2),
                    "stdev": round(stdev, 1),
                })
                results.append(entry)
                total += 1
                print(f"  {spec:22s} {anchor:20s} {label:56s} {dps:9.1f}")
            results.sort(key=lambda row: -row["dps"])
            anchors[anchor] = results
        specs_out[spec] = {"why": round_["why"], "anchors": anchors}

    document = {
        "meta": {
            "what": (
                "Weapon rounds, one per spec in the registry of "
                "tools/run_weapon_pair_sims.py, each combination run as a "
                "VARIANT of that spec's anchor profiles: the exported gear "
                "with only the weapon slots changed, a filled slot keeping "
                "its enchant and a two-hander row running the off hand "
                "EMPTY, the anchor's own consumables, buffs and seed held "
                "still. Which styles each spec's table holds is ruled in "
                "data/judgments/weapon-styles.yaml, and the Enhancement "
                "round is further ruled in "
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
