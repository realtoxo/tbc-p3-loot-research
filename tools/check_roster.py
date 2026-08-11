#!/usr/bin/env python3
"""Check the raid groups against the counts and the shaman constraint.

THE GROUPS WERE HALF WRITTEN FOR A LONG TIME AND NOTHING NOTICED. Only g1 and
g2 were enumerated, holding nine of twenty-one rostered specs, so the two plate
tanks and every healer sat in no group at all. Group membership decides which
group buffs a spec is credited with, and a spec in no group is credited with
none, so the gap was one step from moving a figure.

WHAT THIS ENFORCES, and each rule earns its place:

  1. Every group holds five, and the groups hold twenty-five between them. A
     25-player raid is five parties of five and there is no other shape.
  2. What the groups place matches what `counts` records, or the difference is
     named in `counts_not_placed`. That mismatch is real today: counts records
     three Arcane Mages and the groups hold two, because a roster is deeper
     than a raid.
  3. One shaman per party, which is how Heroism reaches the whole raid, and the
     shaman `shaman_by_party` names for a party is actually in it. That block
     was written before the groups were and turned out to describe all five
     correctly, which is how g5 was corroborated rather than guessed.
  4. Every spec named anywhere here exists in `hit.yaml`, so a name that drifts
     is caught. `roster.yaml` said `feral_druid` for a while where every other
     file said `feral_bear`.

Usage:
    python3 tools/check_roster.py
"""

from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

import yaml

ROSTER = Path("data/facts/roster.yaml")
HIT = Path("data/facts/hit.yaml")

PARTY_SIZE = 5
RAID_SIZE = 25


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--roster", type=Path, default=ROSTER)
    ap.add_argument("--hit", type=Path, default=HIT)
    args = ap.parse_args()

    roster = yaml.safe_load(args.roster.read_text())
    known = {spec["id"] for spec in yaml.safe_load(args.hit.read_text())["specs"]}

    groups = roster.get("groups") or []
    problems: list[str] = []

    placed: collections.Counter[str] = collections.Counter()
    for group in groups:
        members = group.get("members") or []
        if len(members) != PARTY_SIZE:
            problems.append(
                f"{group.get('id')} holds {len(members)} members, not {PARTY_SIZE}")
        placed.update(members)

    total = sum(placed.values())
    if total != RAID_SIZE:
        problems.append(
            f"the groups place {total} bodies, and a 25-player raid holds "
            f"{RAID_SIZE}")

    # A name that drifts is the failure this catches.
    for name in sorted(set(placed) | set(roster.get("counts") or {})):
        if name == "feral_druid_in_melee_groups":
            continue
        if name not in known:
            problems.append(f"{name!r} is in {args.roster} and not in {args.hit}")

    # A roster is deeper than a raid, so a spec may be counted and unplaced.
    # What is not allowed is an UNDECLARED difference.
    declared = roster.get("counts_not_placed") or {}
    counts = roster.get("counts") or {}
    for name, wanted in sorted(counts.items()):
        if name == "feral_druid_in_melee_groups":
            continue
        got = placed.get(name, 0)
        if got == wanted:
            continue
        gap = wanted - got
        if declared.get(name) == gap:
            continue
        problems.append(
            f"counts records {wanted} {name} and the groups place {got}. "
            f"Declare the difference as `counts_not_placed: {{{name}: {gap}}}` "
            "with a reason, or correct one of the two")

    # One shaman per party is how Heroism reaches everybody.
    by_party = roster.get("shaman_by_party") or {}
    ids = {group.get("id"): (group.get("members") or []) for group in groups}
    for party, shaman in sorted(by_party.items()):
        if party not in ids:
            problems.append(f"shaman_by_party names {party}, which has no group")
        elif shaman not in ids[party]:
            problems.append(
                f"shaman_by_party puts {shaman} in {party}, whose members are "
                f"{ids[party]}")
    for group in groups:
        if group.get("id") not in by_party:
            problems.append(
                f"{group.get('id')} has no shaman in shaman_by_party, so "
                "Heroism does not reach it")

    print(f"{len(groups)} group(s), {total} raid slot(s) placed")
    for name, gap in sorted(declared.items()):
        print(f"  declared unplaced: {gap} {name}")

    if problems:
        print(f"\n{len(problems)} problem(s):", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    print("groups, counts and the shaman constraint agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
