#!/usr/bin/env python3
"""Index where each item is spoken about in the creator transcripts.

WHY THIS IS NOT A GREP. Plain substring search fails in both directions on this
corpus, and both failures were observed before this file was written:

  OVER-MATCHES. `Devastation` sits inside `Band of Devastation` and inside
  `Cuffs of Devastation`, and is also an ordinary English word. A substring
  count credited it to 19 transcripts. Longest match wins here, so a span
  already claimed by a longer item name cannot be claimed again by a shorter
  one, and a single-word name is flagged rather than trusted.

  UNDER-MATCHES. `Merciless Gladiator's Maul` is transcribed both with and
  without the apostrophe by the same automatic caption track. Both sides are
  normalised to letters, digits and single spaces before matching, so the
  punctuation stops mattering.

  SPANS ROWS. An item name is regularly split across two caption lines, as
  `cursed vision of` then `sargeras`. Matching row by row misses those, so the
  transcript is matched as one string and each character maps back to the row
  it came from, which is what carries the timestamp.

WHAT IT WRITES. data/facts/transcript-mentions.csv, one row per PASSAGE, where a
passage is a run of mentions of the same item in the same recording merged when
they fall within MERGE_SECONDS of each other. A creator returning to an item
half an hour later is a separate passage, because it is a separate remark.

SHORT FORMS. A creator says "the warglaives" and never "Warglaive of Azzinoth",
which is spoken zero times in 67 recordings. The part before "of" is therefore
admitted as an alias, but ONLY where it names exactly one item and is not a
generic equipment noun, because `gauntlets` heads three items and `talisman`
two. Every alias match is flagged ambiguous, since `warglaive` also names
Illidan's own weapon in the fight commentary rather than the loot.

WHAT IT DOES NOT DO. It records that an item was NAMED. It does not record what
was said about it, and a mention is not an opinion. The ambiguous flag marks
rows where the name may not be the item at all.

Usage:
    python3 tools/index_transcript_mentions.py --out data/facts/transcript-mentions.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import yaml

TRANSCRIPTS = Path("data/research/creator-transcripts")
ITEMS = Path("data/facts/items.csv")

# Two mentions of one item closer than this are one remark, not two.
MERGE_SECONDS = 120
# How much speech to hand a reader either side of the passage.
LEAD_IN, LEAD_OUT = 20, 45

# A single-word item name that is also ordinary English cannot be trusted from
# the name alone. These are the ones this corpus actually contains; the flag is
# what matters, not the completeness of the list, because every single-word name
# is flagged regardless of whether it appears here.
COMMON_WORDS = {
    "devastation", "madness", "infamy", "netherbane", "shadowmoon", "torment",
    "despair", "malice", "rage", "vengeance", "fury", "glory", "brilliance",
    "cataclysm", "eternium", "syphon", "crystalforged", "lightbringer",
}

# A creator says "the warglaives", never "Warglaive of Azzinoth". The full name
# is spoken ZERO times in 67 recordings, so the index missed the item this
# guild most needs commentary on until an alias was allowed for the part before
# "of". SHORT FORMS ARE NOT FREE, though: the same rule turns `gauntlets` into a
# match for three different items and `talisman` into two, which would invent
# agreement between creators talking about different things. An alias is
# therefore admitted only when it is unique across item NAMES and is not one of
# the generic equipment nouns below, which a creator uses to mean any item in
# the slot rather than a particular one.
SLOT_NOUNS = {
    "gauntlets", "pendant", "talisman", "slippers", "vestments", "breastplate",
    "chestguard", "greaves", "pauldrons", "pantaloons", "sextant", "shuriken",
    "wristbands", "garments", "band", "belt", "boots", "ring", "cloak", "helm",
    "robe", "staff", "blade", "shield", "bracers", "cord", "girdle", "drape",
    "mantle", "hood", "seal", "wand", "mace", "axe", "bow", "gloves", "leggings",
    "legguards", "shoulderpads", "necklace", "amulet", "choker", "signet",
}


# Variants a caption track produces that no rule derives. Keep this small and
# add only what has been OBSERVED in the corpus, with the count seen, because a
# guessed variant is a fabricated mention. Maps a spoken form to the exact
# `name` column in items.csv.
SPOKEN_ALIASES = {
    # "war glaive" split in two, 6 times across 3 recordings. One of them,
    # jambrosay-feral-druid-p3-p4-loot, uses ONLY this form, so without the
    # entry that creator is invisible on the item.
    "war glaive": "Warglaive of Azzinoth",
}


def norm(text: str) -> str:
    """Letters, digits and single spaces. Apostrophes vanish rather than split."""
    text = text.replace("’", "").replace("'", "")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def rows(tsv: Path) -> list[tuple[float, str]]:
    out = []
    for line in tsv.read_text().splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            out.append((float(parts[0]), parts[2]))
    return out


def flatten(lines: list[tuple[float, str]]) -> tuple[str, list[tuple[int, float]]]:
    """One normalised string, plus a character offset to start time map."""
    pieces, marks, pos = [], [], 0
    for start, text in lines:
        piece = norm(text)
        if not piece:
            continue
        marks.append((pos, start))
        pieces.append(piece)
        pos += len(piece) + 1
    return " ".join(pieces), marks


def time_at(marks: list[tuple[int, float]], offset: int) -> float:
    lo, hi = 0, len(marks) - 1
    best = marks[0][1] if marks else 0.0
    while lo <= hi:
        mid = (lo + hi) // 2
        if marks[mid][0] <= offset:
            best = marks[mid][1]
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path,
                    default=Path("data/facts/transcript-mentions.csv"))
    args = ap.parse_args()

    manifest = yaml.safe_load((TRANSCRIPTS / "manifest.yaml").read_text())
    videos = {e["slug"]: e for e in manifest["transcripts"]}

    catalogue = [r for r in csv.DictReader(ITEMS.open()) if len(norm(r["name"])) >= 5]

    # An alias is admitted only where the head names exactly one item, so
    # `gauntlets`, which heads three, never becomes a search term.
    heads: dict[str, set[str]] = {}
    for row in catalogue:
        name = norm(row["name"])
        head = name.split(" of ")[0]
        if head != name:
            heads.setdefault(head, set()).add(name)

    spoken = {}
    for phrase, target in SPOKEN_ALIASES.items():
        for row in catalogue:
            if row["name"] == target:
                spoken.setdefault(norm(phrase), []).append(row)

    items = []
    for row in catalogue:
        name = norm(row["name"])
        items.append((name, row["item_id"], row["name"], "name"))
        for phrase, targets in spoken.items():
            if row in targets:
                items.append((phrase, row["item_id"], row["name"], "alias"))
        head = name.split(" of ")[0]
        if (head != name and len(heads.get(head, ())) == 1
                and head not in SLOT_NOUNS
                and (len(head.split()) >= 2 or len(head) >= 8)):
            items.append((head, row["item_id"], row["name"], "alias"))
    # LONGEST FIRST. This ordering is the whole defence against the substring
    # over-match, so it is not an optimisation and must not be removed.
    items.sort(key=lambda i: -len(i[0]))

    found = []
    for slug, video in sorted(videos.items()):
        tsv = TRANSCRIPTS / f"{slug}.tsv"
        if not tsv.is_file():
            continue
        lines = rows(tsv)
        text, marks = flatten(lines)
        if not text:
            continue
        claimed: list[tuple[int, int]] = []
        for name, item_id, display, how in items:
            # A trailing s lets "warglaives" reach "Warglaive of Azzinoth".
            for m in re.finditer(r"(?<![a-z0-9])" + re.escape(name) +
                                 r"s?(?![a-z0-9])", text):
                span = (m.start(), m.end())
                if any(span[0] < c[1] and c[0] < span[1] for c in claimed):
                    continue
                claimed.append(span)
                found.append({
                    "item_id": item_id, "item_name": display, "slug": slug,
                    "seconds": time_at(marks, m.start()),
                    "ambiguous": (" " not in name or name in COMMON_WORDS
                                  or how == "alias"),
                    "matched_by": how,
                })

    # Merge repeats of one item in one recording into a single passage.
    found.sort(key=lambda r: (r["slug"], r["item_id"], r["seconds"]))
    passages: list[dict] = []
    for row in found:
        prev = passages[-1] if passages else None
        if (prev and prev["slug"] == row["slug"]
                and prev["item_id"] == row["item_id"]
                and row["seconds"] - prev["last"] <= MERGE_SECONDS):
            prev["last"] = row["seconds"]
            prev["mentions"] += 1
            continue
        passages.append({**row, "last": row["seconds"], "mentions": 1})

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        # csv defaults to CRLF, which git normalises on the next touch and the
        # drift check in `just check` then sees a file that differs from what
        # the transform just wrote. Unix endings keep the generated file stable.
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["item_id", "item_name", "slug", "channel", "video_id",
                    "start_seconds", "end_seconds", "mentions", "ambiguous",
                    "matched_by", "cite_url"])
        for p in sorted(passages, key=lambda r: (int(r["item_id"]), r["slug"],
                                                 r["seconds"])):
            v = videos[p["slug"]]
            start = max(0, int(p["seconds"]) - LEAD_IN)
            w.writerow([p["item_id"], p["item_name"], p["slug"], v["channel"],
                        v["id"], start, int(p["last"]) + LEAD_OUT,
                        p["mentions"], "yes" if p["ambiguous"] else "no",
                        p["matched_by"], f"{v['url']}&t={start}s"])

    distinct = len({p["item_id"] for p in passages})
    amb = sum(1 for p in passages if p["ambiguous"])
    print(f"{len(passages)} passages, {distinct} distinct items, "
          f"{len(videos)} recordings")
    print(f"  {amb} passage(s) flagged ambiguous, meaning the name is one word "
          "or ordinary English and may not be the item")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
