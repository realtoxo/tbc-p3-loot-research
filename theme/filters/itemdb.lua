--[[
  The item table, read once and shared. Not a filter.

  Two filters resolve an item name against data/facts/items.csv: items.lua,
  which turns a name into a linked tooltip, and delta.lua, which turns a pair of
  names into a converted difference. A second resolver would be a second answer
  to "does this name exist", and the two would disagree the day the CSV gains a
  column. There is one, and it lives here.

  Load it with dofile from the repository root, or set ITEMDB_LUA:

      local itemdb = dofile(os.getenv("ITEMDB_LUA")
        or "theme/filters/itemdb.lua")

  What it provides: `parse_csv`, `fold`, `STATS` and `LABEL`, the `by_name`,
  `by_id` and `ambiguous` indexes, `resolve`, `near_matches`, `number` and
  `armour_of`.
]]

local M = {}

M.ITEMS = os.getenv("ITEMS_CSV") or "data/facts/items.csv"
M.EFFECTS = os.getenv("ITEM_EFFECTS_CSV") or "data/facts/item-effects.csv"
M.EFFECT_TEXT = os.getenv("EFFECT_TEXT_CSV") or "data/facts/effect-text.csv"

-- Stats in reading order, with the labels the documents use. A column absent
-- from this list is never printed, so a stat index the extractor could not name
-- is omitted rather than guessed at. Naming it wrongly is the worse failure.
M.STATS = {
  { "strength", "strength" },
  { "agility", "agility" },
  { "stamina", "stamina" },
  { "intellect", "intellect" },
  { "spirit", "spirit" },
  { "attack_power", "attack power" },
  { "ranged_attack_power", "ranged attack power" },
  { "feral_attack_power", "feral attack power" },
  { "melee_hit", "hit rating" },
  { "melee_crit", "crit rating" },
  { "melee_haste", "haste rating" },
  { "expertise", "expertise rating" },
  { "armor_pen", "armor penetration" },
  { "spell_damage", "spell damage" },
  { "healing_power", "healing power" },
  { "arcane_damage", "arcane damage" },
  { "fire_damage", "fire damage" },
  { "frost_damage", "frost damage" },
  { "holy_damage", "holy damage" },
  { "nature_damage", "nature damage" },
  { "shadow_damage", "shadow damage" },
  { "spell_hit", "spell hit rating" },
  { "spell_crit", "spell crit rating" },
  { "spell_haste", "spell haste rating" },
  { "spell_pen", "spell penetration" },
  { "defense", "defense rating" },
  { "dodge", "dodge rating" },
  { "parry", "parry rating" },
  { "block_rating", "block rating" },
  { "block_value", "block value" },
  { "resilience", "resilience" },
}

M.LABEL = {}
for _, pair in ipairs(M.STATS) do M.LABEL[pair[1]] = pair[2] end

-- ---------------------------------------------------------------- csv reading

