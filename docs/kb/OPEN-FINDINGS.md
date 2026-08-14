# Open Findings

**STATUS, 9 August 2026: fifteen of sixteen findings were remediated, and an independent judge caught the sixteenth still open after this header claimed otherwise.** The Priest "only spec whose first token is free" entry was declared fixed and was not; it is fixed now, and the header that overstated it is the reason this line reads the way it does. A status line is a claim like any other. The
sections below are kept as the record of what was found and why, because the
reasoning outlives the fix. Three needed a ruling from the guild lead and got
one: the Arms Warrior takes Flurry, the Retribution Paladin is not an engineer,
and the roster groups stand as discussed.

**RE-VERIFIED 13 AUGUST 2026: nothing is open.** All seventeen findings were
checked against the current files and every one had already been settled by
corrections that landed after the sweep. The list was never updated when they
did, so it presented settled work as outstanding for four days, which is the
same failure the paragraph above describes. One new defect surfaced during the
re-verification and is fixed; it is recorded with the others.

Findings from the 9 August 2026 defect sweep for claims stated more strongly than what they rest on. This file answers "what did the sweep find and what would settle each item"; it does not answer what any item is worth or who should receive it, and nothing here is a priority. Line numbers were read on 9 August 2026 while other corrections were landing, so verify each against the current file before acting.

Every entry states whether settling it needs a decision from the guild lead, because a per-player or per-roster fact cannot be settled by any source.

## Resolved during the sweep

These are recorded because the reasoning is the useful part, not the outcome.

1. **Warrior Precision: the finding was wrong and checking it mattered.** The sweep claimed Precision sits at Fury tier 5 needing 20 points, which would have cut the Arms net hit target from 142 to 95 and flipped every Arms anchor from short to full. The simulator talent tree places Precision at `rowIdx: 6`, the seventh row, needing 30 points, and the 2.4.3 tooltip endpoint returns three ranks at 1, 2 and 3 percent. [`hit.yaml`](../../data/facts/hit.yaml) was right and the target stays 142. The lesson: a cap-moving correction is verified against the primary source before anything moves, because a false fix here routes every hit off-piece wrongly.
2. **Arms and Flurry: the same check found a real defect one row down.** `crit.yaml` said Arms cannot reach Flurry "for the same tier reason hit.yaml gives for Precision". Flurry is `rowIdx: 5`, 25 points, so a 33/28/0 build spending 28 in Fury does reach it. [`haste.yaml`](../../data/facts/haste.yaml) already recorded the question honestly as NOT VERIFIED, and `crit.yaml` now matches it. Two files held two positions and the honest one was not the one being read. Whether this roster's Arms Warrior actually takes Flurry is a per-player fact: **guild lead needed** before any figure credits it.
3. **`docs/framework.md` per-spec figures: fixed structurally.** Every per-spec figure the sweep flagged as stale was stale, and none was wrong when written; the captures behind them were repaired four more times after the document was updated once. The document now states the mechanism and points at [`hit-captured.yaml`](../../data/facts/hit-captured.yaml). A governing document that quotes a moving figure goes stale on every repair, so it now quotes none.
4. **The stray "Held at Priority 2" in [`priorities.yaml`](../../data/judgments/priorities.yaml): removed.** It contradicted the file's own ruling that no priority is set anywhere.

## Handled but unsettled

**Ranged attack power per agility, [`attack-power.yaml`](../../data/facts/attack-power.yaml).** The sweep claimed the file grants 1 ranged attack power per agility to all nine classes when only Hunter, Rogue and Warrior convert. The counter-claim could not be verified either, so no figure changed; the file's confidence now names exactly which part is unverified. What would settle it: the 2.4.3 class pages or the simulator's per-class `agility_to_rap` coefficients, read per class rather than as one rule. Routing weight is low because only the Hunters price ranged attack power. Guild lead needed: no.

## Open

**NOTHING IN THIS SECTION IS OPEN. Re-verified 13 August 2026, all seventeen against the current files, and every one had already been settled by the corrections that landed after the sweep.** The section was never updated when they landed, so it went on presenting settled work as outstanding for four days. That is the failure this file warns about in its own header: a status line is a claim like any other, and a stale open list is worse than no list, because it sends a reader to re-fix what is fixed and lends the settled items a doubt they have not earned.

