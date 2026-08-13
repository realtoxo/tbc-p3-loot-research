#!/usr/bin/env python3
"""Extract the full stat line of every Tier 4, Tier 5 and Tier 6 item in scope.

Facts only. What each item is and what it carries. No scoring, no weighting,
no opinion about who should want it.

Three populations, one table, told apart by the `source` column.

`raid_drop` is whatever drops.csv holds, so the tiers covered there are decided
by the zone map in extract_drops.py and nowhere else. The `tier` column is
carried across from drops.csv rather than re-derived, because a comparison
against what a player already wears is the common question and it should not
need a join to answer. An item that drops in more than one tier gets both,
pipe-separated.

`tier_vendor` is the 255 tier set pieces named in tokens.yaml. They are bought
from a vendor with a token, so they never appear in a boss loot table and were
therefore absent from this file, yet almost every priority on a Phase 3 drop is
argued against the tier piece it competes with. A named alternative that is not
in the item table is one argued about from memory. Their `tier` comes from the
`tier` field of the set that lists them, never from a zone.

`worn` is an item a captured gear set names that no scope below reaches: the
relic slot entirely, because the workbook ranks no idol, libram or totem, plus
the badge trinkets and arena weapons a real set holds. A set total that silently
omits a trinket is worse than one that says it is missing one.

`drop`, `crafted`, `badge` and `arena` are the fifth through eighth values,
and they mark an item the EP Workbook ladder names that neither scope above
reaches. The first two scopes are defined by where an item COMES FROM; this one
is defined by whether the compendium SHOWS it, which is why it needs the ladder
to answer and why it carries the workbook's own acquisition label rather than a
tier. A `drop` here is an earlier-tier or five-player drop outside the Phase 3
zone map, so it is not the same claim as `raid_drop`.

tokens.yaml is hand-authored from the Wowhead 2.4.3 tooltip endpoint and this
database was captured separately, so requiring the two to agree on all 255 ids
and names is a real cross-check rather than a formality. The run fails if any
piece is missing from the database or is named differently there.

Stat indices come from proto/common.proto :: enum Stat in the WoWSims source,
transcribed rather than guessed. An earlier hand-written map in this repository
was off by one and filed every belt as a wrist item, so the rule is: read the
enum, never infer it.

Usage:
    python3 tools/extract_items.py --db PATH --out data/facts/items.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

# proto/common.proto :: enum Stat. Transcribed, not inferred.
STAT = {
    0: "strength", 1: "agility", 2: "stamina", 3: "intellect",
    4: "healing_power", 5: "spell_damage", 6: "arcane_damage", 7: "fire_damage",
    8: "frost_damage", 9: "holy_damage", 10: "nature_damage", 11: "shadow_damage",
    12: "spell_hit", 13: "spell_crit", 14: "spell_haste", 15: "spell_pen", 16: "spirit",
    17: "attack_power", 18: "ranged_attack_power", 19: "feral_attack_power",
    20: "melee_hit", 21: "melee_crit", 22: "melee_haste", 23: "armor_pen", 24: "expertise",
    25: "defense", 26: "block_rating", 27: "block_value", 28: "dodge", 29: "parry",
    30: "resilience", 31: "armor", 32: "bonus_armor",
}

# EVERY STAT AN EFFECT CAN GRANT, which is more than an ITEM can carry. STAT
# above stops at 32 because those are the columns items.csv holds, and adding to
# it would add columns. An effect reaches further: Shadowmoon Insignia grants
# health and Memento of Tyrande grants mana per five, and neither index was
# mapped, so item-effects.csv wrote the raw enum number and the card read
# "1750 33" and "76 35". Transcribed from proto/common.proto :: enum Stat, the
# same source as STAT.
EFFECT_STAT = dict(STAT)
EFFECT_STAT.update({
    33: "health", 34: "mana", 35: "mp5",
    36: "arcane_resistance", 37: "fire_resistance", 38: "frost_resistance",
    39: "nature_resistance", 40: "shadow_resistance",
})

ITEM_TYPE = {
    0: "Unknown", 1: "Head", 2: "Neck", 3: "Shoulder", 4: "Back", 5: "Chest",
    6: "Wrist", 7: "Hands", 8: "Waist", 9: "Legs", 10: "Feet", 11: "Finger",
    12: "Trinket", 13: "Weapon", 14: "Ranged",
}
ARMOR_TYPE = {0: "", 1: "Cloth", 2: "Leather", 3: "Mail", 4: "Plate"}

# Which hand a weapon is worn in, and what kind of weapon it is. Both were
# written out as the raw enum integer, which reached a rendered tooltip as
# `Tier 6 - weapon - 9` and told a reader nothing, and which left the two
# Warglaives of Azzinoth indistinguishable anywhere the name is printed.
#
# Every value was confirmed against items the database itself carries rather
# than transcribed from memory: Gorehowl is an axe, Malchazeen a dagger, Claw of
# the Phoenix a fist weapon, Light's Justice a mace, Halberd of Desolation a
# polearm, Terestian's Stranglestaff a staff, King's Defender a sword, and
# Aran's Soothing Sapphire is held in the off hand. The hands were confirmed the
# same way: Warglaive of Azzinoth 32837 is a main hand and 32838 an off hand,
# Torch of the Damned is two-handed, Swiftsteel Bludgeon is one-handed.
HAND_TYPE = {
    0: "", 1: "Main Hand", 2: "One Hand", 3: "Off Hand", 4: "Two Hand",
}
WEAPON_TYPE = {
    0: "", 1: "Axe", 2: "Dagger", 3: "Fist", 4: "Mace", 5: "Off Hand",
    6: "Polearm", 7: "Shield", 8: "Staff", 9: "Sword",
}
GEM_COLOUR = {0: "", 1: "Meta", 2: "Red", 3: "Blue", 4: "Yellow", 5: "Green",
              6: "Orange", 7: "Purple", 8: "Prismatic"}

BASE = ["item_id", "tier", "source", "source_note", "name", "icon", "slot", "armor_type", "hand_type",
        "weapon_type", "ranged_weapon_type", "set_name", "class_allowlist",
        "has_effect", "sockets", "socket_bonus", "weapon_min", "weapon_max",
        "weapon_speed", "url"]

# WoW's own ChrClasses ids, which is what `classAllowlist` carries. NOT the
# proto Class enum, which this map used to be and which is off by one from
# Shaman onward. The two agree through Priest and then diverge, so the error was
# invisible on warriors, paladins, hunters, rogues and priests and mislabeled
# every shaman set as Druid, every druid set as `11`, every mage as Warlock and
# every warlock as nothing at all.
#
# Verified against the database rather than transcribed: Skyshatter Headguard
# 31014 is a shaman helm and reads 7, Thunderheart Cover 31041 is a druid helm
# and reads 11, Onslaught Greathelm 30974 is a warrior helm and reads 1,
# Absolution Hood 31064 is a priest helm and reads 5.
#
# 6 and 10 do not exist in 2.4.3 and are listed so the gap is deliberate rather
# than looking like an omission.
CLASS = {0: "", 1: "Warrior", 2: "Paladin", 3: "Hunter", 4: "Rogue",
         5: "Priest", 6: "Death Knight", 7: "Shaman", 8: "Mage",
         9: "Warlock", 10: "Monk", 11: "Druid"}

# proto/ui.proto :: enum RepFaction and enum RepLevel, transcribed from the
# vendored proto rather than recalled. THE ASHTONGUE TALISMANS ARE WHY. They are
# Ashtongue Deathsworn Exalted rewards bought from a quartermaster, and the
# workbook leaves their Location cell empty, so route_of bucketed all nine into
# `drop` and every card said they fall off a boss. The database knew better the
# whole time and nothing read it.
REP_FACTION = {
    933: "The Consortium", 941: "The Mag'har", 942: "Cenarion Expedition",
    946: "Honor Hold", 947: "Thrallmar", 970: "Sporeggar", 978: "Kurenai",
    1012: "Ashtongue Deathsworn", 1015: "Netherwing", 1038: "Ogri'la",
}
REP_LEVEL = {
    1: "Hated", 2: "Hostile", 3: "Unfriendly", 4: "Neutral", 5: "Friendly",
    6: "Honored", 7: "Revered", 8: "Exalted",
}

# proto/common.proto :: enum Profession
PROFESSION = {
    1: "Alchemy", 2: "Blacksmithing", 3: "Enchanting", 4: "Engineering",
    5: "Herbalism", 6: "Inscription", 7: "Jewelcrafting", 8: "Leatherworking",
    9: "Mining", 10: "Skinning", 11: "Tailoring",
}


def source_note(item: dict) -> tuple[str, bool]:
    """How the item is acquired in words, and whether a reputation grants it.

    The `source` column is a ROUTE, one word from a fixed set. This is the
    sentence a card can print, which a route cannot carry: which faction, at
    what standing, or which profession.
    """
    notes, is_rep = [], False
    for entry in item.get("sources") or []:
        if "rep" in entry:
            is_rep = True
            rep = entry["rep"]
            faction = REP_FACTION.get(rep.get("repFactionId"),
                                      f"faction {rep.get('repFactionId')}")
            level = REP_LEVEL.get(rep.get("repLevel"), "an unrecorded standing")
            notes.append(f"{faction}, {level}")
        elif "crafted" in entry:
            trade = PROFESSION.get(entry["crafted"].get("profession"), "")
            notes.append(f"Crafted, {trade}" if trade else "Crafted")
    # The database lists a crafted source twice for every crafted item, so the
    # note would read the profession twice without this.
    seen, unique = set(), []
    for note in notes:
        if note not in seen:
            seen.add(note)
            unique.append(note)
    return "; ".join(unique), is_rep


# WHAT MAKES AN EFFECT FIRE, which the compendium never said. The guild lead
# asked for passive and on-use effects to be shown and both were printed
# identically, so a card could not tell a button press from a chance on hit.
# `onUse` and `proc` sit on the effect record and both were discarded.
EFFECT_FIELDS = ["item_id", "tier", "item_name", "buff_id", "buff_name",
                 "trigger", "proc_chance", "proc_icd_ms", "proc_ppm",
                 "duration_ms", "stats_granted"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, required=True, help="WoWSims db.json")
    ap.add_argument("--loot", type=Path, default=Path("data/facts/drops.csv"))
    ap.add_argument("--tokens", type=Path, default=Path("data/facts/tokens.yaml"))
    ap.add_argument("--workbook", type=Path,
                    default=Path("data/research/epv-workbook"))
    ap.add_argument("--captures", type=Path,
                    default=Path("data/facts/sim-profiles/hit-capture"))
    ap.add_argument("--out", type=Path, default=Path("data/facts/items.csv"))
    args = ap.parse_args()

    if not args.db.exists():
        print(f"error: database not found: {args.db}", file=sys.stderr)
        return 2

    tiers: dict[int, set[str]] = {}
    sources: dict[int, set[str]] = {}
    for row in csv.DictReader(args.loot.open()):
        tiers.setdefault(int(row["item_id"]), set()).add(row["tier"])
        sources.setdefault(int(row["item_id"]), set()).add("raid_drop")

    # Tier set pieces, named by the hand-authored token table. Claimed names are
    # kept so the database can be made to answer for every one of them below.
    claimed: dict[int, str] = {}
    tokens = yaml.safe_load(args.tokens.read_text())
    for entry in tokens["sets"]:
        for piece in entry["pieces"].values():
            item_id = int(piece["item_id"])
            claimed[item_id] = piece["name"]
            tiers.setdefault(item_id, set()).add(f"T{entry['tier']}")
            sources.setdefault(item_id, set()).add("tier_vendor")

    # The third population: everything the EP Workbook ladder names. A badge
    # item, a crafted item or an earlier-tier drop is not a Phase 3 raid drop
    # and is not a tier piece, so neither scope above reaches it, yet the
    # compendium shows it. The Badge of Justice vendor alone fills six tank
    # slots, and Tankatronic Goggles carries more defense than the Tier 6 helm
    # and competes with it directly. Naming a baseline the item table does not
    # hold is naming one the council argues about from memory.
    #
    # SCOPE IS WHAT THE LADDER SELECTS, not every row of the workbook. The
    # definition lives in extract_ladder.referenced_ids so there is one of it
    # rather than two, and it reads the workbook and tokens only, never this
    # file's own output, so calling it here is not a cycle.
    #
    # THE `tier` COLUMN IS EMPTY FOR THESE. A tier is what a raid zone or a
    # token set states, and neither states one for a badge purchase or a
    # crafted item. The workbook's Phase column is a release window rather than
    # a tier, so filling the column from it would put a claim in the table that
    # no source makes.
    # Imported here rather than at the top of the file. extract_ladder reads
    # this module's stat and slot enums, so a module-level import in this
    # direction closes a cycle and neither module loads.
    from extract_ladder import referenced_ids

    # ONLY WHERE NOTHING ELSE ALREADY ANSWERS. The workbook route is a weaker
    # claim than the two above it: it is a label typed into a spreadsheet's
    # Location column, while `raid_drop` comes from the boss loot table and
    # `tier_vendor` from the hand-verified token file. Where a stronger source
    # already names the item, adding the weaker one beside it would say nothing
    # and would read as disagreement. The Deathmantle pieces are the case that
    # shows it: the workbook labels three of them `Leather Armor`, which
    # route_of buckets as `crafted`, and they are tier vendor pieces.
    for item_id, routes in referenced_ids(args.workbook, tokens).items():
        if item_id in sources:
            continue
        tiers.setdefault(item_id, set())
        sources[item_id] = set(routes)

    # The fourth population: every item the captured gear sets name. The ladder
    # scope above covers what the workbook ranks, and the workbook ranks no
    # relic slot at all, so idols, librams and totems were absent along with the
    # badge trinkets and the arena weapons a real set holds. Those are worn
    # items carrying real stats, and a set total that silently omits a trinket
    # is worse than one that says it is missing one.
    for path in sorted(args.captures.glob("*.yaml")):
        capture = yaml.safe_load(path.read_text())
        for anchor in (capture.get("anchors") or {}).values():
            if not isinstance(anchor, dict):
                continue
            rows = anchor.get("hit_by_slot")
            if not isinstance(rows, dict):
                continue
            for row in rows.values():
                item_id = row.get("id") if isinstance(row, dict) else None
                if isinstance(item_id, int) and item_id not in sources:
                    tiers.setdefault(item_id, set())
                    sources[item_id] = {"worn"}

    wanted = set(tiers)
    db = json.loads(args.db.read_text())

    rows, seen, unstatted, effect_rows = [], set(), [], []
    for item in db["items"]:
        if item["id"] not in wanted or item["id"] in seen:
            continue
        seen.add(item["id"])
        scaling = item.get("scalingOptions", {}).get("0", {})
        stats = {int(k): v for k, v in scaling.get("stats", {}).items() if v}
        if not stats:
            unstatted.append((item["id"], item["name"]))
        effects = item.get("itemEffects", []) or []
        tier = "|".join(sorted(tiers[item["id"]]))
        note, is_rep = source_note(item)
        # THE DATABASE OUTRANKS THE FALLBACK BUCKET. `route_of` returns "drop"
        # for any Location it does not recognize, including an empty one, so
        # "drop" here means "nothing else answered" rather than "a boss drops
        # it". A rep source in the database is a positive statement and
        # replaces it. It never touches `raid_drop` or `tier_vendor`, which are
        # positive statements of their own.
        routes = set(sources[item["id"]])
        if is_rep and routes == {"drop"}:
            routes = {"reputation"}
        row = {
            "item_id": item["id"],
            "tier": tier,
            "source": "|".join(sorted(routes)),
            "source_note": note,
            "name": item["name"],
            # The icon file name, which tools/fetch_icons.py turns into a
            # committed image. An item is recognized by its icon before its
            # name is read.
            "icon": item.get("icon", ""),
            "slot": ITEM_TYPE.get(item.get("type"), ""),
            "armor_type": ARMOR_TYPE.get(item.get("armorType"), ""),
            "hand_type": HAND_TYPE.get(item.get("handType"), ""),
            "weapon_type": WEAPON_TYPE.get(item.get("weaponType"), ""),
            "ranged_weapon_type": item.get("rangedWeaponType", ""),
            "set_name": item.get("setName", ""),
            "class_allowlist": "|".join(
                CLASS.get(c, str(c)) for c in item.get("classAllowlist", [])),
            "has_effect": "yes" if effects else "",
            "sockets": "|".join(GEM_COLOUR.get(g, str(g)) for g in item.get("gemSockets", [])),
            "socket_bonus": "|".join(
                f"{STAT.get(i, i)}={v}" for i, v in enumerate(item.get("socketBonus", [])) if v),
            "weapon_min": scaling.get("weaponDamageMin", ""),
            "weapon_max": scaling.get("weaponDamageMax", ""),
            "weapon_speed": item.get("weaponSpeed", ""),
            "url": f"https://www.wowhead.com/tbc/item={item['id']}",
        }
        for idx, name in STAT.items():
            row[name] = stats.get(idx, "")
        rows.append(row)
        for e in effects:
            est = e.get("scalingOptions", {}).get("0", {}).get("stats", {})
            effect_rows.append({
                "item_id": item["id"],
                "tier": tier,
                "item_name": item["name"],
                "buff_id": e.get("buffId", ""),
                "buff_name": e.get("buffName", ""),
                "trigger": ("on_use" if "onUse" in e
                            else "proc" if "proc" in e else ""),
                "proc_chance": e.get("proc", {}).get("procChance", ""),
                "proc_icd_ms": e.get("proc", {}).get("icdMs", ""),
                "proc_ppm": e.get("proc", {}).get("ppm", ""),
                "duration_ms": e.get("effectDurationMs", ""),
                "stats_granted": "|".join(
                    f"{EFFECT_STAT.get(int(k), k)}={v}"
                    for k, v in est.items() if v),
            })

    rows.sort(key=lambda r: r["item_id"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = BASE + [STAT[i] for i in sorted(STAT)]
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    eff_out = args.out.parent / "item-effects.csv"
    effect_rows.sort(key=lambda r: r["item_id"])
    with eff_out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=EFFECT_FIELDS)
        w.writeheader()
        w.writerows(effect_rows)
    print(f"wrote {len(effect_rows)} on-use and on-equip effects -> {eff_out}")

    missing = sorted(wanted - seen)
    print(f"wrote {len(rows)} items -> {args.out}")
    print(f"  {len(wanted)} distinct ids in scope")
    for tier in sorted({r["tier"] for r in rows}):
        n = sum(1 for r in rows if r["tier"] == tier)
        trinkets = sum(1 for r in rows if r["tier"] == tier and r["slot"] == "Trinket")
        print(f"  {tier}: {n} items, {trinkets} of them trinkets")
    for source in sorted({r["source"] for r in rows}):
        print(f"  {source}: {sum(1 for r in rows if r['source'] == source)} items")
    if missing:
        print(f"  NOT IN DATABASE: {len(missing)} -> {missing}")

    # The token table and this database were captured from different sources, so
    # every tier piece agreeing on both id and name is the cross-check. A
    # disagreement is a wrong id in one of them and must stop the run, because a
    # tier piece silently absent from items.csv is the failure this scope exists
    # to remove.
    by_id = {r["item_id"]: r["name"] for r in rows}
    disagreements = [
        f"{item_id}: tokens.yaml says {name!r}, database says "
        f"{by_id.get(item_id, '<absent>')!r}"
        for item_id, name in sorted(claimed.items())
        if by_id.get(item_id) != name
    ]
    if disagreements:
        print(f"error: {len(disagreements)} tier piece(s) the database does not "
              f"confirm:", file=sys.stderr)
        for line in disagreements:
            print(f"  {line}", file=sys.stderr)
        return 1
    print(f"  {len(claimed)} tier pieces confirmed against {args.tokens}")
    if unstatted:
        print(f"  no stat line (relics, tokens and oddities): {len(unstatted)}")
        for i, n in unstatted[:10]:
            print(f"    {i}  {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
