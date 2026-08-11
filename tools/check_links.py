#!/usr/bin/env python3
"""Validate internal references across the compendium.

Three checks, each earned by a failure this repository actually had.

1.  **Links and anchors.** Checking that a target file exists is not enough.
    A link to `framework.md#fixed-assumptions` is broken if the heading is
    renamed, and a file-only check passes it silently.

2.  **Retired vocabulary.** Deleting a concept reliably leaves its name behind
    in prose, where no link checker can see it. It has happened on every strip
    so far: the tank engine, the L0 to L3 layer model, the weights layer, the
    exception list, the audit tier, and more. Each named something with no
    definition left anywhere. The terms are therefore listed explicitly, with
    what replaced them, and a term returns to the docs only alongside a
    definition, at which point it comes off the list in the same commit.

3.  **Cross-file pointers out of the fact files.** A note in `hit.yaml` read
    "See the framework's tank engine" and pointed at nothing. A prose pointer
    cannot be resolved, so fact files must cite an explicit path such as
    `docs/framework.md#cap-state-and-stat-valuation`, which this then verifies.

Heading identifiers follow pandoc's `auto_identifiers` rule: lowercase, drop
anything that is not a letter, digit, hyphen, underscore, or space, then
replace spaces with hyphens.

Usage:
    python3 tools/check_links.py [ROOT]      # ROOT defaults to the repo root
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")
EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.IGNORECASE)

# An explicit path reference from anywhere: docs/framework.md#some-anchor
PATH_REF = re.compile(r"\b(docs/[\w./-]+\.md)(?:#([\w-]+))?")

# A prose pointer at a document, which cannot be resolved and so is banned.
VAGUE_REF = re.compile(
    r"\bsee\s+(?:the\s+)?(?:framework|conventions|overview|index|compendium)(?:'s)?\b",
    re.IGNORECASE,
)

# Concepts deleted from the project. Each entry is the term and what replaced it.
# A term returns to the docs only alongside a definition, at which point it comes
# off this list in the same commit.
RETIRED = {
    r"\btank engine\b":
        "the tank valuation model was removed; state the threshold facts directly",
    r"\bweights layer\b":
        "the layer model was removed; say what actually consumes the input",
    r"\bL[0-3]\b":
        "the L0 to L3 layer model was removed and was never defined in the docs",
    r"\bMV\(":
        "the MV scoring formula was removed; no scoring formula is fixed yet",
    r"\bseat\b(?!\s*belt)":
        "seats were reverted; the unit of analysis is the spec",
    r"\bexception list\b":
        "belonged to the MV scoring rule, which was removed",
    r"\barbitration question":
        "the arbitration ladder was removed; cross-role contests are not ordered by number",
    r"\bconflict ledger\b":
        "removed; disagreeing sources are recorded with their provenance instead",
    r"\baudit tier\b":
        "the three-tier page model was removed; name the file or page directly",
    r"\bstated position\b":
        "a second word for priority; use priority, which conventions.md defines",
    r"\bcatalog(ue)? specification\b":
        "no such document exists",
    r"\bdisagreement ledger\b":
        "removed; disagreeing sources are recorded with their provenance instead",
    r"\bnumber fence\b":
        "removed along with the gain percentage machinery",
    r"\bgain_pct\b|\bgain percentage\b":
        "removed; no derived score is published",
    r"\bmarginal value\b":
        "removed with the MV scoring rule",
    # Renamed on 9 August 2026. One term, not two: a reader who meets `band` on
    # one page and `priority` on the next has to work out that they are the same
    # thing, and the shorthand `P1` said nothing to anyone who had not read the
    # definition. `Bands` as an item name, the wrist pieces, is not this term and
    # lives in tokens.yaml, which this check does not scan for it.
}

# Retired terms that are also ordinary words somewhere in the data. `Band` is a
# wrist piece and a ring in the item tables, `Band of the Ranger General` among
# them, so scanning a CSV of item names for it reports the game's vocabulary as
# our own. These rules run over prose only.
RETIRED_IN_PROSE = {
    r"\bbands?\b":
        "renamed to priority; write priority, and Priority 1 rather than P1",
    r"\bP[0-3]\b":
        "the shorthand was retired; write Priority 0 through Priority 3 in full",
}
PROSE_SUFFIXES = {".md"}

# An item reference and an inline code span are not our prose. `Insidious
# Bands`, `Band of the Ranger-General` and `Bands of the Celestial Archer` are
# the game's names for wrist and finger pieces, and reading them as our retired
# word reported 37 problems the moment one page per item existed. The names are
# masked before any retired term is looked for, which is the same reason the
# style checker ignores fenced and inline code.
ITEM_REF = re.compile(r"\[[^\]]*\]\{\.item[^}]*\}")
INLINE_CODE = re.compile(r"`[^`]*`")


def prose_only(line: str) -> str:
    """One line with the parts that are not our own words removed."""
    line = ITEM_REF.sub(" ", line)
    return INLINE_CODE.sub(" ", line)

SCAN_SUFFIXES = {".md", ".yaml", ".yml", ".csv", ".py"}
SKIP_DIRS = {".git", "site", "vendor", "node_modules", "__pycache__", "scratch",
             "research", "data/derived"}
# This file names every retired term in order to detect them.
SKIP_FILES = {"tools/check_links.py"}


def slug(text: str) -> str:
    """Pandoc auto_identifier for a heading."""
    text = re.sub(r"`([^`]*)`", r"\1", text)              # inline code
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # links
    text = re.sub(r"[*_]", "", text)                      # emphasis
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = text.strip().replace(" ", "-")
    text = re.sub(r"-+", "-", text)
    return text.lstrip("-")


def headings(path: Path) -> set[str]:
    ids: set[str] = set()
    in_fence = False
    for line in path.read_text().splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING.match(line)
        if m:
            ids.add(slug(m.group(2)))
    return ids


def markdown_links(path: Path) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    in_fence = False
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in LINK.finditer(line):
            found.append((n, m.group(1)))
    return found


def scan_files(root: Path) -> list[Path]:
    out = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix not in SCAN_SUFFIXES:
            continue
        rel = p.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if str(rel) in SKIP_FILES:
            continue
        out.append(p)
    return out


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    files = scan_files(root)
    docs = [p for p in files if p.suffix == ".md"]
    if not docs:
        print(f"no markdown files under {root}")
        return 0

    cache: dict[Path, set[str]] = {}
    problems: list[str] = []
    checked = 0

    def anchors_of(dest: Path) -> set[str]:
        if dest not in cache:
            cache[dest] = headings(dest)
        return cache[dest]

    def rel(p: Path) -> str:
        return str(p.relative_to(root))

    # 1. Markdown links and anchors.
    for path in docs:
        for line_no, target in markdown_links(path):
            if EXTERNAL.match(target):
                continue
            checked += 1
            file_part, _, anchor = target.partition("#")
            if file_part:
                dest = (path.parent / file_part).resolve()
                if not dest.exists():
                    problems.append(f"{rel(path)}:{line_no}  missing file: {target}")
                    continue
            else:
                dest = path.resolve()
            if anchor and anchor not in anchors_of(dest):
                problems.append(f"{rel(path)}:{line_no}  missing anchor: {target}")

    # 2 and 3. Retired vocabulary, explicit path refs, and vague pointers.
    for path in files:
        lines = path.read_text().splitlines()
        # A document's YAML frontmatter is metadata rather than prose, and on a
        # generated item page the title IS the item's name. `Insidious Bands`
        # is a wrist piece, not our retired word.
        body_from = 0
        if path.suffix == ".md" and lines and lines[0].strip() == "---":
            for n, line in enumerate(lines[1:], 2):
                if line.strip() == "---":
                    body_from = n
                    break
        # A GENERATED PAGE IS NOT OUR PROSE. Its words are item names, spec
        # names and structure, and the retired-word rules exist to catch our own
        # vocabulary lingering in text a person wrote. A boss index linking to
        # `Band of Devastation` and `Insidious Bands` is the game's vocabulary
        # in a link, and no masking rule short of ignoring link text can tell
        # the two apart. The file says it is generated, so it is taken at its
        # word; the rules that catch a genuine defect still run over it.
        written_by_hand = "GENERATED BY tools/" not in "\n".join(lines[:12])
        for n, line in enumerate(lines, 1):
            if n <= body_from:
                continue
            rules = dict(RETIRED)
            if path.suffix in PROSE_SUFFIXES and written_by_hand:
                rules.update(RETIRED_IN_PROSE)
            ours = prose_only(line)
            for pattern, why in rules.items():
                found = re.search(pattern, ours, re.IGNORECASE)
                if found:
                    problems.append(
                        f"{rel(path)}:{n}  retired term {found.group(0)!r}: {why}")

            for m in PATH_REF.finditer(line):
                checked += 1
                dest = (root / m.group(1)).resolve()
                if not dest.exists():
                    problems.append(f"{rel(path)}:{n}  missing file: {m.group(1)}")
                elif m.group(2) and m.group(2) not in anchors_of(dest):
                    problems.append(
                        f"{rel(path)}:{n}  missing anchor: {m.group(1)}#{m.group(2)}")

            if path.suffix in {".yaml", ".yml", ".csv"} and VAGUE_REF.search(line):
                problems.append(
                    f"{rel(path)}:{n}  prose pointer at a document. Cite an explicit "
                    f"path such as docs/framework.md#anchor so it can be verified")

    # 4. Every fact file is documented in its provenance.
    facts = root / "data" / "facts"
    prov = facts / "PROVENANCE.md"
    if facts.is_dir() and prov.exists():
        text = prov.read_text()
        for entry in sorted(facts.iterdir()):
            if entry.name == "PROVENANCE.md" or not entry.is_file():
                continue
            checked += 1
            if f"`{entry.name}`" not in text:
                problems.append(
                    f"data/facts/PROVENANCE.md  undocumented fact file: {entry.name}. "
                    f"Every file in data/facts must appear in the inventory")

    # A markdown link often repeats its path in the link text, and the path
    # scan sees both. Same file, same line, same complaint is one problem.
    problems = list(dict.fromkeys(problems))

    print(f"checked {checked} reference(s) across {len(files)} file(s)")
    if problems:
        print()
        for p in problems:
            print(f"  {p}")
        print(f"\n{len(problems)} problem(s)")
        return 1
    print("all references resolve, and no retired vocabulary is present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
