--[[
  Turn a plain Markdown heading plus definition list into a spec card.

  One spec's argument for one item is a record, not a table row. Eight columns
  of prose wrap to a word a line at any page width, so the argument is rendered
  as a card: the spec name and its standing as a header, the upgrade figure
  below it, then each remaining field labelled.

  The source stays Markdown that a council member can edit. There is no HTML
  and no attribute syntax, and the same source reads correctly on GitHub and in
  an editor, where it is a heading followed by a definition list.

  Markdown

      ::: {.specs}

      #### Combat Rogue

      Delta
      :   [Cursed Vision of Sargeras]{.item}

      :::

  A DOCUMENT NAMES THE CLAIMANTS AND NOTHING ELSE. Everything a card says comes
  from a file, and the two files answer different questions:

      Constraints   where the spec sits against its hit, crit and haste caps,
                    built by tools/extract_constraints.py from
                    data/facts/hit.yaml, crit.yaml and haste.yaml
      Standing      BIS or Upgrade, derived from the best-in-slot captures via
                    theme/filters/bis.generated.lua, or stated on the heading
                    by the page generator, which derives it from the same
                    captures

  All of it was inline once, and both halves went wrong in the way inline text
  goes wrong. The facts drifted: the cards claimed the Beast Mastery Hunter and
  the Retribution Paladin were short at Entry while hit.yaml recorded both as
  full, because the written text left out an assumed raid debuff. The judgments
  were unfindable: the council's own conclusions existed in exactly one place,
  the middle of a document, keyed by nothing. Writing any of these terms in a
  document now fails the build naming the file it belongs in.

  Upgrade is still written, and any other term becomes a labelled field in the
  order it was written, so a document may add its own without a filter change.

  A block of two or more cards also carries the control that shows and hides
  them by spec. It is built here rather than in the browser because the standing
  order is decided here, and a list rebuilt from the page would either repeat
  that sort or contradict it.

  THE CONTROL IS AN ENHANCEMENT AND NEVER A GATE. Every card is written
  visible, the control ships with `hidden` on it, and the inline script in
  theme/template.html reveals it. A reader with no script therefore sees every
  card and no control, which is the page as it was before this existed. Cards
  rendered hidden and revealed by script would show a council member nothing at
  all when the script does not run, and a hidden claimant is how this feature
  would cause a wrong decision.

  The state is not remembered between page loads, for the same reason.
]]

local SPECIAL = { Upgrade = true }

-- Terms a document may no longer write, and where each one lives instead. Every
-- one of them was inline in a document once, and every one of them was either a
-- restatement of a fact file, a judgment kept in the only copy nobody could
-- find, or a label the pipeline now derives. The message names the source so
-- the fix is one step.
local GENERATED_TERM = {
  Constraints = "It is built from data/facts/hit.yaml, crit.yaml and "
    .. "haste.yaml. A fact in it belongs in the fact file it came from.",
  Standing = "It is derived from the best-in-slot captures in "
    .. "data/facts/sim-profiles/bis-capture and rendered by this filter; it "
    .. "is never written by hand.",
  Priority = "The priority scale retired from display on 20 August 2026 in "
    .. "favour of the two-level standing. The council's allocation record is "
    .. "held in data/judgments/priorities.yaml and no longer renders.",
  Unit = "It qualified the retired priority scale and is held in "
    .. "data/judgments/priorities.yaml, on the same entry.",
  For = "This field was removed on 10 August 2026. What creators said is "
    .. "captured in data/facts/creator-stances.yaml and renders above the cards.",
  Against = "This field was removed on 10 August 2026. What creators said is "
    .. "captured in data/facts/creator-stances.yaml and renders above the cards.",
}

local CONSTRAINTS = os.getenv("CONSTRAINTS_LUA")
  or "theme/filters/constraints.generated.lua"
local BIS = os.getenv("BIS_LUA") or "theme/filters/bis.generated.lua"

local function generated(path)
  local ok, table_ = pcall(dofile, path)
  if not ok or type(table_) ~= "table" then
    error(string.format(
      "specs.lua: cannot read %s.\nRun `just regen` to write it, and run the "
      .. "filters from the repository root.\n%s", path, tostring(table_)), 0)
  end
  return table_
end

local TRINKETS = os.getenv("TRINKETS_LUA")
  or "theme/filters/trinkets.generated.lua"

