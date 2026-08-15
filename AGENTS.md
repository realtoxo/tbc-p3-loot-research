# AGENTS.md

A loot council decision system for World of Warcraft: The Burning Crusade Classic, Anniversary Phase 3, Mount Hyjal and Black Temple. It is not a best-in-slot list. A published reference workbook already scores items within a spec, and this project builds the layer above that: what the raid loses by routing a drop one way instead of another, which claimant on a contested token line goes first, what a tier piece breaks when equipped, in what order items should flow, and whether loot is reaching people fairly.

The governing document is [`docs/framework.md`](docs/framework.md). Every analytical decision must trace back to a section in it, and if this file conflicts with it, that document wins and this file needs updating.

## Knowledge Base Model

This repository's knowledge base holds **claims an agent cannot recover by reading the code**. Anything derivable, such as directory layouts, dependency lists, architecture overviews and flag tables, is deliberately absent, because restating what the code already says is redundancy, and redundancy is what makes documentation harmful rather than merely useless.

Every claim carries a referent so it can be checked. Which referent a claim takes depends on what it asserts.

| Claim asserts | Referent |
|---|---|
| What the code does | `ref:` a symbol, or `file:line` when no symbol contains it |
| What a term means | `def:` the type, module or document embodying it |
| An invariant that must hold | `test:` the check that proves it, or an explicit `unenforced` |
| Why a choice was made | `why:` the ticket, PR, ADR or commit that decided it |
| A fact about a system outside this repository | `ext:` the source, with the date observed |

**Every claim lives at exactly one boundary.** Parents link to child claims; they never restate them. **No file is mandatory**, because files are containers, created only when claims exist to fill them.

## Knowledge Base Structure

`AGENTS.md` is the routing and constraint layer, and it is the only file reliably always loaded. **Anything that must always hold belongs here.** Its sibling `CLAUDE.md` is a symlink, because Claude Code does not read `AGENTS.md`.

The knowledge base lives under `docs/kb/`, which `just build` excludes, because everything else under `docs/` is rendered into the published compendium and agent-facing conventions are not compendium content.

Which knowledge-base file answers which question:

| File | Holds |
|---|---|
| [README.md](README.md) | Premise and routing, for humans |
| [docs/kb/DEVELOPING.md](docs/kb/DEVELOPING.md) | House writing style, Markdown component vocabulary, regeneration contract |
| [docs/kb/DOMAIN.md](docs/kb/DOMAIN.md) | TBC 2.4.3 truths and outside-source truths that have already caused wrong conclusions |

An empty or filler file is a defect, not compliance.

## Read First

Eight documents carry the context a newcomer needs before changing anything.

| Document | Why |
|---|---|
| [docs/framework.md](docs/framework.md) | The governing document. It is where the reasoning behind a call comes from |
| [docs/conventions.md](docs/conventions.md) | Compendium vocabulary: spec, claimant, priority, blocker, gear anchor, rank-unstable |
| [data/judgments/priorities.yaml](data/judgments/priorities.yaml) | Every priority the council has settled, and why. Kept out of `data/facts/` on purpose |
| [data/judgments/token-verdicts.yaml](data/judgments/token-verdicts.yaml) | What the council reads out of the token arithmetic. Conclusions, not measurements, each saying whether a named source supports it or whether it is ours |
| [data/judgments/capture-fidelity.yaml](data/judgments/capture-fidelity.yaml) | What a captured gear set is: a record of a published source, not a set rebuilt to the workbook. Read it before correcting gear against a ladder |
| [data/facts/PROVENANCE.md](data/facts/PROVENANCE.md) | What every fact table holds, how it was produced, and whether `just regen` overwrites it |
| [data/facts/sim-results.yaml](data/facts/sim-results.yaml) | What the simulated figures MEAN, and nothing they already say. Two specs measure LOWER at a better anchor, and both were investigated rather than published as they stood. The figures themselves are in `sim-figures.yaml` |
| [data/research/epv-workbook/PROVENANCE.md](data/research/epv-workbook/PROVENANCE.md) | The reference workbook, what it provides, and what it deliberately leaves to us |

## Commands

Everything runs through `just`. Run `just` alone to list.

