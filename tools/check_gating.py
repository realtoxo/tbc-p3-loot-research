#!/usr/bin/env python3
"""Fail when a sim profile wears a gem or an enchant Phase 3 cannot supply.

THE GATING WAS ALREADY RECORDED AND NOTHING READ IT. `enchants-gems.yaml` marks
every gem and enchant with `phase_3_available`, and twelve entries are false or
unverified, but no gate compared that list against the gear the profiles
actually name. So the fact sat in the repository being true and unused, which is
the failure mode a fact table exists to prevent.

WHY THE PROFILES ARE THE THING TO CHECK. Published guides are written against
complete 2.4.3 content, where the Isle of Quel'Danas vendors are open and
Zul'Aman has been out for a patch. A profile transcribed from one of those
guides inherits its assumptions silently: the gem list looks ordinary, every
name resolves, and nothing about the page says the meta gem needs a reputation
nobody can earn on 27 August 2026. This check is what makes that visible.

TWO SEVERITIES, because the underlying claims differ in kind. An entry marked
`phase_3_available: false` fails the build. An entry marked `unverified`, or one
whose reason is a schedule inference we have flagged as needing a live re-check,
is reported and does not fail, because refusing to build over a claim we have
already labelled provisional would be asserting more confidence than we hold.

RE-CHECK AFTER LAUNCH. Every `false` here is an inference from the published
Anniversary phase plan rather than an observation of a live realm. The Anniversary
client runs unrestricted 2.4.3 item data, so whether the build gates the ITEMS or
only the ZONE is genuinely open, and `enchants-gems.yaml` records that under
open_questions.anniversary_phase_gating. If week one shows an item reachable, the
fix is to change the fact file, never to silence this check.

Usage:
    python3 tools/check_gating.py
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

GEMS = Path("data/facts/enchants-gems.yaml")
PROFILES = Path("data/facts/sim-profiles")


def gated(node, inherited=None, out=None):
    """Every gem and enchant name the fact file says Phase 3 cannot supply.

    Availability is recorded at whichever level it applies to. A single gem
    carries its own flag; a whole block, such as the six haste gems, carries one
    flag above a list of `entries` that each carry only a name. So a walk has to
    inherit the nearest enclosing verdict rather than expect one per name.
    """
    out = {} if out is None else out
    if isinstance(node, dict):
        verdict = node.get("phase_3_available", inherited)
        name = node.get("name")
        if name and verdict is not True and verdict is not None:
            out[name.lower()] = (name, verdict,
                                 node.get("phase_3_available_reason")
                                 or (inherited and inherited[1] if isinstance(inherited, tuple) else None))
        for key, value in node.items():
            if key == "name":
                continue
            gated(value, verdict, out)
    elif isinstance(node, list):
        for value in node:
            gated(value, inherited, out)
    return out


def reasons(node, out=None):
    """The reason text keyed by name, read the same way the verdicts are."""
    out = {} if out is None else out
    if isinstance(node, dict):
        why = node.get("phase_3_available_reason")
        if why:
            for entry in [node] + list(node.get("entries") or []):
                if entry.get("name"):
                    out.setdefault(entry["name"].lower(), why.strip())
        for value in node.values():
            reasons(value, out)
    elif isinstance(node, list):
        for value in node:
            reasons(value, out)
    return out


def worn(path: Path) -> list[tuple[int, str]]:
    """Every gem and enchant a profile names, with the line it sits on.

    Read as TEXT, not as parsed YAML. The gear rows are inline maps whose gem
    lists and enchant fields are free strings, and a profile is also allowed to
    mention a gem in a note, in a substitution or in a caveat about what a guide
    recommended. All of those are worth catching, and a structural read would
    see only the ones in the fields it knew to look at.
    """
    found = []
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        if line.lstrip().startswith("#"):
            continue
        found.append((number, line))
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gems", type=Path, default=GEMS)
    ap.add_argument("--profiles", type=Path, default=PROFILES)
    args = ap.parse_args()

    if not args.gems.exists():
        print(f"error: not found: {args.gems}", file=sys.stderr)
        return 2

    facts = yaml.safe_load(args.gems.read_text())
    blocked = gated(facts)
    why = reasons(facts)
    if not blocked:
        print("error: no gating recorded in enchants-gems.yaml, so this check "
              "would pass vacuously", file=sys.stderr)
        return 2

    # Longest first, so `Enchant Weapon - Executioner` is reported rather than a
    # shorter name that happens to be a substring of it.
    names = sorted(blocked, key=len, reverse=True)
    patterns = [(name, re.compile(re.escape(name), re.IGNORECASE))
                for name in names]

    failures, warnings = [], []
    profiles = sorted(args.profiles.glob("*.yaml"))
    for profile in profiles:
        for number, line in worn(profile):
            # Every match on the line, not the first. A single socket list
            # holds several gems and a profile transcribed from one guide is
            # likely to carry more than one of that guide's assumptions.
            covered: list[tuple[int, int]] = []
            for key, pattern in patterns:
                for hit in pattern.finditer(line):
                    span = hit.span()
                    # Longest name wins, so a shorter name sitting inside one
                    # already reported is not reported a second time.
                    if any(a <= span[0] and span[1] <= b for a, b in covered):
                        continue
                    covered.append(span)
                    name, verdict, _ = blocked[key]
                    record = (f"{profile}:{number}", name, verdict,
                              why.get(key, ""), line.strip())
                    (failures if verdict is False else warnings).append(record)

    print(f"{len(profiles)} profile(s) checked against "
          f"{len(blocked)} gated gem(s) and enchant(s)")

    for where, name, _, note, line in warnings:
        print(f"  unverified: {name}")
        print(f"    {where}: {line[:100]}")
        if note:
            print(f"    {note.splitlines()[0]}")

    if failures:
        where_from = len({record[0].split(":")[0] for record in failures})
        print(f"\n{len(failures)} gated item(s) worn across {where_from} "
              f"profile(s):", file=sys.stderr)
        for where, name, _, note, line in failures:
            print(f"  {name}", file=sys.stderr)
            print(f"    {where}: {line[:100]}", file=sys.stderr)
            if note:
                print(f"    why: {note.splitlines()[0]}", file=sys.stderr)
        print("\nThe gear is what to change, not this check. If an item turns "
              "out to be reachable, correct data/facts/enchants-gems.yaml.",
              file=sys.stderr)
        return 1

    print("no profile wears a gem or an enchant Phase 3 cannot supply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
