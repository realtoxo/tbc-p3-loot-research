#!/usr/bin/env python3
"""Validate every Wowhead id this repository links to, and the name it claims.

The internal checker proves a link points at a heading that exists. It says
nothing about the 585 Wowhead ids in the docs and fact files, and a wrong id is
the most damaging error this project can publish: it looks authoritative, it
resolves to a real page, and it describes the wrong item. That has already
happened once here, where item 31101 was recorded as the Vanquisher helm when it
is Pauldrons of the Forgotten Conqueror, a different slot and a different token
line.

So this does two things. It confirms each id resolves, and where the repository
also states a name for that id, it confirms the name matches.

`www.wowhead.com` returns a redirect to a slugged URL and is served through a
CDN that blocks automated clients unpredictably. Ids are therefore resolved at
`nether.wowhead.com/tbc/tooltip/...`, which returns JSON from the 2.4.3 data
environment and is the same source the fact files were built from.

Usage:
    python3 tools/check_external_links.py            # every id
    python3 tools/check_external_links.py --limit 40 # a sample, for a quick pass
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

LINK = re.compile(r"wowhead\.com/tbc/(item|item-set)=(\d+)")
ENDPOINT = "https://nether.wowhead.com/tbc/tooltip/{kind}/{id}"
SCAN = ["docs/*.md", "data/facts/*", "*.md"]


def collect(root: Path) -> dict[tuple[str, str], set[str]]:
    """Map (kind, id) to the files that reference it."""
    found: dict[tuple[str, str], set[str]] = {}
    for pattern in SCAN:
        for path in sorted(root.glob(pattern)):
            if path.is_dir():
                continue
            try:
                text = path.read_text()
            except (UnicodeDecodeError, OSError):
                continue
            for kind, item_id in LINK.findall(text):
                found.setdefault((kind, item_id), set()).add(path.name)
    return found


def claimed_names(root: Path) -> dict[str, str]:
    """Names the repository asserts for an item id, from the generated tables."""
    names: dict[str, str] = {}
    for name_file, id_col, name_col in [
        ("data/facts/items.csv", "item_id", "name"),
        ("data/facts/drops.csv", "item_id", "item_name"),
    ]:
        path = root / name_file
        if not path.exists():
            continue
        with path.open() as fh:
            for row in csv.DictReader(fh):
                if row.get(id_col) and row.get(name_col):
                    names[row[id_col]] = row[name_col]
    return names


def resolve(kind: str, item_id: str) -> tuple[str, str | None, str | None]:
    """Return (id, name, error)."""
    url = ENDPOINT.format(kind=kind, id=item_id)
    req = urllib.request.Request(url, headers={"User-Agent": "tbc-p3-loot-research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return item_id, None, f"HTTP {exc.code}"
    except Exception as exc:  # network, timeout, malformed JSON
        return item_id, None, type(exc).__name__
    name = payload.get("name")
    if not name:
        return item_id, None, "resolved but has no name"
    return item_id, name, None


def normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--limit", type=int, default=0, help="check only the first N ids")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    root = args.root.resolve()
    refs = collect(root)
    names = claimed_names(root)
    targets = sorted(refs)
    if args.limit:
        targets = targets[: args.limit]

    print(f"resolving {len(targets)} unique Wowhead id(s) referenced by this repository")

    problems: list[str] = []
    mismatches: list[str] = []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = pool.map(lambda t: (t, resolve(*t)), targets)
        for (kind, item_id), (_, name, error) in results:
            where = ", ".join(sorted(refs[(kind, item_id)]))
            if error:
                problems.append(f"{kind}={item_id}  {error}  (in {where})")
                continue
            claimed = names.get(item_id) if kind == "item" else None
            if claimed and normalise(claimed) != normalise(name):
                mismatches.append(
                    f"{kind}={item_id}  we say {claimed!r}, Wowhead says {name!r}  (in {where})")

    if problems:
        print(f"\n{len(problems)} id(s) did not resolve:")
        for line in problems:
            print(f"  {line}")
    if mismatches:
        print(f"\n{len(mismatches)} id(s) resolve to a different item than we claim:")
        for line in mismatches:
            print(f"  {line}")

    if not problems and not mismatches:
        print(f"every id resolves, and every name we assert matches the source")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
