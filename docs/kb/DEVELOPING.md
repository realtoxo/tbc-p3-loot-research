# Developing

Conventions that produce wrong output if violated. The prohibitions that must hold everywhere are in [`AGENTS.md`](../../AGENTS.md); this file holds the detail that is only needed once a document or a transform is actually being written.

## House writing style

The style was extracted from the prior repositories in this series by measuring them, so the rules are mechanical properties rather than taste.

Three of them are enforced. `just style` fails on any of these inside prose, but not inside fenced code, inline code, links or block quotations.

- No contractions. Write `do not`, never the shortened form. <!-- test: tools/check_style.py::contraction -->
- No em dashes and no en dashes. Use a comma, a semicolon, or a full stop. <!-- test: tools/check_style.py::em-dash -->
- No vague hedge. `probably`, `might`, `maybe`, `perhaps`, `sort of` and `kind of` are rejected, while hedging with a named condition is correct, so `should`, `unless`, `may` and `usually` are fine. If a claim is uncertain, say what the uncertainty depends on. <!-- test: tools/check_style.py::vague-hedge -->

The rest are conventions no check can see.

- Every table is preceded by one sentence stating the question it answers. <!-- unenforced -->
- Open a document by contrasting the question it answers with the question it does not. <!-- unenforced -->
- State confidence per spec as High, Good or Conservative, with the reason. Thin evidence gets conservative policy, never a confident guess. <!-- unenforced -->
- Priority notation is `>` for preferred order, `=` for the same lane, and `Temp` for a bridge item. There is no notation for warning a spec off an item: a spec either has a priority or has none, and the reason carries the rest. <!-- def: docs/conventions.md::Priority -->
- In loot documents, items are written `[Name]{.item}` and the build supplies the link and the tooltip. Write `[Name](https://www.wowhead.com/tbc/item=ID/slug)` by hand only for an item outside the scope of `items.csv`, with apostrophes stripped from the slug. In numeric and simulation documents, item names take backticks and are not linked. `just links-external` resolves every id and confirms the name claimed for it. <!-- test: tools/check_external_links.py -->

## Authoring the site

Documents are pandoc Markdown with fenced divs enabled. These map to styled components in `theme/style.css`.

```markdown
::: {.note}            Callout. Variants: .veto .brass .verd
::: {.cards}           Responsive grid; wrap ::: {.card} inside
::: {.card .funnel}    Card. Variants: .funnel .equity .warn
::: {.stack}           Layer diagram; wrap ::: {.layer} inside
::: {.rules}           Wrap an ordered list to get boxed counters
::: {.rows}            Key/value rows
::: {.specs}           Spec argument cards. Wrap a level-4 heading plus a
                       definition list per spec. Recognized terms: Priority,
                       Upgrade, Unit, Delta. Any other term
                       becomes a labeled field in the order written.
::: {.delta}           Stat deltas, one spec per definition list term. The
                       definition is [A]{.item}, whose four baselines are
                       derived, or [A]{.item} over [B]{.item} to pin both sides.
                       Every baseline is a column group of one table.

[Name]{.item}          Item reference. Becomes a Wowhead link carrying the
                       item's stat line as a hover and focus tooltip.
```

A `Delta` on a spec card takes the spec from the card's own heading, so the item under discussion is all that is written and every baseline is derived:

```markdown
#### Feral Cat

Delta
:   [Cursed Vision of Sargeras]{.item}
```

The standalone block names each spec instead, which is how two specs contesting one item are put beside each other:

```markdown
::: {.delta}

Feral Cat
:   [Thunderheart Cover]{.item}

Feral Bear
:   [Thunderheart Cover]{.item}

:::
```

Writing two references pins both sides and renders one table. The standalone block above uses it where the derived baselines would differ between the two specs and hide the comparison being made:

```markdown
Feral Cat
:   [Thunderheart Cover]{.item} over [Nordrassil Headdress]{.item}
```

Several build behaviors are worth knowing before authoring.

- **An item reference carries only the name.** `[Slayer's Helm]{.item}` resolves
  at build time against `data/facts/items.csv`, which supplies the item id for
  the link and the stat line for the tooltip, and against `data/facts/drops.csv`
  for the boss and the raid. No id and no stat line is written into prose, so
  neither can go stale. Wowhead's own tooltip script is deliberately not used:
  it is an external dependency, it costs a network round trip on a site that is
  read locally, it cannot be styled, and it would place an unverified stat line
  beside our verified ones. <!-- ref: theme/filters/items.lua -->
