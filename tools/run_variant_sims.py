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
            (
            "An Enhancement Shaman carries a Windfury imbue in each "
            "hand, pairs two weapons of the same speed, and wants them "
            "slow. The set above wears the pair its published source "
            "ranked, so each row below is THIS PROFILE with only the "
            "two weapon ids replaced: the slot keeps its Mongoose, and "
            "the consumables, buffs and seed hold still, so every "
            "figure is directly comparable with the one at the top of "
            "this page. The character is a Draenei, so no row inherits "
            "the Orc axe privilege the published lists assume. The "
            "weapons run unsynced.")),
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
            "A trinket is worth one thing beside an attack power "
            "partner and another beside an armor penetration one, so "
            "the two slots are measured together: every row below is "
            "THIS PROFILE with only the two trinket ids replaced, and "
            "a trinket carries no enchant and no gem, so the "
            "consumables, buffs and seed hold still and every figure "
            "is directly comparable with the one at the top of this "
            "page. The candidates are every max-level trinket on the "
            "EP Workbook's Trinket ladder for this spec, from Gruul's "
            "Lair, the raids above it, the badge vendor, the Darkmoon "
            "Faire, one max-level quest and one reputation, and every "
            "pair from that pool was measured, so the table is an "
            "enumeration rather than a selection; the ten best appear "
            "below, with the worn pair beside them. An on-use trinket "
            "is activated on the simulator's own schedule. The "
            "Ashtongue Talisman of Vision carries no worn statistics, "
            "so everything its rows measure is the simulator's pricing "
            "of its procs. Madness of the Betrayer carries armor "
            "penetration, which moves with the boss's armor, and these "
            "figures are at the armor tier ten of the fourteen bosses "
            "sit in.")),
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
            (
            "A Retribution Paladin always carries a two-hander, so "
            "every row below is a single weapon and the off hand runs "
            "empty. Each row is THIS PROFILE with only the main hand id "
            "replaced: the slot keeps its Mongoose, and the "
            "consumables, buffs and seed hold still, so every figure is "
            "directly comparable with the one at the top of this page. "
            "The candidates are the top of the EP Workbook's Two Hand "
            "ladder for this spec, kept to the weapon classes a paladin "
            "wields. Cataclysm's Edge appears as a measurement only: it "
            "goes to the Arms Warrior, and Torch of the Damned stays "
            "with this spec.")),
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
        ],
        "trinkets_why": (
            (
            "A trinket is worth one thing beside an attack power "
            "partner and another beside an armor penetration one, so "
            "the two slots are measured together: every row below is "
            "THIS PROFILE with only the two trinket ids replaced, and "
            "a trinket carries no enchant and no gem, so the "
            "consumables, buffs and seed hold still and every figure "
            "is directly comparable with the one at the top of this "
            "page. The candidates are every max-level trinket on the "
            "EP Workbook's Trinket ladder for this spec, from Karazhan, "
            "the raids above it, the badge vendor and one max-level "
            "quest, and every pair from that pool was measured, so the "
            "table is an enumeration rather than a selection; the ten "
            "best appear below, with the worn pair beside them. An "
            "on-use trinket is activated on the simulator's own "
            "schedule. Madness of the Betrayer carries armor "
            "penetration, which moves with the boss's armor, and these "
            "figures are at the armor tier ten of the fourteen bosses "
            "sit in.")),
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
            (
            "A Fury Warrior considers only one-handers and main "
            "handers, so every row below is a main hand with an off "
            "hand and no row is a two-hander. Each row is THIS PROFILE "
            "with only the two weapon ids replaced: each slot keeps its "
            "Mongoose, and the consumables, buffs and seed hold still, "
            "so every figure is directly comparable with the one at the "
            "top of this page. The candidates are the top of the EP "
            "Workbook's Main Hand and Off Hand ladders for this spec, "
            "kept to the weapon classes a warrior dual-wields. A row of "
            "two copies of one item needs both copies before it is "
            "wearable. The Warglaives of Azzinoth are ranked first by "
            "this spec's published Phase 3 list and by the Combat "
            "Rogue's, the raid holds one pair, and which of the two "
            "receives it is open council business, which is why this "
            "spec carries a best-in-slot set both with and without "
            "them.")),
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
            {"id": 30446, "phase3": False},  # Solarian's Sapphire
            {"id": 32505, "phase3": True},   # Madness of the Betrayer
            {"id": 30627, "phase3": False},  # Tsunami Talisman
            {"id": 31856, "phase3": False},  # Darkmoon Card: Crusade
            {"id": 29383, "phase3": False},  # Bloodlust Brooch
            {"id": 29776, "phase3": False},  # Core of Ar'kelos
        ],
        "trinkets_why": (
            (
            "A trinket is worth one thing beside an attack power "
            "partner and another beside an armor penetration one, so "
            "the two slots are measured together: every row below is "
            "THIS PROFILE with only the two trinket ids replaced, and "
            "a trinket carries no enchant and no gem, so the "
            "consumables, buffs and seed hold still and every figure "
            "is directly comparable with the one at the top of this "
            "page. The candidates are every max-level trinket on the "
            "EP Workbook's Trinket ladder for this spec, from Gruul's "
            "Lair, the raids above it, the badge vendor, the Darkmoon "
            "Faire and one max-level quest, and every pair from that "
            "pool was measured, so the table is an enumeration rather "
            "than a selection; the ten best appear below, with the "
            "worn pair beside them. An on-use trinket is activated on "
            "the simulator's own schedule. Solarian's Sapphire "
            "strengthens the wearer's Battle Shout for the whole "
            "party, the simulator prices that effect outside the "
            "trinket slot, and these runs do not engage it, so its "
            "rows price the worn stats alone and understate it. "
            "Madness of the Betrayer carries armor penetration, which "
            "moves with the boss's armor, and these figures are at the "
            "armor tier ten of the fourteen bosses sit in.")),
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
            (
            "A Combat Rogue carries two one-handers, so every row below "
            "is a main hand with an off hand and no row is a two- "
            "hander. Each row is THIS PROFILE with only the two weapon "
            "ids replaced: each slot keeps its Mongoose, and the "
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
            "which is why this spec carries a best-in-slot set both "
            "with and without them.")),
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
            "A trinket is worth one thing beside an attack power "
            "partner and another beside an armor penetration one, so "
            "the two slots are measured together: every row below is "
            "THIS PROFILE with only the two trinket ids replaced, and "
            "a trinket carries no enchant and no gem, so the "
            "consumables, buffs and seed hold still and every figure "
            "is directly comparable with the one at the top of this "
            "page. The candidates are every max-level trinket on the "
            "EP Workbook's Trinket ladder for this spec, from Karazhan, "
            "the raids above it and the badge vendor, and every pair "
            "from that pool was measured, so the table is an "
            "enumeration rather than a selection; the ten best appear "
            "below, with the worn pair beside them. An on-use trinket "
            "is activated on the simulator's own schedule. Warp-Spring "
            "Coil and Madness of the Betrayer carry armor penetration, "
            "which moves with the boss's armor, and these figures are "
            "at the armor tier ten of the fourteen bosses sit in.")),
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
            "the slot keeps its Mongoose, and the consumables, buffs "
            "and seed hold still, so every figure is directly "
            "comparable with the one at the top of this page. The "
            "published Phase 3 page ranks only dual Warglaives, which "
            "this spec will not receive, so the Phase 3 candidates are "
            "the drop table's two-handers in the weapon classes a "
            "warrior wields, and the earlier candidates are the top of "
            "the EP Workbook's Two Hand ladder for this spec. This spec "
            "takes Cataclysm's Edge. Torch of the Damned appears as a "
            "measurement only: it stays with the Retribution Paladin.")),
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
            {"id": 30446, "phase3": False},  # Solarian's Sapphire
            {"id": 32505, "phase3": True},   # Madness of the Betrayer
            {"id": 31856, "phase3": False},  # Darkmoon Card: Crusade
            {"id": 29776, "phase3": False},  # Core of Ar'kelos
        ],
        "trinkets_why": (
            (
            "A trinket is worth one thing beside an attack power "
            "partner and another beside an armor penetration one, so "
            "the two slots are measured together: every row below is "
            "THIS PROFILE with only the two trinket ids replaced, and "
            "a trinket carries no enchant and no gem, so the "
            "consumables, buffs and seed hold still and every figure "
            "is directly comparable with the one at the top of this "
            "page. The candidates are every max-level trinket on the "
            "EP Workbook's Trinket ladder for this spec, from Gruul's "
            "Lair, the raids above it, the badge vendor, the Darkmoon "
            "Faire and one max-level quest, and every pair from that "
            "pool was measured, so the table is an enumeration rather "
            "than a selection; the ten best appear below, with the "
            "worn pair beside them. An on-use trinket is activated on "
            "the simulator's own schedule. Solarian's Sapphire "
            "strengthens the wearer's Battle Shout for the whole "
            "party, the simulator prices that effect outside the "
            "trinket slot, and these runs do not engage it, so its "
            "rows price the worn stats alone and understate it. "
            "Madness of the Betrayer carries armor penetration, which "
            "moves with the boss's armor, and these figures are at the "
            "armor tier ten of the fourteen bosses sit in.")),
    },
    # BEAST MASTERY: both styles in the same table, per the 20 August 2026
    # ruling in data/judgments/weapon-styles.yaml, the first spec to mix
    # them: a dual_wield row is a main hand with an off hand, and a two_hand
    # row runs the off hand empty. The melee slots are stat sticks, the
    # ranged weapon does the damage and is not part of this round, so the
    # candidates are the top of the BM workbook tab's One Hand pool, which
    # is combined like Enhancement's rather than split like Fury's, and its
    # Two Hand ladder, kept to the weapon classes a hunter wields: axes,
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
            "ids replaced: a filled slot keeps its enchant, and the "
            "consumables, buffs and seed hold still, so every figure is "
            "directly comparable with the one at the top of this page. "
            "Holding the consumables still includes the weapon stones, "
            "which the hunters choose by the WORN weapon's class, so a "
            "candidate whose class differs from the worn weapon runs "
            "under the capture's stone rather than its own. The "
            "candidates are the top of the EP Workbook's One Hand and "
            "Two Hand ladders for this spec, kept to the weapon classes "
            "a hunter wields, and the 41/20/0 build carries no weapon "
            "specialization talent, so no class is favored.")),
        "pairs": [
            # DUAL WIELD. The worn best-in-slot pair: Boundless Agony from
            # Azgalor, the capture's Best MH, with Blade of Infamy from
            # Anetheron, its top Best OH row.
            {"mh": 30901, "oh": 30881, "phase3": True},
            # The sword field: Blade of Infamy is the One Hand pool's rank
            # one and is not unique, so its doubled row is a question of
            # weeks; Tracker's Blade from Rage Winterchill is rank two, and
            # Blade of Savagery drops from Mother Shahraz.
            {"mh": 30881, "oh": 30881, "phase3": True},
            {"mh": 30881, "oh": 30865, "phase3": True},
            {"mh": 30881, "oh": 32369, "phase3": True},
            # The Season 3 fist pair, the Right Ripper, Main Hand only,
            # with the Left Ripper, Off Hand only. Fist weapons, so at the
            # best-in-slot anchor this row runs under the worn pair's
            # Sharpening Stone rather than the Weightstone a fist pair
            # would carry.
            {"mh": 33737, "oh": 33705, "phase3": True},
            # Reachable before Phase 3: Talon of the Phoenix from Al'ar
            # with Claw of the Phoenix, also Al'ar, is the worn entry AND
            # tier pair, per the capture in data/facts/sim-profiles/
            # hit-capture/beast-mastery-hunter.yaml; Talon of Azshara from
            # Morogrim Tidewalker is the pool's rank four.
            {"mh": 32944, "oh": 29948, "phase3": False},
            {"mh": 32944, "oh": 30082, "phase3": False},
            # TWO HAND. Phase 3: the Halberd of Desolation from High
            # Warlord Naj'entus is the Two Hand ladder's rank one, and the
            # Vengeful Gladiator's Decapitator is Season 3 arena, tied to
            # the point with the Waraxe, so it stands for both.
            {"mh": 32248, "oh": None, "phase3": True},
            {"mh": 33670, "oh": None, "phase3": True},
            # Reachable before Phase 3: Twinblade of the Phoenix from
            # Kael'thas Sunstrider is the ladder's best reachable epic and
            # carries three sockets, which arrive EMPTY here because no BM
            # anchor wears it, so its figure is understated by the gems a
            # raider would add; Bloodmoon is crafted by Blacksmithing and
            # carries none.
            {"mh": 29993, "oh": None, "phase3": False},
            {"mh": 28436, "oh": None, "phase3": False},
        ],
        "ranged_why": (
            (
            "The bow is the one hunter weapon that is not a stat stick, "
            "so it gets its own pass: each row below is THIS PROFILE "
            "with only the ranged slot changed, the slot keeping its "
            "scope, so every figure is directly comparable with the one "
            "at the top of this page. The candidates are the workbook's "
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
        ],
        "trinkets_why": (
            (
            "A trinket is worth one thing beside a flat attack power "
            "partner and another beside a proc, so the two slots are "
            "measured together: every row below is THIS PROFILE with "
            "only the two trinket ids replaced, and a trinket carries "
            "no enchant and no gem, so the consumables, buffs and seed "
            "hold still and every figure is directly comparable with "
            "the one at the top of this page. The candidates are every "
            "max-level trinket on the EP Workbook's Trinket ladder for "
            "this spec, from Gruul's Lair, the raids above it, the "
            "badge vendor, the Darkmoon Faire and one max-level quest, "
            "and every pair from that pool was measured, so the table "
            "is an enumeration rather than a selection; the ten best "
            "appear below, with the worn pair beside them. An on-use "
            "trinket is activated on the simulator's own schedule. "
            "Talon of Al'ar carries no worn stats, so its rows measure "
            "the simulator's pricing of its proc alone. Madness of the "
            "Betrayer carries armor penetration, which moves with the "
            "boss's armor, and these figures are at the armor tier ten "
            "of the fourteen bosses sit in.")),
    },
    # SURVIVAL: both styles in the same table, per the 20 August 2026 ruling
    # in data/judgments/weapon-styles.yaml, the second spec to mix them: a
    # dual_wield row is a main hand with an off hand, and a two_hand row runs
    # the off hand empty. The melee slots are stat sticks, the ranged weapon
    # does the damage and is not part of this round, so the candidates are
    # the top of the SV workbook tab's One Hand pool, which is combined like
    # the BM and Enhancement tabs rather than split like Fury's, and its Two
    # Hand ladder, kept to the weapon classes a hunter wields. The two-hand
    # field is the same four the BM round ran, so the two hunter tables read
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
            "enchant, and the consumables, buffs and seed hold still, "
            "so every figure is directly comparable with the one at the "
            "top of this page. Holding the consumables still includes "
            "the weapon stones, which the hunters choose by the WORN "
            "weapon's class, so a candidate whose class differs from "
            "the worn weapon runs under the capture's stone rather than "
            "its own. The candidates are the top of the EP Workbook's "
            "One Hand and Two Hand ladders for this spec, kept to the "
            "weapon classes a hunter wields, with the same two-hander "
            "field the Beast Mastery round ran so the two hunter tables "
            "read side by side, and the 7/20/34 build carries no weapon "
            "specialization talent, so no class is favored.")),
        "pairs": [
            # DUAL WIELD. The worn best-in-slot pair: two copies of Blade
            # of Infamy from Anetheron, the capture's 'Best x2' row, per
            # data/facts/sim-profiles/bis-capture/survival-hunter.yaml.
            # Not unique, so two copies is a question of weeks.
            {"mh": 30881, "oh": 30881, "phase3": True},
            # One Blade of Infamy before the second drops, held with each
            # of the worn weapons it would displace: the entry axe
            # Netherbane and the entry fist Claw of the Phoenix, both from
            # Al'ar.
            {"mh": 30881, "oh": 29924, "phase3": True},
            {"mh": 30881, "oh": 29948, "phase3": True},
            # Messenger of Fate from Gurtogg Bloodboil is the One Hand
            # pool's rank three, its only Black Temple one-hander.
            {"mh": 30881, "oh": 32269, "phase3": True},
            # The Season 3 fist pair, the Right Ripper, Main Hand only,
            # with the Left Ripper, Off Hand only. Fist weapons, so at the
            # best-in-slot anchor this row runs under the worn pair's
            # Sharpening Stone rather than the Weightstone a fist pair
            # would carry.
            {"mh": 33737, "oh": 33705, "phase3": True},
            # Reachable before Phase 3: Netherbane with Claw of the
            # Phoenix, both from Al'ar, is the worn entry AND tier pair,
            # per the capture in data/facts/sim-profiles/hit-capture/
            # survival-hunter.yaml; Talon of Azshara from Morogrim
            # Tidewalker is the pool's rank five.
            {"mh": 29924, "oh": 29948, "phase3": False},
            {"mh": 29924, "oh": 30082, "phase3": False},
            # TWO HAND, the same field the BM round ran. Phase 3: the
            # Halberd of Desolation from High Warlord Naj'entus is the Two
            # Hand ladder's rank one, and the Vengeful Gladiator's
            # Decapitator is Season 3 arena, tied to the point with the
            # Waraxe, so it stands for both.
            {"mh": 32248, "oh": None, "phase3": True},
            {"mh": 33670, "oh": None, "phase3": True},
            # Reachable before Phase 3: Twinblade of the Phoenix from
            # Kael'thas Sunstrider carries three sockets, which arrive
            # EMPTY here because no SV anchor wears it, so its figure is
            # understated by the gems a raider would add; Bloodmoon is
            # crafted by Blacksmithing and carries none.
            {"mh": 29993, "oh": None, "phase3": False},
            {"mh": 28436, "oh": None, "phase3": False},
        ],
        "ranged_why": (
            (
            "The bow is the one hunter weapon that is not a stat stick, "
            "so it gets its own pass: each row below is THIS PROFILE "
            "with only the ranged slot changed, the slot keeping its "
            "scope, so every figure is directly comparable with the one "
            "at the top of this page. The candidates are the workbook's "
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
        ],
        "trinkets_why": (
            (
            "A trinket is worth one thing beside a flat attack power "
            "partner and another beside a proc, so the two slots are "
            "measured together: every row below is THIS PROFILE with "
            "only the two trinket ids replaced, and a trinket carries "
            "no enchant and no gem, so the consumables, buffs and seed "
            "hold still and every figure is directly comparable with "
            "the one at the top of this page. The candidates are every "
            "max-level trinket on the EP Workbook's Trinket ladder for "
            "this spec, from Gruul's Lair, the raids above it, the "
            "badge vendor, the Darkmoon Faire, one max-level quest and "
            "one Apexis Crystal charge, and every pair from that pool "
            "was measured, so the table is an enumeration rather than "
            "a selection; the ten best appear below, with the worn "
            "pair beside them. An on-use trinket is activated on the "
            "simulator's own schedule. One stat carries more than its "
            "line for this spec: Expose Weakness scales with this "
            "hunter's own agility, so the on-use agility of Badge of "
            "Tenacity feeds the debuff as well as the wearer, which is "
            "why this spec's ladder is the one melee ladder that ranks "
            "it. Talon of Al'ar carries no worn stats, so its rows "
            "measure the simulator's pricing of its proc alone. "
            "Madness of the Betrayer carries armor penetration, which "
            "moves with the boss's armor, and these figures are at the "
            "armor tier ten of the fourteen bosses sit in.")),
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
    # holds any frill. The pairing is the top main hands against the top
    # frills rather than the full cross product. The Vengeful Gladiator's
    # War Staff is not a row: the Battle Staff carries the same statistics
    # plus 28 spell hit, so it equals or beats the War Staff at every hit
    # state and stands for both. STONES AND OILS: the caster runs Brilliant
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
            "slot, and the consumables, buffs and seed hold still, so "
            "every figure is directly comparable with the one at the "
            "top of this page. The Brilliant Wizard Oil applies to any "
            "weapon, staff and dagger alike, and a frill takes no "
            "imbue, so nothing about the consumables varies across the "
            "rows. The candidates are the top of the EP Workbook's Two "
            "Hand, One Hand and Off Hand ladders for this spec, and no "
            "candidate carries a socket. Zhar'doom goes to the "
            "warlocks, the Balance Druid, the Elemental Shaman and the "
            "Shadow Priest, and its wearers hold no off hand, which is "
            "why the best-in-slot anchor wears it with the off-hand "
            "slot empty. Tempest of Chaos is taken first by the Arcane "
            "Mage, and first is an ordering rather than an exclusion: "
            "the warlocks' lists rank it too, so its rows measure what "
            "this spec holds once the mage is served.")),
        "pairs": [
            # TWO HAND, a staff alone, off hand EMPTY. Zhar'doom,
            # Greatstaff of the Devourer, from Illidan Stormrage, is the
            # worn best-in-slot weapon and the workbook's rank one; the
            # Vengeful Gladiator's Battle Staff is Season 3 arena and
            # stands for both Season 3 staves.
            {"mh": 32374, "oh": None, "phase3": True},
            {"mh": 34540, "oh": None, "phase3": True},
            # Reachable before Phase 3: the Merciless Gladiator's War
            # Staff is Season 2 arena and the workbook's best reachable
            # staff; The Nexus Key drops from Kael'thas Sunstrider.
            {"mh": 32055, "oh": None, "phase3": False},
            {"mh": 29988, "oh": None, "phase3": False},
            # MAIN HAND WITH A HELD FRILL. Tempest of Chaos from
            # Archimonde is the One Hand ladder's rank one, held with
            # each of the top frills: Chronicle of Dark Secrets from Rage
            # Winterchill, Blind-Seers Icon from Shade of Akama, and the
            # worn Jewel of Infinite Possibilities from Netherspite, the
            # state where the sword drops before a Phase 3 frill does.
            {"mh": 30910, "oh": 30872, "phase3": True},
            {"mh": 30910, "oh": 32361, "phase3": True},
            {"mh": 30910, "oh": 28734, "phase3": True},
            # The other Phase 3 main hands, each with the rank one
            # frill: the Vengeful Gladiator's Spellblade is Season 3
            # arena and The Maelstrom's Fury drops from High Warlord
            # Naj'entus.
            {"mh": 33763, "oh": 30872, "phase3": True},
            {"mh": 32237, "oh": 30872, "phase3": True},
            # The worn Merciless Gladiator's Spellblade with the rank one
            # frill, the state where a frill drops before any Phase 3
            # main hand does.
            {"mh": 32053, "oh": 30872, "phase3": True},
            # Reachable before Phase 3: the Merciless Gladiator's
            # Spellblade, Season 2 arena, with the Jewel of Infinite
            # Possibilities from Netherspite is the worn entry AND tier
            # combination, per the capture in data/facts/sim-profiles/
            # hit-capture/affliction-warlock.yaml.
            {"mh": 32053, "oh": 28734, "phase3": False},
        ],
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
        ],
        "trinkets_why": (
            (
            "A trinket is worth one thing beside a steady spell damage "
            "partner and another beside an on-use haste one, so the "
            "two slots are measured together: every row below is THIS "
            "PROFILE with only the two trinket ids replaced, and a "
            "trinket carries no enchant and no gem, so the "
            "consumables, buffs and seed hold still and every figure "
            "is directly comparable with the one at the top of this "
            "page. The candidates are every max-level trinket on the "
            "EP Workbook's Trinket ladder for this spec, from "
            "Magtheridon's Lair, the raids above it, the badge vendor, "
            "the Darkmoon Faire, one reputation, one max-level quest "
            "and the dungeon trinket every anchor wears, and every "
            "pair from that pool was measured, so the table is an "
            "enumeration rather than a selection; the ten best appear "
            "below, with the worn pair beside them. An on-use trinket "
            "is activated on the simulator's own schedule, which is "
            "how The Skull of Gul'dan's haste burst meets the casting "
            "rotation. Darkmoon Card: Crusade carries no worn "
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
    # Vengeful Gladiator's War Staff is not a row for the same reason as
    # in the Affliction round: the Battle Staff carries the same
    # statistics plus 28 spell hit, so it equals or beats the War Staff
    # at every hit state and stands for both. SOCKETS: the only socketed
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
            "slot, and the consumables, buffs and seed hold still, so "
            "every figure is directly comparable with the one at the "
            "top of this page. The Brilliant Wizard Oil applies to any "
            "weapon, staff and dagger alike, and a frill takes no "
            "imbue, so nothing about the consumables varies across the "
            "rows. The candidates are the top of the EP Workbook's Two "
            "Hand, One Hand and Off Hand ladders for this spec, and no "
            "candidate carries a socket. Zhar'doom goes to the "
            "warlocks, the Balance Druid, the Elemental Shaman and the "
            "Shadow Priest, and its wearers hold no off hand, which is "
            "why the best-in-slot anchor wears it with the off-hand "
            "slot empty. Tempest of Chaos is taken first by the Arcane "
            "Mage, and first is an ordering rather than an exclusion: "
            "the warlocks' lists rank it too, so its rows measure what "
            "this spec holds once the mage is served.")),
        "pairs": [
            # TWO HAND, a staff alone, off hand EMPTY. Zhar'doom,
            # Greatstaff of the Devourer, from Illidan Stormrage, is the
            # worn best-in-slot weapon and the workbook's rank one; the
            # Vengeful Gladiator's Battle Staff is Season 3 arena and
            # stands for both Season 3 staves.
            {"mh": 32374, "oh": None, "phase3": True},
            {"mh": 34540, "oh": None, "phase3": True},
            # Reachable before Phase 3: the Merciless Gladiator's War
            # Staff is Season 2 arena and the workbook's best reachable
            # staff; The Nexus Key drops from Kael'thas Sunstrider.
            {"mh": 32055, "oh": None, "phase3": False},
            {"mh": 29988, "oh": None, "phase3": False},
            # MAIN HAND WITH A HELD FRILL. Tempest of Chaos from
            # Archimonde is the One Hand ladder's rank one, held with
            # each of the top frills: Chronicle of Dark Secrets from Rage
            # Winterchill, Blind-Seers Icon from Shade of Akama, and the
            # worn Flametongue Seal from the badge vendor, the state
            # where the sword drops before a Phase 3 frill does.
            {"mh": 30910, "oh": 30872, "phase3": True},
            {"mh": 30910, "oh": 32361, "phase3": True},
            {"mh": 30910, "oh": 29270, "phase3": True},
            # The other Phase 3 main hands, each with the rank one
            # frill: the Vengeful Gladiator's Spellblade is Season 3
            # arena and The Maelstrom's Fury drops from High Warlord
            # Naj'entus.
            {"mh": 33763, "oh": 30872, "phase3": True},
            {"mh": 32237, "oh": 30872, "phase3": True},
            # The worn Merciless Gladiator's Spellblade with the rank one
            # frill, the state where a frill drops before any Phase 3
            # main hand does.
            {"mh": 32053, "oh": 30872, "phase3": True},
            # Reachable before Phase 3: the Merciless Gladiator's
            # Spellblade, Season 2 arena, with the Flametongue Seal from
            # G'eras is the worn entry AND tier combination, per the
            # capture in data/facts/sim-profiles/hit-capture/
            # destruction-warlock.yaml.
            {"mh": 32053, "oh": 29270, "phase3": False},
        ],
    },
    # ARCANE MAGE: both styles in the same table, per the 20 August 2026
    # ruling in data/judgments/weapon-styles.yaml, in the shape the
    # Affliction round set as the caster template. The candidates are the
    # top of the Arc workbook tab, whose weapon ladders are One Hand,
    # Off Hand, Two Hand and Ranged; a mage wields daggers, one-hand
    # swords and staves and holds any frill. ZHAR'DOOM IS NOT A ROW: the
    # guild lead routed it to the warlocks, the Balance Druid, the
    # Elemental Shaman and the Shadow Priest, and ruled that the Arcane
    # Mage takes Tempest of Chaos first, so this spec's best-in-slot set
    # wears the one-hander with a frill and never holds the staff. The
    # rows below therefore price the mage's OWN staff field, Season 3,
    # Season 2 and the worn Nexus Key, against Tempest and the other main
    # hands with the top frills; the warlock rounds measured what other
    # specs lose while the mage holds Tempest, and this round measures
    # what the mage loses if it concedes it. The Vengeful Gladiator's War
    # Staff is not a row for the same reason as in the warlock rounds:
    # the Battle Staff carries the same statistics plus 28 spell hit, so
    # it equals or beats the War Staff at every hit state and stands for
    # both. SOCKETS: no candidate carries a socket, per items.csv.
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
            "slot, and the consumables, buffs and seed hold still, so "
            "every figure is directly comparable with the one at the "
            "top of this page. The Brilliant Wizard Oil applies to any "
            "weapon, staff and sword alike, and a frill takes no imbue, "
            "so nothing about the consumables varies across the rows. "
            "The candidates are the top of the EP Workbook's Two Hand, "
            "One Hand and Off Hand ladders for this spec, and no "
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
        "pairs": [
            # TWO HAND, a staff alone, off hand EMPTY. Zhar'doom is
            # the ladder's rank one and is ROUTED to five other specs;
            # it is measured anyway, because a routing never excludes a
            # candidate. The Vengeful Gladiator's Battle Staff is Season
            # 3 arena and stands for both Season 3 staves.
            {"mh": 32374, "oh": None, "phase3": True},
            {"mh": 34540, "oh": None, "phase3": True},
            # Reachable before Phase 3: The Nexus Key from Kael'thas
            # Sunstrider is the worn entry AND tier weapon, per the
            # capture in data/facts/sim-profiles/hit-capture/
            # arcane-mage.yaml; the Merciless Gladiator's War Staff is
            # Season 2 arena, the ladder's next reachable staff.
            {"mh": 29988, "oh": None, "phase3": False},
            {"mh": 32055, "oh": None, "phase3": False},
            # MAIN HAND WITH A HELD FRILL. Tempest of Chaos from
            # Archimonde is the One Hand ladder's rank one and the guild
            # lead's routing, held with each of the top frills: the worn
            # Chronicle of Dark Secrets from Rage Winterchill,
            # Blind-Seers Icon from Shade of Akama, and the Talisman of
            # Kalecgos from G'eras, the state where the sword drops
            # before a Phase 3 frill does.
            {"mh": 30910, "oh": 30872, "phase3": True},
            {"mh": 30910, "oh": 32361, "phase3": True},
            {"mh": 30910, "oh": 29271, "phase3": True},
            # The other Phase 3 main hands, each with the rank one
            # frill: the Vengeful Gladiator's Spellblade is Season 3
            # arena and The Maelstrom's Fury drops from High Warlord
            # Naj'entus.
            {"mh": 33763, "oh": 30872, "phase3": True},
            {"mh": 32237, "oh": 30872, "phase3": True},
            # The Merciless Gladiator's Spellblade with the rank one
            # frill, the state where a frill drops before any Phase 3
            # main hand does.
            {"mh": 32053, "oh": 30872, "phase3": True},
            # Reachable before Phase 3: Fang of the Leviathan from
            # Leotheras the Blind and the Merciless Gladiator's
            # Spellblade, Season 2 arena, each with the Talisman of
            # Kalecgos, the best frill reachable before Phase 3, price
            # the one-hander style against the worn Nexus Key at the
            # entry anchor.
            {"mh": 30095, "oh": 29271, "phase3": False},
            {"mh": 32053, "oh": 29271, "phase3": False},
        ],
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
    # warlock tabs. The Vengeful Gladiator's War Staff is not a row for
    # the same reason as in the other caster rounds: the Battle Staff
    # carries the same statistics plus 28 spell hit, so it equals or
    # beats the War Staff at every hit state and stands for both.
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
            "slot, and the consumables, buffs and seed hold still, so "
            "every figure is directly comparable with the one at the "
            "top of this page. The Superior Wizard Oil applies to any "
            "weapon, staff and mace alike, and a frill takes no imbue, "
            "so nothing about the consumables varies across the rows. "
            "The candidates are the top of the EP Workbook's Two Hand, "
            "One Hand and Off Hand ladders for this spec, and no "
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
        "pairs": [
            # TWO HAND, a staff alone, off hand EMPTY. Zhar'doom,
            # Greatstaff of the Devourer, from Illidan Stormrage, is the
            # worn best-in-slot weapon and the workbook's rank one; the
            # Vengeful Gladiator's Battle Staff is Season 3 arena and
            # stands for both Season 3 staves.
            {"mh": 32374, "oh": None, "phase3": True},
            {"mh": 34540, "oh": None, "phase3": True},
            # Reachable before Phase 3: the Merciless Gladiator's War
            # Staff is Season 2 arena and the workbook's best reachable
            # staff; The Nexus Key drops from Kael'thas Sunstrider.
            {"mh": 32055, "oh": None, "phase3": False},
            {"mh": 29988, "oh": None, "phase3": False},
            # MAIN HAND WITH A HELD FRILL. The Vengeful Gladiator's
            # Gavel, Season 3 arena, is the One Hand ladder's rank one
            # and stands for the identically statted Spellblade, held
            # with each of the top frills: Blind-Seers Icon from Shade
            # of Akama, Chronicle of Dark Secrets from Rage Winterchill,
            # and the worn Orb of the Soul-Eater from the badge vendor,
            # the state where the mace arrives before a Phase 3 frill
            # drops.
            {"mh": 33687, "oh": 32361, "phase3": True},
            {"mh": 33687, "oh": 30872, "phase3": True},
            {"mh": 33687, "oh": 29272, "phase3": True},
            # The Phase 3 raid-drop main hands, each with the rank one
            # frill: Hammer of Judgement drops in Hyjal Summit and The
            # Maelstrom's Fury drops from High Warlord Naj'entus.
            {"mh": 34009, "oh": 32361, "phase3": True},
            {"mh": 32237, "oh": 32361, "phase3": True},
            # The worn Merciless Gladiator's Spellblade with the rank
            # one frill, the state where a frill drops before any Phase
            # 3 main hand does.
            {"mh": 32053, "oh": 32361, "phase3": True},
            # Reachable before Phase 3: the Merciless Gladiator's
            # Spellblade, Season 2 arena, with the Orb of the Soul-Eater
            # from G'eras is the worn entry AND tier combination, per
            # the capture in data/facts/sim-profiles/hit-capture/
            # shadow-priest.yaml.
            {"mh": 32053, "oh": 29272, "phase3": False},
        ],
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
    # Shadow Priest's. The Vengeful Gladiator's War Staff is not a row
    # for the same reason as in the other caster rounds: the Battle Staff
    # carries the same statistics plus 28 spell hit, so it equals or
    # beats the War Staff at every hit state and stands for both.
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
            "slot, and the consumables, buffs and seed hold still, so "
            "every figure is directly comparable with the one at the "
            "top of this page. The Brilliant Wizard Oil applies to any "
            "weapon, staff and mace alike, and a frill takes no imbue, "
            "so nothing about the consumables varies across the rows. "
            "The candidates are the top of the EP Workbook's Two Hand, "
            "One Hand and Off Hand ladders for this spec, and no "
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
        "pairs": [
            # TWO HAND, a staff alone, off hand EMPTY. Zhar'doom,
            # Greatstaff of the Devourer, from Illidan Stormrage, is the
            # worn best-in-slot weapon and the workbook's rank one; the
            # Vengeful Gladiator's Battle Staff is Season 3 arena and
            # stands for both Season 3 staves.
            {"mh": 32374, "oh": None, "phase3": True},
            {"mh": 34540, "oh": None, "phase3": True},
            # Reachable before Phase 3: the Merciless Gladiator's War
            # Staff is Season 2 arena and the workbook's best reachable
            # staff after The Nexus Key, which drops from Kael'thas
            # Sunstrider and is the worn entry AND tier weapon, per the
            # capture in data/facts/sim-profiles/hit-capture/
            # balance-druid.yaml.
            {"mh": 32055, "oh": None, "phase3": False},
            {"mh": 29988, "oh": None, "phase3": False},
            # MAIN HAND WITH A HELD FRILL. The Vengeful Gladiator's
            # Gavel, Season 3 arena, is the One Hand ladder's rank one
            # and stands for the identically statted Spellblade, held
            # with each of the top frills: Chronicle of Dark Secrets
            # from Rage Winterchill, Blind-Seers Icon from Shade of
            # Akama, and the Jewel of Infinite Possibilities from
            # Netherspite, the state where the mace arrives before a
            # Phase 3 frill drops.
            {"mh": 33687, "oh": 30872, "phase3": True},
            {"mh": 33687, "oh": 32361, "phase3": True},
            {"mh": 33687, "oh": 28734, "phase3": True},
            # The Phase 3 raid-drop main hands, each with the rank one
            # frill: Hammer of Judgement drops in Hyjal Summit and The
            # Maelstrom's Fury drops from High Warlord Naj'entus.
            {"mh": 34009, "oh": 30872, "phase3": True},
            {"mh": 32237, "oh": 30872, "phase3": True},
            # The Merciless Gladiator's Spellblade with the rank one
            # frill, the state where a frill drops before any Phase 3
            # main hand does.
            {"mh": 32053, "oh": 30872, "phase3": True},
            # Reachable before Phase 3: the Merciless Gladiator's
            # Spellblade, Season 2 arena, with the Jewel of Infinite
            # Possibilities from Netherspite prices the one-hander
            # style against the worn Nexus Key at the entry anchor.
            {"mh": 32053, "oh": 28734, "phase3": False},
        ],
    },
    # ELEMENTAL SHAMAN: both styles in the same table, per the 20 August
    # 2026 ruling in data/judgments/weapon-styles.yaml, in the caster
    # template's shape. The candidates are the top of the Ele workbook
    # tab, whose weapon ladders are One Hand, Off Hand and Two Hand, with
    # no Main Hand section. A shaman wields maces, axes, staves, daggers
    # and fist weapons and CANNOT WIELD SWORDS, so Tempest of Chaos is
    # not a row: its exclusion is proficiency rather than routing. The
    # tab itself lists two swords the class cannot carry, the
    # Illidari-Bane Mageblade at One Hand rank eleven and the Eternium
    # Runed Blade at rank twelve, both far below the cut, and neither is
    # a row. The One Hand ladder's rank one is The Maelstrom's Fury;
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
    # Gladiator's War Staff is not a row for the same reason as in the
    # other caster rounds: the Battle Staff carries the same statistics
    # plus 28 spell hit, so it equals or beats the War Staff at every
    # hit state and stands for both. SOCKETS: no candidate carries a
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
            "the slot, and the consumables, buffs and seed hold still, "
            "so every figure is directly comparable with the one at the "
            "top of this page. The Brilliant Wizard Oil applies to any "
            "weapon, staff and mace alike, and a frill or a shield "
            "takes no imbue, so nothing about the consumables varies "
            "across the rows. The candidates are the top of the EP "
            "Workbook's Two Hand, One Hand and Off Hand ladders for "
            "this spec, and no candidate carries a socket. A shaman "
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
        "pairs": [
            # TWO HAND, a staff alone, off hand EMPTY. Zhar'doom,
            # Greatstaff of the Devourer, from Illidan Stormrage, is the
            # worn best-in-slot weapon and the workbook's rank one; the
            # Vengeful Gladiator's Battle Staff is Season 3 arena and
            # stands for both Season 3 staves.
            {"mh": 32374, "oh": None, "phase3": True},
            {"mh": 34540, "oh": None, "phase3": True},
            # Reachable before Phase 3: the Merciless Gladiator's War
            # Staff is Season 2 arena and the workbook's best reachable
            # staff; The Nexus Key drops from Kael'thas Sunstrider.
            {"mh": 32055, "oh": None, "phase3": False},
            {"mh": 29988, "oh": None, "phase3": False},
            # MAIN HAND WITH A HELD OFF HAND. The Vengeful Gladiator's
            # Gavel, Season 3 arena, stands for the identically statted
            # Spellblade, held with each of the tab's top off hands:
            # Chronicle of Dark Secrets from Rage Winterchill,
            # Antonidas's Aegis of Rapt Concentration from Archimonde,
            # which is the shield row, Blind-Seers Icon from Shade of
            # Akama, and the worn Fathomstone from Hydross the
            # Unstable, the state where the mace arrives before a
            # Phase 3 off hand drops.
            {"mh": 33687, "oh": 30872, "phase3": True},
            {"mh": 33687, "oh": 30909, "phase3": True},
            {"mh": 33687, "oh": 32361, "phase3": True},
            {"mh": 33687, "oh": 30049, "phase3": True},
            # The Phase 3 raid-drop main hands, each with the rank one
            # off hand: The Maelstrom's Fury, the One Hand ladder's
            # rank one, drops from High Warlord Naj'entus and Hammer of
            # Judgement drops in Hyjal Summit.
            {"mh": 32237, "oh": 30872, "phase3": True},
            {"mh": 34009, "oh": 30872, "phase3": True},
            # The worn Merciless Gladiator's Spellblade with the rank
            # one off hand, the state where a Phase 3 frill drops
            # before any Phase 3 main hand does.
            {"mh": 32053, "oh": 30872, "phase3": True},
            # Reachable before Phase 3: the Merciless Gladiator's
            # Spellblade, Season 2 arena, with the Fathomstone is the
            # worn entry AND tier combination, per the capture in
            # data/facts/sim-profiles/hit-capture/elemental-shaman.yaml.
            {"mh": 32053, "oh": 30049, "phase3": False},
        ],
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

    # THE FILE KEEPS THE REGISTRY'S ORDER regardless of which spec a --spec
    # run reran, or every partial run reorders the file and its diff reads
    # far larger than it is.
    specs_out = {spec: specs_out[spec] for spec in ROUNDS if spec in specs_out}

    document = {
        "meta": {
            "what": (
                "Weapon rounds, one per spec in the registry of "
                "tools/run_variant_sims.py, each combination run as a "
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
