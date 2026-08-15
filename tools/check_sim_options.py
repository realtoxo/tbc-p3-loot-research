#!/usr/bin/env python3
"""Fail the build on a class option the simulator's own preset sets and we do not.

WHY THIS EXISTS. `run_sims.py` sends a `classOptions` block per spec, and an
option absent from it does not error: it takes the proto default, and a proto
default is a zero. proto/hunter.proto defaults `pet_type` to PetNone, `ammo` to
AmmoNone and `quiver_bonus` to QuiverNone, so both hunters were simulated with
NO PET, NO AMMO AND NO QUIVER for as long as their block was empty. The run
succeeded every time. It cost Beast Mastery 1508 DPS and Survival 769, and the
guild lead found it by reading a table and saying the number looked wrong.

An audit the same day found five more: both warriors were in the wrong stance
with no starting rage, the Arcane Mage had no Mage Armor, and the Shadow Priest
opened without Shadowform, worth 74 to 181 DPS each.

WHAT IT CHECKS. Every key inside `DefaultOptions` in a spec's own presets.ts
must be either sent by run_sims.py or listed in DECLINED with a reason. It does
NOT check the VALUE, because a value we deliberately differ on is a modelling
choice this project is allowed to make and does make; it checks that no option
is missing by accident, which is the failure that does not announce itself.

Usage:
    python3 tools/check_sim_options.py
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_sims  # noqa: E402

WOWSIMS = Path(os.path.expanduser(os.environ.get(
    "WOWSIMS_TBC",
    "../tbc-phase-research-recovered/data/raw/vendor/wowsims-tbc-new-master")))

# Which preset directory each spec reads. Two specs frequently share one, which
# is why the map is per spec rather than per directory.
PRESETS = {
    "combat_rogue": "rogue/dps",
    "arms_warrior": "warrior/dps",
    "fury_warrior": "warrior/dps",
    "retribution_paladin": "paladin/retribution",
    "enhancement_shaman": "shaman/enhancement",
    "elemental_shaman": "shaman/elemental",
    "beast_mastery_hunter": "hunter/dps",
    "survival_hunter": "hunter/dps",
    "affliction_warlock": "warlock/dps",
    "destruction_warlock": "warlock/dps",
    "arcane_mage": "mage/dps",
    "balance_druid": "druid/balance",
    "shadow_priest": "priest/dps",
}

# Options the shipped preset sets and this project deliberately does not, each
# with the ruling that declined it. A key here is a DECISION and is expected to
# be argued with; a key in neither place is an accident.
DECLINED = {
    ("enhancement_shaman", "syncType"):
        "The guild lead ruled on 15 August 2026 that the Enhancement Shaman's "
        "weapons are NOT synced. The preset sets DelayOffhandSwings and it "
        "measures 16.5 DPS higher, so this is declined rather than overlooked. "
        "See tools/run_sims.py::SPEC_OPTIONS.",
    ("balance_druid", "innervateTarget"):
        "An innervate target names another player, and this project simulates "
        "one player alone. raid-buffs.yaml sets innervates to 0 for the same "
        "reason, so a target would point at nobody.",
}


def shipped_options(path: Path) -> set[str]:
    """The classOptions keys a preset sets, read from its own presets.ts."""
    text = path.read_text()
    match = re.search(
        r"export const DefaultOptions\s*=\s*\w+\.create\(\{(.*?)\n\}\);",
        text, re.S)
    if not match:
        return set()
    block = match.group(1)
    # `classOptions: { ... }` plus anything the preset sets BESIDE it, which is
    # how the Enhancement Shaman's off-hand imbue and sync type are written.
    return {key for key in re.findall(r"^\s*(\w+):", block, re.M)
            if key != "classOptions"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()

    if not (WOWSIMS / "ui").is_dir():
        print(f"error: no simulator checkout at {WOWSIMS}. Set WOWSIMS_TBC.",
              file=sys.stderr)
        return 1

    failures: list[str] = []
    checked = 0
    for spec, ui in sorted(PRESETS.items()):
        path = WOWSIMS / "ui" / ui / "presets.ts"
        if not path.is_file():
            failures.append(f"{spec}: no presets at {path}")
            continue
        checked += 1
        wanted = shipped_options(path)
        ours = set(run_sims.CLASS_OPTIONS.get(spec, {})) \
            | set(run_sims.SPEC_OPTIONS.get(spec, {}))
        for key in sorted(wanted - ours):
            if (spec, key) in DECLINED:
                continue
            failures.append(
                f"{spec}: the shipped preset at ui/{ui}/presets.ts sets "
                f"`{key}` and run_sims.py sends neither it nor a reason for "
                "declining it. An unsent option takes the proto default, which "
                "is a zero, and the run SUCCEEDS with a smaller number.")

    declined = len(DECLINED)
    print(f"sim options: {checked} preset(s) checked, {declined} option(s) "
          "declined with a stated reason")
    for (spec, key), why in sorted(DECLINED.items()):
        print(f"  declined {spec}.{key}: {why.split('.')[0]}.")
    if failures:
        print(f"\n{len(failures)} failure(s):", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
