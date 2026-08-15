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

CAPTURES = Path("data/facts/sim-profiles/hit-capture")
ITEMS = Path("data/facts/items.csv")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_ladder import SPECS  # noqa: E402
from extract_hit_captures import (  # noqa: E402
    TOKEN_CONFIGURATION_CONTESTED, fill_contested)

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


def resolve(name: str, table: dict[str, set[float]]) -> tuple[str, set[float]]:
    """The longest suffix of `name` the tab knows, and its scores.

    WHY A SUFFIX AND NOT THE WHOLE MATCH. The pair pattern reads prose, so it
    takes whatever words sit before the figure, and a sentence saying "87.78
    EPV against Grips of Silent Justice 101.88" hands over the name with "EPV
    against " still attached. Dropping leading words until the tab recognises
    what is left is what lets an unresolved name MEAN something: it then means
    the figure is quoted for an item this spec's tab does not carry.
    """
    words = name.strip().split()
    for start in range(len(words)):
        candidate = " ".join(words[start:])
        if candidate in table:
            return candidate, table[candidate]
    return name.strip(), set()


def check_contested(captures: Path, items_csv: Path, workbook: Path,
                    tab_of: dict[str, str], arithmetic: dict) -> tuple[
                        int, list[str]]:
    """Every contested-token sentence, as the card would print it.

    THIS IS THE HOLE THIS CHECK EXISTS TO CLOSE. The sentences live in
    tools/extract_hit_captures.py rather than in a fact file, so nothing read
    them back, and a claim RETRACTED in token-arithmetic.yaml kept printing on a
    card for five days: the Arms Warrior said the head token cost a Destroyer
    four-piece against a capture holding two Destroyer pieces.

    WHAT EACH HALF OF A SENTENCE RESTS ON. Every piece count, slot and item name
    is now filled from the spec's own capture, so it cannot drift from the set
    it describes, and `just check` regenerates hit-captured.yaml and diffs it, so
    a hand edit cannot survive either. What CANNOT be derived is an EP figure,
    because a capture records gear and not item value. So the figures are
    checked here, on the rendered sentence, against the spec's own workbook tab.
    """
    problems: list[str] = []
    reproduced = 0

    tier_ids = {
        int(row["item_id"]) for row in csv.DictReader(items_csv.open())
        if row.get("set_name") and row.get("source") == "tier_vendor"}

    captured = {}
    for path in sorted(captures.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        if isinstance(data, dict) and "anchors" in data:
            captured[data.get("spec")] = (path, data)

    for spec, template in sorted(TOKEN_CONFIGURATION_CONTESTED.items()):
        if spec not in arithmetic:
            problems.append(
                f"{spec} prints a contested sentence and {TOKENS} records no "
                "token arithmetic for it")
        if spec not in captured:
            problems.append(
                f"{spec} prints a contested sentence and {captures} holds no "
                "capture for it")
            continue
        path, data = captured[spec]
        sentence = fill_contested(
            template, data, lambda item_id: (
                isinstance(item_id, int) and item_id in tier_ids))
        # A placeholder filled from a slot the capture does not hold renders as
        # `None`, which would print on a card as a sentence about an item named
        # None. It is a missing fact, not a wording problem.
        if "None" in sentence:
            problems.append(
                f"{spec} renders {sentence!r} from {path}, which names no item "
                "for a slot the sentence describes")
        tab = tab_of.get(spec)
        table = scores(workbook / tab) if tab else {}
        if not table:
            problems.append(f"{spec} maps to no readable workbook tab")
            continue
        for name, number in PAIR.findall(sentence):
            resolved, found = resolve(name, table)
            quoted = round(float(number), 2)
            if not found:
                problems.append(
                    f"{spec} quotes {quoted} for {resolved!r} in its contested "
                    f"sentence and {tab} carries no such item")
            elif any(abs(quoted - value) < TOLERANCE for value in found):
                reproduced += 1
            else:
                problems.append(
                    f"{spec} quotes {quoted} for {resolved!r} in its contested "
                    f"sentence and {tab} carries {sorted(found)}")
    return reproduced, problems


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

    in_sentences, contested = check_contested(
        CAPTURES, ITEMS, args.workbook, tab_of, specs)

    print(f"{len(specs)} spec(s) checked against {args.workbook}")
    print(f"  {reproduced} figure(s) reproduce on the spec's own tab")
    print(f"  {len(TOKEN_CONFIGURATION_CONTESTED)} contested sentence(s) "
          f"rendered, {in_sentences} figure(s) in them reproduce")
    for line in unresolved:
        print(f"  unverifiable: {line}")

    if contested:
        print(f"\n{len(contested)} problem(s) in the contested sentences "
              "tools/extract_hit_captures.py prints:", file=sys.stderr)
        for line in contested:
            print(f"  {line}", file=sys.stderr)
        print("\nThese sentences print on a claimant card. Correct the "
              "template, or delete a sentence that cannot be checked.",
              file=sys.stderr)
        return 1

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
