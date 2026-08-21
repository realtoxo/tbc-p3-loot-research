---
title: Framework
eyebrow: Method
subtitle: >-
  How a loot decision is reached: the inputs, the considerations, and the order
  in which they win when they disagree. This is the governing document. Every
  other document must trace its method back to a section here.
status: review
updated: 2026-08-08
---

Every policy document in this compendium builds on the method below.

## Mission

Produce the loot council decision system for Mount Hyjal and Black Temple in TBC Anniversary Phase 3.

**How it is used.** The council reviews this compendium as a group, discusses the conclusions it reaches, and works out a decision path from them in advance. It is not consulted at the moment a drop happens. That is why every conclusion travels with its basis: the basis is what the group argues about, and the argument happens before the raid rather than during it.

The unit of output is a **standing**: what an item is to a spec, BIS where the spec's simulated best-in-slot set wears it and Upgrade where the spec is a claimant without wearing it there, with the reasoning that produced the underlying sets. A standing is derived from the simulated profiles and the claimant rule rather than judged per item, so it is checked by rerunning the pipeline, and who receives a contested drop FIRST remains the council's judgment, recorded in the judgment store with its reasons. The scale, and a worked example, are in [Conventions](conventions.md#standing-bis-and-upgrade).

The design intent follows from that. Give a clear answer, and show enough of its basis that the council can test it. A conclusion with no answer is useless; an answer with no basis cannot be argued with, only accepted or discarded. Both fail.

This is not a personal best-in-slot list, and it is not a gear optimizer. Published lists and stat weights already rank items within a spec, and this project consumes them rather than competing with them. It holds best in slot as reference data so the council can anticipate what a player expects, and it never lets that reference decide a priority. Whether those sources agree with each other, or with our own runs, is an open question.

## Scope

The question this project answers is not "is this item best in slot?" It is "what does the raid lose by giving this item here instead of there, and in what order should items flow?"

| Included | Not included |
|---|---|
| Mount Hyjal and Black Temple boss and trash loot | A gear optimizer or a character planner |
| Best in slot per spec, as reference data | Best in slot as an input to any priority |
| Tier 6 tokens, set bonus routing, and set bonus blockers | Shadow resistance gearing (excluded by decision) |
| Off-piece routing and cross-spec contention | A gear optimizer or character planner |
| Weapons, trinkets, and Warglaive routing | Per-player gear tracking |
| Badge of Justice substitution and crafted alternatives | Full profession economy planning |
| Optimal placement ordering across raid weeks | A replacement for attendance and performance judgment |
| Equitable access measurement | Encounter strategy or raid composition guides |

## Fixed Assumptions

These assumptions travel with every figure in this compendium. A conclusion is only valid under the assumptions that produced it.

| Assumption | Value |
|---|---|
| Content | Mount Hyjal and Black Temple, TBC Anniversary Edition |
| Phase 3 launch | 27 August 2026 |
| Arena Season 3 launch | 1 September 2026, five days after Phase 3 |
| Launch-week PvP baseline | Season 2. Season 3 is not available in the first lockout |
| Faction | Alliance |
| Racial buffs | **Not assumed.** No Heroic Presence, no Inspiring Presence. Every spec budgets hit from gear alone, which raises hit requirements by roughly one percent against a source that assumes a Draenei in each party |
| Group buffs | Assumed, per the group assignments in `data/facts/roster.yaml` |
| Longevity horizon | Through Sunwell Plateau, Phase 5 |
| Raid size | 25 |
| Roster model | Spec-based, not player-named |
| Tank corps | Druid main tank, Paladin off-tank, Druid third tank, Warrior fourth tank |
| Warglaive claimants | Both a Combat Rogue and a Fury Warrior are present |
| Support coverage | Buff-maximizing; every spec represented |
| Shadow resistance | Out of scope |
| Consumables in our own sims | **Fully applied.** Flask or the appropriate elixir pair, food, weapon enhancement such as an oil, stone or poison, and scrolls where a spec uses them |
| Enchants and gems in our own sims | **Fully applied**, at the best available choice for that spec, in every socket and every enchantable slot |

Our own runs model a raider who is fully prepared, because that is the state an item is actually used in. An unconsumed, unenchanted profile misprices haste and crit against a spec's real breakpoints and understates what the raid loses by routing a drop badly.

::: {.note}
**This is deliberately the opposite of how cap state is computed.** [`hit.yaml`](../data/facts/hit.yaml) sets `consumables_assumed` and `gems_and_enchants_counted` to false, so that a spec called short is short **on gear**, which is a claim on loot, rather than short because a player skipped a flask, which is not. The two settings answer different questions and must not be reconciled by changing either one. A sim result is what a prepared raider produces; a cap state is what the gear alone supplies.
:::

::: {.note .veto}
**The tank corps is the assumption that changes the most conclusions.** A Bear main tank is not a cosmetic variation: it moves the crit-immunity threshold from 490 defense skill to 415, it puts no plate or shield on the main tank, and it makes leather with high armor contested between the main tank and the third tank. Conclusions drawn for a Warrior main tank do not transfer.
:::

## Analytical Approach By Area

No scoring formula is fixed here, deliberately. The inputs are both quantitative (simulator output, stat weights, cap arithmetic) and qualitative (longevity, contention, set-bonus timing, what the field does). The output is a judgment the council reaches from those facts together. A formula that turned them into one number would hide the judgment rather than remove it, and would be argued with on its arithmetic instead of its reasoning. Collect the facts first; decide how to weigh them when the council can see what there is to weigh.

### Inputs

No single source is authoritative. Four independent inputs feed the valuation, and where they disagree the disagreement is recorded rather than averaged away.

| Input | What it supplies | Standing |
|---|---|---|
| **Published EP Workbook** | Per-slot ranked item lists for every spec, across raid, badge, crafted and arena sources. The alternative EP Workbook comes from here. | Broadest coverage, static weights, set bonuses excluded by its author's design |
| **Class community weights** | Stat weights and community best-in-slot lists maintained by each class community, most of them living in class Discords rather than on any website. Retrieved manually and imported with their stated gear baseline | Informational. Used to see what a spec believes and to assemble gear sets in Sixty Upgrades, not as an input to any figure we derive. Closest to current play, but quality varies by class and the baseline must be recorded per source. A Discord source cannot be linked or re-fetched, so the capture records the server, the channel, the author and the date, and the retrieved text is kept verbatim in `data/research/` |
| **Guides and field commentary** | Two kinds. Broad tier-wide guides from well-known content creators, which cover the whole phase in one consistent voice and are usually the most reliable of the two. And class-specific guides, which carry per-item reasoning no table can hold | Explains mechanisms; never moves a number on its own. Class-specific coverage is spotty in both availability and quality: some specs have nothing current, and a guide written by an author who plays the spec it covers is not an independent source for it. Record the author and the date with every claim taken from one, and treat a claim that flatters the author's own spec as needing a second source |
| **Our own simulator runs** | Custom runs configured for our actual raid environment: real buff set, our comp, our fight lengths, both gear anchors | The only input we control end to end, and the only one that reflects this raid rather than a generic one |

The fourth matters most where the others are weakest, and where loot is most contested. Published weights assume a generic raid; ours are built on the buffs, comp and fight lengths this guild actually fields, which is exactly what shifts a spec's cap position. Contention compounds this. An uncontested item can rest on a published list without anyone minding, but a contested one is where a conclusion gets challenged, and a challenge is answerable only if the numbers behind it were built on this raid rather than a generic one.

The inputs supply weights. They do not supply a baseline to derive them at, so we add one.

**A shared gear baseline, for our own simulator runs.** These three variants are the gear configurations our own runs are executed at. They are the specification a simulator profile is built from, and they do not apply to the imported inputs, which arrive with whatever baseline their author chose. Weights are derived at Phase 3 entry rather than at full Tier 6, because rulings happen while raiders wear Phase 2 gear and weights derived at best-in-slot price a margin nobody is standing on. Thirteen of the twenty-one rostered specs are run at all three, and which are absent and why is on [Simulated Throughput](sims.md). Any item whose priority moves between anchors is flagged rank-unstable.

| Variant | Gear | What it exists to catch |
|---|---|---|
| **Entry** | Phase 3 entry gear, no Tier 6 | What a spec is worth on the day the raid opens, which is when most rulings are made |
| **Tier** | A set a player could hold four to six weeks in: the Tier 6 pieces reachable by then, worn beside the early Hyjal and Black Temple off-pieces a raid has actually collected. | Mid-tier itemization shifts. Tier 6 changes a spec's cap position, and a weight derived only at entry is blind to that |
| **BiS** | The full Phase 3 best-in-slot set, every slot, with the guild lead's weapon and trinket routing applied where a published list gives a spec something this raid will not | What a spec is worth fully geared, which is what the Tier variant cannot show because its weapons and trinkets are still the entry ones |

An earlier version of this anchor was deliberately tier-only, on the reasoning that a hit-heavy off-piece would hide the tier set's own effect. That rule is retired. It answered a real question, but it put five Tier 6 pieces on a character who can reach two, so it described nobody. The isolated comparison is still recorded, labelled as retired, in `data/facts/hit.yaml`.

**Every run records both the absolute change and the proportional one.** Absolute change is what the raid gains: so many points of damage per second, healing per second, or effective health. Proportional change is that same result divided by what the spec was already producing at the same variant, expressed as a percentage of itself.

Both are recorded because each is biased on its own, in opposite directions.

- **Absolute change alone always favors whoever already does the most.** A flat gain of 40 damage per second is the same number whether it lands on the top parser or the bottom one, so ordering claims by raw gain routes every contested item to the same handful of specs. Applied across a phase that is not a loot policy, it is a loot funnel, and it is also wrong on its own terms: the carry is the spec whose gear is already best, so it is where added stats do the least additional work.
- **Proportional change alone flatters low-throughput specs.** A five percent gain on a small number is still a small number of points to the raid. A spec can show the largest percentage in the room and still be the wrong place to put the item.

So the two travel together and answer different questions. Absolute says what the raid gains this phase, and it is the only one of the two that says that. Proportional says how much the item changes that spec against itself, which is what makes the same raw number transformative for one player and routine for another. A percentage is comparable between two specs as impact and as equity, and it is not a proxy for raid gain, because the same percentage of two different outputs is two different numbers of points. Neither figure is used alone, and neither orders claims across roles.

### The buff baseline

Alongside the gear anchors, this is the other half of the simulator profile. Every number our own runs produce depends on which buffs the raid is assumed to have, so the buff list in a run configuration comes from here rather than from a simulator default. A run configured against a different buff set is not comparable to anything else in this compendium. Change anything here and the numbers downstream change with it.

The composition it derives from is `data/facts/roster.yaml`.

**What is assumed.** The racial and group buff states are the ones the [Fixed Assumptions](#fixed-assumptions) table records, and they are not restated here. Two rows are specific to this baseline:

| Assumption | State | Effect |
|---|---|---|
| Improved Faerie Fire | Assumed | Supplied by the Balance Druid. A raid-wide three percent **physical** hit debuff, worth 48 hit rating |
| Weapons at entry | Season 2 or better | The floor a weapon claim is measured against. Season 3 weapons are part of this tier and belong in the comparison set, but are not assumed owned, because the guild does not expect every player to run arena for the current season |

### Best in slot, as reference rather than input

Players care about best in slot, so the council has to know what each spec's community considers best in slot. That knowledge is carried as **reference data attached to the item, and it never feeds a priority.**

The reason to hold it is anticipation. A player who has read a best-in-slot list arrives expecting a specific item. When a conclusion runs against that expectation, the council should know which expectations it is contradicting while it is still deciding, rather than afterwards.

What each source is for.

| Source | Use |
|---|---|
| The EP Workbook | Rank one at a time within a spec, which is a usable proxy for best in slot |
| Wowhead per-spec lists | Cross-check, and the published expectation many players actually read |
| Class community lists | The most reliable statement of what a spec believes, and the place trinket choice is genuinely argued |

Two rules keep this from leaking into decisions. A best-in-slot entry is never a reason for a priority, because best in slot for one player says nothing about what the raid loses by routing the item elsewhere. And where a priority rules against a spec's stated best in slot, the priority says so in its reason, so the conflict is on the page rather than in someone's head.

### Cap state and stat valuation

A stat weight is only true at a given cap position. The same item is worth very different amounts to two specs that sit on opposite sides of a cap, and that difference is invisible in a ranked list.

This is what turns a generic weight into a claim about our raid. The mechanics are held per spec in three files, split by stat so that a file name states which mechanism is inside it:

| File | Holds |
|---|---|
| [`data/facts/hit.yaml`](../data/facts/hit.yaml) | The four hit caps, expertise against boss dodge and parry, the talents and buffs supplying them, and each spec's position |
| [`data/facts/crit.yaml`](../data/facts/crit.yaml) | The melee attack table and the crit cap it produces, the spell and ranged cases, and the tank thresholds: crit immunity and uncrushable |
| [`data/facts/haste.yaml`](../data/facts/haste.yaml) | Conversions, the global cooldown floor, which thresholds are real in 2.4.3, and where haste does nothing |

Each carries its own scope, sources and open questions at the top. For each spec we record the following at both gear anchors.

**No simulator run has produced any figure in this section.** Every figure below comes from captured gear lists joined to the item table. Simulated figures do exist, for thirteen specs at three gear anchors against each Phase 3 boss armor tier, and they live in [Simulated Throughput](sims.md) and `data/facts/sim-figures.yaml`. The two are kept apart because they answer different questions: a cap state here is what a published gear list carries, and a figure there is what a spec measures wearing it.

| Recorded | Why |
|---|---|
| Which caps apply | Melee hit and expertise, spell hit, defense for the tanks, and any talent or racial that lowers them. Haste is recorded here too, though it caps differently: see below |
| Position at each anchor | What the gear actually supplies. At Entry that is the set a player walks in with. At Tier it is a set a player could hold four to six weeks in, captured per spec from published gear lists and recorded in `data/facts/hit-captured.yaml`. Only two Tier 6 tokens are reachable in that window, so the Tier anchor carries two figures rather than one |
| Resulting state | One of `short`, `full`, or `not_applicable`, per spec and per anchor in `data/facts/hit-captured.yaml`. The four healer specs are `not_applicable` because healing cannot miss. A `short` state counts ITEMS only: gems and enchants are excluded from every figure, so the gap is stated again after the two hit enchants and the remainder in gems against the sockets the set carries |
| Consequence for valuation | How much a point of that stat is worth to this spec, and therefore how items carrying it are prioritized |

The consequence is direct. An off-piece carrying hit is a strong claim for a spec still short of its cap and close to worthless for one already over it, whatever a static weight says. Where a spec's own tier set pushes it past a cap, every hit-bearing off-piece in the instance drops in value for that spec and rises in relative value for its competitors, which changes who should receive contested drops.

**Both anchors are computed, and some specs change state across them.** Which ones, and which way, is recorded per spec in [`hit-captured.yaml`](../data/facts/hit-captured.yaml) and is not restated here.

**The Beast Mastery Hunter is worth reading as a caution.** `Gronnstalker's Armor` carries no hit on any of its five pieces, verified piece by piece, and for a long time this document said that consequently the spec falls from full to short as its tier set arrives. The mechanism is real and the consequence was not: it held because the captured set had also taken two off-pieces carrying no hit, and once those were corrected against the workbook the spec reads full at every anchor. **A true mechanism is not a finding until the set it acts on is right.**

That is the movement this anchor was built to expose, and it runs the opposite way to the usual assumption. That spec does not stop competing for hit-bearing off-pieces as its set comes together. **It competes harder**, because the set gives it none. No Tier 6 set bonus supplies hit either.

**An earlier reading of this section named the Protection Warrior alongside it and was wrong.** That figure came from a rule that swapped in all five Tier 6 pieces, which no spec can assemble in this window, and under the captured sets that spec RISES rather than collapsing. The rule is retired and recorded as retired in `data/facts/hit.yaml`.

**For several specs the second token is a hit downgrade**, which is the finding the retired rule could not produce. The Tier 6 helms carry no hit against the Tier 5 helms they displace, so killing the tier's hardest boss makes those specs worse at hitting it.

**No per-spec figure is written here, and that is deliberate.** Every number in this passage went stale within a day the first time they were, because the captures behind them were repaired several times: a tank set that turned out to be a damage set, a shoulder priced for the wrong class, gear that could not be reached at the anchor wearing it. A figure copied into a document is a second copy, and the second copy is the one that goes wrong. **[`data/facts/hit-captured.yaml`](../data/facts/hit-captured.yaml) is the one place these live**, per spec and per anchor, with the state, the gap after the hit enchants, and the gems remaining against the sockets the set carries. `just check` verifies it against the captures it was built from.

Every figure there counts ITEMS only, so a `short` reading is a gemming and enchanting question before it is a claim on loot.

**The window itself is a forecast.** `data/facts/progression.yaml` records the encounter order as fact and the four-to-six-week window as a forecast, with Archimonde named as the tier's first wall. That is why the Tier anchor states two figures, one with the hands token alone and one with the head token as well, and why neither should be read as settled.

Tier set itemization is the usual cause, so each set is assessed for what it does to the wearer's cap position rather than only for its bonuses. A set that is hit-heavy frees its wearer to chase throughput stats elsewhere; a set that is hit-light constrains which off-pieces are usable at all.

**Haste is a planned stat, not an uncapped one.** TBC has no hard haste cap, and that is exactly why it needs recording: a stat with no ceiling looks linear on a weight table and is not. Three kinds of threshold are captured per spec where they exist.

::: {.cards}

::: {.card}
#### The global cooldown floor
Casters cannot push a global cooldown below 1.0 second, so haste past that point buys nothing on the abilities that sit on it. A spec close to the floor values haste well below its listed weight.
:::

::: {.card}
#### Fit thresholds
Haste is worth a step change where it fits one more cast, tick, or swing inside a fixed window: a proc duration, a shield or damage-over-time effect, or a burst phase the raid times. Between two such steps it is close to inert.
:::

::: {.card}
#### Rotation and proc interactions
Where a spec's talents or weapon procs key off swing timing, haste changes how often those fire rather than only how fast the bar moves. Enhancement and the dual-wield specs are the cases to check first.
:::

:::

Expertise against boss dodge and parry, and any crit threshold a spec's talents key off, are recorded the same way. All of these are noted as conditions rather than treated as hard caps, because a spec can sit between two thresholds and gain almost nothing from more of the stat while a weight table still prices it as though it gains steadily.

## Tier Sets and Set Bonuses

Every item is prioritized on its own merits for each spec, and tokens are no exception: a token is prioritized on the piece it turns into, judged in isolation against the best alternative for that slot. There is no second scale and no separate procedure for tier.

That leaves one gap, and it is worth being precise about it. A set bonus is not a property of any item. The fourth token completes a bonus and the first does not, so the difference lives in the sequence rather than in the piece, and no per-item priority can carry it. The answer is to record what each bonus is worth as a fact the council reads, rather than to build a second ranking around it.

### What each set bonus is worth

Per spec, per threshold, measured the way every other run is measured: the run with the bonus active minus the identical run without it, same gear on both sides, at the Tier anchor, in absolute and proportional terms.

| Recorded | Why |
|---|---|
| Threshold | The two-piece, the four-piece, or a named split configuration |
| Composition | Which pieces it is made of, including any Tier 5 pieces retained |
| Value | Absolute and proportional, with the unit named, since a tank bonus and a damage bonus are not the same quantity |
| Source | Where the composition came from, and whether we had to work it out ourselves |

This is reference data. It sits beside the priorities and informs the council; it does not override a priority or generate a priority of its own.

**Which pieces make up a threshold is read from the inputs, not derived by us.** A five-piece set gives five ways to hold four pieces, and more once combinations across two tiers are allowed, but those permutations are not open questions in practice. Most specs have a settled optimal two-piece, a settled optimal four-piece, and settled split combinations, established by the class communities and already known to the players who will be asking for the tokens. Where no reliable source exists for a spec, or where sources contradict each other, we simulate it and record that we did, because a composition we worked out ourselves is a weaker fact than one the whole class agrees on.

The division is worth stating because the two halves look like they conflict. The community establishes **which** pieces a threshold is made of. Our own runs measure **what** that threshold is worth to this raid. We do not re-derive the first, and we do not import the second.

### When a partial set is worth breaking

A tier piece is not automatically an upgrade over what it replaces. A spec sitting on an active Tier 5 four-piece bonus that equips one Tier 6 piece loses that bonus and gains only the raw stat difference, which is frequently a downgrade. This is a normal and well-documented pattern: in Tier 5 many specs held tokens unequipped until the fourth piece arrived, because nothing below four pieces beat the set they were breaking.

So for every spec we record, per step from one piece to five:

| Recorded | Why |
|---|---|
| What is lost | The set bonus being broken, named, with its effect |
| What is gained | The new bonus if the step activates one, plus the raw stat difference |
| Net verdict | Whether that step is worth equipping on arrival, or the piece is held |
| Hold depth | If held, the piece count at which equipping becomes correct |

Hold depth is a fact about wearing, not about wanting. A spec that banks its first two pieces does not have a weaker claim than one that gains immediately. Its reward arrives later, and frequently arrives larger.

### What a shared token changes

A token is not an off-piece with three times the claimants.

**Its claimant set spans three classes and every role, by construction.** Conqueror serves Paladin, Priest and Warlock. Protector serves Warrior, Hunter and Shaman. Vanquisher serves Rogue, Mage and Druid. Against our roster, every one of the three lines contains a tank, a healer and at least two damage roles. The counts are recomputed from `spec_to_set` in `data/facts/tokens.yaml`, and each spec is named so the count can be checked rather than trusted. This table used to say 6, 7 and 6, totalling nineteen; that undercounted Conqueror by one and Protector by one against the mapping the document itself cites:

| Line | Count | Rostered specs | Roles present |
|---|---|---|---|
| Conqueror | 7 | Holy Paladin, Protection Paladin, Retribution Paladin, Priest healer, Shadow Priest, Affliction Warlock, Destruction Warlock | tank, healer, melee damage, caster damage |
| Protector | 8 | Arms Warrior, Fury Warrior, Protection Warrior, Beast Mastery Hunter, Survival Hunter, Enhancement Shaman, Elemental Shaman, Restoration Shaman | tank, healer, melee damage, ranged damage, caster damage |
| Vanquisher | 6 | Combat Rogue, Arcane Mage, Feral Bear, Feral Cat, Balance Druid, Restoration Druid | tank, healer, melee damage, caster damage |

An off-piece's claimants usually share a unit. A token's claimants are guaranteed not to, so every tier token that drops this phase is a cross-role contest rather than an occasional one.

**Contention on a token recurs for months.** An off-piece contest ends when the item is awarded. A token contest is a flow, so the council is routing a stream rather than a drop, and the same claim on a crowded line converts into a longer wait than on a sparse one.

**The derangement resets everyone to zero at once.** Tier 6 rearranges the token lines completely against Tier 5, so no class keeps its Tier 5 partners and no spec enters Phase 3 with any Tier 6 progress.

**A token is slot-specific.** The five tokens drop from five different bosses: head from Archimonde, hands from Azgalor, shoulders from Mother Shahraz, legs from the Illidari Council, chest from Illidan Stormrage. A composition that includes the chest cannot complete until Illidan dies, which is a fact about what the council can fund this week rather than about what anything is worth.

### Tanks and healers are not valued the same way

Prioritization an item on its own merits assumes more of the stat is better. That holds for damage. It does not hold for either of the other two roles, and tokens are where the difference shows most, because a tier set is the largest single block of stats a spec receives in a phase.

**Tank value is step-shaped.** The stats that matter arrive at thresholds: crit immunity, which is 490 defense skill in plate or 415 for a Bear holding Survival of the Fittest, and 102.4 percent combined avoidance and block for uncrushable. The second of those applies to two of our four tanks. A Bear cannot parry and cannot block, so it holds two of the four entries and no amount of gear closes the gap in normal raiding. Our main tank and third tank are both Druids, so uncrushable is a target for the Paladin off-tank and the Warrior fourth tank only, and a piece is never worth more to a Bear for moving it toward 102.4. Below a threshold, the piece that crosses it is worth more than a larger quantity of anything else. Above it, further avoidance is an ordinary upgrade. A tier piece carrying defense can therefore be the cheapest route across a threshold even when its raw stat line is unremarkable, which is the shape of the argument when a token is what crosses the line. Whether to route tokens to tanks first is a council decision, not a consequence of the arithmetic.

The other half of the tank argument is raid-level rather than personal. A tank who cannot reach crit immunity is a constraint on twenty-four other people, so the item that fixes it is not competing on the same terms as an upgrade that makes one player faster. That is a reason the council can state plainly, and it is the strongest argument in the room when it is true. It is also the weakest once the threshold is met, and it should stop being made at that point.

**Healer value is sufficiency-shaped.** Healing throughput above what an encounter demands is overheal and buys nothing. Whether a healing set bonus is worth anything depends on whether healing is the binding constraint on the fights the raid is actually working on, so the value is recorded with that condition attached rather than as a single figure. A bonus worth a great deal on a heavy-damage encounter can be worth close to zero on a fight the raid already clears comfortably.

Healer set bonuses are also frequently mana returns or cast-time effects rather than throughput, and mana only matters where a fight runs long enough to exhaust it. The comparability table below marks these as not comparable for that reason: there is no way to express a mana return as healing per second without assuming the encounter that decides the answer.

So healer and tank claims carry their condition:

| Role | Recorded with the value | The question it answers |
|---|---|---|
| Tank | Which threshold the piece crosses, if any, and the spec's distance from it | Does this cross a line, or add to a stat already past its line |
| Healer | Which encounters the bonus is worth something on, and whether healing is currently the constraint there | Is the raid short of healing, or short of time |

Neither condition is a number, and neither is a reason to leave the claim out. A tank claim that names the threshold it crosses is more concrete than a damage claim quoting a percentage, not less.

### Comparability of set bonus values

Values are comparable in one case and not in three. Stating which is which is what stops a table of numbers being used to answer a question it cannot answer.

| Comparison | Comparable | Why |
|---|---|---|
| Two damage specs, on the absolute figure | Yes, as raid gain | The unit is the same and the raid gains the same amount whoever holds it |
| Two damage specs, on the proportional figure | Yes, but it answers a different question | Five percent of 800 and five percent of 1600 are both five percent, and are 40 and 80 damage per second |
| Across roles, either figure | No | Normalising does not make healing and damage the same quantity. A percentage of each is still a percentage of a different thing, and dividing two incomparable numbers by their own baselines does not make them comparable to each other |
| Bonuses that are not throughput | No | Mana returns, cooldown reductions and utility procs do not produce a delta of the same kind, and forcing one invents precision |

**The denominator is the catch.** A proportional figure is only comparable between two specs if both denominators were produced the same way: same anchor, same buffs, same fight length, same target count. It also carries any error in that baseline, and carries it magnified. If the simulator models one spec's rotation worse than another's, the absolute figure is wrong once and the proportional figure is wrong twice, since the flawed baseline sits underneath both terms. Where a baseline is known to be weak for a spec, its proportional figures are marked and are not used to order claims.

Comparison is only ever needed within a token line, because a Conqueror threshold never competes with a Vanquisher one. They are different drops. That reduces the problem to three small comparison sets rather than one ranking of twenty-one specs, the count `spec_to_set` in `data/facts/tokens.yaml` gives and the claimant table above names. This sentence used to say nineteen, carrying the same undercount that table corrected. It does not remove the cross-role problem inside each line, which no number resolves.

### Funnelling

The council can decide to route one line's tokens to one spec until a set completes. That is a judgment, informed by the bonus values above and taken in advance, not an output of this framework.

Hold depth is the reason it is sometimes correct. Where hold depth is four, partial awards buy the raid nothing until the fourth token lands, so spreading a line across four such specs delays every payoff without purchasing one. The decision is recorded with what is being bought, what is being deferred, and when it ends, so that a player passed over can read which plan outranked them.

### Two facts this depends on, one settled and one not

**The holder chooses which set the turn-in produces.** A token is not bound to a set. `Chestguard of the Forgotten Conqueror` exchanges at one vendor for six different chest pieces belonging to six different sets across three classes, each at one token, with no restriction: three Paladin sets, two Priest sets and the one Warlock set, per the vendor exchange evidence under `token_exchange` in `data/facts/tokens.yaml`. This sentence used to say "across three sets", which miscounted the sets as if each class held one. So a spec that changes its mind is not blocked by an earlier award. Which pieces a player already holds still governs which bonuses are reachable, but the token itself commits nothing.

That settles the mapping too. `spec_to_set` in `data/facts/tokens.yaml` now maps all twenty-one rostered specs to a set in each of the three tiers, identified by the itemization of the chest piece rather than by a label: defense with block or parry for a tank set, healing done with spirit or mana per five for a healing set, spell damage with spell hit and no healing line for caster damage, strength or agility with hit and crit and no defense for melee. So the piece a token becomes is defined for every spec, and a token can be prioritized.

**Token drop counts are now verified, and the supply side of every crowding argument follows from them.** Each Tier 6 token boss drops **three** tokens per 25-player kill, read from the 2.4.3 loot templates and recorded under `drop_counts` in [`tokens.yaml`](../data/facts/tokens.yaml). Each of the three rolls draws one of the three lines independently and with repetition, so a kill can yield three of one line, and each line expects one per kill over time. The Illidari Council supplies its three across Gathios, Malande and Veras, and none from Zerevor.

::: {.note .veto}
**Which tuning the Anniversary realms open on is not settled.** Patch 2.4.0 added a token to every 25-player boss, taking the count from two to three, and the drop rates recorded here match two rolls rather than three. If Phase 3 opens on the earlier tuning, every supply figure above falls by a third. Recorded under `open_questions.anniversary_opening_count` in `tokens.yaml`; the first kills settle it.
:::

### Overlapping and split set bonuses

Set bonuses are not confined to one tier. A spec can hold two two-piece bonuses from different sets at once, and for some specs the community-established configuration is exactly that rather than a clean four-piece. Shaman are the usual worked example, and they are not the only case.

Every split combination available to a spec in this phase is therefore enumerated and compared against the clean four-piece, including combinations that keep two pieces of Tier 5. Three consequences follow:

- A split configuration changes which slots are free for off-pieces, so it changes what the spec contests.
- It changes hold depth. A spec whose best configuration is two plus two never needs a fourth Tier 6 piece.
- Where the community configuration and our own runs disagree, both are recorded with their sources rather than one being dropped quietly.

Both questions feed the equip order: which token goes to which spec first, and whether the receiving player equips it on arrival or banks it until the set completes.
