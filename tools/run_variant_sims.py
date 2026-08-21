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
August 2026 ruling. The rows are ENUMERATED from each spec's weapon field,
ruled by the guild lead on 20 August 2026, and are facts, not a ranking;
which pair each anchor wears is the council's call.

Writes data/facts/variant-sims.yaml and nothing else. The pages that
show these figures are written by tools/generate_sim_pages.py, the same
generator that owns every other sim page. Runs the simulator, so it runs
inside `just sim` and `just sim-weapons` and outside `just regen` and
`just check`.

Usage:
    python3 tools/run_variant_sims.py --iterations 10000
"""

from __future__ import annotations

import argparse
import itertools
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

OUT = Path("data/facts/variant-sims.yaml")

# The anchors the variants run on, as the gear stems and page slugs spell
# them. Hyphens, because that is the naming scheme of data/sim/gear and of
# the page slugs in generate_sim_pages.py; the consumable key converts back
# to underscores inside build_request's caller.
ANCHORS = ("entry", "tier-hands-and-head", "bis")

# ONE ENTRY PER SPEC THAT RUNS A WEAPON ROUND. THE ROUNDS ARE ENUMERATIVE,
# ruled by the guild lead on 20 August 2026, "lets make our weapon rounds
# enumerative": each spec carries a `weapon_field`, a candidate FIELD the
# runner enumerates under the spec's ruled styles, rather than a
# hand-curated pair list. The field is derived, and re-derivable for
# review, by tools/derive_weapon_fields.py: the union of the spec's ladder
# shortlist sections, every weapon its anchors wear, and every weapon a
# standing ruling routes for it, because a routing never excludes a
# candidate. `phase3` marks a candidate the entry anchor cannot reach, and
# `why` is the paragraph the anchor pages print above the table.
#
# GENERATION, in enumerate_pairs below, is shaped by the spec's styles,
# ruled in data/judgments/weapon-styles.yaml. Style two_hand runs each
# two-hander alone with the off hand EMPTY. Styles dual_wield and
# main_hand_off_hand run every ORDERED main-hand and off-hand pairing:
# where both items are One Hand weapons they sit in both lists and BOTH
# orders run, because the off-hand swing penalty makes the order a real
# question, and a pair of two copies of one id runs ONCE and arises only
# for a One Hand weapon, the doubled precedent. `matched_speed` is
# Enhancement's alone, per data/judgments/enhancement-weapon-rules.yaml:
# only pairs whose two speeds are EQUAL run, and each row carries
# `pair_speed`. A spec with more profiles than the standard three, which
# today is the two Warglaive specs and their bis_no_glaives, lists its
# anchors under `anchors`. A spec entry that still carried a hand-curated
# `pairs` list would run it unchanged, but every spec now carries a field.
ROUNDS: dict[str, dict] = {
    "enhancement_shaman": {
        "why": (
            (
            "An Enhancement Shaman carries a Windfury imbue in each "
            "hand, pairs two weapons of the same speed, and wants them "
            "slow. The set above wears the pair its published source "
            "ranked, so each row below is THIS PROFILE with only the "
            "two weapon ids replaced: the slot keeps its Mongoose. "
            "The table is an enumeration: every matched-speed "
            "pairing the slow one-hand field supports, and the field is "
            "the spec's shortlist together with every weapon an anchor "
            "wears. The character is a Draenei, so no row inherits "
            "the Orc axe privilege the published lists assume. The "
            "weapons run unsynced.")),
        # enhancement_shaman: derived by tools/derive_weapon_fields.py
        "weapon_field": {
            "styles": ["dual_wield"],
            "matched_speed": True,
            "two_hand": [],
            "main_hand": [
                {"id": 28305, "phase3": False},   # Gladiator's Pummeler
                {"id": 28313, "phase3": False},   # Gladiator's Right Ripper
                {"id": 28431, "phase3": False},   # The Planar Edge
                {"id": 28432, "phase3": False},   # Black Planar Edge
                {"id": 28433, "phase3": False},   # Wicked Edge of the Planes
                {"id": 28437, "phase3": False},   # Drakefist Hammer
                {"id": 28438, "phase3": False},   # Dragonmaw
                {"id": 28439, "phase3": False},   # Dragonstrike
                {"id": 28584, "phase3": False},   # Big Bad Wolf's Paw
                {"id": 28657, "phase3": False},   # Fool's Bane
                {"id": 28767, "phase3": False},   # The Decapitator
                {"id": 29924, "phase3": False},   # Netherbane
                {"id": 29996, "phase3": False},   # Rod of the Sun King
                {"id": 32028, "phase3": False},   # Merciless Gladiator's Right Ripper
                {"id": 32236, "phase3": True},   # Rising Tide
                {"id": 32262, "phase3": True},   # Syphon of the Nathrezim
                {"id": 32944, "phase3": False},   # Talon of the Phoenix
                {"id": 32946, "phase3": True},   # Claw of Molten Fury
                {"id": 33669, "phase3": True},   # Vengeful Gladiator's Cleaver
                {"id": 33737, "phase3": True},   # Vengeful Gladiator's Right Ripper
            ],
            "off_hand": [
                {"id": 28305, "phase3": False},   # Gladiator's Pummeler
                {"id": 29924, "phase3": False},   # Netherbane
                {"id": 29996, "phase3": False},   # Rod of the Sun King
                {"id": 32236, "phase3": True},   # Rising Tide
                {"id": 32262, "phase3": True},   # Syphon of the Nathrezim
                {"id": 33669, "phase3": True},   # Vengeful Gladiator's Cleaver
            ],
        },
        # THE TRINKET POOL, the fifth enumerative trinket round after the
        # Combat Rogue pilot and the Retribution, Arms and Fury rounds:
        # every max-level trinket the Enh tab's Trinket ladder ranks, with
        # anything from Karazhan and the badge vendor onward acceptable,
        # and the runner generates every unordered pair itself. The ladder
        # ranks fifteen; eight are out on the standing exclusions, all
        # availability rather than routing: Mark of the Champion, Slayer's
        # Crest, Drake Fang Talisman and Kiss of the Spider drop in
        # level-60 raids; the Abacus of Violent Odds, the Hourglass of the
        # Unraveller and the Icon of Unyielding Courage drop in five-man
        # dungeons below Karazhan; and the Empty Mug of Direbrew drops
        # from a holiday boss inside Blackrock Depths, a level-60
        # five-man. Core of Ar'kelos stays in as a max-level Netherstorm
        # quest reward, per the Retribution precedent. No Ahn'Qiraj and no
        # world-boss trinket is on the tab, and no totem or relic strays
        # into its Trinket section. The Ashtongue Talisman of Vision, the
        # tab's rank five, stays in as this spec's shaman-only Ashtongue
        # Deathsworn Exalted reward; it carries no worn stats per
        # items.csv, so everything its rows measure is the simulator's
        # pricing of its procs, and the VENDORED BINARY DOES price them:
        # a diagnostic run on 20 August 2026 read Dragonspine beside it
        # 57.6 above Dragonspine beside an EMPTY slot at best in slot.
        # The recovered source checkout marks id 32491 an unimplemented
        # TODO, so that checkout is stale against the binary and is not
        # evidence about what the binary implements. The entry
        # and tier anchors wear Dragonspine Trophy with Bloodlust Brooch
        # and the best-in-slot anchor wears Dragonspine Trophy with
        # Madness of the Betrayer, all three in the pool, so no worn item
        # needed adding. `phase3` marks what the entry anchor cannot
        # reach: Madness of the Betrayer is a Black Temple drop and the
        # Ashtongue Talisman of Vision is Ashtongue Deathsworn Exalted, a
        # reputation earned in Black Temple and Mount Hyjal.
        "trinket_pool": [
            {"id": 28830, "phase3": False},  # Dragonspine Trophy
            {"id": 32505, "phase3": True},   # Madness of the Betrayer
            {"id": 31856, "phase3": False},  # Darkmoon Card: Crusade
            {"id": 32491, "phase3": True},   # Ashtongue Tal. of Vision
            {"id": 30627, "phase3": False},  # Tsunami Talisman
            {"id": 29383, "phase3": False},  # Bloodlust Brooch
            {"id": 29776, "phase3": False},  # Core of Ar'kelos
        ],
        "trinkets_why": (
            (
            "The candidates are every max-level trinket on the EP "
            "Workbook's Trinket ladder for this spec, from Gruul's "
            "Lair, the raids above it, the badge vendor, the Darkmoon "
            "Faire, one max-level quest and one reputation, and every "
            "pair from that pool was measured, so the table is an "
            "enumeration rather than a selection. The "
            "Ashtongue Talisman of Vision carries no worn statistics, "
            "so everything its rows measure is the simulator's pricing "
            "of its procs.")),
    },
    # RETRIBUTION: two-handers only, per the 20 August 2026 ruling. The
    # field is the workbook's Two Hand ladder for this spec plus every worn
    # weapon, kept to weapon classes a paladin wields: swords, maces, axes
    # and polearms, never a staff or a fist weapon. Every row runs the off
    # hand EMPTY. The two worn weapons are rows on purpose: their variants must
    # reproduce the anchor figures to the digit, which is the same
    # verification the Enhancement round carries.
    "retribution_paladin": {
        "why": (
            (
            "A Retribution Paladin always carries a two-hander, so "
            "every row below is a single weapon and the off hand runs "
            "empty. Each row is THIS PROFILE with only the main hand id "
            "replaced: the slot keeps its Mongoose. "
            "The table is an enumeration of the EP Workbook's Two Hand "
            "ladder for this spec together with every worn and routed "
            "weapon, kept to the weapon classes a paladin "
            "wields. Cataclysm's Edge appears as a measurement only: it "
            "goes to the Arms Warrior, and Torch of the Damned stays "
            "with this spec.")),
        # retribution_paladin: derived by tools/derive_weapon_fields.py
        "weapon_field": {
            "styles": ["two_hand"],
            "two_hand": [
                {"id": 24550, "phase3": False},   # Gladiator's Greatsword
                {"id": 28298, "phase3": False},   # Gladiator's Decapitator
                {"id": 28300, "phase3": False},   # Gladiator's Painsaw
                {"id": 28428, "phase3": False},   # Lionheart Blade
                {"id": 28429, "phase3": False},   # Lionheart Champion
                {"id": 28430, "phase3": False},   # Lionheart Executioner
                {"id": 28435, "phase3": False},   # Mooncleaver
                {"id": 28436, "phase3": False},   # Bloodmoon
                {"id": 28441, "phase3": False},   # Deep Thunder
                {"id": 28442, "phase3": False},   # Stormherald
                {"id": 28773, "phase3": False},   # Gorehowl
                {"id": 28800, "phase3": False},   # Hammer of the Naaru
                {"id": 29993, "phase3": False},   # Twinblade of the Phoenix
                {"id": 30090, "phase3": False},   # World Breaker
                {"id": 30902, "phase3": True},   # Cataclysm's Edge
                {"id": 31959, "phase3": False},   # Merciless Gladiator's Bonegrinder
                {"id": 31966, "phase3": False},   # Merciless Gladiator's Decapitator
                {"id": 32025, "phase3": False},   # Merciless Gladiator's Painsaw
                {"id": 32248, "phase3": True},   # Halberd of Desolation
                {"id": 32332, "phase3": True},   # Torch of the Damned
                {"id": 32348, "phase3": True},   # Soul Cleaver
                {"id": 33663, "phase3": True},   # Vengeful Gladiator's Bonegrinder
                {"id": 33670, "phase3": True},   # Vengeful Gladiator's Decapitator
                {"id": 33727, "phase3": True},   # Vengeful Gladiator's Painsaw
            ],
            "main_hand": [],
            "off_hand": [],
        },
        # THE TRINKET POOL, the second enumerative trinket round after the
        # Combat Rogue pilot: every max-level trinket the Ret tab's Trinket
        # ladder ranks, with anything from Karazhan and the badge vendor
        # onward acceptable, and the runner generates every unordered pair
        # itself. The ladder ranks fifteen; nine are out on the standing
        # exclusions, all availability rather than routing: Mark of the
        # Champion, Slayer's Crest, Kiss of the Spider and Drake Fang
        # Talisman drop in level-60 raids; the Abacus of Violent Odds and
        # the Hourglass of the Unraveller drop in five-man dungeons below
        # Karazhan; the Empty Mug of Direbrew drops from a holiday boss
        # inside Blackrock Depths, a level-60 five-man; and Bladefist's
        # Breadth and the Ancient Draenei War Talisman are leveling quest
        # rewards, not max-level items. Core of Ar'kelos stays in as a
        # max-level Netherstorm quest reward. No Ahn'Qiraj and no
        # world-boss trinket is on the tab. The entry and tier anchors
        # wear Dragonspine Trophy with Darkmoon Card: Crusade and the
        # best-in-slot anchor wears Dragonspine Trophy with Bloodlust
        # Brooch, all three in the pool, so no worn item needed adding.
        # `phase3` marks what the entry anchor cannot reach: Madness of
        # the Betrayer is a Black Temple drop.
        "trinket_pool": [
            {"id": 28830, "phase3": False},  # Dragonspine Trophy
            {"id": 31856, "phase3": False},  # Darkmoon Card: Crusade
            {"id": 32505, "phase3": True},   # Madness of the Betrayer
            {"id": 30627, "phase3": False},  # Tsunami Talisman
            {"id": 29383, "phase3": False},  # Bloodlust Brooch
            {"id": 29776, "phase3": False},  # Core of Ar'kelos
            # The class talisman from the Ashtongue Deathsworn, a
            # reputation purchase contesting nothing, in the pool by
            # ruling even where the ladder is silent.
            {"id": 32489, "phase3": True},   # Ashtongue Tal. of Zeal
        ],
        "trinkets_why": (
            (
            "The candidates are every max-level trinket on the EP "
            "Workbook's Trinket ladder for this spec, from Karazhan, "
            "the raids above it, the badge vendor and one max-level "
            "quest, and every pair from that pool was measured, so the "
            "table is an enumeration rather than a selection.")),
    },
    # FURY: one-handers and main handers only, per the 20 August 2026 ruling
    # in data/judgments/weapon-styles.yaml, so every row is a main hand with
    # an off hand and no row is a two-hander. The field is the Fury tab's
    # Main Hand and Off Hand ladders, which the tab splits unlike the
    # Enhancement tab's combined pool, plus every worn and routed weapon,
    # kept to the weapon classes a warrior
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
            (
            "A Fury Warrior considers only one-handers and main "
            "handers, so every row below is a main hand with an off "
            "hand and no row is a two-hander. Each row is THIS PROFILE "
            "with only the two weapon ids replaced: each slot keeps its "
            "Mongoose. The table is an enumeration of the EP "
            "Workbook's Main Hand and Off Hand ladders for this spec "
            "together with every worn and routed weapon, kept to the "
            "weapon classes a warrior dual-wields, and every ordered "
            "pairing the field supports is a row. A row of "
            "two copies of one item needs both copies before it is "
            "wearable. The Warglaives of Azzinoth are ranked first by "
            "this spec's published Phase 3 list and by the Combat "
            "Rogue's, the raid holds one pair, and which of the two "
            "receives it is open council business, which is why this "
            "spec carries a best-in-slot set both with and without "
            "them.")),
        # fury_warrior: derived by tools/derive_weapon_fields.py
        "weapon_field": {
            "styles": ["dual_wield"],
            "two_hand": [],
            "main_hand": [
                {"id": 23544, "phase3": False},   # Runic Hammer
                {"id": 27872, "phase3": False},   # The Harvester of Souls
                {"id": 28210, "phase3": False},   # Bloodskull Destroyer
                {"id": 28267, "phase3": False},   # Edge of the Cosmos
                {"id": 28295, "phase3": False},   # Gladiator's Slicer
                {"id": 28313, "phase3": False},   # Gladiator's Right Ripper
                {"id": 28432, "phase3": False},   # Black Planar Edge
                {"id": 28433, "phase3": False},   # Wicked Edge of the Planes
                {"id": 28438, "phase3": False},   # Dragonmaw
                {"id": 28439, "phase3": False},   # Dragonstrike
                {"id": 28729, "phase3": False},   # Spiteblade
                {"id": 28767, "phase3": False},   # The Decapitator
                {"id": 29124, "phase3": False},   # Vindicator's Brand
                {"id": 29924, "phase3": False},   # Netherbane
                {"id": 29996, "phase3": False},   # Rod of the Sun King
                {"id": 30082, "phase3": False},   # Talon of Azshara
                {"id": 30788, "phase3": False},   # Illidari-Bane Broadsword
                {"id": 30881, "phase3": True},   # Blade of Infamy
                {"id": 31332, "phase3": False},   # Blinkstrike
                {"id": 31965, "phase3": False},   # Merciless Gladiator's Cleaver
                {"id": 32028, "phase3": False},   # Merciless Gladiator's Right Ripper
                {"id": 32052, "phase3": False},   # Merciless Gladiator's Slicer
                {"id": 32236, "phase3": True},   # Rising Tide
                {"id": 32262, "phase3": True},   # Syphon of the Nathrezim
                {"id": 32837, "phase3": True},   # Warglaive of Azzinoth
                {"id": 32944, "phase3": False},   # Talon of the Phoenix
                {"id": 32946, "phase3": True},   # Claw of Molten Fury
                {"id": 33737, "phase3": True},   # Vengeful Gladiator's Right Ripper
                {"id": 33762, "phase3": True},   # Vengeful Gladiator's Slicer
                {"id": 38175, "phase3": False},   # The Horseman's Blade
            ],
            "off_hand": [
                {"id": 23544, "phase3": False},   # Runic Hammer
                {"id": 27747, "phase3": False},   # Boggspine Knuckles
                {"id": 27872, "phase3": False},   # The Harvester of Souls
                {"id": 28210, "phase3": False},   # Bloodskull Destroyer
                {"id": 28267, "phase3": False},   # Edge of the Cosmos
                {"id": 28295, "phase3": False},   # Gladiator's Slicer
                {"id": 28729, "phase3": False},   # Spiteblade
                {"id": 29124, "phase3": False},   # Vindicator's Brand
                {"id": 29924, "phase3": False},   # Netherbane
                {"id": 29996, "phase3": False},   # Rod of the Sun King
                {"id": 30082, "phase3": False},   # Talon of Azshara
                {"id": 30788, "phase3": False},   # Illidari-Bane Broadsword
                {"id": 30881, "phase3": True},   # Blade of Infamy
                {"id": 31332, "phase3": False},   # Blinkstrike
                {"id": 31965, "phase3": False},   # Merciless Gladiator's Cleaver
                {"id": 32052, "phase3": False},   # Merciless Gladiator's Slicer
                {"id": 32236, "phase3": True},   # Rising Tide
                {"id": 32262, "phase3": True},   # Syphon of the Nathrezim
                {"id": 32838, "phase3": True},   # Warglaive of Azzinoth
                {"id": 33762, "phase3": True},   # Vengeful Gladiator's Slicer
                {"id": 34015, "phase3": True},   # Vengeful Gladiator's Chopper
            ],
        },
        # THE TRINKET POOL, the fourth enumerative trinket round after the
        # Combat Rogue pilot, the Retribution round and the Arms round:
        # every max-level trinket the Fury tab's Trinket ladder ranks, with
        # anything from Karazhan and the badge vendor onward acceptable,
        # and the runner generates every unordered pair itself. The ladder
        # ranks fifteen; eight are out on the standing exclusions, all
        # availability rather than routing: Mark of the Champion, Kiss of
        # the Spider and Slayer's Crest drop in Naxxramas and Badge of the
        # Swarmguard in Ahn'Qiraj, all level-60 raids, the Badge also
        # standing barred by data/judgments/trinket-routing.yaml and
        # check_sim_profiles; the Hourglass of the Unraveller, the Abacus
        # of Violent Odds and the Icon of Unyielding Courage drop in
        # five-man dungeons below Karazhan; and Bladefist's Breadth is a
        # leveling quest reward, not a max-level item. Core of Ar'kelos
        # stays in as a max-level Netherstorm quest reward, per the
        # Retribution precedent. No world-boss trinket is on the tab.
        # Solarian's Sapphire, the tab's rank two, stays in as a Tempest
        # Keep drop a warrior alone may wear, WITH THE SAME CAVEAT the
        # Arms round states: sim/warrior/items.go registers id 30446 as an
        # empty effect and the Battle Shout bonus is applied only when the
        # class option hasBsSolarianSapphire is sent, which
        # run_sims.py::CLASS_OPTIONS does not send, so its rows price the
        # trinket's worn stats alone. The entry and tier anchors wear
        # Dragonspine Trophy with Tsunami Talisman and both best-in-slot
        # anchors wear Dragonspine Trophy with Bloodlust Brooch, the
        # Brooch per the 15 August 2026 routing, all three in the pool, so
        # no worn item needed adding. `phase3` marks what the entry anchor
        # cannot reach: Madness of the Betrayer is a Black Temple drop.
        "trinket_pool": [
            {"id": 28830, "phase3": False},  # Dragonspine Trophy
            {"id": 32505, "phase3": True},   # Madness of the Betrayer
            {"id": 30627, "phase3": False},  # Tsunami Talisman
            {"id": 31856, "phase3": False},  # Darkmoon Card: Crusade
            {"id": 29383, "phase3": False},  # Bloodlust Brooch
            {"id": 29776, "phase3": False},  # Core of Ar'kelos
        ],
        "trinkets_why": (
            (
            "The candidates are every max-level trinket on the EP "
            "Workbook's Trinket ladder for this spec, from Gruul's "
            "Lair, the raids above it, the badge vendor, the Darkmoon "
            "Faire and one max-level quest, and every pair from that "
            "pool was measured, so the table is an enumeration rather "
            "than a selection. Solarian's Sapphire "
            "strengthens the wearer's Battle Shout for the whole "
            "party, the simulator prices that effect outside the "
            "trinket slot, and these runs do not engage it, so its "
            "rows price the worn stats alone and understate it.")),
    },
    # COMBAT ROGUE: dual wield only, per the 20 August 2026 ruling in
    # data/judgments/weapon-styles.yaml. The build is Combat Swords, 20/41/0
    # as the guide labels it and 19/42/0 as its calculator string sums, per
    # data/facts/talents.yaml, and its combat segment decodes to Sword
    # Specialization 5/5; the rotation is the simulator's swords APL, built
    # on Sinister Strike. Every row runs under that rotation, so a dagger
    # row measures the dagger inside the swords rotation rather than a
    # dagger build, and the dagger, fist and mace rows are measured with
    # the caveat the why paragraph states: Sword Specialization does not
    # benefit them. The field is the Rogue tab's Main Hand ladder plus
    # every worn and routed weapon. Combat carries FOUR anchors for the
    # same reason Fury does: the Warglaives of Azzinoth are ranked first by
    # both specs' published lists, the raid holds one pair, and the guild
    # lead has not routed it. Each anchor's worn pair is a row on purpose:
    # its variant must reproduce the anchor figure to the digit, the same
    # verification the other rounds carry. Fool's Bane is the one socketed
    # candidate and no anchor wears it, so its rows arrive ungemmed and
    # its figures are understated by the gem a raider would add.
    "combat_rogue": {
        "anchors": ("entry", "tier-hands-and-head", "bis",
                    "bis-no-glaives"),
        "why": (
            (
            "A Combat Rogue carries two one-handers, so every row below "
            "is a main hand with an off hand and no row is a two- "
            "hander. Each row is THIS PROFILE with only the two weapon "
            "ids replaced: each slot keeps its Mongoose. "
            "The build is Combat Swords and the rotation is built on "
            "Sinister Strike, and every row runs under that rotation, "
            "so a dagger row measures the dagger inside the swords "
            "rotation rather than a dagger build, and the dagger, fist "
            "and mace rows carry a stated "
            "caveat: the build's Sword Specialization talent procs only "
            "on sword strikes and does not benefit them. The table is "
            "an enumeration of the EP Workbook's Main Hand ladder for "
            "this spec together with every worn and routed weapon, and "
            "every ordered pairing the field supports is a row. A row "
            "of two copies of one item "
            "needs both copies before it is wearable. The Warglaives of "
            "Azzinoth are ranked first by this spec's published Phase 3 "
            "list and by the Fury Warrior's, the raid holds one pair, "
            "and which of the two receives it is open council business, "
            "which is why this spec carries a best-in-slot set both "
            "with and without them.")),
        # combat_rogue: derived by tools/derive_weapon_fields.py
        "weapon_field": {
            "styles": ["dual_wield"],
            "two_hand": [],
            "main_hand": [
                {"id": 28295, "phase3": False},   # Gladiator's Slicer
                {"id": 28313, "phase3": False},   # Gladiator's Right Ripper
                {"id": 28437, "phase3": False},   # Drakefist Hammer
                {"id": 28438, "phase3": False},   # Dragonmaw
                {"id": 28439, "phase3": False},   # Dragonstrike
                {"id": 28657, "phase3": False},   # Fool's Bane
                {"id": 28768, "phase3": False},   # Malchazeen
                {"id": 29996, "phase3": False},   # Rod of the Sun King
                {"id": 30082, "phase3": False},   # Talon of Azshara
                {"id": 30103, "phase3": False},   # Fang of Vashj
                {"id": 30881, "phase3": True},   # Blade of Infamy
                {"id": 30901, "phase3": True},   # Boundless Agony
                {"id": 32028, "phase3": False},   # Merciless Gladiator's Right Ripper
                {"id": 32044, "phase3": False},   # Merciless Gladiator's Shanker
                {"id": 32052, "phase3": False},   # Merciless Gladiator's Slicer
                {"id": 32262, "phase3": True},   # Syphon of the Nathrezim
                {"id": 32369, "phase3": True},   # Blade of Savagery
                {"id": 32471, "phase3": True},   # Shard of Azzinoth
                {"id": 32837, "phase3": True},   # Warglaive of Azzinoth
                {"id": 32944, "phase3": False},   # Talon of the Phoenix
                {"id": 32946, "phase3": True},   # Claw of Molten Fury
                {"id": 33737, "phase3": True},   # Vengeful Gladiator's Right Ripper
                {"id": 33754, "phase3": True},   # Vengeful Gladiator's Shanker
                {"id": 33762, "phase3": True},   # Vengeful Gladiator's Slicer
            ],
            "off_hand": [
                {"id": 28295, "phase3": False},   # Gladiator's Slicer
                {"id": 28768, "phase3": False},   # Malchazeen
                {"id": 29996, "phase3": False},   # Rod of the Sun King
                {"id": 30082, "phase3": False},   # Talon of Azshara
                {"id": 30103, "phase3": False},   # Fang of Vashj
                {"id": 30881, "phase3": True},   # Blade of Infamy
                {"id": 30901, "phase3": True},   # Boundless Agony
                {"id": 32027, "phase3": False},   # Merciless Gladiator's Quickblade
                {"id": 32044, "phase3": False},   # Merciless Gladiator's Shanker
                {"id": 32052, "phase3": False},   # Merciless Gladiator's Slicer
                {"id": 32262, "phase3": True},   # Syphon of the Nathrezim
                {"id": 32369, "phase3": True},   # Blade of Savagery
                {"id": 32471, "phase3": True},   # Shard of Azzinoth
                {"id": 32838, "phase3": True},   # Warglaive of Azzinoth
                {"id": 33754, "phase3": True},   # Vengeful Gladiator's Shanker
                {"id": 33762, "phase3": True},   # Vengeful Gladiator's Slicer
            ],
        },
        # THE TRINKET POOL, the pilot of the enumerative trinket rounds
        # ruled on 20 August 2026: every max-level trinket the Rog tab's
        # Trinket ladder ranks, with anything from Karazhan and the badge
        # vendor onward acceptable, and the runner generates every
        # unordered pair itself. The ladder ranks fifteen; seven are out
        # on the standing exclusions, all availability rather than
        # routing: Mark of the Champion, Slayer's Crest, Kiss of the
        # Spider and Drake Fang Talisman drop in level-60 raids, and the
        # Abacus of Violent Odds, Icon of Unyielding Courage and
        # Hourglass of the Unraveller drop in five-man dungeons below
        # Karazhan. No Ahn'Qiraj and no world-boss trinket is on the tab.
        # All four anchors wear Dragonspine Trophy with Warp-Spring Coil,
        # both in the pool, so no worn item needed adding. `phase3` marks
        # what the entry anchor cannot reach: Madness of the Betrayer is
        # a Black Temple drop and the Ashtongue Talisman of Lethality is
        # Ashtongue Deathsworn Exalted, a reputation earned in Black
        # Temple and Mount Hyjal.
        "trinket_pool": [
            {"id": 28830, "phase3": False},  # Dragonspine Trophy
            {"id": 30450, "phase3": False},  # Warp-Spring Coil
            {"id": 32492, "phase3": True},   # Ashtongue Tal. of Lethality
            {"id": 32505, "phase3": True},   # Madness of the Betrayer
            {"id": 30627, "phase3": False},  # Tsunami Talisman
            {"id": 31856, "phase3": False},  # Darkmoon Card: Crusade
            {"id": 29383, "phase3": False},  # Bloodlust Brooch
            {"id": 28579, "phase3": False},  # Romulo's Poison Vial
        ],
        "trinkets_why": (
            (
            "The candidates are every max-level trinket on the EP "
            "Workbook's Trinket ladder for this spec, from Karazhan, "
            "the raids above it and the badge vendor, and every pair "
            "from that pool was measured, so the table is an "
            "enumeration rather than a selection.")),
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
            (
            "An Arms Warrior considers only two-handers, so every row "
            "below is a single weapon and the off hand runs empty. Each "
            "row is THIS PROFILE with only the main hand id replaced: "
            "the slot keeps its Mongoose. The "
            "published Phase 3 page ranks only dual Warglaives, which "
            "this spec will not receive, so the table is an enumeration "
            "of the EP Workbook's Two Hand ladder for this spec "
            "together with every worn and routed weapon, kept to the "
            "weapon classes a warrior wields. This spec "
            "takes Cataclysm's Edge. Torch of the Damned appears as a "
            "measurement only: it stays with the Retribution Paladin.")),
        # arms_warrior: derived by tools/derive_weapon_fields.py
        "weapon_field": {
            "styles": ["two_hand"],
            "two_hand": [
                {"id": 24550, "phase3": False},   # Gladiator's Greatsword
                {"id": 28298, "phase3": False},   # Gladiator's Decapitator
                {"id": 28300, "phase3": False},   # Gladiator's Painsaw
                {"id": 28429, "phase3": False},   # Lionheart Champion
                {"id": 28430, "phase3": False},   # Lionheart Executioner
                {"id": 28435, "phase3": False},   # Mooncleaver
                {"id": 28436, "phase3": False},   # Bloodmoon
                {"id": 28441, "phase3": False},   # Deep Thunder
                {"id": 28442, "phase3": False},   # Stormherald
                {"id": 28773, "phase3": False},   # Gorehowl
                {"id": 28794, "phase3": False},   # Axe of the Gronn Lords
                {"id": 28800, "phase3": False},   # Hammer of the Naaru
                {"id": 29993, "phase3": False},   # Twinblade of the Phoenix
                {"id": 30090, "phase3": False},   # World Breaker
                {"id": 30902, "phase3": True},   # Cataclysm's Edge
                {"id": 31959, "phase3": False},   # Merciless Gladiator's Bonegrinder
                {"id": 31966, "phase3": False},   # Merciless Gladiator's Decapitator
                {"id": 32025, "phase3": False},   # Merciless Gladiator's Painsaw
                {"id": 32248, "phase3": True},   # Halberd of Desolation
                {"id": 32332, "phase3": True},   # Torch of the Damned
                {"id": 32348, "phase3": True},   # Soul Cleaver
                {"id": 33663, "phase3": True},   # Vengeful Gladiator's Bonegrinder
                {"id": 33670, "phase3": True},   # Vengeful Gladiator's Decapitator
                {"id": 33727, "phase3": True},   # Vengeful Gladiator's Painsaw
            ],
            "main_hand": [],
            "off_hand": [],
        },
        # THE TRINKET POOL, the third enumerative trinket round after the
        # Combat Rogue pilot and the Retribution round: every max-level
        # trinket the Arms tab's Trinket ladder ranks, with anything from
        # Karazhan and the badge vendor onward acceptable, and the runner
        # generates every unordered pair itself. The ladder ranks fifteen;
        # eight are out on the standing exclusions, all availability rather
        # than routing: Mark of the Champion, Slayer's Crest and Drake Fang
        # Talisman drop in level-60 raids; the Hourglass of the Unraveller,
        # the Abacus of Violent Odds and the Icon of Unyielding Courage
        # drop in five-man dungeons below Karazhan; and Bladefist's Breadth
        # and the Ancient Draenei War Talisman are leveling quest rewards,
        # not max-level items. Core of Ar'kelos stays in as a max-level
        # Netherstorm quest reward, per the Retribution precedent. No
        # Ahn'Qiraj and no world-boss trinket is on the tab; Badge of the
        # Swarmguard is barred by data/judgments/trinket-routing.yaml and
        # is not on the tab either. Solarian's Sapphire, the tab's rank
        # one, stays in as a Tempest Keep drop a warrior alone may wear,
        # WITH A CAVEAT the why paragraph states: sim/warrior/items.go
        # registers id 30446 as an empty effect and the Battle Shout bonus
        # is applied only when the class option hasBsSolarianSapphire is
        # sent, which run_sims.py::CLASS_OPTIONS does not send, so its
        # rows price the trinket's worn stats alone. The entry and tier
        # anchors wear Dragonspine Trophy with Tsunami Talisman and the
        # best-in-slot anchor wears Dragonspine Trophy with Bloodlust
        # Brooch, the Brooch per the 15 August 2026 routing, all three in
        # the pool, so no worn item needed adding. `phase3` marks what the
        # entry anchor cannot reach: Madness of the Betrayer is a Black
        # Temple drop.
        "trinket_pool": [
            {"id": 28830, "phase3": False},  # Dragonspine Trophy
            {"id": 30627, "phase3": False},  # Tsunami Talisman
            {"id": 29383, "phase3": False},  # Bloodlust Brooch
            {"id": 32505, "phase3": True},   # Madness of the Betrayer
            {"id": 31856, "phase3": False},  # Darkmoon Card: Crusade
            {"id": 29776, "phase3": False},  # Core of Ar'kelos
        ],
        "trinkets_why": (
            (
            "The candidates are every max-level trinket on the EP "
            "Workbook's Trinket ladder for this spec, from Gruul's "
            "Lair, the raids above it, the badge vendor, the Darkmoon "
            "Faire and one max-level quest, and every pair from that "
            "pool was measured, so the table is an enumeration rather "
            "than a selection. Solarian's Sapphire "
            "strengthens the wearer's Battle Shout for the whole "
            "party, the simulator prices that effect outside the "
            "trinket slot, and these runs do not engage it, so its "
            "rows price the worn stats alone and understate it.")),
    },
    # BEAST MASTERY: both styles in the same table, per the 20 August 2026
    # ruling in data/judgments/weapon-styles.yaml, the first spec to mix
    # them: a dual_wield row is a main hand with an off hand, and a two_hand
    # row runs the off hand empty. The melee slots are stat sticks, the
    # ranged weapon does the damage and is not part of this round, so the
    # field is the BM tab's One Hand pool, which is combined like
    # Enhancement's rather than split like Fury's, and its
    # Two Hand ladder, plus every worn and routed weapon, kept to the
    # weapon classes a hunter wields: axes,
    # swords, polearms, staves, fist weapons and daggers, never a mace. The
    # 41/20/0 build carries no weapon specialization talent, per
    # data/facts/talents.yaml, so no class is favored. The worn pairs are
    # rows on purpose: their variants must reproduce the anchor figures to
    # the digit, the same verification the other rounds carry. STONES: the
    # hunters run the Adamantite stone chosen by the WORN weapon's class,
    # per data/judgments/weapon-imbues.yaml, and a variant holds the
    # anchor's consumables still, so the entry and tier anchors, worn with
    # fist weapons, run every candidate under the Weightstone, and the bis
    # anchor, worn with a dagger and a sword, runs the Season 3 fist pair
    # under the Sharpening Stone. SOCKETS: Twinblade of the Phoenix is the
    # one socketed candidate, three sockets, and no BM anchor wears it, so
    # its row arrives ungemmed and its figure is understated by the gems a
    # raider would add.
    "beast_mastery_hunter": {
        "why": (
            (
            "A Beast Mastery Hunter can carry a two-hander or two one- "
            "handers, and both styles run in the same table, so a row "
            "below is either a main hand with an off hand or a single "
            "two-hander with the off hand empty. These slots are stat "
            "sticks: the ranged weapon does the damage and no row here "
            "touches it. Each row is THIS PROFILE with only the weapon "
            "ids replaced: a filled slot keeps its enchant. "
            "Holding the consumables still includes the weapon stones, "
            "which the hunters choose by the WORN weapon's class, so a "
            "candidate whose class differs from the worn weapon runs "
            "under the capture's stone rather than its own. The table "
            "is an enumeration of the EP Workbook's One Hand and "
            "Two Hand ladders for this spec together with every worn "
            "and routed weapon, kept to the weapon classes "
            "a hunter wields and holding no crafted weapon, and the "
            "41/20/0 build carries no weapon "
            "specialization talent, so no class is favored.")),
        # beast_mastery_hunter: derived by tools/derive_weapon_fields.py
        "weapon_field": {
            "styles": ["two_hand", "dual_wield"],
            "two_hand": [
                {"id": 27903, "phase3": False},   # Sonic Spear
                {"id": 28587, "phase3": False},   # Legacy
                {"id": 29166, "phase3": False},   # Hellforged Halberd
                {"id": 29167, "phase3": False},   # Blackened Spear
                {"id": 29993, "phase3": False},   # Twinblade of the Phoenix
                {"id": 30789, "phase3": False},   # Illidari-Bane Claymore
                {"id": 31966, "phase3": False},   # Merciless Gladiator's Decapitator
                {"id": 32248, "phase3": True},   # Halberd of Desolation
                {"id": 33670, "phase3": True},   # Vengeful Gladiator's Decapitator
                {"id": 33727, "phase3": True},   # Vengeful Gladiator's Painsaw
            ],
            "main_hand": [
                {"id": 30082, "phase3": False},   # Talon of Azshara
                {"id": 30865, "phase3": True},   # Tracker's Blade
                {"id": 30881, "phase3": True},   # Blade of Infamy
                {"id": 30901, "phase3": True},   # Boundless Agony
                {"id": 32369, "phase3": True},   # Blade of Savagery
                {"id": 32944, "phase3": False},   # Talon of the Phoenix
            ],
            "off_hand": [
                {"id": 29948, "phase3": False},   # Claw of the Phoenix
                {"id": 30082, "phase3": False},   # Talon of Azshara
                {"id": 30865, "phase3": True},   # Tracker's Blade
                {"id": 30881, "phase3": True},   # Blade of Infamy
                {"id": 30901, "phase3": True},   # Boundless Agony
                {"id": 32369, "phase3": True},   # Blade of Savagery
            ],
        },
        "ranged_why": (
            (
            "The bow is the one hunter weapon that is not a stat stick, "
            "so it gets its own pass: each row below is THIS PROFILE "
            "with only the ranged slot changed, the slot keeping its "
            "scope. The candidates are the workbook's "
            "own Ranged ladder plus the worn weapons, none carries a "
            "socket, and the ammunition and quiver hold still across "
            "the rows.")),
        "ranged": [
            # The Ranged ladder's Phase 3 rows: Bristleblitz Striker
            # from Archimonde is the worn best-in-slot weapon, the Black
            # Bow of the Betrayer falls from Illidan, and Legionkiller
            # from Gurtogg Bloodboil.
            {"id": 30906, "phase3": True},
            {"id": 32336, "phase3": True},
            {"id": 32253, "phase3": True},
            # Reachable before Phase 3: Serpent Spine Longbow from Lady
            # Vashj is the worn entry AND tier weapon, the Arcanite
            # Steam-Pistol from Kael'thas, and the Sunfury Bow of the
            # Phoenix, also from Kael'thas.
            {"id": 30105, "phase3": False},
            {"id": 29949, "phase3": False},
            {"id": 28772, "phase3": False},
        ],
        # THE TRINKET POOL, the sixth enumerative trinket round after the
        # Combat Rogue pilot and the Retribution, Arms, Fury and
        # Enhancement rounds: every max-level trinket the BM tab's Trinket
        # ladder ranks, with anything from Karazhan and the badge vendor
        # onward acceptable, and the runner generates every unordered pair
        # itself. The ladder ranks fifteen; eight are out on the standing
        # exclusions, all availability rather than routing: Mark of the
        # Champion, Slayer's Crest, Kiss of the Spider and Drake Fang
        # Talisman drop in level-60 raids; the Hourglass of the
        # Unraveller, the Abacus of Violent Odds and the Icon of
        # Unyielding Courage drop in five-man dungeons below Karazhan; and
        # Bladefist's Breadth is a leveling quest reward, not a max-level
        # item. Core of Ar'kelos stays in as a max-level Netherstorm quest
        # reward, per the Retribution precedent. Talon of Al'ar, the tab's
        # rank ten and this pool's one class-locked piece, is new to the
        # trinket rounds: it carries no worn stats per items.csv, and the
        # vendored binary DOES price its proc, tested behaviorally on 20
        # August 2026 per the Enhancement precedent, Dragonspine Trophy
        # beside the Talon reading 24.1 above Dragonspine beside an empty
        # slot on the best-in-slot anchor at the same seed. No Ahn'Qiraj
        # and no world-boss trinket is on the tab, and no Ashtongue
        # Talisman is either: the hunter Ashtongue piece is not ranked, so
        # it is not a candidate. The entry and tier anchors wear
        # Dragonspine Trophy with Bloodlust Brooch and the best-in-slot
        # anchor wears Dragonspine Trophy with Madness of the Betrayer,
        # all three in the pool, so no worn item needed adding. `phase3`
        # marks what the entry anchor cannot reach: Madness of the
        # Betrayer is a Black Temple drop.
        "trinket_pool": [
            {"id": 28830, "phase3": False},  # Dragonspine Trophy
            {"id": 32505, "phase3": True},   # Madness of the Betrayer
            {"id": 30627, "phase3": False},  # Tsunami Talisman
            {"id": 31856, "phase3": False},  # Darkmoon Card: Crusade
            {"id": 29383, "phase3": False},  # Bloodlust Brooch
            {"id": 30448, "phase3": False},  # Talon of Al'ar
            {"id": 29776, "phase3": False},  # Core of Ar'kelos
            # The class talisman from the Ashtongue Deathsworn, a
            # reputation purchase contesting nothing, in the pool by
            # ruling even where the ladder is silent.
            {"id": 32487, "phase3": True},   # Ashtongue Tal. of Swiftness
        ],
        "trinkets_why": (
            (
            "The candidates are every max-level trinket on the EP "
            "Workbook's Trinket ladder for this spec, from Gruul's "
            "Lair, the raids above it, the badge vendor, the Darkmoon "
            "Faire and one max-level quest, and every pair from that "
            "pool was measured, so the table is an enumeration rather "
            "than a selection. "
            "Talon of Al'ar carries no worn stats, so its rows measure "
            "the simulator's pricing of its proc alone.")),
    },
    # SURVIVAL: both styles in the same table, per the 20 August 2026 ruling
    # in data/judgments/weapon-styles.yaml, the second spec to mix them: a
    # dual_wield row is a main hand with an off hand, and a two_hand row runs
    # the off hand empty. The melee slots are stat sticks, the ranged weapon
    # does the damage and is not part of this round, so the candidates are
    # the top of the SV workbook tab's One Hand pool, which is combined like
    # the BM and Enhancement tabs rather than split like Fury's, and its Two
    # Hand ladder, kept to the weapon classes a hunter wields. The two-hand
    # field largely overlaps the BM round's, so the two hunter tables read
    # side by side. The 7/20/34 build carries no weapon specialization
    # talent, per data/facts/talents.yaml, so no class is favored, but one
    # stat is worth more than its line here: Expose Weakness is self-applied
    # and scales with this hunter's own agility, so a candidate that moves
    # agility moves the debuff with it. The worn pairs are rows on purpose:
    # their variants must reproduce the anchor figures to the digit, the
    # same verification the other rounds carry. STONES: the hunters run the
    # Adamantite stone chosen by the WORN weapon's class, per
    # data/judgments/weapon-imbues.yaml, and a variant holds the anchor's
    # consumables still. The entry and tier anchors wear an axe with a fist
    # off hand, so their off-hand slot carries the Weightstone, the one
    # stone that feeds ranged base damage per docs/kb/DOMAIN.md, and every
    # bladed off-hand candidate there inherits it; the bis anchor wears two
    # swords, so the Season 3 fist pair runs under the Sharpening Stone.
    # SOCKETS: Twinblade of the Phoenix is the one socketed candidate, three
    # sockets, and no SV anchor wears it, so its row arrives ungemmed and
    # its figure is understated by the gems a raider would add.
    "survival_hunter": {
        "why": (
            (
            "A Survival Hunter can carry a two-hander or two one- "
            "handers, and both styles run in the same table, so a row "
            "below is either a main hand with an off hand or a single "
            "two-hander with the off hand empty. These slots are stat "
            "sticks: the ranged weapon does the damage and no row here "
            "touches it. One stat carries more than its line for this "
            "spec: Expose Weakness is self-applied and scales with this "
            "hunter's own agility, so a candidate that moves agility "
            "moves the debuff with it. Each row is THIS PROFILE with "
            "only the weapon ids replaced: a filled slot keeps its "
            "enchant. Holding the consumables still includes "
            "the weapon stones, which the hunters choose by the WORN "
            "weapon's class, so a candidate whose class differs from "
            "the worn weapon runs under the capture's stone rather than "
            "its own. The table is an enumeration of the EP Workbook's "
            "One Hand and Two Hand ladders for this spec together with "
            "every worn and routed weapon, kept to the "
            "weapon classes a hunter wields and holding no crafted "
            "weapon, and the 7/20/34 build carries no weapon "
            "specialization talent, so no class is favored.")),
        # survival_hunter: derived by tools/derive_weapon_fields.py
        "weapon_field": {
            "styles": ["two_hand", "dual_wield"],
            "two_hand": [
                {"id": 27903, "phase3": False},   # Sonic Spear
                {"id": 28587, "phase3": False},   # Legacy
                {"id": 28773, "phase3": False},   # Gorehowl
                {"id": 29166, "phase3": False},   # Hellforged Halberd
                {"id": 29167, "phase3": False},   # Blackened Spear
                {"id": 29329, "phase3": False},   # Terokk's Quill
                {"id": 29993, "phase3": False},   # Twinblade of the Phoenix
                {"id": 30789, "phase3": False},   # Illidari-Bane Claymore
                {"id": 32248, "phase3": True},   # Halberd of Desolation
                {"id": 33670, "phase3": True},   # Vengeful Gladiator's Decapitator
            ],
            "main_hand": [
                {"id": 28263, "phase3": False},   # Stellaris
                {"id": 28524, "phase3": False},   # Emerald Ripper
                {"id": 29121, "phase3": False},   # Guile of Khoraazi
                {"id": 29182, "phase3": False},   # Riftmaker
                {"id": 29924, "phase3": False},   # Netherbane
                {"id": 30082, "phase3": False},   # Talon of Azshara
                {"id": 30881, "phase3": True},   # Blade of Infamy
                {"id": 31492, "phase3": False},   # Claw of the Netherwing Flight
                {"id": 32269, "phase3": True},   # Messenger of Fate
                {"id": 32946, "phase3": True},   # Claw of Molten Fury
            ],
            "off_hand": [
                {"id": 28263, "phase3": False},   # Stellaris
                {"id": 28524, "phase3": False},   # Emerald Ripper
                {"id": 29121, "phase3": False},   # Guile of Khoraazi
                {"id": 29182, "phase3": False},   # Riftmaker
                {"id": 29924, "phase3": False},   # Netherbane
                {"id": 29948, "phase3": False},   # Claw of the Phoenix
                {"id": 30082, "phase3": False},   # Talon of Azshara
                {"id": 30881, "phase3": True},   # Blade of Infamy
                {"id": 31492, "phase3": False},   # Claw of the Netherwing Flight
                {"id": 32269, "phase3": True},   # Messenger of Fate
                {"id": 32945, "phase3": True},   # Fist of Molten Fury
            ],
        },
        "ranged_why": (
            (
            "The bow is the one hunter weapon that is not a stat stick, "
            "so it gets its own pass: each row below is THIS PROFILE "
            "with only the ranged slot changed, the slot keeping its "
            "scope. The candidates are the workbook's "
            "own Ranged ladder plus the worn weapons, none carries a "
            "socket, and the ammunition and quiver hold still across "
            "the rows.")),
        "ranged": [
            # The Ranged ladder's Phase 3 rows: Bristleblitz Striker
            # from Archimonde is the worn best-in-slot weapon, the Black
            # Bow of the Betrayer falls from Illidan, and Legionkiller
            # from Gurtogg Bloodboil.
            {"id": 30906, "phase3": True},
            {"id": 32336, "phase3": True},
            {"id": 32253, "phase3": True},
            # Reachable before Phase 3: Serpent Spine Longbow from Lady
            # Vashj is the worn entry AND tier weapon, the Arcanite
            # Steam-Pistol from Kael'thas, and the Sunfury Bow of the
            # Phoenix, also from Kael'thas.
            {"id": 30105, "phase3": False},
            {"id": 29949, "phase3": False},
            {"id": 28772, "phase3": False},
        ],
        # THE TRINKET POOL, the seventh enumerative trinket round after the
        # Combat Rogue pilot and the Retribution, Arms, Fury, Enhancement
        # and Beast Mastery rounds: every max-level trinket the SV tab's
        # Trinket ladder ranks, with anything from Karazhan and the badge
        # vendor onward acceptable, and the runner generates every
        # unordered pair itself. The ladder ranks fifteen; seven are out on
        # the standing exclusions, all availability rather than routing:
        # Mark of the Champion, Slayer's Crest, Kiss of the Spider and
        # Drake Fang Talisman drop in level-60 raids, and the Hourglass of
        # the Unraveller, the Abacus of Violent Odds and the Icon of
        # Unyielding Courage drop in five-man dungeons below Karazhan.
        # Core of Ar'kelos stays in as a max-level Netherstorm quest
        # reward, per the Retribution precedent. Badge of Tenacity, the
        # tab's rank five, is new to the trinket rounds: the SV tab is the
        # one melee tab that ranks it, because its 150 on-use agility
        # feeds Expose Weakness, which scales with this hunter's own
        # agility. Its phase3 flag is False despite the workbook's own
        # phase column saying 3: it is charged from Apexis Crystals in
        # Blade's Edge, content available since Anniversary Phase 2 per
        # enchants-gems.yaml, and the Feral Bear ENTRY capture wears it
        # and passes check_capture_availability, so the repository already
        # treats it as reachable before Phase 3. Talon of Al'ar carries no
        # worn stats per items.csv and the vendored binary DOES price its
        # proc, tested behaviorally on 20 August 2026 in the Beast Mastery
        # round. No Ahn'Qiraj and no world-boss trinket is on the tab, and
        # no Ashtongue Talisman is either: the hunter Ashtongue piece is
        # not ranked, so it is not a candidate. The entry and tier anchors
        # wear Dragonspine Trophy with Bloodlust Brooch and the
        # best-in-slot anchor wears Dragonspine Trophy with Madness of the
        # Betrayer, all three in the pool, so no worn item needed adding.
        # `phase3` marks what the entry anchor cannot reach: Madness of
        # the Betrayer is a Black Temple drop.
        "trinket_pool": [
            {"id": 28830, "phase3": False},  # Dragonspine Trophy
            {"id": 32505, "phase3": True},   # Madness of the Betrayer
            {"id": 30627, "phase3": False},  # Tsunami Talisman
            {"id": 32658, "phase3": False},  # Badge of Tenacity
            {"id": 31856, "phase3": False},  # Darkmoon Card: Crusade
            {"id": 29383, "phase3": False},  # Bloodlust Brooch
            {"id": 30448, "phase3": False},  # Talon of Al'ar
            {"id": 29776, "phase3": False},  # Core of Ar'kelos
            # The class talisman from the Ashtongue Deathsworn, a
            # reputation purchase contesting nothing, in the pool by
            # ruling even where the ladder is silent.
            {"id": 32487, "phase3": True},   # Ashtongue Tal. of Swiftness
        ],
        "trinkets_why": (
            (
            "The candidates are every max-level trinket on the EP "
            "Workbook's Trinket ladder for this spec, from Gruul's "
            "Lair, the raids above it, the badge vendor, the Darkmoon "
            "Faire, one max-level quest and one Apexis Crystal charge, "
            "and every pair from that pool was measured, so the table "
            "is an enumeration rather than a selection. "
            "One stat carries more than its "
            "line for this spec: Expose Weakness scales with this "
            "hunter's own agility, so the on-use agility of Badge of "
            "Tenacity feeds the debuff as well as the wearer, which is "
            "why this spec's ladder is the one melee ladder that ranks "
            "it. Talon of Al'ar carries no worn stats, so its rows "
            "measure the simulator's pricing of its proc alone.")),
    },
    # AFFLICTION: both styles in the same table, per the 20 August 2026
    # ruling in data/judgments/weapon-styles.yaml, and THE FIRST CASTER
    # ROUND, so this entry is the template the other five casters copy. A
    # caster's two_hand row is a STAFF alone with the off hand EMPTY, and
    # its main_hand_off_hand row is a one-hander with a HELD FRILL, an Off
    # Hand item that is not a weapon, so `oh` there is the frill's id. The
    # candidates are the top of the Aff workbook tab, which splits One Hand
    # (main-hand casting weapons) from Off Hand (frills) from Two Hand
    # (staves); a warlock wields daggers, one-hand swords and staves and
    # holds any frill. The pairing is the FULL cross product of the main
    # hands against the frills. The Vengeful Gladiator's
    # War Staff is a row beside the Battle Staff, which carries the same
    # statistics plus 28 spell hit. STONES AND OILS: the caster runs Brilliant
    # Wizard Oil on the main hand, an oil applies to any weapon, staff
    # included, and a frill takes no imbue because the simulator excludes
    # non-weapon off hands from imbues, so nothing about the consumables
    # varies across the rows. ENCHANT: the main-hand slot carries Soulfrost
    # per data/facts/enchants-by-spec.yaml and the off-hand slot carries
    # none, so a staff row inherits the main-hand slot's Soulfrost, which
    # is what a raider would do. SOCKETS: no candidate carries a socket,
    # per items.csv, so no figure here is understated against a gemmed
    # worn weapon. The worn combinations are rows on purpose: their
    # variants must reproduce the anchor figures to the digit, the same
    # verification the other rounds carry, including the best-in-slot
    # Zhar'doom row with its empty off hand.
    "affliction_warlock": {
        "why": (
            (
            "An Affliction Warlock can carry a staff or a one-hander "
            "with a held frill, and both styles run in the same table, "
            "so a row below is either a single staff with the off hand "
            "empty or a main hand with an off-hand frill that is not a "
            "weapon. Each row is THIS PROFILE with only the weapon "
            "slots changed: the main hand keeps its Soulfrost, which a "
            "staff row inherits because the enchant belongs to the "
            "slot. The Brilliant Wizard Oil applies to any "
            "weapon, staff and dagger alike, and a frill takes no "
            "imbue, so nothing about the consumables varies across the "
            "rows. The table is an enumeration of the EP Workbook's Two "
            "Hand, One Hand and Off Hand ladders for this spec together "
            "with every worn and routed weapon, and no "
            "candidate carries a socket. Zhar'doom goes to the "
            "warlocks, the Balance Druid, the Elemental Shaman and the "
            "Shadow Priest, and its wearers hold no off hand, which is "
            "why the best-in-slot anchor wears it with the off-hand "
            "slot empty. Tempest of Chaos is taken first by the Arcane "
            "Mage, and first is an ordering rather than an exclusion: "
            "the warlocks' lists rank it too, so its rows measure what "
            "this spec holds once the mage is served.")),
        # affliction_warlock: derived by tools/derive_weapon_fields.py
        "weapon_field": {
            "styles": ["two_hand", "main_hand_off_hand"],
            "two_hand": [
                {"id": 24557, "phase3": False},   # Gladiator's War Staff
                {"id": 27842, "phase3": False},   # Grand Scepter of the Nexus-Kings
                {"id": 28341, "phase3": False},   # Warpstaff of Arcanum
                {"id": 28633, "phase3": False},   # Staff of Infinite Mysteries
                {"id": 28935, "phase3": False},   # High Warlord's War Staff
                {"id": 28959, "phase3": False},   # Grand Marshal's War Staff
                {"id": 29130, "phase3": False},   # Auchenai Staff
                {"id": 29355, "phase3": False},   # Terokk's Shadowstaff
                {"id": 29988, "phase3": False},   # The Nexus Key
                {"id": 32055, "phase3": False},   # Merciless Gladiator's War Staff
                {"id": 32374, "phase3": True},   # Zhar'doom, Greatstaff of the Devourer
                {"id": 33766, "phase3": True},   # Vengeful Gladiator's War Staff
                {"id": 34540, "phase3": True},   # Vengeful Gladiator's Battle Staff
            ],
            "main_hand": [
                {"id": 23554, "phase3": False},   # Eternium Runed Blade
                {"id": 27905, "phase3": False},   # Greatsword of Horrid Dreams
                {"id": 28297, "phase3": False},   # Gladiator's Spellblade
                {"id": 28770, "phase3": False},   # Nathrezim Mindblade
                {"id": 28802, "phase3": False},   # Bloodmaw Magus-Blade
                {"id": 29153, "phase3": False},   # Blade of the Archmage
                {"id": 29155, "phase3": False},   # Stormcaller
                {"id": 30095, "phase3": False},   # Fang of the Leviathan
                {"id": 30787, "phase3": False},   # Illidari-Bane Mageblade
                {"id": 30910, "phase3": True},   # Tempest of Chaos
                {"id": 31336, "phase3": False},   # Blade of Wizardry
                {"id": 32053, "phase3": False},   # Merciless Gladiator's Spellblade
                {"id": 32237, "phase3": True},   # The Maelstrom's Fury
                {"id": 33763, "phase3": True},   # Vengeful Gladiator's Spellblade
            ],
            "off_hand": [
                {"id": 25099, "phase3": False},   # Draenei Crystal Rod
                {"id": 28187, "phase3": False},   # Star-Heart Lamp
                {"id": 28260, "phase3": False},   # Manual of the Nethermancer
                {"id": 28412, "phase3": False},   # Lamp of Peaceful Radiance
                {"id": 28603, "phase3": False},   # Talisman of Nightbane
                {"id": 28734, "phase3": False},   # Jewel of Infinite Possibilities
                {"id": 28781, "phase3": False},   # Karaborian Talisman
                {"id": 29272, "phase3": False},   # Orb of the Soul-Eater
                {"id": 29273, "phase3": False},   # Khadgar's Knapsack
                {"id": 30049, "phase3": False},   # Fathomstone
                {"id": 30872, "phase3": True},   # Chronicle of Dark Secrets
                {"id": 31978, "phase3": False},   # Merciless Gladiator's Endgame
                {"id": 32361, "phase3": True},   # Blind-Seers Icon
                {"id": 32533, "phase3": False},   # Karrog's Shard
                {"id": 32651, "phase3": False},   # Crystal Orb of Enlightenment
            ],
        },
        # THE TRINKET POOL, the eighth enumerative trinket round and the
        # FIRST FOR A CASTER, the shape the five remaining caster rounds
        # copy: every max-level trinket the Aff tab's Trinket ladder
        # ranks, with anything from Karazhan and the badge vendor onward
        # acceptable, and the runner generates every unordered pair
        # itself. The ladder ranks fifteen; seven are out on the standing
        # exclusions, all availability rather than routing: Mark of the
        # Champion, Neltharion's Tear and The Restrained Essence of
        # Sapphiron drop in level-60 raids; Arcanist's Stone and
        # Shiffar's Nexus-Horn drop in five-man dungeons below Karazhan;
        # the Dark Iron Smoking Pipe drops from a holiday boss inside
        # Blackrock Depths, a level-60 five-man; and the Terokkar Tablet
        # of Vim is a leveling quest reward, not a max-level item.
        # Starkiller's Bauble stays in as a max-level Netherstorm quest
        # reward, per the Retribution precedent for Core of Ar'kelos.
        # Quagmirran's Eye drops in a five-man below Karazhan too and
        # the standing exclusion would bar it, but every anchor WEARS
        # it, entry and tier beside the Icon of the Silver Crescent and
        # best in slot beside The Skull of Gul'dan, so it enters as a
        # worn trinket, the first round to need that rule. No Ahn'Qiraj
        # and no world-boss trinket is on the tab. The warlock's own
        # Ashtongue Talisman of Shadows, id 32493, is NOT in the pool,
        # because the tab does not rank it and the pool is the ladder.
        # Darkmoon Card: Crusade carries no worn stats per items.csv, so
        # everything its rows measure is the simulator's pricing of its
        # stacking proc, and the vendored binary DOES price it: a
        # diagnostic run on 20 August 2026 read The Skull of Gul'dan
        # beside the Card at 2233.6 on the best-in-slot anchor, 72.9
        # above the Skull beside an EMPTY slot at 2160.7. The same
        # diagnostic priced the Skull itself, worn stats plus its on-use
        # haste: Quagmirran's Eye beside the Skull read 2227.6, 100.8
        # above Quagmirran's Eye beside an empty slot at 2126.8, and
        # 2227.6 IS the anchor figure, this being the worn pair. Eye of
        # Magtheridon, whose proc fires on a RESIST, read 2185.2 beside
        # Quagmirran's Eye, 58.4 above the empty slot, on a hit-capped
        # set that rarely resists. The recovered source checkout is
        # stale against the vendored binary and is not evidence about
        # what the binary implements; every claim above is a behavioral
        # measurement of the binary. `phase3` marks what the entry
        # anchor cannot reach: The Skull of Gul'dan drops from Illidan
        # Stormrage in Black Temple.
        "trinket_pool": [
            {"id": 32483, "phase3": True},   # The Skull of Gul'dan
            {"id": 27683, "phase3": False},  # Quagmirran's Eye
            {"id": 30626, "phase3": False},  # Sextant of Unstable Currents
            {"id": 31856, "phase3": False},  # Darkmoon Card: Crusade
            {"id": 29132, "phase3": False},  # Scryer's Bloodgem
            {"id": 28789, "phase3": False},  # Eye of Magtheridon
            {"id": 29370, "phase3": False},  # Icon of the Silver Crescent
            {"id": 30340, "phase3": False},  # Starkiller's Bauble
            # The class talisman from the Ashtongue Deathsworn, a
            # reputation purchase contesting nothing, in the pool by
            # ruling even where the ladder is silent.
            {"id": 32493, "phase3": True},   # Ashtongue Tal. of Shadows
        ],
        "trinkets_why": (
            (
            "The candidates are every max-level trinket on the EP "
            "Workbook's Trinket ladder for this spec, from "
            "Magtheridon's Lair, the raids above it, the badge vendor, "
            "the Darkmoon Faire, one reputation, one max-level quest "
            "and the dungeon trinket every anchor wears, and every "
            "pair from that pool was measured, so the table is an "
            "enumeration rather than a selection. The Skull of "
            "Gul'dan's haste burst meets the casting rotation on that "
            "schedule. Darkmoon Card: Crusade carries no worn "
            "statistics, so everything its rows measure is the "
            "simulator's pricing of its stacking proc. Eye of "
            "Magtheridon procs when a spell is resisted, so its rows "
            "price its worn spell damage and a proc a hit-capped set "
            "rarely triggers.")),
    },
    # DESTRUCTION: both styles in the same table, per the 20 August 2026
    # ruling in data/judgments/weapon-styles.yaml, in the shape the
    # Affliction round set as the caster template. The candidates are the
    # top of the Dest workbook tab, whose weapon ladders are One Hand,
    # Off Hand, Two Hand and Ranged, and the two warlock tabs rank the
    # same weapons at the top of every ladder; where the specs differ is
    # the worn off hand, the Destruction captures hold the Flametongue
    # Seal where Affliction held the Jewel of Infinite Possibilities. The
    # Vengeful Gladiator's War Staff is a row beside the Battle Staff,
    # which carries the same
    # statistics plus 28 spell hit. SOCKETS: the only socketed
    # weapon anywhere in the tab's ladders is Talon of the Tempest, One
    # Hand rank five, below the cut, so no candidate in the round carries
    # a socket. STONES, OILS AND ENCHANT: identical to the Affliction
    # round, Brilliant Wizard Oil on the main hand, no frill imbue, and
    # the main-hand slot's Soulfrost inherited by every row, staff
    # included. The worn combinations are rows on purpose: their variants
    # must reproduce the anchor figures to the digit, including the
    # best-in-slot Zhar'doom row with its empty off hand.
    "destruction_warlock": {
        "why": (
            (
            "A Destruction Warlock can carry a staff or a one-hander "
            "with a held frill, and both styles run in the same table, "
            "so a row below is either a single staff with the off hand "
            "empty or a main hand with an off-hand frill that is not a "
            "weapon. Each row is THIS PROFILE with only the weapon "
            "slots changed: the main hand keeps its Soulfrost, which a "
            "staff row inherits because the enchant belongs to the "
            "slot. The Brilliant Wizard Oil applies to any "
            "weapon, staff and dagger alike, and a frill takes no "
            "imbue, so nothing about the consumables varies across the "
            "rows. The table is an enumeration of the EP Workbook's Two "
            "Hand, One Hand and Off Hand ladders for this spec together "
            "with every worn and routed weapon, and no "
            "candidate carries a socket. Zhar'doom goes to the "
            "warlocks, the Balance Druid, the Elemental Shaman and the "
            "Shadow Priest, and its wearers hold no off hand, which is "
            "why the best-in-slot anchor wears it with the off-hand "
            "slot empty. Tempest of Chaos is taken first by the Arcane "
            "Mage, and first is an ordering rather than an exclusion: "
            "the warlocks' lists rank it too, so its rows measure what "
            "this spec holds once the mage is served.")),
        # destruction_warlock: derived by tools/derive_weapon_fields.py
        "weapon_field": {
            "styles": ["two_hand", "main_hand_off_hand"],
            "two_hand": [
                {"id": 24557, "phase3": False},   # Gladiator's War Staff
                {"id": 27842, "phase3": False},   # Grand Scepter of the Nexus-Kings
                {"id": 28341, "phase3": False},   # Warpstaff of Arcanum
                {"id": 28633, "phase3": False},   # Staff of Infinite Mysteries
                {"id": 28935, "phase3": False},   # High Warlord's War Staff
                {"id": 28959, "phase3": False},   # Grand Marshal's War Staff
                {"id": 29130, "phase3": False},   # Auchenai Staff
                {"id": 29355, "phase3": False},   # Terokk's Shadowstaff
                {"id": 29988, "phase3": False},   # The Nexus Key
                {"id": 32055, "phase3": False},   # Merciless Gladiator's War Staff
                {"id": 32374, "phase3": True},   # Zhar'doom, Greatstaff of the Devourer
                {"id": 33766, "phase3": True},   # Vengeful Gladiator's War Staff
                {"id": 34540, "phase3": True},   # Vengeful Gladiator's Battle Staff
            ],
            "main_hand": [
                {"id": 23554, "phase3": False},   # Eternium Runed Blade
                {"id": 27905, "phase3": False},   # Greatsword of Horrid Dreams
                {"id": 28297, "phase3": False},   # Gladiator's Spellblade
                {"id": 28770, "phase3": False},   # Nathrezim Mindblade
                {"id": 28802, "phase3": False},   # Bloodmaw Magus-Blade
                {"id": 29153, "phase3": False},   # Blade of the Archmage
                {"id": 29155, "phase3": False},   # Stormcaller
                {"id": 30095, "phase3": False},   # Fang of the Leviathan
                {"id": 30787, "phase3": False},   # Illidari-Bane Mageblade
                {"id": 30910, "phase3": True},   # Tempest of Chaos
                {"id": 31336, "phase3": False},   # Blade of Wizardry
                {"id": 32053, "phase3": False},   # Merciless Gladiator's Spellblade
                {"id": 32237, "phase3": True},   # The Maelstrom's Fury
                {"id": 33763, "phase3": True},   # Vengeful Gladiator's Spellblade
            ],
            "off_hand": [
                {"id": 25099, "phase3": False},   # Draenei Crystal Rod
                {"id": 28187, "phase3": False},   # Star-Heart Lamp
                {"id": 28412, "phase3": False},   # Lamp of Peaceful Radiance
                {"id": 28603, "phase3": False},   # Talisman of Nightbane
                {"id": 28734, "phase3": False},   # Jewel of Infinite Possibilities
                {"id": 28781, "phase3": False},   # Karaborian Talisman
                {"id": 29270, "phase3": False},   # Flametongue Seal
                {"id": 29272, "phase3": False},   # Orb of the Soul-Eater
                {"id": 29273, "phase3": False},   # Khadgar's Knapsack
                {"id": 30049, "phase3": False},   # Fathomstone
                {"id": 30872, "phase3": True},   # Chronicle of Dark Secrets
                {"id": 31978, "phase3": False},   # Merciless Gladiator's Endgame
                {"id": 32361, "phase3": True},   # Blind-Seers Icon
                {"id": 32533, "phase3": False},   # Karrog's Shard
                {"id": 32651, "phase3": False},   # Crystal Orb of Enlightenment
            ],
        },
        # THE TRINKET POOL, the ninth enumerative trinket round and the
        # second caster round, in the shape the Affliction round set:
        # every max-level trinket the Dest tab's Trinket ladder ranks,
        # with anything from Karazhan and the badge vendor onward
        # acceptable, and the runner generates every unordered pair
        # itself. The ladder ranks fifteen; six are out on the standing
        # exclusions, all availability rather than routing: Mark of the
        # Champion, Neltharion's Tear and The Restrained Essence of
        # Sapphiron drop in level-60 raids; Arcanist's Stone and
        # Shiffar's Nexus-Horn drop in five-man dungeons below Karazhan;
        # and the Dark Iron Smoking Pipe drops from a holiday boss inside
        # Blackrock Depths, a level-60 five-man. The Dest tab differs
        # from the Aff tab twice at the bottom: it does not rank the
        # Terokkar Tablet of Vim, and it ranks the Void Star Talisman,
        # rank fifteen, a warlock-only Tempest Keep drop from High
        # Astromancer Solarian, which enters as a max-level raid
        # trinket. Starkiller's Bauble stays in as a max-level
        # Netherstorm quest reward, per the Retribution precedent for
        # Core of Ar'kelos. Quagmirran's Eye drops in a five-man below
        # Karazhan and the standing exclusion would bar it, but every
        # anchor WEARS it, entry and tier beside the Sextant of Unstable
        # Currents and best in slot beside The Skull of Gul'dan, so it
        # enters as a worn trinket, per the Affliction precedent. No
        # Ahn'Qiraj and no world-boss trinket is on the tab. The
        # warlock's own Ashtongue Talisman of Shadows, id 32493, is NOT
        # in the pool, because the tab does not rank it and the pool is
        # the ladder. Darkmoon Card: Crusade carries no worn stats per
        # items.csv, so everything its rows measure is the simulator's
        # pricing of its stacking proc, which the Affliction round
        # measured behaviorally against the vendored binary; the
        # recovered source checkout is stale against that binary and is
        # not evidence about what it implements. `phase3` marks what the
        # entry anchor cannot reach: The Skull of Gul'dan drops from
        # Illidan Stormrage in Black Temple.
        "trinket_pool": [
            {"id": 32483, "phase3": True},   # The Skull of Gul'dan
            {"id": 30626, "phase3": False},  # Sextant of Unstable Currents
            {"id": 27683, "phase3": False},  # Quagmirran's Eye
            {"id": 31856, "phase3": False},  # Darkmoon Card: Crusade
            {"id": 28789, "phase3": False},  # Eye of Magtheridon
            {"id": 29370, "phase3": False},  # Icon of the Silver Crescent
            {"id": 29132, "phase3": False},  # Scryer's Bloodgem
            {"id": 30340, "phase3": False},  # Starkiller's Bauble
            {"id": 30449, "phase3": False},  # Void Star Talisman
            # The class talisman from the Ashtongue Deathsworn, a
            # reputation purchase contesting nothing, in the pool by
            # ruling even where the ladder is silent.
            {"id": 32493, "phase3": True},   # Ashtongue Tal. of Shadows
        ],
        "trinkets_why": (
            (
            "The candidates are every max-level trinket on the EP "
            "Workbook's Trinket ladder for this spec, from "
            "Magtheridon's Lair, the raids above it, the badge vendor, "
            "the Darkmoon Faire, one reputation, one max-level quest "
            "and the dungeon trinket every anchor wears, and every "
            "pair from that pool was measured, so the table is an "
            "enumeration rather than a selection. The Skull of "
            "Gul'dan's haste burst meets the casting rotation on that "
            "schedule. Darkmoon Card: Crusade carries no worn "
            "statistics, so everything its rows measure is the "
            "simulator's pricing of its stacking proc. Eye of "
            "Magtheridon procs when a spell is resisted, so its rows "
            "price its worn spell damage and a proc a hit-capped set "
            "rarely triggers. The Void Star Talisman is the one "
            "candidate only a warlock can wear, and its on-use effect "
            "is a damage shield on the demon rather than a damage "
            "statistic, so its rows price its worn spell damage "
            "alone.")),
    },
    # ARCANE MAGE: both styles in the same table, per the 20 August 2026
    # ruling in data/judgments/weapon-styles.yaml, in the shape the
    # Affliction round set as the caster template. The field is the Arc
    # tab's One Hand, Off Hand and Two Hand ladders plus every worn and
    # routed weapon; a mage wields daggers, one-hand
    # swords and staves and holds any frill. ZHAR'DOOM IS A ROW even
    # though the
    # guild lead routed it to the warlocks, the Balance Druid, the
    # Elemental Shaman and the Shadow Priest, because a routing never
    # excludes a candidate; the mage takes Tempest of Chaos first, so
    # this spec's best-in-slot set
    # wears the one-hander with a frill and never holds the staff. The
    # rows below therefore price the mage's OWN staff field, Season 3,
    # Season 2 and the worn Nexus Key, against Tempest and the other main
    # hands with the top frills; the warlock rounds measured what other
    # specs lose while the mage holds Tempest, and this round measures
    # what the mage loses if it concedes it. The Vengeful Gladiator's War
    # Staff is a row beside the Battle Staff, which carries the same
    # statistics plus 28 spell hit.
    # SOCKETS: no candidate carries a socket, per items.csv.
    # STONES, OILS AND ENCHANT: Brilliant Wizard Oil on the main hand at
    # every anchor, no frill imbue, and the main-hand slot's Sunfire
    # inherited by every row, staff included. The worn combinations are
    # rows on purpose: their variants must reproduce the anchor figures
    # to the digit, the entry and tier anchors wearing The Nexus Key
    # alone and the best-in-slot anchor wearing Tempest of Chaos with
    # the Chronicle of Dark Secrets.
    "arcane_mage": {
        "why": (
            (
            "An Arcane Mage can carry a staff or a one-hander with a "
            "held frill, and both styles run in the same table, so a "
            "row below is either a single staff with the off hand empty "
            "or a main hand with an off-hand frill that is not a "
            "weapon. Each row is THIS PROFILE with only the weapon "
            "slots changed: the main hand keeps its Sunfire, which a "
            "staff row inherits because the enchant belongs to the "
            "slot. The Brilliant Wizard Oil applies to any "
            "weapon, staff and sword alike, and a frill takes no imbue, "
            "so nothing about the consumables varies across the rows. "
            "The table is an enumeration of the EP Workbook's Two Hand, "
            "One Hand and Off Hand ladders for this spec together with "
            "every worn and routed weapon, and no "
            "candidate carries a socket. Zhar'doom is a row even though "
            "it goes to the warlocks, the Balance Druid, the Elemental "
            "Shaman and the Shadow Priest, with the Arcane Mage taking "
            "Tempest of Chaos first, so this spec's best-in-slot set "
            "wears the one-hander with a frill rather than the staff. "
            "The staff is measured anyway, and the preference stays "
            "with the council. The table therefore carries every half "
            "of the Tempest question: the warlock rounds measure what "
            "other specs lose while the mage holds it, and this table "
            "measures what the mage loses if it concedes it, and what "
            "the routed staff would be worth here.")),
        # arcane_mage: derived by tools/derive_weapon_fields.py
        "weapon_field": {
            "styles": ["two_hand", "main_hand_off_hand"],
            "two_hand": [
                {"id": 24557, "phase3": False},   # Gladiator's War Staff
                {"id": 28188, "phase3": False},   # Bloodfire Greatstaff
                {"id": 28341, "phase3": False},   # Warpstaff of Arcanum
                {"id": 28633, "phase3": False},   # Staff of Infinite Mysteries
                {"id": 28935, "phase3": False},   # High Warlord's War Staff
                {"id": 29130, "phase3": False},   # Auchenai Staff
                {"id": 29355, "phase3": False},   # Terokk's Shadowstaff
                {"id": 29988, "phase3": False},   # The Nexus Key
                {"id": 31308, "phase3": False},   # The Bringer of Death
                {"id": 32055, "phase3": False},   # Merciless Gladiator's War Staff
                {"id": 32374, "phase3": True},   # Zhar'doom, Greatstaff of the Devourer
                {"id": 32662, "phase3": False},   # Flaming Quartz Staff
                {"id": 33766, "phase3": True},   # Vengeful Gladiator's War Staff
                {"id": 34540, "phase3": True},   # Vengeful Gladiator's Battle Staff
            ],
            "main_hand": [
                {"id": 23554, "phase3": False},   # Eternium Runed Blade
                {"id": 27905, "phase3": False},   # Greatsword of Horrid Dreams
                {"id": 28297, "phase3": False},   # Gladiator's Spellblade
                {"id": 28770, "phase3": False},   # Nathrezim Mindblade
                {"id": 28802, "phase3": False},   # Bloodmaw Magus-Blade
                {"id": 29153, "phase3": False},   # Blade of the Archmage
                {"id": 29155, "phase3": False},   # Stormcaller
                {"id": 30095, "phase3": False},   # Fang of the Leviathan
                {"id": 30787, "phase3": False},   # Illidari-Bane Mageblade
                {"id": 30910, "phase3": True},   # Tempest of Chaos
                {"id": 31336, "phase3": False},   # Blade of Wizardry
                {"id": 32053, "phase3": False},   # Merciless Gladiator's Spellblade
                {"id": 32237, "phase3": True},   # The Maelstrom's Fury
                {"id": 33763, "phase3": True},   # Vengeful Gladiator's Spellblade
            ],
            "off_hand": [
                {"id": 28187, "phase3": False},   # Star-Heart Lamp
                {"id": 28260, "phase3": False},   # Manual of the Nethermancer
                {"id": 28412, "phase3": False},   # Lamp of Peaceful Radiance
                {"id": 28603, "phase3": False},   # Talisman of Nightbane
                {"id": 28734, "phase3": False},   # Jewel of Infinite Possibilities
                {"id": 28781, "phase3": False},   # Karaborian Talisman
                {"id": 29271, "phase3": False},   # Talisman of Kalecgos
                {"id": 29273, "phase3": False},   # Khadgar's Knapsack
                {"id": 29330, "phase3": False},   # The Saga of Terokk
                {"id": 30049, "phase3": False},   # Fathomstone
                {"id": 30872, "phase3": True},   # Chronicle of Dark Secrets
                {"id": 31494, "phase3": False},   # Netherwing Sorceror's Charm
                {"id": 31978, "phase3": False},   # Merciless Gladiator's Endgame
                {"id": 32361, "phase3": True},   # Blind-Seers Icon
                {"id": 32651, "phase3": False},   # Crystal Orb of Enlightenment
            ],
        },
        # THE TRINKET POOL, the tenth enumerative trinket round and the
        # third caster round, in the shape the Affliction round set: every
        # max-level trinket the Arc tab's Trinket ladder ranks, with
        # anything from Karazhan and the badge vendor onward acceptable,
        # and the runner generates every unordered pair itself. The ladder
        # ranks fifteen; seven are out on the standing exclusions, all
        # availability rather than routing: Mark of the Champion, The
        # Restrained Essence of Sapphiron and Neltharion's Tear drop in
        # level-60 raids; Shiffar's Nexus-Horn, Scarab of the Infinite
        # Cycle and Quagmirran's Eye drop in five-man dungeons below
        # Karazhan; and the Dark Iron Smoking Pipe drops from a holiday
        # boss inside Blackrock Depths, a level-60 five-man. Quagmirran's
        # Eye entered both warlock rounds as a WORN trinket over the same
        # exclusion, but no arcane anchor wears it, so the override does
        # not trigger here and the standing exclusion holds. The Arc tab's
        # bottom differs from the warlock tabs': it ranks the Serpent-Coil
        # Braid, mage-only per items.csv and worn at EVERY anchor, entry
        # and tier beside the Icon of the Silver Crescent and best in slot
        # beside The Skull of Gul'dan; the Pendant of the Violet Eye from
        # Shade of Aran, in as a Karazhan drop; and Xi'ri's Gift at Sha'tar
        # Revered, in as a max-level reputation reward; and it does not
        # rank Scryer's Bloodgem or Starkiller's Bauble. No Ahn'Qiraj and
        # no world-boss trinket is on the tab. Darkmoon Card: Crusade
        # carries no worn stats per items.csv, so everything its rows
        # measure is the simulator's pricing of its stacking proc, which
        # both warlock rounds measured behaviorally against the vendored
        # binary; a diagnostic on 20 August 2026 repeated the test for
        # this spec, each candidate beside the worn Serpent-Coil Braid
        # against the Braid beside an EMPTY slot, same seed, best-in-slot
        # anchor: the figures are in sim-results.yaml under
        # the_arcane_trinket_round_is_enumerated. The recovered source
        # checkout is stale against the vendored binary and is not
        # evidence about what the binary implements; every claim above is
        # a behavioral measurement of the binary. `phase3` marks what the
        # entry anchor cannot reach: The Skull of Gul'dan drops from
        # Illidan Stormrage in Black Temple.
        "trinket_pool": [
            {"id": 32483, "phase3": True},   # The Skull of Gul'dan
            {"id": 30626, "phase3": False},  # Sextant of Unstable Currents
            {"id": 31856, "phase3": False},  # Darkmoon Card: Crusade
            {"id": 28789, "phase3": False},  # Eye of Magtheridon
            {"id": 29370, "phase3": False},  # Icon of the Silver Crescent
            {"id": 30720, "phase3": False},  # Serpent-Coil Braid
            {"id": 28727, "phase3": False},  # Pendant of the Violet Eye
            {"id": 29179, "phase3": False},  # Xi'ri's Gift
            # The class talisman from the Ashtongue Deathsworn, a
            # reputation purchase contesting nothing, in the pool by
            # ruling even where the ladder is silent.
            {"id": 32488, "phase3": True},   # Ashtongue Tal. of Insight
        ],
        "trinkets_why": (
            (
            "The candidates are every max-level trinket on the EP "
            "Workbook's Trinket ladder for this spec, from Karazhan, "
            "Magtheridon's Lair, the raids above them, the badge "
            "vendor, the Darkmoon Faire and one reputation, and every "
            "pair from that pool was measured, so the table is an "
            "enumeration rather than a selection. Four candidates "
            "carry an on-use effect and Arcane Power is an on-use "
            "cooldown, so how a trinket burst lines up with Arcane "
            "Power is the engine's scheduling rather than an "
            "assumption. "
            "Darkmoon Card: Crusade carries no worn statistics, so "
            "everything its rows measure is the simulator's pricing of "
            "its stacking proc. Eye of Magtheridon procs when a spell "
            "is resisted, so its rows price its worn spell damage and "
            "a proc a hit-capped set rarely triggers. The Serpent-Coil "
            "Braid improves the mana gem the rotation already uses, "
            "and the Pendant of the Violet Eye restores mana on use, "
            "so what their rows price beyond their worn statistics is "
            "mana, which becomes damage only when the set runs dry.")),
    },
    # SHADOW PRIEST: both styles in the same table, per the 20 August 2026
    # ruling in data/judgments/weapon-styles.yaml, in the shape the
    # Affliction round set as the caster template. The candidates are the
    # top of the Shad workbook tab, whose weapon ladders are One Hand,
    # Off Hand, Two Hand and Ranged. A priest wields daggers, one-hand
    # maces and staves and holds any frill, and CANNOT WIELD SWORDS, so
    # Tempest of Chaos is not a row: its exclusion is proficiency rather
    # than routing, and the tab agrees, its One Hand ladder holds no
    # sword. The ladder's rank one and rank two, the Vengeful Gladiator's
    # Gavel and Spellblade, carry identical statistics per items.csv, a
    # mace and a dagger at the same figures, so the Gavel row stands for
    # both. The rank-one frill for THIS spec is the Blind-Seers Icon,
    # 61.45 to the Chronicle of Dark Secrets' 59.95, the reverse of the
    # warlock tabs. The Vengeful Gladiator's War Staff is a row beside
    # the Battle Staff, which
    # carries the same statistics plus 28 spell hit.
    # SOCKETS: the only socketed weapon anywhere in the tab's ladders is
    # Talon of the Tempest, One Hand rank seven, below the cut, so no
    # candidate in the round carries a socket. STONES, OILS AND ENCHANT:
    # Superior Wizard Oil on the main hand at every anchor, per the
    # priest's picks in consumable-ids.yaml, no frill imbue, and the
    # main-hand slot's Soulfrost inherited by every row, staff included.
    # The worn combinations are rows on purpose: their variants must
    # reproduce the anchor figures to the digit, the entry and tier
    # anchors wearing the Merciless Gladiator's Spellblade with the Orb
    # of the Soul-Eater and the best-in-slot anchor wearing Zhar'doom
    # with its empty off hand.
    "shadow_priest": {
        "why": (
            (
            "A Shadow Priest can carry a staff or a one-hander with a "
            "held frill, and both styles run in the same table, so a "
            "row below is either a single staff with the off hand empty "
            "or a main hand with an off-hand frill that is not a "
            "weapon. Each row is THIS PROFILE with only the weapon "
            "slots changed: the main hand keeps its Soulfrost, which a "
            "staff row inherits because the enchant belongs to the "
            "slot. The Superior Wizard Oil applies to any "
            "weapon, staff and mace alike, and a frill takes no imbue, "
            "so nothing about the consumables varies across the rows. "
            "The table is an enumeration of the EP Workbook's Two Hand, "
            "One Hand and Off Hand ladders for this spec together with "
            "every worn and routed weapon, and no "
            "candidate carries a socket. A priest wields daggers, one- "
            "hand maces and staves and holds any frill, and cannot "
            "wield swords, so Tempest of Chaos, the sword the warlock "
            "and mage rounds price, is not a row here: the warlocks "
            "hold it in principle and concede it to the Arcane Mage, "
            "where this spec cannot equip it at all, so its one-hand "
            "rows draw on maces and daggers instead. Zhar'doom goes to "
            "the warlocks, the Balance Druid, the Elemental Shaman and "
            "the Shadow Priest, and its wearers hold no off hand, which "
            "is why the best-in-slot anchor wears it with the off-hand "
            "slot empty.")),
        # shadow_priest: derived by tools/derive_weapon_fields.py
        "weapon_field": {
            "styles": ["two_hand", "main_hand_off_hand"],
            "two_hand": [
                {"id": 24557, "phase3": False},   # Gladiator's War Staff
                {"id": 27842, "phase3": False},   # Grand Scepter of the Nexus-Kings
                {"id": 28341, "phase3": False},   # Warpstaff of Arcanum
                {"id": 28633, "phase3": False},   # Staff of Infinite Mysteries
                {"id": 28935, "phase3": False},   # High Warlord's War Staff
                {"id": 28959, "phase3": False},   # Grand Marshal's War Staff
                {"id": 29130, "phase3": False},   # Auchenai Staff
                {"id": 29355, "phase3": False},   # Terokk's Shadowstaff
                {"id": 29988, "phase3": False},   # The Nexus Key
                {"id": 32055, "phase3": False},   # Merciless Gladiator's War Staff
                {"id": 32374, "phase3": True},   # Zhar'doom, Greatstaff of the Devourer
                {"id": 33766, "phase3": True},   # Vengeful Gladiator's War Staff
                {"id": 34540, "phase3": True},   # Vengeful Gladiator's Battle Staff
            ],
            "main_hand": [
                {"id": 23554, "phase3": False},   # Eternium Runed Blade
                {"id": 27543, "phase3": False},   # Starlight Dagger
                {"id": 27937, "phase3": False},   # Sky Breaker
                {"id": 28297, "phase3": False},   # Gladiator's Spellblade
                {"id": 28770, "phase3": False},   # Nathrezim Mindblade
                {"id": 30787, "phase3": False},   # Illidari-Bane Mageblade
                {"id": 30832, "phase3": False},   # Gavel of Unearthed Secrets
                {"id": 32053, "phase3": False},   # Merciless Gladiator's Spellblade
                {"id": 32237, "phase3": True},   # The Maelstrom's Fury
                {"id": 33687, "phase3": True},   # Vengeful Gladiator's Gavel
                {"id": 34009, "phase3": True},   # Hammer of Judgement
            ],
            "off_hand": [
                {"id": 25099, "phase3": False},   # Draenei Crystal Rod
                {"id": 28187, "phase3": False},   # Star-Heart Lamp
                {"id": 28412, "phase3": False},   # Lamp of Peaceful Radiance
                {"id": 28603, "phase3": False},   # Talisman of Nightbane
                {"id": 28734, "phase3": False},   # Jewel of Infinite Possibilities
                {"id": 28781, "phase3": False},   # Karaborian Talisman
                {"id": 29272, "phase3": False},   # Orb of the Soul-Eater
                {"id": 29273, "phase3": False},   # Khadgar's Knapsack
                {"id": 29330, "phase3": False},   # The Saga of Terokk
                {"id": 30049, "phase3": False},   # Fathomstone
                {"id": 30872, "phase3": True},   # Chronicle of Dark Secrets
                {"id": 31978, "phase3": False},   # Merciless Gladiator's Endgame
                {"id": 32361, "phase3": True},   # Blind-Seers Icon
                {"id": 32533, "phase3": False},   # Karrog's Shard
                {"id": 32651, "phase3": False},   # Crystal Orb of Enlightenment
            ],
        },
        # THE TRINKET POOL, the eleventh enumerative trinket round and
        # the fourth caster round, in the shape the Affliction round set:
        # every max-level trinket the Shad tab's Trinket ladder ranks,
        # with anything from Karazhan and the badge vendor onward
        # acceptable, and the runner generates every unordered pair
        # itself. The ladder ranks fifteen; eight are out on the standing
        # exclusions, all availability rather than routing: Mark of the
        # Champion and The Restrained Essence of Sapphiron drop in
        # Naxxramas and Neltharion's Tear in Blackwing Lair, level-60
        # raids all three; Arcanist's Stone and Shiffar's Nexus-Horn drop
        # in five-man dungeons below Karazhan; the Dark Iron Smoking Pipe
        # drops from a holiday boss inside Blackrock Depths, a level-60
        # five-man; and the Ancient Crystal Talisman is a Zangarmarsh
        # leveling quest reward, not a max-level item. Quagmirran's Eye
        # drops in a five-man below Karazhan and entered both warlock
        # rounds as a WORN trinket over that exclusion, but no shadow
        # priest anchor wears it, so the override does not trigger here
        # and the standing exclusion holds. Starkiller's Bauble stays in
        # as a max-level Netherstorm quest reward, per the Retribution
        # precedent for Core of Ar'kelos. The worn pairs are all
        # tab-ranked: entry and tier wear Darkmoon Card: Crusade beside
        # the Icon of the Silver Crescent and best in slot wears The
        # Skull of Gul'dan beside the Card, so the worn-trinket override
        # admits nothing, the first caster round where it has nothing to
        # do. The priest's own Ashtongue Talisman of Acumen, id 32490, is
        # NOT in the pool, because the tab does not rank it and the pool
        # is the ladder, the same call the Affliction round made for the
        # warlock's Ashtongue Talisman of Shadows. No Ahn'Qiraj and no
        # world-boss trinket is on the tab. Darkmoon Card: Crusade
        # carries no worn stats per items.csv, so everything its rows
        # measure is the simulator's pricing of its stacking proc, which
        # the earlier caster rounds measured behaviorally against the
        # vendored binary; a diagnostic on 20 August 2026 repeated the
        # test for this spec, each candidate beside the worn Card against
        # the Card beside an EMPTY slot, same seed, best-in-slot anchor:
        # the figures are in sim-results.yaml under
        # the_shadow_priest_trinket_round_is_enumerated. The recovered
        # source checkout is stale against the vendored binary and is not
        # evidence about what the binary implements; every claim above is
        # a behavioral measurement of the binary. `phase3` marks what the
        # entry anchor cannot reach: The Skull of Gul'dan drops from
        # Illidan Stormrage in Black Temple.
        "trinket_pool": [
            {"id": 32483, "phase3": True},   # The Skull of Gul'dan
            {"id": 31856, "phase3": False},  # Darkmoon Card: Crusade
            {"id": 28789, "phase3": False},  # Eye of Magtheridon
            {"id": 29370, "phase3": False},  # Icon of the Silver Crescent
            {"id": 30626, "phase3": False},  # Sextant of Unstable Currents
            {"id": 29132, "phase3": False},  # Scryer's Bloodgem
            {"id": 30340, "phase3": False},  # Starkiller's Bauble
            # The class talisman from the Ashtongue Deathsworn, a
            # reputation purchase contesting nothing, in the pool by
            # ruling even where the ladder is silent.
            {"id": 32490, "phase3": True},   # Ashtongue Tal. of Acumen
        ],
        "trinkets_why": (
            (
            "The candidates are every max-level trinket on the EP "
            "Workbook's Trinket ladder for this spec, from "
            "Magtheridon's Lair, the raids above it, the badge vendor, "
            "the Darkmoon Faire, one reputation and one max-level "
            "quest, and every pair from that pool was measured, so the "
            "table is an enumeration rather than a selection. The "
            "Skull of Gul'dan's haste burst meets the casting rotation "
            "on that schedule. Darkmoon Card: Crusade "
            "carries no worn statistics, so everything its rows "
            "measure is the simulator's pricing of its stacking proc. "
            "Eye of Magtheridon procs when a spell is resisted, so its "
            "rows price its worn spell damage and a proc a hit-capped "
            "set rarely triggers.")),
    },
    # BALANCE DRUID: both styles in the same table, per the 20 August 2026
    # ruling in data/judgments/weapon-styles.yaml, in the shape the
    # Affliction round set as the caster template. The candidates are the
    # top of the Owl workbook tab, whose weapon ladders are One Hand, Off
    # Hand and Two Hand, plus a Main Hand header the tab leaves without
    # rows; its Two Hand ladder begins at rank three, Zhar'doom, with no
    # rank one or two row in the capture. A druid wields maces, staves,
    # daggers and fist weapons and holds any frill, and CANNOT WIELD
    # SWORDS, so Tempest of Chaos is not a row: its exclusion is
    # proficiency rather than routing, and the tab agrees, its One Hand
    # ladder holds no sword. The ladder's rank one and rank two, the
    # Vengeful Gladiator's Gavel and Spellblade, carry identical
    # statistics per items.csv, a mace and a dagger at the same figures,
    # so the Gavel row stands for both. The rank-one frill for THIS spec
    # is the Chronicle of Dark Secrets, 80.76 to the Blind-Seers Icon's
    # 76.88, the same order as the warlock tabs and the reverse of the
    # Shadow Priest's. The Vengeful Gladiator's War Staff is a row
    # beside the Battle Staff, which
    # carries the same statistics plus 28 spell hit.
    # SOCKETS: no candidate carries a socket, per items.csv; the tab's
    # one socketed weapon, Talon of the Tempest, is One Hand rank seven,
    # below the cut. STONES, OILS AND ENCHANT: Brilliant Wizard Oil on
    # the main hand at every anchor, per the druid's picks in
    # consumable-ids.yaml, no frill imbue, and the main-hand slot's
    # Sunfire inherited by every row, staff included. The worn
    # combinations are rows on purpose: their variants must reproduce the
    # anchor figures to the digit, the entry AND tier anchors wearing The
    # Nexus Key alone and the best-in-slot anchor wearing Zhar'doom with
    # its empty off hand. This round runs the three standard anchors
    # only; the capture's alternative tier states holding the Tier 5
    # four-piece are not anchors here.
    "balance_druid": {
        "why": (
            (
            "A Balance Druid can carry a staff or a one-hander with a "
            "held frill, and both styles run in the same table, so a "
            "row below is either a single staff with the off hand empty "
            "or a main hand with an off-hand frill that is not a "
            "weapon. Each row is THIS PROFILE with only the weapon "
            "slots changed: the main hand keeps its Sunfire, which a "
            "staff row inherits because the enchant belongs to the "
            "slot. The Brilliant Wizard Oil applies to any "
            "weapon, staff and mace alike, and a frill takes no imbue, "
            "so nothing about the consumables varies across the rows. "
            "The table is an enumeration of the EP Workbook's Two Hand, "
            "One Hand and Off Hand ladders for this spec together with "
            "every worn and routed weapon, and no "
            "candidate carries a socket. A druid wields maces, staves, "
            "daggers and fist weapons and holds any frill, and cannot "
            "wield swords, so Tempest of Chaos, the sword the warlock "
            "and mage rounds price, is not a row here: the warlocks "
            "hold it in principle and concede it to the Arcane Mage, "
            "where this spec cannot equip it at all, so its one-hand "
            "rows draw on maces and daggers instead. Zhar'doom goes to "
            "the warlocks, the Balance Druid, the Elemental Shaman and "
            "the Shadow Priest, and its wearers hold no off hand, which "
            "is why the best-in-slot anchor wears it with the off-hand "
            "slot empty.")),
        # balance_druid: derived by tools/derive_weapon_fields.py
        "weapon_field": {
            "styles": ["two_hand", "main_hand_off_hand"],
            "two_hand": [
                {"id": 24557, "phase3": False},   # Gladiator's War Staff
                {"id": 27842, "phase3": False},   # Grand Scepter of the Nexus-Kings
                {"id": 28341, "phase3": False},   # Warpstaff of Arcanum
                {"id": 28633, "phase3": False},   # Staff of Infinite Mysteries
                {"id": 28935, "phase3": False},   # High Warlord's War Staff
                {"id": 28959, "phase3": False},   # Grand Marshal's War Staff
                {"id": 29130, "phase3": False},   # Auchenai Staff
                {"id": 29355, "phase3": False},   # Terokk's Shadowstaff
                {"id": 29988, "phase3": False},   # The Nexus Key
                {"id": 32055, "phase3": False},   # Merciless Gladiator's War Staff
                {"id": 32374, "phase3": True},   # Zhar'doom, Greatstaff of the Devourer
                {"id": 32854, "phase3": False},   # Hammer of Righteous Might
                {"id": 33766, "phase3": True},   # Vengeful Gladiator's War Staff
                {"id": 34540, "phase3": True},   # Vengeful Gladiator's Battle Staff
            ],
            "main_hand": [
                {"id": 23554, "phase3": False},   # Eternium Runed Blade
                {"id": 27543, "phase3": False},   # Starlight Dagger
                {"id": 28297, "phase3": False},   # Gladiator's Spellblade
                {"id": 28770, "phase3": False},   # Nathrezim Mindblade
                {"id": 28931, "phase3": False},   # High Warlord's Spellblade
                {"id": 30787, "phase3": False},   # Illidari-Bane Mageblade
                {"id": 30832, "phase3": False},   # Gavel of Unearthed Secrets
                {"id": 32053, "phase3": False},   # Merciless Gladiator's Spellblade
                {"id": 32237, "phase3": True},   # The Maelstrom's Fury
                {"id": 33687, "phase3": True},   # Vengeful Gladiator's Gavel
                {"id": 34009, "phase3": True},   # Hammer of Judgement
            ],
            "off_hand": [
                {"id": 25099, "phase3": False},   # Draenei Crystal Rod
                {"id": 28187, "phase3": False},   # Star-Heart Lamp
                {"id": 28260, "phase3": False},   # Manual of the Nethermancer
                {"id": 28412, "phase3": False},   # Lamp of Peaceful Radiance
                {"id": 28603, "phase3": False},   # Talisman of Nightbane
                {"id": 28734, "phase3": False},   # Jewel of Infinite Possibilities
                {"id": 28781, "phase3": False},   # Karaborian Talisman
                {"id": 29273, "phase3": False},   # Khadgar's Knapsack
                {"id": 30049, "phase3": False},   # Fathomstone
                {"id": 30872, "phase3": True},   # Chronicle of Dark Secrets
                {"id": 31978, "phase3": False},   # Merciless Gladiator's Endgame
                {"id": 32361, "phase3": True},   # Blind-Seers Icon
                {"id": 32533, "phase3": False},   # Karrog's Shard
                {"id": 32651, "phase3": False},   # Crystal Orb of Enlightenment
            ],
        },
        # THE TRINKET POOL, the twelfth enumerative trinket round and
        # the fifth caster round, in the shape the Affliction round set:
        # every max-level trinket the Owl tab's Trinket ladder ranks,
        # with anything from Karazhan and the badge vendor onward
        # acceptable, and the runner generates every unordered pair
        # itself. The ladder ranks fifteen; six are out on the standing
        # exclusions, all availability rather than routing: Mark of the
        # Champion and The Restrained Essence of Sapphiron drop in
        # Naxxramas and Neltharion's Tear in Blackwing Lair, level-60
        # raids all three; Arcanist's Stone and Shiffar's Nexus-Horn
        # drop in five-man dungeons below Karazhan; and the Dark Iron
        # Smoking Pipe drops from a holiday boss inside Blackrock
        # Depths, a level-60 five-man. Quagmirran's Eye drops in a
        # five-man below Karazhan, but the entry AND tier anchors WEAR
        # it, so the worn-trinket override that admitted it to both
        # warlock rounds admits it here too. Starkiller's Bauble stays
        # in as a max-level Netherstorm quest reward, per the
        # Retribution precedent for Core of Ar'kelos. The best-in-slot
        # anchor wears the Ashtongue Talisman of Equilibrium, id 32486,
        # class-locked to druids and NOT on the tab, and this is the
        # first round where the worn-trinket override meets the
        # Ashtongue precedent: the Affliction and Shadow Priest rounds
        # kept their class's Ashtongue Talisman OUT because the tab
        # does not rank it, but neither spec WORE it, where this spec's
        # best-in-slot capture does, so the worn override admits it.
        # FLAGGED OPEN FOR THE COUNCIL in sim-results.yaml. No
        # Ahn'Qiraj and no world-boss trinket is on the tab. Darkmoon
        # Card: Crusade carries no worn stats per items.csv, so
        # everything its rows measure is the simulator's pricing of its
        # stacking proc; a diagnostic on 20 August 2026 repeated the
        # behavioral partner-versus-empty test for this spec, each
        # candidate beside a fixed partner against the partner beside
        # an EMPTY slot, same seed, best-in-slot anchor: the figures
        # are in sim-results.yaml under
        # the_balance_druid_trinket_round_is_enumerated. The recovered
        # source checkout is stale against the vendored binary and is
        # not evidence about what the binary implements; every claim
        # above is a behavioral measurement of the binary. `phase3`
        # marks what the entry anchor cannot reach: The Skull of
        # Gul'dan drops from Illidan Stormrage in Black Temple, and the
        # Ashtongue Talisman of Equilibrium requires Exalted with the
        # Ashtongue Deathsworn, a Black Temple reputation.
        "trinket_pool": [
            {"id": 32483, "phase3": True},   # The Skull of Gul'dan
            {"id": 30626, "phase3": False},  # Sextant of Unstable Currents
            {"id": 31856, "phase3": False},  # Darkmoon Card: Crusade
            {"id": 28789, "phase3": False},  # Eye of Magtheridon
            {"id": 27683, "phase3": False},  # Quagmirran's Eye
            {"id": 29370, "phase3": False},  # Icon of the Silver Crescent
            {"id": 29132, "phase3": False},  # Scryer's Bloodgem
            {"id": 30340, "phase3": False},  # Starkiller's Bauble
            {"id": 29179, "phase3": False},  # Xi'ri's Gift
            {"id": 32486, "phase3": True},   # Ashtongue Talisman of Equilibrium
        ],
        "trinkets_why": (
            (
            "The candidates are every max-level trinket on the EP "
            "Workbook's Trinket ladder for this spec, from "
            "Magtheridon's Lair, the raids above it, the badge vendor, "
            "the Darkmoon Faire, three reputations and one max-level "
            "quest, plus the dungeon trinket the entry and tier sets "
            "already wear, and every pair from that pool was measured, "
            "so the table is an enumeration rather than a selection. "
            "The Ashtongue Talisman of Equilibrium is in the "
            "pool because the best-in-slot set wears it: it is locked "
            "to this class, and what its rows measure beyond an empty "
            "slot is the simulator's pricing of its Starfire proc. "
            "The Skull of Gul'dan's haste burst "
            "meets the casting rotation on that schedule. Darkmoon Card: Crusade "
            "carries no worn statistics, so everything its rows "
            "measure is the simulator's pricing of its stacking proc. "
            "Eye of Magtheridon procs when a spell is resisted, so "
            "what its rows price beyond its worn spell damage moves "
            "with each anchor's distance from the hit target.")),
    },
    # ELEMENTAL SHAMAN: both styles in the same table, per the 20 August
    # 2026 ruling in data/judgments/weapon-styles.yaml, in the caster
    # template's shape. The field is the Ele tab's One Hand, Off Hand
    # and Two Hand ladders plus every worn and routed weapon; the tab has
    # no Main Hand section. A shaman wields maces, axes, staves, daggers
    # and fist weapons and CANNOT WIELD SWORDS, so Tempest of Chaos is
    # not a row: its exclusion is proficiency rather than routing. The
    # Illidari-Bane Mageblade and the Eternium Runed Blade, which the tab
    # ranks low, are daggers per items.csv, so both are rows.
    # The One Hand ladder's rank one is The Maelstrom's Fury;
    # ranks two and three, the Vengeful Gladiator's Gavel and
    # Spellblade, carry identical statistics per items.csv, a mace and a
    # dagger at the same figures, so the Gavel row stands for both. The
    # rank-one off hand for this spec is the Chronicle of Dark Secrets
    # at 69.20, and the rank TWO is Antonidas's Aegis of Rapt
    # Concentration at 63.40, which is a SHIELD per items.csv: a shaman
    # is the one Zhar'doom wearer that can legally carry a shield in the
    # off hand, so a shield row runs where every other caster round
    # holds frills alone. The worn Fathomstone is rank three at 57.42
    # and the Blind-Seers Icon rank four at 54.80. The Vengeful
    # Gladiator's War Staff is a row beside the Battle Staff, which
    # carries the same statistics
    # plus 28 spell hit. SOCKETS: no candidate carries a
    # socket, per items.csv; the tab's one socketed weapon, Talon of the
    # Tempest, is One Hand rank seven, below the cut. OILS AND ENCHANT:
    # Brilliant Wizard Oil on the main hand at every anchor, per the
    # shaman's picks in consumable-ids.yaml, no imbue on a frill or a
    # shield, and the main-hand slot's Major Spellpower inherited by
    # every row. The runner's class options send shieldProcrate 0 for
    # this spec, the shipped preset's own value, so no row moves on it.
    # The worn combinations are rows on purpose: their variants must
    # reproduce the anchor figures to the digit, the entry AND tier
    # anchors wearing the Merciless Gladiator's Spellblade with the
    # Fathomstone and the best-in-slot anchor wearing Zhar'doom with its
    # empty off hand, per the routing in weapon-routing.yaml.
    "elemental_shaman": {
        "why": (
            (
            "An Elemental Shaman can carry a staff or a one-hander with "
            "a held off hand, and both styles run in the same table, so "
            "a row below is either a single staff with the off hand "
            "empty or a main hand with an off-hand item that is not a "
            "weapon. Each row is THIS PROFILE with only the weapon "
            "slots changed: the main hand keeps its Major Spellpower, "
            "which a staff row inherits because the enchant belongs to "
            "the slot. The Brilliant Wizard Oil applies to any "
            "weapon, staff and mace alike, and a frill or a shield "
            "takes no imbue, so nothing about the consumables varies "
            "across the rows. The table is an enumeration of the EP "
            "Workbook's Two Hand, One Hand and Off Hand ladders for "
            "this spec together with every worn and routed weapon, and "
            "no candidate carries a socket. A shaman "
            "wields maces, axes, staves, daggers and fist weapons and "
            "cannot wield swords, so Tempest of Chaos, the sword the "
            "warlock and mage rounds price, is not a row here. A shaman "
            "can also carry a shield in the off hand, alone among the "
            "five Zhar'doom wearers, and the workbook's rank-two off "
            "hand for this spec, Antonidas's Aegis of Rapt "
            "Concentration from Archimonde, is a shield, so one row "
            "prices it against the held frills. Zhar'doom goes to the "
            "warlocks, the Balance Druid, the Elemental Shaman and the "
            "Shadow Priest, and its wearers hold no off hand, which is "
            "why the best-in-slot anchor wears it with the off-hand "
            "slot empty.")),
        # elemental_shaman: derived by tools/derive_weapon_fields.py
        "weapon_field": {
            "styles": ["two_hand", "main_hand_off_hand"],
            "two_hand": [
                {"id": 24557, "phase3": False},   # Gladiator's War Staff
                {"id": 28341, "phase3": False},   # Warpstaff of Arcanum
                {"id": 28633, "phase3": False},   # Staff of Infinite Mysteries
                {"id": 28935, "phase3": False},   # High Warlord's War Staff
                {"id": 28959, "phase3": False},   # Grand Marshal's War Staff
                {"id": 29130, "phase3": False},   # Auchenai Staff
                {"id": 29355, "phase3": False},   # Terokk's Shadowstaff
                {"id": 29988, "phase3": False},   # The Nexus Key
                {"id": 31308, "phase3": False},   # The Bringer of Death
                {"id": 32055, "phase3": False},   # Merciless Gladiator's War Staff
                {"id": 32374, "phase3": True},   # Zhar'doom, Greatstaff of the Devourer
                {"id": 32854, "phase3": False},   # Hammer of Righteous Might
                {"id": 33766, "phase3": True},   # Vengeful Gladiator's War Staff
                {"id": 34540, "phase3": True},   # Vengeful Gladiator's Battle Staff
            ],
            "main_hand": [
                {"id": 23554, "phase3": False},   # Eternium Runed Blade
                {"id": 27741, "phase3": False},   # Bleeding Hollow Warhammer
                {"id": 27868, "phase3": False},   # Runesong Dagger
                {"id": 28297, "phase3": False},   # Gladiator's Spellblade
                {"id": 28770, "phase3": False},   # Nathrezim Mindblade
                {"id": 30787, "phase3": False},   # Illidari-Bane Mageblade
                {"id": 30832, "phase3": False},   # Gavel of Unearthed Secrets
                {"id": 32053, "phase3": False},   # Merciless Gladiator's Spellblade
                {"id": 32237, "phase3": True},   # The Maelstrom's Fury
                {"id": 33687, "phase3": True},   # Vengeful Gladiator's Gavel
                {"id": 34009, "phase3": True},   # Hammer of Judgement
            ],
            "off_hand": [
                {"id": 25099, "phase3": False},   # Draenei Crystal Rod
                {"id": 28260, "phase3": False},   # Manual of the Nethermancer
                {"id": 28412, "phase3": False},   # Lamp of Peaceful Radiance
                {"id": 28603, "phase3": False},   # Talisman of Nightbane
                {"id": 28781, "phase3": False},   # Karaborian Talisman
                {"id": 29268, "phase3": False},   # Mazthoril Honor Shield
                {"id": 29273, "phase3": False},   # Khadgar's Knapsack
                {"id": 30049, "phase3": False},   # Fathomstone
                {"id": 30872, "phase3": True},   # Chronicle of Dark Secrets
                {"id": 30909, "phase3": True},   # Antonidas's Aegis of Rapt Concentration
                {"id": 31287, "phase3": False},   # Draenei Honor Guard Shield
                {"id": 32361, "phase3": True},   # Blind-Seers Icon
                {"id": 32533, "phase3": False},   # Karrog's Shard
                {"id": 34011, "phase3": True},   # Illidari Runeshield
            ],
        },
        # THE TRINKET POOL, the thirteenth and LAST enumerative trinket
        # round and the sixth caster round, in the shape the Affliction
        # round set: every max-level trinket the Ele tab's Trinket
        # ladder ranks, with anything from Karazhan and the badge
        # vendor onward acceptable, and the runner generates every
        # unordered pair itself. The ladder ranks fifteen; nine are out
        # on the standing exclusions, all availability rather than
        # routing: Mark of the Champion and The Restrained Essence of
        # Sapphiron drop in Naxxramas and Neltharion's Tear in
        # Blackwing Lair, level-60 raids all three; Arcanist's Stone
        # and Shiffar's Nexus-Horn drop in five-man dungeons below
        # Karazhan; the Dark Iron Smoking Pipe drops from a holiday
        # boss inside Blackrock Depths, a level-60 five-man; the
        # Ancient Crystal Talisman and Vengeance of the Illidari are
        # leveling quest rewards; and Quagmirran's Eye drops in a
        # five-man below Karazhan and, unlike in the warlock and
        # Balance rounds, NO anchor of this spec wears it, so the worn
        # override does not fire for it and it stays out. The override
        # fires instead for The Lightning Capacitor, id 28785, a
        # Karazhan drop the tab does not rank at all: every one of the
        # three anchors wears it, entry and tier beside the Icon of
        # the Silver Crescent and best in slot beside The Skull of
        # Gul'dan, so a pool without it could not reproduce ANY worn
        # pair. The Ashtongue Talisman of Vision, this class's
        # talisman, is NOT on the tab and NO anchor wears it, so it
        # stays out, per the Affliction and Shadow Priest precedent.
        # No Ahn'Qiraj and no world-boss trinket is on the tab.
        # Darkmoon Card: Crusade carries no worn stats per items.csv,
        # so everything its rows measure is the simulator's pricing of
        # its stacking proc; a diagnostic on 20 August 2026 repeated
        # the behavioral partner-versus-empty test for this spec, each
        # candidate beside a fixed partner against the partner beside
        # an EMPTY slot, same seed, best-in-slot anchor: the figures
        # are in sim-results.yaml under
        # the_elemental_shaman_trinket_round_is_enumerated. The
        # recovered source checkout is stale against the vendored
        # binary and is not evidence about what the binary implements;
        # every claim above is a behavioral measurement of the binary.
        # `phase3` marks what the entry anchor cannot reach: The Skull
        # of Gul'dan drops from Illidan Stormrage in Black Temple.
        "trinket_pool": [
            {"id": 32483, "phase3": True},   # The Skull of Gul'dan
            {"id": 30626, "phase3": False},  # Sextant of Unstable Currents
            {"id": 31856, "phase3": False},  # Darkmoon Card: Crusade
            {"id": 28789, "phase3": False},  # Eye of Magtheridon
            {"id": 29370, "phase3": False},  # Icon of the Silver Crescent
            {"id": 29179, "phase3": False},  # Xi'ri's Gift
            {"id": 28785, "phase3": False},  # The Lightning Capacitor
            # The class talisman from the Ashtongue Deathsworn, a
            # reputation purchase contesting nothing, in the pool by
            # ruling even where the ladder is silent.
            {"id": 32491, "phase3": True},   # Ashtongue Tal. of Vision
        ],
        "trinkets_why": (
            (
            "The candidates are every max-level trinket on the EP "
            "Workbook's Trinket ladder for this spec, from "
            "Magtheridon's Lair, the raids above it, the badge vendor, "
            "the Darkmoon Faire and one reputation, plus The Lightning "
            "Capacitor, which the ladder does not rank and which "
            "every one of the three sets wears, and every pair from "
            "that pool was measured, so the table is an enumeration "
            "rather than a selection. What The Lightning Capacitor "
            "is worth beyond an empty slot is entirely the "
            "simulator's pricing of its charge-and-discharge proc, "
            "because it carries no worn statistics, and the same "
            "holds for Darkmoon Card: Crusade and its stacking proc. "
            "The Skull of Gul'dan's haste "
            "burst meets the casting rotation on that schedule. Eye of Magtheridon "
            "procs when a spell is resisted, so what its rows price "
            "beyond its worn spell damage moves with each anchor's "
            "distance from the hit target.")),
    },
}


def with_trinkets(gear: dict, a: int, b: int) -> dict:
    """The gear wearing one trinket combination.

    RULED BY THE GUILD LEAD ON 20 AUGUST 2026: the trinket rounds are
    ENUMERATIVE, every unordered pair from the spec's pool, so the pairs are
    generated from the pool rather than listed by hand and a rerun is always
    exhaustive. A trinket carries no enchant and no socket, so the slots are
    simply replaced, and which of the two sits in which slot does not matter
    to the simulator.
    """
    out = {"items": [dict(entry) for entry in gear["items"]]}
    for slot, item_id in (("trinket_1", a), ("trinket_2", b)):
        out["items"][SLOT_ORDER.index(slot)] = {"id": item_id}
    return out


def with_ranged(gear: dict, item_id: int) -> dict:
    """The gear wearing one ranged candidate, the slot keeping its scope.

    RULED BY THE GUILD LEAD ON 20 AUGUST 2026: the hunters get a special pass
    for the ranged slot, "they hit with their bows", because the bow is the
    one hunter weapon that is not a stat stick. The same variant rules as
    with_pair: the enchant, which for this slot is the scope, stays with the
    slot, and a candidate arrives ungemmed unless it IS the worn item, whose
    row exists to reproduce the anchor figure.
    """
    out = {"items": [dict(entry) for entry in gear["items"]]}
    index = SLOT_ORDER.index("ranged")
    entry = dict(out["items"][index])
    if entry.get("id") != item_id:
        entry.pop("gems", None)
    entry["id"] = item_id
    out["items"][index] = entry
    return out


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


def enumerate_pairs(round_: dict, anchor: str, speed_of) -> list[dict]:
    """The combinations one anchor runs, generated from the spec's field.

    RULED BY THE GUILD LEAD ON 20 AUGUST 2026: the weapon rounds are
    ENUMERATIVE, so the rows are generated from the spec's `weapon_field`
    under its ruled styles rather than listed by hand, and a rerun is
    always exhaustive. Style two_hand runs each two-hander alone with the
    off hand EMPTY. Styles dual_wield and main_hand_off_hand run every
    ORDERED main-hand and off-hand pairing: a One Hand weapon sits in both
    lists, so BOTH orders run, because the off-hand swing penalty makes
    the order a real question, and a pair of two copies of one id arises
    ONCE, from a One Hand weapon alone. With `matched_speed`, which is
    Enhancement's rule, only pairs whose two speeds are EQUAL run, and
    each row carries the shared speed. The entry anchor drops every
    candidate marked `phase3`. A spec still carrying a hand-curated
    `pairs` list runs it unchanged.
    """
    field = round_.get("weapon_field")
    if field is None:
        return [dict(pair) for pair in round_["pairs"]
                if not (anchor == "entry" and pair["phase3"])]

    def kept(candidates: list[dict]) -> list[dict]:
        return [c for c in candidates
                if not (anchor == "entry" and c["phase3"])]

    rows: list[dict] = []
    if "two_hand" in field["styles"]:
        for cand in kept(field.get("two_hand") or []):
            rows.append({"mh": cand["id"], "oh": None})
    if {"dual_wield", "main_hand_off_hand"} & set(field["styles"]):
        for mh in kept(field.get("main_hand") or []):
            for oh in kept(field.get("off_hand") or []):
                row = {"mh": mh["id"], "oh": oh["id"]}
                if field.get("matched_speed"):
                    a, b = speed_of(mh["id"]), speed_of(oh["id"])
                    if a is None or a != b:
                        continue
                    row["speed"] = a
                rows.append(row)
    return rows


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

    def speed_of(item_id: int) -> float | None:
        row = rows_by_id.get(item_id) or {}
        if row.get("weapon_speed"):
            return float(row["weapon_speed"])
        return None

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
        # THE SCALE OF THE ROUND, printed before it runs, so the log says
        # up front how many combinations the long run will take.
        if round_.get("weapon_field"):
            field = round_["weapon_field"]
            sizes = ", ".join(
                f"{key} {len(field.get(key) or [])}"
                for key in ("two_hand", "main_hand", "off_hand"))
            counts = ", ".join(
                f"{anchor} {len(enumerate_pairs(round_, anchor, speed_of))}"
                for anchor in round_.get("anchors", ANCHORS))
            print(f"{spec}: field {sizes}; combinations {counts}")
        anchors: dict[str, list[dict]] = {}
        for anchor in round_.get("anchors", ANCHORS):
            path = args.gear / f"{stem}.{anchor}.gear.json"
            if not path.is_file():
                print(f"error: no profile at {path}. Run `just regen` first.",
                      file=sys.stderr)
                return 1
            gear = json.loads(path.read_text())
            results = []
            for pair in enumerate_pairs(round_, anchor, speed_of):
                oh = pair.get("oh")
                label = names.get(pair["mh"], str(pair["mh"])) + (
                    f" + {names.get(oh, oh)}" if oh else ", two-hander")
                dps, stdev, error = run(args.cli, build_request(
                    spec, with_pair(gear, pair["mh"], oh), talents,
                    args.iterations, args.seed, buffs, party_of,
                    anchor.replace("-", "_"), args.seconds, args.armor))
                if error:
                    if "No item with id" in error:
                        # THE BINARY'S DATABASE IS THE AUTHORITY, and it is
                        # narrower than the checkout's db.json, which is how a
                        # holiday-boss weapon crashed a four-hour run three
                        # and a half hours in. A row the binary cannot equip
                        # is skipped loudly, never fatal.
                        print(f"  SKIPPED, unknown to the binary: {label}")
                        continue
                    raise SystemExit(f"run_variant_sims.py: {spec}: "
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

        # THE RANGED PASS, for a spec whose registry entry carries one. Same
        # anchors, same variant rules, one slot: the worn row reproduces the
        # anchor figure and every other candidate arrives with the slot's
        # scope and no gems.
        if round_.get("ranged"):
            ranged_anchors: dict[str, list[dict]] = {}
            for anchor in round_.get("anchors", ANCHORS):
                path = args.gear / f"{stem}.{anchor}.gear.json"
                gear = json.loads(path.read_text())
                results = []
                for cand in round_["ranged"]:
                    if anchor == "entry" and cand["phase3"]:
                        continue
                    label = names.get(cand["id"], str(cand["id"]))
                    dps, stdev, error = run(args.cli, build_request(
                        spec, with_ranged(gear, cand["id"]), talents,
                        args.iterations, args.seed, buffs, party_of,
                        anchor.replace("-", "_"), args.seconds, args.armor))
                    if error:
                        if "No item with id" in error:
                            print(f"  SKIPPED, unknown to the binary: {label}")
                            continue
                        raise SystemExit(
                            f"run_variant_sims.py: {spec}: {anchor}: "
                            f"ranged {label}: {error}")
                    results.append({
                        "ranged": weapon(cand["id"]),
                        "dps": round(dps, 1),
                        "standard_error": round(
                            stdev / math.sqrt(args.iterations), 2),
                        "stdev": round(stdev, 1),
                    })
                    total += 1
                    print(f"  {spec:22s} {anchor:20s} "
                          f"{label + ' (ranged)':56s} {dps:9.1f}")
                results.sort(key=lambda row: -row["dps"])
                ranged_anchors[anchor] = results
            specs_out[spec]["ranged_why"] = round_["ranged_why"]
            specs_out[spec]["ranged_anchors"] = ranged_anchors

        # THE TRINKET PASS, enumerative by ruling: every unordered pair from
        # the pool, the entry anchor dropping what Phase 3 supplies, so the
        # table is complete rather than curated and a rerun cannot silently
        # narrow it. The pages show the top ten and the worn pair; the fact
        # file keeps every row.
        if round_.get("trinket_pool"):
            trinket_anchors: dict[str, list[dict]] = {}
            for anchor in round_.get("anchors", ANCHORS):
                path = args.gear / f"{stem}.{anchor}.gear.json"
                gear = json.loads(path.read_text())
                pool = [c for c in round_["trinket_pool"]
                        if not (anchor == "entry" and c["phase3"])]
                results = []
                for one, two in itertools.combinations(pool, 2):
                    label = (f"{names.get(one['id'], one['id'])} + "
                             f"{names.get(two['id'], two['id'])}")
                    dps, stdev, error = run(args.cli, build_request(
                        spec, with_trinkets(gear, one["id"], two["id"]),
                        talents, args.iterations, args.seed, buffs, party_of,
                        anchor.replace("-", "_"), args.seconds, args.armor))
                    if error:
                        if "No item with id" in error:
                            print(f"  SKIPPED, unknown to the binary: {label}")
                            continue
                        raise SystemExit(
                            f"run_variant_sims.py: {spec}: {anchor}: "
                            f"trinkets {label}: {error}")
                    results.append({
                        "trinket_1": weapon(one["id"]),
                        "trinket_2": weapon(two["id"]),
                        "dps": round(dps, 1),
                        "standard_error": round(
                            stdev / math.sqrt(args.iterations), 2),
                        "stdev": round(stdev, 1),
                    })
                    total += 1
                    print(f"  {spec:22s} {anchor:20s} "
                          f"{label:56s} {dps:9.1f}")
                results.sort(key=lambda row: -row["dps"])
                trinket_anchors[anchor] = results
            specs_out[spec]["trinkets_why"] = round_["trinkets_why"]
            specs_out[spec]["trinket_anchors"] = trinket_anchors

        # WRITE AFTER EVERY SPEC, not once at the end. A crash three and a
        # half hours into a run once discarded every finished spec because
        # the document was held in memory; a partial file that carries what
        # ran is strictly better than a clean absence of everything.
        _write_document(args, specs_out)

    # THE FILE KEEPS THE REGISTRY'S ORDER regardless of which spec a --spec
    # run reran, or every partial run reorders the file and its diff reads
    # far larger than it is.
    specs_out = {spec: specs_out[spec] for spec in ROUNDS if spec in specs_out}

    _write_document(args, specs_out)
    total_specs = len(specs_out)
    print(f"{total} variant(s) across {total_specs} spec(s) -> {args.out}")
    return 0


def _write_document(args, specs_out: dict) -> None:
    document = {
        "meta": {
            "what": (
                "Weapon rounds, one per spec in the registry of "
                "tools/run_variant_sims.py, each combination run as a "
                "VARIANT of that spec's anchor profiles: the exported gear "
                "with only the weapon slots changed, a filled slot keeping "
                "its enchant and a two-hander row running the off hand "
                "EMPTY, the anchor's own consumables, buffs and seed held "
                "still. The combinations are ENUMERATED from each spec's "
                "weapon field under its ruled styles rather than curated. "
                "Which styles each spec's table holds is ruled in "
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


if __name__ == "__main__":
    raise SystemExit(main())