The findings are kept below with what settles each, because the reasoning outlives the fix.

### Would change a routing decision: eight, all settled

| Finding | What settles it |
|---|---|
| `hit.yaml` misquoted its own tank captures | `hit.yaml` near line 467 now records both corrections and what they were: the Protection Warrior reads 156 where it read 192, the Protection Paladin 42 where it read 81 |
| Crit headroom did not state its basis | `crit.yaml` near line 536 states the rule as `white_cap` minus `sheet_crit` minus 4.8, and says the column is the same on either basis once one side is adjusted. Near line 557 the "26 points" sentence is retracted |
| Token claimants counted 19 in the document and 21 in the data | `docs/framework.md` near line 250 recounts from `spec_to_set` to 7, 8 and 6, names the two lines it had undercounted, and near line 300 reads twenty-one |
| The Retribution verdict collapsed two tokens into one | `token-verdicts.yaml` near line 137 splits it: hands a raw stat downgrade, head a raw stat upgrade. The engineering condition is discharged, not carried: **the guild lead confirmed on 13 August 2026, restating 9 August, that this roster's Retribution Paladin is not an engineer** |
| The Priest uniqueness claim contradicted its neighbours | `token-verdicts.yaml` near line 108 retracts "the only spec whose FIRST token is free" and quotes what it retracted |
| The Balance verdict stated unconditionally what its fact stated conditionally | `token-verdicts.yaml` near line 48 carries the composition condition into the verdict, and near line 63 records the unconditional wording it replaced |
| The Wildfury commentary claimed hit the Bear capture does not hold | The note is scoped to the Cat, and the Cat capture wears the weapon at all three anchors at 18 hit. The Bear capture reads hit 0 and no longer has a claim resting on it |
| Predatory Strikes was recorded without its third rank | `attack-power.yaml` near line 231 carries all three spell ids at 50, 100 and 150 percent. The two suspected companions are also resolved: Trueshot Aura near line 133 carries four ranks and cites the fourth at 125, and Greatstaff of the Leviathan near line 187 carries item id 27757 |

### Would not change a routing decision: nine, all settled

| Finding | What settles it |
|---|---|
| Base miss stated two ways | `hit.yaml` near line 227 retracts 8.6 as a wiki-era figure and names it as retracted |
| Two spell hit targets differed by one point | Every net spell target now reads 165; no 164 survives |
| `set-stats.yaml` counted six disagreeing specs against a disclosure naming three | The claim is gone from the file; `tools/check_token_arithmetic.py` is the arbiter and runs in `just check` |
| Resolved entries sat under `open_questions` | `tokens.yaml` carries eight open questions and none of them is marked `resolved` or `superseded_by` |
| The `conventions.md` inventory restated and undercounted | `docs/conventions.md` links `data/facts/PROVENANCE.md` instead of restating it, and records why the copy was removed |
| The chest turn-in was counted across three sets | `docs/framework.md` near line 310 reads six sets across three classes, and names the miscount it replaced |
| Roster spec naming drifted and two tanks sat in no group | `tools/check_roster.py` passes: five groups, twenty-five slots placed, counts and the shaman constraint agreeing. `feral_druid` survives only in the comment recording the rename and in one count key where it names both Feral specs together, which is what that key counts |
| Rounding applied silently in two places | `hit.yaml` near line 206 states the rule with its arithmetic, 3 times 15.77 equals 47.31 credited at 48, every net target the ceiling. `haste.yaml` near line 66 derives 788 the same way |
| The Warglaive commentary was pinned to one id | `field-commentary.yaml` near line 131 carries an explicit ID SCOPE line naming the main hand as 32837 and the off hand as 32838 |

### One defect found while re-verifying, and fixed

**Merciless Gladiator's Maul was recorded as Arena Season 3 gear.** It is Season 2. `field-commentary.yaml` entry `fc-006` carried the wrong season in the note that scopes the Feral Cat's entry weapon.

It matters because of a rule this project already holds: `docs/kb/DOMAIN.md` records Season 3 as opening 1 September 2026, five days after Phase 3, so Season 3 gear is barred from an entry anchor. Read as written, the note barred the weapon the Feral Cat capture actually walks in holding at every anchor, and it is the source of the 18 hit the Cat's entry figures rest on. `tools/extract_ladder.py` had the seasons right the whole time, deduplicating Vengeful as `season3` and Merciless as `season2`, so no published figure moved; only the prose was wrong. Corrected 13 August 2026, with the previous claim quoted.

