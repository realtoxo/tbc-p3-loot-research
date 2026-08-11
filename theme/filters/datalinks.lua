-- Make links to the fact files work in the built site.
--
-- A document links a fact file the way it sits on disk, `../data/facts/hit.yaml`
-- relative to `docs/`. That is correct in the repository and it is what
-- `tools/check_links.py` validates. It is wrong in the built site, where the
-- page sits at the site root and `../` escapes the served directory, so every
-- one of those links 404s under `just serve`.
--
-- The build copies `data/facts/` into the site and passes each page its own
-- `root` prefix. This rewrites the disk-relative form into the site-relative
-- one, so a single link in the source resolves in both places.

local root = ""

function Meta(meta)
  if meta.root then
    root = pandoc.utils.stringify(meta.root)
  end
  return meta
end

local function rewrite(target)
  -- Only touch links that climb out of docs/ to reach data/.
  local rest = target:match("^%.%./.*data/(.*)$")
  if rest then
    return root .. "data/" .. rest
  end
  return target
end

function Link(el)
  el.target = rewrite(el.target)
  return el
end

return {
  { Meta = Meta },
  { Link = Link },
}
