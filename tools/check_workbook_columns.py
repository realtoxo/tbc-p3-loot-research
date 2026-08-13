#!/usr/bin/env python3
"""Check that no reader crosses into the workbook's shifted stat columns.

THE DEFECT THIS GUARDS, found by a per-spec audit on 11 August 2026. In a
WEAPON section the workbook declares its stat columns as `type, dps, spd, ap,
str, agi` starting at one column, and every data row underneath carries an
EXTRA leading cell holding the equip slot, `One Hand` or `Main Hand` or `Off
Hand`. So the declared header and the data are one column apart, and a reader
that trusts the header reads the weapon TYPE where it asked for dps:

    header  ... type      dps    spd   ap
    data    ... One Hand  Mace   100.3 1.5

IT IS INERT TODAY AND THAT IS THE POINT. `tools/extract_ladder.py` resolves the
columns it needs by name and reaches at most column 10, which is the Wowhead
url. Every stat it publishes comes from `data/facts/items.csv`, keyed on the id
in that url, and never from the workbook's own stat columns. So no figure in
the compendium is wrong today.

WHAT WOULD MAKE IT LIVE. Someone adding `dps` or `speed` or any stat to the
column map, reasonably, because the header says it is there. That change would
read plausible numbers of the wrong kind and nothing else would notice, which
is this project's most common failure. This check fails the build at that
moment rather than after the figures have travelled.

Usage:
    python3 tools/check_workbook_columns.py
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from extract_ladder import SPECS, WORKBOOK, columns  # noqa: E402

# The header word that marks where the shifted block starts. Anything at or
# right of it in a weapon section is one column out from its label.
FIRST_SHIFTED = "type"


def shift_column(rows: list[list[str]]) -> int | None:
    """Where the shifted stat block begins, or None if this tab has none."""
    for row in rows:
        for index, cell in enumerate(row):
            if cell.strip().lower() == FIRST_SHIFTED and index > 10:
                return index
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workbook", type=Path, default=WORKBOOK)
    args = ap.parse_args()

    problems: list[str] = []
    shifted_tabs = 0
    checked = 0

    for spec, (tab, _) in sorted(SPECS.items()):
        path = args.workbook / tab
        if not path.is_file():
            continue
        rows = list(csv.reader(path.open()))
        _, where = columns(rows, path)
        checked += 1
        boundary = shift_column(rows)
        if boundary is None:
            continue
        shifted_tabs += 1
        crossing = {name: at for name, at in where.items() if at >= boundary}
        if crossing:
            problems.append(
                f"{tab}: the column map reads {crossing} at or right of column "
                f"{boundary}, where the declared stat header and the data are "
                "one column apart. Those values are the cell to the LEFT of "
                "what the header names.")

    print(f"{checked} workbook tab(s) checked, {shifted_tabs} carrying the "
          "shifted stat block in their weapon sections")
    if problems:
        print(f"\n{len(problems)} problem(s):", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    print("no reader crosses into the shifted columns: every published stat "
          "comes from items.csv, keyed on the id in the workbook url")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