- **Two items sharing a name take the id beside the name.** `Warglaive of
  Azzinoth` is item 32837 in the main hand and 32838 in the off hand, and the
  name alone fails the build as ambiguous. Write
  `[Warglaive of Azzinoth]{.item item=32837}`. The id decides which row is read,
  and the name beside it is checked against that row, so a name and an id that
  disagree fail rather than render. Write the id only where the name is
  ambiguous. <!-- ref: itemdb.lua::resolve_span -->
- **A name the item table does not hold fails the build.** The error names the
  document, the reference and the nearest matches, and no page is written. An
  unresolvable name is a wrong reference, and an empty tooltip would hide it.
  Tier pieces resolve because `items.csv` carries them; see the `source` column
  in [`data/facts/PROVENANCE.md`](../../data/facts/PROVENANCE.md). <!-- ref: theme/filters/items.lua -->
- **The tooltip is reachable by keyboard.** The reference renders as a focusable
  link described by the bubble, which appears on `:focus-within` as well as on
  hover, and the bubble is hidden with opacity so it stays in the accessibility
  tree. Hiding it with `display` or `visibility` would silence it for a screen
  reader. <!-- ref: theme/style.css::.item-tip -->

- **A delta is read A over B**, meaning what a player gains by taking A instead
  of B. The items are the `[Name]{.item}` references in the definition, in the
  order written, so the author supplies no item id and no rate. Only stats that
  differ get a row, and every rate that produced a converted figure is printed
  under the table with the fact file and the key it came from.
  <!-- ref: theme/filters/delta.lua -->
- **One table holds every baseline, not one table each.** A `Stat` column names
  each differing stat once, each baseline adds a `Change` and a `Converted`
  column under its own label, and one `Net` line runs along the bottom. Separate
  tables side by side each sized their own rows, so the same stat sat on
  different lines, each printed the stat name and the rates again, and each was
  a quarter of the card wide and needed a scrollbar of its own. Rows now line up
  because they are rows of one table. The rates are printed once, because a rate
  belongs to the spec and not to the baseline.
  <!-- ref: theme/filters/delta.lua::table_of -->
- **Hit and crit are printed as a percentage on a card, never as a rating.**
  Rating is what the game and the item database record, and it is what the fact
  files keep, but it means nothing to a reader without a conversion done in the
  head. So the two rows carry the converted figure where a raw one would sit,
  the `Converted` cell beside it is left empty, and the rows are named `hit` and
  `crit` rather than `hit rating` and `crit rating`. Printing the rating and the
  percentage together states one quantity twice, and the shorter name is what
  keeps that column off a second line. A rating still appears in one place, the
  `Rates` block, which is what makes a percentage checkable, so do not remove
  it. The same rule governs the `Constraints` prose on a
  spec card. The exact percentage forms of the caps are recorded in
  `hit.yaml.raw_caps`, and a card names those rather than converting the rating
  itself, because 9%, 28% and 16% are round where the rating is not.
  <!-- ref: theme/filters/delta.lua::PERCENT_ONLY -->
- **A card prints `%`, never the word.** `+0.57%`, with no space. The word costs
  seven characters plus a space on every figure, and a `Net` cell carries two
  figures against four baselines, so it was a column of its own repeated eight
  times. The fact files spell `percent` out and are correct to, because they are
  read as documents rather than scanned as tables, so the generated rate strings
  are converted at render time rather than at their source.
  <!-- ref: theme/filters/delta.lua::percent_symbol -->
- **The `Net` row prints one figure per line, at a footer size.** It is a
  summary of the rows above it, so it reads smaller than they do; at body size
  it was the largest thing in the table. Two totals joined by a middot wrapped
  mid-phrase and left `melee crit` alone on a second line, and the cells only
  get narrower as baselines are added, so each figure is now its own block. That
  also lines the `Net` row up across the baselines the way the stat rows line
  up. <!-- ref: theme/filters/delta.lua::lines_cell -->