## The tier-set rebuild, attempted and reverted, 14 August 2026

**A rebuild of all seventeen tier sets was applied, reviewed by seventeen Opus
agents, and reverted the same night on the guild lead's instruction.** The gear
it produced was right. What it did not touch was every word written about that
gear, and the review returned 96 findings across all 17 specs.

THE RULE IT IMPLEMENTED, which still stands and is worth keeping. A tier set is
the entry set with only the five token slots reconsidered: take a tier token the
spec's Wowhead Phase 3 best-in-slot list puts there, from ANY tier; otherwise
keep the entry item unless it is a tier piece whose set bonus no longer holds, in
which case take the best off-piece the workbook ranks.

WHAT IT GOT RIGHT. Token counts matched the seventeen extracted Phase 3 lists
spec for spec: five for the Feral Bear, four for most, three for the warlocks,
one for the Protection Warrior, and none for the Enhancement Shaman or the
Retribution Paladin, whose lists wear no tier at all. It also removed the defect
that started it, the orphaned Tier 4 Voidheart Mantle on the Affliction Warlock.

WHY IT WAS REVERTED. The data moved and the prose did not, so roughly 74 of the
96 findings were fact files contradicting themselves:

  - Affliction's note still said Mantle of the Malefic "is not available, so
    Voidheart Mantle is carried forward", beside a file holding the Malefic.
  - Protection Warrior's note named item 30111 as Destroyer Legguards from Shade
    of Akama. Wrong item, wrong boss.
  - Feral Bear's crit-immunity note quoted defense totals from the old set, and
    that note feeds a TANK SURVIVABILITY claim.
  - Card footnotes read "Tier rows assume both reachable tokens", false for the
    four specs that ended with one or none.
  - token-arithmetic.yaml, crit.yaml's retraction block, hit-captured.yaml's
    contested text and the sim gear files all still described the old sets.

TWO THINGS THE REVERT DID NOT RESOLVE, and they were true before the rebuild too.

  1. THE ORPHANS ARE STILL THERE. Six tier pieces are worn at a tier anchor for
     no set bonus, and the workbook ranks a better off-piece for four of them.
     The Affliction Warlock's Voidheart Mantle is the case the guild lead found:
     rank 6, EPV 84.72 and 14 hit, against Blood-cursed Shoulderpads at rank 2,
     98.08 and 18 hit. Worse on both counts, and the Destruction Warlock, same
     class and same gear pool, already wears the Blood-cursed.

  2. NOTHING CAN CATCH A TIER PIECE FROM AN OUT-OF-WINDOW BOSS.
     `check_capture_availability.py` resolves an item's boss through
     `drops.csv`, and a tier piece is a vendor purchase with no row there. The
     shoulder, legs and chest tokens come from Mother Shahraz, the Illidari
     Council and Illidan, which `progression.yaml` places out of reach, and a
     capture could wear one today without any check noticing.

WHAT A SECOND ATTEMPT MUST DO IN ONE PASS. Rebuild the sets, strip or rewrite
every note that describes the old ones, refresh token-arithmetic and the sim
gear files, fix the card footnote, and settle what `progression.yaml` means now
that the guild lead has ruled the tier set does not respect the window. The
seventeen Phase 3 best-in-slot lists are captured and do not need re-reading.


## The tier-set rebuild, second attempt, 14 August 2026: landed, NOT verified

The rebuild is on `main` at 8292f10 and is **not published**. `gh-pages` remains
on f84406d. A second seventeen-agent Opus review took the findings from 96 to
54, with two specs clean, and the remaining 21 routing findings are real. Do not
publish until they are settled.

WHAT THE SECOND PASS FIXED. The prose moved with the data: 37 note keys retired
under `notes_from_the_previous_construction` behind a header, the card footnote
"Tier rows assume both reachable tokens" removed from 243 places, and
`progression.yaml` told what it now governs.

### Three defects in the rebuild itself

