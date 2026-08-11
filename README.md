# Hyjal / Black Temple Loot Council Research

Research pack and decision system for TBC Anniversary **Phase 3** loot: Mount Hyjal, Black Temple, Tier 6 tokens, off-pieces, weapons, trinkets, badge substitution, and crafted alternatives.

This is not a personal best-in-slot list. It is written for a council that reviews it as a group and works out, in advance, who has a claim on what, what the raid loses by routing an item one way instead of another, and in what order items should flow across the phase.

**Phase 3 opens 27 August 2026.**

## Read it

The compendium is a static site built from the Markdown in `docs/`.

### Run the dev server

From the repository root:

```bash
just dev
```

Then open **<http://localhost:4000>**.

That one command builds the site, serves it, watches `docs/`, `theme/`, `data/` and `tools/`, and reloads the browser on every save. Leave it running while you work. Stop it with `Ctrl-C`.

The first run pauses for a few seconds while `npx` fetches browser-sync. Later runs start immediately.

### Other ways to view it

| Command | Result |
|---|---|
| `just dev` | Build, serve on :4000, live-reload on change. The normal way. |
| `just serve` | Build and serve on :4000, no watching. |
| `just build` | Write `site/` and stop. |
| `just style` | Check documents against the house writing style. |
| `just bundle docs/index.md` | One self-contained HTML file in `site/bundles/`, for sharing. |

After `just build` you can also open `site/index.html` straight from disk. Every path is relative, so the site works over `file://` with no server at all.

Change the port by putting the assignment **before** the recipe name:

```bash
just port=8080 dev
```

### Where to start reading

[`docs/index.md`](docs/index.md) is the entry point. The governing document is [`docs/framework.md`](docs/framework.md); every analytical decision traces back to a section in it.

## Work on it

Read [`AGENTS.md`](AGENTS.md) first. It carries the rules that must always hold and routes to everything else: [`docs/kb/DEVELOPING.md`](docs/kb/DEVELOPING.md) for the house writing style and the Markdown component vocabulary, and [`docs/kb/DOMAIN.md`](docs/kb/DOMAIN.md) for the TBC and source-data truths that have already caused wrong conclusions.

Run `just` to list every command.

## Toolchain

`pandoc` renders, `just` orchestrates, `watchexec` watches, Python transforms. Pandoc is a native binary with no runtime, so nothing here depends on a language version manager.

```bash
brew install pandoc just watchexec
just versions
```

## Limitations

The project is gathering facts. No priority has been assigned to any item, no
ruling has been written, and no simulation has been run, so nothing here is
binding policy yet. The worked example in
[`docs/conventions.md`](docs/conventions.md) carries invented upgrade figures
and says so.

## Credit

Item scoring builds on the **TBC Phase 3 PVE EPV BIS LIST** by **Fazers**. See [`data/research/epv-workbook/PROVENANCE.md`](data/research/epv-workbook/PROVENANCE.md) for the source, what it provides, and what it deliberately leaves to us.

## Notes

- Documentation-first. Scripts regenerate data; they do not distribute loot.
- Transcripts are research artifacts and may contain caption errors, so policy documents synthesise and cross-check rather than quoting captions as exact.
- Review every document against your actual roster before treating it as binding policy.
- Add a `LICENSE` before publishing anything outside the guild.
