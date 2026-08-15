#!/usr/bin/env python3
"""Resolve the consumable PROSE into the ids a RaidSimRequest carries.

WHAT THIS PRODUCES. `data/facts/consumable-ids.yaml`: a catalog of every
consumable name this project can turn into a simulator id, the id it becomes,
and where that id was read from; then, per spec, which name was taken for which
`ConsumesSpec` field, which names were passed over, and what the guide said
around the one that was taken.

WHY IT IS A FACT FILE AND NOT A DICT IN run_sims.py. A wrong id does not fail.
The run succeeds and the DPS is wrong, and nothing in the output says which
flask was drunk. Written out here, "Flask of Pure Death" sits beside 22866 and
beside the file that id was read from, so a reader can check it in a minute.

WHERE THE PROSE COMES FROM. `data/facts/consumables.yaml` for sixteen specs,
and `data/facts/sim-profiles/combat-rogue.yaml` for the Combat Rogue, which
keeps its consumables beside its gear and is deliberately not copied into the
other file.

HOW A NAME IS CHOSEN. The guides lead with the pick and follow with the cheaper
or conditional alternatives, so the FIRST catalog name in a field wins and every
later one is written out under `alternatives_named`. Where two catalog names
start at the same character the longer one wins, because "Adamantite Sharpening
Stone" and "Consecrated Sharpening Stone" are different stones and this project
has dispositioned an item on a shared word four times.

A NAME THE PROSE QUALIFIES IS TESTED AGAINST THE CAPTURED FACT, not taken on
its position. Two conditions appear in these guides, and each one names a fact
this repository already holds:

  the weapon type   "Adamantite Sharpening Stone (bladed) or Adamantite
                    Weightstone (blunt)" is one sentence naming two stones, and
                    which one applies is decided by the weapon in the captured
                    gear, so `data/sim/gear` and `items.csv` settle it.
  the hit cap       "Spicy Hot Talbuk if not yet hit-capped, or Grilled Mudfish
                    once hit-capped" is a rule rather than a pick, and
                    `hit-captured.yaml` records whether each spec closes its gap.

BOTH WERE ANSWERED BY POSITION BEFORE 15 AUGUST 2026 and both were wrong. The
Beast Mastery Hunter carries a Fist weapon, which the simulator counts as blunt,
and took the sharpening stone: only the Weightstone, 34340, adds 12 to ranged
base damage in sim/core/consumes.go, which is the half of a hunter that fires.
The same hunter is hit-capped at both anchors and ate the not-capped food.
NEITHER FAILED. Both ran and returned a smaller number.

A MAIN-HAND IMBUE IS DROPPED IN A WINDFURY PARTY, so several of the picks below
are correct and worth nothing. sim/core/consumes.go applies `MhImbueId` only
where the party has no Windfury Totem, and applies `OhImbueId` with no condition
at all. `data/facts/weapon-imbue-gating.yaml` holds that rule with its source
lines; this transform READS which parties carry the totem from
`data/facts/raid-buffs.yaml` and stamps every affected pick with `gate`, so a
reader who measures one of those stones and reads a delta of 0.0 meets the
reason beside the id rather than deriving it again. THE FURY WARRIOR'S STONE IS
THE WORKED EXAMPLE: its main hand is a Mace, the sharp stone it carried was the
wrong type, and correcting it to the Weightstone is worth exactly 0.0 because
the gate drops both.

WHAT IS DELIBERATELY NOT RESOLVED, and each is a defect avoided rather than
work skipped:

  elixirs_instead  The field name says instead. A flask counts as both a battle
                   and a guardian elixir in 2.4.3, so wiring both would stack
                   two things the game does not stack.
  scrolls          The prose names scrolls it rejects in the same sentence, for
                   example "Warcraft Tavern's table also lists Scroll of
                   Strength V and Scroll of Protection V, but neither ... serves
                   a BM Hunter". A substring match would switch on a scroll the
                   source turned down.
  other            Runes, ammo, sappers and seeds, mixed with prose about who in
                   the raid brings them. Nothing here maps to one field.
  drums            `raid-buffs.yaml` already gives every party its drums through
                   PartyBuffs, so a drums_id in ConsumesSpec would count them a
                   second time.

Usage:
    python3 tools/extract_consumable_ids.py --out data/facts/consumable-ids.yaml
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

import yaml

# THE SLOT ORDER IS RUN_SIMS' OWN LIST, imported rather than copied. Both tools
# index the same `items` array of a gear export, and two hand-kept copies of one
# order drift: a copy that moved `ranged` above `off_hand` would read the bow as
# the off-hand weapon and imbue it with a stone.
from run_sims import SLOT_ORDER

CONSUMABLES = Path("data/facts/consumables.yaml")
ROGUE = Path("data/facts/sim-profiles/combat-rogue.yaml")
# THE TWO CAPTURED FACTS A PICK CAN DEPEND ON. Both are generated, and both are
# regenerated BEFORE this tool in `just regen`, so a run here reads the current
# figures rather than the previous ones. Moving this line earlier in that recipe
# would resolve a conditional pick against a stale capture.
GEAR = Path("data/sim/gear")
ITEMS = Path("data/facts/items.csv")
HIT = Path("data/facts/hit-captured.yaml")
# The third anchor's hit state, which hit-captured.yaml deliberately does not
# carry. See hit_states() for why the two files split this.
BIS_CAPTURES = Path("data/facts/sim-profiles/bis-capture")
# One hit gem is 10 rating, the constant hit.yaml.discretionary_hit_budget sets
# and tools/extract_hit_captures.py::RATING_PER_GEM uses.
RATING_PER_HIT_GEM = 10
# WHICH PARTY CARRIES A WINDFURY TOTEM, and who stands in it. Read rather than
# listed, because a party list typed into this file is a second copy of one that
# already exists, and the copy is what goes stale when the roster moves.
BUFFS = Path("data/facts/raid-buffs.yaml")
ROSTER = Path("data/facts/roster.yaml")
GATING = Path("data/facts/weapon-imbue-gating.yaml")
WOWSIMS = Path(os.path.expanduser(os.environ.get(
    "WOWSIMS_TBC",
    "../tbc-phase-research-recovered/data/raw/vendor/wowsims-tbc-new-master")))
DB = WOWSIMS / "assets" / "database" / "db.json"
IMBUE_UI = WOWSIMS / "ui" / "core" / "components" / "inputs" / "consumables.ts"
IMBUE_SIM = WOWSIMS / "sim" / "core" / "consumes.go"
ROGUE_SIM = WOWSIMS / "sim" / "rogue" / "poisons.go"
UTILS = WOWSIMS / "ui" / "core" / "proto_utils" / "utils.ts"

# proto/common.proto :: enum ConsumableType. Transcribed, because db.json prints
# the number and a reader of this file should not have to decode it.
CONSUMABLE_TYPE = {
    1: "ConsumableTypePotion",
    2: "ConsumableTypeFlask",
    3: "ConsumableTypeFood",
    6: "ConsumableTypeBattleElixir",
    7: "ConsumableTypeGuardianElixir",
    9: "ConsumableTypePetFood",
}

# Which prose field feeds which proto/common.proto :: ConsumesSpec field, and
# which db.json consumable type is allowed to answer it. The type constraint is
# the guard against a food name landing in flask_id.
WIRED = [
    ("flask", "flask_id", 2),
    ("food", "food_id", 3),
    ("potions", "pot_id", 1),
    ("weapon_main_hand", "mhImbue_id", None),
    ("weapon_off_hand", "ohImbue_id", None),
]

# THE WEAPON IMBUES ARE NOT IN db.json. The `consumables` array holds 105
# entries and none of them is an oil, a stone or a poison, so an imbue id cannot
# be looked up the way a flask can. It is a SPELL id, and the simulator accepts
# a fixed handful of them and silently ignores every other number.
#
# Each row below therefore carries three things: the value the request sends,
# the item the wowsims UI shows for it, and the file that ACCEPTS it. The names
# are this project's, because no source in the vendored checkout prints a name
# for these item ids; `verify_imbues` checks the two numbers of every row
# against the vendored source, so a name is the only part a reader must judge.
#
# `accepted_by` of None means the simulator reads the field and does nothing
# with the value. That is the worst case the task warns about, so those rows are
# never picked; they are reported as unresolved instead.
#
# `requires` is the WEAPON THIS IMBUE GOES ON, transcribed from the `showWhen`
# of the same UI declaration and checked by `verify_imbues`. A stone the UI
# hides on the equipped weapon is one the guide did not mean, and the simulator
# applies it anyway: the encoder takes the id, registerStaticImbue takes the
# case, and the run succeeds with a stone the character could not have used.
IMBUES = [
    # name, imbue value, wowsims UI item id, UI const, accepting source, requires
    ("Mana Oil", 25123, 20748, "ManaOil",
     "sim/core/consumes.go::registerStaticImbue", None),
    ("Brilliant Wizard Oil", 25122, 20749, "BrilWizardOil",
     "sim/core/consumes.go::registerStaticImbue", None),
    ("Superior Wizard Oil", 28017, 22522, "SupWizardOil",
     "sim/core/consumes.go::registerStaticImbue", None),
    ("Adamantite Sharpening Stone", 29453, 23529, "AdamantiteSharpeningMH",
     "sim/core/consumes.go::registerStaticImbue", "sharp"),
    ("Adamantite Weightstone", 34340, 28421, "AdamantiteWeightMH",
     "sim/core/consumes.go::registerStaticImbue", "blunt"),
    ("Consecrated Sharpening Stone", 28891, 23122, "ConsecratedSharpeningStoneMH",
     "sim/core/consumes.go::registerStaticImbue", "weapon"),
    # THE RANK IS NOT CLAIMED. The guides say "Deadly Poison VII" and the
    # simulator carries exactly one deadly poison imbue, so the rank chooses
    # between nothing. Naming it "Deadly Poison VII" here would be a rank read
    # off a guide and printed as though the simulator had confirmed it.
    ("Instant Poison", 26891, 21927, "RogueInstantPoison",
     "sim/rogue/poisons.go::instantImbueID", "weapon"),
    ("Deadly Poison", 27186, 22054, "RogueDeadlyPoison",
     "sim/rogue/poisons.go::deadlyImbueID", "weapon"),
    ("Wound Poison", 27188, 22055, "RogueWoundPoison",
     "sim/rogue/poisons.go::woundImbueID", "weapon"),
    # A SHAMAN SELF-IMBUE IS NOT A CONSUMABLE. The wowsims UI offers Windfury
    # Weapon in the same dropdown as the oils, which is why it is listed here,
    # but ConsumesSpec is not where the simulator reads it: it reads
    # ShamanOptions.imbue_mh, an enum in proto/shaman.proto. Sending 25505 in
    # mhImbue_id is accepted by the encoder and does nothing at all.
    ("Windfury Weapon", 25505, None, "ShamanImbueWindfury", None, "weapon"),
    ("Flametongue Weapon", 25489, None, "ShamanImbueFlametongue", None, "weapon"),
]

# WHICH `showWhen` EACH REQUIREMENT MUST NAME. The poison rows gate on the class
# rather than on the weapon, so they are not checked here; a rogue with no
# off-hand weapon is caught by the gear instead.
SHOW_WHEN = {"sharp": "hasSharp", "blunt": "hasBlunt"}

# proto/common.proto :: enum WeaponType, split the way the simulator splits it.
# `verify_weapon_classes` reads both lists back out of the vendored UI, so
# neither set is typed in here on trust. A FIST WEAPON IS BLUNT, which is the
# whole of defect A: two hunters carry Fist weapons that read as blades to
# anyone sorting by how the item looks.
BLUNT = {"Fist", "Mace", "Staff"}
SHARP = {"Axe", "Dagger", "Polearm", "Sword"}

# What items.csv calls the two off-hand items that take no imbue. A held item
# and a shield are worn in the off hand and are not weapons, and the simulator
# agrees: ui/core/proto_utils/gear.ts::hasOHWeapon excludes both.
NOT_A_WEAPON = {"Off Hand", "Shield"}

# THE HIT-CAP CONDITION, in the words these guides use for it. The not-capped
# phrases are tested FIRST, because "if not yet hit-capped" contains
# "hit-capped" and a capped-first test would read the negation as the
# affirmative and pick the food the source rules out.
NOT_CAPPED_PHRASES = [
    "if not yet hit-capped", "if not hit-capped", "if still short of hit",
    "while still short", "short of the hit cap", "reaching the hit cap",
    "short of hit",
]
CAPPED_PHRASES = ["once hit-capped", "once capped", "when hit-capped",
                  "if hit-capped"]

# Prose fields carrying real consumables that are deliberately left unwired. The
# reason travels into the generated file, so a reader asking why a spec runs no
# scroll gets an answer rather than a silence.
DECLINED = {
    "elixirs_instead":
        "A flask counts as both a battle and a guardian elixir in 2.4.3, and "
        "this field names what to drink INSTEAD of the flask. Wiring both would "
        "stack two things the game does not stack.",
    "against_demons":
        "Elixir of Demonslaying replaces the battle elixir against demons only. "
        "The encounter these runs use is a generic level 73 target, so a "
        "demon-only elixir would be credited against a target that is not one.",
    "scrolls":
        "Several specs name a scroll in the same sentence that rejects it, so "
        "matching on the name would switch on a scroll the source turned down. "
        "A scroll is 20 points of one stat; a wrong one is a wrong number.",
    "other":
        "Runes, ammunition, sapper charges and seeds, mixed with prose about "
        "which raider brings them. No single ConsumesSpec field answers it.",
}


def load_db_catalog() -> dict:
    """Every db.json consumable, indexed by name, with its type and its id.

    A DUPLICATE NAME STOPS THE RUN. Four Major Protection Potions appear twice
    in this array under two ids, and picking either silently would be exactly
    the mistake this project has made four times on item names.
    """
    if not DB.is_file():
        raise SystemExit(
            f"extract_consumable_ids.py: no item database at {DB}. Set "
            "WOWSIMS_TBC to a wowsims-tbc-new checkout.")
    entries = json.loads(DB.read_text())["consumables"]
    catalog: dict = {}
    duplicates: dict = {}
    for entry in entries:
        name = entry["name"]
        if name in catalog and catalog[name]["id"] != entry["id"]:
            duplicates.setdefault(name, [catalog[name]["id"]]).append(entry["id"])
        catalog[name] = {"id": entry["id"], "type": entry.get("type")}
    for name, ids in duplicates.items():
        catalog[name]["duplicate_ids"] = sorted(ids)
    return catalog


def verify_imbues() -> None:
    """Check every IMBUES row against the vendored simulator before using it.

    THE DEFECT THIS PREVENTS is an id the request carries and the simulator
    drops. `mhImbue_id` is an int32, so any number is accepted by the encoder,
    and a value outside the switch in registerStaticImbue produces a run that
    succeeds with no imbue on the weapon. Nothing in the output says so.
    """
    ui = IMBUE_UI.read_text() if IMBUE_UI.is_file() else ""
    accepting = {
        "sim/core/consumes.go::registerStaticImbue":
            IMBUE_SIM.read_text() if IMBUE_SIM.is_file() else "",
    }
    for path, key in ((ROGUE_SIM, "sim/rogue/poisons.go::instantImbueID"),
                      (ROGUE_SIM, "sim/rogue/poisons.go::deadlyImbueID"),
                      (ROGUE_SIM, "sim/rogue/poisons.go::woundImbueID")):
        accepting[key] = path.read_text() if path.is_file() else ""
    if not ui:
        raise SystemExit(
            f"extract_consumable_ids.py: no imbue table at {IMBUE_UI}. Every "
            "imbue id in this project is read from that file, so it cannot be "
            "regenerated without it.")

    for name, value, item_id, const, accepted_by, requires in IMBUES:
        block = re.search(
            r"export const " + re.escape(const) + r"\s*=\s*\{(.*?)\}", ui, re.S)
        if not block:
            raise SystemExit(
                f"extract_consumable_ids.py: {const} is no longer declared in "
                f"{IMBUE_UI}. {name} claims imbue id {value} on the strength of "
                "that declaration, so the claim cannot stand without it.")
        body = block.group(1)
        if f"value: {value}" not in body:
            raise SystemExit(
                f"extract_consumable_ids.py: {const} no longer carries value "
                f"{value} in {IMBUE_UI}, so the id claimed for {name} is stale.")
        if item_id is not None and f"fromItemId({item_id})" not in body:
            raise SystemExit(
                f"extract_consumable_ids.py: {const} no longer names item "
                f"{item_id} in {IMBUE_UI}, so the name {name!r} is unsupported.")
        if accepted_by and str(value) not in accepting.get(accepted_by, ""):
            raise SystemExit(
                f"extract_consumable_ids.py: {accepted_by} no longer reads "
                f"{value}, so {name} would be sent and ignored.")
        # ONE ROW SERVES BOTH HANDS, so the off-hand twin must carry the same
        # numbers. The UI declares AdamantiteWeightMH and AdamantiteWeightOH
        # separately, and this file cites the main-hand const for a stone sent
        # to either hand. If the two ever part, that citation becomes a number
        # read from the wrong declaration.
        if const.endswith("MH"):
            twin = re.search(
                r"export const " + re.escape(const[:-2]) + r"OH\s*=\s*\{(.*?)\}",
                ui, re.S)
            if not twin or f"value: {value}" not in twin.group(1) or (
                    item_id is not None
                    and f"fromItemId({item_id})" not in twin.group(1)):
                raise SystemExit(
                    f"extract_consumable_ids.py: {const[:-2]}OH no longer "
                    f"matches {const} in {IMBUE_UI}, so an off-hand pick citing "
                    f"{const} would cite the wrong declaration.")
        want = SHOW_WHEN.get(requires)
        if want and want not in body:
            raise SystemExit(
                f"extract_consumable_ids.py: {const} no longer shows on a "
                f"{requires} weapon in {IMBUE_UI}, so the weapon class claimed "
                f"for {name} is stale. A stale class picks a stone the "
                "character could not use, and the run still succeeds.")


def verify_weapon_classes() -> None:
    """Check BLUNT and SHARP against the lists the simulator's UI holds.

    THE DEFECT THIS PREVENTS is a weapon class read off the item art. Fist
    weapons look like blades and are counted blunt, and a wrong class chooses
    the wrong stone, which runs and returns a smaller number.
    """
    text = UTILS.read_text() if UTILS.is_file() else ""
    if not text:
        raise SystemExit(
            f"extract_consumable_ids.py: no weapon-class lists at {UTILS}. "
            "Which stone a weapon takes is decided by those two lists, so it "
            "cannot be decided without them.")
    for func, ours in (("isBluntWeaponType", BLUNT), ("isSharpWeaponType", SHARP)):
        found = re.search(func + r"[^{]*\{\s*return \[([^\]]*)\]", text, re.S)
        if not found:
            raise SystemExit(
                f"extract_consumable_ids.py: {func} is no longer declared in "
                f"{UTILS}, so the {func} set here stands on nothing.")
        theirs = set(re.findall(r"WeaponType\.WeaponType(\w+)", found.group(1)))
        if theirs != ours:
            raise SystemExit(
                f"extract_consumable_ids.py: {func} now reads {sorted(theirs)} "
                f"and this file claims {sorted(ours)}.")


def weapon_types() -> dict:
    """Per spec, PER ANCHOR, the weapon type worn in each imbued slot.

    IT USED TO BE PER SPEC, AND THAT BROKE ON 15 AUGUST 2026. This function
    merged every anchor into one set per slot, and its own docstring said a spec
    whose anchors carry different weapon classes has no single answer and would
    be reported unresolved, adding that it did not happen. The best-in-slot
    anchor made it happen for TEN of the fourteen specs: a warlock swinging a
    dagger and a tome at entry holds a two-handed staff at best in slot, and
    both hunters change every weapon they carry.

    The consequence was not a warning. It was ten specs silently losing their
    weapon imbue in EVERY anchor, including the two that had it before, because
    an unresolved pick is not sent at all. This project has already measured
    what that costs: adding the off-hand stone both hunters were missing moved
    them 26.1 and 29.6 DPS.

    So the answer is per anchor, because the weapon is per anchor. A caller that
    wants one spec's imbue has to say which anchor it means.
    """
    if not ITEMS.is_file():
        raise SystemExit(
            f"extract_consumable_ids.py: no item table at {ITEMS}. Run "
            "`just regen`; the weapon a spec carries decides which stone it "
            "takes, and that table is where the weapon type is recorded.")
    kinds = {int(row["item_id"]): (row["weapon_type"] or "").strip()
             for row in csv.DictReader(ITEMS.open())}
    slots = {"weapon_main_hand": SLOT_ORDER.index("main_hand"),
             "weapon_off_hand": SLOT_ORDER.index("off_hand")}
    out: dict = {}
    for path in sorted(GEAR.glob("*.gear.json")):
        stem = path.name[:-len(".gear.json")]
        spec = stem.partition(".")[0].replace("-", "_")
        anchor = stem.partition(".")[2].replace("-", "_")
        items = json.loads(path.read_text())["items"]
        for field, index in slots.items():
            item_id = (items[index] or {}).get("id")
            if not item_id:
                out.setdefault(spec, {}).setdefault(anchor, {}).setdefault(
                    field, set())
                continue
            kind = kinds.get(item_id)
            if kind is None:
                raise SystemExit(
                    f"extract_consumable_ids.py: {path.name} wears item "
                    f"{item_id}, which {ITEMS} does not carry, so its weapon "
                    "class cannot be read.")
            if kind and kind not in BLUNT | SHARP | NOT_A_WEAPON:
                raise SystemExit(
                    f"extract_consumable_ids.py: {path.name} wears weapon type "
                    f"{kind!r}, which is neither blunt, sharp, nor an off-hand "
                    "item. Guessing which stone it takes is the defect this "
                    "check exists for.")
            out.setdefault(spec, {}).setdefault(anchor, {}).setdefault(
                field, set())
            if kind and kind not in NOT_A_WEAPON:
                out[spec][anchor][field].add(kind)
    return out


def hit_states() -> dict:
    """Per spec, PER ANCHOR, whether the set closes the hit gap.

    `gap_after_gems` is the rating still missing once the discretionary gems are
    spent, so zero is the "hit-capped" the guides write their food rule against.

    IT USED TO COLLAPSE EVERY ANCHOR INTO ONE ANSWER and drop the spec entirely
    where the anchors disagreed. With two anchors that was tolerable. With the
    best-in-slot anchor added it is not: four specs are short there and capped
    earlier, so collapsing would have removed the food pick from all three of
    their anchors rather than answering each one.

    THE BIS ANCHOR IS NOT IN hit-captured.yaml, deliberately. That file is the
    compendium's rollup and knows two anchors; the third carries its own
    `hit_state`, written by tools/build_bis_capture.py with the same arithmetic.
    Both are read here so this file answers for every anchor a run exists for.
    """
    if not HIT.is_file():
        raise SystemExit(
            f"extract_consumable_ids.py: no hit capture at {HIT}. Several "
            "guides make the food conditional on the hit cap, and that file is "
            "where this project records whether the cap is met.")
    out: dict = {}
    for spec, entry in (yaml.safe_load(HIT.read_text()).get("specs") or {}).items():
        for anchor, block in entry.items():
            if not isinstance(block, dict) or "gap_after_gems" not in block:
                continue
            out.setdefault(spec, {})[anchor] = \
                "capped" if block["gap_after_gems"] == 0 else "short"
    for path in sorted(BIS_CAPTURES.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text())
        state = ((doc.get("anchors") or {}).get("bis") or {}).get("hit_state")
        if not state:
            continue
        # The best-in-slot capture states the gap BEFORE gems and the count of
        # gems that close it, so the gap after gems is what remains once those
        # are spent, the same quantity hit-captured.yaml records.
        after = max(0, state.get("gap_rating", 0)
                    - state.get("gems_needed", 0) * RATING_PER_HIT_GEM)
        out.setdefault(doc["spec"], {})["bis"] = \
            "capped" if after == 0 else "short"
    return out


def windfury_specs() -> set[str]:
    """Every spec whose party carries a Windfury Totem.

    THE DEFECT THIS PREVENTS is a main-hand imbue that reads as live damage. The
    simulator applies MhImbueId only where the party Windfury Totem is Missing,
    so for these specs a correct stone and no stone at all produce the same
    number. Nothing in a run says which of the two happened.

    A SPEC IN TWO PARTIES takes both, and a totem in either is enough, because
    the run places it in one party and both of this roster's shaman parties
    carry the totem anyway.
    """
    for path in (BUFFS, ROSTER):
        if not path.is_file():
            raise SystemExit(
                f"extract_consumable_ids.py: no {path}. Which parties carry a "
                "Windfury Totem decides whether a main-hand imbue is applied "
                "at all, and guessing it would print a live pick that is inert.")
    buffs = yaml.safe_load(BUFFS.read_text())
    roster = yaml.safe_load(ROSTER.read_text())
    parties = {name for name, entry in (buffs.get("party") or {}).items()
               if (entry or {}).get("windfury_totem")}
    out = set()
    for group in roster.get("groups") or []:
        if group.get("id") in parties:
            out.update(group.get("members") or [])
    return out


def condition_of(prose: str, at: int, name: str, ends: list[int]) -> str | None:
    """Whether the clause carrying this name qualifies it on the hit cap.

    THE CLAUSE, NOT THE FIELD. Both hunters name the capped food and the
    not-capped food in one sentence, so a search across the whole field finds
    both phrases and can attribute either to either name. The window runs from
    the end of the name to the next catalog name or the end of the clause,
    whichever comes first.
    """
    start = at + len(name)
    stop = min([end for end in ends if end > start] + [len(prose)])
    window = prose[start:stop]
    for terminator in (".", ";"):
        cut = window.find(terminator)
        if cut >= 0:
            window = window[:cut]
    lowered = window.lower()
    if any(phrase in lowered for phrase in NOT_CAPPED_PHRASES):
        return "short"
    if any(phrase in lowered for phrase in CAPPED_PHRASES):
        return "capped"
    return None


def matches(prose: str, names: list[str]) -> list[tuple[int, str]]:
    """Every catalog name in this prose, earliest first, longest at a tie."""
    found = []
    for name in names:
        at = prose.find(name)
        if at >= 0:
            found.append((at, -len(name), name))
    return [(at, name) for at, _, name in sorted(found)]


def resolve(spec: str, block: dict, db: dict, imbues: dict, worn: dict,
            hit: str | None, windfury: bool) -> tuple[dict, list, list]:
    """One spec's prose, turned into picks, declines and unresolved entries.

    `worn` is the weapon class in each imbued slot, read from the captured gear,
    and `hit` is whether that spec is capped. Both are facts this repository
    already records, and both are READ here rather than answered by hand: a pick
    typed into a table cannot notice that the gear changed.
    """
    picks: dict = {}
    declined: list = []
    unresolved: list = []

    for prose_field, proto_field, want_type in WIRED:
        prose = (block.get(prose_field) or "").strip()
        source_field = prose_field
        slot_worn = worn.get(prose_field) if want_type is None else None

        # AN OFF-HAND WEAPON THE PROSE DOES NOT MENTION IS STILL SWUNG. Both
        # hunters carry Claw of the Phoenix in the off hand. Survival's prose
        # denies it outright, "not a dual-wield set", and Beast Mastery's file
        # has no off-hand field at all, so one produced a wrong answer and the
        # other produced no row and no gap to see. Where the captured gear wears
        # a weapon in a slot the prose leaves unanswered, the main-hand sentence
        # is read for that slot too: these guides name the stone for "the
        # Hunter's melee weapon" without counting them.
        overridden = None
        if (prose_field == "weapon_off_hand" and slot_worn
                and not matches(prose, list(imbues))):
            overridden = " ".join(prose.split()) or None
            prose = (block.get("weapon_main_hand") or "").strip()
            source_field = ("weapon_main_hand, because the off-hand field named "
                            "no imbue and the captured gear wears a weapon "
                            "there")
        if not prose:
            continue

        # A SLOT WITH NO WEAPON TAKES NO STONE. A caster's off hand holds a
        # tome, and ui/core/proto_utils/gear.ts::hasOHWeapon excludes it, so an
        # imbue sent for that slot is credited against nothing.
        if want_type is None and slot_worn is not None and not slot_worn:
            unresolved.append({
                "spec": spec, "prose_field": prose_field,
                "proto_field": proto_field,
                "why": "the captured gear wears no weapon in this slot, so no "
                       "imbue applies to it",
            })
            continue

        if want_type is None:
            names = list(imbues)
        else:
            names = [n for n, e in db.items() if e["type"] == want_type]
        found = matches(prose, names)
        if not found:
            unresolved.append({
                "spec": spec, "prose_field": prose_field,
                "proto_field": proto_field,
                "why": "no name in this field is in the catalog. The prose is "
                       "quoted so a reader can see whether that is a gap or a "
                       "spec with no such slot",
                "prose": " ".join(prose.split()),
            })
            continue

        # The first accepted name wins. A name the simulator reads and drops is
        # skipped rather than sent, and reported, because a sent-and-dropped id
        # produces a run that looks like it worked.
        chosen = None
        for at, name in found:
            entry = imbues[name] if want_type is None else db[name]
            if want_type is None and entry["accepted_by"] is None:
                unresolved.append({
                    "spec": spec, "prose_field": prose_field,
                    "proto_field": proto_field, "name": name,
                    "why": "the simulator does not read this value out of "
                           "ConsumesSpec, so sending it would change nothing",
                    "where_it_lives": entry["where_it_lives"],
                })
                continue
            if entry.get("duplicate_ids"):
                unresolved.append({
                    "spec": spec, "prose_field": prose_field,
                    "proto_field": proto_field, "name": name,
                    "why": f"the database holds this name twice, under ids "
                           f"{entry['duplicate_ids']}, and nothing here settles "
                           "which one the guide meant",
                })
                continue

            # THE WEAPON DECIDES THE STONE. One sentence names both stones and
            # ties each to a weapon class, so the captured weapon answers it.
            # Beast Mastery took the sharpening stone with a Fist weapon, and
            # sim/core/consumes.go gives the plus 12 ranged base damage to
            # 34340 alone, so a hunter lost the half of the stone it fires.
            classes = {"blunt" if kind in BLUNT else "sharp"
                       for kind in (slot_worn or set())}
            # A SPEC WITH NO EXPORTED GEAR IS NOT FILTERED, because there is
            # nothing to filter against. Its pick carries `unchecked` instead,
            # so a silence is never read as a check that passed.
            if slot_worn is not None and \
                    entry.get("requires") in ("blunt", "sharp") and \
                    classes != {entry["requires"]}:
                unresolved.append({
                    "spec": spec, "prose_field": prose_field,
                    "proto_field": proto_field, "name": name,
                    "why": f"this imbue applies to a {entry['requires']} "
                           f"weapon, and the captured gear carries "
                           f"{sorted(slot_worn) or 'nothing'} in this slot, "
                           f"which the simulator counts as "
                           f"{sorted(classes) or 'no weapon'}",
                })
                continue

            # THE CONDITION DECIDES THE FOOD. "Spicy Hot Talbuk if not yet
            # hit-capped, or Grilled Mudfish once hit-capped" is a rule, and a
            # resolver taking the first name takes the branch the capture rules
            # out. Both hunters close their gap at both anchors.
            condition = condition_of(prose, at, name, [a for a, _ in found])
            if condition and condition != hit:
                unresolved.append({
                    "spec": spec, "prose_field": prose_field,
                    "proto_field": proto_field, "name": name,
                    "why": f"the prose names this the {condition} pick, and "
                           f"{HIT} reports this spec "
                           + (f"{hit} at every anchor" if hit else
                              "neither capped nor short at every anchor"),
                })
                continue
            chosen = (at, name, entry, condition)
            break
        if chosen is None:
            continue

        at, name, entry, condition = chosen
        # THE WHOLE FIELD IS QUOTED, not the sentence holding the name. Half
        # these picks are conditional and the condition is usually in a
        # different sentence: the Arcane Mage's flask is named first and called
        # the situational pick two sentences later, and clipping to one sentence
        # printed a flask that read unconditional. A reader of an id needs the
        # clause that qualifies it.
        pick = {
            "name": name,
            "id": entry["id"],
            "from": source_field,
            "position": "first named in the field the captured facts allow",
            "alternatives_named": [n for _, n in found if n != name],
            "prose": " ".join(prose.split()),
        }
        # THE SENTENCE THE GEAR CONTRADICTS IS KEPT, not deleted. Survival's
        # off-hand field says the spec carries no dual-wield set and the
        # captured set carries one, so both are printed and a reader can see
        # which was believed. Deleting the losing side leaves a disagreement
        # that nobody can find again.
        if overridden:
            pick["field_prose_overridden"] = overridden
        # WHICH CAPTURED FACT CARRIED THE PICK, written beside it. A reader
        # asking why this hunter eats the agility food gets the file and the
        # figure rather than a name with no reason under it.
        if condition:
            pick["hit_cap"] = {
                "state": condition,
                "from": f"{HIT}, gap_after_gems at every anchor",
            }
        if entry.get("requires") in ("blunt", "sharp"):
            pick["weapon_class"] = {
                "worn": sorted(slot_worn) if slot_worn else [],
                "counts_as": entry["requires"],
                "from": f"{GEAR} and {ITEMS}, split by "
                        "ui/core/proto_utils/utils.ts::isBluntWeaponType",
            }
            # A SPEC WITH NO CAPTURED GEAR CANNOT BE CHECKED, and saying so is
            # the point. The tanks are out of simulation scope, so no set is
            # exported for them, and the stone below stands on the order of the
            # prose alone. It is left rather than dropped, and labelled rather
            # than left to read as verified.
            if slot_worn is None:
                pick["weapon_class"]["unchecked"] = (
                    "no gear is exported for this spec, so the weapon it "
                    "carries did not decide this stone. The prose order did")
        # CORRECT AND INERT IS A STATE, AND IT IS WRITTEN DOWN. The Fury
        # Warrior's stone was the sharp one against a Mace and was corrected to
        # the blunt one on 15 August 2026; the correction moved the result by
        # 0.0, because this spec sits under a Windfury Totem and the simulator
        # never applies the stone. Without this stamp the next reader measures
        # it, reads zero, and looks for a wrong id.
        if proto_field == "mhImbue_id" and windfury:
            pick["gate"] = {
                "applied": False,
                "why": "sim/core/consumes.go applies MhImbueId only where the "
                       "party Windfury Totem is Missing, and this spec's party "
                       "carries one",
                "party_from": str(BUFFS) + ", party.*.windfury_totem, joined to "
                              + str(ROSTER) + " groups",
                "rule_from": str(GATING),
                "so": "this id is sent and dropped. It is the right id for the "
                      "weapon and it is worth 0.0 DPS today. An off-hand imbue "
                      "is NOT gated this way and is live damage.",
            }
        picks[proto_field] = pick

    for prose_field in DECLINED:
        if (block.get(prose_field) or "").strip():
            declined.append(prose_field)
    return picks, declined, unresolved


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("data/facts/consumable-ids.yaml"))
    args = ap.parse_args()

    verify_imbues()
    verify_weapon_classes()
    db = load_db_catalog()
    worn = weapon_types()
    hit = hit_states()
    windfury = windfury_specs()
    imbues = {
        name: {"id": value, "wowsims_item_id": item_id, "ui_const": const,
               "accepted_by": accepted_by, "requires": requires,
               "where_it_lives": None if accepted_by else
               "proto/shaman.proto :: ShamanOptions.imbue_mh for the main hand "
               "and EnhancementShaman.Options.imbue_oh for the off hand, both "
               "class options rather than consumables. run_sims.py sends both "
               "there, in CLASS_OPTIONS and SPEC_OPTIONS, so the imbue is "
               "unresolved as a consumable only and is not missing from a run"}
        for name, value, item_id, const, accepted_by, requires in IMBUES
    }

    blocks = {}
    doc = yaml.safe_load(CONSUMABLES.read_text())
    for spec, entry in (doc.get("specs") or {}).items():
        blocks[spec] = entry.get("consumables") or {}
    rogue = yaml.safe_load(ROGUE.read_text())
    blocks["combat_rogue"] = rogue.get("consumables") or {}

    # DECLINED IS KEYED ON THE FIELD, NOT THE SPEC. The reason is the same for
    # all seventeen, and seventeen copies of one sentence is the second copy
    # problem this project keeps out of its fact files.
    # ONE PICK SET PER SPEC PER ANCHOR, because two of the three inputs are
    # per anchor: the weapon class decides the stone and the hit cap decides the
    # food, and both move when the gear moves. A spec with no exported gear at
    # all still gets one entry under `no_gear`, so its flask and potion are
    # resolved and the absence of a gear-dependent pick is visible rather than
    # silent.
    picks, declined, unresolved = {}, {}, []
    for spec in sorted(blocks):
        anchors = sorted(worn.get(spec) or {}) or ["no_gear"]
        for anchor in anchors:
            spec_picks, spec_declined, spec_unresolved = resolve(
                spec, blocks[spec], db, imbues,
                (worn.get(spec) or {}).get(anchor, {}),
                (hit.get(spec) or {}).get(anchor),
                spec in windfury)
            picks.setdefault(spec, {})[anchor] = spec_picks
            for entry in spec_unresolved:
                entry["anchor"] = anchor
            unresolved.extend(spec_unresolved)
            if anchor == anchors[0]:
                for prose_field in spec_declined:
                    declined.setdefault(
                        prose_field,
                        {"why": DECLINED[prose_field],
                         "specs": []})["specs"].append(spec)

    # Only the names something actually took are written out. The whole 105-row
    # database is not a fact about this raid, and copying it here would be a
    # second copy of a file that regenerates.
    taken = {p["name"] for spec in picks.values() for anchor in spec.values()
             for p in anchor.values()}
    catalog = {}
    for prose_field, proto_field, want_type in WIRED:
        if want_type is None:
            continue
        rows = {n: {"id": e["id"], "id_from": "db.json consumables[], type "
                    + CONSUMABLE_TYPE[want_type]}
                for n, e in sorted(db.items())
                if e["type"] == want_type and n in taken}
        if rows:
            catalog[proto_field] = rows
    catalog["imbue"] = {
        # THE FULL PATH, not the basename. `consumables.ts` alone reads like
        # this repository's own consumables.yaml to anyone scanning quickly.
        name: {"id": e["id"], "id_from": f"ui/core/components/inputs/"
               f"consumables.ts :: {e['ui_const']}, "
               f"accepted by {e['accepted_by']}",
               "wowsims_item_id": e["wowsims_item_id"]}
        for name, e in imbues.items()
        if name in taken and e["accepted_by"]
    }

    out = {
        "meta": {
            "what": "The simulator id behind every consumable name this project "
                    "sends, and which name each spec sends for which "
                    "ConsumesSpec field.",
            "generated_by": "tools/extract_consumable_ids.py",
            "do_not_edit": "A hand edit is lost on the next `just regen`, and "
                           "`just check` fails the build by regenerating and "
                           "diffing. Fix the prose or the transform.",
            "prose_from": [str(CONSUMABLES), str(ROGUE)],
            "ids_from": {
                "flasks, food and potions": "the `consumables` array of "
                                            "assets/database/db.json in the "
                                            "vendored wowsims-tbc-new checkout",
                "weapon imbues": "ui/core/components/inputs/consumables.ts, "
                                 "checked against the switch in "
                                 "sim/core/consumes.go and the poison ids in "
                                 "sim/rogue/poisons.go. Imbues are NOT in "
                                 "db.json; they are spell ids",
            },
            "rule": "The guides lead with the pick, so the first catalog name "
                    "in a field is taken and every later one is written out "
                    "under alternatives_named. Nothing is chosen for being "
                    "cheaper. A name the prose QUALIFIES is passed over when "
                    "the captured fact rules it out: a stone shows only on a "
                    "blunt or on a sharp weapon, and a food conditional on the "
                    "hit cap is read against gap_after_gems.",
            "conditions_read_from": {
                "the weapon a spec carries": f"{GEAR}, typed by {ITEMS} and "
                                             "split blunt from sharp by "
                                             "ui/core/proto_utils/utils.ts",
                "whether a spec is hit-capped": f"{HIT}, gap_after_gems at "
                                                "every anchor",
            },
            "main_hand_imbues_are_gated": f"{GATING}. sim/core/consumes.go "
                                          "applies a main-hand imbue only "
                                          "where the party has no Windfury "
                                          "Totem, so a pick carrying `gate` is "
                                          "sent and dropped and is worth 0.0 "
                                          "DPS. Off-hand imbues are not gated.",
            "specs": len(picks),
        },
        "catalog": catalog,
        "picks": picks,
        "declined": declined,
        "unresolved": unresolved,
    }
    args.out.write_text(yaml.safe_dump(out, sort_keys=False, width=88,
                                       allow_unicode=True))
    # COUNTED PER ANCHOR, because the picks are per anchor now. Counting per
    # spec against a two-level structure returned zero for every field and
    # printed a clean-looking summary line saying nothing was resolved.
    every = [(spec, anchor, p) for spec, anchors in picks.items()
             for anchor, p in anchors.items()]
    with_flask = sum(1 for _s, _a, p in every if "flask_id" in p)
    with_food = sum(1 for _s, _a, p in every if "food_id" in p)
    with_mh = sum(1 for _s, _a, p in every if "mhImbue_id" in p)
    with_oh = sum(1 for _s, _a, p in every if "ohImbue_id" in p)
    gated = sum(1 for _s, _a, p in every
                if "gate" in (p.get("mhImbue_id") or {}))
    print(f"wrote {args.out}: {len(picks)} spec(s) across {len(every)} anchor(s), "
          f"{with_flask} with a flask, {with_food} with food, "
          f"{with_mh} with a main-hand imbue "
          f"({gated} of them inert under the Windfury gate), "
          f"{with_oh} with an off-hand imbue, {len(unresolved)} unresolved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
