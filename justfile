# TBC Phase 3 Loot Compendium
#
# Every command for this repository lives here. Run `just` to list them.

set shell := ["bash", "-uc"]

src      := "docs"
out      := "site"
assets   := "theme"
template := "theme/template.html"
filters  := "--lua-filter=theme/filters/tables.lua --lua-filter=theme/filters/links.lua --lua-filter=theme/filters/delta.lua --lua-filter=theme/filters/commentary.lua --lua-filter=theme/filters/shortlist.lua --lua-filter=theme/filters/items.lua --lua-filter=theme/filters/specs.lua --lua-filter=theme/filters/toc.lua --lua-filter=theme/filters/datalinks.lua"
port     := "4000"

# List available commands.
default:
    @just --list --unsorted

# ---------------------------------------------------------------- site build

# Render every Markdown document to a nested static site.
build: _clean-site
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p "{{out}}"
    cp "{{assets}}/style.css" "{{out}}/style.css"
    # Item icons, committed rather than hotlinked, for the same reason the
    # Wowhead tooltip script is not used: this site is read locally.
    if [ -d "{{assets}}/icons" ]; then cp -R "{{assets}}/icons" "{{out}}/icons"; fi
    # The documents link their fact files. Publish them so those links resolve
    # under `just serve` as well as on disk.
    mkdir -p "{{out}}/data"
    cp -R data/facts "{{out}}/data/facts"
    count=0
    # docs/kb/ is the agent knowledge base, not compendium content. It is read
    # from the repository, never published, so the build skips it.
    while IFS= read -r f; do
        rel="${f#{{src}}/}"
        dest="{{out}}/${rel%.md}.html"
        mkdir -p "$(dirname "$dest")"
        # Relative path back to the site root, so the site works from file://
        depth=$(awk -F/ '{print NF-1}' <<< "$rel")
        root=""
        for ((i=0; i<depth; i++)); do root="../$root"; done
        pandoc "$f" \
            --from=markdown+fenced_divs+bracketed_spans+pipe_tables+raw_html+auto_identifiers \
            --to=html5 \
            --standalone \
            --template="{{template}}" \
            --toc --toc-depth=2 \
            {{filters}} \
            --css="${root}style.css" \
            --metadata=root:"$root" \
            --metadata=srcpath:"$rel" \
            --output="$dest"
        count=$((count+1))
    done < <(find "{{src}}" -name '*.md' -type f -not -path "{{src}}/kb/*" | sort)
    echo "built $count page(s) -> {{out}}/"

# Render one document to a single self-contained HTML file, for publishing.
bundle FILE:
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p "{{out}}/bundles"
    name="$(basename "{{FILE}}" .md)"
    pandoc "{{FILE}}" \
        --from=markdown+fenced_divs+bracketed_spans+pipe_tables+raw_html \
        --to=html5 --standalone --embed-resources \
        --template="{{template}}" \
        {{filters}} \
        --metadata=root:"" --metadata=standalone_bundle:true \
        --css="{{assets}}/style.css" \
        --output="{{out}}/bundles/${name}.html"
    echo "bundled -> {{out}}/bundles/${name}.html  ($(du -h "{{out}}/bundles/${name}.html" | cut -f1))"

# Publish the built site to the gh-pages branch. The output is not tracked on
# main, so the commit is written from a throwaway index instead of the work
# tree, and parented on the current gh-pages tip so the push fast-forwards.
publish: build
    #!/usr/bin/env bash
    set -euo pipefail
    git fetch origin gh-pages
    export GIT_INDEX_FILE="$(mktemp -u "${TMPDIR:-/tmp}/tbc-publish-index.XXXXXX")"
    trap 'rm -f "$GIT_INDEX_FILE"' EXIT
    # --work-tree puts the repository .gitattributes out of reach, so the
    # `*.csv text eol=lf` rule stops applying and the CRLF that Python's csv
    # writer emits into data/facts/*.csv would rewrite three files on every
    # publish. Point git back at the attributes file to keep the bytes stable.
    git -c core.attributesfile="$PWD/.gitattributes" --work-tree="{{out}}" add -Af .
    tree="$(git write-tree)"
    if [ "$tree" = "$(git rev-parse origin/gh-pages^{tree})" ]; then
        echo "gh-pages already carries this site; nothing to publish"
        exit 0
    fi
    commit="$(git commit-tree "$tree" -p origin/gh-pages -m "publish site $(git rev-parse --short HEAD)")"
    git push origin "$commit":gh-pages
    echo "published -> gh-pages  ($commit, tree $tree)"