**THE ORPHAN REPLACEMENT HAS NO AVAILABILITY FILTER.** Rule 2 replaces an
orphaned tier piece with the highest-EPV off-piece the workbook ranks, and
nothing stops that being an Illidan drop. Cursed Vision of Sargeras (32235)
landed in the Combat Rogue, Beast Mastery Hunter and Protection Paladin head
slots. AGENTS.md bars Illidan, Mother Shahraz, the Illidari Council and Arena
Season 3 from EVERY anchor, and that rule is separate from the progression
window the guild lead set aside. The replacement must be filtered.

**ONE PHASE 3 LIST WAS EXTRACTED WRONG.** The Protection Warrior's shoulder was
captured as Onslaught Shoulderblades, item 30979, which is `Onslaught
Battlegear`, the DPS set: 0 defense, 39 strength. The tank set is `Onslaught
Armor`. A tank guide does not recommend it, so the extractor took a row from the
wrong table. `check_tank_defense` still passes because the defense shortfall
sits inside the gem and enchant budget, so nothing caught it. EVERY captured
list needs re-checking against the spec's own set before the rebuild is trusted.

**A DERIVED FIELD WAS NOT RECOMPUTED.** The Protection Paladin tier anchor
carries `total_item_spell_hit: 17` while no item in the set has any spell hit.
The rebuild recomputed `total_item_hit` and missed its sibling, and the stale 17
has already reached hit-captured.yaml and the spell line derived from it.

### Two things that are contested rather than wrong

**TIER TOKENS FROM OUT-OF-WINDOW BOSSES.** Eight specs wear a shoulder, chest or
legs token from Mother Shahraz, the Illidari Council or Illidan. That follows
directly from the guild lead's rule and his ruling that progression does not
constrain the tier set. It is recorded, not a defect. Note it sits uneasily
beside the AGENTS.md rule above, which bars those bosses at any anchor: the two
rules now disagree and one of them has to give.

**THE ARCANE MAGE'S ORPHANED LEGS.** Leggings of the Tempest sits alone in
Tempest Regalia, buys no bonus, and the workbook ranks Leggings of Channeled
Elements above it, 94.31 to 92.97. Rule 1 took it because the Phase 3 list
chose it, and rule 2 does not test a rule 1 pick. Working as specified, and
worth a ruling.

### Still stale

Contested-token sentences printed on Arms Warrior, Balance Druid and Feral Cat
cards describe token configurations the rebuilt sets no longer hold. The Arms
Warrior one repeats a claim already retracted in token-arithmetic.yaml: it says
the head token costs the Destroyer four-piece when that capture holds two
Destroyer pieces. The string is hardcoded in tools/extract_hit_captures.py and
so bypasses tools/check_token_arithmetic.py entirely.


## Swept and found clean

Token to slot to boss for all 45 tokens; set bonus verbatim text across files; the conversion constants; the 490, 415, 332, 284 and 102.4 tank thresholds; expertise caps; the generated table counts against `PROVENANCE.md`; `docs/bosses.md` against `drops.csv`; every EPV figure in `docs/conventions.md` against the workbook; `docs/kb/DOMAIN.md`; `enchants-gems.yaml` era claims; all item id and name pairs in the captures; the schedule dates; and `just check` passes.

## Still open, and none of it is a defect

**The plate tanks sit in no group.** `roster.yaml` enumerates g1 and g2, holding
the nine melee and hunter specs. The Protection Warrior, the Protection Paladin
and the four healers appear in no group, so this file credits them no group
buff. Nothing reads a tank's group today, so no figure moves; it would the
moment a group buff entered a tank's cap arithmetic. Placements are a roster
fact. **Guild lead needed.**

**No simulation has been run at our gear anchors, and no set bonus has ever been priced.** This entry used to say no simulation had ever been run, and an independent judge caught that as too strong: [`crit.yaml`](../../data/facts/crit.yaml) records four raid-buffed crit percentages from a wowsims run against **that engine's own** presets, single-source and flagged uncorroborated. What is missing is a run at OUR anchors, which `sim-profiles.yaml` records as `specs_collected: 0`, and a price for a set bonus, which [`token-arithmetic.yaml`](../../data/facts/sim-profiles/token-arithmetic.yaml) says no source gives. The set bonus is the term in dispute in every token question this sweep touched: the Retribution head, the Balance four-piece, the Rogue's Deathmantle against Slayer's. Reading more published lists cannot settle it. **Guild lead needed.**