local constraints = generated(CONSTRAINTS)
local trinkets = generated(TRINKETS)

-- Which item ids each spec's simulated best-in-slot set wears, indexed by the
-- lowercase spec name because the card lowers its heading before every lookup.
local bis = {}
for spec, ids in pairs(generated(BIS)) do bis[spec:lower()] = ids end

-- Set by the template on every page, so a link from docs/items/ reaches
-- docs/specs/ whatever depth the reader is at.
local root = ""

-- A spec's page, from its name. The one rule, matching the slug the page
-- generator writes: lowercase, apostrophes dropped, everything else that is
-- not a letter or a digit becomes a hyphen.
local function spec_page(name)
  local slug = name:lower():gsub("'", ""):gsub("[^%w]+", "-")
  return root .. "specs/" .. slug:gsub("^%-+", ""):gsub("%-+$", "") .. ".html"
end

local card_failures = {}

-- Every definition of one term, flattened. A term carries one definition here,
-- but the AST permits several and dropping them silently would lose text.
local function flatten(definitions)
  local blocks = pandoc.List({})
  for _, definition in ipairs(definitions) do
    for _, block in ipairs(definition) do
      blocks:insert(block)
    end
  end
  return blocks
end

-- The inline content of paragraph-like blocks, for the places that need bare
-- text inside an element of our own rather than a wrapped paragraph.
local function inlines_of(blocks)
  local inlines = pandoc.List({})
  for _, block in ipairs(blocks) do
    if block.t == "Para" or block.t == "Plain" then
      inlines:extend(block.content)
    end
  end
  return inlines
end

local function label(text, class)
  return pandoc.Div({ pandoc.Plain(pandoc.Str(text)) }, pandoc.Attr("", { class }))
end

local function labelled(class, label_text, label_class, blocks)
  local content = pandoc.List({ label(label_text, label_class) })
  content:extend(blocks)
  return pandoc.Div(content, pandoc.Attr("", { class }))
end