# ---------------------------------------------------------------- dev loop

# Serve the built site. Does not rebuild.
serve: build
    @echo "serving {{out}} on http://localhost:{{port}}"
    @npx --yes browser-sync start --server "{{out}}" --port {{port}} --no-open --no-notify --files "{{out}}/**/*"

# Rebuild on change and live-reload the browser.
dev:
    #!/usr/bin/env bash
    set -euo pipefail
    just build
    echo "watching docs/ theme/ data/ on http://localhost:{{port}}"
    npx --yes browser-sync start --server "{{out}}" --port {{port}} --no-open --no-notify --files "{{out}}/**/*" &
    bs=$!
    trap 'kill $bs 2>/dev/null || true' EXIT INT TERM
    # Only watch directories that exist; evidence/ and others arrive later.
    watch=()
    for d in {{src}} {{assets}} data tools evidence; do
        [[ -d "$d" ]] && watch+=(--watch "$d")
    done
    watchexec --exts md,css,html,lua,csv,yml,yaml,py \
        "${watch[@]}" \
        --debounce 200ms --on-busy-update=restart -- just build
    wait

# ---------------------------------------------------------------- integrity

# Fail if generated documents drift from their data, or were hand-edited.
check: regen
    #!/usr/bin/env bash
    set -euo pipefail
    generated="data/facts/consumable-ids.yaml data/facts/drops.csv data/facts/items.csv data/facts/effect-text.csv data/facts/talent-conversions.yaml data/facts/transcript-mentions.csv data/facts/item-effects.csv data/facts/hit-captured.yaml data/facts/set-stats.yaml theme/filters/commentary.generated.lua theme/filters/constraints.generated.lua theme/filters/conversions.generated.lua theme/filters/judgments.generated.lua theme/filters/ladder.generated.lua theme/filters/trinkets.generated.lua theme/filters/unranked.generated.lua theme/filters/pages.generated.lua docs/items docs/specs docs/bosses.md docs/specs.md data/facts/sim-profiles/bis-capture data/sim/gear docs/sims.md docs/sims"
    if ! git diff --quiet -- $generated; then
        echo "ERROR: the generated tables differ after regeneration." >&2
        echo "Either the data changed and you should commit, or a generated file was hand-edited." >&2
        git --no-pager diff --stat -- $generated >&2
        exit 1
    fi
    echo "generated files are in sync with their data"
    python3 tools/check_gating.py
    python3 tools/check_hit_capture.py
    python3 tools/check_capture_availability.py
    python3 tools/check_tank_defense.py
    python3 tools/check_token_arithmetic.py
    python3 tools/check_roster.py
    python3 tools/check_raid_buffs.py
    python3 tools/check_weapon_layout.py
    python3 tools/check_workbook_columns.py
    python3 tools/check_sim_profiles.py
    python3 tools/check_sim_options.py

# Run every gear profile through the simulator and rewrite the figures and the
# pages that read them. NOT part of `just regen` or `just check`: it needs the
# wowsimcli binary and takes minutes, and a check that reruns a simulation would
# fail the build on run-to-run noise. Install the binary with
# tools/install_wowsimcli.sh first.
sim ITERATIONS="10000":
    @python3 tools/run_sims.py --iterations {{ITERATIONS}} --out data/facts/sim-figures.yaml
    @python3 tools/generate_sim_pages.py

# Fail if a sim profile wears a gem or an enchant Phase 3 cannot supply.
# Runs inside `just check` as well; this is the one-line way to run it alone.
gating:
    @python3 tools/check_gating.py

# Check each captured hit set against its own per-slot rows, and check the
# progression premise those captures rest on against the drop table.
captures:
    @python3 tools/check_roster.py
    @python3 tools/check_raid_buffs.py
    @python3 tools/check_token_arithmetic.py
    @python3 tools/check_hit_capture.py
    @python3 tools/check_capture_availability.py
    @python3 tools/check_tank_defense.py

# Path to a wowsims-tbc-new checkout holding assets/database/db.json.
wowsims := env_var_or_default("WOWSIMS_TBC", "../tbc-phase-research-recovered/data/raw/vendor/wowsims-tbc-new-master")

# Fetch any item icon not already committed. Network-bound, and deliberately
# not part of `just regen`, which must run offline and be reproducible.
icons:
    @python3 tools/fetch_icons.py --db "{{wowsims}}/assets/database/db.json" --out theme/icons

