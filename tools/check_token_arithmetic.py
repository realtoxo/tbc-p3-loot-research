#!/usr/bin/env python3
"""Verify every EP figure in token-arithmetic.yaml against the workbook.

THE FIGURES WERE UNCITED AND TWO SPECS' WERE WRONG. This file was
conventionalized from twenty-one per-spec agent captures whose reports were not
retained, so their sources were lost and the numbers stood on nothing. A sweep
on 9 August 2026 reproduced fourteen exactly and contradicted seven: the Balance
Druid's were reversed in DIRECTION, making a token that gains 16.88 read as a
loss, and that claim was printing on its card.

WHAT MAKES THIS CHECKABLE AT ALL is that the EP Workbook is in the repository,
under data/research/epv-workbook, one tab per spec. So a figure quoted beside an
item name either appears on that spec's tab or it does not, and there is no
third possibility. That is the same shape as the check comparing a captured
gear row against items.csv, which caught three understated rows the
self-consistency check could not.

HOW A FIGURE IS FOUND. The file writes prose, not fields, so this reads
`<Item Name> <number>` pairs out of the text. A pair is checked only when the
item name resolves on that spec's tab, which means a name this cannot resolve is
reported as unverifiable rather than passed. Both score columns are accepted,
because the non-healer tabs carry an `If Hit Capped` column beside `EPV` and
either is a legitimate thing to quote.

Usage:
    python3 tools/check_token_arithmetic.py
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import yaml

TOKENS = Path("data/facts/sim-profiles/token-arithmetic.yaml")
WORKBOOK = Path("data/research/epv-workbook")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_ladder import SPECS  # noqa: E402
from extract_hit_captures import (  # noqa: E402
    TOKEN_CONFIGURATION_CONTESTED)

# An item name followed by a score. Names run from a capital through letters,
# apostrophes, hyphens and spaces; scores carry one or two decimal places.
PAIR = re.compile(r"([A-Z][A-Za-z'\-/ ]{4,44}?)\s+(\d{2,4}\.\d{1,2})")

# How far a quoted figure may sit from the workbook's, to absorb the file
# rounding to one decimal where the tab carries two.
TOLERANCE = 0.06

# Keys whose text is a RETRACTION and therefore quotes figures on purpose. A
# correction has to be able to say what it corrects, so those numbers must not
# be checked against the workbook; they are there precisely because they
# disagree with it. Any other key is checked.
RETRACTION_KEYS = {"previously_claimed", "corrected", "retracted"}


def scores(tab: Path) -> dict[str, set[float]]:
    """Every score the tab carries, by item name.

    Column 5 is EPV on every tab. Column 6 is `If Hit Capped` on the fourteen
    non-healer tabs and the Location on the four healer tabs, so it is read
    only where it parses as a number.
    """
    out: dict[str, set[float]] = {}
    if not tab.is_file():
        return out
    for row in csv.reader(tab.open(newline="", encoding="utf-8")):
        if len(row) <= 6 or not row[2].strip():
            continue
        for column in (5, 6):
            try:
                out.setdefault(row[2].strip(), set()).add(
                    round(float(row[column].replace(",", "")), 2))
            except (ValueError, IndexError):
                pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tokens", type=Path, default=TOKENS)
    ap.add_argument("--workbook", type=Path, default=WORKBOOK)
    args = ap.parse_args()

    tab_of = {spec_id: tab for tab, spec_id in SPECS.values()}
    specs = yaml.safe_load(args.tokens.read_text())["specs"]

    reproduced = 0
    unresolved: list[str] = []
    wrong: list[str] = []
    for spec, block in sorted(specs.items()):
        tab = tab_of.get(spec)
        if not tab:
            unresolved.append(f"{spec} maps to no workbook tab")
            continue
        table = scores(args.workbook / tab)
        if not table:
            unresolved.append(f"{spec} names tab {tab}, which is absent")
            continue
        text = " ".join(str(value) for key, value in block.items()
                        if key not in RETRACTION_KEYS)
        for name, number in PAIR.findall(text):
            found = table.get(name.strip())
            if not found:
                continue
            quoted = round(float(number), 2)
            if any(abs(quoted - value) < TOLERANCE for value in found):
                reproduced += 1
            else:
                wrong.append(
                    f"{spec} quotes {quoted} for {name.strip()!r} and {tab} "
                    f"carries {sorted(found)}")

    print(f"{len(specs)} spec(s) checked against {args.workbook}")
    print(f"  {reproduced} figure(s) reproduce on the spec's own tab")
    for line in unresolved:
        print(f"  unverifiable: {line}")

    if wrong:
        print(f"\n{len(wrong)} figure(s) the workbook contradicts:",
              file=sys.stderr)
        for line in wrong:
            print(f"  {line}", file=sys.stderr)
        print("\nThe workbook is the source. Correct the figure, and say in "
              "the entry what it used to claim.", file=sys.stderr)
        return 1

    print("every resolvable figure agrees with the workbook")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
