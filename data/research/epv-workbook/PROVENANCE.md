# EPV Workbook Extract

Raw capture. Do not edit these files. Corrections belong upstream with the author, or as documented overrides in `data/facts/`.

## Source

**TBC Phase 3 PVE EPV BIS LIST, Per Class**, by **Fazers** (contact `Fazers#1963` on Discord).

Published Google Sheet:
`https://docs.google.com/spreadsheets/d/e/2PACX-1vQhUJP-KpFvQwgC8DWm39laCPB-0hPcIorSy7Q3yhc12hdsD0WsC7WVi1mp6SbIIeRryMQI0qcX_z77/pubhtml`

Maintained since March 2021. Workbook last updated **23 March 2026**. Captured **8 August 2026**.

## How to re-capture

```bash
BASE="https://docs.google.com/spreadsheets/d/e/2PACX-1vQhUJP-KpFvQwgC8DWm39laCPB-0hPcIorSy7Q3yhc12hdsD0WsC7WVi1mp6SbIIeRryMQI0qcX_z77"
curl -sL "$BASE/pub?output=ods" -o workbook.ods
# then parse content.xml; one CSV per table. openpyxl is not installed;
# ODS plus xml.etree works with no dependencies.
```

The `pubhtml` endpoint returns only page chrome, not the grid. Use the `ods` export.

## Contents

27 sheets. 23 spec tabs, plus:

| Sheet | Contents |
|---|---|
| `Intro..csv` | Author's scope notes and disclaimer |
| `EPV.csv` | Master stat weights, 20 stats by 23 specs, Phase 3 |
| `Pawn.csv` | Pawn addon import strings |
| `log.csv` | Changelog since 2021 |

Each spec tab lists items per slot, ranked, with:

`rank · item name · quality · EPV · EPV if hit capped · source zone · boss · phase · Wowhead URL · per-slot stat columns`

## What it provides

The per-slot ranked lists are the **next-best-alternative ladder** across every source: raid, badge, crafted, and arena. That is the denominator of every marginal-value calculation in this project. Do not rebuild it.

## What it does not provide

Stated by the author in `Intro..csv`:

> Set bonuses are not included in any item value. It's up to you to factor them in.

Also absent, and therefore this project's job:

- Cross-spec comparison. Each tab is one spec in isolation.
- Contention mapping, sequencing, and equity.
- **Any armor or defense weight.** The master weights tab has no column for either, and Bear resilience is weighted zero. The per-item tank rows carry `def`, `dodge`, `parry` and `block`, but no weight applies to defense. The score therefore cannot express crit immunity, which is a cliff rather than a slope. A Bear geared by descending EPV rank can fall below the threshold while the sheet shows improvement. This is not a defect in the workbook, because no linear model represents a threshold. It is why the tank constraint layer sits above the scores.

## Attribution

The author's own disclaimer, carried here because it is correct and this project relies on it:

> PLEASE REMEMBER EP VALUES AND STAT WEIGHTS FLUCTUATE DEPENDING ON THE GEAR YOU HAVE. While the weights do not usually fluctuate too much, please use more as a general guide and not gospel.

If any part of this compendium is published, credit Fazers by name, link the source sheet, and mark clearly which numbers are his and which are ours. Do not redistribute the workbook itself.


## How to parse these tabs

Facts learned by parsing the workbook, recorded here because each one cost a
silent-data-loss bug to find. Any future parser needs all four.

**Tabs are identified by an explicit map, never by filename.** Two pairs carry
identical titles and only their tier pieces distinguish them.

| Tab | Title in the sheet | Actually |
|---|---|---|
| `Prot.csv` | Protection Phase 3 | Protection **Warrior** (Onslaught pieces) |
| `Tank.csv` | Protection Phase 3 | Protection **Paladin** (Lightbringer pieces) |
| `Holy.csv` | Holy Phase 3 | **Priest** healer (Absolution pieces) |
| `Heal.csv` | Holy Phase 3 | **Paladin** healer (Lightbringer pieces) |

The remaining tabs map as: Aff Affliction Warlock, Arc Arcane Mage, Arms Arms
Warrior, BM Beast Mastery Hunter, Bear Feral Bear, Cat Feral Cat, Dest
Destruction Warlock, Ele Elemental Shaman, Enh Enhancement Shaman, Fire Fire
Mage, Fury Fury Warrior, Owl Balance Druid, Resto Restoration Shaman, Ret
Retribution Paladin, Rog Combat Rogue, SV Survival Hunter, Shad Shadow Priest,
Tree Restoration Druid. `Rog_D_.csv` is a dead tab containing `#REF!` rows.

**Section headers are the slot vocabulary, and it is not what you would guess.**
The sheet uses `Head, Neck, Shoulders, Back, Chest, Wrist, Hands, Waist, Ring,
Legs, Feet, Trinket, One Hand, Two Hand, Off Hand, Main Hand, Ranged`. It is
`Shoulders` and `Ring`, not `Shoulder` and `Finger`. Guessing the wrong header
does not error: every row silently inherits the section above it, so rings file
themselves under Waist.

**Scores of 1000 and above carry a thousands separator.** A bare `float()`
raises and the row disappears without a message. This dropped 171 rows,
including every Warglaive of Azzinoth entry.

**Item ids come from the Wowhead URL column**, not from name matching. Names in
the sheet are truncated and occasionally differ from the item's real name.

**Column layout**, zero-indexed: 1 rank, 2 item name, 4 quality, 5 EPV,
6 EPV if hit capped, 7 source, 8 boss, 9 phase, 10 Wowhead URL.

## Known defects in specific tabs

Found by direct inspection of the extracted CSVs. Recorded here because
`data/facts/hit.yaml` cites them.

- **Retribution Paladin, second column.** Irregular, reaching a 199 EPV
  difference on Bulwark of Kings. Any figure taken from this column is held at
  Conservative confidence.
- **Head block, ranks 2 and 3 of the Fury Warrior tab.** The cells carry the
  strings `Yes, its that good.` and `0` rather than scores. Both rows are
  quarantined and excluded from any supplied figure.
- **Worked example for the Combat Rogue hit target.** The workbook gives 79
  with the Draenei racial and names 95 without it. Since racials are not
  assumed here, 95 is the operative number and the worked example is stale.



## The weapon sections declare their stat columns one column left of the data

Found 11 August 2026 by a per-spec audit, and confirmed on eleven of the twenty-one tabs.

In a WEAPON section the header declares `type, dps, spd, ap, str, agi` starting at one column, and every data row underneath carries an EXTRA leading cell holding the equip slot:

```
header  ... type      dps    spd   ap
data    ... One Hand  Mace   100.3 1.5
```

So a reader that trusts the header reads the weapon TYPE where it asked for dps.

**No figure in this compendium is wrong because of it.** `tools/extract_ladder.py` resolves the columns it needs by name and reaches at most column 10, the Wowhead url. Every stat published comes from `data/facts/items.csv`, keyed on the id in that url, never from the workbook's own stat columns. The EPV column, at 5, is left of the shift and unaffected, so every ranking is sound.

**What would make it live** is somebody adding `dps` or `speed` to the column map, which the header invites. `tools/check_workbook_columns.py` fails the build at that moment rather than after the figures have travelled, and `just check` runs it.
