---
title: Conventions
eyebrow: Reference
subtitle: >-
  The vocabulary this compendium uses. Every term here has one meaning across
  every document; if a document uses one of these words differently, the
  document is wrong.
status: draft
updated: 2026-08-08
---

This page defines terms. It does not argue for any of them; the reasoning lives in the [Framework](framework.md), and the numbers live in the fact files below.

## Where the facts live

Every figure this compendium quotes comes from a file under `data/facts/`. The inventory of those files, what each one holds, how it was produced and whether `just regen` overwrites it, lives in [`data/facts/PROVENANCE.md`](../data/facts/PROVENANCE.md) and is not restated here. A copy of that table used to sit on this page and did what a second copy does: it went stale, listing nine files where the inventory holds fifteen, so the rule below was being asserted over an incomplete list. Each fact file states its own scope, sources and open questions at the top, and none of them evaluates anything.

**A stat is only in one file.** Hit is not in `crit.yaml` and crit is not in `hit.yaml`, so a figure has one home and a disagreement between two files is a defect rather than a difference of opinion.

## Vocabulary

Which words carry a fixed technical meaning, and what each one means.

| Term | Meaning |
|---|---|
| **Spec** | A class and talent configuration, such as Feral Bear or Combat Rogue. The claiming entity. Every standing and every comparison in this compendium is per spec. If the raid runs two players of one spec, which of them receives an item is a council judgment, not something this compendium models. |
| **Claimant** | A spec with a real case for an item. Armor type is a ceiling rather than a match, so it excludes little; stat relevance does the filtering. |
| **Standing** | What an item is to a spec, on the two-level scale below: BIS or Upgrade. Derived from the simulated sets and the claimant rule, never judged per item. |
| **Blocker** | A specific, named reason a tier piece cannot or should not be equipped yet, such as an active set bonus it would break. |
| **Gear anchor** | A defined gear baseline that our own simulator runs are executed at. Three are used per spec: **Entry**, the best gear a raider can hold before this raid opens, with no Tier 6 in it; **Tier**, that same gear with only the five tier token slots reconsidered; and **BiS**, the full Phase 3 best-in-slot set. Cards spell these out rather than naming them. Which specs are run at which, and the figures, are in [Simulated Throughput](sims.md). |
| **Rank-unstable** | An item whose standing changes between gear anchors. Its ordering is provisional, and it moves as the raid gears up. |

## Standing: BIS and Upgrade

A spec either has a claim on an item or it does not, and every claim carries one of two standings. The scale replaced the earlier four-step priority scale on 20 August 2026, when the simulated best-in-slot sets became measured and ruling-complete, because a derived label the whole pipeline enforces beats a judged one the council had to maintain.

| Standing | Meaning | Where it comes from |
|---|---|---|
| **BIS** | The spec's best-in-slot simulated set wears this item. | Derived from the spec's best-in-slot profile, which carries every routing ruling and every measured revision. |
| **Upgrade** | The spec is a claimant on the item, and its best-in-slot set does not wear it. | Derived from the claimant rule: the shortlist rank, a class-locked relic or reputation lock, or a shared weapon set. |

No claim means no standing. That covers two situations and the reason says which: the stats do nothing for the spec, or something the spec already holds is better. Both end with the spec not receiving the item.

A spec without a simulated best-in-slot set labels nothing BIS. The tanks, the healers and the Feral Cat have no such profile, so every claim those specs hold renders as an Upgrade, and that is a statement about what this compendium has measured rather than about the item.

The standing says what an item IS to a spec. It does not say who receives a contested drop first: that ordering is the council's, and where the council has settled one it lives in the judgment store with its reasons.

