--[[
  Suppress the table of contents on documents that have too few headings for it
  to earn its column.

  The page shell reserves a fixed rail for the table of contents. On a document
  with two or three sections that rail lists what the reader can already see,
  while the content column beside it is starved of the width its tables and
  card grids need. Counting the headings here, rather than asking each author
  to remember a front-matter switch, keeps the decision mechanical.

  Sets the `tocless` metadata flag, which theme/template.html reads to drop the
  aside and collapse the shell to one column.

  The count follows `--toc-depth=2` in the justfile. Change one and change the
  other.
]]

local TOC_DEPTH = 2
local MIN_ENTRIES = 4

local entries = 0

function Header(h)
  if h.level <= TOC_DEPTH then
    entries = entries + 1
  end
end

function Pandoc(doc)
  if entries < MIN_ENTRIES then
    doc.meta.tocless = true
  end
  return doc
end
