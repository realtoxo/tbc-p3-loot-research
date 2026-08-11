--[[
  Rewrite internal Markdown links to their built HTML counterparts.

  Documents cross-reference each other as `../method/framework.md` so the source
  tree stays navigable on GitHub and in an editor. The built site needs those to
  point at `.html`. External links, anchors, and mailto: are left alone.

  ../method/framework.md#the-verdict-stack
      -> ../method/framework.html#the-verdict-stack

  A MARKDOWN FILE UNDER data/ IS NOT A PAGE. `just build` renders `docs/**.md`
  and copies `data/facts/` across verbatim, so `data/facts/PROVENANCE.md`
  arrives in the site as Markdown and no `.html` is ever written for it.
  Rewriting its extension produced the only broken internal link in the site
  the first time a document linked it.
]]

function Link(el)
  local target = el.target

  -- Absolute URLs (scheme:) and bare anchors pass through untouched.
  if target:match("^%a[%w+.%-]*:") or target:sub(1, 1) == "#" then
    return el
  end

  local path, anchor = target:match("^([^#]*)(.*)$")
  -- Left as Markdown: these are copied, not rendered. datalinks.lua rewrites
  -- the leading `../` so the copied file resolves from the page.
  if path:match("data/") then
    return el
  end
  if path:sub(-3) == ".md" then
    el.target = path:sub(1, -4) .. ".html" .. anchor
  end
  return el
end