-- RFC 4180 enough for these files: quoted fields, doubled quotes inside them,
-- and CRLF line endings, which the Python csv writer produces.
function M.parse_csv(path)
  local fh = io.open(path, "r")
  if not fh then
    error(string.format(
      "itemdb.lua: cannot read %s. Run the filters from the repository root, "
      .. "or set ITEMS_CSV and DROPS_CSV.", path))
  end
  local text = fh:read("a")
  fh:close()

  local rows, row, field, quoted, i = {}, {}, {}, false, 1
  local function end_field()
    row[#row + 1] = table.concat(field)
    field = {}
  end
  local function end_row()
    end_field()
    if not (#row == 1 and row[1] == "") then rows[#rows + 1] = row end
    row = {}
  end

  while i <= #text do
    local c = text:sub(i, i)
    if quoted then
      if c == '"' then
        if text:sub(i + 1, i + 1) == '"' then
          field[#field + 1] = '"'
          i = i + 1
        else
          quoted = false
        end
      else
        field[#field + 1] = c
      end
    elseif c == '"' then
      quoted = true
    elseif c == "," then
      end_field()
    elseif c == "\r" then
      -- part of CRLF; the \n ends the row
    elseif c == "\n" then
      end_row()
    else
      field[#field + 1] = c
    end
    i = i + 1
  end
  if #field > 0 or #row > 0 then end_row() end

  local header = table.remove(rows, 1)
  local out = {}
  for _, r in ipairs(rows) do
    local record = {}
    for n, key in ipairs(header) do record[key] = r[n] or "" end
    out[#out + 1] = record
  end
  return out
end

-- ------------------------------------------------------------------- indexing

-- Pandoc's smart punctuation turns the apostrophe in Slayer's Helm into a
-- typographic one before any filter sees it, and the item database spells it
-- straight. Both sides of the lookup are folded so the two agree.
-- Rating printed with its percentage. A rating is an internal unit; the
-- percentage is what a raider reasons about. Both appear, because the item's own
-- record is in rating and a tooltip quotes the item.
--
-- No spec is needed. TBC keeps hit and spell hit as separate item stats, and
-- likewise crit, so the denominator follows the stat column. That is what makes
-- this safe on a tooltip, which is shared across every card that names the item.
-- Divisors come from `conversions.generated.lua`, which reads them from the fact
-- files; none is written here.
local CONVERSIONS = os.getenv("CONVERSIONS_LUA")
  or "theme/filters/conversions.generated.lua"
local ok, conversions = pcall(dofile, CONVERSIONS)
M.RATING_PER_PERCENT = (ok and conversions and conversions.rating_per_percent) or {}

function M.with_percent(key, value, label)
  local conv = M.RATING_PER_PERCENT[key]
  if not conv or not conv.divisor or conv.divisor == 0 then
    return value .. " " .. label
  end
  return string.format("%s %s (%.2f%%)", value, label, value / conv.divisor)
end

function M.fold(name)
  return (name
    :gsub("\226\128\152", "'")
    :gsub("\226\128\153", "'")
    :gsub("\226\128\156", '"')
    :gsub("\226\128\157", '"'))
end

-- Items by exact name. A name held by more than one id is recorded as
-- ambiguous rather than resolved to whichever row was read last.
--
-- Items are indexed by id as well, because a derived comparison baseline is
-- chosen by id rather than by name: the workbook truncates names and repeats
-- them across tiers, so an id is the only stable handle on a ladder row.
M.by_name, M.by_id, M.ambiguous = {}, {}, {}
-- WHAT AN ITEM DOES, beside what it carries. An on-use or on-equip effect is
-- frequently the whole reason an item is contested, and until 12 August 2026 it
-- appeared nowhere a reader could see: not on the item card, not in a tooltip.
-- Madness of the Betrayer printed 84 attack power and 20 hit and said nothing
-- about the armor penetration proc that every creator discusses.
--
-- READ FROM data/facts/item-effects.csv, which the transform generates from the
-- item database, so the text cannot drift from the item. The prose in
-- item-procs.yaml is richer and is NOT used here, because it covers 29 items
-- against this file's 134 and a card that describes some effects and not others
-- reads as though the quiet ones have none.
-- AN ITEM CAN CARRY MORE THAN ONE EFFECT, and seventeen do. Beast-tamer's
-- Shoulders grant increased pet damage AND increased pet crit, and a table
-- keyed by item id alone kept whichever row came last, so the card named one
-- and hid the other.
--
-- AN EFFECT WITH NO NAME IS STILL AN EFFECT. Four rows carry a buff id and an
-- empty name, and Black Bow of the Betrayer is one of them. Skipping those
-- printed nothing at all, which tells a reader the item has no effect. It is
-- named as unnamed instead, with its buff id, so the gap is visible and
-- checkable rather than silent.
-- Labels for the stats only an EFFECT can grant. items.csv has no column for
-- these, so M.LABEL does not carry them, and they printed as bare enum numbers
-- until tools/extract_items.py::EFFECT_STAT named them on 12 August 2026.
M.EFFECT_LABEL = {
  health = "health", mana = "mana", mp5 = "mana per 5",
  arcane_resistance = "arcane resistance", fire_resistance = "fire resistance",
  frost_resistance = "frost resistance", nature_resistance = "nature resistance",
  shadow_resistance = "shadow resistance",
}

M.EFFECT = {}
for _, row in ipairs(M.parse_csv(M.EFFECTS)) do
  local name = (row.buff_name or ""):gsub("%s*%(%d+%)%s*$", "")
  local id = (row.buff_name or ""):match("%((%d+)%)%s*$")
  local list = M.EFFECT[row.item_id] or {}
  list[#list + 1] = {
    name = name,
    buff_id = id,
    stats = row.stats_granted or "",
    duration = tonumber(row.duration_ms),
    trigger = row.trigger or "",
    chance = tonumber(row.proc_chance),
    icd = tonumber(row.proc_icd_ms),
    ppm = tonumber(row.proc_ppm),
  }
  M.EFFECT[row.item_id] = list
end

-- WHAT THE EFFECT ACTUALLY DOES, IN WORDS, for the twenty-four items the
-- WoWSims database names but does not describe. Captured from Wowhead on
-- 13 August 2026 and parsed by tools/extract_effect_text.py. See
-- data/research/wowhead-effects/ for the bytes the sentence came from.
M.EFFECT_WORDS = {}
for _, row in ipairs(M.parse_csv(M.EFFECT_TEXT)) do
  local list = M.EFFECT_WORDS[row.item_id] or {}
  list[#list + 1] = row.trigger .. ": " .. row.text
  M.EFFECT_WORDS[row.item_id] = list
end

-- The effect as one line: what it is called, what it grants, and for how long.
-- Nil where the item has none, so a caller adds nothing rather than an empty
-- row.
function M.effect_line(row)
  -- THE CAPTURED SENTENCE WINS WHERE THERE IS ONE. It exists only for items
  -- whose database record is an internal label such as "Rogue Tier 6 Trinket",
  -- so it never competes with a record that describes itself; where it is
  -- present it is the whole description and the label adds nothing.
  local words = row and M.EFFECT_WORDS[tostring(row.item_id)]
  if words then return table.concat(words, " ") end
  local effects = row and M.EFFECT[tostring(row.item_id)]
  if not effects then return nil end
  local lines = {}
  for _, effect in ipairs(effects) do
    local parts = {}
    -- THE EXTRACTOR JOINS WITH A PIPE, not a semicolon. Splitting on the
    -- wrong character meant an effect granting two stats was read as one
    -- unparseable pair and printed with no stats at all.
    for pair in (effect.stats or ""):gmatch("[^|]+") do
      local key, value = pair:match("^%s*([%w_]+)=(-?%d+)%s*$")
      if key then
        parts[#parts + 1] = value .. " "
          .. (M.LABEL[key] or M.EFFECT_LABEL[key] or key:gsub("_", " "))
      end
    end
    -- WHAT MAKES IT FIRE, which the guild lead asked for by name and which
    -- nothing printed. A button press and a chance on hit read identically
    -- before this, so a card could not tell a player what to do with the item.
    local how
    if effect.trigger == "on_use" then
      how = "On use"
    elseif effect.trigger == "proc" then
      local terms = {}
      if effect.chance then
        terms[#terms + 1] = string.format("%g%% chance", effect.chance * 100)
      end
      if effect.ppm then
        terms[#terms + 1] = string.format("%g per minute", effect.ppm)
      end
      if effect.icd and effect.icd > 0 then
        terms[#terms + 1] = math.floor(effect.icd / 1000)
          .. " sec internal cooldown"
      end
      how = #terms > 0 and ("Proc, " .. table.concat(terms, ", ")) or "Proc"
    end

    local text
    if effect.name ~= "" then
      text = effect.name
    elseif effect.buff_id then
      text = "An effect the item database does not name, buff " .. effect.buff_id
    else
      text = "An effect the item database does not name"
    end
    if #parts > 0 then text = text .. ": " .. table.concat(parts, ", ") end
    if effect.duration and effect.duration > 0 then
      text = text .. " for " .. math.floor(effect.duration / 1000) .. " sec"
    end
    -- AN EFFECT THE DATABASE NAMES BUT DOES NOT DESCRIBE. The nine Ashtongue
    -- Talismans are the case: wowsims models them in Go and carries no stats,
    -- no duration and no trigger for them, so the buff name is an internal
    -- label such as "Rogue Tier 6 Trinket". Saying nothing would read as an
    -- item that does nothing, which is the opposite of the truth for a trinket
    -- whose whole worth is its effect.
    if #parts == 0 and not how
      and not (effect.duration and effect.duration > 0) then
      text = text .. ". The item database records the effect but not what it "
        .. "does, so it must be read on Wowhead"
    elseif how then
      text = how .. ". " .. text
    end
    lines[#lines + 1] = text
  end
  if #lines == 0 then return nil end
  return table.concat(lines, " · ")
end

for _, row in ipairs(M.parse_csv(M.ITEMS)) do
  local key = M.fold(row.name)
  local existing = M.by_name[key]
  if existing and existing.item_id ~= row.item_id then
    M.ambiguous[key] = true
  end
  M.by_name[key] = row
  M.by_id[row.item_id] = row
end

-- One name to one row, or to nil and the reason it failed. A caller collects
-- the reasons and reports them together; nothing here calls error, because a
-- document with three bad names should report three, not the first.
function M.resolve(name)
  local key = M.fold(name)
  if M.ambiguous[key] then
    return nil, "held by more than one item id in " .. M.ITEMS
  end
  local row = M.by_name[key]
  if not row then
    return nil, "not in " .. M.ITEMS
  end
  return row
end

-- TWO ITEMS CAN CARRY ONE NAME. `Warglaive of Azzinoth` is two ids, 32837 in
-- the main hand and 32838 in the off hand, and that pair is the loot decision
-- this project was started for. A name alone cannot say which of the two a card
-- is about, so a span may carry the id beside the name:
--
--   [Warglaive of Azzinoth]{.item item=32837}
--
-- The id decides, and the name beside it is still checked against the table,
-- because a name that disagrees with its id is a document making two claims and
-- the reader believes the one they can read.
function M.resolve_span(span)
  local name = M.fold(pandoc.utils.stringify(span.content))
  local id = span.attributes and span.attributes.item
  if id and id ~= "" then
    local row = M.by_id[id]
    if not row then
      return nil, "carries item=" .. id .. ", which is not in " .. M.ITEMS
    end
    -- Either the item's own name or the qualified one this build prints for it.
    -- A filter that has already resolved a row emits the printed name, and
    -- requiring the bare one there would fail on exactly the ambiguous items the
    -- qualifier exists for.
    if M.fold(row.name) ~= name and M.fold(M.display_name(row)) ~= name then
      return nil, string.format(
        "carries item=%s, which %s calls %q", id, M.ITEMS, row.name)
    end
    return row
  end
  local row, why = M.resolve(name)
  if not row and M.ambiguous[name] then
    why = why .. ". Write the id beside the name to say which one: "
      .. "[Name]{.item item=32837}"
  end
  return row, why
end

-- The name to print for a row, which is its own name except where the item
-- table holds another item by that name.
--
-- `Warglaive of Azzinoth` printed twice on one card, once as the item under
-- discussion and once as its own comparison baseline, because on the Combat
-- Rogue's single weapon ladder the off-hand glaive's best competitor is the
-- main-hand one. Two identical names beside each other read as an item compared
-- with itself, which is the one thing every baseline rule in this project exists
-- to prevent, so the hand is printed where and only where it is what separates
-- them. An item whose name is unique never carries the qualifier, because a
-- qualifier on every weapon is noise on every card that has no ambiguity.
function M.display_name(row)
  if not row then return "" end
  if M.ambiguous[M.fold(row.name)] and row.hand_type and row.hand_type ~= "" then
    return row.name .. " (" .. row.hand_type .. ")"
  end
  return row.name
end

-- Names close enough to be the typo behind an unresolved reference.
function M.near_matches(name)
  local needle = name:lower():gsub("[^%w]", "")
  local hits = {}
  for candidate in pairs(M.by_name) do
    local hay = candidate:lower():gsub("[^%w]", "")
    if hay:find(needle, 1, true) or needle:find(hay, 1, true) then
      hits[#hits + 1] = candidate
    end
  end
  table.sort(hits)
  return hits
end

-- ------------------------------------------------------------------ stat reads

function M.number(value)
  return tonumber(value) and tonumber(value) or nil
end

-- Armor is the sum of `armor` and `bonus_armor`, because that is the single
-- figure the game tooltip shows and the figure the documents quote.
-- Thunderheart Cover is 373 base plus 238 bonus, and it is 611 everywhere.
function M.armour_of(row)
  local base = M.number(row.armor) or 0
  local bonus = M.number(row.bonus_armor) or 0
  local total = base + bonus
  if total > 0 then return total end
  return nil
end

-- The ladder reaches wider than the compendium's item table: the Combat
-- Rogue's best Phase 1 or 2 head is an engineering goggle and the Survival
-- Hunter's is an arena piece, and neither is a raid drop or a tier piece. Where
-- items.csv holds the item it answers, because it is the stat line's one home.
-- Where it does not, the generated ladder carries the stat line it was given at
-- `just regen` time from the same item database items.csv is built from.
-- Where the built site keeps the icons, relative to the page being written.
-- Set from the document's `root` metadata by whichever filter runs first; a
-- page in docs/items/ needs `../` and a page at the root needs nothing.
M.root = ""

-- The item's icon, as an image, or nil where the item database named none and
-- nothing was fetched for it. AN ITEM IS RECOGNIZED BY ITS ICON before its name
-- is read, and a council scanning a page of claimants is doing exactly that.
--
-- The alt text is deliberately empty. The icon carries no information the name
-- beside it does not already carry, so announcing it twice is noise to a screen
-- reader. It is decoration in the accessibility sense and content in every
-- other sense.
function M.icon_img(source)
  local icon = source and source.icon
  if not icon or icon == "" then return nil end
  return pandoc.Image({}, M.root .. "icons/" .. icon .. ".jpg", "",
    pandoc.Attr("", { "item-icon" }, { loading = "lazy", ["aria-hidden"] = "true" }))
end

function M.ladder_row(entry)
  local row = M.by_id[tostring(entry.item_id)]
  if row then return row, true end
  if not entry.stats then return nil end
  local synthesized = { name = entry.name, item_id = tostring(entry.item_id),
    icon = entry.icon }
  for key, value in pairs(entry.stats) do synthesized[key] = value end
  return synthesized, false
end

-- One stat off a row, with the mirrored generic attack power counted once. The
-- item database writes a generic attack power bonus into both `attack_power`
-- and `ranged_attack_power`, so reading both double-counts it.
function M.stat_of(row, key)
  local value = M.number(row[key]) or 0
  if key == "ranged_attack_power" then
    local ap = M.number(row.attack_power) or 0
    if ap ~= 0 and ap == value then return 0 end
  end
  return value
end

-- The stat line as one sentence.
function M.stat_summary(row)
  local parts = {}
  local armour = M.armour_of(row)
  if armour then parts[#parts + 1] = armour .. " armor" end
  for _, pair in ipairs(M.STATS) do
    local value = M.stat_of(row, pair[1])
    if value ~= 0 then parts[#parts + 1] = value .. " " .. pair[2] end
  end
  return table.concat(parts, ", ")
end

-- How a baseline outside the item table is obtained, in words, for the last
-- line of its tooltip. The same fact the column label carries, written as a
-- sentence rather than as a label.
local ROUTE_PHRASE = {
  crafted = "%s, crafted rather than dropped",
  arena = "%s, an arena reward bought with rating",
  badge = "%s, bought with badges",
  drop = "Drops in %s",
}

function M.route_line(entry)
  local where = entry.location
  if not where or where == "" then return "" end
  return string.format(ROUTE_PHRASE[entry.route or "drop"] or "%s", where)
end

local counter = 0

local function tip_part(class, text)
  if text == nil or text == "" then return nil end
  return pandoc.Span(pandoc.Str(text), pandoc.Attr("", { class }))
end

-- EVERY BASELINE CARRIES THE SAME TOOLTIP. A baseline the item table holds
-- becomes an `.item` span and items.lua builds its bubble. One the item table
-- does NOT hold used to become a bare link whose stat line sat in the `title`
-- attribute, which the browser renders as its own plain tooltip after a delay
-- and which looks nothing like the styled bubble beside it. That read as a
-- broken tooltip rather than as a different kind of item, and it is now the
-- common case: the off-piece columns are frequently crafted or arena items,
-- which items.csv does not carry, so two of the four baselines on a card would
-- have behaved differently from the other two.
--
-- The bubble is built here instead, in the shape items.lua produces, from the
-- stat line the generated ladder carries and the acquisition route it was found
-- under. It states no tier, no armor type and no boss, because the ladder does
-- not carry those for an item outside the compendium, and an invented line is
-- worse than an absent one.
function M.ladder_inline(entry, row, held, prefix)
  if held then
    -- WITH THE ID, NOT THE NAME ALONE. A baseline is chosen by id, so handing
    -- items.lua only the name asks it to answer a question already answered,
    -- and it cannot answer it where two items share the name: an off-hand
    -- Warglaive of Azzinoth takes the other Warglaive as its baseline on the
    -- Combat Rogue tab, and the build stopped on the ambiguity.
    return pandoc.Span(pandoc.Str(M.display_name(row)),
      pandoc.Attr("", { "item" }, { item = tostring(entry.item_id) }))
  end
  counter = counter + 1
  local tip_id = prefix .. "-" .. tostring(entry.item_id) .. "-" .. counter

  local tip = pandoc.List({})
  local function add(part) if part then tip:insert(part) end end
  add(tip_part("item-tip-name", M.display_name(row)))
  if entry.phase then
    add(tip_part("item-tip-meta", "Phase " .. entry.phase))
  end
  add(tip_part("item-tip-stats", M.stat_summary(row)))
  add(tip_part("item-tip-effect", M.effect_line(row)))
  add(tip_part("item-tip-source", M.route_line(entry)))

  local shown = pandoc.List({})
  local icon = M.icon_img(row) or M.icon_img(entry)
  if icon then shown:insert(icon) end
  shown:insert(pandoc.Str(M.display_name(row)))
  local link = pandoc.Link(
    shown, entry.url, "",
    pandoc.Attr("", { "item-link" }, {
      ["aria-describedby"] = tip_id,
      -- A NEW TAB, ALWAYS. A council member clicks an item to check it while
      -- reading the card, and navigating away loses the card, the spec filter
      -- state and their place on the page. `noopener` and `noreferrer` are not
      -- optional company for `_blank`: without them the opened page can reach
      -- back at this one through `window.opener`.
      target = "_blank",
      rel = "noopener noreferrer",
    }))
  local bubble = pandoc.Span(tip,
    pandoc.Attr(tip_id, { "item-tip" }, { role = "tooltip" }))
  return pandoc.Span({ link, bubble }, pandoc.Attr("", { "item-ref" }))
end


return M
