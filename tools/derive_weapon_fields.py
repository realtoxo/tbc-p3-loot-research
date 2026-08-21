#!/usr/bin/env python3
"""Derive each spec's weapon field and print the registry block.

A REVIEW AID AND A REPRODUCIBILITY RECORD, not part of `just regen`. The
guild lead ruled on 20 August 2026 that the weapon rounds are ENUMERATIVE,
so the per-spec `weapon_field` in tools/run_variant_sims.py stops being a
hand-curated pair list and becomes a candidate FIELD the runner enumerates
under the spec's ruled styles. This tool derives that field from the same
sources a reviewer would check by hand and prints it in the registry's own
format, so a re-derivation can be diffed against what the registry holds.

THE FIELD PER SPEC IS A UNION OF THREE SOURCES:
  (a) every row of the spec's weapon shortlist sections in
      theme/filters/ladder.generated.lua, sections "One Hand", "Main Hand",
      "Off Hand" and "Two Hand" of its by_slot, which are already
      rule-filtered: the Enhancement ladder holds only slow weapons and the
      hunter ladders hold no crafted weapon;
  (b) every weapon worn in any of the spec's gear files under
      data/sim/gear/, slots main_hand and off_hand, so the self-match
      property holds by construction;
  (c) every id a standing ruling routes for the spec, per
      data/judgments/weapon-routing.yaml, because a routing never excludes
      a candidate.

Each id is classified by items.csv hand_type: Two Hand goes to the
two_hand list, Main Hand to the main_hand list, One Hand to BOTH the
main_hand and off_hand lists, and Off Hand to the off_hand list. For the
six casters the off_hand list holds held frills, Off Hand items that are
not weapons, and for the Elemental Shaman also shields, while their One
Hand weapons go to the main hand only, because a caster carries at most
one weapon. The phase3 flag is True for a Mount Hyjal or Black Temple
drop per drops.csv, for a Hyjal reputation reward, and for a Season 3
arena piece, the Vengeful set; everything else is reachable earlier.

Usage:
    python3 tools/derive_weapon_fields.py [spec ...]
"""

from __future__ import annotations

import csv
import glob
import json
import re
import sys
from pathlib import Path

LADDER = Path("theme/filters/ladder.generated.lua")
ITEMS = Path("data/facts/items.csv")
DROPS = Path("data/facts/drops.csv")
GEAR = Path("data/sim/gear")

# WEAPON PROFICIENCY PER CLASS IN 2.4.3, transcribed from the class
# trainers: the set of items.csv weapon_type values the class can wield.
# Rogues have no axe skill in 2.4.3, priests have neither axes nor swords,
# druids and shamans never swords, mages and warlocks only sword, dagger
# and staff, paladins no staves, fists or daggers, hunters no maces. A
# shield is a proficiency of its own and among these thirteen specs only
# the shamans hold one. An Off Hand frill is not a weapon and any class
# can hold it.
PROFICIENCY = {
    "Warrior": {"Axe", "Mace", "Sword", "Dagger", "Fist", "Polearm",
                "Staff"},
    "Paladin": {"Axe", "Mace", "Sword", "Polearm"},
    "Hunter": {"Axe", "Sword", "Dagger", "Fist", "Polearm", "Staff"},
    "Rogue": {"Dagger", "Fist", "Mace", "Sword"},
    "Priest": {"Dagger", "Mace", "Staff"},
    "Shaman": {"Axe", "Mace", "Dagger", "Fist", "Staff"},
    "Mage": {"Sword", "Dagger", "Staff"},
    "Warlock": {"Sword", "Dagger", "Staff"},
    "Druid": {"Mace", "Dagger", "Fist", "Polearm", "Staff"},
}
SHIELD_CLASSES = {"Warrior", "Paladin", "Shaman"}

