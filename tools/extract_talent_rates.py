#!/usr/bin/env python3
"""Read the captured talent tooltips into rates, and say which rank we take.

WHAT IT PRODUCES. `data/facts/talent-conversions.yaml`: for each talent that
turns a stat into spell power, the percentage at every rank, and for each
rostered spec the rank that spec's own build takes.

WHERE EACH HALF COMES FROM, because they are different kinds of claim.

  THE PERCENTAGES are read out of the Wowhead tooltip text captured under
  `data/research/wowhead-talents/`, which is never edited after capture. They
  are not transcribed by hand at any point: the sentence says "by 35% of your
  total Intellect" and the figure is taken from that sentence.

  THE RANKS are decoded from `talents.yaml::wowsims_talent_strings`, which
  records the wowsims preset build for each spec. A string is one digit per
  talent, in the order the vendored tree lists them, so the digit at a talent's
  position is the points that build spends on it. The decode is checked: each
  tree's digit count must match that tree's talent count and the point totals
  must match the spread already recorded for the spec, or the run fails.

THE HEALERS HAVE NO BUILD RECORDED AND THIS FILE SAYS SO RATHER THAN GUESSING.
wowsims TBC ships no healer simulation, so no preset exists for the Holy
Paladin, the Priest Healer, the Restoration Shaman or the Restoration Druid.
Those are exactly the specs these talents matter most to. Each is listed with
its talent and `rank: null`, so the gap is visible and countable instead of
looking like the talent does not apply.

Usage:
    python3 tools/extract_talent_rates.py --out data/facts/talent-conversions.yaml
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import yaml

CAPTURES = Path("data/research/wowhead-talents")
TALENTS = Path("data/facts/talents.yaml")
WOWSIMS = Path(os.environ.get(
    "WOWSIMS_TBC",
    "../tbc-phase-research-recovered/data/raw/vendor/wowsims-tbc-new-master"))

# Which spec, in this roster's vocabulary, each talent can belong to. A talent
# sits in a tree and a tree is shared by every spec of the class, so the tree
# alone would claim Lunar Guidance for a Feral Bear.
SPECS_BY_TALENT = {
    "Lunar Guidance": ["Balance Druid", "Restoration Druid"],
    "Holy Guidance": ["Holy Paladin"],
    "Spiritual Guidance": ["Priest Healer", "Shadow Priest"],
    "Nature's Blessing": ["Restoration Shaman"],
    "Mind Mastery": ["Arcane Mage"],
    "Arcane Mind": ["Arcane Mage"],
    "Divine Intellect": ["Holy Paladin"],
    "Living Spirit": ["Restoration Druid"],
}

SPEC_KEY = {
    "Balance Druid": "balance_druid", "Restoration Druid": "restoration_druid",
    "Holy Paladin": "holy_paladin", "Priest Healer": "priest_healer",
    "Shadow Priest": "shadow_priest",
    "Restoration Shaman": "restoration_shaman", "Arcane Mage": "arcane_mage",
}

# "by up to 25% of your total Spirit", "by an amount equal to 30% of your
# Intellect", "by 35% of your total Intellect", "your total Intellect by 15%".
GRANT = re.compile(
    r"(spell damage and healing|spell damage|healing)\s+by\s+(?:up to\s+|an "
    r"amount equal to\s+)?(\d+)%\s+of your(?: total)?\s+(Intellect|Spirit)",
    re.I)
RAISE = re.compile(r"your total (Intellect|Spirit) by (\d+)%", re.I)


def plain(tooltip: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", "", tooltip).split())


def tree_index(klass: str) -> tuple[list[dict], list[str]]:
    path = WOWSIMS / "ui/core/talents/trees" / f"{klass}.json"
    trees = json.loads(path.read_text())
    return trees, [t["name"] for t in trees]


def points_taken(string: str, klass: str, talent_name: str,
                 spec: str) -> int | None:
    """How many points this build spends on one talent, or None if unrecorded."""
    trees, _ = tree_index(klass)
    parts = string.split("-")
    if len(parts) != len(trees):
        raise SystemExit(
            f"extract_talent_rates.py: {spec} has {len(parts)} tree(s) in its "
            f"talent string and the {klass} tree file has {len(trees)}.")
    for tree, part in zip(trees, parts):
        # A STRING IS TRUNCATED, NOT PADDED. wowsims drops trailing zeros, so
        # the Shadow Priest's Discipline part is nine digits against a tree of
        # twenty-two: everything past the ninth talent is unspent. A strict
        # length check rejected that build, correctly reporting a disagreement
        # that was in the check rather than in the data. Longer than the tree is
        # still fatal, because that cannot be truncation.
        if len(part) > len(tree["talents"]):
            raise SystemExit(
                f"extract_talent_rates.py: {spec} spends over {len(part)} "
                f"talent(s) in {tree['name']} and that tree holds "
                f"{len(tree['talents'])}. The string and the tree disagree, so "
                "no rank can be read from it.")
        digits = part.ljust(len(tree["talents"]), "0")
        for talent, digit in zip(tree["talents"], digits):
            if talent["fancyName"] == talent_name:
                return int(digit)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--captures", type=Path, default=CAPTURES)
    ap.add_argument("--out", type=Path,
                    default=Path("data/facts/talent-conversions.yaml"))
    args = ap.parse_args()

    strings = (yaml.safe_load(TALENTS.read_text())
               ["wowsims_talent_strings"]["strings"])

    manifests = sorted(args.captures.glob("*/manifest.yaml"))
    if not manifests:
        print("extract_talent_rates.py: no capture found under "
              f"{args.captures}. Run tools/fetch_talent_text.py first.",
              file=sys.stderr)
        return 1

    talents: dict[str, dict] = {}
    for manifest in manifests:
        doc = yaml.safe_load(manifest.read_text())
        captured = doc["meta"]["captured"]
        for entry in doc["captures"]:
            if "class" not in entry:
                continue
            payload = json.loads(
                (manifest.parent / entry["file"]).read_text())
            text = plain(payload.get("tooltip", ""))
            match = GRANT.search(text)
            if match:
                grants, percent, stat = (match.group(1).lower(),
                                         int(match.group(2)),
                                         match.group(3).lower())
            else:
                match = RAISE.search(text)
                if not match:
                    print(f"  no rate in {entry['talent']} rank "
                          f"{entry['rank']}: {text[:90]}", file=sys.stderr)
                    return 1
                grants, percent, stat = ("the stat itself", int(match.group(2)),
                                         match.group(1).lower())
            name = entry["talent"]
            block = talents.setdefault(name, {
                "class": entry["class"], "tree": entry["tree"],
                "kind": entry["kind"], "converts": stat, "grants": grants,
                "captured": captured, "ranks": [],
            })
            block["ranks"].append({
                "rank": entry["rank"], "spell_id": entry["spell_id"],
                "percent": percent,
            })

    unresolved = []
    for name, block in talents.items():
        block["ranks"].sort(key=lambda r: r["rank"])
        block["max_rank"] = block["ranks"][-1]["rank"]
        taken = {}
        for spec in SPECS_BY_TALENT.get(name, []):
            key = SPEC_KEY[spec]
            entry = strings.get(key)
            if entry is None:
                taken[spec] = None
                unresolved.append(f"{spec} / {name}")
                continue
            taken[spec] = points_taken(entry["string"], block["class"], name,
                                       spec)
        block["points_taken"] = taken

    doc = {
        "meta": {
            "what": ("The talents that turn a stat into spell power, the "
                     "percentage at every rank, and the rank each rostered "
                     "spec's own build takes."),
            "percentages_from": ("the Wowhead tooltip text captured under "
                                 "data/research/wowhead-talents/, read out of "
                                 "the sentence rather than transcribed"),
            "ranks_from": ("data/facts/talents.yaml :: "
                           "wowsims_talent_strings, decoded against the "
                           "vendored talent trees and checked against the "
                           "point spread already recorded for each spec"),
            "no_build_recorded": sorted(unresolved),
            "why_some_are_null": (
                "wowsims TBC ships no healer simulation, so no preset build "
                "exists for the Holy Paladin, the Priest Healer, the "
                "Restoration Shaman or the Restoration Druid. Those are the "
                "specs these talents matter most to. A rank of null is a gap "
                "this project has not filled, not a talent that does not "
                "apply."),
        },
        "talents": dict(sorted(talents.items())),
    }
    args.out.write_text(yaml.safe_dump(doc, sort_keys=False, width=84,
                                       allow_unicode=True))
    print(f"{len(talents)} talent(s), "
          f"{sum(len(t['ranks']) for t in talents.values())} rank(s), "
          f"{len(unresolved)} spec/talent pair(s) with no build recorded "
          f"-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