local function card(header, list, id, item)
  local upgrade
  local fields = pandoc.List({})

  local name = pandoc.utils.stringify(header.content)

  -- THE STANDING IS DERIVED, NEVER WRITTEN BY HAND. The page generator states
  -- it on the claimant heading as a `standing` attribute, derived from the
  -- best-in-slot captures; a heading without one, which is the hand-written
  -- worked example, falls back to the same answer read from
  -- bis.generated.lua, keyed by the item the container stamped and the spec
  -- the heading names. Both roads start at the same captures, so they cannot
  -- disagree.
  --
  -- TWO STATES AND NO THIRD. A claimant is BIS where its simulated
  -- best-in-slot set wears the item and an Upgrade everywhere else. There is
  -- no undecided state, because nothing here waits on a council: a spec with
  -- no simulated set, which is the tanks, the healers and the Feral Cat, has
  -- no set to wear anything and every claim it holds reads Upgrade.
  --
  -- THE ARGUMENT NO LONGER LIVES HERE. A For and Against pair was written per
  -- item per spec and only ever filled in for Cursed Vision, one worked
  -- example across eight claimants. What a card now carries instead is what
  -- creators actually said, captured with a timestamp, which is 580 remarks on
  -- 173 items rather than one hand-written argument. The guild lead removed the
  -- field on 10 August 2026 as a feature the commentary had superseded.
  local standing = header.attributes and header.attributes.standing
  if standing ~= "BIS" and standing ~= "Upgrade" then
    local worn = bis[name:lower()]
    standing = (worn and item and worn[tonumber(item)]) and "BIS" or "Upgrade"
  end
  local caps = constraints[name:lower()]
  if not caps then
    card_failures[#card_failures + 1] = string.format(
      "%q has no cap position in %s, so its Constraints cannot be built.\n"
      .. "      Add the spec to SPECS in tools/extract_ladder.py and give it a "
      .. "row in data/facts/hit.yaml, then run `just regen`.", name, CONSTRAINTS)
    return nil
  end
  -- Ahead of every written field, because a reader needs what binds the spec
  -- before an argument about one item makes sense.
  --
  -- ROWS, NOT A PARAGRAPH. These used to be joined with spaces into one block
  -- of prose, which printed on every claimant card and ran to a dozen lines on
  -- an item page carrying twenty of them. The generator now emits
  -- "label<TAB>value<TAB>note" for a figure, a bare sentence for a note, and an
  -- empty string for a break between groups.
  local rows = pandoc.List({})
  for _, line in ipairs(caps) do
    if line == "" then
      rows:insert(pandoc.Div({}, pandoc.Attr("", { "constraint-break" })))
    else
      local label, value, note = line:match("^([^\t]*)\t([^\t]*)\t(.*)$")
      if label then
        local cells = pandoc.List({
          pandoc.Span({ pandoc.Str(label) },
            pandoc.Attr("", { "constraint-label" })),
          pandoc.Span({ pandoc.Str(value) },
            pandoc.Attr("", { "constraint-value" })),
        })
        -- ALWAYS THREE CELLS, EVEN WHEN THE NOTE IS EMPTY. The row is a
        -- `display: contents` grid row, so its children ARE the grid cells. A
        -- row that emitted only two left the third column unfilled and the
        -- NEXT row's label slid into it, which put "Improved Faerie Fire" in
        -- Precision's note column and pushed every following row one cell
        -- left. Reported from a screenshot on 10 August 2026.
        cells:insert(pandoc.Span(note ~= "" and { pandoc.Str(note) } or {},
          pandoc.Attr("", { "constraint-note" })))
        rows:insert(pandoc.Div({ pandoc.Plain(cells) },
          pandoc.Attr("", { "constraint-row" })))
      else
        rows:insert(pandoc.Div({ pandoc.Plain({ pandoc.Str(line) }) },
          pandoc.Attr("", { "constraint-line" })))
      end
    end
  end
  fields:insert({ term = "Constraints", body = pandoc.List({
    pandoc.Div(rows, pandoc.Attr("", { "constraint-block" })),
  }) })

  -- A PLAYER WEARS TWO TRINKETS, so a trinket card that names only the item
  -- under discussion answers half the question. The other slot comes from the
  -- captured set for this spec, which is a fact about what that set holds and
  -- not a recommendation.
  --
  -- NO SINGLE TRINKET IS ASSUMED. Dragonspine Trophy fits the eight physical
  -- specs and none of the casters, who carry 40 attack power for nothing;
  -- Icon of the Silver Crescent is the caster counterpart at five of six. The
  -- capture gets all of them right, including the Destruction Warlock, who
  -- wears neither.
  if item and trinkets.trinket_ids[tonumber(item)] then
    -- The spec id is the card's own heading, lowered and underscored, which is
    -- the key the captures use.
    local pair = trinkets.pairs[name:lower():gsub("[^%w]+", "_")]
    if pair then
      local other
      for _, worn in ipairs(pair) do
        if tostring(worn.id) ~= tostring(item) then other = worn end
      end
      if other then
        fields:insert({ term = "Paired with", body = pandoc.List({
          pandoc.Plain(pandoc.List({
            pandoc.Str(other.name),
            pandoc.Space(),
            pandoc.Emph({ pandoc.Str("in this spec's captured set") }),
          })),
        }) })
      end
    end
  end

  for _, item in ipairs(list.content) do
    local term = pandoc.utils.stringify(item[1])
    local body = flatten(item[2])
    if GENERATED_TERM[term] then
      card_failures[#card_failures + 1] = string.format(
        "the %s card writes a %s field, which is not written in a document.\n"
        .. "      %s", name, term, GENERATED_TERM[term])
    elseif not SPECIAL[term] then
      fields:insert({ term = term, body = body })
    elseif term == "Upgrade" then upgrade = body
    end
  end

  local blocks = pandoc.List({})

  -- The header keeps its own attributes. Pandoc's HTML writer hoists them onto
  -- the enclosing element and writes it as a <section>, so adding a class here
  -- would duplicate it onto that section. Style the heading through its parent.
  -- THE CLAIMANT NAME LINKS TO ITS SPEC PAGE. A reader looking at six
  -- claimants on one drop asks what else each of them wants, and that answer
  -- is one page away. The heading keeps its own level and identifier; only its
  -- text becomes a link.
  header = header:clone()
  -- The attribute has done its work; leaving it on the heading would hoist it
  -- onto the enclosing section as markup no reader needs.
  header.attributes.standing = nil
  header.content = pandoc.List({
    pandoc.Link(header.content, spec_page(name), "",
      pandoc.Attr("", { "spec-link" })) })

  local head = pandoc.List({ header })
  -- THE WORD "STANDING" IS SAID, NOT IMPLIED. The priority badge once carried
  -- its value alone and the guild lead reported it on 13 August 2026: "we just
  -- see the priority value and it's very confusing". The lesson outlives the
  -- scale: the badge names its field.
  --
  -- Two states, two appearances. BIS takes the loud badge, because it is the
  -- answer a council table reaches for first; Upgrade takes the quiet one, and
  -- a reader scanning a page tells them apart without reading the words.
  local classes = { "spec-standing" }
  if standing ~= "BIS" then
    table.insert(classes, "spec-standing-upgrade")
  end
  head:insert(pandoc.Plain(pandoc.Span({
    pandoc.Span(pandoc.Str("Standing"), pandoc.Attr("", { "spec-standing-label" })),
    pandoc.Span(pandoc.Str(standing), pandoc.Attr("", classes)),
  }, pandoc.Attr("", { "spec-standing-pair" }))))
  blocks:insert(pandoc.Div(head, pandoc.Attr("", { "spec-head" })))

  if upgrade then
    local classes = { "spec-figure" }
    if pandoc.utils.stringify(upgrade):match("^%s*[Mm]inus") then
      table.insert(classes, "down")
    end
    blocks:insert(pandoc.Div({ pandoc.Plain(inlines_of(upgrade)) }, pandoc.Attr("", classes)))
  end

  if #fields > 0 then
    local body = pandoc.List({})
    for _, f in ipairs(fields) do
      body:insert(labelled("field", f.term, "field-label", f.body))
    end
    blocks:insert(pandoc.Div(body, pandoc.Attr("", { "spec-fields" })))
  end

  -- BIS above Upgrade, always, because the set that wears the item is the
  -- claim a council table reads first.
  local rank = standing == "BIS" and 1 or 2
  return pandoc.Div(blocks, pandoc.Attr(id, { "spec" })),
    rank,
    pandoc.utils.stringify(header.content),
    standing