- **The delta table never scrolls sideways, at any width.** There is no scroll
  container around it. Above 860px the stat and change columns hold their line
  and the converted text wraps, so the table gives way vertically. At 860px and
  below one column of each baseline's pair is dropped and the rest is laid out
  at fixed widths, because four baselines at two columns each is nine columns
  whose combined minimum content width is 749px, which the card cannot give
  below 841px of page, and the rule is to print less rather than to add a
  scrollbar. What is dropped is the raw `Change` figure, except on the `hit` and
  `crit` rows, where the percentage is the only figure the row carries and the
  empty `Converted` cell goes instead, so every row keeps the same length. The
  breakpoint was 680px while there were three baselines and seven columns, and
  900px while hit and crit printed their converted figure as a wrapping phrase;
  measuring is what found each move, including the 821px to 840px priority a
  breakpoint of 820px left overflowing. Measured at every width from 320px to
  2400px in both themes, `scrollWidth` equals `clientWidth` on the page, the
  card, the delta block and the table.
  <!-- ref: theme/style.css::.delta-grid -->
- **Below 860px the body cells do not sit under their own column group.** A
  dropped cell is `display:none`, so a body row holds five cells while the
  header row holds four cells each spanning two columns plus the stat cell, and
  the figures sit further left than the label they belong to. It predates the
  percentage rows and it affects every row equally. Collapsing each dropped cell
  to zero width instead would line them up and needs automatic table layout,
  which sizes columns from content and reintroduces the overflow the fixed
  widths exist to stop, so a fix has to size the columns some other way, such as
  a `colgroup` the stylesheet can address per column. <!-- unenforced -->
- **One reference derives four baselines on a two by two, and each column group
  says which it is.** One axis is the phase, this phase against the phase before
  it; the other is the tier piece against the best item that is not tier. They
  are printed in reading order: `Over Tier 6`, `Over best Phase 3 off-piece`,
  `Over Tier 5`, `Over best pre-phase off-piece`. The two tier baselines are the
  spec's own pieces for the slot, from `spec_to_set` in `tokens.yaml`; Tier 5 is
  the realistic one, because a raider obtains it by raiding. The two off-piece
  baselines are the highest-EPV item in the slot whose workbook Phase column
  reads 3, and reads 1 or 2, that belongs to no tier set. **The four categories
  are disjoint by construction, so no collapse logic exists for them.** There
  used to be one `Over best available` view, the best Phase 1 or 2 item whether
  tier or not, which overlapped `Over Tier 5` and collapsed into it on four of
  the eight cards of the worked example. A slot outside the five a tier set
  covers renders the two off-piece column groups alone. A slot with no non-tier
  item in one of the two phase groups, a spec missing a tier piece for one of
  the five slots a set does cover, and a spec with no ladder each fail the build
  naming the spec and the slot.
  <!-- ref: theme/filters/delta.lua::views_for -->
- **The item under discussion is excluded from every baseline.** Otherwise a
  card compares an item with itself, and this is not a corner case:
  `Cursed Vision of Sargeras` is the top Phase 3 head on all eight ladders of
  the worked example, so taking rank one blindly would drop the whole Phase 3
  off-piece column there. `tools/extract_ladder.py` emits two ranked candidates
  in each off-piece cell and `delta.lua` takes the first that is not the item on
  the card. Two is enough, because the item occupies at most one rank.
  <!-- ref: theme/filters/delta.lua::first_other -->
- **Every view names its acquisition route, always.** The strongest item in a
  slot is frequently one a raider cannot obtain, and comparing against it
  without saying so is the defect this rule exists to stop: four of the eight
  baselines on the worked example were gated, three engineering goggles and one
  arena helm, and a rogue who is not an engineer was being measured against a
  helm he cannot get. It matters more with the Phase 3 off-piece column in
  place, because the Feral Cat's baseline there is a Season 3 arena helm and
  `roster.yaml` records Season 3 as part of the tier and not as gear the roster
  is assumed to hold. On an off-piece the route comes from the workbook
  `Location` column; on a tier piece it comes from the zone its token drops in,
  in `boss_by_tier_and_slot`. It is recorded by `tools/extract_ladder.py` on
  **every** baseline rather than on the gated ones only, and is bucketed into
  four: `crafted` for a profession, `arena` for a season, `badge` for Badge of
  Justice, and `drop` for everything else. The raw `Location` string is kept
  beside the bucket and is what the label prints, so `Engineering`, `Season 3`
  and `Mount Hyjal` each name their own source. A gated label also carries
  `.delta-view-gated` and takes the caution tone, at 4.6:1 on light and 6.2:1 on
  dark against the table head it sits on.
  <!-- ref: tools/extract_ladder.py::route_of -->
