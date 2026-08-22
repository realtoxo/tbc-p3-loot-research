#!/usr/bin/env python3
"""Run every sim profile through wowsimcli, and report DPS per spec per anchor.

WHAT THIS IS FOR. The council's question is almost never "what is this spec's
DPS". It is "what does THIS ITEM do for this spec", which is a difference
between two runs that are identical but for one slot. So this tool holds
everything still and varies one thing, and the encounter is fixed at a single
target for the length in ENCOUNTER_SECONDS so that two results are always
comparable.

WHY THE REQUEST IS BUILT HERE AND NOT STORED. wowsimcli takes a RaidSimRequest,
which wraps the player, the encounter and the sim options together. Storing 45
of those would put the encounter and the buffs in 45 places, and they would
drift. The gear is stored, in data/sim/gear, and everything around it is
assembled at run time from the fact files.

VARYING AN ITEM is the point of the whole thing. `--swap` replaces one slot in
one profile and runs it beside the unchanged profile, so the answer is a
difference between two runs identical in every other respect. Several `--swap`
arguments run several candidates against the same baseline, which is how a slot
gets a landscape rather than a verdict.

Usage:
    python3 tools/run_sims.py --check          # every profile runs, no DPS
    python3 tools/run_sims.py --iterations 10000

    # what one item is worth in one slot, against everything else held still
    python3 tools/run_sims.py --profile combat-rogue.tier-hands-only \
        --slot trinket_1 --swap 32505 --swap 30627 --swap 29383

    # a two-hander, or any pair, by naming both slots
    python3 tools/run_sims.py --profile arms-warrior.entry \
        --slot main_hand --swap 30902 --slot off_hand --swap 0
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

GEAR = Path("data/sim/gear")
ITEMS = Path("data/facts/items.csv")

# proto/common.proto :: ItemSlot order, the same list export_sim_profiles.py
# writes against. A swap names a slot by this vocabulary.
SLOT_ORDER = [
    "head", "neck", "shoulder", "back", "chest", "wrist", "hands", "waist",
    "legs", "feet", "ring_1", "ring_2", "trinket_1", "trinket_2", "main_hand",
    "off_hand", "ranged",
]
WOWSIMS = Path(os.path.expanduser(os.environ.get(
    "WOWSIMS_TBC",
    "../tbc-phase-research-recovered/data/raw/vendor/wowsims-tbc-new-master")))

# THE ROTATION EACH SPEC USES, taken from the action priority list the simulator
# itself ships. Writing our own would be a modelling choice we could not defend;
# taking theirs is one we can cite.
#
# THIS IS NOT OPTIONAL FOR A CASTER. Running with rotation type Auto returns
# 0.0 DPS for every caster and a plausible figure for every physical spec, which
# is the worst kind of failure: it looks like a result. Six specs read zero
# before the lists below were loaded.
APL = {
    "combat_rogue":         "rogue/dps/apls/swords.apl.json",
    "arms_warrior":         "warrior/dps/apls/arms.apl.json",
    "fury_warrior":         "warrior/dps/apls/fury.apl.json",
    # NO APL EXISTS FOR THIS SPEC IN THIS BUILD, and the preset beside it is a
    # stub: empty talents, no rotation, minimal options. It falls back to Auto
    # and returns about a fifth of what every other melee spec does, which is a
    # non-result rather than a low one. See IMPLAUSIBLE below.
    "feral_cat":            "druid/feralcat/apls/default.apl.json",
    "retribution_paladin":  "paladin/retribution/apls/default.apl.json",
    "enhancement_shaman":   "shaman/enhancement/apls/default.apl.json",
    # THE HUNTERS RUN A REPO-LOCAL VARIANT, ruled by the guild lead on
    # 22 August 2026: "ah yes we should assume no weaving". The shipped
    # hunter preset hard-codes melee weaving as an APL constant, and every
    # hunter figure published before this ruling assumed it. The variant is
    # the preset with exactly two edits: the Melee weave constant set false,
    # and the weave-gated prepull move replaced with an unconditional move
    # to 25 yards, because without it the hunter stands at spawn in melee
    # range where ranged shots cannot fire and the figure collapses to a
    # plausible-looking melee-only number. See data/judgments/sim-context.yaml.
    "beast_mastery_hunter": "data/sim/apls/hunter-no-weave.apl.json",
    "survival_hunter":      "data/sim/apls/hunter-no-weave.apl.json",
    "affliction_warlock":   "warlock/dps/apls/affliction.apl.json",
    "destruction_warlock":  "warlock/dps/apls/destruction.apl.json",
    "arcane_mage":          "mage/dps/apls/arcane.apl.json",
    "balance_druid":        "druid/balance/apls/default.apl.json",
    "shadow_priest":        "priest/dps/apls/default.apl.json",
    "elemental_shaman":     "shaman/elemental/apls/default.apl.json",
}
TALENTS = Path("data/facts/talents.yaml")
BUFFS = Path("data/facts/raid-buffs.yaml")
ROSTER = Path("data/facts/roster.yaml")
BOSS_ARMOR = Path("data/facts/boss-armor.yaml")
CONSUMABLES = Path("data/facts/consumable-ids.yaml")
PROTO = WOWSIMS / "proto" / "common.proto"

# COUNTS, NOT SWITCHES, for the fields the proto types as int32. Each is "how
# many of this are in the raid", and roster.yaml decides. Ferocious Inspiration
# is one Beast Mastery hunter; Totem of Wrath is one Elemental Shaman.
COUNTS = {"ferociousInspiration": 1, "totemOfWrath": 1, "manaTideTotems": 1,
          "innervates": 0, "powerInfusions": 0,
          "drums": "GreaterDrumsOfBattle",
          # NOT A HEADCOUNT. sim/core/buffs.go grants MP5 = dps * 0.25 from
          # this field, so it is the donor priest's DPS and a value of 1 buys
          # a quarter of one MP5. It was set to 1 as though it counted priests,
          # which delivered approximately none of the intended mana and looked
          # like it worked. Found by a second review on 10 August 2026.
          #
          # 1150 is this project's own Shadow Priest figure, the mean of its
          # three buffed anchors, so the number is ours rather than invented.
          "shadowPriestDps": 1150}

# TRISTATE FIELDS TAKE Missing, Regular or Improved, and Improved needs the
# TALENT rather than merely the class. Every entry here is justified by a talent
# decoded from the strings in talents.yaml, so none of it is assumed.
#
# ONLY faerieFire WAS RAISED AT FIRST, and an adversarial review on 10 August
# 2026 found six more this roster earns. Each is live damage: the simulator
# multiplies Battle Shout by 1.25 on Improved, reads Curse of the Elements as
# ranks 0 or 3, and passes two talent points to the totems only on Improved.
IMPROVED = {
    "faerieFire",            # Balance Druid, already credited in hit.yaml
    "battleShout",           # both warriors decode commandingPresence 5/5
    "curseOfElements",       # Affliction decodes malediction 3/3
    "huntersMark",           # Survival decodes improvedHuntersMark 5/5
    "sanctityAura",          # Retribution decodes improvedSanctityAura 2/2
    "strengthOfEarthTotem",  # Enhancement decodes enhancingTotems 2/2
    "graceOfAirTotem",       # the same talent
    "giftOfTheWild",         # Balance's Restoration 13 decodes improvedMarkOfTheWild 5/5
    # Retribution decodes improvedSealOfTheCrusader 3/3, and debuffs.go reads
    # this tristate as 0 points on Regular and 3 on Improved, so Regular would
    # credit the base judgement and none of the talent.
    "improvedSealOfTheCrusader",
    # sim/druid/druid.go makes Moonkin Aura Improved when the Balance Druid holds
    # Idol of the Raven Goddess, item 32387, in the ranged slot, and ours holds
    # it at ALL THREE anchors, verified in the gear files. Improved adds 20 spell
    # crit rating on top of the base 5 percent. Worth 17.8 to 22.1 DPS to the
    # Elemental Shaman, which shares g3. The Balance Druid itself measures 0.0,
    # because druid.go sets its own party buff from the idol regardless of what
    # this tool sends.
    "moonkinAura",
}

# THE TWO DOUBLE-TYPED FIELDS THIS RAID SUPPLIES, and both must be sent or
# neither is worth anything. sim/core/debuffs.go gates Expose Weakness on
# Uptime > 0 and then sets the attack power from agility times 0.25, so an uptime
# with no agility beside it buys exactly zero. Sending one alone is the failure
# this pair is written to prevent.
#
# EXPOSE WEAKNESS WAS RULED IN by the guild lead on 15 August 2026, overriding
# the NOT_SENT note in raid-buffs.yaml, whose stated reason was that an uptime is
# a rotation outcome this project has not measured. The simulator now ships a
# phase-specific answer, so that reason no longer holds.
#
# 1210 IS THE SIMULATOR'S PHASE 3 FIGURE, NOT OUR HUNTER'S MEASURED AGILITY, and
# that distinction is the honest part of this entry. ui/core/proto_utils/utils.ts
# gives Phase 3 an uptime of 0.9 and a hunter agility of 1210. Our own Survival
# Hunter's raid-buffed agility is NOT KNOWN: set-stats.yaml records 419 to 442 of
# ITEM agility, which excludes base stats, Gift of the Wild, Blessing of Kings,
# Grace of Air, scrolls and food, and wowsimcli exposes neither final player
# stats nor target aura stacks, so it cannot be read out of a run either.
# SETTLED BY a build of the simulator that reports final stats, or by deriving
# the total from sim/core and checking it against one. Until then this is the
# simulator's assumption, cited as such.
#
# THE SURVIVAL HUNTER ITSELF IS UNAFFECTED, correctly: sim/hunter/hunter.go
# zeroes the raid debuff for any hunter that has the talent, because it self
# applies. It measures +0.0 and every other physical spec gains.
DOUBLE_FIELDS = {
    # MEASURED, not assumed. See EXPOSE_WEAKNESS_AGILITY below for how.
    "exposeWeaknessUptime": 0.98,
    "exposeWeaknessHunterAgility": 1152.0,
}

# OUR SURVIVAL HUNTER'S AGILITY, MEASURED PER ANCHOR RATHER THAN ASSUMED.
#
# THIS STARTED AS THE SIMULATOR'S NUMBER AND IS NOW OURS. Expose Weakness gives
# the raid attack power equal to a quarter of the Survival Hunter's agility, and
# the effect is exactly linear, so the value is not a detail: measured on the
# Combat Rogue, an agility of 605 is worth +63.8 and 1210 is worth +129.4.
# ui/core/proto_utils/utils.ts ships 1210 for Phase 3, and that was sent for a
# few hours on 15 August 2026 while this comment said plainly that it was the
# simulator's assumption and not our hunter's agility.
#
# IT COULD NOT BE READ OUT OF A RUN. wowsimcli has no stats subcommand, its
# result exposes no final player stats, and its target auras carry uptime and
# procs but no stacks. set-stats.yaml holds only ITEM agility, 419 to 447, which
# excludes base stats, Gift of the Wild, Grace of Air, Blessing of Kings,
# Lightning Reflexes, the scroll and the food, and is wrong by more than a factor
# of two.
#
# SO IT WAS MEASURED BY BISECTION. sim/hunter/hunter.go zeroes BOTH debuff fields
# for any hunter holding the talent, which is why the hunter is immune to the
# external value: even 20000 agility moves it exactly 0.0. Removing the talent
# from its string lifts that immunity, so the external agility that reproduces
# the hunter's own self-applied result IS its agility. Nine bisection steps at
# 10000 iterations per anchor, against the measured self-uptime of 0.98.
#
# CROSS-CHECKED BY HAND, independently: base 151 plus 4 for Night Elf, item and
# gem and enchant agility from the gear files, plus 20 scroll and 20 food, plus
# Gift of the Wild at 14 times 1.35 and Grace of Air at 77 times 1.15, all
# multiplied by 1.1 for Blessing of Kings and 1.15 for Lightning Reflexes 5 of 5,
# gives 1131 at best in slot against the measured 1152. Agreement to 1.8 percent
# by two methods that share no step.
#
# THE UPTIME IS MEASURED TOO. The hunter's own Expose Weakness debuff sits on the
# target for 147.0 seconds of 150, which is 0.98 and not the 0.9 the preset
# assumes. The pair is calibrated TOGETHER: each agility below was solved with
# the uptime held at 0.98, so the two must be changed together or not at all.
EXPOSE_WEAKNESS_AGILITY = {
    "entry": 1119.0,
    "tier_hands_and_head": 1105.0,
    "bis": 1152.0,
    # The no-glaive profiles differ from `bis` only in the two weapon slots of
    # the spec being simulated, and the hunter supplying this debuff is not that
    # spec, so its agility is the best-in-slot figure unchanged.
    "bis_no_glaives": 1152.0,
}

# WINDFURY IS DELIBERATELY NOT HERE. Enhancement decodes improvedWeaponTotems at
# 1 of 2, and a tristate cannot express half a talent, so Regular is the honest
# reading rather than a rounding up.

# Which specs count as physical for the blessing split. A blessing of might is
# attack power and a caster cannot use it; wisdom is mana and a rogue cannot.
PHYSICAL = {"combat_rogue", "arms_warrior", "fury_warrior", "feral_cat",
            "retribution_paladin", "enhancement_shaman",
            "beast_mastery_hunter", "survival_hunter"}
HIT = Path("data/facts/hit.yaml")

# proto/common.proto :: enum Class. Transcribed, not inferred. It matches the
# WoW ChrClasses ids, which is the same map extract_items.py uses after two enum
# bugs were found there.
CLASS = {
    "warrior": 1, "paladin": 2, "hunter": 3, "rogue": 4, "priest": 5,
    "shaman": 7, "mage": 8, "warlock": 9, "druid": 11,
}

# proto/common.proto :: enum Race. Transcribed, not inferred.
RACE = {
    "BloodElf": 1, "Draenei": 2, "Dwarf": 3, "Gnome": 4, "Human": 5,
    "NightElf": 6, "Orc": 7, "Tauren": 8, "Troll": 9, "Undead": 10,
}

# WHICH RACE MAY PLAY WHICH CLASS, transcribed from the AddBaseStatsCombo calls
# in sim/core/base_stats.go. That function is the ONLY place base stats are
# registered, so a combination absent from it has no entry in the BaseStats map.
#
# THIS IS THE MOST EXPENSIVE DEFECT THIS PROJECT HAS SHIPPED, and it shipped
# because Go does not error on a missing map key. `run_sims.py` sent race 1,
# Blood Elf, for every spec. Blood Elf cannot be a Warrior, a Druid or a Shaman
# in 2.4.3, so the lookup returned the zero value and six specs ran with NO BASE
# STRENGTH, AGILITY OR STAMINA. Nothing failed. Every affected figure was simply
# smaller: the Fury Warrior by 472 DPS, the Arms Warrior by 335.
#
# So an illegal pairing now STOPS THE RUN. A wrong race that is legal is a
# modelling choice someone can argue with; an illegal one is a character that
# does not exist, and it does not announce itself.
LEGAL_RACES = {
    "warrior": {"Draenei", "Dwarf", "Gnome", "Human", "NightElf", "Orc",
                "Tauren", "Troll", "Undead"},
    "paladin": {"BloodElf", "Draenei", "Dwarf", "Human"},
    "hunter":  {"BloodElf", "Draenei", "Dwarf", "NightElf", "Orc", "Tauren",
                "Troll"},
    "rogue":   {"BloodElf", "Dwarf", "Gnome", "Human", "NightElf", "Orc",
                "Troll", "Undead"},
    "priest":  {"BloodElf", "Draenei", "Dwarf", "Gnome", "Human", "NightElf",
                "Troll", "Undead"},
    "shaman":  {"Draenei", "Orc", "Tauren", "Troll"},
    "mage":    {"BloodElf", "Draenei", "Dwarf", "Gnome", "Human", "Troll",
                "Undead"},
    "warlock": {"BloodElf", "Gnome", "Human", "Orc", "Undead"},
    "druid":   {"NightElf", "Tauren"},
}


_ROSTER_CACHE: dict = {}


def race_of(spec: str, klass: str, roster: dict) -> int:
    """The race this spec is simulated as, from the roster, checked for legality."""
    by_spec = ((roster.get("races") or {}).get("by_spec") or {})
    name = by_spec.get(spec)
    if name is None:
        raise SystemExit(
            f"run_sims.py: {spec} has no race in roster.yaml::races.by_spec. A "
            "race is not optional: sim/core/base_stats.go keys base stats on "
            "race AND class, and an unset race is Blood Elf, which for a "
            "warrior, a druid or a shaman means no base stats at all.")
    if name not in RACE:
        raise SystemExit(
            f"run_sims.py: {spec} is recorded as race {name!r}, which is not a "
            f"value of proto Race. One of: {', '.join(sorted(RACE))}.")
    if name not in LEGAL_RACES[klass]:
        raise SystemExit(
            f"run_sims.py: {spec} is a {klass} recorded as {name}, which is not "
            f"a {klass} race in 2.4.3. sim/core/base_stats.go registers no base "
            "stats for that pairing, so the run would SUCCEED and return a "
            "character with no base strength, agility or stamina. Legal: "
            f"{', '.join(sorted(LEGAL_RACES[klass]))}.")
    return RACE[name]

# Which class each spec is, and which field of the Player `spec` oneof it fills.
# The oneof name is NOT always the spec name: both warriors share dps_warrior,
# both hunters share hunter, both warlocks share warlock, and the Feral Cat is
# feral_druid where the Bear is guardian_druid.
SPECS = {
    "combat_rogue":         ("rogue",   "rogue"),
    "arms_warrior":         ("warrior", "dpsWarrior"),
    "fury_warrior":         ("warrior", "dpsWarrior"),
    "feral_cat":            ("druid",   "feralDruid"),
    "retribution_paladin":  ("paladin", "retributionPaladin"),
    "enhancement_shaman":   ("shaman",  "enhancementShaman"),
    "beast_mastery_hunter": ("hunter",  "hunter"),
    "survival_hunter":      ("hunter",  "hunter"),
    "affliction_warlock":   ("warlock", "warlock"),
    "destruction_warlock":  ("warlock", "warlock"),
    "arcane_mage":          ("mage",    "mage"),
    "balance_druid":        ("druid",   "balanceDruid"),
    "shadow_priest":        ("priest",  "priest"),
    "elemental_shaman":     ("shaman",  "elementalShaman"),
}

# THE ENCOUNTER IS FIXED AND IS NOT A KNOB. Single target, a level 73 boss, and
# the length below. Every result in this project is produced against exactly
# this, so two numbers can always be subtracted. Changing it invalidates every
# figure collected before the change, which is why the length is written once,
# here, and read from here by everything that needs it. It was stated in three
# places until 14 August 2026, so a change could half-apply and leave the prose
# describing an encounter the runs no longer used.
#
# TWO AND A HALF MINUTES, ruled by the guild lead on 15 August 2026, replacing
# the 180 seconds ruled on 14 August, which had itself replaced 150. Every figure
# collected before this date was produced against a different encounter and is
# not comparable with one collected after it.
#
# SHORTENING THE FIGHT IS NOT NEUTRAL ACROSS SPECS AND NEVER WAS. Measured at 90
# seconds against 180 on 15 August 2026, every spec gained but by wildly
# different amounts: the mana-constrained casters gained 41 to 45 percent because
# they stop running dry, while the melee gained 5 to 8. At 150 seconds the effect
# is milder and the same shape. It is a real property of the encounter rather
# than a modelling error, and it is why `--out` stamps the length into the meta
# block of whatever it writes.
ENCOUNTER_SECONDS = 150

# THE CLASS OPTIONS EACH SPEC NEEDS, taken from the DefaultOptions its own
# preset ships. An empty block is not a safe default: a warlock with no armor,
# no pet and no curse returns about 65 DPS, which is a tenth of the real figure
# and looks like a number rather than a failure.
#
# Enum values are transcribed from proto/warlock.proto: Armor FelArmor is 1,
# Summon Succubus is 3, CurseOptions Recklessness is 3.
# THE CLASS OPTIONS EACH SPEC NEEDS, taken from the DefaultOptions its own
# preset ships, and taken WHOLESALE rather than key by key.
#
# AN EMPTY BLOCK IS NOT A SAFE DEFAULT, and this file has now learned that twice.
# A warlock with no armor, no pet and no curse returns about 65 DPS, a tenth of
# the real figure. Worse, on 15 August 2026 the guild lead found the Beast
# Mastery Hunter "critically low" and the cause was that BOTH hunters were sent
# an empty block: proto/hunter.proto defaults pet_type to PetNone, ammo to
# AmmoNone and quiver_bonus to QuiverNone, so they hunted with NO PET, NO AMMO
# and NO QUIVER. It cost Beast Mastery 1508 DPS and Survival 769.
#
# An audit of every spec's shipped preset the same day found five more gaps:
# both warriors 74 to 80 DPS of stance, shout, starting rage and the Tier 2
# Battle Shout flag, the Arcane Mage 89 of Mage Armor, and the Shadow Priest
# 181 of pre-pull Shadowform. Only the two Shaman specs were already complete.
#
# THE RULE THIS NOW FOLLOWS: whatever the spec's own presets.ts sets, we set,
# unless a ruling declines it and says why. tools/check_sim_options.py compares
# the two and fails the build on a key we neither send nor decline.
CLASS_OPTIONS = {
    # SACRIFICE IS OFF FOR AFFLICTION AND ON FOR DESTRUCTION, and the same flag
    # is right for one and wrong for the other. Demonic Sacrifice is a DEMONOLOGY
    # talent; the Affliction build is 40/0/21 with an EMPTY Demonology tree, so
    # sim/warlock/talents.go returns early and grants no shadow multiplier, while
    # sim/warlock/warlock.go destroys the pet regardless. Affliction was
    # sacrificing its Succubus for nothing. Worth 150 to 154 DPS, re-measured by
    # an arbiter across three seeds after the audit's own +168.1 failed to
    # reproduce. Destruction decodes the talent 1/1 and LOSES 66 to 126 with
    # sacrifice off, which is the asymmetry that proves the diagnosis.
    #
    # `summon` STAYS SUCCUBUS. Voidwalker crashes this build of the simulator
    # with a nil CritMultiplier.
    "affliction_warlock": {"armor": 1, "summon": 3, "curseOptions": 3,
                           "sacrificeSummon": False},
    "destruction_warlock": {"armor": 1, "summon": 3, "curseOptions": 3,
                            "sacrificeSummon": True},
    # A WEAPON IMBUE IS A SELF-BUFF, NOT A CONSUMABLE. The guild lead ruled on
    # 15 August 2026 that the shamans "use dual WF weapon", and Windfury Weapon
    # reaches the simulator only through the class options: sim/shaman/
    # enhancement/enhancement.go reads ClassOptions.ImbueMh into SelfBuffs, and
    # sim/shaman/weapon_imbues.go arms the main hand only when that field says
    # WindfuryWeapon. An id sent in the ConsumesSpec field mhImbue_id is
    # accepted by the encoder and dropped, which is why consumable-ids.yaml
    # leaves both imbues unresolved and why this spec ran bare.
    #
    # WindfuryWeapon is 1 in proto/shaman.proto :: ShamanImbue, sent by the
    # enum name because the encoder rejects a name it does not know and would
    # accept a wrong number in silence.
    "enhancement_shaman": {"imbueMh": "WindfuryWeapon", "shieldProcrate": 0},
    "elemental_shaman": {"shieldProcrate": 0},
    # A HUNTER WITHOUT A PET IS NOT A HUNTER, and Beast Mastery least of all:
    # the pet alone is worth 1268 DPS to it against 531 to Survival, which is
    # the whole reason the two specs are shaped differently. Ravager at 100
    # percent uptime, Warden's Arrow and a 15 percent quiver are what the
    # shipped preset uses; none of the three is our choice.
    "beast_mastery_hunter": {"ammo": "WardensArrow", "quiverBonus": "Speed15",
                             "petType": "Ravager", "petUptime": 1.0,
                             "petSingleAbility": False},
    "survival_hunter": {"ammo": "WardensArrow", "quiverBonus": "Speed15",
                        "petType": "Ravager", "petUptime": 1.0,
                        "petSingleAbility": False},
    # BERSERKER STANCE IS THE ONE THAT MATTERS HERE. Recklessness and Whirlwind
    # both require it, and a warrior left in the default stance cannot use
    # either. `hasBsT2` is the Tier 2 Battle Shout bonus the preset assumes.
    "arms_warrior": {"queueDelay": 250, "startingRage": 50,
                     "defaultShout": "WarriorShoutBattle",
                     "defaultStance": "WarriorStanceBerserker",
                     "hasBsT2": True, "stanceSnapshot": True},
    "fury_warrior": {"queueDelay": 250, "startingRage": 50,
                     "defaultShout": "WarriorShoutBattle",
                     "defaultStance": "WarriorStanceBerserker",
                     "hasBsT2": True, "stanceSnapshot": True},
    "arcane_mage": {"defaultMageArmor": "MageArmorMageArmor"},
    # Shadowform is a 15 percent shadow damage multiplier and the pre-pull flag
    # is what puts the priest in it before the first cast.
    "shadow_priest": {"preShadowform": True},
}

# CONSUMABLES THE SHIPPED PRESET SETS AND NO GUIDE PROSE NAMES.
#
# data/facts/consumable-ids.yaml resolves the flask, food, potion and weapon
# imbue each spec's GUIDE names. It cannot resolve a field no guide writes about,
# and the shipped presets set several: a conjured mana item, pet food, pet
# scrolls and character scrolls. Those are the simulator's own defaults, cited
# the same way the action priority lists and the class options are.
#
# THE CONJURED FIELD IS THE potId TRAP AGAIN, ONE FIELD OVER. sim/core/
# consumes.go:285 registers the cooldown by iterating `conjuredItems`, and :339
# gates activation on `conjuredId` matching an entry of that list. Sending
# either one alone measures EXACTLY +0.0, which was confirmed by control run
# before the fix was accepted. Sending both is worth 94.3 to the Beast Mastery
# Hunter, 86.7 to Survival and 12.5 to the Combat Rogue, and it collapses the
# hunters' mana problem: seconds out of mana falls from 34.05 to 6.27 and Aspect
# of the Viper uptime from 54.6 seconds to 28.3 of a 180 second fight.
#
# `data/facts/consumable-ids.yaml::declined.other` declined these for the
# hunters on the ground that "No single ConsumesSpec field answers it". Two
# fields answer it. That entry is corrected there rather than here.
#
# NOT SENT FOR THE CASTERS. The Shadow Priest never runs out of mana in this
# encounter, so a rune measures +0.0 for it; the warlocks do gain and are added
# when their own audit is applied.
PRESET_CONSUMABLES = {
    # ui/hunter/dps/presets.ts :: DefaultConsumables
    "beast_mastery_hunter": {"conjuredId": 12662, "conjuredItems": [12662],
                             "petFoodId": 33874, "petScrollAgi": True,
                             "petScrollStr": True,
                             "scrollAgi": True, "scrollStr": True},
    "survival_hunter": {"conjuredId": 12662, "conjuredItems": [12662],
                        "petFoodId": 33874, "petScrollAgi": True,
                        "petScrollStr": True,
                        "scrollAgi": True, "scrollStr": True},
    # ui/rogue/dps/presets.ts :: DefaultConsumables. Thistle Tea, the second
    # action of swords.apl.json.
    "combat_rogue": {"conjuredId": 7676, "conjuredItems": [7676]},
    # FOUND BY THE GUARD ITSELF, not by any of the five audits, on the day it
    # was widened to read DefaultConsumables. ui/warlock/dps/presets.ts sets pet
    # scrolls for both warlocks. They are inert while a warlock sacrifices its
    # pet, which is why no audit noticed, and they become live for Affliction the
    # moment that sacrifice is corrected.
    # THE WARLOCKS' CONJURED RUNE, worth 15 to 25 DPS each. The Shadow Priest is
    # deliberately absent: it measures EXACTLY 0.0 there, because it never runs
    # out of mana in this encounter.
    "affliction_warlock": {"petScrollAgi": True, "petScrollStr": True,
                           "conjuredId": 12662, "conjuredItems": [12662]},
    "destruction_warlock": {"petScrollAgi": True, "petScrollStr": True,
                            "conjuredId": 12662, "conjuredItems": [12662]},
    # SCROLLS ARE FLAT AND UNCONDITIONAL, +20 strength and +20 agility from
    # sim/core/consumes.go, in their own buff slot so they stack with the
    # blessings. Every preset that ships them is listed; worth 28.6 to 47.5 on
    # the warriors and 34.6 to 40.4 on the two hybrids.
    #
    # THE WARRIORS' CONJURED ITEM IS FLAME CAP, 22788, not a mana rune, and both
    # warrior rotations cast it pre-pull and again in the priority list, so both
    # actions did nothing at all. Worth 2.3 to 5.9, quoted at the arbiter's
    # floor rather than the audit's.
    "arms_warrior": {"scrollAgi": True, "scrollStr": True,
                     "conjuredId": 22788, "conjuredItems": [22788]},
    "fury_warrior": {"scrollAgi": True, "scrollStr": True,
                     "conjuredId": 22788, "conjuredItems": [22788]},
    # THE FOUR REMAINING MANA USERS GET THE PRESET'S RUNE TOO, and three of them
    # were badly mana-starved without it. Measured 15 August 2026, 8000
    # iterations seed 1 at the best-in-slot anchor against boss armor 6193, with
    # seconds out of mana beside each: the Retribution Paladin gains 144.1 and
    # falls from 57.9 seconds to 20.1, the Balance Druid gains 151.0 and falls
    # from 21.5 to 5.4, the Elemental Shaman gains 110.7 and falls from 10.8 to
    # 0.3. The Enhancement Shaman gains 3.1 because it was barely short, and it
    # is sent anyway because the preset sets it and consistency is cheaper than a
    # special case.
    #
    # A rune and a potion are separate cooldowns, so this is additive with the
    # mana potion question the Retribution audit raised rather than an
    # alternative to it.
    "retribution_paladin": {"scrollAgi": True, "scrollStr": True,
                            "conjuredId": 12662, "conjuredItems": [12662]},
    "enhancement_shaman": {"scrollAgi": True, "scrollStr": True,
                           "conjuredId": 12662, "conjuredItems": [12662]},
    "balance_druid": {"conjuredId": 12662, "conjuredItems": [12662]},
    "elemental_shaman": {"conjuredId": 12662, "conjuredItems": [12662]},
}

# THE ROGUE'S MAIN HAND IS EMPTY WITHOUT THIS, and the guide prose cannot say so.
#
# consumable-ids.yaml resolves the rogue's main-hand imbue to Adamantite
# Sharpening Stone 29453 from its guide. sim/core/consumes.go:80-86 applies
# MhImbueId ONLY where the party carries no Windfury Totem, and the rogue sits
# in g1 with the Enhancement Shaman, so the stone is dropped and the slot is
# bare for the whole fight. Setting the id to 0 measures exactly +0.0, which is
# the control proving it.
#
# A POISON IN THAT FIELD IS NOT GATED. sim/rogue/poisons.go:182-191 reads
# Consumables.MhImbueId directly, so Instant Poison VII lands and measures
# +36.6. Deadly Poison in the main hand measures only +9.9, and Wound Poison
# +21.7, so the pairing below is the best of the three by measurement as well as
# by the sources: Icy Veins and Warcraft Tavern both put Instant Poison on the
# main hand and Deadly on the off hand for a TBC combat rogue.
#
# THE OFF HAND IS ALREADY DEADLY POISON and is left alone; it is applied
# unconditionally and is already live.
IMBUE_OVERRIDE = {
    ("combat_rogue", "mhImbueId"): (
        26891, "Instant Poison VII. The guide's sharpening stone is silently "
               "dropped by the Windfury Totem gate and measures +0.0; a poison "
               "in the same field bypasses that gate and measures +36.6."),
}

# OPTIONS THAT SIT BESIDE classOptions RATHER THAN INSIDE IT. The proto puts
# the shared shaman fields in ShamanOptions and the off hand in the spec
# message, so EnhancementShaman.Options.imbue_oh has no home in CLASS_OPTIONS.
# Writing it there would place it in a message that has no such field, and the
# encoder would reject it, which is the good case; the bad case is a field name
# that exists in both and takes effect in the wrong one.
SPEC_OPTIONS = {
    # The off hand of the dual Windfury ruling. sim/shaman/enhancement/
    # enhancement.go reads enhOptions.ImbueOh, one level up from ClassOptions.
    "enhancement_shaman": {"imbueOh": "WindfuryWeapon"},
    # syncType IS DELIBERATELY ABSENT, and it must stay absent.
    #
    # proto/shaman.proto ShamanSyncType offers NoSync, SyncMainhandOffhandSwings,
    # DelayOffhandSwings and Auto. Sending nothing falls to the default branch of
    # sim/shaman/enhancement/enhancement.go::ApplySyncType, which clears the
    # swing replacement, and that is unsynced. The guild lead ruled on 15 August
    # 2026: "enhancement shaman DO NOT want weapons synced".
    #
    # THIS IS WRITTEN DOWN BECAUSE THE OPPOSITE LOOKS LIKE AN IMPROVEMENT, and
    # the paragraph that used to sit here was wrong in three separate places. It
    # is corrected rather than deleted, because the wrong version was cited.
    #
    # PREVIOUSLY CLAIMED: DelayOffhandSwings "measures 16.5 DPS higher on the
    # entry anchor", and "Auto selects DelayOffhandSwings for matched weapon
    # speeds, which is the pairing this spec runs", and "Both are sync, and both
    # are declined".
    #
    # MEASURED, 10000 iterations seed 1, 15 August 2026:
    #   DelayOffhandSwings        entry +13.3   bis -51.0
    #   Auto                      entry  -2.2   bis  -0.3
    #   SyncMainhandOffhandSwings entry -34.7   bis +25.0
    #
    # So the entry figure was 13.3 rather than 16.5; AUTO IS NOT DELAY here,
    # because sim/shaman/enhancement/enhancement.go::AutoSyncWeapons delays the
    # off hand only when the two weapon speeds are EQUAL and this spec's are
    # mismatched at both anchors, 2.7 against 2.6 at entry and 2.6 against 2.8 at
    # best in slot; and a THIRD mode nobody discussed, SyncMainhandOffhandSwings,
    # is worth plus 25.0 at best in slot.
    #
    # THE RULING IS UNAFFECTED. The guild lead ruled the weapons unsynced on
    # 15 August 2026 and this file sends nothing, which reaches the default
    # branch and clears the swing replacement. What changes is that a reader can
    # now see the third mode exists and was not measured when the ruling was
    # made. What the option does is space the off hand around Flurry, whose
    # internal cooldown is the 500 ms constant ApplySyncType passes: two crits
    # inside one window waste the second.
}

# SPECS THIS BUILD OF THE SIMULATOR CANNOT MODEL, and why. Named rather than
# left to a threshold, because a threshold cannot tell a low spec from a broken
# one.
#
# The Feral Cat preset in this vendored snapshot is a STUB: empty talents, no
# action priority list, and options carrying one field. It runs, and returns
# about a fifth of what every other melee spec does.
#
# THE HEAD SLOT IS NO LONGER ONE OF THE REASONS. It was, while Wolfshead Helm
# was simmed empty; the ruling of 15 August 2026 puts the Tier 6 head in the
# profile instead, so the gear is now complete and the rotation is the whole of
# the blocker. Filling the head therefore does not make this spec simulatable,
# and saying that plainly is the point: 11 of the 14 files in sim/druid/feralcat
# are underscore-prefixed and so are not compiled into the binary at all.
NOT_SIMULATABLE = {
    "feral_cat": "the preset is a stub in this build: no rotation and no "
                 "talents, and the cat abilities are not compiled in",
}

# A FLOOR UNDER WHICH A RESULT IS NOT A RESULT. Nothing enforces that a
# simulation which RUNS is one that MODELLED anything: six casters returned
# exactly 0.0 before the rotations were loaded, and both warlocks returned about
# 65 before their armor, pet and curse were set. An exit code of zero would have
# shipped all eight.
#
# 300 IS DELIBERATELY LOW. The Balance Druid lands near 420 unbuffed, which is
# a real TBC Moonkin figure and not a failure, so a tighter floor would flag a
# correct result. This catches collapse, not weakness.
IMPLAUSIBLE = 300.0

ARMOR_INDEX = 31
# THE DEFAULT IS THE HIGHEST TIER, ruled by the guild lead on 20 August
# 2026: "our armor tiers should alway assume highest armor tiers!". Ten of
# the fourteen bosses sit at 6193 and that fact stands in
# data/facts/boss-armor.yaml; decisions assume the hardest target. See
# data/judgments/sim-context.yaml.
DEFAULT_ARMOR = 7684

# proto/common.proto stat indices for the three inert fields, transcribed.
AP_INDEX, BLOCK_VALUE_INDEX, HEALTH_INDEX = 17, 27, 33


def target_stats(armor: int) -> list:
    stats = [0] * 48
    stats[ARMOR_INDEX] = armor
    stats[AP_INDEX] = 320
    stats[BLOCK_VALUE_INDEX] = 54
    stats[HEALTH_INDEX] = 6070400
    return stats


def encounter_for(seconds: int, armor: int = DEFAULT_ARMOR) -> dict:
    """The fixed encounter, at a stated length.

    THE LENGTH IS A PARAMETER AND IS STILL NOT A KNOB TO TURN CASUALLY. Two
    figures are subtractable only if they were produced against the same
    encounter, and a shorter fight systematically favours a spec with long
    cooldowns: Death Wish is a three minute cooldown that fires ONCE whether the
    pull lasts 90 seconds or 180, so halving the fight doubles its share of the
    damage. That is a real effect and not a modelling error, which is exactly
    why the length has to travel with every figure rather than sit in a comment.
    `--out` records it in the meta block for that reason.
    """
    # A DEEP COPY, NOT A SHALLOW ONE. `dict(ENCOUNTER, ...)` shares the SAME
    # targets list and the SAME stats array with every other request, so any
    # caller varying the encounter silently mutates every run that follows. It
    # has already produced false measurements for two independent reviewers.
    out = copy.deepcopy(ENCOUNTER)
    out["duration"] = seconds
    out["targets"][0]["stats"] = target_stats(armor)
    return out


# THE BOSS HAS ARMOR, AND IT IS PER BOSS. Until 15 August 2026 this array was
# forty-eight zeros, so every simulation this project ever ran was against a boss
# with NO ARMOR. Index 31 is stats.Armor, per the Stat iota in
# sim/core/stats/stats.go, counted rather than assumed and corroborated against a
# shipped build file that carries 7685 at that position.
#
# WHAT IT COST. Physical specs were inflated 17 to 23 percent and casters not at
# all, so no comparison between the two survived. Worse, mitigation is
# max(armor - debuffs - armorPen, 0), so at zero armor EVERY armor debuff this
# raid supplies was worth exactly nothing and so was every point of armor
# penetration on every item. Sunder Armor, Faerie Fire and Curse of Recklessness
# together are worth 304 DPS on a corrected encounter and 0.0 on the old one.
#
# THE VALUE IS NOT A CONSTANT AND MUST NOT BE COPIED. data/facts/boss-armor.yaml
# holds one row per Phase 3 boss with a source each. Phase 3 spans two tiers,
# 7684 and 6193, and a single global figure misprices ten of the fourteen bosses
# by 120 to 315 DPS per physical spec. `--armor` selects which, `--out` stamps it
# into the meta block, and the DEFAULT IS THE LOWER TIER because ten of fourteen
# Phase 3 bosses sit in it.
#
# The other three fields come from the simulator's own default target at
# sim/encounters/register_all.go. Only armor moves DPS; attack power, health and
# block value all measured 0.0 against these profiles, which take no damage.
# Sending the preset's target whole is cheaper to defend than sending one field
# of it.
ENCOUNTER = {
    "duration": ENCOUNTER_SECONDS,
    "durationVariation": 0,
    # THE EXECUTE PHASE NEVER HAPPENED WITHOUT THESE. proto/common.proto declares
    # five executeProportion fields and sim/core/sim.go computes the phase from
    # them; all zero means the fight never enters execute range and Execute is
    # cast ZERO times. Worth 133.1 to the Fury Warrior and 43.6 to Arms, and
    # exactly 0.0 to all eleven other specs. The values are the simulator's own
    # preset, so they are citable rather than invented.
    #
    # RETRIBUTION MEASURES 0.0 HERE AND SHOULD NOT. Hammer of Wrath is an execute
    # ability the simulator implements at sim/paladin/hammer_of_wrath.go, and the
    # shipped Retribution action priority list does not contain it. So this spec
    # is under-credited for a reason that is in the rotation rather than here,
    # and that is recorded so nobody reads its flat result as a fact about the
    # spec.
    "executeProportion20": 0.2,
    "executeProportion25": 0.25,
    "executeProportion35": 0.35,
    "executeProportion45": 0.45,
    "executeProportion90": 0.9,
    "targets": [{
        "level": 73,
        "mobType": 0,
        "stats": target_stats(DEFAULT_ARMOR),
        "minBaseDamage": 10000,
        "damageSpread": 0.3333,
        "swingSpeed": 2.0,
    }],
}


def rotation_for(spec: str) -> dict:
    """The shipped action priority list for this spec.

    A MISSING FILE STOPS THE RUN rather than falling back to Auto. It fell back
    silently at first, and the Combat Rogue read 521 DPS against 880 for the
    warriors, because its list is named swords.apl.json and the map pointed at
    default.apl.json. Auto does not error; it just produces a smaller number,
    which is indistinguishable from a spec being weak.
    """
    # A rotation may live in the simulator checkout or in this repository:
    # a map entry starting with data/ is a repo-local variant of a preset,
    # with its derivation documented beside the map.
    if APL[spec].startswith("data/"):
        path = Path(APL[spec])
    else:
        path = WOWSIMS / "ui" / APL[spec]
    if not path.is_file():
        raise SystemExit(
            f"run_sims.py: {spec} names the rotation {APL[spec]}, which is not "
            f"under {WOWSIMS / 'ui'}. Falling back to Auto would return a "
            "plausible smaller number instead of an error, so this stops.")
    return json.loads(path.read_text())


def proto_field_types() -> dict:
    r"""Every buff field and its proto type, read rather than assumed.

    THE CLOSING BRACE MUST BE ANCHORED. `\n\}` first matched the brace at the
    end of the NEXT message, because RaidBuffs closes on an indented line, so
    RaidBuffs came back holding PartyBuffs' fields too and the one validation
    gate here would have accepted a party buff named under raid_wide. Found by
    a second review on 10 August 2026.

    THE TYPES ARE MIXED AND GUESSING FAILS LOUDLY. Sending `true` to a tristate
    field is rejected by the simulator with "invalid value for enum field",
    which is the good case; sending a bool where an int32 is wanted would be
    accepted in some encoders and silently mean something else.
    """
    text = PROTO.read_text()
    out: dict = {}
    for name in ("RaidBuffs", "PartyBuffs", "IndividualBuffs", "Debuffs"):
        # SPLIT ON THE NEXT MESSAGE, not on a closing brace. RaidBuffs closes
        # with an INDENTED brace in this proto, so every brace-anchored pattern
        # ran past it into PartyBuffs and reported 44 fields where there are 7.
        start = text.index(f"message {name} {{")
        rest = text[start:]
        nxt = re.search(r"\n(?://[^\n]*\n)*message \w+ \{", rest[1:])
        block = type("M", (), {"group": lambda self, n: rest[:nxt.start() + 1]
                               if nxt else rest})()
        fields = {}
        for kind, field in re.findall(
                r"^\s+([\w.]+)\s+(\w+)\s*=\s*\d+", block.group(1), re.M):
            parts = field.split("_")
            camel = parts[0] + "".join(w.title() for w in parts[1:])
            fields[camel] = kind
        out[name] = fields
    return out


def typed(name: str, kind: str):
    """The value this field wants, for a buff this raid supplies."""
    if kind == "bool":
        return True
    if kind == "TristateEffect":
        return "TristateEffectImproved" if name in IMPROVED \
            else "TristateEffectRegular"
    if kind == "int32":
        return COUNTS.get(name, 1)
    if kind == "Drums":
        return COUNTS.get("drums")
    if kind == "double":
        # A DOUBLE USED TO BE UNSENDABLE BY CONSTRUCTION, and that silently
        # decided a question rather than deferring it. Returning None here meant
        # `expose_weakness_uptime` and `expose_weakness_hunter_agility` could
        # never reach the simulator no matter what raid-buffs.yaml said, so the
        # raid's Survival Hunter contributed nothing to anyone else all along.
        # RULED IN by the guild lead on 15 August 2026.
        return DOUBLE_FIELDS.get(name)
    return None


# A SPEC MAY NOT BE HANDED A BUFF IT IS ITSELF THE SOURCE OF.
#
# raid-buffs.yaml names which spec supplies each party buff and each debuff, and
# run_sims.py then delivered every one of them to every member of the party
# INCLUDING the supplier. That is wrong in two different ways depending on the
# buff, and both were measured on 15 August 2026.
#
# A STAT DOUBLE COUNT, where the simulator declares no exclusive category, so the
# supplier receives the effect twice. Totem of Wrath is the case: sim/core/
# buffs.go declares an ExclusiveCategory for Strength of Earth, Grace of Air,
# Mana Spring and Wrath of Air, and NOT for Totem of Wrath, so the Elemental
# Shaman took 6 percent spell hit and crit where it earns 3. Worth 62 to 75 DPS
# of pure over-credit.
#
# A GCD SUBSIDY, where the category does exist so the stats do not stack, but the
# supplier never has to spend the global cooldown supplying it. The Balance
# Druid casts Faerie Fire 5.56 times a pull when it is not handed the debuff and
# 0.00 times when it is, and the Enhancement Shaman twists Grace of Air the same
# way. Worth 55.3 and 11.2.
#
# EVERY OTHER MEMBER OF THE PARTY STILL RECEIVES ALL OF THEM. Only the supplier
# is skipped, which is what makes this a correction rather than a nerf.
SELF_SUPPLIED = {
    ("elemental_shaman", "totemOfWrath"):
        "no ExclusiveCategory in sim/core/buffs.go, so the supplier stacked it "
        "with its own cast: 62 to 75 DPS of double count",
    ("balance_druid", "faerieFire"):
        "a GCD subsidy: handed the debuff the druid casts it 0.00 times a pull, "
        "denied it 5.56 times, worth 55.3 DPS it never paid for",
    ("enhancement_shaman", "graceOfAirTotem"):
        "the same, for the totem this spec twists itself: 11.2 DPS",
    # THE SHADOW PRIEST IS ITS OWN MANA DONOR. run_sims.py grants
    # shadowPriestDps to everyone in g4 and the Shadow Priest sits in g4, so it
    # credited itself 287.5 MP5 of its own Vampiric Touch on top of the
    # Vampiric Touch its rotation already casts. It measures 0.0 today ONLY
    # because this spec never runs out of mana in this encounter, so it is a
    # correctness fix taken before some future change makes it bite.
    ("shadow_priest", "shadowPriestDps"):
        "the priest is the donor; measured 0.0 today because it never goes out "
        "of mana, and wrong regardless",
}


def buffs_for(spec: str, buffs: dict, party_of: dict) -> tuple[dict, dict, dict]:
    """The raid buffs, this spec's PARTY buffs, and the boss debuffs.

    PARTY IS THE WHOLE POINT. A totem, an aura and a shout reach the caster's
    party and not the raid in 2.4.3, so a spec in g4 gets nothing from the
    Elemental Shaman's Totem of Wrath in g3. This project has published a wrong
    figure by forgetting that once.
    """
    types = proto_field_types()

    def build(names, message):
        out = {}
        for raw in names:
            if raw == "note":
                continue
            parts = raw.split("_")
            camel = parts[0] + "".join(w.title() for w in parts[1:])
            kind = types[message].get(camel)
            if kind is None:
                raise SystemExit(
                    f"run_sims.py: raid-buffs.yaml names {raw!r}, which is not "
                    f"a field of {message} in {PROTO}. A buff this raid cannot "
                    "express is a mistake in one of the two files.")
            if (spec, camel) in SELF_SUPPLIED:
                continue
            value = typed(camel, kind)
            if value is not None:
                out[camel] = value
        return out

    party_name = party_of.get(spec)
    raid = build(buffs.get("raid_wide") or {}, "RaidBuffs")
    party = build((buffs.get("party") or {}).get(party_name) or {}, "PartyBuffs")
    debuffs = build(buffs.get("debuffs") or {}, "Debuffs")
    return raid, party, debuffs


def consumables_for(spec: str, anchor: str) -> dict:
    """The ConsumesSpec this spec drinks, read from the resolved fact table.

    NO ID IS WRITTEN HERE. `consumable-ids.yaml` holds the name, the id and the
    file each id was read from, so a reader can check that the flask the run
    drank is the flask the guide named. An id in this script would be a number
    nobody can audit, and a wrong one does not fail: the run succeeds and the
    DPS is quietly wrong.

    A MISSING SPEC STOPS THE RUN rather than running dry. Unbuffed by flask,
    food and oil, a spec loses roughly a tenth of its damage and still returns
    a plausible-looking figure, which is the failure this project keeps meeting.

    DRUMS ARE NOT HERE ON PURPOSE. raid-buffs.yaml already gives every party its
    drums through PartyBuffs, so a drums_id would count them twice.
    """
    doc = yaml.safe_load(CONSUMABLES.read_text())
    # THE PICK IS PER ANCHOR, because two of its three inputs are. The weapon
    # class decides which stone, and the hit cap decides which food, and both
    # move with the gear: this roster's Beast Mastery hunter swings Fist weapons
    # at entry and a dagger and a sword at best in slot, which is a Weightstone
    # in one and a Sharpening Stone in the other. A per-spec lookup answered one
    # anchor and was silently wrong for the others.
    by_anchor = (doc.get("picks") or {}).get(spec)
    if by_anchor is None:
        raise SystemExit(
            f"run_sims.py: {spec} has no entry in {CONSUMABLES}. Regenerate it "
            "with `just regen`; running a spec with no consumables returns a "
            "smaller number rather than an error.")
    picks = by_anchor.get(anchor)
    if picks is None:
        raise SystemExit(
            f"run_sims.py: {spec} has no consumables recorded for the anchor "
            f"{anchor!r} in {CONSUMABLES}, which holds "
            f"{sorted(by_anchor)}. Regenerate with `just regen` so the "
            "consumable table covers every exported profile.")
    out = {}
    for field, entry in picks.items():
        parts = field.split("_")
        camel = parts[0] + "".join(w.title() for w in parts[1:])
        out[camel] = entry["id"]
    # `potId` ALONE DRINKS NOTHING. sim/core/consumes.go::registerPotionCD
    # iterates `consumes.Potions` and registers a cooldown only for an id in
    # THAT list; potId merely marks which entry of the list is the combat
    # potion. With `potions` empty the loop body never runs, no potion is ever
    # drunk, and the run succeeds with a quietly smaller number. The simulator's
    # own UI fills the list, at ui/core/player.ts. Measured on 15 August 2026:
    # the Arms Warrior's entry anchor rose 3.1 percent when the list was sent.
    if "potId" in out:
        out["potions"] = [out["potId"]]
    # THE PRESET'S OWN CONSUMABLES, added after the guide-sourced picks so a
    # guide never loses to a preset. Nothing here overlaps a guide field today.
    for field, value in PRESET_CONSUMABLES.get(spec, {}).items():
        out.setdefault(field, value)
    # AND THE ONE PLACE A GUIDE PICK IS OVERRIDDEN, loudly and with its reason
    # carried in the table rather than here.
    for (that_spec, field), (value, _why) in IMBUE_OVERRIDE.items():
        if that_spec == spec:
            out[field] = value
    # THE MAIN-HAND IMBUE IS DROPPED IN A WINDFURY PARTY, and the off-hand one
    # is not. sim/core/consumes.go applies MhImbueId only when the party carries
    # no Windfury Totem, because the totem overwrites the imbue in 2.4.3, while
    # OhImbueId is applied unconditionally. Every melee spec in g1 and g2 sits
    # under a Windfury Totem in raid-buffs.yaml, so a main-hand stone changes
    # nothing for them and an off-hand stone is live damage. Measured on
    # 15 August 2026: correcting the Beast Mastery main-hand stone to the type
    # its Fist weapon takes moved the result 0.0, and adding the off-hand stone
    # both hunters were missing moved it 26.1 and 29.6. A reader measuring a
    # main-hand imbue and reading zero is meeting this gate, not a rejected id.
    return out


def build_request(spec: str, gear: dict, talents: str, iterations: int,
                  seed: int, buffs: dict, party_of: dict, anchor: str,
                  seconds: int = ENCOUNTER_SECONDS,
                  armor: int = DEFAULT_ARMOR) -> dict:
    """One RaidSimRequest: one player, alone, against the fixed encounter.

    THE ANCHOR IS NOT DECORATION. It selects the consumables, because the stone
    a spec takes follows the weapon it holds and the food follows whether that
    set is hit-capped. Both are properties of the gear, so both are per anchor.
    """
    klass, oneof = SPECS[spec]
    rotation = rotation_for(spec)
    raid_buffs, party_buffs, debuffs = buffs_for(spec, buffs, party_of)
    # THE HUNTER SUPPLYING EXPOSE WEAKNESS IS AT THE SAME ANCHOR AS EVERYONE
    # ELSE, so its agility moves with the anchor and the debuff moves with it.
    # An anchor with no measured figure keeps the default rather than inventing
    # one, which is what an alternative profile such as the Arms refuse-head run
    # takes.
    if "exposeWeaknessHunterAgility" in debuffs:
        debuffs["exposeWeaknessHunterAgility"] = EXPOSE_WEAKNESS_AGILITY.get(
            anchor, DOUBLE_FIELDS["exposeWeaknessHunterAgility"])
    # Kings to everyone, and the split blessing by what the spec can use. These
    # go through the same typed builder as the rest: Kings is a bool and the
    # other two are tristates, and sending true to a tristate is rejected.
    # THE INDIVIDUAL BLOCK USED TO BE DECLARED AND NEVER READ. raid-buffs.yaml
    # recorded unleashed_rage and shadow_priest_dps, and this function wrote
    # neither, so eight physical specs lost roughly ten percent attack power and
    # the Arcane Mages lost their Shadow Priest mana. Found on 10 August 2026.
    types = proto_field_types()
    individual = {}
    # THREE PALADINS MAINTAIN THREE BLESSINGS, so every spec receives all three.
    # RULED by the guild lead on 15 August 2026: "include paladin blessings ofc".
    #
    # THIS REPLACES AN EITHER/OR SPLIT THAT CONTRADICTED ITS OWN PREMISE. The
    # ruling recorded in capture-fidelity.yaml says in its own words that three
    # paladins can maintain three blessings, and the code then handed each spec
    # Kings plus exactly ONE of Might and Wisdom, chosen by whether the spec was
    # physical. For a mage that is harmless, because Might is dead weight on a
    # caster, and for a rogue Wisdom is dead weight on an energy user. FOR THE
    # RETRIBUTION PALADIN BOTH ARE LIVE, and it was the one spec the split
    # actually cost: it sat 57.9 seconds out of mana of a 150 second fight, and
    # Blessing of Wisdom alone is worth 91 to 97 DPS to it.
    #
    # BOTH ARE SENT AS REGULAR, NOT IMPROVED, and that is deliberate. Improved
    # Blessing of Might is a Retribution talent and this roster's paladin decodes
    # it 0 of 5, verified independently by two arbiters against the proto field
    # numbers. Improved Blessing of Wisdom is a HOLY talent and this project has
    # never decoded the Holy Paladin's build at all, so claiming it would be
    # inventing a roster fact.
    wanted = ["blessingOfKings", "blessingOfMight", "blessingOfWisdom"]
    if spec in PHYSICAL and party_of.get(spec) in ("g1", "g2"):
        wanted.append("unleashedRage")   # Enhancement decodes unleashedRage 5/5
    if party_of.get(spec) == "g4":
        wanted.append("shadowPriestDps")  # the Shadow Priest shares g4
    for field in wanted:
        if (spec, field) in SELF_SUPPLIED:
            continue
        value = typed(field, types["IndividualBuffs"][field])
        if value is not None:
            individual[field] = value
    player = {
        "name": spec,
        # THE ROSTER IS READ ONCE. This used to parse roster.yaml on every
        # request, which a --swap sweep issues once per candidate.
        "race": race_of(spec, klass, _ROSTER_CACHE.get("doc") or
                        _ROSTER_CACHE.setdefault(
                            "doc", yaml.safe_load(ROSTER.read_text()))),
        "class": CLASS[klass],
        # ONLY THE ITEMS ARE SENT. A profile carrying a substitution also
        # carries a `_divergence` list, written by export_sim_profiles.py so the
        # warning travels with the file. That key belongs to this project and
        # not to proto Equipment, and it is dropped HERE rather than left to the
        # simulator to ignore: an encoder that ignores unknown fields today is
        # not a promise, and a rejected request would read as a broken profile.
        "equipment": {"items": gear["items"]},
        "talentsString": talents,
        # 100 MILLISECONDS, NOT ZERO. sim/core/character.go:109 reads
        # max(ReactionTimeMs, 10), so an unset field is a 10 ms reaction rather
        # than a human one, and 100 is the wowsims universal UI default for every
        # spec rather than a hunter quirk. THE EFFECT IS BIDIRECTIONAL and is not
        # a uniform realism tax: Survival loses 23.7 and Retribution GAINS 31.0,
        # reproducibly across three seeds. A spec that gains DPS from a slower
        # reaction has a timing-fragile rotation, which is worth knowing about
        # Retribution in particular, whose list also omits Hammer of Wrath.
        "reactionTimeMs": 100,
        "consumables": consumables_for(spec, anchor),
        "buffs": individual,
        "rotation": rotation,
        # `classOptions` MUST BE PRESENT, even empty. Sending `options: {}`
        # alone panics the simulator with a nil dereference rather than
        # defaulting, which cost an hour to find because the panic names no
        # field. Every spec block the presets ship writes it explicitly.
        oneof: {"options": {"classOptions": CLASS_OPTIONS.get(spec, {}),
                            **SPEC_OPTIONS.get(spec, {})}},
    }
    return {
        "raid": {
            # ONE PLAYER IN ONE PARTY, carrying that party's buffs. The rest of
            # the raid is not simulated; its contribution is the buff and debuff
            # lists, which is why they are derived from roster.yaml rather than
            # switched on wholesale.
            "parties": [{"players": [player], "buffs": party_buffs}],
            "buffs": raid_buffs,
            "debuffs": debuffs,
        },
        "encounter": encounter_for(seconds, armor),
        "simOptions": {"iterations": iterations, "randomSeed": str(seed)},
    }


def item_names() -> dict:
    """Every item id this tool can name, from both tables that hold names.

    items.csv IS SCOPED TO PHASE 3 AND PRE-PHASE GEAR, so three best-in-slot
    items are absent from it: `Badge of the Swarmguard` is an AQ40 trinket and
    `Barrel-Blade Longrifle` is outside the compendium's slot scope. Read from
    items.csv alone they printed as bare ids in a diagnostic whose whole purpose
    is telling a reader which item moved a figure, and a bare id is how this
    project dispositioned an item on its name four times.
    """
    names = {int(r["item_id"]): r["name"]
             for r in csv.DictReader(ITEMS.open())} if ITEMS.is_file() else {}
    db = WOWSIMS / "assets" / "database" / "db.json"
    if db.is_file():
        for item in json.loads(db.read_text()).get("items") or []:
            names.setdefault(item["id"], item["name"])
    return names


def dress_from(gear: dict, other: dict, slots: list[str]) -> dict:
    """A copy of the gear wearing another profile's slots, enchants and all.

    THIS IS THE OPPOSITE CHOICE FROM `swap_into`, AND BOTH ARE RIGHT. `--swap`
    answers "what is this item worth", so the candidate arrives bare and the
    enchant question is kept separate. This answers "which SLOT explains the
    difference between two whole sets", and there the enchant and the gems
    belong to the slot: dressing one side and not the other would credit a
    Mongoose enchant to the item that happened to be underneath it. Measured on
    15 August 2026, replacing an item with ITSELF through `--swap` read minus
    56.1 DPS on the Arms Warrior main hand, which is the enchant, not the item.

    A slot the other profile leaves empty is emptied here, because a two-handed
    weapon displacing an off hand is precisely one of the differences this is
    asked to price.
    """
    out = {"items": [dict(entry) for entry in gear["items"]]}
    for slot in slots:
        index = SLOT_ORDER.index(slot)
        out["items"][index] = dict(other["items"][index])
    return out


def swap_into(gear: dict, slot: str, item_id: int) -> dict:
    """A copy of the gear with one slot replaced.

    ITEM ID 0 EMPTIES THE SLOT, which is what a two-hander needs: taking one
    means the off hand holds nothing, and a comparison that left the old off
    hand in place would credit the two-hander with a weapon it displaces.

    The enchant and the gems go with the old item, deliberately. They belonged
    to it, and carrying them onto a different item would silently move stats the
    new item does not have. A swapped slot is bare until this project decides
    what a candidate should be enchanted and gemmed with, which is a separate
    question from what the item is worth.
    """
    out = {"items": [dict(entry) for entry in gear["items"]]}
    index = SLOT_ORDER.index(slot)
    out["items"][index] = {"id": item_id} if item_id else {}
    return out


def run(cli: Path, request: dict) -> tuple[float | None, float | None, str | None]:
    """One simulation. Returns the DPS and its spread, or the simulator's error.

    THE SPREAD IS THE POINT OF THE SECOND FIGURE. `avg` alone invites a reader
    to treat a 4 DPS gap as a result. `stdev` is the spread ACROSS ITERATIONS,
    which is how much one pull of this encounter varies, and the uncertainty on
    the MEAN of `n` of them is that divided by the square root of `n`. Both are
    returned raw and neither is combined here, because the number of iterations
    belongs to the caller.
    """
    with tempfile.TemporaryDirectory() as tmp:
        infile = Path(tmp) / "in.json"
        outfile = Path(tmp) / "out.json"
        infile.write_text(json.dumps(request))
        proc = subprocess.run(
            [str(cli), "sim", "--infile", str(infile), "--outfile", str(outfile)],
            capture_output=True, text=True)
        if not outfile.is_file():
            return None, None, (proc.stderr or proc.stdout
                                or "no output").strip()[:200]
        result = json.loads(outfile.read_text())
    if result.get("error"):
        # The stack trace is the least useful part of a simulator error, and the
        # first line is nearly always the whole answer.
        return None, None, str(result["error"].get("message", "")).split("\n")[0]
    metrics = (result.get("raidMetrics") or {}).get("dps") or {}
    return metrics.get("avg"), metrics.get("stdev"), None


def against(args, strings: dict, iterations: int) -> int:
    """Two whole profiles, and which slot explains the gap between them.

    THE WHOLE-SET DIFFERENCE IS PRINTED BESIDE THE SUM OF THE PARTS, and they do
    not agree. Set bonuses, hit caps and crit suppression are not additive, so a
    slot list that sums to plus 48.8 against a whole-set difference of plus
    108.4 is telling the truth about both: no single slot is the answer, and the
    set is worth more than its slots. Printing only one of the two figures would
    invite a reader to treat the slot list as a decomposition, which it is not.
    """
    a_path = args.gear / f"{args.profile}.gear.json"
    b_path = args.gear / f"{args.against}.gear.json"
    for path in (a_path, b_path):
        if not path.is_file():
            print(f"error: no profile at {path}", file=sys.stderr)
            return 1
    spec = args.profile.partition(".")[0].replace("-", "_")
    if spec != args.against.partition(".")[0].replace("-", "_"):
        print("error: --profile and --against name two different specs. A "
              "cross-spec comparison is not a slot question and this project "
              "does not rank one spec against another.", file=sys.stderr)
        return 1
    if spec in NOT_SIMULATABLE:
        print(f"error: {spec} cannot be simulated in this build: "
              f"{NOT_SIMULATABLE[spec]}", file=sys.stderr)
        return 1

    talents = (strings.get(spec) or {}).get("string")
    a = json.loads(a_path.read_text())
    b = json.loads(b_path.read_text())
    names = item_names()
    buffs = yaml.safe_load(BUFFS.read_text())
    roster = yaml.safe_load(ROSTER.read_text())
    party_of = {}
    for group in roster.get("groups") or []:
        for member in group.get("members") or []:
            party_of.setdefault(member, group["id"])

    # BOTH SIDES DRINK THE BASELINE'S CONSUMABLES. This measures which SLOT
    # explains a gap, so the consumables are part of what is held still; letting
    # each side take its own anchor's stone would fold a consumable difference
    # into whichever slot happened to carry the weapon.
    anchor = args.profile.partition(".")[2].replace("-", "_")

    def measure(gear):
        dps, _spread, error = run(args.cli, build_request(
            spec, gear, talents, iterations, args.seed, buffs, party_of,
            anchor, args.seconds, args.armor))
        if error:
            raise SystemExit(f"run_sims.py: {error}")
        return dps

    slots = [s for s in (args.slot.split(",") if args.slot else SLOT_ORDER)
             if a["items"][SLOT_ORDER.index(s)]
             != b["items"][SLOT_ORDER.index(s)]]
    base = measure(a)
    whole = measure(b)
    print(f"{args.profile} against {args.against}, {iterations} iterations\n")
    print(f"  {'baseline':44s} {base:9.1f}")
    rows = []
    for slot in slots:
        rows.append((measure(dress_from(a, b, [slot])) - base, slot))
    for delta, slot in sorted(rows):
        index = SLOT_ORDER.index(slot)
        was = (a["items"][index] or {}).get("id")
        now = (b["items"][index] or {}).get("id")
        print(f"  {slot:11s} {delta:+8.1f}   "
              f"{names.get(was, 'empty' if not was else was)} -> "
              f"{names.get(now, 'empty' if not now else now)}")
    print(f"\n  sum of the single-slot deltas {sum(r[0] for r in rows):+8.1f}")
    print(f"  whole-set difference          {whole - base:+8.1f}")
    print("  The two do not agree, and neither is wrong. Set bonuses and cap "
          "positions are not additive.")
    return 0


def compare(args, strings: dict, iterations: int) -> int:
    """One profile, one or more slots, several candidates, against a baseline.

    THE BASELINE IS RUN FIRST AND WITH THE SAME SEED. Two simulations of the
    same gear with different seeds differ by a few DPS, and an item worth a few
    DPS is exactly the kind this is asked about, so the seed is held and the
    difference is attributable to the item alone.

    SEVERAL SLOTS AT ONCE, because some items cannot be valued alone. A trinket
    is the case that forced it: Dragonspine Trophy is worth one thing beside an
    attack power trinket and another beside an armor penetration one, so varying
    the second while holding the first fixed answers a question nobody asked.
    A two-handed weapon is the other case, since taking one empties the off hand.

    `--slot a,b --swap 1,2 --swap 3,4` fills a with 1 and b with 2, then a with
    3 and b with 4. THE DOCSTRING PROMISED THIS FOR DAYS AND THE PARSER DID NOT
    DELIVER IT: `--slot` was single-valued, so `--slot main_hand --slot off_hand`
    silently kept only the last one and the run measured something other than
    what was asked. A single slot and a single id still work unchanged.
    """
    if not args.profile:
        print("error: --profile is required when swapping", file=sys.stderr)
        return 1
    if not args.slot:
        print("error: --slot is required when swapping", file=sys.stderr)
        return 1
    slots = [s.strip() for s in args.slot.split(",") if s.strip()]
    for slot in slots:
        if slot not in SLOT_ORDER:
            print(f"error: {slot!r} is not a slot. One of: "
                  f"{', '.join(SLOT_ORDER)}", file=sys.stderr)
            return 1
    candidates = []
    for raw in args.swap:
        ids = [int(x) for x in str(raw).split(",")]
        if len(ids) != len(slots):
            print(f"error: --swap {raw!r} names {len(ids)} item(s) for "
                  f"{len(slots)} slot(s). Every --swap has to fill every slot "
                  "named in --slot, so that each run is a complete "
                  "configuration rather than a partial one.", file=sys.stderr)
            return 1
        candidates.append(ids)

    path = args.gear / f"{args.profile}.gear.json"
    if not path.is_file():
        print(f"error: no profile at {path}", file=sys.stderr)
        return 1
    spec = args.profile.partition(".")[0].replace("-", "_")
    if spec in NOT_SIMULATABLE:
        print(f"error: {spec} cannot be simulated in this build: "
              f"{NOT_SIMULATABLE[spec]}", file=sys.stderr)
        return 1
    talents = (strings.get(spec) or {}).get("string")
    gear = json.loads(path.read_text())

    names = item_names()
    worn = [(gear["items"][SLOT_ORDER.index(s)] or {}).get("id") for s in slots]

    def label_of(ids):
        return " + ".join(
            names.get(i, "empty" if not i else str(i)) for i in ids)

    buffs = yaml.safe_load(BUFFS.read_text())
    roster = yaml.safe_load(ROSTER.read_text())
    party_of = {}
    for group in roster.get("groups") or []:
        for member in group.get("members") or []:
            party_of.setdefault(member, group["id"])
    anchor = args.profile.partition(".")[2].replace("-", "_")
    base, _spread, error = run(args.cli, build_request(
        spec, gear, talents, iterations, args.seed, buffs, party_of, anchor,
        args.seconds, args.armor))
    if error:
        print(f"error: the baseline failed: {error}", file=sys.stderr)
        return 1
    print(f"{args.profile}, varying {', '.join(slots)}, "
          f"{iterations} iterations\n")
    print(f"  {'baseline':52s} {base:9.1f}        {label_of(worn)}")

    rows = []
    for ids in candidates:
        candidate = gear
        for slot, item_id in zip(slots, ids):
            candidate = swap_into(candidate, slot, item_id)
        dps, _spread, error = run(args.cli, build_request(
            spec, candidate, talents, iterations, args.seed, buffs, party_of,
            anchor, args.seconds, args.armor))
        if error:
            print(f"  {label_of(ids):<52} FAILED  {error}", file=sys.stderr)
            continue
        rows.append((ids, dps, dps - base))
    for ids, dps, delta in sorted(rows, key=lambda r: -r[1]):
        print(f"  {label_of(ids)[:52]:52s} {dps:9.1f} {delta:+8.1f}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gear", type=Path, default=GEAR)
    ap.add_argument("--cli", type=Path,
                    # THE DEFAULT IS WHERE tools/install_wowsimcli.sh PUTS IT. It used to
                    # be /tmp/wowsimcli, which is a path that survives until the
                    # next reboot and then produces a missing-binary error that
                    # reads like a broken tool rather than a cleared temp
                    # directory. WOWSIMCLI still overrides it.
                    default=Path(os.environ.get(
                        "WOWSIMCLI", "vendor/wowsims/wowsimcli")))
    ap.add_argument("--iterations", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--profile", help="one profile stem, such as "
                                      "combat-rogue.tier-hands-only")
    ap.add_argument("--slot", help=f"which slot to vary, or several separated "
                                   f"by commas. One of: {', '.join(SLOT_ORDER)}")
    ap.add_argument("--swap", action="append", default=[],
                    help="an item id to try, or one id per slot separated by "
                         "commas, matching --slot in order. Repeatable. 0 "
                         "empties a slot, which is what a two-hander needs")
    ap.add_argument("--all-tiers", action="store_true",
                    help="Sweep every profile at EVERY armor tier the boss "
                         "table derives, writing boss_armor per row. This is "
                         "what `just sim` sends, so the figures file holds "
                         "all three tiers rather than one run's worth.")
    ap.add_argument("--armor", type=int, default=DEFAULT_ARMOR,
                    help=f"boss armor. Default {DEFAULT_ARMOR}, the highest "
                         "Phase 3 tier, per the guild lead's ruling; ten of "
                         "the fourteen bosses sit at 6193. "
                         "data/facts/boss-armor.yaml holds one row per boss "
                         "with a source each. --out stamps the value used")
    ap.add_argument("--seconds", type=int, default=ENCOUNTER_SECONDS,
                    help=f"encounter length. Default {ENCOUNTER_SECONDS}, the "
                         "ruling of 14 August 2026. A figure produced at any "
                         "other length is NOT comparable with the recorded ones "
                         "and --out stamps the length it used")
    ap.add_argument("--against", help="a second profile stem. Prints which "
                                      "slot explains the gap between the two, "
                                      "carrying each slot's enchant and gems")
    ap.add_argument("--out", type=Path,
                    help="write every result, with its spread, to this YAML "
                         "file. Omitted, the run only prints")
    ap.add_argument("--check", action="store_true",
                    help="run every profile once, cheaply, and report only "
                         "whether it runs")
    args = ap.parse_args()

    if not args.cli.is_file():
        print(f"error: no simulator at {args.cli}. Build it with\n"
              f"  go build -o {args.cli} ./cmd/wowsimcli\n"
              "from the wowsims checkout.", file=sys.stderr)
        return 1

    strings = yaml.safe_load(TALENTS.read_text())["wowsims_talent_strings"]["strings"]
    buffs = yaml.safe_load(BUFFS.read_text())
    roster = yaml.safe_load(ROSTER.read_text())
    # WHICH PARTY EACH SPEC SITS IN, read from the roster rather than restated.
    # A spec appearing in two parties, as the Enhancement Shaman does, takes the
    # first.
    #
    # SOMETHING DOES TURN ON IT, and this comment used to say otherwise. The
    # totems ARE the same in g1 and g2, which is what the old wording checked,
    # but g1 carries Sanctity Aura and g2 carries Ferocious Inspiration. Sanctity
    # Aura is holy damage and worth nothing to a shaman; Ferocious Inspiration is
    # 3 percent to all damage. Measured 15 August 2026: g2 is worth plus 25.1 DPS
    # over g1 at best in slot, and plus 23.7 at entry.
    #
    # WHICH PARTY THE SHAMAN ACTUALLY SITS IN IS A ROSTER FACT, not a modelling
    # choice, so this tool keeps taking the first and the question goes to the
    # guild lead rather than being settled here. The old comment told a reader
    # not to look.
    party_of = {}
    for group in roster.get("groups") or []:
        for member in group.get("members") or []:
            party_of.setdefault(member, group["id"])
    iterations = 100 if args.check else args.iterations

    if args.against:
        return against(args, strings, iterations)
    if args.swap or args.slot or args.profile:
        return compare(args, strings, iterations)

    # THE ARMOR TIERS COME FROM THE FACT FILE, derived rather than copied, so
    # a corrected boss row moves the sweep without anyone re-deriving a list.
    # A boss whose armor points at its parts contributes its parts, a part the
    # DPS never attacks contributes nothing, and Veras Darkshadow's None is
    # skipped because near-zero with the digits unestablished is not a number
    # a request can carry.
    if args.all_tiers:
        by_armor: dict[int, list[str]] = {}
        armor_doc = yaml.safe_load(BOSS_ARMOR.read_text())
        for entry in armor_doc["bosses"]:
            if isinstance(entry.get("armor"), int):
                by_armor.setdefault(entry["armor"], []).append(entry["boss"])
        for entry in armor_doc.get("parts") or []:
            if isinstance(entry.get("armor"), int) and entry.get("dps_attacks_it"):
                by_armor.setdefault(entry["armor"], []).append(entry["part"])
        armors = sorted(by_armor, reverse=True)
        armor_tiers_run = {a: sorted(by_armor[a]) for a in armors}
    else:
        armors = [args.armor]
        armor_tiers_run = None

    rows, failures, skipped = [], [], []
    for armor in armors:
        if len(armors) > 1:
            print(f"\nboss armor {armor}:")
        for path in sorted(args.gear.glob("*.gear.json")):
            stem = path.name[:-len(".gear.json")]
            spec_slug, _, anchor = stem.partition(".")
            spec = spec_slug.replace("-", "_")
            if spec in NOT_SIMULATABLE:
                if armor == armors[0]:
                    skipped.append(f"{stem}: {NOT_SIMULATABLE[spec]}")
                continue
            if spec not in SPECS:
                failures.append((stem, f"{spec} is not a DPS spec this tool knows"))
                continue
            talents = (strings.get(spec) or {}).get("string")
            if not talents:
                failures.append((stem, "no talent string recorded"))
                continue
            dps, spread, error = run(args.cli, build_request(
                spec, json.loads(path.read_text()), talents, iterations,
                args.seed, buffs, party_of, anchor.replace("-", "_"),
                args.seconds, armor))
            if error:
                failures.append((stem, error))
            else:
                # ONE STANDARD ERROR, RULED BY THE GUILD LEAD ON 15 AUGUST 2026,
                # shown both options. It is stdev over the square root of the
                # iteration count, and it covers about 68 percent rather than 95.
                # THAT LABEL MATTERS: calling this "the confidence interval" would
                # let a reader read two barely-overlapping figures as settled when
                # the 95 percent intervals would still overlap by a wide margin. It
                # is printed and recorded as `standard_error` for that reason and is
                # never to be called a 95 percent interval.
                stderr = (spread / math.sqrt(iterations)) if spread else None
                rows.append({"profile": stem, "spec": spec, "anchor": anchor,
                             "dps": round(dps, 1),
                             "standard_error": round(stderr, 2) if stderr else None,
                             "stdev": round(spread, 1) if spread else None,
                             "boss_armor": armor})
                flag = "   <-- IMPLAUSIBLE" if dps < IMPLAUSIBLE else ""
                pm = f" +/- {stderr:5.2f}" if stderr else " " * 11
                print(f"  {stem:52s} {dps:9.1f}{pm}{flag}")

    if skipped:
        print(f"\n{len(skipped)} profile(s) skipped as not simulatable:")
        for line in skipped:
            print(f"  {line}")
    low = [(r["profile"], r["dps"]) for r in rows if r["dps"] < IMPLAUSIBLE]
    if args.out:
        meta = {
            "generated_by": "tools/run_sims.py",
            "simulator": (Path("vendor/wowsims/VERSION").read_text().strip()
                          if Path("vendor/wowsims/VERSION").is_file()
                          else "unrecorded"),
            "iterations": iterations,
            "seed": args.seed,
            "encounter_seconds": args.seconds,
            "boss_armor_source": (
                "data/facts/boss-armor.yaml, one row per boss with a source "
                "each. Phase 3 spans two tiers and a figure at one is NOT "
                "comparable with a figure at the other."),
            "targets": 1,
            "target_level": 73,
            "interval": (
                "`standard_error` is ONE standard error on the mean, stdev "
                f"over the square root of {iterations}. It covers about 68 "
                "percent, NOT 95. Ruled by the guild lead on 15 August "
                "2026, shown both options. Do not relabel it as a "
                "confidence interval."),
        }
        if args.all_tiers:
            # THE CONTEXT NOTES LIVE IN THE WRITER, not hand-merged into the
            # output, because a generated file that needs a hand edit after
            # every run is a generated file somebody will forget to edit. The
            # 15 August 2026 figures file was exactly that: a hand-merged
            # union of three single-tier runs, and a bare `just sim` would
            # have silently destroyed two of the tiers and all of the notes.
            meta["default_tier"] = (
                "7684, the highest tier, ruled by the guild lead on 20 "
                "August 2026: decisions assume the hardest target. Ten of "
                "the fourteen Phase 3 bosses sit at 6193, and the per-tier "
                "rows keep every figure.")
            meta["the_zero_tier_is_one_target"] = (
                "Essence of Suffering alone, plus Veras Darkshadow, whose "
                "armor is near-zero with the digits unestablished. Run "
                "because the guild lead ruled per boss, and a target with no "
                "armor is a real part of two encounters.")
            meta["expose_weakness"] = (
                "The Survival Hunter's agility is MEASURED per anchor by "
                "bisection, 1119 entry, 1105 tier, 1152 best in slot, with "
                "the uptime measured at 0.98. See data/facts/raid-buffs.yaml. "
                "It was the simulator's generic 1210 for a few hours on 15 "
                "August 2026 and that was 5 to 9 percent high for this "
                "roster.")
            meta["armor_tiers_run"] = armor_tiers_run
            meta["the_no_glaive_anchor"] = (
                "fury_warrior and combat_rogue each carry a second "
                "best-in-slot profile, bis_no_glaives, identical in every "
                "slot except the two weapons. Both specs' published Phase 3 "
                "lists rank the Warglaives of Azzinoth and the raid holds "
                "one pair, so at most one of them can be the `bis` row and "
                "the other is this one. The replacement weapons were found "
                "by running all 33 candidates Phase 3 can supply, not "
                "chosen.")
        else:
            meta["boss_armor"] = args.armor
        args.out.write_text(yaml.safe_dump({
            "meta": meta,
            "results": rows,
        }, sort_keys=False, width=78))
        print(f"\n{len(rows)} result(s) -> {args.out}")
    print(f"\n{len(rows)} profile(s) ran, {len(failures)} failed")
    if low:
        print(f"\n{len(low)} result(s) below {IMPLAUSIBLE:g} DPS. A profile that "
              "runs is not a profile that modelled anything, and these did not:",
              file=sys.stderr)
        for stem, dps in low:
            print(f"  {stem}: {dps:.1f}", file=sys.stderr)
    if failures:
        print(f"\n{len(failures)} failure(s):", file=sys.stderr)
        for stem, why in failures:
            print(f"  {stem}: {why}", file=sys.stderr)
    return 1 if (failures or low) else 0


if __name__ == "__main__":
    raise SystemExit(main())
