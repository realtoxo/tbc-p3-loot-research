# Collected simulator profiles

One file per rostered spec. The schema, the anchor definitions and the open
questions live in [`../sim-profiles.yaml`](../sim-profiles.yaml); this directory
holds what was collected against it.

Every profile carries its own sources and the date they were read. Nothing here
is generated: `just regen` does not write these files and `just check` does not
diff them.

## What the two anchors are

`entry` is the spec's Tier 5 best-in-slot set, what a raider walks into Phase 3
wearing. Season 2 is in, Season 3 is out, because Season 3 opens five days after
the phase does.

`tier` is NOT a Phase 3 best-in-slot list. It is what a player could plausibly
wear four to six weeks into Mount Hyjal and Black Temple: the Tier 6 token
pieces actually reachable by then, with every other slot filled by Phase 2 gear,
early off-pieces, badge rewards and crafted items.

## Two things every reader must know before using a figure

**Gems are derived, not sourced.** No published guide gives a per-slot gem map;
they give a policy. Every gem in every profile was assigned by applying that
policy to the item's socket colors. The `gems_derived` field says so on each
profile, and it is the weakest data here.

**Only two Tier 6 tokens are reachable in the window,** the head from Archimonde
and the hands from Azgalor, both in Mount Hyjal. Shoulders, legs and chest come
from Black Temple bosses seven, eight and nine. Several specs therefore hold a
previous tier's set bonus, and for several the token is a raw stat downgrade or
breaks a bonus worth more than it. `token_arithmetic` on each profile records
what each token replaces and what it costs, in the source's own units. It states
no priority: that is the council's call, per the rule in AGENTS.md.
