#!/usr/bin/env python3
"""Resolve the consumable PROSE into the ids a RaidSimRequest carries.

WHAT THIS PRODUCES. `data/facts/consumable-ids.yaml`: a catalog of every
consumable name this project can turn into a simulator id, the id it becomes,
and where that id was read from; then, per spec, which name was taken for which
`ConsumesSpec` field, which names were passed over, and what the guide said
around the one that was taken.

WHY IT IS A FACT FILE AND NOT A DICT IN run_sims.py. A wrong id does not fail.
The run succeeds and the DPS is wrong, and nothing in the output says which
flask was drunk. Written out here, "Flask of Pure Death" sits beside 22866 and
beside the file that id was read from, so a reader can check it in a minute.

WHERE THE PROSE COMES FROM. `data/facts/consumables.yaml` for sixteen specs,
and `data/facts/sim-profiles/combat-rogue.yaml` for the Combat Rogue, which
keeps its consumables beside its gear and is deliberately not copied into the
other file.

HOW A NAME IS CHOSEN. The guides lead with the pick and follow with the cheaper
or conditional alternatives, so the FIRST catalog name in a field wins and every
later one is written out under `alternatives_named`. Where two catalog names
start at the same character the longer one wins, because "Adamantite Sharpening
Stone" and "Consecrated Sharpening Stone" are different stones and this project
has dispositioned an item on a shared word four times.

WHAT IS DELIBERATELY NOT RESOLVED, and each is a defect avoided rather than
work skipped:

  elixirs_instead  The field name says instead. A flask counts as both a battle
                   and a guardian elixir in 2.4.3, so wiring both would stack
                   two things the game does not stack.
  scrolls          The prose names scrolls it rejects in the same sentence, for
                   example "Warcraft Tavern's table also lists Scroll of
                   Strength V and Scroll of Protection V, but neither ... serves
                   a BM Hunter". A substring match would switch on a scroll the
                   source turned down.
  other            Runes, ammo, sappers and seeds, mixed with prose about who in
                   the raid brings them. Nothing here maps to one field.
  drums            `raid-buffs.yaml` already gives every party its drums through
                   PartyBuffs, so a drums_id in ConsumesSpec would count them a
                   second time.

Usage:
    python3 tools/extract_consumable_ids.py --out data/facts/consumable-ids.yaml
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import yaml

CONSUMABLES = Path("data/facts/consumables.yaml")
ROGUE = Path("data/facts/sim-profiles/combat-rogue.yaml")
WOWSIMS = Path(os.path.expanduser(os.environ.get(
    "WOWSIMS_TBC",
    "../tbc-phase-research-recovered/data/raw/vendor/wowsims-tbc-new-master")))
DB = WOWSIMS / "assets" / "database" / "db.json"
IMBUE_UI = WOWSIMS / "ui" / "core" / "components" / "inputs" / "consumables.ts"
IMBUE_SIM = WOWSIMS / "sim" / "core" / "consumes.go"
ROGUE_SIM = WOWSIMS / "sim" / "rogue" / "poisons.go"

# proto/common.proto :: enum ConsumableType. Transcribed, because db.json prints
# the number and a reader of this file should not have to decode it.
CONSUMABLE_TYPE = {
    1: "ConsumableTypePotion",
    2: "ConsumableTypeFlask",
    3: "ConsumableTypeFood",
    6: "ConsumableTypeBattleElixir",
    7: "ConsumableTypeGuardianElixir",
    9: "ConsumableTypePetFood",
}

# Which prose field feeds which proto/common.proto :: ConsumesSpec field, and
# which db.json consumable type is allowed to answer it. The type constraint is
# the guard against a food name landing in flask_id.
WIRED = [
    ("flask", "flask_id", 2),
    ("food", "food_id", 3),
    ("potions", "pot_id", 1),
    ("weapon_main_hand", "mhImbue_id", None),
    ("weapon_off_hand", "ohImbue_id", None),
]

# THE WEAPON IMBUES ARE NOT IN db.json. The `consumables` array holds 105
# entries and none of them is an oil, a stone or a poison, so an imbue id cannot
# be looked up the way a flask can. It is a SPELL id, and the simulator accepts
# a fixed handful of them and silently ignores every other number.
#
# Each row below therefore carries three things: the value the request sends,
# the item the wowsims UI shows for it, and the file that ACCEPTS it. The names
# are this project's, because no source in the vendored checkout prints a name
# for these item ids; `verify_imbues` checks the two numbers of every row
# against the vendored source, so a name is the only part a reader must judge.
#
# `accepted_by` of None means the simulator reads the field and does nothing
# with the value. That is the worst case the task warns about, so those rows are
# never picked; they are reported as unresolved instead.
IMBUES = [
    # name, imbue value, wowsims UI item id, UI const, accepting source
    ("Mana Oil", 25123, 20748, "ManaOil",
     "sim/core/consumes.go::registerStaticImbue"),
    ("Brilliant Wizard Oil", 25122, 20749, "BrilWizardOil",
     "sim/core/consumes.go::registerStaticImbue"),
    ("Superior Wizard Oil", 28017, 22522, "SupWizardOil",
     "sim/core/consumes.go::registerStaticImbue"),
    ("Adamantite Sharpening Stone", 29453, 23529, "AdamantiteSharpeningMH",
     "sim/core/consumes.go::registerStaticImbue"),
    ("Adamantite Weightstone", 34340, 28421, "AdamantiteWeightMH",
     "sim/core/consumes.go::registerStaticImbue"),
    ("Consecrated Sharpening Stone", 28891, 23122, "ConsecratedSharpeningStoneMH",
     "sim/core/consumes.go::registerStaticImbue"),
    # THE RANK IS NOT CLAIMED. The guides say "Deadly Poison VII" and the
    # simulator carries exactly one deadly poison imbue, so the rank chooses
    # between nothing. Naming it "Deadly Poison VII" here would be a rank read
    # off a guide and printed as though the simulator had confirmed it.
    ("Instant Poison", 26891, 21927, "RogueInstantPoison",
     "sim/rogue/poisons.go::instantImbueID"),
    ("Deadly Poison", 27186, 22054, "RogueDeadlyPoison",
     "sim/rogue/poisons.go::deadlyImbueID"),
    ("Wound Poison", 27188, 22055, "RogueWoundPoison",
     "sim/rogue/poisons.go::woundImbueID"),
    # A SHAMAN SELF-IMBUE IS NOT A CONSUMABLE. The wowsims UI offers Windfury
    # Weapon in the same dropdown as the oils, which is why it is listed here,
    # but ConsumesSpec is not where the simulator reads it: it reads
    # ShamanOptions.imbue_mh, an enum in proto/shaman.proto. Sending 25505 in
    # mhImbue_id is accepted by the encoder and does nothing at all.
    ("Windfury Weapon", 25505, None, "ShamanImbueWindfury", None),
    ("Flametongue Weapon", 25489, None, "ShamanImbueFlametongue", None),
]

# Prose fields carrying real consumables that are deliberately left unwired. The
# reason travels into the generated file, so a reader asking why a spec runs no
# scroll gets an answer rather than a silence.
DECLINED = {
    "elixirs_instead":
        "A flask counts as both a battle and a guardian elixir in 2.4.3, and "
        "this field names what to drink INSTEAD of the flask. Wiring both would "
        "stack two things the game does not stack.",
    "against_demons":
        "Elixir of Demonslaying replaces the battle elixir against demons only. "
        "The encounter these runs use is a generic level 73 target, so a "
        "demon-only elixir would be credited against a target that is not one.",
    "scrolls":
        "Several specs name a scroll in the same sentence that rejects it, so "
        "matching on the name would switch on a scroll the source turned down. "
        "A scroll is 20 points of one stat; a wrong one is a wrong number.",
    "other":
        "Runes, ammunition, sapper charges and seeds, mixed with prose about "
        "which raider brings them. No single ConsumesSpec field answers it.",
}


def load_db_catalog() -> dict:
    """Every db.json consumable, indexed by name, with its type and its id.

    A DUPLICATE NAME STOPS THE RUN. Four Major Protection Potions appear twice
    in this array under two ids, and picking either silently would be exactly
    the mistake this project has made four times on item names.
    """
    if not DB.is_file():
        raise SystemExit(
            f"extract_consumable_ids.py: no item database at {DB}. Set "
            "WOWSIMS_TBC to a wowsims-tbc-new checkout.")
    entries = json.loads(DB.read_text())["consumables"]
    catalog: dict = {}
    duplicates: dict = {}
    for entry in entries:
        name = entry["name"]
        if name in catalog and catalog[name]["id"] != entry["id"]:
            duplicates.setdefault(name, [catalog[name]["id"]]).append(entry["id"])
        catalog[name] = {"id": entry["id"], "type": entry.get("type")}
    for name, ids in duplicates.items():
        catalog[name]["duplicate_ids"] = sorted(ids)
    return catalog


def verify_imbues() -> None:
    """Check every IMBUES row against the vendored simulator before using it.

    THE DEFECT THIS PREVENTS is an id the request carries and the simulator
    drops. `mhImbue_id` is an int32, so any number is accepted by the encoder,
    and a value outside the switch in registerStaticImbue produces a run that
    succeeds with no imbue on the weapon. Nothing in the output says so.
    """
    ui = IMBUE_UI.read_text() if IMBUE_UI.is_file() else ""
    accepting = {
        "sim/core/consumes.go::registerStaticImbue":
            IMBUE_SIM.read_text() if IMBUE_SIM.is_file() else "",
    }
    for path, key in ((ROGUE_SIM, "sim/rogue/poisons.go::instantImbueID"),
                      (ROGUE_SIM, "sim/rogue/poisons.go::deadlyImbueID"),
                      (ROGUE_SIM, "sim/rogue/poisons.go::woundImbueID")):
        accepting[key] = path.read_text() if path.is_file() else ""
    if not ui:
        raise SystemExit(
            f"extract_consumable_ids.py: no imbue table at {IMBUE_UI}. Every "
            "imbue id in this project is read from that file, so it cannot be "
            "regenerated without it.")

    for name, value, item_id, const, accepted_by in IMBUES:
        block = re.search(
            r"export const " + re.escape(const) + r"\s*=\s*\{(.*?)\}", ui, re.S)
        if not block:
            raise SystemExit(
                f"extract_consumable_ids.py: {const} is no longer declared in "
                f"{IMBUE_UI}. {name} claims imbue id {value} on the strength of "
                "that declaration, so the claim cannot stand without it.")
        body = block.group(1)
        if f"value: {value}" not in body:
            raise SystemExit(
                f"extract_consumable_ids.py: {const} no longer carries value "
                f"{value} in {IMBUE_UI}, so the id claimed for {name} is stale.")
        if item_id is not None and f"fromItemId({item_id})" not in body:
            raise SystemExit(
                f"extract_consumable_ids.py: {const} no longer names item "
                f"{item_id} in {IMBUE_UI}, so the name {name!r} is unsupported.")
        if accepted_by and str(value) not in accepting.get(accepted_by, ""):
            raise SystemExit(
                f"extract_consumable_ids.py: {accepted_by} no longer reads "
                f"{value}, so {name} would be sent and ignored.")


def matches(prose: str, names: list[str]) -> list[tuple[int, str]]:
    """Every catalog name in this prose, earliest first, longest at a tie."""
    found = []
    for name in names:
        at = prose.find(name)
        if at >= 0:
            found.append((at, -len(name), name))
    return [(at, name) for at, _, name in sorted(found)]


def resolve(spec: str, block: dict, db: dict, imbues: dict) -> tuple[dict, list, list]:
    """One spec's prose, turned into picks, declines and unresolved entries."""
    picks: dict = {}
    declined: list = []
    unresolved: list = []

    for prose_field, proto_field, want_type in WIRED:
        prose = (block.get(prose_field) or "").strip()
        if not prose:
            continue
        if want_type is None:
            names = list(imbues)
        else:
            names = [n for n, e in db.items() if e["type"] == want_type]
        found = matches(prose, names)
        if not found:
            unresolved.append({
                "spec": spec, "prose_field": prose_field,
                "proto_field": proto_field,
                "why": "no name in this field is in the catalog. The prose is "
                       "quoted so a reader can see whether that is a gap or a "
                       "spec with no such slot",
                "prose": " ".join(prose.split()),
            })
            continue

        # The first accepted name wins. A name the simulator reads and drops is
        # skipped rather than sent, and reported, because a sent-and-dropped id
        # produces a run that looks like it worked.
        chosen = None
        for at, name in found:
            entry = imbues[name] if want_type is None else db[name]
            if want_type is None and entry["accepted_by"] is None:
                unresolved.append({
                    "spec": spec, "prose_field": prose_field,
                    "proto_field": proto_field, "name": name,
                    "why": "the simulator does not read this value out of "
                           "ConsumesSpec, so sending it would change nothing",
                    "where_it_lives": entry["where_it_lives"],
                })
                continue
            if entry.get("duplicate_ids"):
                unresolved.append({
                    "spec": spec, "prose_field": prose_field,
                    "proto_field": proto_field, "name": name,
                    "why": f"the database holds this name twice, under ids "
                           f"{entry['duplicate_ids']}, and nothing here settles "
                           "which one the guide meant",
                })
                continue
            chosen = (at, name, entry)
            break
        if chosen is None:
            continue

        at, name, entry = chosen
        # THE WHOLE FIELD IS QUOTED, not the sentence holding the name. Half
        # these picks are conditional and the condition is usually in a
        # different sentence: the Arcane Mage's flask is named first and called
        # the situational pick two sentences later, and clipping to one sentence
        # printed a flask that read unconditional. A reader of an id needs the
        # clause that qualifies it.
        picks[proto_field] = {
            "name": name,
            "id": entry["id"],
            "from": prose_field,
            "position": "first named in the field",
            "alternatives_named": [n for _, n in found if n != name],
            "prose": " ".join(prose.split()),
        }

    for prose_field in DECLINED:
        if (block.get(prose_field) or "").strip():
            declined.append(prose_field)
    return picks, declined, unresolved


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("data/facts/consumable-ids.yaml"))
    args = ap.parse_args()

    verify_imbues()
    db = load_db_catalog()
    imbues = {
        name: {"id": value, "wowsims_item_id": item_id, "ui_const": const,
               "accepted_by": accepted_by,
               "where_it_lives": None if accepted_by else
               "proto/shaman.proto :: ShamanOptions.imbue_mh for the main hand "
               "and EnhancementShaman.Options.imbue_oh for the off hand, both "
               "class options rather than consumables"}
        for name, value, item_id, const, accepted_by in IMBUES
    }

    blocks = {}
    doc = yaml.safe_load(CONSUMABLES.read_text())
    for spec, entry in (doc.get("specs") or {}).items():
        blocks[spec] = entry.get("consumables") or {}
    rogue = yaml.safe_load(ROGUE.read_text())
    blocks["combat_rogue"] = rogue.get("consumables") or {}

    # DECLINED IS KEYED ON THE FIELD, NOT THE SPEC. The reason is the same for
    # all seventeen, and seventeen copies of one sentence is the second copy
    # problem this project keeps out of its fact files.
    picks, declined, unresolved = {}, {}, []
    for spec in sorted(blocks):
        spec_picks, spec_declined, spec_unresolved = resolve(
            spec, blocks[spec], db, imbues)
        picks[spec] = spec_picks
        for prose_field in spec_declined:
            declined.setdefault(prose_field, {"why": DECLINED[prose_field],
                                              "specs": []})["specs"].append(spec)
        unresolved.extend(spec_unresolved)

    # Only the names something actually took are written out. The whole 105-row
    # database is not a fact about this raid, and copying it here would be a
    # second copy of a file that regenerates.
    taken = {p["name"] for spec in picks.values() for p in spec.values()}
    catalog = {}
    for prose_field, proto_field, want_type in WIRED:
        if want_type is None:
            continue
        rows = {n: {"id": e["id"], "id_from": "db.json consumables[], type "
                    + CONSUMABLE_TYPE[want_type]}
                for n, e in sorted(db.items())
                if e["type"] == want_type and n in taken}
        if rows:
            catalog[proto_field] = rows
    catalog["imbue"] = {
        # THE FULL PATH, not the basename. `consumables.ts` alone reads like
        # this repository's own consumables.yaml to anyone scanning quickly.
        name: {"id": e["id"], "id_from": f"ui/core/components/inputs/"
               f"consumables.ts :: {e['ui_const']}, "
               f"accepted by {e['accepted_by']}",
               "wowsims_item_id": e["wowsims_item_id"]}
        for name, e in imbues.items()
        if name in taken and e["accepted_by"]
    }

    out = {
        "meta": {
            "what": "The simulator id behind every consumable name this project "
                    "sends, and which name each spec sends for which "
                    "ConsumesSpec field.",
            "generated_by": "tools/extract_consumable_ids.py",
            "do_not_edit": "A hand edit is lost on the next `just regen`, and "
                           "`just check` fails the build by regenerating and "
                           "diffing. Fix the prose or the transform.",
            "prose_from": [str(CONSUMABLES), str(ROGUE)],
            "ids_from": {
                "flasks, food and potions": "the `consumables` array of "
                                            "assets/database/db.json in the "
                                            "vendored wowsims-tbc-new checkout",
                "weapon imbues": "ui/core/components/inputs/consumables.ts, "
                                 "checked against the switch in "
                                 "sim/core/consumes.go and the poison ids in "
                                 "sim/rogue/poisons.go. Imbues are NOT in "
                                 "db.json; they are spell ids",
            },
            "rule": "The guides lead with the pick, so the first catalog name "
                    "in a field is taken and every later one is written out "
                    "under alternatives_named. Nothing is chosen for being "
                    "cheaper or conditional.",
            "specs": len(picks),
        },
        "catalog": catalog,
        "picks": picks,
        "declined": declined,
        "unresolved": unresolved,
    }
    args.out.write_text(yaml.safe_dump(out, sort_keys=False, width=88,
                                       allow_unicode=True))
    with_flask = sum(1 for p in picks.values() if "flask_id" in p)
    with_food = sum(1 for p in picks.values() if "food_id" in p)
    with_mh = sum(1 for p in picks.values() if "mhImbue_id" in p)
    print(f"wrote {args.out}: {len(picks)} spec(s), {with_flask} with a flask, "
          f"{with_food} with food, {with_mh} with a main-hand imbue, "
          f"{len(unresolved)} unresolved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
