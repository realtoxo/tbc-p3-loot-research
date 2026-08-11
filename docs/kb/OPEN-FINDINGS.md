# Open Findings

**STATUS, 9 August 2026: fifteen of sixteen findings were remediated, and an independent judge caught the sixteenth still open after this header claimed otherwise.** The Priest "only spec whose first token is free" entry was declared fixed and was not; it is fixed now, and the header that overstated it is the reason this line reads the way it does. A status line is a claim like any other. The
sections below are kept as the record of what was found and why, because the
reasoning outlives the fix. Three needed a ruling from the guild lead and got
one: the Arms Warrior takes Flurry, the Retribution Paladin is not an engineer,
and the roster groups stand as discussed. What remains open is listed at the
foot of this file.

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

Each entry carries the claim, the contradiction, the sweep's confidence, whether it would change a loot routing decision, what would settle it, and whether the guild lead is needed.

### Would change a routing decision

- **`hit.yaml` misquotes its own captures.** [`hit.yaml`](../../data/facts/hit.yaml) near line 420 says the captures give the Protection Warrior "87 rising to 192" and the Protection Paladin "15 rising to 81". The capture files state 105 rising to 156 and 15 rising to 42. CONFIRMED. Routing: yes, both tanks' claims on hit off-pieces rest on these. Settle: reread the three capture totals and restate, or replace the quoted figures with a pointer to `hit-captured.yaml`, which is the fix `docs/framework.md` already took. Guild lead: no.
- **Crit headroom figures do not follow the file's own comparison rule.** [`crit.yaml`](../../data/facts/crit.yaml) near line 484 rules that sheet crit and effective caps differ by 4.8 points and one side must be adjusted before comparing. The headroom column near line 524 and the prose "about 11 points" near line 1187 do not state which basis they used, and recomputing on either basis gives a different figure. The file's own note that applying the rule "widens every distance" is honest; the printed numbers still do not reconcile. CONFIRMED for the arithmetic. The companion sentence near line 2291 generalises "headroom is 11 to 26 points" from four simulated specs to the roster; SUSPECTED for the specs never measured. Routing: yes, near-cap crit awards for Fury and Combat. Settle: recompute the column stating the basis, and scope the sentence to the four measured specs or measure the rest. Guild lead: no.
- **Token line claimant counts are 19 in the governing document and 21 in the data.** [`docs/framework.md`](../framework.md) near line 252 tables Conqueror 6, Protector 7, Vanquisher 6, and near line 298 says "one ranking of nineteen specs", while the same document near line 310 and `spec_to_set` plus `set_claimants_by_tier` in [`tokens.yaml`](../../data/facts/tokens.yaml) give 7, 8 and 6, which is 21. CONFIRMED. Routing: yes, line crowding is the document's own wait-time argument. Settle: recount from `spec_to_set` and state which specs each line holds. Guild lead: no.
- **The Priest uniqueness claim contradicts its neighbours.** [`token-verdicts.yaml`](../../data/judgments/token-verdicts.yaml) near line 92 calls the Priest healer "the only spec whose FIRST token is free" while the same file records the Protection Paladin's first token as free near line 96 and the Combat Rogue as a clean gain. CONFIRMED. Routing: yes, "only" is a funnel-ordering argument. Settle: define free, recount across all entries, and drop or scope the word. Guild lead: no.
- **The Retribution verdict collapses two tokens into one.** `token-verdicts.yaml` near line 114 reads "token is a raw stat downgrade", singular, while [`token-arithmetic.yaml`](../../data/facts/sim-profiles/token-arithmetic.yaml) near line 146 records the hands as a downgrade and the head as an upgrade for a non-engineer, a downgrade only for an engineer. CONFIRMED. Routing: yes, it decides whether the Retribution Paladin claims the head token at all. Settle: split the verdict per token and attach the engineering condition. Whether this roster's Retribution Paladin is an engineer is a per-player fact: **guild lead needed**.
- **The Balance verdict states unconditionally what its fact states conditionally.** `token-verdicts.yaml` near line 47 reads "either one breaks the Tier 5 four-piece" with no condition, while `token-arithmetic.yaml` near line 204 now names the composition the claim depends on and instructs the reader to check it against the capture. CONFIRMED, narrow. Routing: yes, it is the cost side of both Balance token claims. Settle: carry the condition into the verdict card, and confirm the Balance capture holds exactly head, shoulder, chest and hands of Tier 5. Guild lead: no for the capture check; yes if the question becomes what the player actually wears.
- **The Wildfury commentary claims hit the Bear capture does not hold.** [`field-commentary.yaml`](../../data/facts/field-commentary.yaml) near line 156 says the weapon "carries the 18 hit that the Bear and Cat entry figures depend on", while the Feral Bear capture records its Wildfury row at hit 0. CONFIRMED for the Bear. Routing: yes, it colours staff routing between the Bear and the Cat. Settle: read both captures' weapon rows and restate per spec. Guild lead: no.
- **Predatory Strikes is recorded without its third rank.** `attack-power.yaml` near line 222 states "50 to 100 percent of level" for a talent whose 2.4.3 ranks are 50, 100 and 150 percent. CONFIRMED against the rank list; verify the ceiling at the tooltip endpoint before editing. The Trueshot Aura value of 50 near line 133 cites one spell id where the aura has ranks; SUSPECTED. `Greatstaff of the Leviathan` near line 182 is cited by name with no id, which is the dispositioned-on-a-name shape; SUSPECTED. Routing: yes for Predatory Strikes, it feeds every Cat and Bear attack power conversion. Settle: resolve each spell and item id at the 2.4.3 tooltip endpoint and record the id beside the name. Guild lead: no.