Set bonuses do not enter here. Whether a piece would break a set the spec is completing is a question about tier progress and it is answered in [Tier sets and set bonuses](framework.md#tier-sets-and-set-bonuses), not by lowering an item's standing.

**Every claim carries the size of the upgrade, in both forms.** The raw change and the change as a percentage of what that spec already produces, measured against the named alternative rather than against nothing. Why both are required, and what each form is biased toward alone, is argued once, in [the framework's Inputs section](framework.md#inputs).

### Worked example

The item under discussion is [Cursed Vision of Sargeras]{.item}, and it heads the container the cards sit in. Its stat line, its sockets and the boss it drops from are printed there once, read from [`items.csv`](../data/facts/items.csv) and [`drops.csv`](../data/facts/drops.csv), so no figure about the item is written into this prose, where it would go stale.

Armor type is a ceiling rather than a match, so every class above leather can physically equip this. That is not what decides the standing. What decides it is what the spec is actually choosing between, and that is derived rather than chosen by an author.

One card per claimant. Each leads with its **Standing**, BIS or Upgrade on the scale above, derived from the simulated sets rather than written here. Below it sits a **Delta**: what the spec gains by taking this item, with every stat converted at that spec's own rates and each rate linked to the file it came from. Everything on a card is real, because everything on a card is derived.

A card used to carry a written **For** and **Against** pair as well, arguing both sides of the item for that spec. The pair was filled in for one item only, this one, and the guild lead removed it on 10 August 2026. What sits above the cards instead is what creators actually said about the item, with a timestamp on each remark, which covers 173 items rather than one.

**What the Delta compares against.** Four baselines, all derived, and one table carrying all four. They sit on a two by two: one axis is the phase, this phase against the phase before it, and the other is the tier piece against the best item that is not tier.

| | Tier piece | Best off-piece |
|---|---|---|
| **This phase** | The spec's Tier 6 piece for the slot | The best Phase 3 item for the slot that belongs to no tier set |
| **Pre-phase** | The spec's Tier 5 piece for the slot | The best Phase 1 or 2 item for the slot that belongs to no tier set |

The stats that differ are the rows, each named once on the left, and each baseline is a pair of columns holding its raw change and that change converted. Rows line up across the baselines because they are rows of one table, so a reader reads `agility` across four answers on one line. The Net line runs along the bottom, one figure per line per baseline, and the conversion rates are printed once under the table, because a rate belongs to the spec and not to the baseline.

This table answers which baseline each pair of columns measures against, and in the order the card prints them.

| Label | What it measures | Where it comes from |
|---|---|---|
| **Over Tier 6** | Set progress, against the piece the spec gives up to equip this one | The spec's own Tier 6 set in [`tokens.yaml`](../data/facts/tokens.yaml), and the piece that set lists for the slot |
| **Over best Phase 3 off-piece** | The competition inside this phase, against the strongest thing in the slot that costs no token | The highest-EPV item in the slot whose EP Workbook Phase column reads 3 and whose id is in no tier set in [`tokens.yaml`](../data/facts/tokens.yaml). The route is the EP Workbook's own `Location` column |
| **Over Tier 5** | The realistic upgrade, against the head most of the roster wears into the phase. A raider obtains a Tier 5 piece by raiding, so this baseline is always reachable | The spec's own Tier 5 set in [`tokens.yaml`](../data/facts/tokens.yaml), and the piece that set lists for the slot |
| **Over best pre-phase off-piece** | The off-piece a raider carries in, which is frequently one the raider cannot obtain, so the route is named on the label | The highest-EPV item in the slot whose EP Workbook Phase column reads 1 or 2 and whose id is in no tier set. Selected the same way as the Phase 3 off-piece |

**Why the middle view was split in two.** There used to be one **Over best available** view, the highest-EPV Phase 1 or 2 item, tier or not. It overlapped **Over Tier 5**, because a Tier 5 piece is a Phase 2 item, and for four of these eight cards the two resolved to the same item and collapsed into one column. Two categories that are not disjoint produce a collapse that reads as informative and is a defect. Excluding tier from both off-piece cells, and adding the phase axis, makes the four disjoint, so no two derived baselines can resolve to one item.

**The Phase 3 off-piece column is the one the cards were missing.** On six of these eight cards it beats the spec's own tier head. `Forest Prowler's Helm` is 292.48 against `Gronnstalker's Helmet` at 257.63 for the Beast Mastery Hunter, 477.00 against 449.63 for the Survival Hunter, and 291.23 against 289.76 for the Enhancement Shaman, so one Black Temple mail helm is contested by three specs at once. `Helm of the Illidari Shatterer` beats `Onslaught Battle-Helm` for both warriors here, and it beats `Lightbringer War-Helm` for the Retribution Paladin, who carries no card on this page. The Combat Rogue and the Feral Bear are the two whose tier head wins.

**Which items are tier is never a name test.** It is the item ids in [`tokens.yaml`](../data/facts/tokens.yaml), read from `spec_to_set` and the set piece lists. A filter written on names returns `Cursed Vision of Sargeras` as the best non-tier head, which is the item under discussion.

**The route is on the label because the best item in a slot is frequently one a raider cannot obtain.** On this worked example the best pre-phase off-piece is `Deathblow X11 Goggles` for the Combat Rogue and both feral druids, `Furious Gizmatic Goggles` for both warriors, `Surestrike Goggles v2.0` for the Beast Mastery Hunter and the Enhancement Shaman, and `Mask of the Deceiver` for the Survival Hunter. The goggles are engineering and the mask costs badges. A rogue who is not an engineer measured against a helm he cannot get is a comparison that reads as a ruling and is not one, which is why the route is printed on every label, gated or not.

**Arena armor is not a baseline, and arena weapons are.** Ruled on 9 August 2026. A resilience-bearing armor piece is not what a raider gears into, so measuring a raid drop against one asks the council to compare a piece the roster neither holds nor wants. A weapon is the opposite case: it carries no armor to distort the comparison, and for several specs an arena weapon is the best thing available in the slot. The exclusion runs before the candidates are ranked, so the next item that is not arena takes the column. Where nothing else exists the card says so rather than showing three columns beside a neighbor's four, and on this worked example the Combat Rogue and both feral druids say it: outside their tier sets and outside arena, no other Phase 3 head competes with this one at all.

Four routes are distinguished, because four is what changes a raider's answer: crafted or profession-gated, arena, badge, and a drop, which is everything else. The `Location` string itself is printed rather than a bucket name, so `Engineering`, `Season 2` and `Serpentshrine Cavern` each say where the EP Workbook read it from. A gated label is set in the caution tone as well, at 4.6:1 on light and 6.2:1 on dark against the head it sits on.

None of the four is picked by hand, so no card can quietly answer a different question from its neighbor. The item under discussion is excluded from every baseline, or a card would compare an item with itself: `Cursed Vision of Sargeras` is the top Phase 3 head on all eight of these spec tabs, so each off-piece cell holds two ranked candidates and the card takes the first that is not the item on it. A slot outside the five a tier set covers, such as Neck or Trinket, has no tier baseline in either tier, so the two tier cells can never fill and the card is topped up instead, as the next paragraph states. A slot with no non-tier item in one of the two phase groups, a spec missing a tier piece for one of the five slots a set does cover, or a spec whose EP Workbook cannot be read, stops the build naming the spec and the slot.

**An off-piece card is topped up to four baselines.** Ruled by the guild lead on 14 August 2026. Neck, Back, Wrist, Waist, Feet, Ring and Trinket hold no tier piece, so those cards carried two column groups beside a four-column neighbor and a reader counts columns before reading labels. The two rules above are applied first and nothing they select is displaced. The remaining columns are then filled from the best items of that slot across every phase, tier excluded exactly as the two off-piece cells exclude it, best first, skipping the item under discussion and skipping every item another column already holds. Each added column is labelled **Over next best off-piece** and carries its route and its EPV like any other. Fewer than four is still a legitimate outcome where the EP Workbook ranks too few items in the slot, and a top-up column that cannot fill says nothing, because a shortage of ranked items is not the absence of a named comparison. Ranged is not topped up, because the ruling named the jewelry and the armor off-pieces.

**What influencers say appears only where something is captured.** An item page carries that section when a creator or a class community has been recorded saying something about the item, and omits it entirely otherwise. Its absence means nothing has been captured, not that nothing has been said. The section used to print "Nothing captured for this item yet" so silence could not be mistaken for consensus, and with commentary recorded for a handful of items that line appeared on 173 of 177 pages, which teaches a reader to skip the section on the few where it carries something. Coverage is no longer a handful: 580 remarks are captured across 173 items, and a page shows up to five of them, widest reach first, with every stance represented so a lone objection is not crowded out.

The views answer differently often enough to be worth all of them. The Combat Rogue wears `Deathmantle Helm` into the phase, holds `Slayer's Helm` after it, and only reaches `Deathblow X11 Goggles` with a profession, so its column groups are three different arguments and its fourth is the finding that nothing else in the slot competes.

:::: {.subject}

[Cursed Vision of Sargeras]{.item}

::: {.commentary}

[Cursed Vision of Sargeras]{.item}

:::

::: {.specs}

#### Combat Rogue


Delta
:   [Cursed Vision of Sargeras]{.item}



#### Feral Cat


Delta
:   [Cursed Vision of Sargeras]{.item}



#### Feral Bear



Delta
:   [Cursed Vision of Sargeras]{.item}



#### Fury Warrior


Delta
:   [Cursed Vision of Sargeras]{.item}



#### Arms Warrior


Delta
:   [Cursed Vision of Sargeras]{.item}



#### Beast Mastery Hunter


Delta
:   [Cursed Vision of Sargeras]{.item}



#### Survival Hunter


Delta
:   [Cursed Vision of Sargeras]{.item}



#### Enhancement Shaman


Delta
:   [Cursed Vision of Sargeras]{.item}



:::

::::

The two warriors carry negative rows in both of their tables, and in both cases those negatives are most of the answer.

The two hunters are the pair to read twice. They share both tier sets and the same Phase 3 off-piece, so three of their four column groups hold the same figures, and everything that separates one hunter's claim from the other sits in the pre-phase off-piece and in how much hit each of them still needs. That view is gated for both of them, on an engineering goggle for Beast Mastery and on a badge purchase for Survival, which is exactly the case the route label exists to show: the same drop reads as a different upgrade for each, and neither raider is certain to hold the item being compared against.

The Rogue and the Cat sitting at the same standing is the normal case, not a failure to decide: which of the two receives it is the council's judgment, and the reasons are what that judgment is made from.

What is real here: every standing, every stat line, every delta table, every conversion rate, every cap figure, and all four derived baselines and their acquisition routes on every card, taken from the best-in-slot captures in `data/facts/sim-profiles/`, `data/facts/items.csv`, `data/facts/hit.yaml`, `data/facts/crit.yaml`, `data/facts/attack-power.yaml`, `data/facts/tokens.yaml` and the EP Workbook in `data/research/epv-workbook/`. Every creator remark is real and carries a link to the second it was said. Nothing on a card is illustrative, because nothing on a card is judged: who receives a contested drop first remains the council's call, and it is not printed here.

Throughput figures are absent from these cards by choice. A card previously led with a line like "plus 41 damage per second", which had no source at the time. Simulated figures now exist, in [Simulated Throughput](sims.md), and they are not restated on a card: a card compares one item against a baseline, and a simulated figure is a whole set against an encounter.

The pattern each reason follows: state the constraint the spec is under, name the gear that constraint is measured in and what the numbers mean for the spec, show the delta, then argue both directions and land. A reason that only argues one way is not finished.

### The same pair, read by two specs

The Feral Cat card carries a `Delta`, and the table under it is what makes the card checkable. In the **Over Tier 6** columns, the tier helm's 53 strength is 106 attack power for a feral druid against this item's 108, so the net across the whole piece is two attack power and the real difference is crit. That is invisible in the raw stat lines and it is one row of the table.

A conversion rate is not a constant. It differs by class, and for a druid it differs by form, so the same two items read differently for two specs that contest them. The block below pins both sides on purpose, which is what the `A over B` form is for: the EP Workbook gives the Cat and the Bear different pre-phase off-pieces, and a derived comparison would put the two specs on different pairs and hide the one difference this is meant to show.

::: {.delta}

Feral Cat
:   [Thunderheart Cover]{.item} over [Nordrassil Headdress]{.item}

Feral Bear
:   [Thunderheart Cover]{.item} over [Nordrassil Headdress]{.item}

:::

Strength converts the same way for both, at two attack power per point in every form. Agility does not: Cat Form reads "40 plus Agility" and Bear Form names a flat figure and no stat term, so the six agility is six attack power for the Cat and none for the Bear. Both still buy the same crit from it. Every rate under a table names the fact file and the key it was read from, so a figure can be checked without leaving the page.

