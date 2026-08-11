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
