--[[
  Turn a spec's name into what that spec wants, slot by slot.

  Markdown

      ::: {.shortlist}
      Combat Rogue
      :::

  The page names the spec and nothing else. Every row below is read at build
  time from `theme/filters/ladder.generated.lua`, which
  `tools/extract_ladder.py` lifts out of the EP Workbook, and every priority
  from `theme/filters/judgments.generated.lua`.

  THIS IS THE SECOND WAY IN. An item page answers "who wants this drop", which
  is the question at the moment loot falls. A spec page answers "what does this
  player still need", which is the question when planning a week. They read the
  same shortlist, five deep per slot, so the two views cannot disagree: a spec
  shown an item here is a spec that appears as a claimant there.

  WHAT EACH COLUMN IS. Rank and EPV are the workbook's own, and EPV is printed
  because it is the basis of the rank and a reader comparing two rows deserves
  to see how far apart they are. Phase and route say whether the item is
  reachable: a Phase 1 item at rank one means the spec's best in that slot is
  something it already holds, and a crafted or arena route means the item is
  gated.

  THE PRIORITY COLUMN HAS THREE STATES and they are not the same absence.
  A settled priority prints. An item this phase drops that the council has not
  reached prints as not yet decided. An item from an earlier tier carries no
  priority at all and says so, because this compendium prioritizes Mount Hyjal
  and Black Temple loot and an earlier-tier item is not a decision anyone
  declined to make.

  A tier set piece is marked, because a row that costs a token is a different
  proposition from a row that drops.
]]

local itemdb = dofile(os.getenv("ITEMDB_LUA") or "theme/filters/itemdb.lua")

local LADDER = os.getenv("LADDER_LUA") or "theme/filters/ladder.generated.lua"
local JUDGMENTS = os.getenv("JUDGMENTS_LUA")
  or "theme/filters/judgments.generated.lua"

local function generated(path)
  local ok, value = pcall(dofile, path)
  if not ok or type(value) ~= "table" then
    error(string.format(
      "shortlist.lua: cannot read %s.\nRun `just regen` to write it, and run "
      .. "the filters from the repository root.\n%s", path, tostring(value)), 0)
  end
  return value
end

local ladder = generated(LADDER)
local judgments = generated(JUDGMENTS)

-- Which items have a page of their own. Written by the page generator, which
-- owns the slug rule, so this cannot drift from where the pages actually are.
local PAGES = os.getenv("PAGES_LUA") or "theme/filters/pages.generated.lua"
local ok_pages, pages = pcall(dofile, PAGES)
if not ok_pages or type(pages) ~= "table" then pages = {} end

-- Set by the template on every page, so a link from docs/specs/ reaches
-- docs/items/ whatever depth the reader is at.
local root = ""

local failures = {}

-- The order the slots read down, which is the order a character sheet reads
-- rather than the order the workbook happens to write its sections. A reader
-- looking for their boots should not have to hunt.
local SLOT_ORDER = {
  "Head", "Neck", "Shoulders", "Back", "Chest", "Wrist", "Hands", "Waist",
  "Legs", "Feet", "Ring", "Trinket",
  "Main Hand", "One Hand", "Off Hand", "Two Hand", "Ranged",
}

