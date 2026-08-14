--[[
What creators have said about the item, above the cards, read from data.

  ::: {.commentary}

  [Cursed Vision of Sargeras]{.item}

  :::

The author names the item and nothing else. Every entry comes from
`data/facts/field-commentary.yaml` by way of `commentary.generated.lua`, so a
claim, a creator, a link and a timestamp are never retyped into a document where
they would go stale.

WHY IT RUNS BEFORE `items.lua`. It reads the plain `[Name]{.item}` span to
resolve the item, and emits `.item` spans of its own, which `items.lua` then
links and gives tooltips. `delta.lua` runs first for the same reason.

WHY IT SITS ABOVE THE CARDS. It is about the item, not about one spec, so a
reader meets it once rather than card by card.

WHY A PARAPHRASE. A transcript quote is someone else's words reproduced. A
paraphrase is our summary, and the timestamp is what makes it checkable against
the recording.

WHAT THIS IS NOT. A field source explains a mechanism and nominates an item for
a closer look. It never moves a number, per the framework, so it is set quieter
than the analysis below it and never sits beside a figure.
]]

local itemdb = dofile(os.getenv("ITEMDB_LUA") or "theme/filters/itemdb.lua")
local GENERATED = os.getenv("COMMENTARY_LUA")
  or "theme/filters/commentary.generated.lua"

local ok, commentary = pcall(dofile, GENERATED)
if not ok or type(commentary) ~= "table" then commentary = {} end

local failures = {}

