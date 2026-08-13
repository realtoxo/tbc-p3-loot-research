#!/usr/bin/env python3
"""Capture the effect text Wowhead prints for items the database cannot describe.

WHY ANYTHING IS FETCHED AT ALL. `data/facts/item-effects.csv` comes from the
WoWSims database, which carries a buff id, a buff name, granted stats and proc
terms. For most items that is the whole effect. For forty-six it is not: wowsims
models those effects in Go and stores no stats, no duration and no trigger, so
the database holds an internal label such as "Rogue Tier 6 Trinket" and nothing
else. A card printing that label reads like an item which does nothing, which is
the opposite of the truth for a trinket whose only worth is its effect.

WHY THESE TWENTY-FOUR AND NOT ALL FORTY-SIX. The remaining twenty-two carry
utility buffs a loot council does not argue about: eleven engineering goggles
sharing Gas Cloud Tracking and Stealth Detection, three stealth items, three
Lionheart weapons granting fear resistance, three Illidari-Bane weapons granting
demon slaying, and one silence resistance neck. The guild lead reviewed the full
forty-six on 13 August 2026 and approved these twenty-four. The list is written
out rather than derived, because the cut is a decision and a derived cut would
look like a measurement.

THE CAPTURE IS THE CITATION. Raw responses are written under `data/research/`
and never edited afterwards, so a claim in the compendium points at bytes that
were actually received, on a date that is recorded. `tools/extract_effect_text.py`
reads those bytes and produces the fact table.

Usage:
    python3 tools/fetch_effect_text.py --out data/research/wowhead-effects
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import yaml

# The same host `tools/check_external_links.py` resolves ids against. Wowhead's
# own pages render their loot and tooltip data client-side, so a plain fetch of
# the item page returns chrome only; this endpoint returns the tooltip as data.
ENDPOINT = "https://nether.wowhead.com/tbc/tooltip/item/{id}"

# THE APPROVED TWENTY-FOUR, grouped as they were reviewed. Every one is an item
# whose effect the WoWSims database names but does not describe.
WANTED: dict[str, list[int]] = {
    # The whole relic slot. A relic carries no stats at all, so the effect is
    # the entire item and a card showing a buff name shows nothing.
    "relics": [
        28568,  # Idol of the Avian Heart
        30051,  # Idol of the Crescent Goddess
        32387,  # Idol of the Raven Goddess
        32257,  # Idol of the White Stag
        30063,  # Libram of Absolute Truth
        28592,  # Libram of Souls Redeemed
        27917,  # Libram of the Eternal Rest
        32368,  # Tome of the Lightbringer
        32330,  # Totem of Ancestral Guidance
        28523,  # Totem of Healing Rains
        27815,  # Totem of the Astral Winds
        30023,  # Totem of the Maelstrom
        28248,  # Totem of the Void
    ],
    # The five Ashtongue Deathsworn trinkets the database leaves blank. The
    # other four of the nine carry stats or proc terms and describe themselves.
    "ashtongue_trinkets": [
        32490,  # Ashtongue Talisman of Acumen
        32486,  # Ashtongue Talisman of Equilibrium
        32492,  # Ashtongue Talisman of Lethality
        32491,  # Ashtongue Talisman of Vision
        32489,  # Ashtongue Talisman of Zeal
    ],
    "other_trinkets": [
        31859,  # Darkmoon Card: Madness
        30448,  # Talon of Al'ar
        30720,  # Serpent-Coil Braid
        30446,  # Solarian's Sapphire
    ],
    "weapons": [
        30318,  # Netherstrand Longbow
        31334,  # Staff of Natural Fury
    ],
}


# THE NAMES THE IDS MUST RESOLVE TO. Three of the twenty-four ids above were
# first written from memory and three were wrong; one of them, 32369, is a real
# item with a real tooltip, Blade of Savagery, so the capture would have
# succeeded and filed a weapon's text under a bow. An id typed by hand is a
# guess until something checks it, and this is the something.
def expected_names(items_csv: Path) -> dict[int, str]:
    import csv
    return {int(r["item_id"]): r["name"]
            for r in csv.DictReader(items_csv.open())}


def fetch(item_id: int) -> dict:
    url = ENDPOINT.format(id=item_id)
    req = urllib.request.Request(
        url, headers={"User-Agent": "tbc-p3-loot-research/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path,
                    default=Path("data/research/wowhead-effects"))
    ap.add_argument("--items", type=Path, default=Path("data/facts/items.csv"))
    args = ap.parse_args()

    today = str(date.today())
    into = args.out / today
    into.mkdir(parents=True, exist_ok=True)

    names = expected_names(args.items)
    captured, failed = [], []
    for group, ids in WANTED.items():
        for item_id in ids:
            path = into / f"item-{item_id}.json"
            if path.exists():
                # A capture is never re-fetched. The bytes on disk are what a
                # citation points at, and replacing them would move a claim
                # under a reader who already read it.
                captured.append({"item_id": item_id, "group": group,
                                 "file": path.name, "refetched": False})
                continue
            try:
                payload = fetch(item_id)
            except (urllib.error.HTTPError, urllib.error.URLError,
                    TimeoutError, json.JSONDecodeError) as exc:
                failed.append(f"{item_id}: {exc}")
                print(f"  {item_id}: FAILED {exc}", file=sys.stderr)
                continue
            claimed = names.get(item_id)
            if claimed is not None and payload.get("name") != claimed:
                failed.append(
                    f"{item_id}: Wowhead calls it {payload.get('name')!r} and "
                    f"data/facts/items.csv calls it {claimed!r}. The id names "
                    "two different items, so nothing is written")
                print(f"  {item_id}: NAME MISMATCH, not written", file=sys.stderr)
                continue
            path.write_text(json.dumps(payload, indent=1, ensure_ascii=False)
                            + "\n")
            captured.append({"item_id": item_id, "group": group,
                             "file": path.name, "name": payload.get("name", ""),
                             "refetched": True})
            print(f"  {item_id}: {payload.get('name', '')}", file=sys.stderr)
            time.sleep(1)

    manifest = into / "manifest.yaml"
    doc = {
        "meta": {
            "captured": today,
            "source": ENDPOINT,
            "what": ("The Wowhead tooltip payload for items whose effect the "
                     "WoWSims database names but does not describe."),
            "scope": ("Twenty-four items approved by the guild lead on "
                      "13 August 2026 out of forty-six candidates. The "
                      "twenty-two not captured carry utility buffs a loot "
                      "council does not argue about. See the module docstring "
                      "of tools/fetch_effect_text.py."),
            "items": len(captured),
        },
        "captures": captured,
    }
    if failed:
        doc["meta"]["not_resolved"] = failed
    manifest.write_text(yaml.safe_dump(doc, sort_keys=False, width=88,
                                       allow_unicode=True))
    print(f"{len(captured)} captured, {len(failed)} failed -> {into}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