- **Tier membership is never a name test.** Tier pieces sit in the ladders
  beside raid drops, so which items are tier comes from `spec_to_set` and the
  set piece lists and from nowhere else, as a set of item ids. A probe written
  the other way reported `Slayer's Helm` as the Rogue's best non-tier head; it
  is the Rogue's tier head, and a name filter returns
  `Cursed Vision of Sargeras`, which is the item under discussion. This test is
  what makes the two off-piece cells disjoint from the two tier cells.
  <!-- ref: tools/extract_ladder.py::tier_item_ids -->
- **A derived baseline can be an item `items.csv` does not hold.** The ladder
  covers crafted, arena, badge and dungeon items as well as raid loot, and the
  Combat Rogue's best Phase 1 or 2 head is an engineering goggle. Where
  `items.csv` holds the baseline it supplies the stat line and `items.lua`
  builds the tooltip; where it does not, the generated ladder carries the stat
  line and `delta.lua` builds the same tooltip itself, because `items.lua` fails
  the build on a name it cannot resolve.
  <!-- ref: theme/filters/delta.lua::baseline_row -->
- **Every baseline gets the same tooltip, whichever table it came from.** A
  baseline outside `items.csv` used to render as a bare link carrying its stat
  line in the `title` attribute. The browser draws that as its own plain box
  after a delay, so beside a styled bubble it reads as a broken tooltip rather
  than as a second style of item reference, and it is the common case now: the off-piece
  columns are frequently crafted or arena items, so two of the four baselines on
  a card behaved differently from the other two. The synthesized bubble carries
  the name, the phase, the stat line and the acquisition route as a sentence. It
  states no tier, no armor type and no boss, because the ladder does not carry
  those for an item outside the compendium and an invented line is worse than an
  absent one. <!-- ref: theme/filters/delta.lua::baseline_inline -->
- **A tooltip inside the delta table is anchored to the table, not to the name.**
  The bubble is 360px wide and opens from the left edge of the name, which is
  fine in prose, where names sit in a 68ch column at the left of the page. A
  baseline name sits in the third or fourth column group, so the bubble opened
  past the card and, below about 860px, past the viewport, which put a
  horizontal scrollbar on the document for as long as the pointer rested on the
  name. Hovering with a real pointer and reading `scrollWidth` against
  `clientWidth`, eight of the eleven baseline names on a card did it at 800px and
  twenty-three did at 375px; the three-baseline build failed the same way from
  1000px down, so it predates the fourth column. `.item-ref` is therefore not the
  positioned ancestor inside the table: the bubble resolves against the header
  row, opens under the head at the table's own left edge, and takes
  `max-width:min(360px,100%)`, where `100%` is the table. It cannot reach past
  the card at any width, no measurement of where the name sits is needed, and a
  wrapped name no longer moves it. Only one bubble is ever open, so they cannot
  collide. <!-- ref: theme/style.css::.delta-grid .item-tip -->
- **No conversion rate is written in a filter.** The rates are lifted out of
  `attack-power.yaml`, `crit.yaml` and `hit.yaml` by `tools/extract_conversions.py`
  into `theme/filters/conversions.generated.lua`, which is the only source of
  rates `delta.lua` reads. The rates are not constants: strength is two attack
  power for a Warrior, Paladin, Shaman or Druid and one for everyone else, and
  agility is attack power for a Cat and none for a Bear. One hardcoded figure
  would render a page that looks authoritative and is wrong for most specs.
  <!-- test: justfile::check -->
- **A missing rate, a missing spec or an unresolvable item name fails the
  build.** The generator stops on a fact-file key it cannot find, naming the
  spec and the key. The filter stops on a spec that is not in the generated
  table, on a definition that does not hold exactly two item references, and on
  a differing stat that has no rate for that spec, in each case naming the
  document and the cause. No page is written.
  <!-- ref: theme/filters/delta.lua::Pandoc -->
- **Name resolution is shared, not repeated.** `theme/filters/itemdb.lua` reads
  `items.csv` once and holds the CSV parser, the stat vocabulary, the name
  index and the armor rule. `items.lua` and `delta.lua` both use it, so there
  is one answer to whether a name exists. <!-- ref: theme/filters/itemdb.lua -->