# THE THIRTEEN SPECS OF THE WEAPON ROUNDS: registry key -> (ladder key,
# class, styles). Styles are ruled in data/judgments/weapon-styles.yaml.
SPECS = {
    "enhancement_shaman": ("enhancement shaman", "Shaman", ["dual_wield"]),
    "retribution_paladin": ("retribution paladin", "Paladin", ["two_hand"]),
    "fury_warrior": ("fury warrior", "Warrior", ["dual_wield"]),
    "combat_rogue": ("combat rogue", "Rogue", ["dual_wield"]),
    "arms_warrior": ("arms warrior", "Warrior", ["two_hand"]),
    "beast_mastery_hunter": ("beast mastery hunter", "Hunter",
                             ["two_hand", "dual_wield"]),
    "survival_hunter": ("survival hunter", "Hunter",
                        ["two_hand", "dual_wield"]),
    "affliction_warlock": ("affliction warlock", "Warlock",
                           ["two_hand", "main_hand_off_hand"]),
    "destruction_warlock": ("destruction warlock", "Warlock",
                            ["two_hand", "main_hand_off_hand"]),
    "arcane_mage": ("arcane mage", "Mage",
                    ["two_hand", "main_hand_off_hand"]),
    "shadow_priest": ("shadow priest", "Priest",
                      ["two_hand", "main_hand_off_hand"]),
    "balance_druid": ("balance druid", "Druid",
                      ["two_hand", "main_hand_off_hand"]),
    "elemental_shaman": ("elemental shaman", "Shaman",
                         ["two_hand", "main_hand_off_hand"]),
}

# A caster carries at most one weapon, so its off hand is a held frill,
# and for the Elemental Shaman legally also a shield.
CASTERS = {"affliction_warlock", "destruction_warlock", "arcane_mage",
           "shadow_priest", "balance_druid", "elemental_shaman"}

# ROUTED WEAPONS ARE ALWAYS CANDIDATES for the specs a ruling names, per
# data/judgments/weapon-routing.yaml: a routing never excludes.
ROUTED = {
    "fury_warrior": [32837, 32838],          # Warglaives of Azzinoth
    "combat_rogue": [32837, 32838],          # Warglaives of Azzinoth
    "affliction_warlock": [32374],           # Zhar'doom
    "destruction_warlock": [32374],          # Zhar'doom
    "balance_druid": [32374],                # Zhar'doom
    "elemental_shaman": [32374],             # Zhar'doom
    "shadow_priest": [32374],                # Zhar'doom
    "arcane_mage": [30910],                  # Tempest of Chaos
    "arms_warrior": [30902],                 # Cataclysm's Edge
    "beast_mastery_hunter": [33670],         # Vengeful Glad. Decapitator
    "survival_hunter": [32248],              # Halberd of Desolation
}

# HUNTERS USE NO CRAFTED WEAPONS, ruled 20 August 2026 in
# data/judgments/weapon-styles.yaml; the hunter ladders already hold none,
# and this guard keeps a crafted id out of a hunter field unless an anchor
# actually wears it, which the self-match property requires.
NO_CRAFTED = {"beast_mastery_hunter", "survival_hunter"}

# THE ENHANCEMENT SPEED FLOOR, ruled in
# data/judgments/enhancement-weapon-rules.yaml: every candidate slow,
# speed above 2.3. The matched-pair rule itself is the runner's, applied
# at generation time; the floor is a property of the field and is
# asserted here.
SPEED_FLOOR = {"enhancement_shaman": 2.3}


def ladder_sections() -> dict[str, dict[str, list[int]]]:
    """The by_slot weapon shortlist sections per ladder spec key."""
    spec_re = re.compile(r'^    \["(.+)"\] = \{')
    sect_re = re.compile(r'^        \["(.+)"\] = \{')
    item_re = re.compile(r'item_id = (\d+),')
    out: dict[str, dict[str, list[int]]] = {}
    spec = None
    in_by_slot = False
    section = None
    for line in LADDER.read_text().splitlines():
        m = spec_re.match(line)
        if m:
            spec = m.group(1)
            in_by_slot = False
            section = None
            out[spec] = {}
            continue
        if spec is None:
            continue
        if line.startswith("      by_slot = {"):
            in_by_slot = True
            section = None
            continue
        if not in_by_slot:
            continue
        m = sect_re.match(line)
        if m:
            section = m.group(1)
            out[spec].setdefault(section, [])
            continue
        if line.startswith("      },"):
            in_by_slot = False
            section = None
            continue
        if section in ("One Hand", "Main Hand", "Off Hand", "Two Hand"):
            m = item_re.search(line)
            if m:
                out[spec][section].append(int(m.group(1)))
    return out


def worn_ids(stem: str) -> tuple[set[int], set[int]]:
    """Every main-hand and off-hand id any of the spec's gear files wears."""
    mh, oh = set(), set()
    for path in sorted(glob.glob(str(GEAR / f"{stem}.*.gear.json"))):
        items = json.loads(Path(path).read_text())["items"]
        if items[14].get("id"):
            mh.add(items[14]["id"])
        if items[15].get("id"):
            oh.add(items[15]["id"])
    return mh, oh


