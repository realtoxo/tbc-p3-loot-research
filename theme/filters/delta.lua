--[[
  Turn a pair of item names into the difference, converted into what one spec
  actually gains.

  A comparison written as two stat lines asks the reader to do the conversion in
  their head, and most readers cannot, because the rate is not a constant. It
  differs by class and, for a druid, by form. Thunderheart Cover carries 53
  strength; for a feral druid that is 106 attack power against Cursed Vision of
  Sargeras and its 108, so the two pieces are within two attack power of each
  other and the whole difference is crit. That is invisible in raw numbers and
  obvious once converted.

  Two ways to write it. Both are plain Markdown, both name the spec, and both
  stay readable on GitHub, where they degrade to the words the author typed.

  ONE, on a spec card, where the spec is the card's own heading:

      #### Feral Cat

      Delta
      :   [Cursed Vision of Sargeras]{.item}

  TWO, standalone, one row per spec, which is how two specs contesting the same
  item are put beside each other:

      ::: {.delta}

      Feral Cat
      :   [Thunderheart Cover]{.item}

      Feral Bear
      :   [Thunderheart Cover]{.item}

      :::

  ONE ITEM MEANS EVERY BASELINE IS DERIVED. The author names the item under
  discussion and nothing else, and four baselines are derived from it, on a two
  by two of the phase against tier membership:

                    tier piece            best off-piece
      this phase    the Tier 6 piece      the best Phase 3 non-tier item
      pre-phase     the Tier 5 piece      the best Phase 1 or 2 non-tier item

  They are printed in reading order, the row of this phase first:

      Over Tier 6                       the spec's own Tier 6 piece for that
                                        slot, which is the set-progress
                                        question rather than the upgrade one
      Over best Phase 3 off-piece       the highest-EPV item in that slot whose
                                        workbook Phase column reads 3 and which
                                        belongs to no tier set. This is the
                                        column the cards were missing: for six
                                        of the seven specs on the worked
                                        example it beats their own tier head
      Over Tier 5                       the spec's own Tier 5 piece for that
                                        slot. A raider obtains it by raiding,
                                        so it is the realistic baseline and it
                                        is what most of the roster wears coming
                                        into the phase
      Over best pre-phase off-piece     the same as the Phase 3 off-piece, for
                                        a Phase column reading 1 or 2

  WHY FOUR AND NOT THREE. The middle view used to be one `best available`
  baseline, the highest-EPV Phase 1 or 2 item, tier or not. It overlapped the
  Tier 5 view, because a Tier 5 piece is a Phase 2 item, and for four of the
  eight cards on the worked example the two resolved to the same item and
  collapsed into one column. That collapse was explained as informative and was
  a symptom of two categories that are not disjoint. Splitting the off-piece
  cell out of the tier cell and adding the phase axis makes the four disjoint,
  so no two derived baselines can resolve to one item and there is no collapse
  to explain.

  ONE TABLE, NOT ONE PER BASELINE. The four baselines are four column groups of
  a single table: one Stat column on the left, then a Change and a Converted
  column for each baseline, then one Net line across the bottom. Written as
  separate tables side by side the same stat sat on different lines, because
  each table sized its own rows, and each table was a quarter of the card wide
  and needed a scrollbar of its own. The rates are printed once, under the
  table, because a rate belongs to the spec and not to the baseline.

  HIT AND CRIT ARE PRINTED IN PERCENT AND CARRY NO RATING. Rating is what the
  game and the item database record, and it is what the fact files keep, but it
  means nothing to a reader without a conversion done in the head. Those two
  rows therefore carry the converted figure where a raw one would sit, the
  Converted cell beside it stays empty, and they are named `hit` and `crit`
  rather than `hit rating` and `crit rating`. A rating survives in one place
  only, the Rates block, which is what makes a percentage checkable. Every
  figure prints `%` and not the word, with no space before it.

  THE ROUTE IS PART OF THE ANSWER. A view used to be rendered with no statement
  of how the baseline is obtained, and four of the eight baselines on the worked
  example were gated: two engineering goggles, one arena helm, and the same
  goggle again on a second card. A rogue who is not an engineer was being
  compared against a helm he cannot get. The route is now on the label of every
  baseline, tier and off-piece alike, gated or not. It matters most on the Phase
  3 off-piece column, where the Feral Cat's baseline is a Season 3 arena helm
  and data/facts/roster.yaml records Season 3 as part of the tier and NOT as
  gear the roster is assumed to hold.

  All four come from `theme/filters/ladder.generated.lua`, written by
  `tools/extract_ladder.py` from the workbook ladders and data/facts/tokens.yaml.
  TIER MEMBERSHIP IS NEVER A NAME TEST: it is the item ids in tokens.yaml, per
  the note in that generator. Every baseline excludes the item under discussion,
  or a card would compare an item with itself, which is why the generated table
  carries two candidates in each off-piece cell and this filter takes the first
  that is not the item on the card. A slot outside the five a tier set covers
  has no tier baseline in either tier, so only the two off-piece views render
  there. Each view carries its label, so a reader knows what each table
  measures.

  Naming an alternative by hand is still supported, written A over B, and the
  standalone block uses it where both sides are deliberately pinned:

      Feral Cat
      :   [Thunderheart Cover]{.item} over [Nordrassil Headdress]{.item}

  Read A over B as what a player gains by taking A instead of B. The items are
  the `[Name]{.item}` references in the definition, in the order written, so
  the author writes no item id, no rate and no HTML.

  WHERE THE RATES COME FROM. `theme/filters/conversions.generated.lua`, written
  by `tools/extract_conversions.py` from data/facts/attack-power.yaml, crit.yaml
  and hit.yaml, and regenerated by `just regen`. NO RATE IS WRITTEN IN THIS
  FILE. A rate hardcoded here would render a page that looks authoritative and
  is wrong for most specs, which is the worst failure this project can produce.
  Every rate used is printed under the table with the fact file and the key it
  came from, so a converted figure can be audited without leaving the page.

  A spec this cannot find, an item name that does not resolve, a stat that
  differs and has no rate for that spec, a slot with no non-tier item in one of
  the two phase groups, a spec with no tier piece for a slot a tier set covers,
  or a spec whose ladder cannot be read, is a build error naming the document,
  the spec, the slot and the cause, exactly as an unresolvable item name is in items.lua. A view is
  never dropped silently where one was expected.

  This filter must run BEFORE items.lua, because it reads the plain names out of
  the `.item` spans, and BEFORE specs.lua, which turns the `Delta` term into a
  labelled field on the card. It must run AFTER tables.lua, whose scroll wrapper
  is not wanted here: nothing in this block scrolls sideways. The table is sized
  so it fits the card at every width, and where it cannot, the printed text is
  shortened rather than a scrollbar added.
]]