- **`delta.lua` runs third**, after `tables.lua` and `links.lua` and before
  `items.lua` and `specs.lua`. It reads the plain names out of the `.item`
  spans before `items.lua` turns them into links, it leaves the spans in place
  so they still get their tooltips, and it hands `specs.lua` a card whose
  `Delta` term is already built. `tables.lua` has run by then, and its scroll
  wrapper is not wanted: the delta table is sized to fit instead.
  <!-- ref: justfile::filters -->
- Tables need no markup. A Lua filter wraps every table in a horizontal scroll container at build time, so wide tables scroll with JavaScript disabled and when printed. <!-- ref: theme/filters/tables.lua -->
- **Wide components escape the prose priority, prose does not.** `.doc > *` is capped
  at `--priority`; `.table-wrap`, `.cards`, `.specs`, `.stack` and `pre` are exempt
  and take the full column. Widening the page frame does not help, because prose
  is capped at `68ch` and gains nothing from it.
- **The table of contents is dropped below four headings.** `theme/filters/toc.lua`
  sets a `tocless` flag and the template adds `shell-full`, which collapses the
  grid to one column. A rail listing two entries costs 224px and tells the reader
  nothing they cannot already see.
- **A CSS grid promotes bare text to its own grid item.** An `<li>` holding `<b>Label.</b> trailing sentence` inside a two-column grid puts the sentence in the narrow counter column, one word per line. Every grid child must be a single element, which is what `.rules li > *` forces. Writing a list item with a bold lead and a trailing sentence inside `::: {.rules}` triggers it. <!-- ref: theme/style.css::.rules li > * -->

Front matter drives the page header. `generated` is set only on a generated document, and it renders the banner that warns a reader off editing the output. <!-- ref: theme/template.html::generated-banner -->

```yaml
---
title: Framework And Build Plan
eyebrow: Method
subtitle: One or two sentences.
status: draft | review | adopted | blocked
updated: 2026-08-08
generated: data/facts/drops.csv   # only on generated documents
---
```

## Regenerating fact tables

`just regen` reads the WoWSims item database and overwrites `drops.csv`, `items.csv` and `item-effects.csv`. What that means for editing them is the generated-files rule in [`AGENTS.md`](../../AGENTS.md).

It also writes `theme/filters/ladder.generated.lua`, which holds the four comparison baselines per spec and per slot, along with the acquisition route of every ladder entry in it, read from the workbook ladders and `tokens.yaml` by `tools/extract_ladder.py`. Lua cannot read those CSVs and must not carry a second parser of them, so the four parsing traps recorded in [`data/research/epv-workbook/PROVENANCE.md`](../../data/research/epv-workbook/PROVENANCE.md) are handled once, in Python, at regeneration time. <!-- ref: tools/extract_ladder.py -->

It also writes `theme/filters/conversions.generated.lua` from the three fact files that hold conversion rates. **That file is a build artifact and not a fact, so it is deliberately outside `data/facts/`**, and it is not in the inventory in [`data/facts/PROVENANCE.md`](../../data/facts/PROVENANCE.md). It states nothing `attack-power.yaml`, `crit.yaml` and `hit.yaml` do not already state, and a second copy of a fact inside the fact directory is the copy that goes stale. It exists only because Lua cannot read YAML. It sits beside the filter that consumes it, `just check` regenerates it and fails on any drift, and every entry in it cites the file and key it was read from. <!-- ref: tools/extract_conversions.py -->

The one thing that file holds which the fact files do not is the spec registry: which class a spec is, and which druid form it fights in. That is identity rather than a rate, it lives in `SPECS` in the generator, and a spec absent from it fails the build when a document names it. <!-- ref: tools/extract_conversions.py::SPECS -->

The database path defaults to a sibling checkout and is overridden with the `WOWSIMS_TBC` environment variable. <!-- ref: justfile::WOWSIMS_TBC -->

Before writing any parser against that database, read [`data/facts/PROVENANCE.md`](../../data/facts/PROVENANCE.md) and [`data/research/epv-workbook/PROVENANCE.md`](../../data/research/epv-workbook/PROVENANCE.md). Each records parsing facts that were found by a silent data-loss bug: tab identity, slot vocabulary, thousands separators, column layout, which Wowhead endpoints answer an automated client, and why raid loot is filtered by zone rather than by the database phase field. <!-- ref: tools/extract_drops.py::ZONES -->