def main() -> int:
    rows = {int(r["item_id"]): r for r in csv.DictReader(ITEMS.open())}
    hyjal_bt = {int(r["item_id"]) for r in csv.DictReader(DROPS.open())
                if r["zone"] in ("Mount Hyjal", "Black Temple")}
    sections = ladder_sections()

    def phase3(item_id: int) -> bool:
        if item_id in hyjal_bt:
            return True
        row = rows[item_id]
        if (row["source"] == "arena"
                and row["name"].startswith("Vengeful Gladiator's")):
            return True
        if (row["source"] == "reputation"
                and "Scale of the Sands" in row["source_note"]):
            return True
        return False

    wanted = sys.argv[1:] or list(SPECS)
    unknown = [s for s in wanted if s not in SPECS]
    if unknown:
        print(f"error: not a weapon-round spec: {', '.join(unknown)}",
              file=sys.stderr)
        return 1

    for spec in wanted:
        ladder_key, klass, styles = SPECS[spec]
        stem = spec.replace("_", "-")
        worn_mh, worn_oh = worn_ids(stem)
        worn = worn_mh | worn_oh
        field = set(worn) | set(ROUTED.get(spec, []))
        for section in ("One Hand", "Main Hand", "Off Hand", "Two Hand"):
            for item_id in sections.get(ladder_key, {}).get(section, []):
                if item_id not in rows:
                    print(f"# {spec}: ladder id {item_id} is not in "
                          "items.csv and is dropped", file=sys.stderr)
                    continue
                if (spec in NO_CRAFTED
                        and rows[item_id]["source"] == "crafted"
                        and item_id not in worn):
                    continue
                field.add(item_id)

        two_hand: list[int] = []
        main_hand: list[int] = []
        off_hand: list[int] = []
        for item_id in sorted(field):
            row = rows.get(item_id)
            if row is None:
                print(f"# {spec}: id {item_id} is not in items.csv and is "
                      "dropped", file=sys.stderr)
                continue
            wtype = row["weapon_type"]
            hand = row["hand_type"]
            allow = row["class_allowlist"]
            if allow and klass not in allow.split("|"):
                print(f"# {spec}: {row['name']} is locked to {allow} and "
                      "is dropped", file=sys.stderr)
                continue
            if wtype == "Shield":
                if klass not in SHIELD_CLASSES:
                    continue
                off_hand.append(item_id)
                continue
            if wtype == "Off Hand":
                # A held frill, legal for any class, meaningful only where
                # the style pairs a main hand with a held off hand.
                off_hand.append(item_id)
                continue
            if wtype not in PROFICIENCY[klass]:
                print(f"# {spec}: {row['name']} is a {wtype}, outside the "
                      f"{klass} proficiencies, and is dropped",
                      file=sys.stderr)
                continue
            floor = SPEED_FLOOR.get(spec)
            if floor is not None:
                speed = float(row["weapon_speed"] or 0)
                if speed <= floor:
                    print(f"# {spec}: {row['name']} at speed {speed} is at "
                          f"or below the {floor} floor and is dropped",
                          file=sys.stderr)
                    continue
            if hand == "Two Hand":
                if "two_hand" in styles:
                    two_hand.append(item_id)
                else:
                    print(f"# {spec}: {row['name']} is a two-hander "
                          "outside the spec's styles and is dropped",
                          file=sys.stderr)
                continue
            if hand == "Main Hand":
                main_hand.append(item_id)
            elif hand == "One Hand":
                main_hand.append(item_id)
                if spec not in CASTERS:
                    off_hand.append(item_id)
            elif hand == "Off Hand":
                off_hand.append(item_id)

        def block(name: str, ids: list[int]) -> str:
            if not ids:
                return f'            "{name}": [],\n'
            lines = [f'            "{name}": [\n']
            for item_id in ids:
                flag = "True" if phase3(item_id) else "False"
                lines.append(
                    f'                {{"id": {item_id}, '
                    f'"phase3": {flag}}},'
                    f'   # {rows[item_id]["name"]}\n')
            lines.append("            ],\n")
            return "".join(lines)

        styles_lit = ", ".join(f'"{s}"' for s in styles)
        print(f'        # {spec}: derived by tools/derive_weapon_fields.py')
        print(f'        "weapon_field": {{')
        print(f'            "styles": [{styles_lit}],')
        if spec == "enhancement_shaman":
            print('            "matched_speed": True,')
        sys.stdout.write(block("two_hand", two_hand))
        sys.stdout.write(block("main_hand", main_hand))
        sys.stdout.write(block("off_hand", off_hand))
        print("        },")
        print(f"# {spec}: two_hand {len(two_hand)}, "
              f"main_hand {len(main_hand)}, off_hand {len(off_hand)}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
