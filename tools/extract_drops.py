#!/usr/bin/env python3
"""Extract the Tier 4, Tier 5 and Tier 6 raid loot tables from the WoWSims item database.

Why not scrape Wowhead: its loot tables are rendered client-side, so a plain
HTTP fetch returns page chrome only, and CloudFront answers non-browser clients
with 403. The WoWSims database carries the same drop data offline, keyed by
zone and NPC, and it also carries the item stat vectors the scoring pipeline
needs later.

The Tier 6 output was cross-checked against an independent browser-driven
capture of Wowhead's loot tabs. All nine Black Temple boss item counts matched,
and the three bosses that capture could not resolve fell out unambiguously
because their counts are distinct. See data/facts/PROVENANCE.md.

Tier 4 and Tier 5 were added later. The database records a drop as nothing but
`difficulty`, `npcId` and `zoneId`; no zone name and no NPC name appears
anywhere in db.json, so every id here was resolved from an external source
rather than assumed. How, exactly, is recorded above ZONES and BOSSES below.

Usage:
    python3 tools/extract_drops.py --db PATH --out data/facts/drops.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

# proto/common.proto :: enum ItemType. Verified against the vendored proto, not
# guessed. An earlier hand-written version of this map was off by one from
# Wrist onward and filed belts as wrist items.
ITEM_TYPE = {
    0: "Unknown", 1: "Head", 2: "Neck", 3: "Shoulder", 4: "Back", 5: "Chest",
    6: "Wrist", 7: "Hands", 8: "Waist", 9: "Legs", 10: "Feet", 11: "Finger",
    12: "Trinket", 13: "Weapon", 14: "Ranged",
}

# proto/common.proto :: enum ArmorType
ARMOR_TYPE = {0: "", 1: "Cloth", 2: "Leather", 3: "Mail", 4: "Plate"}

QUALITY = {0: "Poor", 1: "Common", 2: "Uncommon", 3: "Rare", 4: "Epic", 5: "Legendary"}

# Zone ids are resolved, never guessed. db.json carries no zone name at all, so
# each id below was resolved from outside the database and then confirmed:
#
#   1. Take every npcId that drops in the candidate zone.
#   2. Read each NPC back from https://nether.wowhead.com/tbc/tooltip/npc/<ID>,
#      the TBC 2.4.3 data environment. That JSON carries the NPC's name and its
#      own `map.zone`. www.wowhead.com and tbc.wowhead.com are CloudFront-blocked
#      to automation and answer 403; nether does not.
#   3. Require the NPC's own `map.zone` to equal the drop record's zoneId. Two
#      independent fields of the same record agreeing is the check.
#   4. Compare the resulting roster against the encounter list on
#      warcraft.wiki.gg. Wikitext is fine for rosters and names; never take a
#      number from it, it has been caught serving post-TBC item values.
#
# Zones that were examined and rejected, all resolved the same way: 3805
# Zul'Aman (Phase 4), 4075 Sunwell Plateau and 4131 Magisters' Terrace (Phase
# 5), 3847, 3848 and 3849 the three five-man wings of Tempest Keep, 3789 to
# 3792 the Auchindoun wings, 3713 to 3717 the Hellfire Citadel and Coilfang
# five-mans, 3562 Hellfire Ramparts, and 1583 through 3456 the classic-era
# instances. Coilfang and Tempest Keep each publish four zone ids, only one of
# which is the raid, which is exactly the trap this procedure exists to avoid.
ZONES = {
    3457: ("T4", "Karazhan"),
    3923: ("T4", "Gruul's Lair"),
    3836: ("T4", "Magtheridon's Lair"),
    3607: ("T5", "Serpentshrine Cavern"),
    3845: ("T5", "Tempest Keep"),
    3606: ("T6", "Mount Hyjal"),
    3959: ("T6", "Black Temple"),
}

# Boss names are not in the database; only NPC ids are. This mapping is the
# human layer and is the one thing here that needs review if it ever changes.
# Every Tier 4 and Tier 5 name below came from the nether tooltip endpoint
# named above, which also confirmed the NPC's zone.
BOSSES = {
    22887: "High Warlord Naj'entus",
    22898: "Supremus",
    22841: "Shade of Akama",
    22871: "Teron Gorefiend",
    22948: "Gurtogg Bloodboil",
    22856: "Reliquary of Souls",
    22947: "Mother Shahraz",
    23426: "The Illidari Council",
    22917: "Illidan Stormrage",
    17767: "Rage Winterchill",
    17808: "Anetheron",
    17888: "Kaz'rogal",
    17842: "Azgalor",
    17968: "Archimonde",
    # Tier 5, Serpentshrine Cavern.
    21216: "Hydross the Unstable",
    21217: "The Lurker Below",
    21215: "Leotheras the Blind",
    21214: "Fathom-Lord Karathress",
    21213: "Morogrim Tidewalker",
    21212: "Lady Vashj",
    # Tier 5, Tempest Keep: The Eye.
    19514: "Al'ar",
    19516: "Void Reaver",
    18805: "High Astromancer Solarian",
    19622: "Kael'thas Sunstrider",
    # Tier 4, Gruul's Lair and Magtheridon's Lair.
    18831: "High King Maulgar",
    19044: "Gruul the Dragonkiller",
    17257: "Magtheridon",
    # Tier 4, Karazhan.
    16152: "Attumen the Huntsman",
    15687: "Moroes",
    16457: "Maiden of Virtue",
    15691: "The Curator",
    16524: "Shade of Aran",
    15688: "Terestian Illhoof",
    15689: "Netherspite",
    15690: "Prince Malchezaar",
    17225: "Nightbane",
    # The Opera Event is one encounter with three possible scripts. The
    # database keys each script's loot to its own final NPC.
    18168: "The Crone",
    17521: "The Big Bad Wolf",
    17533: "Romulo",
    # The Servant's Quarters rare is one encounter with three possible spawns.
    16179: "Hyakiss the Lurker",
    16180: "Shadikith the Glider",
    16181: "Rokad the Ravager",
    None: "Trash / zone drop",
}

# Karazhan is the only raid here whose NPC count and encounter count differ.
# Grouping the two randomised encounters lets the encounter assertion below be
# checked against the roster on warcraft.wiki.gg rather than against itself.
ENCOUNTER_GROUP = {
    "The Crone": "Opera Event",
    "The Big Bad Wolf": "Opera Event",
    "Romulo": "Opera Event",
    "Hyakiss the Lurker": "Servant's Quarters rare",
    "Shadikith the Glider": "Servant's Quarters rare",
    "Rokad the Ravager": "Servant's Quarters rare",
}

# Encounters expected per raid, from the encounter rosters on warcraft.wiki.gg.
# Karazhan is 12 encounters on the wiki; the twelfth is the Chess Event, whose
# reward comes from a chest rather than an NPC and so has no drop record.
EXPECTED_ENCOUNTERS = {
    "Karazhan": 11, "Gruul's Lair": 2, "Magtheridon's Lair": 1,
    "Serpentshrine Cavern": 6, "Tempest Keep": 4,
    "Mount Hyjal": 5, "Black Temple": 9,
}

# Expected item counts per Tier 6 source, from the independent Wowhead
# cross-check. A mismatch means the database changed and the cross-check needs
# redoing.
EXPECTED = {
    "High Warlord Naj'entus": 14, "Supremus": 13, "Shade of Akama": 14,
    "Teron Gorefiend": 12, "Gurtogg Bloodboil": 13, "Reliquary of Souls": 13,
    "Mother Shahraz": 6, "The Illidari Council": 6, "Illidan Stormrage": 14,
    "Rage Winterchill": 12, "Anetheron": 12, "Kaz'rogal": 12,
    "Azgalor": 6, "Archimonde": 12,
}

# Tier 4 and Tier 5 counts are a snapshot of this database, not a second
# source, and they are weaker evidence than the Tier 6 block above for that
# reason. They are asserted anyway so that a silent change in the database or
# in the zone map becomes a crash instead of a quiet edit to the CSV. The boss
# rosters themselves, which are the part that could have been guessed wrong,
# are cross-checked: see ZONES and EXPECTED_ENCOUNTERS.
#
# The counts that look short are short for the reason Tier 6 is short. The
# database models tier pieces, not tier tokens, so every token-dropping boss
# loses its tokens here: The Curator, High King Maulgar, Fathom-Lord
# Karathress, Leotheras the Blind and Void Reaver all read low.
EXPECTED_SNAPSHOT = {
    "Attumen the Huntsman": 12, "Moroes": 12, "Maiden of Virtue": 12,
    "The Curator": 6, "Shade of Aran": 12, "Terestian Illhoof": 12,
    "Netherspite": 12, "Prince Malchezaar": 12, "Nightbane": 12,
    "The Crone": 10, "The Big Bad Wolf": 10, "Romulo": 10,
    "Hyakiss the Lurker": 4, "Shadikith the Glider": 4, "Rokad the Ravager": 4,
    "High King Maulgar": 6, "Gruul the Dragonkiller": 13, "Magtheridon": 12,
    "Hydross the Unstable": 14, "The Lurker Below": 13,
    "Leotheras the Blind": 6, "Fathom-Lord Karathress": 6,
    "Morogrim Tidewalker": 13, "Lady Vashj": 12,
    "Al'ar": 13, "Void Reaver": 7,
    "High Astromancer Solarian": 13, "Kael'thas Sunstrider": 12,
}

FIELDS = [
    "tier", "zone", "npc_id", "boss", "item_id", "item_name",
    "slot", "armor_type", "quality", "db_phase", "url",
]


# KAEL'THAS'S SEVEN WEAPONS ARE NOT LOOT. During the fourth phase of the Tempest
# Keep encounter Kael'thas animates his weapons and the raid picks them up to
# use against him; they vanish when the fight ends. The item database records
# them as legendary zone drops, which is true of how they are handed out and
# false about what they are, so all seven arrived in the drop table as Tier 5
# gear. Reported by the guild lead on 13 August 2026: "netherstrand longbow
# should not be in our data set, it is only relevant for the KT encounter in
# tempest keep".
#
# THEY ARE EXCLUDED BY ID, and by all seven ids rather than the one that was
# noticed. Excluding on the "Legendary" quality would take the two Warglaives of
# Azzinoth with them, which are real loot and the most contested drop in the
# phase.
KAELTHAS_ENCOUNTER_WEAPONS = {
    30311,  # Warp Slicer
    30312,  # Infinity Blade
    30313,  # Staff of Disintegration
    30314,  # Phaseshift Bulwark
    30316,  # Devastation
    30317,  # Cosmic Infuser
    30318,  # Netherstrand Longbow
}


def extract(db_path: Path) -> list[dict]:
    db = json.loads(db_path.read_text())
    rows: list[dict] = []
    for item in db["items"]:
        if item["id"] in KAELTHAS_ENCOUNTER_WEAPONS:
            continue
        for source in item.get("sources", []):
            drop = source.get("drop")
            if not drop or drop.get("zoneId") not in ZONES:
                continue
            npc = drop.get("npcId")
            tier, zone = ZONES[drop["zoneId"]]
            rows.append({
                "tier": tier,
                "zone": zone,
                "npc_id": npc or "",
                "boss": BOSSES.get(npc, f"UNKNOWN npc {npc}"),
                "item_id": item["id"],
                "item_name": item["name"],
                "slot": ITEM_TYPE.get(item.get("type"), f"type{item.get('type')}"),
                "armor_type": ARMOR_TYPE.get(item.get("armorType"), ""),
                "quality": QUALITY.get(item.get("quality"), item.get("quality")),
                # Recorded, never filtered on: the field is wrong for at least
                # the nine Ashtongue Talismans. Filter by zone instead.
                "db_phase": item.get("phase"),
                "url": f"https://www.wowhead.com/tbc/item={item['id']}",
            })
    rows.sort(key=lambda r: (r["tier"], r["zone"], r["boss"], r["item_name"]))
    return rows


def verify(rows: list[dict]) -> list[str]:
    counts = Counter(r["boss"] for r in rows)
    problems = []
    for boss, expected in {**EXPECTED, **EXPECTED_SNAPSHOT}.items():
        actual = counts.get(boss, 0)
        if actual != expected:
            problems.append(f"{boss}: expected {expected}, got {actual}")

    # An encounter that vanished entirely would not show up above, because a
    # boss missing from the map is a boss missing from the count dictionary.
    # Assert the roster size per raid as well.
    encounters: dict[str, set[str]] = {}
    for row in rows:
        if row["boss"] == "Trash / zone drop":
            continue
        name = ENCOUNTER_GROUP.get(row["boss"], row["boss"])
        encounters.setdefault(row["zone"], set()).add(name)
    for zone, expected in EXPECTED_ENCOUNTERS.items():
        actual = len(encounters.get(zone, set()))
        if actual != expected:
            problems.append(f"{zone}: expected {expected} encounters, got {actual}")

    unknown = sorted({r["boss"] for r in rows if r["boss"].startswith("UNKNOWN")})
    problems.extend(f"unmapped NPC: {u}" for u in unknown)
    bad_slot = sorted({r["slot"] for r in rows if r["slot"].startswith("type")})
    problems.extend(f"unmapped item type: {s}" for s in bad_slot)
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, required=True, help="path to WoWSims db.json")
    ap.add_argument("--out", type=Path, required=True, help="output CSV path")
    args = ap.parse_args()

    if not args.db.exists():
        print(f"error: database not found: {args.db}", file=sys.stderr)
        return 2

    rows = extract(args.db)
    problems = verify(rows)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows)} rows -> {args.out}")
    grouped = Counter((r["tier"], r["zone"], r["boss"]) for r in rows)
    for (tier, zone, boss), n in sorted(grouped.items()):
        print(f"  {tier}  {zone:22} {boss:28} {n}")
    for tier, n in sorted(Counter(r["tier"] for r in rows).items()):
        print(f"  {tier} total: {n}")

    if problems:
        print("\nVERIFICATION FAILED:", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1
    print("\nverification passed: boss counts and encounter rosters both match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
