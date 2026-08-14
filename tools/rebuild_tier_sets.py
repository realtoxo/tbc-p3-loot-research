#!/usr/bin/env python3
"""Rebuild every capture's tier set as the entry set plus the tokens Phase 3 wears.

WHAT A TIER SET IS, RULED BY THE GUILD LEAD ON 13 AUGUST 2026. It is the entry
set with only the five token slots reconsidered, one at a time:

  1. If the spec's Wowhead Phase 3 best-in-slot list puts a TIER TOKEN PIECE in
     that slot, from ANY tier, take it.
  2. Otherwise keep whatever the entry set has there, UNLESS that entry item is
     itself a tier piece whose set bonus no longer holds in the finished set, in
     which case take the best available off-piece instead.

The other twelve slots are never touched. A tier set therefore never picks up a
Phase 3 OFF-piece, and the number of tier pieces varies by spec rather than
being five everywhere.

RULE 1 NEEDED "ANY TIER" AND THAT CLAUSE IS LOAD-BEARING. The Arcane Mage's
Phase 3 list keeps the Tier 5 Tirisfal four-piece and takes only the Tier 6
legs. A Tier-6-only rule would have stripped four correct pieces off that spec.

RULE 2 EXISTS BECAUSE OF THE WARLOCK. The guild lead found the Affliction
Warlock wearing Voidheart Mantle, a Tier 4 shoulder, at the tier anchor. It is
correct at ENTRY, where the warlock also wears Voidheart Gloves and the pair
carries the Tier 4 two-piece. At the tier anchor the gloves become Tier 6, the
pair breaks, and the shoulder is left holding nothing while ranking sixth in its
slot. An entry item is only kept if it still earns its place.

WHAT COUNTS AS A BONUS. Two pieces of one set. A tier piece sitting alone in its
set buys nothing, which is what makes it an orphan. Tier 6 has no one-piece
bonus at all, recorded in progression.yaml.

THE SOURCE IS RECORDED PER SPEC, with the URL and the date it was read, because
these lists are client-rendered and cannot be re-fetched by a transform.

Usage:
    python3 tools/rebuild_tier_sets.py --bis DIR [--apply]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

CAPTURES = Path("data/facts/sim-profiles/hit-capture")
ITEMS = Path("data/facts/items.csv")
LADDER = Path("theme/filters/ladder.generated.lua")
HIT = Path("data/facts/hit-captured.yaml")

# The five slots a token can fill, in the capture's own vocabulary keyed by the
# name the Wowhead guide uses for the same slot.
TOKEN_SLOTS = {"head": "head", "shoulder": "shoulder", "chest": "chest",
               "hand": "hands", "leg": "legs"}

# Which hit column on the item answers for a spec, by the cap hit-captured.yaml
# records. A spec capped on both takes the larger, because the capture records
# one figure per slot and the constraint block states each cap separately.
HIT_COLUMN = {"melee_special": ("melee_hit",), "ranged": ("melee_hit",),
              "spell": ("spell_hit",),
              "melee_special_and_spell": ("melee_hit", "spell_hit")}


def number(value: str) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def shortlist(ladder: str, spec: str, slot: str) -> list[tuple[str, str, float]]:
    """The workbook's ranked items for one spec and slot: id, name, EPV."""
    key = {"head": "Head", "shoulder": "Shoulders", "chest": "Chest",
           "hands": "Hands", "legs": "Legs"}[slot]
    start = ladder.find(f'["{spec.replace("_", " ")}"]')
    if start < 0:
        return []
    end = ladder.find('\n    ["', start + 10)
    block = ladder[start:end if end > 0 else len(ladder)]
    at = block.find(f'["{key}"]', block.find("by_slot = {"))
    if at < 0:
        return []
    stop = block.find('\n        ["', at + 14)
    seg = block[at:stop if stop > 0 else at + 3000]
    return [(m.group(1), m.group(2), float(m.group(3))) for m in re.finditer(
        r'item_id = (\d+),\s*name = "([^"]+)",.*?epv = ([\d.]+),', seg, re.S)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bis", type=Path, required=True)
    ap.add_argument("--captures", type=Path, default=CAPTURES)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    items = {r["item_id"]: r for r in csv.DictReader(ITEMS.open())}
    ladder = LADDER.read_text()
    caps = {k: v.get("cap") for k, v in
            yaml.safe_load(HIT.read_text())["specs"].items()}

    def is_tier(item_id: str) -> bool:
        row = items.get(str(item_id))
        return bool(row and row.get("set_name")
                    and row.get("source") == "tier_vendor")

    def hit_of(item_id: str, spec: str) -> int:
        row = items.get(str(item_id))
        if not row:
            return 0
        return max(number(row.get(c, 0))
                   for c in HIT_COLUMN.get(caps.get(spec, "spell"),
                                           ("spell_hit",)))

    changed, report = 0, []
    for path in sorted(args.captures.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text())
        spec = doc.get("spec") or path.stem.replace("-", "_")
        bis_file = args.bis / f"{spec}.json"
        if not bis_file.is_file():
            print(f"  {spec}: no Phase 3 list captured, left alone",
                  file=sys.stderr)
            continue
        bis = json.loads(bis_file.read_text())["slots"]
        entry = (doc["anchors"]["entry"].get("hit_by_slot") or {})

        # Start from the entry set. Every slot outside the five is carried
        # across untouched, which is the whole point of the rule.
        built = {slot: dict(row) for slot, row in entry.items()}
        moves, taken_by_rule_one = [], set()
        for bis_slot, slot in TOKEN_SLOTS.items():
            pick = bis.get(bis_slot)
            if not pick or not pick.get("id"):
                continue
            if not is_tier(pick["id"]):
                continue        # rule 2: an off-piece leaves the entry item
            row = items.get(str(pick["id"]))
            was = (built.get(slot) or {}).get("item", "nothing")
            built[slot] = {"item": row["name"] if row else pick["item"],
                           "id": int(pick["id"]),
                           "hit": hit_of(pick["id"], spec)}
            taken_by_rule_one.add(slot)
            if was != built[slot]["item"]:
                moves.append(f"{slot}: {was} -> {built[slot]['item']} (token)")

        # RULE 2's SECOND HALF. Any tier piece now alone in its set buys
        # nothing, so it is replaced by the best off-piece the workbook ranks
        # for that slot. Only the five token slots are eligible: a tier piece
        # cannot occupy any other.
        sets = Counter()
        for row in built.values():
            item = items.get(str(row.get("id")))
            if item and item.get("set_name"):
                sets[item["set_name"]] += 1
        for slot in TOKEN_SLOTS.values():
            # ONLY THE FALLBACK PATH IS TESTED. A token rule 1 took is what the
            # Phase 3 list chose ON PURPOSE, bonus or no bonus: the Arcane
            # Mage's list keeps the Tier 5 Tirisfal four-piece and adds the
            # Tier 6 legs alone, and the first version of this tool "orphaned"
            # those legs and threw them away. Rule 2 is about an entry item
            # that survived by default, not about a deliberate pick.
            if slot in taken_by_rule_one:
                continue
            row = built.get(slot)
            item = items.get(str((row or {}).get("id")))
            if not item or not item.get("set_name"):
                continue
            # AND ONLY A TIER PIECE. The guild lead's rule says "a tier piece
            # whose set bonus no longer holds". A crafted set is not a tier set:
            # the Balance Druid's Spellstrike Pants were being discarded for
            # holding no bonus, which is not what was asked and is not true of
            # a piece worn for its stats.
            if not is_tier(item["item_id"]):
                continue
            if sets[item["set_name"]] >= 2:
                continue
            options = [o for o in shortlist(ladder, spec, slot)
                       if not is_tier(o[0])]
            if not options:
                moves.append(f"{slot}: {item['name']} is an orphan and the "
                             "workbook ranks no off-piece, so it stays")
                continue
            best = options[0]
            sets[item["set_name"]] -= 1
            built[slot] = {"item": best[1], "id": int(best[0]),
                           "hit": hit_of(best[0], spec)}
            moves.append(f"{slot}: {item['name']} orphaned, no set bonus "
                         f"-> {best[1]} (best off-piece, EPV {best[2]})")

        # A TIER COLUMN IS A RAID, NOT A SET. `items.csv::tier` says which raid
        # tier an item drops in, so Leggings of Channeled Elements reads T6
        # while being an ordinary Black Temple off-piece. Counting on that alone
        # credited the Affliction Warlock with four Tier 6 pieces when its list
        # gives it three. Set membership is `source == tier_vendor`, and both
        # tests have to pass.
        tier6 = sorted(s for s in TOKEN_SLOTS.values()
                       if is_tier((built.get(s) or {}).get("id"))
                       and (items.get(str((built.get(s) or {}).get("id")))
                            or {}).get("tier") == "T6")
        total = sum(int(r.get("hit") or 0) for r in built.values())
        report.append((spec, len(tier6), total, moves))
        if args.apply:
            block = doc["anchors"].setdefault("tier_hands_and_head", {})
            block["hit_by_slot"] = built
            block["tier6_pieces_held"] = tier6
            block["total_item_hit"] = total
            block["rebuilt"] = (
                "Entry set with the token slots the Phase 3 best-in-slot list "
                "devotes to a tier piece, per the rule in "
                "tools/rebuild_tier_sets.py. Source: "
                + json.loads(bis_file.read_text()).get("url", "Wowhead Phase 3 "
                                                       "BiS, read 2026-08-13"))
            doc["anchors"].pop("tier_hands_only", None)
            path.write_text(yaml.safe_dump(doc, sort_keys=False, width=88,
                                           allow_unicode=True))
            changed += 1

    for spec, n, total, moves in report:
        print(f"  {spec:<22} {n} Tier 6 piece(s), {total} item hit")
        for line in moves:
            print(f"      {line}")
    print(f"\n{len(report)} spec(s) computed"
          + (f", {changed} written" if args.apply else ", nothing written"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