| Command | Does |
|---|---|
| `just dev` | Rebuild on change and live-reload the browser on :4000 |
| `just build` | Render `docs/**.md`, excluding `docs/kb/`, to a static site in `site/` |
| `just publish` | Build, then commit `site/` to `gh-pages` from a throwaway index, leaving it untracked here |
| `just regen` | Rebuild the nine generated fact tables and the six generated Lua filters the compendium reads from |
| `just check` | Regenerate, then fail on drift, on a gated gem or enchant, on a capture disagreeing with its own rows or with `items.csv`, on gear an anchor could not have reached, and on a sim profile no character could wear |
| `just sim` | Run every gear profile through wowsimcli and rewrite the figures and the pages that read them. Needs the binary and takes minutes, so it sits outside `just regen` and `just check` |
| `just gating` | Only the gem and enchant gating half of `just check` |
| `just captures` | Only the capture checks: the token figures against the workbook, self-consistency, the item table, the progression premise, availability per anchor, and tank defense against the crit immunity threshold |
| `just style` | Check documents against the house writing style |
| `just filter` | Check that the spec filter still hides what it says it hides. Needs node |
| `just links` | Validate internal links and their anchors in the Markdown source |
| `just links-html` | Check the built HTML for missing link targets |
| `just links-external` | Resolve every Wowhead id and confirm the name claimed for it. Network-bound and slow |

## Critical Rules