local function fail(message)
  failures[#failures + 1] = message
end

-- The one item reference in the block, as the span itself, before `items.lua`
-- runs. The span and not its text, because a span may carry the id that says
-- which of two items sharing a name it means.
local function item_span(blocks)
  for _, block in ipairs(blocks) do
    if block.t == "Para" or block.t == "Plain" then
      for _, inline in ipairs(block.content) do
        if inline.t == "Span" and inline.classes:includes("item") then
          return inline
        end
      end
    end
  end
  return nil
end

-- WHAT THE LABEL SAYS, AND WHY IT STOPPED BEING THE STANCE.
--
-- It used to read "Speaks well of it" or "Argues against it". The guild lead
-- rejected that axis on 13 August 2026: "The item exists to exist. It does not
-- matter if they like it or not. Our influencer quotes should focus on opinions
-- about where the item should be placed."
--
-- Approval and routing are different questions and the stance answers only the
-- first. Zatar on The Skull of Gul'dan is the case that proves it: he speaks
-- well of it throughout AND argues the hit rating is wasted on three of the
-- four casters who could take it. "Speaks well of it" is true and useless. The
-- label now names the destination, from data/facts/creator-routing.yaml.
local STANCE = {
  favours = "Speaks well of it",
  against = "Argues against it",
  conditional = "It depends",
  mentions_only = "Mentioned, no view given",
}

local function name_list(names)
  if #names == 1 then return names[1] end
  if #names == 2 then return names[1] .. " and " .. names[2] end
  local head = {}
  for i = 1, #names - 1 do head[#head + 1] = names[i] end
  return table.concat(head, ", ") .. " and " .. names[#names]
end

-- The routing as one line, or nil where the pass recorded none. A remark that
-- states no routing says so rather than falling back to approval, because
-- "Mentioned, no view given" is the honest answer for those and the stance file
-- already says it.
local function routing_text(entry)
  local to = entry.routes_to or {}
  local away = entry.routes_away_from or {}
  if #to > 0 and #away > 0 then
    return "Puts it on " .. name_list(to) .. ", not " .. name_list(away)
  elseif #to > 0 then
    return "Puts it on " .. name_list(to)
  elseif #away > 0 then
    return "Keeps it off " .. name_list(away)
  end
  return nil
end

local function views_text(views)
  if views >= 1000000 then
    return string.format("%.1fM views", views / 1000000)
  elseif views >= 1000 then
    return string.format("%.0fk views", views / 1000)
  end
  return string.format("%d views", views)
end

local function label(text, class)
  return pandoc.Div({ pandoc.Plain(pandoc.Str(text)) }, pandoc.Attr("", { class }))
end

local function entry_block(entry)
  local source = pandoc.List({
    pandoc.Div({ pandoc.Plain(pandoc.Str(entry.creator)) },
      pandoc.Attr("", { "commentary-creator" })),
  })

  -- The recording line: channel, then the timestamp as a link into the moment.
  local recording = pandoc.List({})
  if entry.channel and entry.channel ~= "" then
    recording:insert(pandoc.Str(entry.channel))
  end
  if entry.timestamp and entry.timestamp ~= "" then
    if #recording > 0 then
      recording:insert(pandoc.Space())
      recording:insert(pandoc.Str("\194\183"))
      recording:insert(pandoc.Space())
    end
    if entry.url and entry.url ~= "" and entry.url ~= "PLACEHOLDER" then
      recording:insert(pandoc.Link(pandoc.Str(entry.timestamp), entry.url))
    else
      recording:insert(pandoc.Str(entry.timestamp))
    end
  end
  if #recording > 0 then
    source:insert(pandoc.Div({ pandoc.Plain(recording) },
      pandoc.Attr("", { "commentary-recording" })))
  end

  -- Reach sits beside the creator so a reader can weigh how far a view
  -- travelled. It says nothing about whether the view is right.
  if entry.views and entry.views > 0 then
    source:insert(pandoc.Div({ pandoc.Plain(pandoc.Str(views_text(entry.views))) },
      pandoc.Attr("", { "commentary-reach" })))
  end

  local classes = { "commentary-entry" }
  if not entry.captured then table.insert(classes, "commentary-entry-pending") end

  -- ONE CHILD PER COLUMN. .commentary-entry is a two column grid, so the
  -- stance, the claim and the note go inside a single body div. Added as
  -- siblings they become grid cells of their own and the stance lands in the
  -- claim column while the claim drops to the next row.
  local body = pandoc.List({})
  local routed = routing_text(entry)
  if routed then
    body:insert(pandoc.Div({ pandoc.Plain(pandoc.Str(routed)) },
      pandoc.Attr("", { "commentary-stance", "commentary-routed",
                        "stance-" .. (entry.stance or "none") })))
  elseif entry.stance and entry.stance ~= "" then
    -- NO ROUTING WAS READ OUT OF THIS ONE, so the card falls back to what the
    -- capture does say. Eighty remarks are genuinely a proc rate or a passing
    -- comparison and state nothing about who should hold the item.
    body:insert(pandoc.Div({ pandoc.Plain(pandoc.Str(STANCE[entry.stance]
      or entry.stance)) },
      pandoc.Attr("", { "commentary-stance", "stance-" .. entry.stance })))
  end
  body:insert(pandoc.Div({ pandoc.Plain(pandoc.Str(entry.claim)) },
    pandoc.Attr("", { "commentary-claim" })))
  if entry.note and entry.note ~= "" then
    body:insert(pandoc.Div({ pandoc.Plain(pandoc.Str(entry.note)) },
      pandoc.Attr("", { "commentary-note" })))
  end

  return pandoc.Div({
    pandoc.Div(source, pandoc.Attr("", { "commentary-source" })),
    pandoc.Div(body, pandoc.Attr("", { "commentary-body" })),
  }, pandoc.Attr("", classes))
end

function Div(div)
  if not div.classes:includes("commentary") then
    return nil
  end

  local span = item_span(div.content)
  if not span then
    fail("a .commentary block names no item. Write one [Item Name]{.item} in it.")
    return div
  end

  local row, why = itemdb.resolve_span(span)
  if not row then
    fail(string.format("%q in a .commentary block %s.",
      pandoc.utils.stringify(span), why))
    return div
  end

  local record = commentary[tostring(row.item_id)] or {}
  local entries = record.remarks or {}

  -- AN EMPTY SECTION IS REMOVED, AND THE HONESTY MOVES TO ONE PLACE.
  -- This used to print "Nothing captured for this item yet" so that silence
  -- could not read as "nobody has said anything about this item", which is a
  -- claim. That reasoning is right and the execution was not: with commentary
  -- captured for a handful of items, the line appeared on 173 of 177 pages,
  -- which trains a reader to skip the section on the four where it matters.
  -- docs/conventions.md now states once that the section appears only where
  -- something is captured, and that its absence means not captured rather
  -- than nothing said.
  if #entries == 0 then
    return {}
  end

  local out = pandoc.List({ label("What influencers say", "commentary-label") })

  -- DISAGREEMENT IS THE USEFUL PART, so it is announced rather than left for a
  -- reader to notice by comparing five paragraphs.
  if record.disagreed then
    out:insert(label("Creators disagree about this item",
      "commentary-disagreed"))
  end
  if record.total and record.total > #entries then
    out:insert(label(string.format(
      "Showing %d of %d captured remarks, widest reach first, with every view "
        .. "represented", #entries, record.total), "commentary-count"))
  end

  do
    local built = pandoc.List({})
    for _, entry in ipairs(entries) do
      built:insert(entry_block(entry))
    end
    out:insert(pandoc.Div(built, pandoc.Attr("", { "commentary-entries" })))
  end

  div.content = out
  return div
end

function Pandoc(doc)
  if #failures == 0 then return nil end
  local source = pandoc.utils.stringify(doc.meta.srcpath or "this document")
  local lines = { string.format(
    "commentary.lua: %d problem(s) in docs/%s.", #failures, source) }
  for _, message in ipairs(failures) do
    lines[#lines + 1] = "  " .. message
  end
  error(table.concat(lines, "\n"), 0)
end