local itemdb = dofile(os.getenv("ITEMDB_LUA") or "theme/filters/itemdb.lua")
local CONVERSIONS = os.getenv("CONVERSIONS_LUA")
  or "theme/filters/conversions.generated.lua"

local LADDER = os.getenv("LADDER_LUA") or "theme/filters/ladder.generated.lua"

local function generated(path)
  local ok, table_ = pcall(dofile, path)
  if not ok or type(table_) ~= "table" then
    error(string.format(
      "delta.lua: cannot read %s.\nRun `just regen` to write it, and run the "
      .. "filters from the repository root.\n%s", path, tostring(table_)))
  end
  return table_
end

local conv = generated(CONVERSIONS)
local ladder = generated(LADDER)

local CONVERTIBLE = {}
for _, stat in ipairs(conv.convertible) do CONVERTIBLE[stat] = true end

-- Collected across the whole document, so a page with three bad references
-- reports three rather than the first. Emptied by Pandoc at the end.
local failures = {}

local function fail(where, message)
  failures[#failures + 1] = { where = where, message = message }
end

-- ------------------------------------------------------------------ arithmetic

-- Whole numbers print whole. Percentages carry two places, which is the
-- resolution at which a rating denominator of 22.08 says anything.
local function figure(value)
  if math.abs(value - math.floor(value + 0.5)) < 1e-9 then
    return string.format("%d", math.floor(value + 0.5))
  end
  return string.format("%.2f", value)
end

-- THE SYMBOL, NOT THE WORD. `percent` costs seven characters plus a space on
-- every figure, and a Net cell carries two figures against four baselines, so
-- the word was a column of its own repeated eight times. `%` is what a raider
-- reads anyway. No space before it.
local function percent_symbol(text)
  return (text:gsub("(%d)%s+percent", "%1%%"))
end

-- Signed, because every number in this table is a difference and an unsigned
-- one would be read as an absolute. Zero takes no sign: it is not a direction.
local function signed(value, unit, label)
  local text
  if value == 0 then
    text = "0"
  else
    text = (value > 0 and "+" or "-") .. figure(math.abs(value))
  end
  if unit == "percent" then
    text = text .. "%"
  elseif unit ~= "" then
    text = text .. " " .. unit
  end
  if label and label ~= "" then text = text .. " " .. label end
  return text
end

local function apply(rule, raw)
  if rule.op == "divide" then return raw / rule.by end
  return raw * rule.by
end

-- The item database mirrors a generic attack power bonus into both columns, so
-- a row whose two figures agree carries one bonus, not two. Counting the mirror
-- would double every attack power difference on such an item.
local function stat_of(row, key)
  local value = itemdb.number(row[key]) or 0
  if key == "ranged_attack_power" then
    local ap = itemdb.number(row.attack_power) or 0
    if ap ~= 0 and ap == value then return 0 end
  end
  return value
end

-- ------------------------------------------------------------------ the table

-- The stats that print in percent and carry no rating, each with the name its
-- row takes. See the note at the head of this file for why.
local PERCENT_ONLY = {
  melee_hit = "hit",
  melee_crit = "crit",
  spell_hit = "spell hit",
  spell_crit = "spell crit",
}

-- The label a stat is printed under, which is the itemdb label except where a
-- row reads in percent.
local function stat_label(key)
  return PERCENT_ONLY[key] or itemdb.LABEL[key]
end

-- Every stat this filter prints, in reading order, armor first. One shared
-- order is what lets four baselines be laid out as four column groups of one
-- table with `agility` on one line across all four.
local STAT_ORDER = { "armor" }
for _, pair in ipairs(itemdb.STATS) do
  STAT_ORDER[#STAT_ORDER + 1] = stat_label(pair[1])
end

-- One difference, resolved into a value per stat, running totals and the rates
-- it used. The values are keyed by the stat label rather than held as an
-- ordered list, because the caller merges four of these into one table.
local function compute(spec, a, b, where)
  local values, count = {}, 0
  local rates, seen_rate = {}, {}
  local totals, order = {}, {}

  -- The units this SPEC converts into, taken from its rules rather than from
  -- the pair being compared. It has to come from the spec: a baseline where the
  -- contributing stat happens to differ by zero fires no rule, and a per-pair
  -- test would then drop that baseline's total and leave the column blank.
  local converts_into = {}
  for _, rules in pairs(spec.rules or {}) do
    for _, rule in ipairs(rules) do
      converts_into[(rule.unit or "") .. "|" .. rule.label] = true
    end
  end

  local function contribute(label, unit, value)
    local key = unit .. "|" .. label
    if not totals[key] then
      totals[key] = { label = label, unit = unit, value = 0, parts = 0 }
      order[#order + 1] = key
    end
    totals[key].value = totals[key].value + value
    totals[key].parts = totals[key].parts + 1
  end

  local function row(name, difference, converted)
    if not values[name] then count = count + 1 end
    values[name] = { difference = difference, converted = converted }
  end

  -- Armor first, as it is on the tooltip, and as the sum the game shows.
  local armour = (itemdb.armour_of(a) or 0) - (itemdb.armour_of(b) or 0)
  if armour ~= 0 then
    contribute("armor", "", armour)
    row("armor", signed(armour, "", ""), "")
  end

  for _, pair in ipairs(itemdb.STATS) do
    local key, label = pair[1], stat_label(pair[1])
    local difference = stat_of(a, key) - stat_of(b, key)
    if difference ~= 0 then
      local rules = spec.rules[key]
      if rules then
        local parts, bare = {}, {}
        for _, rule in ipairs(rules) do
          local value = apply(rule, difference)
          contribute(rule.label, rule.unit, value)
          parts[#parts + 1] = signed(value, rule.unit, rule.label)
          -- The same figure with the stat name dropped, for a row that is
          -- named by the stat already. `crit` reading `+0.59%` says
          -- everything `+0.59% melee crit` on a `crit rating` row says.
          bare[#bare + 1] = signed(value, rule.unit, "")
          if not seen_rate[rule.rate] then
            seen_rate[rule.rate] = true
            rates[#rates + 1] = rule
          end
        end
        -- EVERY ROW READS THE SAME WAY: what the item carries on the left, what
        -- it turns into on the right. A hit or crit row used to print its
        -- percentage on the left and leave the right empty, which put a
        -- converted figure under the heading that says Change and broke the one
        -- reading rule the table has. The row is named `hit`, so the right cell
        -- drops the stat name and prints the percentage alone.
        if PERCENT_ONLY[key] then
          row(label, signed(difference, "", ""), table.concat(bare, " · "))
        else
          row(label, signed(difference, "", ""), table.concat(parts, " · "))
        end
      elseif CONVERTIBLE[key] then
        fail(where, string.format(
          "%s differs by %d and there is no rate for it for %s.\n"
          .. "      Add the figure to the fact file it belongs in, with its "
          .. "source, then run `just regen`.", label, difference, spec.name))
        row(label, signed(difference, "", ""), "")
      else
        -- No conversion exists for this stat. It still counts toward its own
        -- name, which is how a raw attack power line meets a converted one.
        contribute(label, "", difference)
        row(label, signed(difference, "", ""), "")
      end
    end
  end

  -- Every baseline states its total, whatever reached it.
  --
  -- This used to print only where two or more stats reached the same figure, on
  -- the reasoning that a single contributor is already on its own row. In a
  -- four-baseline table that produced a Net on three columns and a blank on the
  -- fourth, which reads as a claim that the fourth baseline has no net effect.
  -- It has one. On the Combat Rogue card the Tier 5 column differs by 0 agility,
  -- so attack power is the only contributor to attack power and crit the only
  -- contributor to crit, and the column nets plus 30 attack power and plus 0.59
  -- percent crit while printing nothing.
  --
  -- A reader compares four totals or none. A cell stays empty only where
  -- nothing converted at all, which is a real absence rather than a suppressed
  -- figure.
  local nets = {}
  for _, key in ipairs(order) do
    local total = totals[key]
    -- A unit the spec converts into is a bottom line and is stated on every
    -- baseline, so a reader compares four totals rather than three and a gap.
    -- A raw stat the spec converts nothing into, armor or stamina, is already
    -- on its own row once and is not repeated here.
    if converts_into[key] and total.value ~= 0 then
      nets[#nets + 1] = signed(total.value, total.unit, total.label)
    end
  end

  return values, count, nets, rates
end

-- ------------------------------------------------------------------ rendering

local function plain(text, class)
  local inline = class
    and pandoc.Span(pandoc.Str(text), pandoc.Attr("", { class }))
    or pandoc.Str(text)
  return pandoc.Plain(inline)
end

-- The view label, carrying the acquisition route of the baseline as a class as
-- well as in its text. A gated baseline reads as gated at a glance and still
-- reads as gated with no stylesheet, because the route is words and not color.
local function view_label(label, route)
  local classes = { "delta-view" }
  if route then
    classes[#classes + 1] = "delta-route-" .. route
    if route ~= "drop" then classes[#classes + 1] = "delta-view-gated" end
  end
  return pandoc.Plain(pandoc.Span(pandoc.Str(label), pandoc.Attr("", classes)))
end

local function text_cell(text, align, colspan, class)
  local content = text == ""
    and { pandoc.Plain(pandoc.List({})) }
    or { pandoc.Plain(pandoc.Str(text)) }
  return pandoc.Cell(content, align, 1, colspan or 1,
    pandoc.Attr("", class and { class } or {}))
end

-- ONE FIGURE PER LINE, NOT ONE RUN. Two totals joined by a middot wrapped
-- mid-phrase, so `melee crit` landed alone on the second line and the two
-- figures did not read as two. Each figure is now its own block, which also
-- lets the Net row line up across the baselines the way the stat rows do. Each
-- carries a class of its own, because the size is set on the figure and not on
-- the cell.
local function lines_cell(texts, align, colspan, class)
  local content = {}
  for _, text in ipairs(texts) do
    content[#content + 1] = pandoc.Plain(pandoc.Span(pandoc.Str(text),
      pandoc.Attr("", { "delta-net-figure" })))
  end
  if #content == 0 then content = { pandoc.Plain(pandoc.List({})) } end
  return pandoc.Cell(content, align, 1, colspan or 1,
    pandoc.Attr("", class and { class } or {}))
end

-- The stats any of the views differ on, once each, in the shared order. A stat
-- one view does not differ on still takes its place on that view's line, as a
-- zero, so the reader reads across the row and not down four separate tables.
local function stats_across(views)
  local names = {}
  for _, name in ipairs(STAT_ORDER) do
    local present = false
    for _, view in ipairs(views) do
      if view.values[name] then present = true end
    end
    if present then names[#names + 1] = name end
  end
  return names
end

-- The column head for one baseline: what the view measures, then the baseline
-- itself, which keeps its own span or link so items.lua gives it its tooltip.
-- A hand-named pair carries no view label, so it reads `over <baseline>`.
local function view_head(view)
  local blocks = pandoc.List({})
  if view.label then
    blocks:insert(view_label(view.label, view.route))
    blocks:insert(pandoc.Plain(view.baseline))
  else
    blocks:insert(pandoc.Plain(pandoc.List({
      pandoc.Span(pandoc.Str("over"), pandoc.Attr("", { "delta-over" })),
      pandoc.Str(" "), view.baseline,
    })))
  end
  return pandoc.Cell(blocks, pandoc.AlignLeft, 1, 2,
    pandoc.Attr("", { "delta-view-head" }))
end

-- ONE TABLE, NOT ONE PER BASELINE. Separate tables in narrow columns each
-- sized their own rows, so the same stat sat on different lines, each
-- printed the stat name and the rates again, and each was narrow enough to need
-- a scrollbar of its own. One table with a column group per baseline aligns the
-- rows by construction, writes each stat name once, and has the whole card.
local function table_of(names, views)
  local aligns = { { pandoc.AlignLeft, nil } }
  local groups = { pandoc.Cell({ pandoc.Plain(pandoc.Str("Stat")) },
    pandoc.AlignLeft, 2, 1, pandoc.Attr("", { "delta-stat-head" })) }
  local units = {}
  for _, view in ipairs(views) do
    aligns[#aligns + 1] = { pandoc.AlignRight, nil }
    aligns[#aligns + 1] = { pandoc.AlignLeft, nil }
    groups[#groups + 1] = view_head(view)
    units[#units + 1] = text_cell("Change", pandoc.AlignRight, 1, "delta-unit-head")
    units[#units + 1] = text_cell("Converted", pandoc.AlignLeft, 1, "delta-unit-head")
  end
  local head = pandoc.TableHead({ pandoc.Row(groups), pandoc.Row(units) })

  local rows = {}
  for _, name in ipairs(names) do
    -- EVERY ROW IS THE SAME SHAPE. The rating the item carries on the left, what
    -- it converts into on the right, hit and crit included. They used to be the
    -- exception, printing a percentage on the left and nothing on the right, and
    -- the exception cost a special case here, another in the narrow layout, and
    -- a converted figure standing under a heading that reads Change.
    local cells = { text_cell(name, pandoc.AlignLeft, 1, "delta-stat") }
    for _, view in ipairs(views) do
      local value = view.values[name]
      cells[#cells + 1] = text_cell(value and value.difference or "0",
        pandoc.AlignRight, 1, "delta-raw")
      cells[#cells + 1] = text_cell(value and value.converted or "",
        pandoc.AlignLeft, 1, "delta-converted")
    end
    rows[#rows + 1] = pandoc.Row(cells)
  end

  -- One Net line across the bottom, one figure per line per baseline. THE NET
  -- SITS IN THE CONVERTED COLUMN, NOT ACROSS THE PAIR. A cell spanning the
  -- Change and Converted columns began at the left edge of the Change column,
  -- where nothing above it starts: the Change figures are right-aligned in
  -- their own column and the Converted text starts one column further right. A
  -- net is a converted quantity, stated in attack power and in percent exactly
  -- as the Converted cells above it are, so it takes that column and the
  -- Change column is left empty. A baseline with no net keeps both cells and
  -- stays blank, so the row cannot collapse or shift its neighbours.
  local foot = pandoc.TableFoot({})
  local any = false
  for _, view in ipairs(views) do
    if #view.nets > 0 then any = true end
  end
  if any then
    local cells = { text_cell("Net", pandoc.AlignLeft, 1, "delta-net-label") }
    for _, view in ipairs(views) do
      cells[#cells + 1] = text_cell("", pandoc.AlignRight, 1, "delta-raw")
      cells[#cells + 1] = lines_cell(view.nets,
        pandoc.AlignLeft, 1, "delta-net-value")
    end
    foot = pandoc.TableFoot({ pandoc.Row(cells, pandoc.Attr("", { "delta-net-row" })) })
  end

  return pandoc.Table(pandoc.Caption({}), aligns, head,
    { pandoc.TableBody(rows, {}, 0) }, foot)
end

-- One block for one spec's reading of one item, holding every baseline it is
-- measured against. The item under discussion keeps the author's own span, so
-- items.lua links it and gives it its tooltip.
local function render(spec, a_span, views, rates, named, absent)
  local blocks = pandoc.List({})

  local head = pandoc.List({})
  if named then
    head:insert(plain(spec.name, "delta-spec"))
  end
  head:insert(pandoc.Plain(pandoc.List({
    a_span, pandoc.Str(" "),
    pandoc.Span(pandoc.Str("in " .. spec.name .. " terms"),
      pandoc.Attr("", { "delta-terms" })),
  })))
  blocks:insert(pandoc.Div(head, pandoc.Attr("", { "delta-head" })))

  blocks:insert(pandoc.Div({ table_of(stats_across(views), views) },
    pandoc.Attr("", { "delta-grid" })))

  -- A baseline the workbook has nothing to fill. It is stated rather than left
  -- as a missing column, because a card with three views beside a card with
  -- four reads as an oversight, and the absence is itself the answer: nothing
  -- else in the slot competes.
  if absent and #absent > 0 then
    local names = {}
    for _, label in ipairs(absent) do names[#names + 1] = label end
    blocks:insert(pandoc.Div(
      { plain("No " .. table.concat(names, " and no ")
        .. " exists for this spec outside its tier sets and outside arena, so "
        .. "that comparison is not shown.") },
      pandoc.Attr("", { "delta-absent" })))
  end

  -- Every rate that produced a figure above, with the file and the key it was
  -- read from. A converted number with no visible rate is not auditable.
  -- ONCE PER CARD. The rate belongs to the spec, not to the baseline, so four
  -- baselines printed the same list four times. The rates of every view are
  -- merged and printed under the one table.
  local cited = pandoc.List({
    pandoc.Div({ plain("Rates") }, pandoc.Attr("", { "delta-rates-label" })),
  })
  -- One line, not one line each. Five sentences of the form "N per stat for a
  -- warrior" repeat the spec on every row when the table header above already
  -- names it, and they pushed the citation block taller than the figures it
  -- explains. The per-spec suffix is dropped and the rates are joined inline.
  local inline = pandoc.List({})
  for i, rule in ipairs(rates) do
    -- The citation is the link, not printed text. Reading the file path and the
    -- key path on every line buried the rate itself, which is the part a reader
    -- is checking. The file is one click away and the key is in the title.
    local file, key = rule.source:match("^(%S+)%s*::%s*(.+)$")
    if not file then file, key = rule.source, rule.source end
    -- "2 attack power per strength for a warrior" becomes "2 attack power per
    -- strength". The header above already says whose terms these are. The
    -- generated rate spells `percent` out, because the fact files it is read
    -- from are read as documents; a card prints the symbol, so it is converted
    -- here rather than in the fact file or the generator.
    local label = percent_symbol(rule.rate:gsub("%s+for an?%s+[%w%s]+$", ""))
    local rate = percent_symbol(rule.rate)
    if i > 1 then
      inline:insert(pandoc.Span(pandoc.Str("\u{00B7}"),
        pandoc.Attr("", { "delta-rate-sep" })))
    end
    inline:insert(pandoc.Link(
      pandoc.Str(label),
      "../" .. file,
      rate .. "  |  " .. key,
      pandoc.Attr("", { "delta-rate" })
    ))
  end
  cited:insert(pandoc.Div({ pandoc.Plain(inline) },
    pandoc.Attr("", { "delta-rate-row" })))
  blocks:insert(pandoc.Div(cited, pandoc.Attr("", { "delta-rates" })))

  return pandoc.Div(blocks, pandoc.Attr("", { "delta-block" }))
end

-- ------------------------------------------------------------------ baselines

-- One ladder entry into a row shaped like an items.csv row.
--
-- Every helper that turns a generated-ladder entry into a link with a tooltip
-- moved to itemdb.lua when shortlist.lua needed the same thing. A spec page and
-- a comparison card show the same crafted goggle, and one of them showing a
-- browser's plain `title` tooltip beside the other's styled bubble is the exact
-- defect that machinery was written to remove.
local baseline_row = itemdb.ladder_row
local function baseline_inline(entry, row, held)
  return itemdb.ladder_inline(entry, row, held, "delta-tip")
end

local function known_ladders()
  local names = {}
  for _, entry in pairs(ladder.specs) do names[#names + 1] = entry.name end
  table.sort(names)
  return names
end

-- The five slots a Tier 4, Tier 5 or Tier 6 set covers. A Neck, Back, Wrist,
-- Waist, Finger, Feet, Trinket or Ranged comparison has no tier baseline in
-- either tier, so it renders the views that exist and does not fail for the
-- ones that cannot exist.
local TIER_SLOTS = {
  Head = true, Shoulder = true, Chest = true, Hands = true, Legs = true,
}

-- WHICH LADDER A WEAPON READS. items.csv files every weapon under the one slot
-- `Weapon` and records the hand the database gives it. The workbook files a
-- weapon by the hand a raider puts it in, so the hand is what picks the ladder,
-- and the generated table keys a weapon by both. The choice between the
-- workbook's sections is made once, in `WEAPON_SECTIONS` in
-- tools/extract_ladder.py, which is where the reasoning is written down. This
-- is only the other half of the same key.
local HAND_KEY = {
  ["Main Hand"] = "MainHand", ["One Hand"] = "OneHand",
  ["Off Hand"] = "OffHand", ["Two Hand"] = "TwoHand",
}

-- The two by two, in the order the card reads: this phase before the phase
-- before it, and the tier piece before the off-piece in each row. `list` marks
-- the two cells the generated table holds as ranked candidates rather than as
-- one item, because the item under discussion is frequently the best off-piece
-- in its own slot.
local BASELINES = {
  { key = "tier6", label = "Tier 6", tier = 6 },
  { key = "phase3", label = "best Phase 3 off-piece", list = true },
  { key = "tier5", label = "Tier 5", tier = 5 },
  { key = "prephase", label = "best pre-phase off-piece", list = true },
}

-- The first candidate in one off-piece cell that is not the item under
-- discussion. EXCLUDING THAT ITEM IS NOT OPTIONAL: it is the top Phase 3 head
-- on seven of the eight ladders the worked example uses, so taking rank one
-- blindly would print a card comparing an item with itself.
local function first_other(candidates, item_id)
  for _, candidate in ipairs(candidates or {}) do
    if tostring(candidate.item_id) ~= item_id then return candidate end
  end
  return nil
end

-- The four views one item earns for one spec. All four derived, none named by
-- the author. Returns nil after recording why, so nothing renders
-- half-answered.
local function views_for(spec, row, where)
  local slot = row.slot or ""
  local rungs = ladder.specs[spec.name:lower()]
  if not rungs then
    fail(where, string.format(
      "no ladder for %s in %s.\n      Known ladders: %s.\n"
      .. "      Add the spec to SPECS in tools/extract_ladder.py and run "
      .. "`just regen`, or name both items as [A]{.item} over [B]{.item}.",
      spec.name, LADDER, table.concat(known_ladders(), ", ")))
    return nil
  end
  local key = slot
  if slot == "Weapon" then
    local hand = HAND_KEY[row.hand_type or ""]
    if not hand then
      fail(where, string.format(
        "%s is a weapon and items.csv gives it no hand, so which of the "
        .. "workbook's weapon sections is its ladder cannot be decided.\n"
        .. "      Fix the item database or the transform, then run `just "
        .. "regen`.", row.name))
      return nil
    end
    key = "Weapon:" .. hand
  end
  local slots = rungs.slots[key] or {}

  -- A tier set is five pieces. Inside those five slots a missing piece is a
  -- defect in the generated table and the build stops naming the spec and the
  -- slot; outside them there is nothing to miss.
  if TIER_SLOTS[slot] then
    for _, pair in ipairs({ { 5, rungs.set5 }, { 6, rungs.set6 } }) do
      local tier, set = pair[1], pair[2]
      if not slots["tier" .. tier] then
        fail(where, string.format(
          "%s has no Tier %d piece for %s in %s, and %s is a five-piece set "
          .. "covering head, shoulder, chest, hands and legs.\n"
          .. "      Run `just regen`.", spec.name, tier, slot, LADDER, set))
        return nil
      end
    end
  end

  -- AN EMPTY BASELINE LIST IS A FACT, NOT A DEFECT, and it used to stop the
  -- build. The Warlock hands slot is the case that proved it: the only two
  -- Phase 3 rows on both warlock tabs are the tier piece itself and a Season 3
  -- arena piece, and arena armor is excluded by a recorded ruling, so there is
  -- genuinely no non-tier Phase 3 alternative. That is worth SAYING on the
  -- card, because it means the token is the only route to the slot, and the
  -- `absent` path below already says exactly that.
  --
  -- The check that a spec has its tier pieces stays hard above, because a
  -- missing tier piece IS a defect in the generated table. And a card with no
  -- baseline at all still fails below, so nothing renders unmeasured.

  -- The four cells are disjoint by construction, so two of them can never
  -- resolve to one item and nothing here merges views. What is still needed is
  -- the exclusion of the item under discussion, which would otherwise be
  -- compared with itself.
  local out, absent = {}, {}
  for _, cell in ipairs(BASELINES) do
    local baseline
    if cell.list then
      baseline = first_other(slots[cell.key] or {}, row.item_id)
    elseif slots[cell.key] and tostring(slots[cell.key].item_id) ~= row.item_id then
      baseline = slots[cell.key]
    end
    if not baseline then
      -- A BASELINE THAT DOES NOT EXIST IS SAID, NOT OMITTED. Dropping the
      -- column leaves a card with three views where its neighbor has four, and
      -- a reader counts columns rather than reading labels. It is also the more
      -- interesting fact of the two: no other Phase 3 leather head exists for a
      -- rogue or a feral outside the tier sets and outside arena, which means
      -- the tier head is unopposed in the slot.
      absent[#absent + 1] = cell.label
    else
      -- The route is on the label of every view, gated or not, because the
      -- baseline a raider cannot obtain must not read as one he holds.
      local label = cell.label
      if baseline.location and baseline.location ~= "" then
        label = label .. ", " .. baseline.location
      end
      out[#out + 1] = {
        entry = baseline, label = "Over " .. label,
        route = baseline.route or "drop",
      }
    end
  end

  if #out == 0 then
    fail(where, string.format(
      "%s is every derived %s baseline for %s, so it has nothing to be "
      .. "measured against. Name the baseline instead, as [A]{.item} over "
      .. "[B]{.item}.", row.name, slot, spec.name))
    return nil
  end
  return out, absent
end

-- ------------------------------------------------------------------- assembly

-- The `.item` references in a definition, in the order written.
local function item_spans(blocks)
  local found = {}
  pandoc.Blocks(blocks):walk({
    Span = function(span)
      if span.classes:includes("item") then found[#found + 1] = span end
    end,
  })
  return found
end

local function spec_named(name)
  return conv.specs[itemdb.fold(name):lower()]
end

local function known_specs()
  local names = {}
  for _, entry in pairs(conv.specs) do names[#names + 1] = entry.name end
  table.sort(names)
  return names
end

-- One `.item` span into its item table row, or nil and the reason recorded.
local function row_of(span, where)
  local name = itemdb.fold(pandoc.utils.stringify(span.content))
  local row, why = itemdb.resolve_span(span)
  if row then return row end
  local lines = { string.format("[%s]{.item}  %s", name, why) }
  local hits = itemdb.near_matches(name)
  for i = 1, math.min(#hits, 3) do
    lines[#lines + 1] = "      did you mean: " .. hits[i]
  end
  fail(where, table.concat(lines, "\n"))
  return nil
end

-- One comparison, A against B, resolved into the column group it renders as.
-- Returns nil after recording why.
local function one_view(spec, a, b_span, b, where, label, route)
  local values, count, nets, rates = compute(spec, a, b, where)
  if count == 0 then
    fail(where, string.format(
      "%s and %s carry the same stat line, so there is nothing to compare.",
      a.name, b.name))
    return nil
  end
  return { values = values, nets = nets, rates = rates,
    baseline = b_span, label = label, route = route }
end

-- The rates of every view, once each. They are a property of the spec, so the
-- four views repeat them, and the reader needs the list once.
local function merged_rates(views)
  local out, seen = {}, {}
  for _, view in ipairs(views) do
    for _, rule in ipairs(view.rates) do
      if not seen[rule.rate] then
        seen[rule.rate] = true
        out[#out + 1] = rule
      end
    end
  end
  return out
end

-- One definition, for one spec, into the blocks it renders as. One item
-- reference derives every baseline and renders up to four views; two item
-- references are the author's own pair and render one. Returns nil after
-- recording why, so the rest of the document still gets checked.
local function build(spec_name, blocks, where, named)
  local spec = spec_named(spec_name)
  if not spec then
    fail(where, string.format(
      "no spec named %q in %s.\n      Known specs: %s.\n"
      .. "      Add it to SPECS in tools/extract_conversions.py and run "
      .. "`just regen`.", spec_name, CONVERSIONS,
      table.concat(known_specs(), ", ")))
    return nil
  end

  local spans = item_spans(blocks)
  if #spans ~= 1 and #spans ~= 2 then
    fail(where, string.format(
      "%s names %d item reference(s); a delta takes one, [A]{.item}, whose "
      .. "baselines are derived, or two, [A]{.item} over [B]{.item}.",
      spec.name, #spans))
    return nil
  end

  local a = row_of(spans[1], where)
  if not a then return nil end

  if #spans == 2 then
    local b = row_of(spans[2], where)
    if not b then return nil end
    local view = one_view(spec, a, spans[2], b, where, nil, nil)
    if not view then return nil end
    return pandoc.List({
      render(spec, spans[1], { view }, merged_rates({ view }), named) })
  end

  local derived, absent = views_for(spec, a, where)
  if not derived then return nil end

  local views = {}
  for _, view in ipairs(derived) do
    local b, held = baseline_row(view.entry)
    if not b then
      fail(where, string.format(
        "the baseline %s for %s carries no stat line in %s and is not in %s.\n"
        .. "      Run `just regen`.", view.entry.name, spec.name, LADDER,
        itemdb.ITEMS))
      return nil
    end
    local built = one_view(spec, a, baseline_inline(view.entry, b, held), b,
      where, view.label, view.route)
    if not built then return nil end
    views[#views + 1] = built
  end
  return pandoc.List({
    render(spec, spans[1], views, merged_rates(views), named, absent) })
end

-- ---------------------------------------------------------------- the filters

-- Standalone form. Each term is a spec, each definition is one pair.
local function standalone(div)
  local out = pandoc.List({})
  for _, block in ipairs(div.content) do
    if block.t == "DefinitionList" then
      for _, entry in ipairs(block.content) do
        local spec_name = pandoc.utils.stringify(entry[1])
        local blocks = pandoc.List({})
        for _, definition in ipairs(entry[2]) do blocks:extend(definition) end
        local built = build(spec_name, blocks, "::: {.delta} " .. spec_name, true)
        if built then out:extend(built) end
      end
    else
      out:insert(block)
    end
  end
  div.content = out
  return div
end

-- Card form. The spec is the card's heading, and the rendered block replaces
-- the body of the `Delta` term, which specs.lua then labels like any field.
local function on_cards(div)
  local heading
  local out = pandoc.List({})
  for _, block in ipairs(div.content) do
    if block.t == "Header" then
      heading = pandoc.utils.stringify(block.content)
      out:insert(block)
    elseif block.t == "DefinitionList" and heading then
      -- Rebuilt rather than mutated in place: a nested table read out of the
      -- AST is a copy, so an assignment into it would be discarded silently.
      local entries = {}
      for _, entry in ipairs(block.content) do
        local term, definitions = entry[1], entry[2]
        if pandoc.utils.stringify(term) == "Delta" then
          local blocks = pandoc.List({})
          for _, definition in ipairs(definitions) do blocks:extend(definition) end
          local built = build(heading, blocks, "the " .. heading .. " card", false)
          -- One definition holding every view, so a card with two views keeps
          -- them under the one `Delta` label rather than repeating it.
          if built then definitions = { built } end
        end
        entries[#entries + 1] = { term, definitions }
      end
      out:insert(pandoc.DefinitionList(entries))
    else
      out:insert(block)
    end
  end
  div.content = out
  return div
end

function Div(div)
  if div.classes:includes("delta") then return standalone(div) end
  if div.classes:includes("specs") then return on_cards(div) end
  return nil
end

function Pandoc(doc)
  if #failures == 0 then return doc end
  local source = pandoc.utils.stringify(doc.meta.srcpath or "")
  if source == "" then source = "this document" end
  local lines = { string.format(
    "delta.lua: %d delta(s) in docs/%s do not resolve.", #failures, source) }
  for _, failure in ipairs(failures) do
    lines[#lines + 1] = "  " .. failure.where .. ":"
    lines[#lines + 1] = "      " .. failure.message
  end
  lines[#lines + 1] =
    "A converted figure with no rate behind it would look authoritative and be "
    .. "wrong, so no page is written."
  error(table.concat(lines, "\n"))
end