- **Collect facts. Decide nothing.** No agent should produce a decision, a score, a priority or a ranking. The inputs to a loot decision are quantitative and qualitative together, and the output is a judgment the council reaches by discussing the facts as a group. A formula reducing them to one number would hide the judgment rather than remove it, and would be argued with on its arithmetic instead of its reasoning. If a task seems to require ranking one spec above another, say that it is out of scope rather than inventing a method. <!-- unenforced -->
- **A judgment lives in `data/judgments/`, never in `data/facts/` and never in a document.** A priority is arguable and a fact is not, so they are separated, and a reader asking what changed an answer gets either "a fact moved" or "we changed our minds" rather than both at once. Writing a Priority or Unit field in a document fails the build. A For and Against pair used to sit beside them and was removed on 10 August 2026, having been filled in for one item only; what creators said is captured instead, in `data/facts/creator-stances.yaml`. <!-- test: theme/filters/specs.lua::GENERATED_TERM -->
- **A claim without provenance is a defect, not a shortcut.** State only what a source supports. A number with no source survives rewrites and gets cited later, so it is worse than no number. A claim citing "our own simulation" must name the figure it means, and there are exactly two places figures live. `data/facts/sim-figures.yaml` holds every run at OUR gear anchors, 13 specs across entry, tier and best in slot, each with its `standard_error`. `crit.yaml.simulated_figures` holds four raid-buffed crit percentages produced against the engine's **own** presets rather than ours, single-source and flagged as uncorroborated. Anything else is unsourced, including any price for a set bonus, which is still measured only in the three cases `sim-results.yaml` names. <!-- unenforced -->
- **The plus or minus beside a DPS figure is ONE standard error, never a confidence interval.** It is the spread across iterations over the square root of the iteration count, so it covers about 68 percent. The guild lead ruled on 15 August 2026, having been shown both that and the 95 percent form. Relabelling it lets a reader treat two barely separated figures as settled. <!-- ref: data/facts/sim-figures.yaml -->
- **A consumable pick is per spec AND per anchor.** The stone follows the weapon class and the food follows whether that set is hit-capped, and both move with the gear: ten of fourteen specs change weapon class between anchors. `consumable-ids.yaml` was keyed on spec alone until 15 August 2026, and adding the best-in-slot anchor made it drop the weapon imbue from ten specs at every anchor rather than answering each one. A dropped imbue does not error; the run succeeds with a smaller number. <!-- ref: tools/extract_consumable_ids.py::weapon_types -->
- **Generated files defend themselves.** `data/facts/drops.csv`, `items.csv`, `item-effects.csv`, `hit-captured.yaml`, `set-stats.yaml`, `consumable-ids.yaml` and `transcript-mentions.csv` are produced by the transform, so editing one by hand loses the work on the next `just regen`, and `just check` fails the build by regenerating and diffing. If a generated file is wrong, fix the data or the transform, never the output. <!-- test: justfile::check -->
- **Two items sharing a word are not the same item, and only the id settles it.** This project has dispositioned an item on its name four times. The most recent cost a gear swap and moved published figures: Belt of Blasting, id 30038, was replaced as a Spellfire Tailoring piece, and the Spellfire belt is a different item, id 21846. <!-- ref: docs/kb/DOMAIN.md -->
- **Every EP figure states which workbook tab it came from, and the tab is checked.** `token-arithmetic.yaml` was conventionalized from agent captures whose reports were not retained, so its figures stood on nothing; a sweep found seven wrong, two of them reversed in direction and printing on a card. The EP Workbook is in the repository, so a figure either reproduces on that spec's tab or it does not. A retraction may quote the figure it retracts, under a key named `previously_claimed`, `corrected` or `retracted`. <!-- test: tools/check_token_arithmetic.py -->
- **The raid is five parties of five, and the groups say so.** `roster.yaml` enumerated only two parties for a long time, so the two plate tanks and every healer sat in no group and were credited no group buff. All five are now written out, and `just check` verifies that each holds five, that they place twenty-five between them, that what they place matches `counts` or declares the difference, and that the shaman `shaman_by_party` names for a party is actually in it. <!-- test: tools/check_roster.py -->
- **A tank's defense is checked against the threshold, not assumed.** `set-stats.yaml` carries defense per spec per anchor and `crit.yaml` carries 284 for plate and 154 for a Bear. A shortfall inside the discretionary gem and enchant budget is reported; one larger than every route combined fails the build, because that is a gear problem rather than a gemming one. <!-- test: tools/check_tank_defense.py -->
- **The ENTRY anchor may not wear what it could not reach.** Entry is the set worn before Phase 3, so it holds no Mount Hyjal or Black Temple drop and no Mount Hyjal reputation reward. Each violation was individually plausible while reading one file and impossible against the drop table. <!-- test: tools/check_capture_availability.py -->
- **The TIER anchor is not constrained by progression at all.** It is each spec's entry set plus the tier pieces its Phase 3 best-in-slot list wears, Tier 6 and any Tier 5 or Tier 4 tier piece the list still keeps, falling back to the entry item slot by slot. Those lists are written for a full clear, so a tier set legitimately holds tokens from Mother Shahraz, the Illidari Council and Illidan. This rule used to bar those bosses at EVERY anchor and the guild lead removed that on 14 August 2026: "progression is moot as a topic". The tier anchor answers what a spec is building toward, not what it plausibly holds in week four. <!-- why: docs/kb/OPEN-FINDINGS.md -->
- **A sim profile may not wear what Phase 3 cannot supply.** Published guides are written against complete 2.4.3 content, so a profile copied from one inherits items the Anniversary schedule places later. `enchants-gems.yaml` records the gating and `just check` compares every profile against it. If an item turns out to be reachable, correct the fact file rather than the check. <!-- test: tools/check_gating.py -->
- **Never edit anything under `data/research/` after capture.** Citations point at those bytes. <!-- unenforced -->
- **Do not add a static site generator, a build system, a framework, or a monorepo tool.** Pandoc plus the template in `theme/` is the renderer, chosen deliberately over MkDocs, Sphinx, Eleventy and mdBook. <!-- why: docs/framework.md -->
- **Do not commit `site/`, a vendored simulator checkout, or anything over a few megabytes of binary.** <!-- ref: .gitignore -->
- **Keep repository-wide claims here.** A boundary-local claim lives inside the boundary that owns it, which for the fact tables means the `PROVENANCE.md` beside them. <!-- unenforced -->
- **Never state the same fact at two boundaries.** Link to it instead, because a second copy is what goes stale. <!-- unenforced -->
- **Never add a claim without a referent**, meaning one of `ref:`, `def:`, `test:`, `why:`, `ext:` or `unenforced`. <!-- unenforced -->
- **When changing behavior, update the affected `README.md` and any relevant `docs/kb/` document in the same change.** <!-- unenforced -->
