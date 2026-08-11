#!/usr/bin/env python3
"""Enforce the house writing style documented in docs/kb/DEVELOPING.md.

The style rules were extracted from the prior repositories in this series by
measuring them: across 24 documents there were zero contractions, zero em
dashes, and zero uses of "probably" or "might". Uncertainty was always a named
condition. Those are mechanical properties, so they are checked mechanically
rather than remembered.

Usage:
    python3 tools/check_style.py            # check docs/ and evidence/
    python3 tools/check_style.py PATH ...   # check specific files or trees
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TARGETS = ["docs", "evidence", "research", "data", "README.md", "AGENTS.md"]


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern
    message: str


RULES = [
    Rule(
        "em-dash",
        re.compile(r"[—–]"),
        "em or en dash; use a comma, semicolon, or full stop",
    ),
    Rule(
        "contraction",
        # Apostrophe forms that are contractions. Possessives and in-game names
        # such as G'eras or Naj'entus are deliberately not matched.
        re.compile(
            r"\b(?:do|does|did|is|are|was|were|has|have|had|would|should|could|will|can|must)n[''`]t\b"
            r"|\b(?:it|that|there|here|what|who|he|she|let)[''`]s\b"
            r"|\b(?:I|you|we|they|it|he|she|that|there)[''`](?:re|ve|ll|d|m)\b",
            re.IGNORECASE,
        ),
        "contraction; write it out",
    ),
    Rule(
        "vague-hedge",
        re.compile(r"\b(probably|might|maybe|perhaps|sort of|kind of)\b", re.IGNORECASE),
        "vague hedge; name the condition the uncertainty depends on",
    ),
]

# Regions where prose rules do not apply.
FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`[^`]*`")
URL = re.compile(r"<https?://\S+>|\]\([^)]*\)|https?://\S+")


def scrub(line: str) -> str:
    """Blank out inline code and URLs so their contents are not linted."""
    line = INLINE_CODE.sub(lambda m: " " * len(m.group()), line)
    line = URL.sub(lambda m: " " * len(m.group()), line)
    return line


def check_file(path: Path) -> list[tuple[int, str, str, str]]:
    findings: list[tuple[int, str, str, str]] = []
    in_fence = False
    in_front_matter = False
    for n, raw in enumerate(path.read_text().splitlines(), 1):
        if n == 1 and raw.strip() == "---":
            in_front_matter = True
            continue
        if in_front_matter:
            if raw.strip() == "---":
                in_front_matter = False
            # Front matter is prose too, so it is still checked below.
        if FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # Block quotations reproduce someone else's words. Editing them to
        # satisfy our style would misquote the source.
        if raw.lstrip().startswith(">"):
            continue
        line = scrub(raw)
        for rule in RULES:
            for m in rule.pattern.finditer(line):
                findings.append((n, rule.name, m.group().strip(), rule.message))
    return findings


def collect(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for t in targets:
        p = Path(t)
        if p.is_dir():
            files.extend(sorted(p.rglob("*.md")))
        elif p.is_file():
            files.append(p)
    return files


def main() -> int:
    targets = sys.argv[1:] or DEFAULT_TARGETS
    files = collect(targets)
    if not files:
        print("no markdown files found")
        return 0

    total = 0
    for path in files:
        findings = check_file(path)
        if not findings:
            continue
        total += len(findings)
        print(f"\n{path}")
        for line_no, rule, text, message in findings:
            print(f"  {line_no:>4}  {rule:<12} {text!r}: {message}")

    print(f"\nchecked {len(files)} file(s)")
    if total:
        print(f"{total} style violation(s)")
        return 1
    print("no style violations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
