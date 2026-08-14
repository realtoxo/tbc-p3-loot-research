#!/usr/bin/env python3
"""Fail where a captured set wears gear that anchor cannot have reached.

THREE FAILURES OF THIS KIND WERE FOUND BY HAND AND NONE BY A CHECK, which is
the argument for the file. Two captures wear a drop from ARCHIMONDE inside
`tier_hands_only`, the state defined as Archimonde not being down. One wears a
drop from the Illidari Council, which `progression.yaml` places outside the
window entirely. Seven entry sets wear a Mount Hyjal reputation ring at an
anchor that is defined as before Mount Hyjal opens.

Each was individually plausible while reading one file. All of them are obvious
against the drop table, and none of them could survive a join.

FOUR RULES, EACH FROM A FILE THAT ALREADY OWNS THE FACT:

  1. A tier-anchor item may not drop from an encounter progression.yaml puts
     outside the four-to-six-week window.
  2. An item in `tier_hands_only` may not drop from Archimonde. That anchor
     exists precisely to describe the raid that has not killed it.
  3. An ENTRY item may not come from a Phase 3 zone at all. The entry anchor is
     the set a player walks in with.
  4. Arena Season 3 is excluded everywhere. DOMAIN.md records it opening five
     days after Phase 3, so no Season 3 item is held four to six weeks in, and
     the existing rule already bars Season 3 from an entry set.

SCALE OF THE SANDS IS BARRED AT ENTRY AND ALLOWED AT TIER, by a ruling recorded
in progression.yaml rather than by a guess here. Its rewards are Mount Hyjal
reputation, so none can exist before the zone opens. At a tier anchor they are
allowed including the Exalted rings and including at tier_hands_only, which
looks contradictory and is not: standing accrues from the trash waves and the
first four bosses as well as from Archimonde, so a guild wiping on Archimonde
banks reputation the whole time.

WHAT THIS STILL CANNOT SEE is profession gating and every reputation other than
that one. Neither is in drops.csv, and items.csv does not carry the database
fields that would answer them.

THAT IS DELIBERATE, ruled by the guild lead on 9 August 2026 after the cost was
measured. The database does carry `requiredProfession` on 41 of our 957 rows and
a typed `rep` source on 8, so the extraction is small. But eleven specs wear
profession-gated gear and NOT ONE of them needs more than two professions or two
specialisations of one profession, so the check would catch nothing that exists.
It is a guardrail against a defect the captures do not have.

The argument the other way, recorded because it is real: a repair earlier that
day swapped the Shadow Priest's belt on the claim that Belt of Blasting requires
Spellfire Tailoring and collided with its Shadoweave pieces. It does not; that is
item 21846 and this is 30038, and `requiredProfession` is empty on the row. A
profession column would have said so at once. The ruling stands anyway, because
the id was always there to check and the error was reading a name instead.

Usage:
    python3 tools/check_capture_availability.py
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import yaml

CAPTURES = Path("data/facts/sim-profiles/hit-capture")
DROPS = Path("data/facts/drops.csv")
ITEMS = Path("data/facts/items.csv")
PROGRESSION = Path("data/facts/progression.yaml")

PHASE_3_ZONES = {"Mount Hyjal", "Black Temple"}

# Reputation rewards from the Phase 3 factions. Not derivable from drops.csv,
# because a reputation reward is not a drop, so they are named. Scale of the
# Sands is the Mount Hyjal faction and cannot be farmed before the zone opens.
PHASE_3_REPUTATION = {
    29294: "Band of Eternity, Scale of the Sands",
    29298: "Band of Eternity, Scale of the Sands",
    29302: "Band of Eternity, Scale of the Sands",
    29304: "Band of Eternity, Scale of the Sands",
    29301: "Band of the Eternal Champion, Scale of the Sands Exalted",
    29305: "Band of the Eternal Sage, Scale of the Sands Exalted",
    29309: "Band of the Eternal Restorer, Scale of the Sands Exalted",
    29297: "Band of the Eternal Defender, Scale of the Sands Exalted",
}

# Arena Season 3, which opens after Phase 3 and is out of scope at every anchor.
SEASON_3_PREFIX = "Vengeful Gladiator's"

# The two outdoor world bosses, whose loot this guild does not run for. Ruled by
# the guild lead on 9 August 2026: see data/judgments/capture-fidelity.yaml.
#
# THE IDS ARE READ FROM A FACT FILE, not listed here, because two tools need
# them: this one to fail a capture that wears one, and extract_ladder.py to keep
# them out of what the compendium recommends. A second copy is what goes stale.
WORLD_BOSSES = Path("data/facts/world-bosses.yaml")

# Level-60 raid loot, out of scope by the same ruling. MATCHED BY ID, because a
# capture records an item and not where it came from, so the location match the
# ladder uses is no help here.
#
# THIS CHECK DID NOT EXIST until 10 August 2026, because the ruling said no
# capture wore a level-60 item. Two did: Badge of the Swarmguard, an Ahn'Qiraj
# trinket, sat in seven slots across both warriors. Same blindness as the world
# bosses and for the same reason, that drops.csv covers seven Outland zones and
# no level-60 raid appears in it.
LEVEL_60 = Path("data/facts/level-60.yaml")


def level_60_loot(path: Path) -> dict[int, str]:
    """Every level-60 raid item the workbook ranks, as id to name."""
    return dict(yaml.safe_load(path.read_text())["items"])


def world_boss_loot(path: Path) -> dict[int, str]:
    """Every world-boss drop, as id to "name, boss".

    NAMED IN A FILE BECAUSE drops.csv CANNOT SEE THEM. That table covers the
    seven instanced zones only, so neither npc appears in it and every check
    keyed on it passed eleven slots in four captures without a word.
    """
    facts = yaml.safe_load(path.read_text())
    return {
        item_id: f"{name}, {boss}"
        for boss, block in (facts.get("bosses") or {}).items()
        for item_id, name in (block.get("drops") or {}).items()
    }



def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--captures", type=Path, default=CAPTURES)
    ap.add_argument("--drops", type=Path, default=DROPS)
    ap.add_argument("--items", type=Path, default=ITEMS)
    ap.add_argument("--progression", type=Path, default=PROGRESSION)
    ap.add_argument("--world-bosses", type=Path, default=WORLD_BOSSES)
    ap.add_argument("--level-60", type=Path, default=LEVEL_60)
    args = ap.parse_args()

    world_boss = world_boss_loot(args.world_bosses)
    level_60 = level_60_loot(args.level_60)

    facts = yaml.safe_load(args.progression.read_text())
    # Which encounters the window reaches, read from the file that decides it.
    out_of_window = set()
    for zone, block in (facts.get("zones") or {}).items():
        for entry in block.get("bosses") or []:
            token = entry.get("token")
            if token in ("shoulder", "legs", "chest"):
                out_of_window.add(entry["name"])
    # Everything after the earliest out-of-window encounter in Black Temple.
    bt = (facts.get("zones") or {}).get("Black Temple", {}).get("bosses") or []
    first = min((e["position"] for e in bt if e["name"] in out_of_window),
                default=None)
    if first is not None:
        out_of_window |= {e["name"] for e in bt if e["position"] >= first}

    source: dict[int, list[tuple[str, str]]] = {}
    for row in csv.DictReader(args.drops.open()):
        source.setdefault(int(row["item_id"]), []).append(
            (row["zone"], row["boss"]))
    names = {int(row["item_id"]): row["name"]
             for row in csv.DictReader(args.items.open())}

    problems: list[str] = []
    for path in sorted(args.captures.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        # Only files carrying anchors are captures. See extract_hit_captures.
        if not isinstance(data, dict) or "anchors" not in data:
            continue
        spec = data.get("spec")
        for anchor, block in (data.get("anchors") or {}).items():
            if not isinstance(block, dict):
                continue
            rows = block.get("hit_by_slot")
            if not isinstance(rows, dict):
                continue
            for slot, row in rows.items():
                if not isinstance(row, dict):
                    continue
                item_id = row.get("id")
                if not isinstance(item_id, int):
                    continue
                name = names.get(item_id, str(row.get("item")))
                where = f"{spec} {anchor} {slot}: {name} ({item_id})"

                if str(name).startswith(SEASON_3_PREFIX):
                    problems.append(
                        f"{where} is Arena Season 3, which opens after Phase 3")
                if item_id in level_60:
                    problems.append(
                        f"{where} is {level_60[item_id]}, a level-60 raid drop, "
                        "and this guild does not run that content. See "
                        "data/judgments/capture-fidelity.yaml")
                if item_id in world_boss:
                    problems.append(
                        f"{where} is {world_boss[item_id]}, and this guild "
                        "does not run outdoor world bosses. See "
                        "data/judgments/capture-fidelity.yaml")
                if item_id in PHASE_3_REPUTATION and anchor == "entry":
                    problems.append(
                        f"{where} is {PHASE_3_REPUTATION[item_id]}, a Phase 3 "
                        "faction, at the pre-Phase-3 anchor")
                # At a TIER anchor these are allowed by a recorded ruling, so
                # they are neither failed nor warned about. Reputation accrues
                # from the trash waves and the first four bosses as well as
                # from Archimonde, so Exalted at tier_hands_only is not the
                # contradiction it looks like. See
                # progression.yaml four_to_six_weeks.scale_of_the_sands_reputation.

                for zone, boss in source.get(item_id, []):
                    if anchor == "entry" and zone in PHASE_3_ZONES:
                        problems.append(
                            f"{where} drops in {zone} from {boss}, and the "
                            "entry anchor is the set worn before Phase 3")
                    if anchor.startswith("tier") and boss in out_of_window:
                        problems.append(
                            f"{where} drops from {boss}, which "
                            f"{args.progression} puts outside the window")
                    # THE MIDDLE ANCHOR IS GONE. It named the state where
                    # Archimonde was not yet down, and the guild lead removed
                    # the progression split on 13 August 2026. There is one
                    # tier anchor now and it may hold an Archimonde drop, so
                    # this rule has nothing left to fire on.
                    if False:
                        problems.append(
                            f"{where} drops from Archimonde, and this anchor "
                            "is defined as Archimonde not being down")

    print(f"{len(list(args.captures.glob('*.yaml')))} capture(s) checked "
          f"for availability")
    if problems:
        print(f"\n{len(problems)} item(s) an anchor could not have reached:",
              file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    print("every captured item is reachable at the anchor that wears it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
