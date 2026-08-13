--[[
  Turn an item name into a Wowhead link carrying its stat line as a tooltip.

  A priority is always argued against a named alternative, so a reader comparing
  two pieces needs both stat lines in front of them. Leaving the page to fetch
  one is what this removes.

  Markdown

      [Slayer's Helm]{.item}

  The author writes the name and nothing else. No item id, no HTML, no stat
  line copied by hand into prose where it goes stale. On GitHub the span
  degrades to `[Slayer's Helm]{.item}`, which is the same degradation the
  fenced-div components already have, and the name stays readable.

  The payload is built here, at build time, from data/facts/items.csv and
  data/facts/drops.csv. Wowhead publishes a tooltip script that would do this
  at view time, and it is not used: it is an external dependency, it costs a
  network round trip on a site that is read locally, it cannot be styled, and
  it would put an unverified stat line beside our verified ones.

  A name this cannot resolve is a build error naming the document, the name and
  the nearest matches. A reference to an item that does not exist is a wrong
  reference, and an empty tooltip would hide it.

  Name resolution, the stat vocabulary and the armour rule are shared with
  delta.lua and live in itemdb.lua. What is here is the tooltip.

  One rendering decision worth knowing. The item database mirrors a generic attack power bonus into both
  `attack_power` and `ranged_attack_power`. When the two are equal, only
  attack power is shown, because "92 attack power, 92 ranged attack power" is
  one bonus printed twice.

  ---------------------------------------------------------------------------

  This file also builds the container that introduces an item before the spec
  cards arguing over it.

  Markdown

      :::: {.subject}

      [Cursed Vision of Sargeras]{.item}

      ::: {.specs}

      #### Combat Rogue

      Priority
      :   Priority 1

      :::

      ::::

  The author writes the item once, as the first block, in the same
  `[Name]{.item}` form used everywhere else. The same row that builds the
  tooltip builds the head, so the stat line, the sockets and the source are
  read from data/facts/items.csv and data/facts/drops.csv rather than copied
  into prose where they would go stale.

  A `.subject` whose first block is not one item reference is a build error.
  A container introducing no item is the confusion it exists to remove.

  Headings inside the container drop one level, so the item is the parent of
  the spec headings rather than their sibling. The author still writes
  `#### Combat Rogue`, which is what specs.lua and GitHub both read, and the
  level is corrected here.
]]

local itemdb = dofile(os.getenv("ITEMDB_LUA") or "theme/filters/itemdb.lua")

local DROPS = os.getenv("DROPS_CSV") or "data/facts/drops.csv"

local STATS, LABEL = itemdb.STATS, itemdb.LABEL
local fold, number, armour_of = itemdb.fold, itemdb.number, itemdb.armour_of

-- ------------------------------------------------------------------- indexing

-- Where each item drops. An item dropping from several bosses keeps all of
-- them; the tooltip prints the count instead once there are more than two.
local drop_sources = {}
for _, row in ipairs(itemdb.parse_csv(DROPS)) do
  local list = drop_sources[row.item_id]
  if not list then
    list = {}
    drop_sources[row.item_id] = list
  end
  local where = row.boss .. ", " .. row.zone
  local seen = false
  for _, w in ipairs(list) do if w == where then seen = true end end
  if not seen then list[#list + 1] = where end
end

-- --------------------------------------------------------------- tooltip text

local function stat_line(row)
  local parts = {}
  local armour = armour_of(row)
  if armour then parts[#parts + 1] = armour .. " armor" end

  local ap = number(row.attack_power)
  local rap = number(row.ranged_attack_power)
  for _, pair in ipairs(STATS) do
    local key, label = pair[1], pair[2]
    local value = number(row[key])
    if value and value ~= 0 then
      -- The mirrored generic attack power bonus, printed once.
      if not (key == "ranged_attack_power" and ap and rap and ap == rap) then
        parts[#parts + 1] = itemdb.with_percent(key, value, label)
      end
    end
  end

  local min, max = number(row.weapon_min), number(row.weapon_max)
  if min and max then
    local damage = string.format("%d to %d damage", min, max)
    if number(row.weapon_speed) then
      damage = damage .. string.format(", speed %.1f", number(row.weapon_speed))
    end
    table.insert(parts, 1, damage)
  end

  return table.concat(parts, ", ")
end

local function socket_line(row)
  local parts = {}
  if row.sockets ~= "" then
    local colours = {}
    for colour in row.sockets:gmatch("[^|]+") do colours[#colours + 1] = colour end
    parts[#parts + 1] = "Sockets " .. table.concat(colours, ", "):lower()
  end
  if row.socket_bonus ~= "" then
    local bonuses = {}
    for entry in row.socket_bonus:gmatch("[^|]+") do
      local key, value = entry:match("^([%w_]+)=(%-?%d+)$")
      -- An unlabeled stat index is dropped. See the STATS note above.
      if key and LABEL[key] then
        bonuses[#bonuses + 1] = value .. " " .. LABEL[key]
      end
    end
    if #bonuses > 0 then
      parts[#parts + 1] = "Socket bonus " .. table.concat(bonuses, ", ")
    end
  end
  return table.concat(parts, " · ")
end

local function meta_line(row)
  local parts = {}
  local tier = row.tier:gsub("|", " and ")
  parts[#parts + 1] = "Tier " .. tier:gsub("T", "")
  if row.slot ~= "" then parts[#parts + 1] = row.slot:lower() end
  if row.armor_type ~= "" then parts[#parts + 1] = row.armor_type:lower() end
  -- THE HAND IS PART OF WHAT A WEAPON IS, and until now it was nowhere on the
  -- page. The two Warglaives of Azzinoth differ only by it, so a tooltip that
  -- omitted it left them identical. The slot `weapon` is dropped where the hand
  -- is present, because `two hand sword` says everything `weapon · two hand ·
  -- sword` says and says it the way a player says it.
  if row.hand_type ~= "" and row.weapon_type ~= "" then
    parts[#parts] = row.hand_type:lower() .. " " .. row.weapon_type:lower()
  elseif row.weapon_type ~= "" then
    parts[#parts + 1] = row.weapon_type:lower()
  elseif row.hand_type ~= "" then
    parts[#parts + 1] = row.hand_type:lower()
  end
  return table.concat(parts, " · ")
end

local function source_line(row)
  if row.source:find("tier_vendor") then
    local set = row.set_name ~= "" and row.set_name or "a tier set"
    return "Tier set piece, " .. set .. ". Bought with a token, never a raid drop"
  end
  -- A ROUTE THAT IS NOT A BOSS DROP still has to say where the item comes
  -- from. Only tier pieces and raid drops did, so every reputation reward and
  -- every crafted piece showed a blank line, and the Ashtongue Talismans read
  -- as items from nowhere. `source_note` names the faction and the standing,
  -- or the profession, and is written by tools/extract_items.py::source_note.
  if row.source_note ~= nil and row.source_note ~= "" then
    if row.source:find("reputation") then
      return "Reputation reward, " .. row.source_note
    end
    return row.source_note
  end
  local list = drop_sources[row.item_id]
  if not list or #list == 0 then return "" end
  if #list <= 2 then return "Drops from " .. table.concat(list, "; ") end
  return string.format("Drops from %d sources", #list)
end

-- --------------------------------------------------------------- construction

local counter = 0

local function tip_part(class, text)
  if text == nil or text == "" then return nil end
  return pandoc.Span(pandoc.Str(text), pandoc.Attr("", { class }))
end

local function item_reference(name, row, bare)
  -- The author writes the bare name; what prints is the name that identifies
  -- the item, which differs only where two items share one.
  name = itemdb.display_name(row)
  counter = counter + 1
  local tip_id = "item-tip-" .. row.item_id .. "-" .. counter

  local tip = pandoc.List({})
  local function add(part) if part then tip:insert(part) end end
  add(tip_part("item-tip-name", name))
  add(tip_part("item-tip-meta", meta_line(row)))
  add(tip_part("item-tip-stats", stat_line(row)))
  add(tip_part("item-tip-sockets", socket_line(row)))
  -- The effect sits between what the item carries and where it drops, because
  -- it is a property of the item rather than of its source.
  add(tip_part("item-tip-effect", itemdb.effect_line(row)))
  add(tip_part("item-tip-source", source_line(row)))

  -- The link is the focusable element and the tooltip describes it, so the
  -- stat line is announced on focus without becoming part of the link name.
  local shown = pandoc.List({})
  -- `item-bare` is set where a larger icon already stands beside the link, so
  -- the inline one would be the same art printed twice.
  local icon = not bare and itemdb.icon_img(row) or nil
  if icon then shown:insert(icon) end
  shown:insert(pandoc.Str(name))
  local link = pandoc.Link(
    shown,
    "https://www.wowhead.com/tbc/item=" .. row.item_id,
    "",
    pandoc.Attr("", { "item-link" }, {
      ["aria-describedby"] = tip_id,
      -- A NEW TAB, ALWAYS. A council member clicks an item to check it while
      -- reading the card, and navigating away loses the card, the spec filter
      -- state and their place on the page. `noopener` and `noreferrer` are not
      -- optional company for `_blank`: without them the opened page can reach
      -- back at this one through `window.opener`.
      target = "_blank",
      rel = "noopener noreferrer",
    })
  )
  local bubble = pandoc.Span(tip, pandoc.Attr(tip_id, { "item-tip" }, { role = "tooltip" }))
  return pandoc.Span({ link, bubble }, pandoc.Attr("", { "item-ref" }))
end

-- ------------------------------------------------------------------- subject

local subject_failures = {}

-- The one `.item` span a container's first block holds, or nil and the reason.
-- The paragraph must hold that reference and nothing else, because a sentence
-- would put prose into a head whose whole job is to name the item.
local function opening_reference(blocks)
  local first = blocks[1]
  if not first or (first.t ~= "Para" and first.t ~= "Plain") then
    return nil, "the first block is not a paragraph holding one [Name]{.item}"
  end
  local found = pandoc.List({})
  pandoc.Blocks({ first }):walk({
    Span = function(span)
      if span.classes:includes("item") then found:insert(span) end
    end,
  })
  if #found ~= 1 then
    return nil, string.format(
      "the first paragraph holds %d item reference(s), and exactly one is required", #found)
  end
  local reference = found[1]
  if pandoc.utils.stringify(first.content) ~= pandoc.utils.stringify(reference.content) then
    return nil, "the first paragraph carries prose beside the item reference"
  end
  return reference
end

local function subject_line(class, text)
  if text == nil or text == "" then return nil end
  return pandoc.Div({ pandoc.Plain(pandoc.Str(text)) }, pandoc.Attr("", { class }))
end

-- Every heading below the item drops one level, so the spec headings sit under
-- the item rather than beside it. Nothing is demoted past level six.
local function demoted(blocks)
  return pandoc.Blocks(blocks):walk({
    Header = function(header)
      if header.level < 6 then header.level = header.level + 1 end
      return header
    end,
  })
end

local function subject(div)
  local reference, why = opening_reference(div.content)
  if not reference then
    subject_failures[#subject_failures + 1] = { why = why }
    return nil
  end

  local row = itemdb.resolve_span(reference)
  -- An unresolvable name is left to the span walk below, which reports it with
  -- the near matches. Reporting it twice would name one mistake as two.
  if not row then return nil end

  local rest = pandoc.List({})
  for n = 2, #div.content do rest:insert(div.content[n]) end

  -- THE ITEM IS STAMPED ONTO THE CARDS BLOCK. `specs.lua` runs after this one
  -- and builds each card's priority and argument from the judgment store, which is
  -- keyed by item and spec together. It cannot read the item itself: pandoc
  -- walks the inner block first, so by the time the container is visited the
  -- cards are already built. Passing it down here is the one point where the
  -- subject is known and the cards have not been touched yet.
  rest = pandoc.Blocks(rest):walk({
    Div = function(inner)
      if not inner.classes:includes("specs") then return nil end
      inner.attributes.item = tostring(row.item_id)
      return inner
    end,
  })

  local blocks = pandoc.List({})
  -- The heading is the container's first child on purpose. Pandoc's HTML writer
  -- then writes the whole container as a <section> the heading introduces, so
  -- the cards sit inside the item's section rather than after it. It carries no
  -- attributes of its own, because that writer hoists a leading header's
  -- attributes onto the section and the class would land in two places. Style it
  -- through its parent.
  local heading = pandoc.List({})
  local big = itemdb.icon_img(row)
  if big then
    heading:insert(pandoc.Span({ big },
      pandoc.Attr("", { "subject-icon" })))
    -- AND THE ONE INSIDE THE LINK IS SUPPRESSED. An inline item link carries
    -- its own small icon so an item named mid-sentence is recognisable, and in
    -- this heading the subject icon above already shows it, so both printed
    -- the same art twice, once large and once small, side by side.
    --
    -- MARKED RATHER THAN STRIPPED, because at this point the reference is
    -- still the author's raw `[Name]{.item}` span: the icon does not exist
    -- yet. The conversion that adds it runs later, in the Span walk below, so
    -- the only thing that can travel from here to there is a class on the
    -- span. Stripping images here removes nothing and looks like it worked.
    reference = reference:clone()
    reference.classes:insert("item-bare")
  end
  heading:insert(reference)
  blocks:insert(pandoc.Header(4, heading))

  local lines = pandoc.List({})
  local function add(line) if line then lines:insert(line) end end
  add(subject_line("subject-meta", meta_line(row)))
  add(subject_line("subject-stats", stat_line(row)))
  add(subject_line("subject-sockets", socket_line(row)))
  add(subject_line("subject-effect", itemdb.effect_line(row)))
  add(subject_line("subject-source", source_line(row)))
  if #lines > 0 then
    blocks:insert(pandoc.Div(lines, pandoc.Attr("", { "subject-lines" })))
  end

  blocks:extend(demoted(rest))
  div.content = blocks
  return div
end

function Meta(meta)
  if meta.root then itemdb.root = pandoc.utils.stringify(meta.root) end
  return meta
end

function Pandoc(doc)
  local source = pandoc.utils.stringify(doc.meta.srcpath or "")
  if source == "" then source = "this document" end

  -- Containers are rebuilt before the spans inside them are, because the head
  -- is built from the item reference the author wrote and the span walk
  -- replaces that reference with the link and its tooltip.
  doc.blocks = doc.blocks:walk({
    Div = function(div)
      if not div.classes:includes("subject") then return nil end
      return subject(div)
    end,
  })

  if #subject_failures > 0 then
    local lines = { string.format(
      "items.lua: %d ::: {.subject} container(s) in docs/%s name no item.",
      #subject_failures, source) }
    for _, failure in ipairs(subject_failures) do
      lines[#lines + 1] = "      " .. failure.why
    end
    lines[#lines + 1] =
      "A container exists to introduce the item its cards argue over, so write "
      .. "that item as its first block: [Name]{.item} on a line of its own."
    error(table.concat(lines, "\n"))
  end

  local failures = {}
  local blocks = doc.blocks:walk({
    Span = function(span)
      if not span.classes:includes("item") then return nil end
      local name = fold(pandoc.utils.stringify(span.content))
      local row, why = itemdb.resolve_span(span)
      if not row then
        failures[#failures + 1] = { name = name, why = why }
        return nil
      end
      return item_reference(name, row, span.classes:includes("item-bare"))
    end,
  })

  if #failures > 0 then
    local lines = { string.format(
      "items.lua: %d item reference(s) in docs/%s do not resolve.",
      #failures, source) }
    for _, failure in ipairs(failures) do
      lines[#lines + 1] = string.format("  [%s]{.item}  %s", failure.name, failure.why)
      local hits = itemdb.near_matches(failure.name)
      for n = 1, math.min(#hits, 3) do
        lines[#lines + 1] = "      did you mean: " .. hits[n]
      end
    end
    lines[#lines + 1] =
      "A name that does not resolve is a wrong reference, not a missing tooltip. "
      .. "Fix the name, or add the item to the extractor's scope."
    error(table.concat(lines, "\n"))
  end

  doc.blocks = blocks
  return doc
end

-- Metadata first, so an icon's path carries the page's root prefix. Pandoc
-- walks the blocks before the metadata unless the passes are named.
return {
  { Meta = Meta },
  { Pandoc = Pandoc },
}
