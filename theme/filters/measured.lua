--[[
  Put the measured slot ladder on every claimant card that has one, and the
  denial reading above the cards.

  The derived-orderings ruling, data/judgments/derived-orderings.yaml, lets a
  page sort a slot's candidates by simulated delta and read a denial cost as
  this item minus the next best available. The measurements live in
  theme/filters/measured.generated.lua, written by
  tools/extract_measured_ladders.py from data/facts/ladder-sims.yaml: each
  single-item slot's workbook candidates priced as variants of the spec's
  TIER profile at the default boss armor, the worn item reproducing the tier
  figure in sim-figures.yaml. Weapons, rings, trinkets and ranged have their
  own enumerated rounds on the sim pages and this filter leaves their pages
  alone.

  TWO RENDERINGS FROM ONE TABLE.

  ON A CLAIMANT CARD, a `Measured` field: the slot's ladder sorted best
  first, each row carrying its absolute figure and its difference against
  the item under discussion, with the one standard error of a difference of
  two runs beside it. The card also states the spec's entry, tier and
  best-in-slot figures, so the reader sees how much of the spec's whole
  progression this one slot moves. Rows are marked where they are the item
  under discussion, the item the tier profile wears, or an item the spec's
  best-in-slot set wears; the best-in-slot marking comes from
  bis.generated.lua, the same source the standing does.

  ABOVE THE CARDS, a denial reading: for every measured spec whose ladder
  holds the item, what routing it elsewhere costs at the tier set. Where the
  item is the spec's best measured candidate, that is the gap to the next
  best; where it is not, the gap to the slot's best is stated as negative.
  Specs are sorted by that value, and two specs whose readings sit within
  two combined standard errors of each other are printed as tied, because
  the measurement cannot separate them. This is an ordering derived from
  measurement; who receives the drop remains the council's call, which is
  why the block says which it is.

  A SPEC OR SLOT WITH NO MEASUREMENT RENDERS EXACTLY AS BEFORE. The ladder
  round lands one spec at a time, and a card whose spec is not in the
  generated table, or whose slot the round does not cover, keeps its EPV
  delta and nothing else. Absence is expected here and is not an error; a
  malformed generated table is.

  This filter runs AFTER delta.lua, whose rendering it never touches, and
  BEFORE specs.lua, which turns the inserted `Measured` term into a labelled
  field like any other. It reads plain item names, never `.item` spans, the
  sim pages' convention for measured tables, so items.lua has nothing to
  resolve inside it.
]]

local itemdb = dofile(os.getenv("ITEMDB_LUA") or "theme/filters/itemdb.lua")

local MEASURED = os.getenv("MEASURED_LUA")
  or "theme/filters/measured.generated.lua"
local BIS = os.getenv("BIS_LUA") or "theme/filters/bis.generated.lua"

local function generated(path)
  local ok, table_ = pcall(dofile, path)
  if not ok or type(table_) ~= "table" then
    error(string.format(
      "measured.lua: cannot read %s.\nRun `just regen` to write it, and run "
      .. "the filters from the repository root.\n%s", path, tostring(table_)))
  end
  return table_
end

local measured = generated(MEASURED)
local bis = generated(BIS)

-- The slots the ladder round covers, items.csv slot vocabulary lowered.
-- Everything else, weapons and rings among them, has its own enumerated
-- round and this filter must not touch its pages.
local SLOTS = {
  head = true, neck = true, shoulder = true, back = true, chest = true,
  wrist = true, hands = true, waist = true, legs = true, feet = true,
}

-- ---------------------------------------------------------------- formatting

local function fig(value)
  return string.format("%.1f", value)
end

local function signed(value)
  if value >= 0 then return "+" .. fig(value) end
  return "-" .. fig(-value)
end

-- The one standard error of a difference of two runs.
local function combined_se(a, b)
  return math.sqrt(a * a + b * b)
end

local function plain(inlines)
  if type(inlines) == "string" then
    return pandoc.Plain({ pandoc.Str(inlines) })
  end
  return pandoc.Plain(inlines)
end

-- A cell of one table, plain text or an inline list.
local function cell(content)
  return { plain(content) }
end

