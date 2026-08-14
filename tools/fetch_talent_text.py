#!/usr/bin/env python3
"""Capture what each stat-to-spell-power talent says, rank by rank.

WHY THESE TALENTS AND NOT THE TREES. `data/facts/talents.yaml` records only the
talents supplying hit, expertise and defense skill, because those were the caps
the project needed. So when a caster card was asked to convert intellect, the
only rate available was intellect to spell CRIT, and the far larger effect,
intellect to spell POWER through a talent, existed nowhere in this repository.
The guild lead asked for talent awareness on 13 August 2026. This is its input.

TWO KINDS ARE CAPTURED and they are not the same thing.

  A CONVERSION turns one stat into spell damage and healing at a stated rate.
  Five exist in 2.4.3: Lunar Guidance, Holy Guidance, Spiritual Guidance,
  Nature's Blessing and Mind Mastery. These are what a delta card needs.

  A MULTIPLIER raises the stat itself and converts nothing: Arcane Mind, Divine
  Intellect, Living Spirit. They are captured beside the conversions because a
  reader pricing intellect for an Arcane Mage needs both, and because leaving
  them out would invite someone to apply a conversion to an unmultiplied stat.

THE IDS COME FROM THE VENDORED TREES, NOT FROM MEMORY. Every rank id is read
from `ui/core/talents/trees/<class>.json` in the wowsims checkout, the same
source the item database comes from, and the fetched name is checked against the
name that file gives. A talent named by hand is a talent dispositioned on its
name, which this project has done four times.

WHAT IS NOT CAPTURED. The percentages themselves are not transcribed here.
Wowhead states them in the tooltip text, this file stores that text verbatim,
and `tools/extract_talent_rates.py` reads the figure out of it. A number typed
between the two would be a third version of the same fact.

Usage:
    python3 tools/fetch_talent_text.py --out data/research/wowhead-talents
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import yaml

ENDPOINT = "https://nether.wowhead.com/tbc/tooltip/spell/{id}"

WOWSIMS = Path(os.environ.get(
    "WOWSIMS_TBC",
    "../tbc-phase-research-recovered/data/raw/vendor/wowsims-tbc-new-master"))

# (class file, tree name, talent fancyName, kind). The tree and the name
# together identify one talent; the ids are read from the tree file.
WANTED = [
    ("druid", "Balance", "Lunar Guidance", "conversion"),
    ("paladin", "Holy", "Holy Guidance", "conversion"),
    ("priest", "Holy", "Spiritual Guidance", "conversion"),
    ("shaman", "Restoration", "Nature's Blessing", "conversion"),
    ("mage", "Arcane", "Mind Mastery", "conversion"),
    ("mage", "Arcane", "Arcane Mind", "multiplier"),
    ("paladin", "Holy", "Divine Intellect", "multiplier"),
    ("druid", "Restoration", "Living Spirit", "multiplier"),
]


def tree_talents(klass: str) -> dict[tuple[str, str], dict]:
    path = WOWSIMS / "ui/core/talents/trees" / f"{klass}.json"
    if not path.is_file():
        raise SystemExit(
            f"fetch_talent_text.py: cannot read {path}. Set WOWSIMS_TBC to the "
            "wowsims checkout.")
    out = {}
    for tree in json.loads(path.read_text()):
        for talent in tree["talents"]:
            out[(tree["name"], talent["fancyName"])] = talent
    return out


def fetch(spell_id: int) -> dict:
    req = urllib.request.Request(
        ENDPOINT.format(id=spell_id),
        headers={"User-Agent": "tbc-p3-loot-research/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path,
                    default=Path("data/research/wowhead-talents"))
    args = ap.parse_args()

    today = str(date.today())
    into = args.out / today
    into.mkdir(parents=True, exist_ok=True)

    trees: dict[str, dict] = {}
    captured, failed = [], []
    for klass, tree, name, kind in WANTED:
        trees.setdefault(klass, tree_talents(klass))
        talent = trees[klass].get((tree, name))
        if talent is None:
            failed.append(f"{klass}/{tree}/{name}: not in the vendored tree")
            continue
        for rank, spell_id in enumerate(talent["spellIds"], start=1):
            path = into / f"spell-{spell_id}.json"
            if path.exists():
                captured.append({"spell_id": spell_id, "rank": rank,
                                 "talent": name, "file": path.name})
                continue
            try:
                payload = fetch(spell_id)
            except (urllib.error.HTTPError, urllib.error.URLError,
                    TimeoutError, json.JSONDecodeError) as exc:
                failed.append(f"{name} rank {rank} ({spell_id}): {exc}")
                continue
            # THE NAME IS CHECKED, for the same reason the item capture checks
            # it: an id typed or ordered wrongly still returns a real tooltip.
            if payload.get("name") and payload["name"] != name:
                failed.append(
                    f"{spell_id}: Wowhead calls it {payload['name']!r} and the "
                    f"vendored tree calls it {name!r}, so nothing is written")
                continue
            path.write_text(json.dumps(payload, indent=1, ensure_ascii=False)
                            + "\n")
            captured.append({"spell_id": spell_id, "rank": rank,
                             "talent": name, "class": klass, "tree": tree,
                             "kind": kind, "file": path.name})
            print(f"  {name} rank {rank}: {spell_id}", file=sys.stderr)
            time.sleep(1)

    doc = {
        "meta": {
            "captured": today,
            "source": ENDPOINT,
            "ids_from": "wowsims ui/core/talents/trees/<class>.json",
            "what": ("The tooltip text of every rank of the talents that turn "
                     "a stat into spell damage and healing, and of the talents "
                     "that raise those stats."),
            "ranks": len(captured),
        },
        "captures": captured,
    }
    if failed:
        doc["meta"]["not_resolved"] = failed
    (into / "manifest.yaml").write_text(
        yaml.safe_dump(doc, sort_keys=False, width=88, allow_unicode=True))
    print(f"{len(captured)} rank(s) captured, {len(failed)} failed -> {into}")
    for line in failed:
        print(f"  {line}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