local function known_specs()
  local names = {}
  for _, entry in pairs(ladder.specs) do names[#names + 1] = entry.name end
  table.sort(names)
  return names
end

local function cell(inlines, align, class)
  return pandoc.Cell({ pandoc.Plain(inlines) }, align, 1, 1,
    pandoc.Attr("", { class }))
end

local function text_cell(text, align, class)
  return cell({ pandoc.Str(text) }, align, class)
end

-- The item, linked and given a tooltip. THE SHORTLIST REACHES WIDER THAN THE
-- ITEM TABLE: a spec's best waist is frequently a crafted belt or a badge
-- reward, which items.csv does not carry because it holds raid loot and tier
-- pieces. Handing items.lua a bare `.item` span for one of those fails the
-- build on a name it cannot resolve, so the shared builder in itemdb.lua is
-- used, which emits an `.item` span where the item table holds the row and
-- builds the same bubble from the generated ladder where it does not.
-- An arena stat block sold in several weapon flavours is ONE choice, so the
-- variants collapse to a single row. The row says how many it stands for,
-- because a reader who counts five arena weapons on Wowhead and finds one here
-- deserves to know why rather than to suspect the table.
local function where_text(entry)
  local where = entry.location or ""
  if entry.variants and entry.variants > 1 then
    return where .. string.format(" (%d weapon types)", entry.variants)
  end
  return where
end

local function item_cell(entry)
  local row, held = itemdb.ladder_row(entry)
  if not row then
    failures[#failures + 1] = string.format(
      "%s carries no stat line in %s and is not in %s. Run `just regen`.",
      entry.name, LADDER, itemdb.ITEMS)
    return cell({ pandoc.Str(entry.name) }, pandoc.AlignLeft, "shortlist-item")
  end
  -- LINKED TO OUR OWN PAGE WHERE THERE IS ONE. A reader on a spec page who
  -- sees an item at rank one wants to know who else is contesting it, and that
  -- answer is on the item's page. Sending them to Wowhead instead answers a
  -- question they did not ask. The Wowhead link stays reachable: the tooltip
  -- beside the name still carries it.
  --
  -- ONE ICON AND ONE NAME, WHICHEVER BRANCH RUNS. This used to emit the name
  -- TWICE on any row we hold a page for: once as the link to that page, and
  -- again inside the bubble beside it, which renders its own icon and its own
  -- copy of the name. Rows with no page emitted the bubble alone and looked
  -- right, so the table showed two different styles down one column. Reported
  -- from a screenshot on 9 August 2026, and the clean rows were the wanted
  -- ones.
  --
  -- Nothing is lost by dropping the bubble here. It carried the Wowhead link
  -- and the stat line, and our own item page carries both, plus the claimants
  -- that are the reason for sending a reader there at all.
  local page = pages[tostring(entry.item_id)]
  local inlines = pandoc.List({})
  if page then
    -- BUILT WITH THIS FILE'S OWN `root`, NOT itemdb.icon_img. That helper
    -- prefixes with `itemdb.root`, which is EMPTY HERE, so every icon it made
    -- pointed at `icons/...` relative to `/specs/` and rendered broken. The
    -- links on the same rows were right, because they use the `root` this file
    -- resolves in its own Meta pass.
    --
    -- THE CAUSE IS NOT FILTER ORDERING, which an earlier version of this note
    -- claimed. Every filter runs its own `dofile` of itemdb.lua, so each holds
    -- a SEPARATE module table, and `itemdb.root` is assigned in exactly one
    -- place, items.lua. No amount of reordering would populate the copy this
    -- file holds. Found by an adversarial review on 10 August 2026.
    --
    -- THE SAME TRAP IS STILL LOADED ELSEWHERE. itemdb.icon_img is reached from
    -- itemdb.ladder_inline, which delta.lua and this file both call. It is
    -- harmless today only because the generated ladder carries no `icon` field,
    -- so that path always gets nil and emits no image at all. Add an icon to
    -- the ladder, which is a plausible next change, and both filters will emit
    -- `src="icons/..."` from `/specs/` and `/items/` and break silently.
    local art = row.icon or entry.icon
    if art and art ~= "" then
      inlines:insert(pandoc.Span(
        { pandoc.Image({}, root .. "icons/" .. art .. ".jpg", "",
          pandoc.Attr("", { "item-icon" },
            { loading = "lazy", ["aria-hidden"] = "true" })) },
        pandoc.Attr("", { "shortlist-icon" })))
    end
    inlines:insert(pandoc.Link(pandoc.Str(itemdb.display_name(row)),
      root .. "items/" .. page .. ".html", "",
      pandoc.Attr("", { "shortlist-link" })))
  else
    inlines:insert(itemdb.ladder_inline(entry, row, held, "shortlist-tip"))
  end
  if entry.tier then
    inlines:insert(pandoc.Space())
    inlines:insert(pandoc.Span(pandoc.Str("tier set"),
      pandoc.Attr("", { "shortlist-tier" })))
  end
  return cell(inlines, pandoc.AlignLeft, "shortlist-item")
end

-- Three states, and they are not the same absence. See the note at the head.
local function priority_cell(entry, spec_name)
  local judgment = judgments[tostring(entry.item_id) .. "|" .. spec_name:lower()]
  if judgment and judgment.priority and judgment.priority ~= "" then
    local classes = { "shortlist-priority" }
    if not judgment.priority:match("^%s*[Pp]riority%s+%d%s*$") then
      table.insert(classes, "shortlist-priority-none")
    end
    return cell({ pandoc.Span(pandoc.Str(judgment.priority),
      pandoc.Attr("", classes)) }, pandoc.AlignLeft, "shortlist-priority-cell")
  end
  -- An item this phase drops has a page and a decision waiting on it. Anything
  -- else is out of the compendium's scope rather than undecided within it.
  local row = itemdb.by_id[tostring(entry.item_id)]
  local this_phase = row and row.tier and row.tier:find("T6")
  local text = this_phase and "not yet decided" or "not this phase"
  local class = this_phase and "shortlist-priority shortlist-priority-undecided"
    or "shortlist-priority shortlist-priority-outside"
  return cell({ pandoc.Span(pandoc.Str(text), pandoc.Attr("", { class })) },
    pandoc.AlignLeft, "shortlist-priority-cell")
end

local HEADS = {
  { "Rank", pandoc.AlignRight }, { "Item", pandoc.AlignLeft },
  { "EPV", pandoc.AlignRight }, { "Phase", pandoc.AlignRight },
  { "Where", pandoc.AlignLeft }, { "Priority", pandoc.AlignLeft },
}

local function table_of(entries, spec_name)
  local aligns, heads = {}, {}
  for _, pair in ipairs(HEADS) do
    aligns[#aligns + 1] = { pair[2], nil }
    heads[#heads + 1] = text_cell(pair[1], pair[2], "shortlist-head")
  end
  local rows = {}
  for _, entry in ipairs(entries) do
    rows[#rows + 1] = pandoc.Row({
      text_cell(tostring(entry.rank), pandoc.AlignRight, "shortlist-rank"),
      item_cell(entry),
      text_cell(string.format("%.2f", entry.epv), pandoc.AlignRight,
        "shortlist-epv"),
      text_cell(tostring(entry.phase), pandoc.AlignRight, "shortlist-phase"),
      text_cell(where_text(entry), pandoc.AlignLeft,
        (entry.route or "drop") == "drop" and "shortlist-where"
          or "shortlist-where shortlist-gated"),
      priority_cell(entry, spec_name),
    })
  end
  return pandoc.Table(pandoc.Caption({}), aligns,
    pandoc.TableHead({ pandoc.Row(heads) }),
    { pandoc.TableBody(rows, {}, 0) }, pandoc.TableFoot({}))
end

function Meta(meta)
  if meta.root then root = pandoc.utils.stringify(meta.root) end
  return meta
end

function Div(div)
  if not div.classes:includes("shortlist") then return nil end

  local name = pandoc.utils.stringify(div.content)
  local rungs = ladder.specs[name:lower()]
  if not rungs then
    failures[#failures + 1] = string.format(
      "%q is not a spec with a workbook tab.\n      Known: %s.", name,
      table.concat(known_specs(), ", "))
    return div
  end
  if not rungs.by_slot then
    failures[#failures + 1] = string.format(
      "%s carries no shortlist in %s. Run `just regen`.", name, LADDER)
    return div
  end

  local out = pandoc.List({})
  local shown = {}
  local function section(slot)
    local entries = rungs.by_slot[slot]
    if not entries or #entries == 0 or shown[slot] then return end
    shown[slot] = true
    out:insert(pandoc.Div({ pandoc.Plain(pandoc.Str(slot)) },
      pandoc.Attr("", { "shortlist-slot" })))
    out:insert(pandoc.Div({ table_of(entries, name) },
      pandoc.Attr("", { "shortlist-grid" })))
  end
  for _, slot in ipairs(SLOT_ORDER) do section(slot) end
  -- A section the order above does not name still prints, at the end, so a
  -- workbook that grows a section cannot lose it silently.
  local extra = {}
  for slot in pairs(rungs.by_slot) do
    if not shown[slot] then extra[#extra + 1] = slot end
  end
  table.sort(extra)
  for _, slot in ipairs(extra) do section(slot) end

  div.content = out
  return div
end

-- Meta before Div, so the root prefix is known before a link is built.
function Pandoc(doc)
  if #failures == 0 then return nil end
  local source = pandoc.utils.stringify(doc.meta.srcpath or "this document")
  local lines = { string.format(
    "shortlist.lua: %d problem(s) in docs/%s.", #failures, source) }
  for _, message in ipairs(failures) do
    lines[#lines + 1] = "  " .. message
  end
  error(table.concat(lines, "\n"), 0)
end

-- THREE PASSES, IN THIS ORDER. Pandoc walks the blocks before the metadata by
-- default, which would build every link with an empty root prefix and break
-- them on any page below the site root. Naming the passes fixes the order.
return {
  { Meta = Meta },
  { Div = Div },
  { Pandoc = Pandoc },
}