### Would not change a routing decision

- **Base miss is stated two ways.** `hit.yaml` near line 204 asserts 8.6 percent base miss; `crit.yaml` near line 190 measures 8.0 and near line 184 explicitly rejects 8.6. Both files gear to the same 9 percent cap, so no target moves. CONFIRMED. Settle: one file owns the figure and the other links, per the one-home rule in [`docs/conventions.md`](../conventions.md). Guild lead: no.
- **Two spell hit targets differ by one point.** `hit.yaml` near line 953 records a net spell target of 164 and near line 1071 a net target of 165 for what reads as the same quantity. SUSPECTED, the two entries may credit different debuffs. Settle: recompute both from the stated buff lists in one pass. Guild lead: no.
- **`set-stats.yaml` counts six disagreeing specs; the disclosure names three.** [`set-stats.yaml`](../../data/facts/set-stats.yaml) near line 27 says `token-arithmetic.yaml` "disagrees for six specs" while the disclosure in that file names three. SUSPECTED, the checker the disclosure cites is the arbiter. Settle: run `tools/check_token_arithmetic.py` and state the count it reports. Guild lead: no.
- **Resolved entries still sit under `open_questions`.** `tokens.yaml` near lines 2291 and 2304 carries entries marked `resolved:` and `superseded_by:` inside the open questions block. CONFIRMED. Settle: move them to a resolved block so the open list is the open list. Guild lead: no.
- **The `conventions.md` fact-file inventory restates and undercounts.** [`docs/conventions.md`](../conventions.md) near line 18 lists nine fact files where [`data/facts/PROVENANCE.md`](../../data/facts/PROVENANCE.md) inventories fifteen, so "a figure has one home" is asserted over an incomplete inventory. CONFIRMED. Settle: link the inventory instead of restating it, per the never-state-a-fact-twice rule in `AGENTS.md`. Guild lead: no.
- **The chest turn-in is counted across three sets, not six.** `docs/framework.md` near line 308 says the Conqueror chest token exchanges "for six different chest pieces across three sets"; the six pieces belong to six sets across three classes. CONFIRMED. Settle: recount from the vendor block in `tokens.yaml`. Guild lead: no.
- **Roster spec naming drifts and two tanks are in no group.** [`roster.yaml`](../../data/facts/roster.yaml) near lines 50 and 117 uses `feral_druid`, a name no other file holds, and the Protection Warrior and Protection Paladin appear in no group despite the file's rule that anything claiming a priority appears there. CONFIRMED. Group membership decides which group buffs are credited, so this can graduate to routing-relevant. Settle: rename to the shared vocabulary and complete the groups. Actual party assignments are a roster fact: **guild lead needed**.
- **Rounding is applied silently in two places.** Improved Faerie Fire is credited at 48 rating where 3 percent converts to 47.31, and the haste floor is stated at 788 rating where 50 percent converts to 788.5. SUSPECTED, both may be deliberate ceiling rounding. Settle: state the rounding rule once beside the conversion constants. Guild lead: no.
- **The Warglaive commentary is pinned to one id.** The field commentary attaches to item 32837, the main hand, with nothing recording whether it covers the pair. SUSPECTED. Settle: read the captured commentary and attach it to both ids or state the scope. Guild lead: no.

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

### Arena Season 3 sits in the delta baselines, and our own rules bar it everywhere else

Sixteen distinct Season 3 items appear in the generated ladder. `tools/check_capture_availability.py` excludes every one of them from every anchor, because Season 3 opens on 1 September and Phase 3 on 27 August, and several captures record removing a Season 3 item for exactly that reason. The baselines still use them, so a card can measure an item against gear no raider can hold in this phase.

Four independent agents found this without prompting: Balance Druid, Protection Paladin, Feral Cat and Shadow Priest. It is not confined to one slot or one spec.

**This is a contradiction between two of our own rules rather than a mistake.** The guild lead ruled that arena armor is out and arena weapons are in, recorded at `data/judgments/capture-fidelity.yaml`. That ruling did not distinguish Season 2, which is obtainable, from Season 3, which is not obtainable at launch. The shortlists were resolved separately in August by taking obtainable items first; the baselines were not touched.

**Needs a ruling, and the record already leans one way.** `data/judgments/capture-fidelity.yaml` states inside the same entry that Season 3 is a separate and stricter matter and that no Season 3 item is reachable at any anchor, armor or weapon. The recorded reason for admitting arena weapons is that such a weapon is a genuine competitor and often the best thing available in the slot, which a Vengeful weapon is not inside this phase window. So every recorded fact points at exclusion, and what needs the guild lead is narrowing his own recorded judgment rather than settling an open question. Correction to an earlier draft of this section: the ruling DID distinguish the seasons for anchors; what it did not do is carry that distinction into the baselines. Every agent that examined a weapon slot named a reachable replacement, usually Hammer of Judgement, id 34009, and each stated which direction the Net moves. Nothing is changed until this is decided.

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
