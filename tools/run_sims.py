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
import csv
import json
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
    "beast_mastery_hunter": "hunter/dps/apls/default.apl.json",
    "survival_hunter":      "hunter/dps/apls/default.apl.json",
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
# THREE MINUTES, ruled by the guild lead on 14 August 2026, replacing 150
# seconds. Every figure collected before that date was produced against the
# shorter encounter and is not comparable with one collected after it.
ENCOUNTER_SECONDS = 180

# THE CLASS OPTIONS EACH SPEC NEEDS, taken from the DefaultOptions its own
# preset ships. An empty block is not a safe default: a warlock with no armor,
# no pet and no curse returns about 65 DPS, which is a tenth of the real figure
# and looks like a number rather than a failure.
#
# Enum values are transcribed from proto/warlock.proto: Armor FelArmor is 1,
# Summon Succubus is 3, CurseOptions Recklessness is 3.
CLASS_OPTIONS = {
    "affliction_warlock": {"armor": 1, "summon": 3, "curseOptions": 3,
                           "sacrificeSummon": True},
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
    "enhancement_shaman": {"imbueMh": "WindfuryWeapon"},
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
    # THIS IS WRITTEN DOWN BECAUSE THE OPPOSITE LOOKS LIKE AN IMPROVEMENT. The
    # shipped preset at ui/shaman/enhancement/presets.ts sets DelayOffhandSwings,
    # and it measures 16.5 DPS higher on the entry anchor, so a reader comparing
    # our request against the preset finds a number sitting on the table and
    # reaches for it. It is declined, not overlooked.
    #
    # What the option does is space the off-hand around Flurry, whose internal
    # cooldown is the 500 ms constant ApplySyncType passes: two crits inside one
    # window waste the second. Auto selects DelayOffhandSwings for matched weapon
    # speeds, which is the pairing this spec runs, so Auto is not a neutral
    # choice here either. Both are sync, and both are declined.
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

ENCOUNTER = {
    "duration": ENCOUNTER_SECONDS,
    "durationVariation": 0,
    "targets": [{
        "level": 73,
        "mobType": 0,
        "stats": [0] * 48,
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
        # An uptime is a rotation outcome rather than a switch, so it is left
        # unset rather than invented. raid-buffs.yaml records which these are.
        return None
    return None


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
            value = typed(camel, kind)
            if value is not None:
                out[camel] = value
        return out

    party_name = party_of.get(spec)
    raid = build(buffs.get("raid_wide") or {}, "RaidBuffs")
    party = build((buffs.get("party") or {}).get(party_name) or {}, "PartyBuffs")
    debuffs = build(buffs.get("debuffs") or {}, "Debuffs")
    return raid, party, debuffs


def consumables_for(spec: str) -> dict:
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
    picks = (doc.get("picks") or {}).get(spec)
    if picks is None:
        raise SystemExit(
            f"run_sims.py: {spec} has no entry in {CONSUMABLES}. Regenerate it "
            "with `just regen`; running a spec with no consumables returns a "
            "smaller number rather than an error.")
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
                  seed: int, buffs: dict, party_of: dict) -> dict:
    """One RaidSimRequest: one player, alone, against the fixed encounter."""
    klass, oneof = SPECS[spec]
    rotation = rotation_for(spec)
    raid_buffs, party_buffs, debuffs = buffs_for(spec, buffs, party_of)
    # Kings to everyone, and the split blessing by what the spec can use. These
    # go through the same typed builder as the rest: Kings is a bool and the
    # other two are tristates, and sending true to a tristate is rejected.
    # THE INDIVIDUAL BLOCK USED TO BE DECLARED AND NEVER READ. raid-buffs.yaml
    # recorded unleashed_rage and shadow_priest_dps, and this function wrote
    # neither, so eight physical specs lost roughly ten percent attack power and
    # the Arcane Mages lost their Shadow Priest mana. Found on 10 August 2026.
    types = proto_field_types()
    individual = {}
    wanted = ["blessingOfKings",
              "blessingOfMight" if spec in PHYSICAL else "blessingOfWisdom"]
    if spec in PHYSICAL and party_of.get(spec) in ("g1", "g2"):
        wanted.append("unleashedRage")   # Enhancement decodes unleashedRage 5/5
    if party_of.get(spec) == "g4":
        wanted.append("shadowPriestDps")  # the Shadow Priest shares g4
    for field in wanted:
        value = typed(field, types["IndividualBuffs"][field])
        if value is not None:
            individual[field] = value
    player = {
        "name": spec,
        "race": 1,
        "class": CLASS[klass],
        # ONLY THE ITEMS ARE SENT. A profile carrying a substitution also
        # carries a `_divergence` list, written by export_sim_profiles.py so the
        # warning travels with the file. That key belongs to this project and
        # not to proto Equipment, and it is dropped HERE rather than left to the
        # simulator to ignore: an encoder that ignores unknown fields today is
        # not a promise, and a rejected request would read as a broken profile.
        "equipment": {"items": gear["items"]},
        "talentsString": talents,
        "consumables": consumables_for(spec),
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
        "encounter": ENCOUNTER,
        "simOptions": {"iterations": iterations, "randomSeed": str(seed)},
    }


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


def run(cli: Path, request: dict) -> tuple[float | None, str | None]:
    """One simulation. Returns the DPS, or the error the simulator gave."""
    with tempfile.TemporaryDirectory() as tmp:
        infile = Path(tmp) / "in.json"
        outfile = Path(tmp) / "out.json"
        infile.write_text(json.dumps(request))
        proc = subprocess.run(
            [str(cli), "sim", "--infile", str(infile), "--outfile", str(outfile)],
            capture_output=True, text=True)
        if not outfile.is_file():
            return None, (proc.stderr or proc.stdout or "no output").strip()[:200]
        result = json.loads(outfile.read_text())
    if result.get("error"):
        # The stack trace is the least useful part of a simulator error, and the
        # first line is nearly always the whole answer.
        return None, str(result["error"].get("message", "")).split("\n")[0]
    metrics = (result.get("raidMetrics") or {}).get("dps") or {}
    return metrics.get("avg"), None


def compare(args, strings: dict, iterations: int) -> int:
    """One profile, one slot, several candidates, against the same baseline.

    THE BASELINE IS RUN FIRST AND WITH THE SAME SEED. Two simulations of the
    same gear with different seeds differ by a few DPS, and an item worth a few
    DPS is exactly the kind this is asked about, so the seed is held and the
    difference is attributable to the item alone.
    """
    for name, value in (("--profile", args.profile), ("--slot", args.slot)):
        if not value:
            print(f"error: {name} is required when swapping", file=sys.stderr)
            return 1
    if args.slot not in SLOT_ORDER:
        print(f"error: {args.slot!r} is not a slot. One of: "
              f"{', '.join(SLOT_ORDER)}", file=sys.stderr)
        return 1

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

    names = {int(r["item_id"]): r["name"]
             for r in csv.DictReader(ITEMS.open())} if ITEMS.is_file() else {}
    index = SLOT_ORDER.index(args.slot)
    worn = (gear["items"][index] or {}).get("id")

    buffs = yaml.safe_load(BUFFS.read_text())
    roster = yaml.safe_load(ROSTER.read_text())
    party_of = {}
    for group in roster.get("groups") or []:
        for member in group.get("members") or []:
            party_of.setdefault(member, group["id"])
    base, error = run(args.cli, build_request(
        spec, gear, talents, iterations, args.seed, buffs, party_of))
    if error:
        print(f"error: the baseline failed: {error}", file=sys.stderr)
        return 1
    print(f"{args.profile}, varying {args.slot}, {iterations} iterations\n")
    print(f"  {'baseline':44s} {base:9.1f}        "
          f"{names.get(worn, worn or 'empty')}")

    rows = []
    for item_id in args.swap:
        dps, error = run(args.cli, build_request(
            spec, swap_into(gear, args.slot, item_id), talents, iterations,
            args.seed, buffs, party_of))
        if error:
            print(f"  {item_id:<44} FAILED  {error}", file=sys.stderr)
            continue
        rows.append((item_id, dps, dps - base))
    for item_id, dps, delta in sorted(rows, key=lambda r: -r[1]):
        label = names.get(item_id, "empty" if not item_id else str(item_id))
        print(f"  {label[:44]:44s} {dps:9.1f} {delta:+8.1f}")
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
    ap.add_argument("--slot", help=f"which slot to vary. One of: "
                                   f"{', '.join(SLOT_ORDER)}")
    ap.add_argument("--swap", action="append", type=int, default=[],
                    help="an item id to try in that slot. Repeatable. 0 empties "
                         "the slot, which is what a two-hander needs")
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
    # first, and both its parties carry the same totems so nothing turns on it.
    party_of = {}
    for group in roster.get("groups") or []:
        for member in group.get("members") or []:
            party_of.setdefault(member, group["id"])
    iterations = 100 if args.check else args.iterations

    if args.swap or args.slot or args.profile:
        return compare(args, strings, iterations)

    rows, failures, skipped = [], [], []
    for path in sorted(args.gear.glob("*.gear.json")):
        stem = path.name[:-len(".gear.json")]
        spec_slug, _, anchor = stem.partition(".")
        spec = spec_slug.replace("-", "_")
        if spec in NOT_SIMULATABLE:
            skipped.append(f"{stem}: {NOT_SIMULATABLE[spec]}")
            continue
        if spec not in SPECS:
            failures.append((stem, f"{spec} is not a DPS spec this tool knows"))
            continue
        talents = (strings.get(spec) or {}).get("string")
        if not talents:
            failures.append((stem, "no talent string recorded"))
            continue
        dps, error = run(args.cli, build_request(
            spec, json.loads(path.read_text()), talents, iterations, args.seed,
            buffs, party_of))
        if error:
            failures.append((stem, error))
        else:
            rows.append((stem, dps))
            flag = "   <-- IMPLAUSIBLE" if dps < IMPLAUSIBLE else ""
            print(f"  {stem:52s} {dps:9.1f}{flag}")

    if skipped:
        print(f"\n{len(skipped)} profile(s) skipped as not simulatable:")
        for line in skipped:
            print(f"  {line}")
    low = [(stem, dps) for stem, dps in rows if dps < IMPLAUSIBLE]
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
