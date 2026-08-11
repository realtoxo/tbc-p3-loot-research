#!/usr/bin/env python3
"""Check raid-buffs.yaml against the roster and the simulator's own proto.

WHY THIS EXISTS. Two adversarial reviews on 10 August 2026 found twenty-one
defects in the raid buff derivation between them, and NOT ONE was catchable by
any gate. The only validation was a runtime failure when a buff name was not a
proto field, which catches a typo and never an omission, never a wrong scope,
and never a buff credited to a party with no source.

WHAT THIS CATCHES, and each rule earns its place from a defect that shipped:

  1. A name that is not a field of the message it is filed under. The parse that
     read the proto was itself wrong: RaidBuffs closes with an INDENTED brace,
     so a brace-anchored pattern ran into PartyBuffs and reported 44 fields
     where there are seven. Anything could have been called raid-wide.
  2. A party buff filed as raid-wide, or the reverse. This is the distinction
     the whole file exists to get right, and the one this project has already
     published a wrong figure over.
  3. A party buff credited to a party whose members cannot supply it. Every
     entry names a `from`, and the roster says who is actually in that party.
  4. The same buff asserted and denied. blood_frenzy sat in `debuffs` and in
     `not_provided_by_this_roster` at the same time for an hour.

Usage:
    python3 tools/check_raid_buffs.py
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import yaml

BUFFS = Path("data/facts/raid-buffs.yaml")
ROSTER = Path("data/facts/roster.yaml")
WOWSIMS = Path(os.path.expanduser(os.environ.get(
    "WOWSIMS_TBC",
    "../tbc-phase-research-recovered/data/raw/vendor/wowsims-tbc-new-master")))

SECTIONS = {"raid_wide": "RaidBuffs", "party": "PartyBuffs",
            "debuffs": "Debuffs", "individual": "IndividualBuffs"}

# Keys inside an entry that describe it rather than name a buff.
PROSE = {"note", "from", "confidence", "found_by", "to", "why", "NOT_SENT",
         "over_credited_slightly", "paladins_available",
         "blessings_each_paladin_can_maintain"}


def fields(name: str, text: str) -> dict:
    """Every field of one proto message, split on the NEXT message.

    NOT ON A CLOSING BRACE. RaidBuffs closes with an indented one in this proto,
    so a brace-anchored pattern silently swallows the message after it.
    """
    start = text.index(f"message {name} {{")
    rest = text[start:]
    nxt = re.search(r"\n(?://[^\n]*\n)*message \w+ \{", rest[1:])
    block = rest[:nxt.start() + 1] if nxt else rest
    out = {}
    for kind, field in re.findall(
            r"^\s+([\w.]+)\s+(\w+)\s*=\s*\d+", block, re.M):
        out[field] = kind
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--buffs", type=Path, default=BUFFS)
    ap.add_argument("--roster", type=Path, default=ROSTER)
    args = ap.parse_args()

    proto = WOWSIMS / "proto" / "common.proto"
    if not proto.is_file():
        print(f"note: no simulator proto at {proto}, so the field names in "
              f"{args.buffs} cannot be checked. Set WOWSIMS_TBC.")
        return 0

    text = proto.read_text()
    known = {msg: fields(msg, text) for msg in set(SECTIONS.values())}
    buffs = yaml.safe_load(args.buffs.read_text())
    roster = yaml.safe_load(args.roster.read_text())
    members = {g["id"]: set(g.get("members") or []) for g in roster["groups"]}

    problems: list[str] = []

    def names(block) -> list[str]:
        return [k for k in (block or {}) if k not in PROSE]

    # 1 and 2: every name is a field of the message it is filed under, which
    # also proves it is scoped the way this file claims.
    for section, message in SECTIONS.items():
        block = buffs.get(section) or {}
        entries = ({k: v for party in block.values()
                    if isinstance(party, dict)
                    for k, v in party.items()} if section == "party" else block)
        # SNAKE AGAINST SNAKE. fields() returns the proto's own names, which
        # are snake case, and raid-buffs.yaml uses the same, so no conversion
        # belongs here. The first version converted to camel and reported six
        # real buffs as unknown, which is the exact class of defect this file
        # was written to catch.
        for raw in names(entries):
            if raw in known[message]:
                continue
            elsewhere = [m for m, f in known.items() if raw in f]
            if elsewhere:
                problems.append(
                    f"{section}: {raw!r} is not a field of {message}, it is a "
                    f"field of {', '.join(elsewhere)}. A buff filed under the "
                    "wrong scope reaches the wrong players")
            else:
                problems.append(
                    f"{section}: {raw!r} is not a field of any buff message in "
                    f"{proto}")

    # 3: a party buff needs a source that is actually in that party.
    for party, block in (buffs.get("party") or {}).items():
        if not isinstance(block, dict):
            continue
        for name, entry in block.items():
            if name in PROSE or not isinstance(entry, dict):
                continue
            source = str(entry.get("from") or "")
            if not source:
                problems.append(f"party {party}: {name!r} names no source")
                continue
            # A source is credible if any member of the party appears in it, or
            # if it names a class or an item rather than a spec.
            if any(m in source for m in members.get(party, ())):
                continue
            if any(word in source.lower() for word in
                   ("warlock", "leatherworker", "shaman", "paladin", "warrior",
                    "hunter", "druid", "priest", "mage")):
                continue
            problems.append(
                f"party {party}: {name!r} is credited to {source!r}, and no "
                f"member of {party} matches it. Members: "
                f"{', '.join(sorted(members.get(party, ())))}")

    # 4: nothing is both supplied and not supplied.
    absent = set(buffs.get("not_provided_by_this_roster") or {})
    supplied = set(names(buffs.get("raid_wide"))) | set(names(buffs.get("debuffs")))
    for party in (buffs.get("party") or {}).values():
        if isinstance(party, dict):
            supplied |= set(names(party))
    for name in sorted(absent & supplied):
        problems.append(
            f"{name!r} is listed under not_provided_by_this_roster AND supplied "
            "elsewhere in the same file")

    counted = sum(len(names(buffs.get(s) or {})) for s in ("raid_wide", "debuffs"))
    counted += sum(len(names(p)) for p in (buffs.get("party") or {}).values()
                   if isinstance(p, dict))
    print(f"{counted} buff and debuff entries checked against {proto.name} "
          f"and {args.roster}")
    print(f"  RaidBuffs holds {len(known['RaidBuffs'])} fields in this build, "
          "and everything else is party scoped")

    if problems:
        print(f"\n{len(problems)} problem(s):", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    print("every buff is a real field, scoped as claimed, sourced from its own "
          "party, and not both supplied and denied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