end

-- ------------------------------------------------------------------- control

local function escape(text)
  return (text
    :gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;")
    :gsub('"', "&quot;"))
end

-- One checkbox per card, plus the count and the reset. The count is a live
-- region rather than a decoration: a reader must never be looking at three of
-- eight cards and reading them as all of them.
--
-- PARTITIONED BY STANDING, NOT LISTED FLAT. A flat row of eight names with a
-- small tag beside each one asks the reader to do the grouping by eye, and the
-- grouping is the thing they came for: the question at a council table is "who
-- wears this in their best set", not "what did the Enhancement Shaman get".
-- The partition is two groups at most, BIS first and Upgrade after it, each
-- labelled and each carrying a checkbox of its own, so showing every BIS
-- claimant alone is one click, and the groups are additive so any combination
-- is reachable.
--
-- The cards arrive already sorted BIS first, so grouping is a run over that
-- order and the control cannot disagree with the cards it filters.
local function control(cards)
  local html = pandoc.List({})
  html:insert('<div class="spec-filter" data-spec-filter hidden>')
  html:insert('<fieldset class="spec-filter-set">')
  html:insert('<legend class="spec-filter-legend">Show spec cards</legend>')
  html:insert('<div class="spec-filter-groups">')

  local group, index, current_key = nil, 0, ""
  local function close_group()
    if group then html:insert("</ul>\n</div>") end
  end
  for _, c in ipairs(cards) do
    if c.standing ~= group then
      close_group()
      group, index = c.standing, index + 1
      local key = "spec-group-" .. tostring(index)
      html:insert('<div class="spec-filter-group">')
      html:insert(string.format(
        '<label class="spec-filter-group-head">'
        .. '<input type="checkbox" checked data-spec-group="%s">'
        .. '<span class="spec-filter-group-name">%s</span>'
        .. "</label>", escape(key), escape(c.standing)))
      html:insert('<ul class="spec-filter-options">')
      current_key = key
    end
    html:insert(string.format(
      '<li><label class="spec-filter-option">'
      .. '<input type="checkbox" checked data-spec-card="%s" aria-controls="%s"'
      .. ' data-spec-member="%s">'
      .. '<span class="spec-filter-name">%s</span>'
      .. "</label></li>",
      escape(c.id), escape(c.id), escape(current_key), escape(c.name)))
  end
  close_group()
  html:insert("</div>")
  html:insert("</fieldset>")
  html:insert(string.format(
    '<p class="spec-filter-count" data-spec-count role="status">'
    .. 'Showing all %d spec cards.</p>', #cards))
  -- Two controls, not one. Turning a filter off a spec at a time is tedious
  -- enough that a reader leaves the page half filtered and forgets, so a single
  -- way back to everything is what makes the filter safe to use at all.
  html:insert('<p class="spec-filter-actions">')
  html:insert('<button type="button" class="spec-filter-reset" data-spec-reset disabled>'
    .. "Show every spec</button>")
  html:insert('<button type="button" class="spec-filter-clear" data-spec-clear>'
    .. "Clear all specs</button>")
  html:insert("</p>")
  -- Cleared must never be a silent empty region. An empty card area with no
  -- message reads as a claim that this item has no claimants, which is a
  -- factual statement and a wrong one.
  html:insert('<p class="spec-filter-empty" data-spec-empty hidden>'
    .. "No specs are selected, so no cards are showing. "
    .. "Use Show every spec to bring all of them back.</p>")
  html:insert("</div>")
  return pandoc.RawBlock("html", table.concat(html, "\n"))
end

-- Card ids are unique within the document, which is one Lua state per page.
local card_id = 0

function Div(div)
  if not div.classes:includes("specs") then
    return nil
  end

  -- Stamped by items.lua from the container that introduces the item. See the
  -- note there for why this filter cannot read it itself.
  local item = div.attributes.item

  local out = pandoc.List({})
  -- Cards render in standing order, BIS first and Upgrade after it, never in
  -- the order an author happened to write them. A reader comparing two items
  -- should meet the wearing claim in the same place every time. Ties keep
  -- written order, which is stable and lets an author group two specs that
  -- share a standing.
  local cards = {}
  local seq = 0
  local pending
  for _, block in ipairs(div.content) do
    if block.t == "Header" then
      if pending then out:insert(pending) end
      pending = block
    elseif block.t == "DefinitionList" and pending then
      card_id = card_id + 1
      local id = "spec-card-" .. card_id
      local built, rank, name, standing = card(pending, block, id, item)
      -- nil means the card recorded why it could not be built. The document is
      -- stopped in the Pandoc hook, so every bad card is reported and not only
      -- the first; nothing is inserted for one that failed.
      if built then
        seq = seq + 1
        cards[#cards + 1] =
          { block = built, rank = rank, seq = seq, id = id, name = name, standing = standing }
      end
      pending = nil
    else
      if pending then
        out:insert(pending)
        pending = nil
      end
      out:insert(block)
    end
  end
  if pending then out:insert(pending) end

  table.sort(cards, function(a, b)
    if a.rank ~= b.rank then return a.rank < b.rank end
    return a.seq < b.seq
  end)
  -- NO CLAIMANT IS SAID, NOT LEFT BLANK. A `.specs` block with nothing in it
  -- happens on an item no spec ranks in the top five of its slot, which is a
  -- real answer and one worth reading: five Tier 6 drops are in no workbook
  -- ladder at all. An empty region would read as a page that failed to build.
  if #cards == 0 then
    out:insert(pandoc.Div(
      { pandoc.Plain(pandoc.Str(
        "No rostered spec ranks this item in the top five of its slot, so no "
        .. "claimant card is drawn. That is what the EP Workbook says about "
        .. "the item, and not a decision the council has taken.")) },
      pandoc.Attr("", { "specs-empty" })))
  end
  -- One card cannot be filtered against anything, so the control is only worth
  -- its own height from two upwards.
  if #cards > 1 then out:insert(control(cards)) end
  for _, c in ipairs(cards) do out:insert(c.block) end

  div.content = out
  return div
end

function Meta(meta)
  if meta.root then root = pandoc.utils.stringify(meta.root) end
  return meta
end

function Pandoc(doc)
  if #card_failures == 0 then return nil end
  local source = pandoc.utils.stringify(doc.meta.srcpath or "this document")
  local lines = { string.format(
    "specs.lua: %d problem(s) in docs/%s.", #card_failures, source) }
  for _, message in ipairs(card_failures) do
    lines[#lines + 1] = "  " .. message
  end
  error(table.concat(lines, "\n"), 0)
end

-- Metadata before blocks, so a card's link to its spec page carries the root
-- prefix. Pandoc walks the other way round unless the passes are named.
return {
  { Meta = Meta },
  { Div = Div },
  { Pandoc = Pandoc },
}