# Regenerate derived fact tables from source data.
regen:
    @python3 tools/extract_drops.py --db "{{wowsims}}/assets/database/db.json" --out data/facts/drops.csv
    @python3 tools/extract_items.py --db "{{wowsims}}/assets/database/db.json" --out data/facts/items.csv
    @python3 tools/extract_unranked.py --out theme/filters/unranked.generated.lua
    @python3 tools/extract_effect_text.py --out data/facts/effect-text.csv
    @python3 tools/extract_talent_rates.py --out data/facts/talent-conversions.yaml
    @python3 tools/extract_commentary.py
    # These two produce what extract_constraints reads, so they run BEFORE it.
    # Reversed, a single `just regen` wrote the card text from the PREVIOUS
    # rollup and only converged on a second run, which `just check` hid by
    # regenerating once and diffing.
    @python3 tools/extract_hit_captures.py --out data/facts/hit-captured.yaml
    @python3 tools/extract_set_stats.py --out data/facts/set-stats.yaml
    @python3 tools/extract_constraints.py --out theme/filters/constraints.generated.lua
    @python3 tools/extract_judgments.py --out theme/filters/judgments.generated.lua
    @python3 tools/extract_trinket_pairs.py --out theme/filters/trinkets.generated.lua
    @python3 tools/generate_item_pages.py --db "{{wowsims}}/assets/database/db.json" --out docs/items
    @python3 tools/generate_spec_pages.py
    @python3 tools/extract_conversions.py --out theme/filters/conversions.generated.lua
    @python3 tools/extract_ladder.py --db "{{wowsims}}/assets/database/db.json" --out theme/filters/ladder.generated.lua
    @python3 tools/index_transcript_mentions.py --out data/facts/transcript-mentions.csv
    @python3 tools/extract_consumable_ids.py --out data/facts/consumable-ids.yaml
    # The best-in-slot anchor and the profiles that carry it. These are offline
    # and deterministic, so they belong here rather than beside the simulator
    # run: `just check` regenerates and diffs, which is what stops a hand edit
    # to a gear file from surviving.
    @python3 tools/build_bis_capture.py
    @python3 tools/export_sim_profiles.py --out data/sim/gear
    # The pages read the recorded figures. They do NOT run the simulator, so
    # `just regen` stays offline and reproducible; `just sim` is what produces
    # new figures.
    @python3 tools/generate_sim_pages.py

# Check documents against the house writing style in docs/kb/DEVELOPING.md.
style *PATHS:
    @python3 tools/check_style.py {{PATHS}}

# Validate internal links and their anchors in the Markdown source.
links:
    @python3 tools/check_links.py

# Resolve every Wowhead id we reference and confirm the name we claim for it.
# Network-bound and slow; not part of `just check`.
links-external:
    @python3 tools/check_external_links.py

# Report links in the built HTML whose target file is missing.
# Check that the spec filter still hides what it says it hides. Needs node.
filter: build
    @node tools/check_spec_filter.js

links-html: build
    #!/usr/bin/env bash
    set -euo pipefail
    bad=0
    while IFS= read -r page; do
        dir="$(dirname "$page")"
        grep -o 'href="[^"#][^":]*"' "$page" 2>/dev/null | sed 's/href="//;s/"$//' | while IFS= read -r href; do
            [[ "$href" =~ ^(https?:|mailto:|#) ]] && continue
            target="${href%%#*}"
            [[ -z "$target" ]] && continue
            [[ -e "$dir/$target" ]] || echo "  $page -> $target"
        done
    done < <(find "{{out}}" -name '*.html') | sort -u | tee /tmp/tbc-badlinks.txt
    if [[ -s /tmp/tbc-badlinks.txt ]]; then echo "broken internal links found"; else echo "all internal links resolve"; fi

# ---------------------------------------------------------------- misc

_clean-site:
    @rm -rf "{{out}}"

# Remove all build output.
clean: _clean-site
    @echo "cleaned"

# Show tool versions this repo depends on.
versions:
    @printf "pandoc     %s\n" "$(pandoc --version | head -1 | cut -d' ' -f2)"
    @printf "just       %s\n" "$(just --version | cut -d' ' -f2)"
    @printf "watchexec  %s\n" "$(watchexec --version | cut -d' ' -f2)"
    @printf "python     %s\n" "$(python3 --version | cut -d' ' -f2)"
