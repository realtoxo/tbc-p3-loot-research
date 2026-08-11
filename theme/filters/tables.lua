--[[
  Wrap every table in a scrolling container at the AST level.

  Wide comparison tables are the dominant content in this compendium. Applying
  the wrapper here rather than with JavaScript means horizontal scrolling works
  with scripts disabled, when printing, and when the page is opened straight
  from disk.

  Markdown            ->  <div class="table-wrap"><table>...</table></div>
]]

function Table(tbl)
  return pandoc.Div({ tbl }, pandoc.Attr("", { "table-wrap" }))
end
