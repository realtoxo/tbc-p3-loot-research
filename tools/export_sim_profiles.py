#!/usr/bin/env python3
"""Write each captured gear set as a wowsims equipment JSON.

WHY THIS SHAPE. A wowsims profile is importable only if it is the tool's own
format, so the output here is exactly what `ui/<class>/<spec>/gear_sets/*.json`
holds: `{"items": [ {id, enchant?, gems?}, ... ]}` with SEVENTEEN entries in
ItemSlot enum order, head first and ranged last. A slot the spec does not fill
is written as an empty object so the positions never shift.

THE SLOT ORDER IS THE ENUM, NOT OURS. proto/common.proto :: ItemSlot numbers
head 0 through ranged 16, and the captures now use the same seventeen names
after the vocabulary normalisation of 9 August 2026. A relic, idol, libram or
totem occupies the RANGED slot in TBC, which is why `relic` maps there.

ENCHANTS AND GEMS ARE ASSIGNED HERE, not copied from a guide. The captures
record items only, so the enchant per slot comes from enchants-by-spec.yaml,
which was farmed from Wowhead, and the gems are placed against each item's own
socket colours from items.csv.

THE HIT ENCHANT IS CONDITIONAL, AND THAT IS THE WHOLE POINT. A guide picks its
enchants for the hit position it assumes, and five of this roster's anchors sit
short on items alone. Where that happens the spec takes its school's hit enchant
instead of the pure-throughput one, and this file decides that from
hit-captured.yaml rather than from anyone's opinion. Once the enchants are
credited, NO anchor still needs a hit gem, so every socket goes to throughput.

Usage:
    python3 tools/export_sim_profiles.py --out data/sim/gear
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import yaml

CAPTURES = Path("data/facts/sim-profiles/hit-capture")
HIT = Path("data/facts/hit.yaml")
CAPTURED = Path("data/facts/hit-captured.yaml")
BY_SPEC = Path("data/facts/enchants-by-spec.yaml")
ITEMS = Path("data/facts/items.csv")
DB = Path(os.path.expanduser(os.environ.get(
    "WOWSIMS_TBC",
    "../tbc-phase-research-recovered/data/raw/vendor/wowsims-tbc-new-master",
))) / "assets/database/db.json"

# THE HIT GEM EACH SCHOOL USES. Ruled by the guild lead on 10 August 2026:
# this guild does not take hit enchants, and a shortfall is closed with gems
# instead, because the throughput enchant a hit enchant displaces is worth more
# than the throughput gem a hit gem displaces.
HIT_GEM = {"spell": "Great Dawnstone", "physical": "Rigid Dawnstone"}

# WHAT EACH META NEEDS BEFORE IT DOES ANYTHING AT ALL. A meta gem whose
# requirement is unmet sits in the socket contributing nothing, and the
# simulator does not complain: it just returns a slightly smaller number.
#
# FIVE PROFILES SHIPPED WITH A DEAD META before an audit on 10 August 2026
# caught it. The exporter gemmed every socket for throughput from the colour
# preferences and never checked the result. The Shadow Priest was the sharp
# case: its meta needs more blue than yellow, and its profiles carried nine
# yellow against five blue, while enchants-by-spec.yaml said in its own words
# that one Glowing Nightseye and no yellow satisfies it.
#
# Requirements are (red, yellow, blue) minimums, or the string "more_blue_than_yellow".
META_REQUIREMENT = {
    "Relentless Earthstorm Diamond": (2, 2, 2),
    "Chaotic Skyfire Diamond": (0, 0, 2),
    "Mystical Skyfire Diamond": "more_blue_than_yellow",
    "Bracing Earthstorm Diamond": "more_red_than_blue",
    "Swift Starfire Diamond": (1, 2, 0),
}

# ITEMS THE SIMULATOR CANNOT HOLD, and what stands in for them in the profile
# ONLY. The compendium is unchanged, ruled by the guild lead on 10 August 2026.
#
# WOLFSHEAD HELM WEARS THE TIER 6 HEAD IN THE PROFILE, ruled by the guild lead
# on 15 August 2026: "put on the t6 helm on the case if we must".
#
# Wolfshead Helm, 8345, is the Feral Cat head at every anchor and is absent from
# the wowsims database, being a level-40 leatherworking helm where the database
# carries TBC items. It was simmed as an EMPTY head slot from 14 August 2026,
# which produced a Cat missing a whole slot of stats, so the ruling above
# replaced the empty slot with the spec's own Tier 6 head.
#
# Thunderheart Cover, 31039, is the head of the Thunderheart Harness, which
# data/facts/tokens.yaml spec_to_set gives feral_cat at tier 6, and
# data/facts/items.csv resolves that set name to this id. It is used at BOTH
# anchors, in the profile ONLY.
#
# THIS IS THE LOUDEST DIVERGENCE IN THIS FILE, and it is not a correction. The
# Feral Cat DECLINES its Tier 6 head in the compendium, and Wolfshead is the
# entire reason: data/facts/sim-profiles/hit-capture/feral-cat.yaml records the
# head slot as never tier at any anchor, on an energy return the EP Workbook
# ranks first while refusing to score. So a run of this profile ANSWERS A
# QUESTION THE CARD REFUSES TO ANSWER. Every one of these figures belongs to a
# character the compendium does not describe, and the divergence is printed on
# every run and written into the profile itself for that reason.
SUBSTITUTIONS: dict[int, tuple[int, str]] = {
    8345: (31039,
           "Wolfshead Helm 8345 is not in the simulator database, so this "
           "profile wears Thunderheart Cover 31039, the Feral Cat Tier 6 head, "
           "ruled by the guild lead on 15 August 2026. THE CARD DECLINES THAT "
           "HELM. Wolfshead is why the Feral Cat takes no tier head at any "
           "anchor, so a figure from this profile answers a question the "
           "compendium refuses to answer and MUST NOT be compared with the "
           "card. Its meta socket is EMPTY, because enchants-by-spec.yaml "
           "records no meta gem for this spec on the ground that Wolfshead has "
           "no meta socket, so the substituted Cat is understated by one meta "
           "gem as well."),
}

# TANKS ARE NOT SIMMED, ruled by the guild lead on 14 August 2026: "we will not
# sim tanks". A tank run answers survivability questions this project does not
# ask, and the three tank captures never exported a gear file anyway, which had
# been failing silently. It is now a stated skip rather than an empty output
# nobody counted.
TANK_SPECS = frozenset({"feral_bear", "protection_paladin",
                        "protection_warrior"})

# proto/common.proto :: ItemSlot, in order. Transcribed, not inferred, which is
# the same rule the item and class enums in extract_items.py are held to after
# two enum bugs were found there.
SLOT_ORDER = [
    "head", "neck", "shoulder", "back", "chest", "wrist", "hands", "waist",
    "legs", "feet", "ring_1", "ring_2", "trinket_1", "trinket_2", "main_hand",
    "off_hand", "ranged",
]

# A relic, idol, libram or totem is equipped in the ranged slot in TBC, so a
# capture recording `relic` fills position 16.
ALIASES = {"relic": "ranged"}


def meta_shortfall(placed: dict, requirement) -> dict:
    """How many more of each colour the meta still needs."""
    if requirement == "more_blue_than_yellow":
        need = max(0, placed.get("yellow", 0) + 1 - placed.get("blue", 0))
        return {"blue": need} if need else {}
    if requirement == "more_red_than_blue":
        need = max(0, placed.get("blue", 0) + 1 - placed.get("red", 0))
        return {"red": need} if need else {}
    red, yellow, blue = requirement
    want = {"red": red, "yellow": yellow, "blue": blue}
    return {c: n - placed.get(c, 0) for c, n in want.items()
            if n - placed.get(c, 0) > 0}


def gear_json(block: dict, enchants: dict, gem_prefs: dict, meta_id, items_csv,
              by_name_enchant: dict, by_name_gem: dict, hit_gems: int,
              hit_gem_id, subbed: list, meta_name: str, gem_colors: dict,
              notes: list) -> dict:
    """One anchor as a wowsims equipment spec.

    GEMS ARE PLACED IN TWO PASSES, because a socket cannot be chosen in
    isolation. The first pass finds every socket; the second assigns, in this
    order of precedence:

      1. the meta socket takes the meta,
      2. hit gems take as many sockets as the shortfall needs, because a hit
         gap is a constraint and throughput is not,
      3. sockets are turned to whatever colour the META still lacks, since a
         meta that never activates is worth less than any gem that does,
      4. everything left takes the spec's preferred gem for its own colour.
    """
    rows = block.get("hit_by_slot") or {}
    by_slot = {}
    for name, row in rows.items():
        by_slot[ALIASES.get(name, name)] = row

    # Pass one: what the set actually has.
    layout = []
    for slot in SLOT_ORDER:
        row = by_slot.get(slot)
        item_id = row.get("id") if isinstance(row, dict) else None
        if item_id in SUBSTITUTIONS:
            new_id, why = SUBSTITUTIONS[item_id]
            subbed.append(f"{slot}: {why}")
            item_id = new_id
        sockets = ((items_csv.get(item_id) or {}).get("sockets") or "").split("|") \
            if item_id else []
        layout.append((slot, item_id, [c.strip().lower() for c in sockets if c.strip()]))

    # Pass two: decide what goes in each socket before writing any of them.
    plan = {}
    overridable: list = []
    remaining_hit = hit_gems
    for i, (_slot, _id, colors) in enumerate(layout):
        for j, color in enumerate(colors):
            if color == "meta":
                plan[(i, j)] = meta_id
            elif remaining_hit > 0 and hit_gem_id:
                plan[(i, j)] = hit_gem_id
                remaining_hit -= 1
            else:
                # PRE-ASSIGNED, NOT LEFT BLANK. The repair below has to know
                # what the whole set will look like, and a socket left to be
                # filled later is invisible to it. The first version left them
                # None, so the repair counted only its own placements, saw no
                # yellow, and declared the Shadow Priest's meta satisfied while
                # the output then filled nine yellow sockets.
                plan[(i, j)] = gem_prefs.get(color)
                overridable.append((i, j))

    requirement = META_REQUIREMENT.get(meta_name or "")
    if meta_id and requirement:
        placed = {}
        for key, gem in plan.items():
            if gem and gem != meta_id:
                for c in gem_colors.get(gem, set()):
                    placed[c] = placed.get(c, 0) + 1
        # ITERATIVE, BECAUSE FILLING A SOCKET CAN MAKE THE REQUIREMENT HARDER.
        # The Shadow Priest's meta wants more blue than yellow, and its
        # preferred yellow-socket gem is ORANGE, which counts as yellow as well
        # as red. Filling one yellow socket therefore raises the blue bar by
        # one, so a single pass never converges. This recomputes after every
        # placement and stops when the requirement is met or the sockets run
        # out.
        placed = {}
        for key, gem in plan.items():
            if gem and gem != meta_id:
                for c in gem_colors.get(gem, set()):
                    placed[c] = placed.get(c, 0) + 1
        free = list(overridable)
        while free:
            short = meta_shortfall(placed, requirement)
            if not short:
                break
            color = next(iter(short))
            gem = gem_prefs.get(color)
            if not gem:
                break
            key = free.pop(0)
            old_gem = plan.get(key)
            if old_gem == gem:
                continue
            for c in gem_colors.get(old_gem, set()):
                placed[c] = max(0, placed.get(c, 0) - 1)
            plan[key] = gem
            for c in gem_colors.get(gem, set()):
                placed[c] = placed.get(c, 0) + 1

    items = []
    for i, (slot, item_id, colors) in enumerate(layout):
        if not item_id:
            items.append({})
            continue
        entry: dict = {"id": item_id}
        name = enchants.get(slot)
        if name and name != "none":
            found = by_name_enchant.get(name)
            if found:
                entry["enchant"] = found["effectId"]
        gems = []
        for j, color in enumerate(colors):
            gem = plan.get((i, j))
            if gem is None:
                gem = gem_prefs.get(color)
            if gem:
                gems.append(gem)
        if gems:
            entry["gems"] = gems
        items.append(entry)

    # Say whether the meta actually activates, rather than assuming it did.
    if meta_id and requirement:
        final = {}
        for entry in items:
            for gem in entry.get("gems", []):
                if gem == meta_id:
                    continue
                for c in gem_colors.get(gem, set()):
                    final[c] = final.get(c, 0) + 1
        short = meta_shortfall(final, requirement)
        if short:
            notes.append(
                f"{meta_name} does NOT activate: still needs "
                + ", ".join(f"{n} more {c}" for c, n in short.items()))
    # THE DIVERGENCE TRAVELS WITH THE FILE. A substitution printed only on the
    # exporter run is invisible to anyone who opens the profile a week later,
    # imports it, and compares the figure with the spec's card. The key is
    # named with a leading underscore because it is ours and not the
    # simulator's; wowsims ignores a field its Equipment message does not
    # declare, and run_sims.py drops it explicitly rather than relying on that.
    out: dict = {"items": items}
    if subbed:
        out["_divergence"] = list(subbed)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--captures", type=Path, default=CAPTURES)
    ap.add_argument("--hit", type=Path, default=HIT)
    ap.add_argument("--out", type=Path, default=Path("data/sim/gear"))
    args = ap.parse_args()

    hit = yaml.safe_load(args.hit.read_text())
    captured = yaml.safe_load(CAPTURED.read_text())["specs"]
    by_spec = yaml.safe_load(BY_SPEC.read_text())["specs"]
    items_csv = {int(r["item_id"]): r for r in csv.DictReader(ITEMS.open())}
    db = json.loads(DB.read_text())
    by_name_enchant = {e["name"]: e for e in db["enchants"]}
    by_name_gem = {g["name"]: g for g in db["gems"]}
    # WHICH COLOURS A GEM COUNTS AS, and a hybrid counts as BOTH. That is the
    # rule meta activation runs on, and missing it made this check report 42
    # dead metas where the real number was 5: every Nightseye is PURPLE, not
    # blue, and a purple gem satisfies a blue requirement as well as a red one.
    # proto/common.proto :: GemColor gives meta 1, red 2, blue 3, yellow 4,
    # green 5, orange 6, purple 7, prismatic 8.
    COLOR = {
        2: {"red"}, 3: {"blue"}, 4: {"yellow"},
        5: {"yellow", "blue"}, 6: {"red", "yellow"}, 7: {"red", "blue"},
        8: {"red", "yellow", "blue"},
    }
    gem_colors = {g["id"]: COLOR.get(g.get("color"), set()) for g in db["gems"]}
    caps = {s["id"]: s.get("cap") for s in hit["specs"]}
    # DPS ONLY, ruled by the guild lead on 10 August 2026. See
    # data/judgments/capture-fidelity.yaml sim_profile_scope.dps_only.
    dps = {s["id"] for s in hit["specs"]
           if s.get("role") not in ("tank", "healer")}

    args.out.mkdir(parents=True, exist_ok=True)
    for stale in args.out.glob("*.json"):
        stale.unlink()

    written, problems, swapped, unknown, substituted = 0, [], [], [], []
    skipped: list[str] = []
    dead_meta: list[str] = []
    known_items = {i["id"] for i in db["items"]}
    for path in sorted(args.captures.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        if not isinstance(data, dict) or "anchors" not in data:
            continue
        spec = data.get("spec")
        if spec not in dps:
            # A SKIP THAT SAYS SO. This read `continue` and printed nothing, so
            # three tank captures produced no gear file and the only way to
            # notice was to count the output against the captures. The guild
            # lead ruled on 14 August 2026 that tanks are not simmed; that is a
            # decision and it should be visible in the run that acts on it.
            skipped.append(
                f"{spec}: not simmed. Tanks are out of scope by the ruling of "
                "14 August 2026, and a tank run answers survivability "
                "questions this project does not ask."
                if spec in TANK_SPECS else
                f"{spec}: no simulator spec is configured for it")
            continue
        conf = by_spec.get(spec) or {}
        prefs_raw = conf.get("gems") or {}
        gem_prefs = {}
        for color in ("red", "yellow", "blue"):
            found = by_name_gem.get(prefs_raw.get(color) or "")
            if found:
                gem_prefs[color] = found["id"]
        meta_name = prefs_raw.get("meta")
        meta = by_name_gem.get(meta_name) if meta_name and meta_name != "none" else None
        meta_id = meta["id"] if meta else None
        school = "spell" if caps.get(spec) == "spell" else "physical"
        hit_gem = by_name_gem.get(HIT_GEM[school])
        hit_gem_id = hit_gem["id"] if hit_gem else None
        meta_name = prefs_raw.get("meta") or ""

        for anchor, block in (data.get("anchors") or {}).items():
            enchants = dict(conf.get("enchants") or {})
            # HIT COMES FROM GEMS, NOT FROM AN ENCHANT SWAP. hit-captured.yaml
            # says how many, having already capped the count at the sockets the
            # set carries.
            state = (captured.get(spec) or {}).get(anchor) or {}
            hit_gems = state.get("gems_needed") or 0
            if hit_gems:
                swapped.append(
                    f"{spec} {anchor}: {hit_gems} hit gem(s) close a "
                    f"{state.get('gap_rating')} rating gap")
            subbed: list[str] = []
            notes: list[str] = []
            spec_json = gear_json(block, enchants, gem_prefs, meta_id,
                                  items_csv, by_name_enchant, by_name_gem,
                                  hit_gems, hit_gem_id, subbed, meta_name,
                                  gem_colors, notes)
            for line in notes:
                dead_meta.append(f"{spec} {anchor}: {line}")
            filled = sum(1 for i in spec_json["items"] if i)
            if filled < 15:
                problems.append(
                    f"{spec} {anchor} fills only {filled} of 17 slots")
            # AN ITEM THE SIMULATOR DOES NOT KNOW CANNOT BE SIMULATED, and the
            # profile has to say so rather than import silently wrong. This is
            # not hypothetical: Wolfshead Helm, 8345, is the Feral Cat's head at
            # every anchor and is absent from the wowsims database, because it
            # is a level-40 leatherworking helm and the database carries TBC
            # items. It is also the one head the EP Workbook ranks first while
            # refusing to score it.
            for line in subbed:
                substituted.append(f"{spec} {anchor} {line}")
            for entry in spec_json["items"]:
                if entry and entry["id"] not in known_items:
                    unknown.append(
                        f"{spec} {anchor}: item {entry['id']} "
                        f"({items_csv.get(entry['id'], {}).get('name', 'not in items.csv')}) "
                        "is not in the simulator database")
            name = f"{spec.replace('_', '-')}.{anchor.replace('_', '-')}.gear.json"
            (args.out / name).write_text(
                json.dumps(spec_json, indent=1) + "\n")
            written += 1

    print(f"{written} gear set(s) -> {args.out}")
    print(f"  {len(dps)} DPS spec(s), tanks and healers excluded by ruling")
    print(f"  {len(swapped)} anchor(s) close a hit gap with gems:")
    for line in swapped:
        print(f"    {line}")
    if dead_meta:
        print(f"\n  {len(dead_meta)} profile(s) whose meta gem does not activate:")
        for line in dead_meta:
            print(f"    {line}")

    for line in skipped:
        print(f"  {line}")
    if substituted:
        # LOUD ON PURPOSE. The Feral Cat head is not a near miss between two
        # similar helms: the card refuses the substituted item on the strength
        # of the item it replaces, so the two figures answer different
        # questions. A reader who skims this block and then quotes a Cat number
        # beside a Cat card has combined two characters.
        print(f"\n  !! {len(set(substituted))} SUBSTITUTION(S), PROFILE ONLY. "
              "The compendium is unchanged, so a run of these specs is NOT "
              "wearing what its card says, and these figures MUST NOT be "
              "compared with a card:")
        for line in sorted(set(substituted)):
            print(f"    !! {line}")
        print("    The same warning is written into each affected profile "
              "under the _divergence key.")

    if unknown:
        print(f"\n  {len(unknown)} slot(s) the simulator cannot resolve. These "
              "profiles import with that slot empty:")
        for line in sorted(set(unknown)):
            print(f"    {line}")

    if problems:
        print(f"\n{len(problems)} problem(s):", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
