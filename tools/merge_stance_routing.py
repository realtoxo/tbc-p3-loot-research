#!/usr/bin/env python3
"""Merge the routing pass into a fact file: who each remark sends an item to.

WHAT THIS ANSWERS, AND WHY THE OLD ANSWER WAS THE WRONG ONE. `creator-stances.
yaml` records a `stance` per remark, one of favours, against, conditional or
mentions_only, and a card printed that as "Speaks well of it" or "Argues against
it". The guild lead rejected the axis on 13 August 2026: "The item exists to
exist. It does not matter if they like it or not. Our influencer quotes should
focus on opinions about where the item should be placed."

He is right, and the fix is not a rename. Approval and routing are different
questions, and the stance answers only the first. The clearest case in the whole
set is Zatar on The Skull of Gul'dan: he speaks well of it throughout AND argues
the hit rating is wasted on three of the four casters who could take it. A
stance of `favours` with a spec list cannot say that. Direction can.

WHERE THE DIRECTION COMES FROM. A workflow of Sonnet subagents read all 579
remarks and split the specs each ALREADY NAMES into the ones it sends the item
to and the ones it sends it away from. The specs were not invented: every agent
was held to the strings already on the record, and a spec named only as a
comparison is in neither list, which is a correct and common answer.

WHY A SEPARATE FILE. `creator-stances.yaml` is the capture and is not
regenerable; PROVENANCE records it as an agent pass rather than a transform.
This is a second reading OF that capture, so it lives beside it rather than
inside it, and the capture stays the thing it was when it was made.

THE KEY IS NOT THE ROW NUMBER. Rows are keyed by item id, creator and timestamp,
the same triple `extract_commentary.py` already matches notes on, so reordering
or adding a remark cannot silently re-point a routing at the wrong claim.

Usage:
    python3 tools/merge_stance_routing.py --journal RUN_DIR/journal.jsonl ... \
        --out data/facts/creator-routing.yaml
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from datetime import date
from pathlib import Path

import yaml

STANCES = Path("data/facts/creator-stances.yaml")


# THE BATCH FILES WERE CANONICALIZED AND THE CAPTURE WAS NOT. The workflow was
# handed rostered spec names where one matched, so an agent echoing its input
# returns "Holy Paladin" where creator-stances.yaml holds "holy paladin". The
# check below compares the two, so it has to fold them the same way or it would
# reject every correct row for naming a spec the remark "did not list". Names
# with no rostered match, "feral druid" and bare "rogue" among them, pass
# through unchanged on both sides.
def canonical(name: str) -> str:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from extract_ladder import SPECS
    return {s.lower(): s for s in SPECS}.get(str(name).strip().lower(),
                                             str(name).strip())


def specs_of(value) -> list[str]:
    if isinstance(value, list):
        return [str(s) for s in value]
    if isinstance(value, str) and value.strip().startswith("["):
        try:
            return [str(s) for s in ast.literal_eval(value)]
        except (ValueError, SyntaxError):
            return []
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--journal", type=Path, nargs="+", required=True)
    ap.add_argument("--stances", type=Path, default=STANCES)
    ap.add_argument("--out", type=Path,
                    default=Path("data/facts/creator-routing.yaml"))
    args = ap.parse_args()

    remarks = yaml.safe_load(args.stances.read_text())["remarks"]

    routed: dict[int, dict] = {}
    for path in args.journal:
        for line in path.read_text().splitlines():
            entry = json.loads(line)
            if entry.get("type") != "result":
                continue
            result = entry.get("result")
            if not isinstance(result, dict):
                continue
            for row in result.get("results") or []:
                # LAST WRITE WINS AND IS REPORTED. A batch re-run replays the
                # same indices; silently keeping the first would hide a rerun
                # that changed its mind.
                if row["n"] in routed and routed[row["n"]] != row:
                    print(f"  index {row['n']} routed twice and differs; "
                          "keeping the later", file=sys.stderr)
                routed[row["n"]] = row

    rows, problems = [], []
    for index, remark in enumerate(remarks):
        row = routed.get(index)
        if row is None:
            problems.append(f"remark {index} was never routed")
            continue
        named = {canonical(s) for s in specs_of(remark.get("specs"))}
        to = [canonical(s) for s in row.get("routes_to") or []]
        away = [canonical(s) for s in row.get("routes_away_from") or []]
        # A SPEC THE REMARK NEVER NAMED CANNOT BE ROUTED. The brief forbade it
        # and this is the check rather than the hope. An invented destination is
        # the one error here that would travel into a council discussion.
        invented = [s for s in to + away if s not in named]
        if invented:
            problems.append(
                f"remark {index} routes {invented}, which its own specs list "
                f"{sorted(named)} does not name")
            continue
        both = sorted(set(to) & set(away))
        if both:
            # A REMARK CAN ROUTE IN BOTH DIRECTIONS ACROSS TIME, and this schema
            # has no axis for when. One remark does it: Jambrosay calls Band of
            # Devastation a large upgrade for an arms warrior entering in Tier 5
            # gear and says it falls off a cliff by Phase 4. Both halves are
            # true and neither is the whole claim.
            #
            # The guild lead ruled on 13 August 2026 that it stays unrouted
            # rather than be flattened to whichever half suits the anchor. The
            # remark still reaches the card through its stance, and the reason
            # is recorded here so the next reader does not "correct" it.
            problems.append(
                f"remark {index} routes {both} both to and away at once, so it "
                "is left unrouted: the claim is time-conditional and this file "
                "records direction, not timing")
            continue
        rows.append({
            "item_id": remark.get("item_id"),
            "item_name": remark.get("item_name"),
            "creator": remark.get("creator"),
            "timestamp": remark.get("timestamp"),
            "stance": remark.get("stance"),
            "routes_to": to,
            "routes_away_from": away,
            "no_routing_stated": bool(row.get("no_routing_stated")),
            **({"note": row["note"]} if row.get("note") else {}),
        })

    doc = {
        "meta": {
            "what": ("Which specs each captured creator remark sends an item "
                     "TO and which it sends it AWAY FROM, read out of the "
                     "remark rather than inferred from its stance."),
            "why": ("A stance says whether a creator likes an item. A council "
                    "needs to know where they think it should go, and those "
                    "are different questions: a remark can speak well of an "
                    "item and still argue three of the four specs that could "
                    "take it would waste it."),
            "produced": str(date.today()),
            "method": ("A workflow of Sonnet subagents, 40 remarks each, "
                       "reading only the paraphrase already captured in "
                       "creator-stances.yaml. No transcript was re-read and no "
                       "new source was consulted."),
            "constraint": ("An agent could only use the spec strings the "
                           "remark already named. This file rejects any row "
                           "that names one it did not, so a destination cannot "
                           "be invented."),
            "keyed_by": "item id, creator and timestamp, never the row number",
            "time_conditional_remarks_are_left_unrouted": (
                "A remark that puts an item on a spec now and takes it off "
                "later routes in both directions, and this file records "
                "direction rather than timing. One remark does it and it is "
                "listed under `rejected`. Ruled 13 August 2026: it stays "
                "unrouted rather than be flattened to one half."),
            "remarks": len(rows),
            "routed_to_someone": sum(1 for r in rows if r["routes_to"]),
            "routed_away_from_someone": sum(
                1 for r in rows if r["routes_away_from"]),
            "both_directions": sum(
                1 for r in rows if r["routes_to"] and r["routes_away_from"]),
            "no_routing_stated": sum(
                1 for r in rows if r["no_routing_stated"]),
        },
        "routing": rows,
    }
    if problems:
        doc["meta"]["rejected"] = problems

    args.out.write_text(yaml.safe_dump(doc, sort_keys=False, width=84,
                                       allow_unicode=True))
    print(f"{len(rows)} routed remark(s) -> {args.out}")
    if problems:
        print(f"\n{len(problems)} rejected:", file=sys.stderr)
        for line in problems[:20]:
            print(f"  {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