local function simple_table(headers, aligns, rows)
  local header_cells = {}
  for _, text in ipairs(headers) do
    header_cells[#header_cells + 1] = plain({ pandoc.Str(text) })
  end
  local widths = {}
  for i = 1, #headers do widths[i] = 0 end
  return pandoc.utils.from_simple_table(pandoc.SimpleTable(
    {}, aligns, widths, header_cells, rows))
end

-- ------------------------------------------------------------------- lookups

local function ladder_for(spec_display, slot_key)
  local block = measured[spec_display]
  if not block or not block.slots then return nil end
  return block.slots[slot_key], block.anchors
end

local function row_for(rows, item_id)
  for index, row in ipairs(rows) do
    if row.id == item_id then return row, index end
  end
  return nil
end

local function in_bis(spec_display, item_id)
  local set = bis[spec_display]
  return set and set[item_id] or false
end

-- --------------------------------------------------------------- card blocks

-- The markers a ladder row carries after its name, each one a claim with a
-- source: the page's own item, the item the tier profile wears, an item the
-- spec's best-in-slot set wears.
local function marked_name(row, spec_display, page_id)
  local inlines = pandoc.List({ pandoc.Str(row.name) })
  local marks = {}
  if row.id == page_id then marks[#marks + 1] = "this item" end
  if row.worn then marks[#marks + 1] = "worn at the tier set" end
  if in_bis(spec_display, row.id) then
    marks[#marks + 1] = "in the best-in-slot set"
  end
  if #marks > 0 then
    inlines:insert(pandoc.Space())
    inlines:insert(pandoc.Emph({
      pandoc.Str("(" .. table.concat(marks, ", ") .. ")") }))
  end
  return inlines
end

-- The spread sentence: what the spec measures at its three anchors, so the
-- reader sees the size of this slot's movement against the whole climb.
local function spread_sentence(anchors)
  if not (anchors and anchors.entry and anchors.tier and anchors.bis) then
    return nil
  end
  return plain(string.format(
    "This spec measures %s at entry, %s at the tier set and %s at best in "
    .. "slot.", fig(anchors.entry), fig(anchors.tier), fig(anchors.bis)))
end

-- The `Measured` field's body for one card: the spread sentence and the
-- ladder table, rows best first, each against the item under discussion.
local function card_body(spec_display, rows, anchors, page_id)
  local blocks = pandoc.List({})
  local spread = spread_sentence(anchors)
  if spread then blocks:insert(spread) end

  local page_row = row_for(rows, page_id)
  local aligns, headers
  if page_row then
    headers = { "Item", "DPS", "Against this item" }
    aligns = { pandoc.AlignLeft, pandoc.AlignRight, pandoc.AlignRight }
  else
    blocks:insert(plain(
      "The measured ladder for this slot does not hold this item, so the "
      .. "rows below carry no difference against it."))
    headers = { "Item", "DPS" }
    aligns = { pandoc.AlignLeft, pandoc.AlignRight }
  end

  local body = {}
  for _, row in ipairs(rows) do
    local cells = {
      cell(marked_name(row, spec_display, page_id)),
      cell(string.format("%s \u{00b1} %.2f", fig(row.dps), row.se)),
    }
    if page_row then
      if row.id == page_id then
        cells[#cells + 1] = cell(signed(0))
      else
        cells[#cells + 1] = cell(string.format(
          "%s \u{00b1} %.2f", signed(row.dps - page_row.dps),
          combined_se(row.se, page_row.se)))
      end
    end
    body[#body + 1] = cells
  end
  blocks:insert(simple_table(headers, aligns, body))
  return blocks
end

-- --------------------------------------------------------------- the summary

-- One spec's denial reading: what routing the item elsewhere costs at the
-- tier set, or how far the item sits behind the slot's best.
local function denial_of(rows, page_id)
  local page_row, index = row_for(rows, page_id)
  if not page_row then return nil end
  if index == 1 then
    local next_row = rows[2]
    if not next_row then return nil end
    return {
      value = page_row.dps - next_row.dps,
      se = combined_se(page_row.se, next_row.se),
      against = next_row.name,
      best = true,
    }
  end
  local best = rows[1]
  return {
    value = page_row.dps - best.dps,
    se = combined_se(page_row.se, best.se),
    against = best.name,
    best = false,
  }
end

local function reading_cell(entry)
  local text
  if entry.best then
    text = string.format("%s \u{00b1} %.2f over the next best, %s",
      signed(entry.value), entry.se, entry.against)
  else
    text = string.format("%s \u{00b1} %.2f behind %s",
      signed(entry.value), entry.se, entry.against)
  end
  local inlines = pandoc.List({ pandoc.Str(text) })
  if entry.tied_with then
    inlines:insert(pandoc.Space())
    inlines:insert(pandoc.Emph({
      pandoc.Str("(tied with " .. entry.tied_with .. ")") }))
  end
  return inlines
end

-- The denial block above the cards: every measured spec whose ladder holds
-- the item, sorted by what denying it costs, ties named where the
-- measurement cannot separate two specs.
local function summary_div(page_id, slot_key)
  local entries = {}
  for spec_display in pairs(measured) do
    local rows = ladder_for(spec_display, slot_key)
    if rows then
      local entry = denial_of(rows, page_id)
      if entry then
        entry.spec = spec_display
        entry.standing = in_bis(spec_display, page_id) and "BIS" or "Upgrade"
        entries[#entries + 1] = entry
      end
    end
  end
  if #entries == 0 then return nil end
  table.sort(entries, function(a, b)
    if a.value ~= b.value then return a.value > b.value end
    return a.spec < b.spec
  end)
  for index = 2, #entries do
    local above, this = entries[index - 1], entries[index]
    if math.abs(above.value - this.value)
        <= 2 * combined_se(above.se, this.se) then
      this.tied_with = above.spec
    end
  end

  local body = {}
  for _, entry in ipairs(entries) do
    body[#body + 1] = {
      cell(entry.spec),
      cell(entry.standing),
      cell(reading_cell(entry)),
    }
  end
  local blocks = pandoc.List({
    plain(
      "What routing this item elsewhere costs, each spec measured on its "
      .. "tier profile with only this slot moving. An ordering derived from "
      .. "measurement; who receives the drop is the council's call."),
    simple_table({ "Spec", "Standing", "At the tier set" },
      { pandoc.AlignLeft, pandoc.AlignLeft, pandoc.AlignLeft }, body),
  })
  return pandoc.Div(blocks, pandoc.Attr("", { "measured-summary" }))
end

-- ------------------------------------------------------------------ the walk

-- Insert the `Measured` entry into each claimant card's definition list.
-- specs.lua consumes strict Header and DefinitionList pairs, so the block
-- must travel inside the list to land inside the card.
local function on_specs(div, slot_key, page_id)
  local heading
  local out = pandoc.List({})
  for _, block in ipairs(div.content) do
    if block.t == "Header" then
      heading = pandoc.utils.stringify(block.content)
      out:insert(block)
    elseif block.t == "DefinitionList" and heading then
      local rows, anchors = ladder_for(heading, slot_key)
      if rows and #rows > 0 then
        local entries = {}
        for _, entry in ipairs(block.content) do
          entries[#entries + 1] = entry
        end
        entries[#entries + 1] = {
          pandoc.Inlines({ pandoc.Str("Measured") }),
          { card_body(heading, rows, anchors, page_id) },
        }
        out:insert(pandoc.DefinitionList(entries))
      else
        out:insert(block)
      end
      heading = nil
    else
      out:insert(block)
    end
  end
  div.content = out
  return div
end

function Div(div)
  if not div.classes:includes("subject") then return nil end

  -- The item under discussion is the first `.item` reference the container
  -- carries. A reference that does not resolve is items.lua's to report;
  -- this filter walks away quietly rather than reporting it twice.
  local page_span
  div.content:walk({
    Span = function(span)
      if not page_span and span.classes:includes("item") then
        page_span = span
      end
    end,
  })
  if not page_span then return nil end
  local row = itemdb.resolve_span(page_span)
  if not row then return nil end

  local slot_key = tostring(row.slot or ""):lower()
  if not SLOTS[slot_key] then return nil end
  local page_id = tonumber(row.item_id)
  if not page_id then return nil end

  local summary = summary_div(page_id, slot_key)
  local out = pandoc.List({})
  for _, block in ipairs(div.content) do
    if block.t == "Div" and block.classes:includes("specs") then
      if summary then out:insert(summary) end
      out:insert(on_specs(block, slot_key, page_id))
    else
      out:insert(block)
    end
  end
  div.content = out
  return div
end

-- Meta runs first so a page in docs/items/ resolves items through the same
-- root every other filter uses; see the note at the foot of delta.lua.
function Meta(meta)
  if meta.root then itemdb.root = pandoc.utils.stringify(meta.root) end
  itemdb.current_page = pandoc.utils.stringify(meta.srcpath or "")
  return meta
end

return {
  { Meta = Meta },
  { Div = Div },
}
