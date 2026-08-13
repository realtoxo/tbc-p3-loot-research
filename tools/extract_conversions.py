#!/usr/bin/env python3
"""Lift the stat conversion rates out of the fact files into a table Lua can read.

A comparison between two items is two raw stat lines until somebody converts
them. Strength is not attack power, and 53 strength is 106 attack power for a
feral druid and 53 for a rogue. The conversion is what the reader actually
wants, and doing it by hand in prose is how a wrong rate gets published.

`theme/filters/delta.lua` does the conversion at build time. Lua cannot read
YAML, so this transform reads the three fact files that hold the rates and
writes them as a Lua table. **No rate is written here.** Every figure below is
looked up in a fact file by key, and a key that is missing ends the run naming
the spec and the key, because a rate invented in a filter would render a page
that looks authoritative and is wrong for most specs.

Three files supply everything:

    data/facts/attack-power.yaml   strength and agility to attack power
    data/facts/crit.yaml           agility to crit, and the rating denominators
    data/facts/hit.yaml            the hit rating denominators

The output is a build artifact, not a fact. It lives beside the filter that
consumes it rather than in `data/facts/`, because it states nothing the three
files above do not already state, and a second copy of a fact in the fact
directory is the copy that goes stale. `just check` regenerates it and fails on
any drift, so it cannot silently disagree with its sources.

The one thing this file holds that the fact files do not is the spec registry:
which class a spec is, and which druid form it fights in. That is identity, not
a rate. It is written out rather than inferred from a spec id, because a spec
id was once matched on its filename in this project's history and read the
Protection Warrior ladder as the Protection Paladin.

Usage:
    python3 tools/extract_conversions.py --out theme/filters/conversions.generated.lua
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ATTACK_POWER = Path("data/facts/attack-power.yaml")
CRIT = Path("data/facts/crit.yaml")
HIT = Path("data/facts/hit.yaml")

# Spec identity. class, and druid form where the class has one. Not a rate.
# A spec claiming a priority must be here, or `delta.lua` fails on its name.
SPECS: dict[str, tuple[str, str | None]] = {
    "Combat Rogue": ("rogue", None),
    "Arms Warrior": ("warrior", None),
    "Fury Warrior": ("warrior", None),
    "Protection Warrior": ("warrior", None),
    "Retribution Paladin": ("paladin", None),
    "Protection Paladin": ("paladin", None),
    "Holy Paladin": ("paladin", None),
    "Enhancement Shaman": ("shaman", None),
    "Elemental Shaman": ("shaman", None),
    "Restoration Shaman": ("shaman", None),
    "Feral Cat": ("druid", "cat"),
    "Feral Bear": ("druid", "bear"),
    "Feral Dire Bear": ("druid", "dire_bear"),
    "Balance Druid": ("druid", "moonkin"),
    "Restoration Druid": ("druid", "no"),
    "Beast Mastery Hunter": ("hunter", None),
    "Survival Hunter": ("hunter", None),
    "Marksmanship Hunter": ("hunter", None),
    "Arcane Mage": ("mage", None),
    "Fire Mage": ("mage", None),
    "Shadow Priest": ("priest", None),
    "Priest Healer": ("priest", None),
    "Affliction Warlock": ("warlock", None),
    "Destruction Warlock": ("warlock", None),
}

# How a druid form is named in prose, for the rate citation.
FORM_NAME = {
    "cat": "Cat Form",
    "bear": "Bear Form",
    "dire_bear": "Dire Bear Form",
    "moonkin": "Moonkin Form",
    "no": "no form",
}

# crit.yaml groups three classes under one key rather than repeating a shared
# figure. Which key holds a class is the file's shape, not a rate.
CRIT_AGILITY_KEY = {
    "mage": "mage_priest_warlock",
    "priest": "mage_priest_warlock",
    "warlock": "mage_priest_warlock",
}


class MissingRate(SystemExit):
    """A rate a spec needs is not in the fact files. The run stops here."""


def load(path: Path) -> dict:
    if not path.is_file():
        raise MissingRate(
            f"extract_conversions.py: cannot read {path}. "
            "Run this from the repository root."
        )
    return yaml.safe_load(path.read_text())


def rate(doc: dict, path: Path, keys: list[str], spec: str) -> float:
    """One figure, by key path, from one fact file. Absent is fatal."""
    node = doc
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            raise MissingRate(
                f"extract_conversions.py: no rate for {spec}.\n"
                f"  wanted  {path}  ::  {'.'.join(keys)}\n"
                f"  missing {key}\n"
                "Add the figure to the fact file with its source, then run "
                "`just regen`. A rate hardcoded in the filter would be wrong "
                "for most specs."
            )
        node = node[key]
    if not isinstance(node, (int, float)):
        raise MissingRate(
            f"extract_conversions.py: the rate for {spec} at {path} :: "
            f"{'.'.join(keys)} is {node!r}, which is not a number."
        )
    return float(node)


def cite(path: Path, keys: list[str]) -> str:
    return f"{path} :: {'.'.join(keys)}"


def number(value: float) -> str:
    return str(int(value)) if value == int(value) else repr(value)


def multiply(stat, label, factor, rate_text, source):
    return {
        "stat": stat, "label": label, "unit": "", "op": "multiply",
        "by": factor, "rate": rate_text, "source": source,
    }


def divide(stat, label, divisor, rate_text, source):
    return {
        "stat": stat, "label": label, "unit": "percent", "op": "divide",
        "by": divisor, "rate": rate_text, "source": source,
    }


# A TANK NETS PRIMARY STATS AND NOTHING ELSE, ruled by the guild lead on 12
# August 2026.
#
# WHAT IT REPLACES. Every tank converted the same six stats as a damage spec:
# strength, agility, melee crit, melee hit, spell crit and spell hit. So the Net
# summarising a tank upgrade was made of offense, while defense, dodge, parry,
# block, armor and stamina printed as raw rows and never reached it. The figure
# that summarised the upgrade left out the stats the role is played on.
#
# WHY PRIMARY STATS RATHER THAN AVOIDANCE. Avoidance is not one number. Dodge
# and parry sit on one attack table, block is mitigation rather than avoidance
# because a blocked hit still lands, armor is a separate multiplicative layer
# and stamina is effective health. Summing them would state a quantity no
# source in this project defines. A primary stat needs no model: it is what the
# item carries, and the divisors are recorded at
# data/facts/crit.yaml::defensive_conversions for whoever prices them later.
TANK_SPECS = frozenset({"Protection Warrior", "Protection Paladin", "Feral Bear"})

PRIMARY_STATS = ("strength", "agility", "stamina", "intellect")


def rules_for(spec: str, klass: str, form: str | None, ap: dict, crit: dict, hit: dict) -> dict:
    """Every conversion one spec has, keyed by the item stat it consumes."""
    rules: dict[str, list[dict]] = {}

    # Strength to melee attack power. Two for Warrior, Paladin, Shaman and
    # Druid, one for everyone else, and the form does not change it.
    keys = ["conversions", "melee_attack_power_per_strength_level_70", klass]
    value = rate(ap, ATTACK_POWER, keys, spec)
    rules["strength"] = [multiply(
        "strength", "attack power", value,
        f"{number(value)} attack power per strength for a {klass}",
        cite(ATTACK_POWER, keys),
    )]

    # Agility to melee attack power. Three cases in the game gain any, and the
    # druid answer is a property of the form, not of the class.
    agility_key = f"druid_{form}_form" if klass == "druid" else klass
    keys = ["conversions", "melee_attack_power_per_agility_level_70", agility_key]
    value = rate(ap, ATTACK_POWER, keys, spec)
    where = f"in {FORM_NAME[form]}" if klass == "druid" else f"for a {klass}"
    text = (
        f"no melee attack power from agility {where}"
        if value == 0
        else f"{number(value)} attack power per agility {where}"
    )
    agility_rules = [multiply("agility", "attack power", value, text, cite(ATTACK_POWER, keys))]

    # Agility to ranged attack power, recorded for the hunters only. Every
    # class gains one per point, and for everyone else the ranged slot is a
    # stat stick, so printing it would be noise. See the note at the key.
    if klass == "hunter":
        keys = ["conversions", "ranged_attack_power_per_agility_level_70", klass]
        value = rate(ap, ATTACK_POWER, keys, spec)
        agility_rules.append(multiply(
            "agility", "ranged attack power", value,
            f"{number(value)} ranged attack power per agility",
            cite(ATTACK_POWER, keys),
        ))

    # Agility to crit. 40 for Rogue and Hunter, 33 for Warrior, 25 for the
    # rest. The modern tables give 40 for all and are wrong.
    keys = ["conversions", "agility_per_percent_crit_level_70",
            CRIT_AGILITY_KEY.get(klass, klass)]
    value = rate(crit, CRIT, keys, spec)
    agility_rules.append(divide(
        "agility", "melee crit", value,
        f"{number(value)} agility per 1 percent crit for a {klass}",
        cite(CRIT, keys),
    ))
    rules["agility"] = agility_rules

    # The four rating denominators. These do not vary by class at level 70,
    # and they are still read from the fact files rather than written here.
    ratings = [
        ("melee_hit", "melee and ranged hit", HIT, hit,
         ["conversions", "melee_ranged_hit_rating_per_percent"]),
        ("melee_crit", "melee crit", CRIT, crit,
         ["conversions", "melee_crit_rating_per_percent"]),
        ("spell_hit", "spell hit", HIT, hit,
         ["conversions", "spell_hit_rating_per_percent"]),
        ("spell_crit", "spell crit", CRIT, crit,
         ["conversions", "spell_crit_rating_per_percent"]),
    ]
    for stat, label, path, doc, keys in ratings:
        value = rate(doc, path, keys, spec)
        rules[stat] = [divide(
            stat, label, value,
            f"{number(value)} rating per 1 percent {label}",
            cite(path, keys),
        )]

    # STATS THAT NET AS THEMSELVES, ruled by the guild lead on 12 August 2026.
    # A conversion is not wanted for these, but the Net has to carry them.
    #
    # WHAT WAS WRONG. Haste, armor penetration, expertise, resilience and spell
    # penetration printed their raw difference as a row and then vanished from
    # the Net, because the Net sums only what a rule converts. So a card could
    # show plus 175 armor penetration in the table and summarise the item
    # without it. Ten Phase 3 drops carry melee haste, thirteen carry spell
    # haste, eight carry armor penetration and eight carry expertise.
    #
    # AN IDENTITY RULE IS THE WHOLE FIX. It converts the stat into itself, so
    # the figure reaching the Net is the rating the item carries, in the same
    # words the row above it uses. This project holds a real haste conversion,
    # 15.77 rating per percent in haste.yaml, and deliberately does NOT use it
    # here: the ruling is that these are captured as themselves.
    for stat, label in (("melee_haste", "haste rating"),
                        ("spell_haste", "spell haste rating"),
                        ("armor_pen", "armor penetration"),
                        ("expertise", "expertise rating"),
                        ("resilience", "resilience"),
                        ("spell_pen", "spell penetration")):
        rules.setdefault(stat, []).append(multiply(
            stat, label, 1, f"{label} counted as itself",
            "guild lead ruling, 12 August 2026: captured as themselves rather "
            "than converted",
        ))

    if spec in TANK_SPECS:
        # THE OFFENSE RULES STAY, AND LEAVE THE NET. They stay because
        # `convertible` in this file means "every spec must have a rate for this
        # stat or the build fails", so removing them stopped the build on the
        # first tank item carrying crit. They leave the Net because the guild
        # lead ruled on 12 August 2026 that a tank nets primary stats. A tank
        # card therefore still SHOWS what its crit and hit convert to, and the
        # Net beneath sums primaries only.
        for stat_rules in rules.values():
            for rule in stat_rules:
                rule["net"] = False
        # Identity, so the Net reads in the stat's own name. A tank card states
        # what the item carries rather than converting it into a currency this
        # project has not defined for the role.
        for stat in PRIMARY_STATS:
            rule = multiply(stat, stat, 1,
                            f"{stat} counted as itself for a tank",
                            "guild lead ruling, 12 August 2026: a tank nets "
                            "primary stats")
            rule["net"] = True
            rules.setdefault(stat, []).append(rule)
    return rules


# --------------------------------------------------------------------- writing


def lua_string(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def lua_rule(rule: dict, indent: str) -> str:
    return (
        f'{indent}{{ label = {lua_string(rule["label"])}, '
        f'unit = {lua_string(rule["unit"])}, '
        f'op = {lua_string(rule["op"])}, by = {number(rule["by"])},\n'
        f'{indent}  rate = {lua_string(rule["rate"])},\n'
        + (f'{indent}  net = false,\n' if rule.get("net") is False else "")
        + f'{indent}  source = {lua_string(rule["source"])} }},'
    )


HEADER = """\
-- GENERATED BY tools/extract_conversions.py. DO NOT EDIT.
--
-- Every rate below is read from a fact file by key, never written by hand.
-- `theme/filters/delta.lua` reads this table and no other source of rates.
-- Change a rate in the fact file it cites, then run `just regen`.
-- `just check` regenerates this file and fails if it drifted.
--
-- Sources:
--   data/facts/attack-power.yaml
--   data/facts/crit.yaml
--   data/facts/hit.yaml
"""


def render(specs: dict[str, dict], crit: dict, hit: dict) -> str:
    out = [HEADER, "return {"]
    out.append("  convertible = { " + ", ".join(
        lua_string(s) for s in
        # STAMINA AND INTELLECT ARE NOT LISTED HERE, and a tank still nets
        # them. This list means "every spec must have a rate for this stat, or
        # the build fails". Adding the two primaries to it broke every non-tank,
        # because a Feral Cat has no intellect rate and needs none. A spec's own
        # rules are read BEFORE this gate, so the tank identity rules apply and
        # every other spec falls through to the raw row it had before.
        ["strength", "agility", "melee_hit", "melee_crit", "spell_hit",
         "spell_crit"]
    ) + " },")
    # Rating to percent, keyed by the stat column rather than by spec. TBC keeps
    # hit and spell hit as SEPARATE item stats, and likewise crit, so the
    # denominator follows the stat name and needs no spec context. That is what
    # lets a tooltip, which is spec-independent and shared across cards, print a
    # percentage beside a rating without guessing who is reading it.
    out.append("  rating_per_percent = {")
    for stat, keys, doc, path in [
        ("melee_hit",  ["conversions", "melee_ranged_hit_rating_per_percent"], hit, HIT),
        ("spell_hit",  ["conversions", "spell_hit_rating_per_percent"], hit, HIT),
        ("melee_crit", ["conversions", "melee_crit_rating_per_percent"], crit, CRIT),
        ("spell_crit", ["conversions", "spell_crit_rating_per_percent"], crit, CRIT),
    ]:
        node = doc
        for k in keys:
            node = node[k]
        out.append(f"    {stat} = {{ divisor = {number(float(node))}, "
                   f"source = {lua_string(cite(path, keys))} }},")
    out.append("  },")
    out.append("  specs = {")
    for name in sorted(specs):
        rules = specs[name]
        out.append(f"    [{lua_string(name.lower())}] = {{")
        out.append(f"      name = {lua_string(name)},")
        out.append("      rules = {")
        for stat in sorted(rules):
            out.append(f"        {stat} = {{")
            for rule in rules[stat]:
                out.append(lua_rule(rule, "          "))
            out.append("        },")
        out.append("      },")
        out.append("    },")
    out.append("  },")
    out.append("}")
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", default="theme/filters/conversions.generated.lua", type=Path)
    args = parser.parse_args()

    ap, crit, hit = load(ATTACK_POWER), load(CRIT), load(HIT)
    specs = {
        name: rules_for(name, klass, form, ap, crit, hit)
        for name, (klass, form) in SPECS.items()
    }
    args.out.write_text(render(specs, crit, hit))
    print(f"{len(specs)} spec(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