**110 off-piece divergences remain open** in [`open-divergences.yaml`](../../data/facts/sim-profiles/hit-capture-review/open-divergences.yaml), each with what would settle it. Of the original 132, twenty-two were worked on 9 August 2026: the material ones at delta 20 and above, excluding every weapon and ranged slot, because the workbook's own author marks the off-hand hit column wrong and the largest deltas in the whole set sit there. The remainder are two sources disagreeing rather than errors, and how far to go is a scope decision. **Guild lead needed.**

**Ranged attack power per agility** stays unverified for seven classes, with the
confidence lowered to say so. It drives no call: only the hunters price the
stat, and the sweep agreed hunters convert.

## Relics have no claimant, because eleven workbook tabs carry no relic section

**Found 11 August 2026, by cross-checking the claimant list against the creator commentary (task 66). Needs a ruling from the guild lead.**

A spec earns a claimant card where the item ranks inside its slot section on that spec's workbook tab. Eleven of the twenty-one tabs have no `Ranged` section at all: both feral specs, the Balance and Restoration Druid, all three Paladins, all three Shamans, and the Priest Healer. Those are exactly the classes whose relic slot holds an idol, a totem or a libram.

The consequence is that a relic can reach the compendium with no claimant at all. Three Phase 3 relic drops carry none: **Idol of the White Stag**, **Totem of Ancestral Guidance** and **Tome of the Lightbringer**. Each is class-locked to a spec that plainly wants it, and each renders as an item nobody claims.

The creator commentary is what surfaced it. Creators name the Feral Cat for the Idol and the Elemental Shaman for the Totem, and neither spec appears on the page, which is the mismatch that led here rather than any figure being wrong.

**Nothing here says the rule is wrong.** The workbook is the published reference and the compendium reports it faithfully; Fazers simply does not rank relics for those classes. What the guild lead has to decide is whether a class-locked relic earns a claimant from its class allowlist rather than from a workbook rank, which is a different rule from the one every other slot uses and would be the first place the two diverge.

**Also found, and NOT the same thing.** Twenty items have a creator naming a spec the page does not list. One is a mis-scoped remark: `Bracers of the Pathfinder` is mail and a creator discussed it for the Combat Rogue. The rest are items the spec could equip and the workbook ranks below the cut, which is the workbook and the creators disagreeing rather than a defect. Disagreement is recorded rather than resolved.

## The per-spec claimant audit, 11 August 2026

All fourteen specs that have a capture were audited, one Opus agent each, comparing the EP ladder against the captured published gear set slot by slot. The four healers have no capture and were not audited: Holy Paladin, Priest Healer, Restoration Druid and Restoration Shaman.

**The per-spec reports were not retained**, which is the same failure this project already records for `token-arithmetic.yaml`: figures standing on agent reports nobody kept. What survives is this section and the commits it names. Any figure below that is not reproducible from a file in this repository should be treated as unsourced. Two findings need a ruling from the guild lead. The rest are recorded so they are not rediscovered.

### Arena Season 3 in the delta baselines: SETTLED 12 August 2026

**Season 3 weapons stay in the delta baselines.** Ruled by the guild lead. A weapon card compares weapons inside the tier, and an arena weapon is part of that field whether or not the season has opened, because a council weighing a drop is weighing it against what the slot will hold.

What was resolved with it: the clones. The Vengeful and Merciless sets are one stat block sold in several weapon flavours, so eleven baseline cells had held two of them and offered the same weapon twice. Each season now contributes one comparison, and a weapon card carries a Season 3 column and a Season 2 column of its own.

The tension this section originally recorded is therefore closed rather than open. `check_capture_availability.py` still bars Season 3 from every captured GEAR SET, and that is a different question from what a card compares against: a capture states what a raider holds at an anchor, and a baseline states what the item is measured against. The two rules disagreeing was the finding; the ruling is that they are answering different questions and both stand.

### A class-locked relic can have no claimant, and the cause is not per spec

Confirmed independently three times. Eleven of the twenty-one workbook tabs carry no `Ranged` section: both feral specs, the Balance and Restoration Druid, all three Paladins, all three Shamans and the Priest Healer. Three Phase 3 relics therefore reach the compendium with zero claimants, and they are half of the six pages in `docs/items/` with none.

The effect data settles who the claimants would be, where the ladder cannot:

