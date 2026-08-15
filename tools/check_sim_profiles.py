#!/usr/bin/env python3
"""Fail the build on a sim profile that could not be worn, or a routed wrong id.

WHY THIS EXISTS. On 15 August 2026 `data/judgments/weapon-routing.yaml` recorded
Tempest of Chaos as item 32943. That id is Swiftsteel Bludgeon, a one-hand mace;
the weapon is 30910, a main-hand sword. Nothing caught it, because no check
resolved a routed id against a name. AGENTS.md already states the rule that
would have caught it, that only the id settles which item is meant, and this
file is that rule made mechanical for the simulator side.

THE SECOND FAILURE THIS CATCHES is a profile that could not exist on a
character. A two-handed weapon beside an off hand is the one that keeps
occurring, because five published lists rank a staff AND an off hand in the same
capture and only a ruling settles which is worn. The simulator accepts the pair
and returns a larger number, so it fails as a result rather than as an error,
which is the failure mode this project meets over and over.

WHAT IT DELIBERATELY DOES NOT FAIL ON. The same item equipped in two slots. Four
Phase 3 pages rank a ring or a weapon as "Best x2", meaning the spec wants two
copies, and two copies of an item that is not unique is a legal set. It is
REPORTED, because a council reading a profile that wants two of one drop should
see that before the drop lands, and it is not an error.

Usage:
    python3 tools/check_sim_profiles.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import yaml

GEAR = Path("data/sim/gear")
ITEMS = Path("data/facts/items.csv")
ROUTING = Path("data/judgments/weapon-routing.yaml")
TRINKETS = Path("data/judgments/trinket-routing.yaml")
BIS_CAPTURES = Path("data/facts/sim-profiles/bis-capture")
DB = Path(os.path.expanduser(os.environ.get(
    "WOWSIMS_TBC",
    "../tbc-phase-research-recovered/data/raw/vendor/wowsims-tbc-new-master",
))) / "assets/database/db.json"

SLOT_ORDER = [
    "head", "neck", "shoulder", "back", "chest", "wrist", "hands", "waist",
    "legs", "feet", "ring_1", "ring_2", "trinket_1", "trinket_2", "main_hand",
    "off_hand", "ranged",
]

# proto/common.proto :: HandType. Transcribed, not inferred, which is the rule
# every enum in this repository is held to after two enum bugs in
# tools/extract_items.py.
MAIN_HAND, ONE_HAND, OFF_HAND, TWO_HAND = 1, 2, 3, 4
HAND_NAME = {MAIN_HAND: "Main Hand", ONE_HAND: "One Hand",
             OFF_HAND: "Off Hand", TWO_HAND: "Two Hand"}


def every_yaml_parses() -> list[str]:
    """Every YAML file under data/ loads, because one of them did not.

    ON 15 AUGUST 2026 data/facts/sim-results.yaml WAS COMMITTED BROKEN. A plain
    multi-line scalar containing ": " is not valid YAML, the file had one, and it
    survived a full `just check` because no tool in this repository reads that
    particular file. Every fact table is only as good as something loading it,
    and a table nothing loads is a table nothing validates.

    THIS IS DELIBERATELY A PARSE CHECK AND NOTHING MORE. It asserts no schema,
    because a schema per file is a second copy of what each file already says
    about itself. It asserts that the bytes are YAML.
    """
    problems = []
    for path in sorted(Path("data").rglob("*.yaml")):
        try:
            yaml.safe_load(path.read_text())
        except Exception as exc:  # noqa: BLE001 - the message is the whole point
            first = str(exc).replace("\n", " ")[:200]
            problems.append(f"{path}: is not valid YAML. {first}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gear", type=Path, default=GEAR)
    args = ap.parse_args()

    if not DB.is_file():
        print(f"error: no simulator database at {DB}. Set WOWSIMS_TBC.",
              file=sys.stderr)
        return 1
    db = json.loads(DB.read_text())
    db_items = {i["id"]: i for i in db["items"]}
    items_csv = {int(r["item_id"]): r for r in csv.DictReader(ITEMS.open())}

    failures: list[str] = every_yaml_parses()
    reports: list[str] = []

    # ---------------------------------------------------------------- routing
    # EVERY ROUTED ID RESOLVES, AND THE NAME BESIDE IT AGREES. This is the check
    # the Tempest of Chaos defect got past.
    routing = yaml.safe_load(ROUTING.read_text())
    for ruling in routing.get("rulings") or []:
        claimed = (ruling.get("weapon") or "").strip()
        for item_id in ruling.get("ids") or []:
            row = items_csv.get(int(item_id))
            actual = (row or {}).get("name") \
                or (db_items.get(int(item_id)) or {}).get("name")
            if actual is None:
                failures.append(
                    f"{ROUTING}: ruling {claimed!r} routes item {item_id}, "
                    "which resolves in neither items.csv nor the simulator "
                    "database")
            elif actual.strip().lower() != claimed.lower():
                failures.append(
                    f"{ROUTING}: ruling {claimed!r} routes item {item_id}, "
                    f"which is {actual!r}. A ruling names a weapon and the id "
                    "beside it has to be that weapon.")

    # EVERY TRINKET RULING RESOLVES TOO, by the same rule, and the barred list
    # is read here so the check does not depend on the builder having applied it.
    trinkets = yaml.safe_load(TRINKETS.read_text())
    barred = {}
    for block in trinkets.get("unavailable_content") or []:
        for item in block.get("barred_items") or []:
            barred[int(item["id"])] = (block["content"], item["item"])
    for ruling in trinkets.get("rulings") or []:
        claimed = (ruling.get("item") or "").strip()
        for item_id in ruling.get("ids") or []:
            actual = (items_csv.get(int(item_id)) or {}).get("name") \
                or (db_items.get(int(item_id)) or {}).get("name")
            if actual is None or actual.strip().lower() != claimed.lower():
                failures.append(
                    f"{TRINKETS}: ruling {claimed!r} routes item {item_id}, "
                    f"which is {actual!r}. A ruling names an item and the id "
                    "beside it has to be that item.")
    for item_id, (content, name) in barred.items():
        actual = (items_csv.get(item_id) or {}).get("name") \
            or (db_items.get(item_id) or {}).get("name")
        if actual is None or actual.strip().lower() != name.strip().lower():
            failures.append(
                f"{TRINKETS}: {content} bars item {item_id} as {name!r}, which "
                f"resolves to {actual!r}. A bar on the wrong id bars nothing.")

    # ------------------------------------------------------------------ gear
    for path in sorted(args.gear.glob("*.gear.json")):
        stem = path.name[:-len(".gear.json")]
        gear = json.loads(path.read_text())["items"]
        if len(gear) != len(SLOT_ORDER):
            failures.append(
                f"{stem}: holds {len(gear)} slots, not {len(SLOT_ORDER)}. The "
                "slot order is positional, so a short list silently moves every "
                "item below the gap into the wrong slot.")
            continue

        worn = {}
        for i, slot in enumerate(SLOT_ORDER):
            item_id = (gear[i] or {}).get("id")
            if not item_id:
                continue
            if item_id in barred:
                content, name = barred[item_id]
                failures.append(
                    f"{stem}: {slot} holds {name}, which drops in {content}. "
                    f"This guild does not run it, ruled by the guild lead in "
                    f"{TRINKETS}, so the item is not a weaker pick, it is not a "
                    "pick. The simulator will happily equip it.")
            if item_id not in db_items:
                failures.append(
                    f"{stem}: {slot} holds item {item_id}, which the simulator "
                    "database does not know. It imports as an EMPTY slot and "
                    "the run succeeds with a smaller number.")
                continue
            worn.setdefault(item_id, []).append(slot)

        # A NAME AND AN ID THAT DISAGREE, where items.csv holds both.
        for item_id, slots in worn.items():
            row = items_csv.get(item_id)
            if row and row["name"] != db_items[item_id]["name"]:
                failures.append(
                    f"{stem}: item {item_id} is {row['name']!r} in items.csv "
                    f"and {db_items[item_id]['name']!r} in the simulator "
                    "database. One of the two tables is wrong about this item.")
            if len(slots) > 1:
                reports.append(
                    f"{stem}: {db_items[item_id]['name']} is worn in "
                    f"{len(slots)} slots, {' and '.join(slots)}. Four Phase 3 "
                    "pages rank an item 'Best x2', so this is the published "
                    "recommendation and not an error, but it means the spec "
                    "wants TWO of that drop.")

        main_id = (gear[SLOT_ORDER.index("main_hand")] or {}).get("id")
        off_id = (gear[SLOT_ORDER.index("off_hand")] or {}).get("id")
        main_hand = db_items.get(main_id) if main_id else None
        off_hand = db_items.get(off_id) if off_id else None

        if main_hand and main_hand.get("handType") == TWO_HAND and off_id:
            failures.append(
                f"{stem}: main hand holds {main_hand['name']}, a two-handed "
                f"weapon, beside an off hand, {off_hand['name'] if off_hand else off_id}. "
                "A character cannot wear both. The simulator accepts the pair "
                "and returns a LARGER number, so this fails as a result rather "
                "than as an error.")
        if off_hand and off_hand.get("handType") == MAIN_HAND:
            failures.append(
                f"{stem}: off hand holds {off_hand['name']}, which is "
                "Main Hand only.")
        if main_hand and main_hand.get("handType") == OFF_HAND:
            failures.append(
                f"{stem}: main hand holds {main_hand['name']}, which is "
                "Off Hand only.")
        if off_id and not main_id:
            failures.append(
                f"{stem}: holds an off hand and no main hand.")

    # --------------------------------------------------- every anchor exported
    # A SPEC MISSING AN ANCHOR IS INVISIBLE ON THE PAGE rather than wrong on it,
    # which is the harder failure to notice: the table renders, one cell reads
    # "not simulated", and nothing says whether that was a ruling or a crash.
    for capture in sorted(BIS_CAPTURES.glob("*.yaml")):
        spec_slug = capture.stem
        for anchor in ("entry", "tier-hands-and-head", "bis"):
            if not (args.gear / f"{spec_slug}.{anchor}.gear.json").is_file():
                failures.append(
                    f"{spec_slug}: has a best-in-slot capture but no {anchor} "
                    "gear file. Run `just sim-profiles`.")

    if reports:
        print(f"{len(reports)} profile(s) wear two copies of one item:")
        for line in reports:
            print(f"  {line}")
    if failures:
        print(f"\n{len(failures)} failure(s):", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1
    print(f"\nsim profiles: every routed id resolves to the weapon its ruling "
          f"names, and every profile could be worn")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