| Relic | id | Claimant, from `item-effects.csv` |
|---|---|---|
| Idol of the White Stag | 32257 | Feral Cat and Feral Bear. Buff 41037 is a Mangle attack power buff, and Mangle is a Feral ability |
| Totem of Ancestral Guidance | 32330 | Elemental Shaman. Buff 41040 is the Increased Lightning Damage family, the same line as Totem of the Void which its capture wears at entry. Enhancement is arguable and unsupported; Restoration is excluded, its relic line is the healing family |
| Tome of the Lightbringer | 32368 | A Paladin relic, by the same class lock |

**Needs a ruling, and it is a real one.** It would create the first claimant not derived from a workbook rank, which changes the model the compendium states about itself, and rendering "no claimant, class locked" is an equally defensible answer. One correction to the framing: `class_allowlist` is EMPTY in `items.csv` for all three relics, so a rule phrased on the allowlist names data that does not exist. The lock is carried by `ranged_weapon_type`, 6, 7 and 8, plus the domain truth in DOMAIN.md. Ruling yes therefore needs a relic-type to class mapping recorded first. The Tome row is also settled by its effect rather than by the allowlist: buff 41042 is Judgement Block Value, which needs a shield and so names the Protection Paladin rather than any paladin. That is a different rule from the one every other slot uses, and it is the first place the two sources would diverge by design.

### Recorded, needing no ruling

**Wolfshead Helm misses the shortlist by one row.** `Cat.csv` ranks it FIRST in the Head section at 0.00 EPV with the author's note "Yes, its that good", because the item is owned by a mechanic a stat ladder cannot price. Sorting by EPV puts it last of eleven eligible rows and the cut takes ten. It is also phase 0, so it belongs to neither the `phase3` nor the `prephase` cell and can never be a baseline. It is absent from `items.csv` as well, because the simulator database does not hold it, so surfacing it would reach an item with no stat line. Three independent obstacles, not one.

**Three captures are self referential and are not independent checks.** `feral-bear.yaml` cites this repository's own fact files. `feral-cat.yaml` cites the EP workbook, which is the same source the ladder reads. `shadow-priest.yaml` cites Wowhead for its entry anchor but the workbook for both tier anchors, because no Phase 3 guide page could be read. An audit of the ladder against any of those three at a tier anchor compares the workbook with itself.

**A single-candidate `phase3` cell drops that column on the item's own page.** Seen on Balance Druid, Protection Paladin, Shadow Priest, Feral Cat and Elemental Shaman. The two-candidate rule exists so a card never compares an item with itself, and where a tab ranks only one non-tier Phase 3 item in a slot there is no legal second. The card states the absence rather than inventing a comparison. No Net is wrong; a column is missing.

**Every tank Net is offense only, and this depends on neither ruling.** All three tanks convert agility, melee crit, melee hit, spell crit, spell hit and strength and no defensive stat, so defense, dodge, parry, block, armor and stamina print as raw rows and never reach the Net. The conversions needed to change that are now recorded at `data/facts/crit.yaml::defensive_conversions`. What a tank Net should SAY is a modelling choice and is unmade.

**The two repaired Combat Rogue off-hand cards still carry Season 3 baselines**, so fixing the hand did not remove the other problem from the same cards.

**The Rogue tab has no `Off Hand` section and the Fury tab has no `Two Hand` section.** The first caused the hand-type defect fixed in `50652f1`. The second is consistent with a spec that dual wields.

## No healer Net contains a healer stat, and one figure in it is unusable

**Found 11 August 2026 by a Fable agent on the Restoration Shaman, then verified directly for all four healers. Needs a ruling from the guild lead, and it is the same ruling the tanks need.**

`theme/filters/conversions.generated.lua` converts, for Holy Paladin, Priest Healer, Restoration Druid and Restoration Shaman alike: `melee_crit`, `melee_hit`, `spell_crit`, `spell_hit` and `strength`. `delta.lua` prints in the Net only what those rules convert into. So a healer card's Net can hold attack power, melee crit, melee hit, spell crit and spell hit.

**Of those, one is useful to a healer and one is actively wrong.**

- **Spell crit** is the single healer-relevant unit, and it is weak: a critical heal lands at 1.5 times rather than 2, per `crit.yaml::crit_multipliers.healing`.
- **Spell hit prints, and healing cannot miss.** `hit.yaml` records the Restoration Shaman as `not_applicable` for exactly that reason. So the Net states a percentage of a stat the spec has no use for.
- Attack power, melee crit and melee hit are noise on a healer card.

**Every stat a healer is actually priced on passes through as a raw row and never reaches the Net**: healing power, mana per five, intellect, spirit and spell haste rating.

The sharpest form of the gap is that the compendium already holds a conversion it declines to apply. `crit.yaml::conversions.intellect_per_percent_spell_crit_level_70` records 80 intellect per 1 percent for every caster and says in its own note that it "is recorded because it prices the intellect on a caster item". No rule uses it.

**Why nothing caught this.** No healer has a captured gear set, healers are out of the sim scope by ruling, and no Phase 3 Holy Paladin recording exists. A healer conversion has therefore never been checked against a capture, a simulation or a creator. The simulator could not have caught it either: the vendored wowsims shaman healing file is `sim/shaman/_heals.go`, and Go excludes a file whose name begins with an underscore, so that code never compiles.

### What was established for the Restoration Shaman, and what it needs

Sourced, with the constant and the file named: spell crit 22.076923 per percent and spell haste 15.76923 per percent from `sim/core/base_stats_auto_gen.go`; mana per five paying at all times and spirit paying only outside the five-second rule, from `sim/core/mana.go`; intellect at 15 mana per point above the first 20 and 0.0125 percent spell crit per point, which is the 80 already recorded.

**The five-second rule is the part that decides a shaman's longevity, and it is not recorded anywhere in this project.** No shaman talent in 2.4.3 lets spirit regenerate while casting; `SpiritRegenRateCasting` is set by the Priest and the Druid and by nothing in `sim/shaman/`. So a Restoration Shaman who is actively healing gets no mana at all from spirit, which is why mana per five and not spirit is that spec's longevity stat.

Two Restoration talents that would matter, **Purification** and **Nature's Blessing**, are implemented nowhere in the checkout and appear in no fact file, so their values are unsourced. `talents.yaml` omits Restoration Shaman entirely, so no rank is recorded for any of them.

## Does every spec have a meaningful delta area? Measured 12 August 2026

**Yes for every damage spec and every tank. No for the healers, and that is now by ruling rather than by oversight.**

Measured from `theme/filters/ladder.generated.lua` and the 288 built pages.

**Baseline coverage is sound everywhere.** Across all 21 specs, **no delta slot carries fewer than two baseline views**. By median views per slot the specs split three ways: four specs at two, four at three and thirteen at four. An earlier version of this section said "two for the two-hand specs and four for the rest", which a Fable review disproved by recomputing it.

An earlier reading of the same data also appeared to show Ring and Shoulders thin for all 21 specs. That was a parse conflating the shortlist block with the delta block, and it is recorded here as wrong so nobody repeats it. There is no systematically thin slot.

**109 of 856 spec cards render a delta table with no Net line.** The decomposition below was corrected on 12 August 2026 after a Fable review recomputed it; the first version said "about 100 plus 2", which does not reach 109.

- **101 are healer cards.** Healing power, mana per five, intellect, spirit and spell haste do not convert, so nothing reaches the Net. The guild lead ruled on 12 August 2026 that healer stats are out of scope, so these cards state their comparison without summarising it, which is honest rather than wrong. The full analysis is in the section above.
- **Seven are relic cards** held by non-healer specs: Idol of the White Stag for the Feral Bear, Feral Cat and Balance Druid; Tome of the Lightbringer for the Retribution and Protection Paladin; Totem of Ancestral Guidance for the Elemental and Enhancement Shaman. A relic carries no stat line, so there is nothing to net. The healer specs on those same three pages are counted in the 101 above.
- **One is Madness of the Betrayer for the Feral Bear**, and it is the only one of the three groups that a decision created. That trinket carries no primary stat, and the tank Net was narrowed to primary stats on 12 August 2026, so the card lost its Net. It is worth knowing about before anyone reads a blank Net there as an error.

**573 of 856 cards state at least one absent comparison.** That is the designed behaviour rather than a gap: a slot outside the five a tier set covers has no Tier 6 or Tier 5 view to show, and the card says so instead of leaving a blank column.

So the remaining work on this question is not per spec. It is the single decision about what a healer card should summarise, which the guild lead has ruled out of scope.
