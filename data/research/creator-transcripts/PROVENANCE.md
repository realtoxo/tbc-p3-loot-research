# Creator Transcripts

Raw capture. Do not edit these files. A citation points at these bytes, and a
correction made here silently changes what a creator is recorded as saying.

## What this is

52 full transcripts of Phase 3 creator videos, 20 hours 52 minutes of speech
across 33 channels and 34,715 caption lines. Captured **10 August 2026** by
`tools/fetch_transcripts.py`.

Each recording is stored twice:

| File | Holds |
|---|---|
| `<slug>.txt` | The flat transcript, one paragraph, for reading and searching |
| `<slug>.tsv` | Start seconds, duration seconds and text, one row per caption line |
| `manifest.yaml` | Per recording: video id, URL, channel, title, upload date, duration, which caption track was taken, and the line count |

The `.tsv` start column is what a timestamped citation quotes. YouTube takes a
`&t=<seconds>s` fragment on the watch URL the manifest records, so a claim found
at row `681.44` in `zatar-black-temple-item-priority.tsv` cites
`https://www.youtube.com/watch?v=6SWlWDYTkvU&t=681s`.

## Why the manifest exists

The Phase 2 repository holds 29 transcripts at
`sources/class-video-transcripts` and records **no video id, no URL and no
capture date** beside any of them. The creator is recoverable from the file
name and nothing else is. A claim taken from that library cannot be pointed
back at the moment it was said, which is what the guild lead asked for on
10 August 2026. This capture records the id, the URL and the caption timing at
the same moment as the words, so the citation exists before anyone needs it.

## Read this before quoting one

**MOST OF THIS IS ORIGINAL TBC CLASSIC, NOT ANNIVERSARY.** By upload date, 19
recordings are from 2021 and 23 from 2022, against 10 from 2026. Phase 3 is the
same raid content in both, so an item claim generally carries across, but the
surrounding rules do not. Arena Season 3 opens five days after Phase 3 on the
Anniversary schedule and did not on the original one, several gems and enchants
are gated differently, and Bloodlust is raid-wide on the Anniversary client and
party-scoped in 2.4.3. A 2021 recording states the original behaviour
confidently and correctly for its own client. Check the upload date in
`manifest.yaml` before treating a claim about anything other than an item's
stat line as current.

**THE CAPTIONS ARE MACHINE TRANSCRIBED.** 49 of 52 tracks are automatic and 3
are manual; `manifest.yaml` records which, per recording. Automatic tracks
mishear item names, drop apostrophes inconsistently, and render jargon
phonetically. Zatar's Black Temple breakdown contains `skull of gul'dan pryo`,
where the last word is "prio", meaning priority, and reads as a misspelled item
name until the surrounding lines are read. A quotation taken from an automatic track is
evidence of what was said only after it is read in context, and the paraphrase
that reaches `data/facts/field-commentary.yaml` is the thing that gets checked,
not the caption text.

**MATCHING ON A NAME IS NOT RELIABLE.** A substring search for an item name
over-matches short names, because `Devastation` appears inside `Band of
Devastation` and `Cuffs of Devastation` and also as an ordinary English word.
It under-matches punctuated names, because `Merciless Gladiator's Maul` is
transcribed both with and without the apostrophe. This is a defect in any
extraction built on plain substring search, and it belongs to the item-by-item
pass rather than to this capture.

## What is here and what is not

The item-by-item spine is five long-form priority breakdowns, about ten hours
between them: Zatar on Black Temple and on Mount Hyjal, Sarthe on both, Joardee,
and Knot on Mount Hyjal. These walk the drop tables item by item and are the
densest source for per-item commentary.

Around them sit tier-wide guides, loot priority lists and per-spec gearing
guides. Fourteen of the Phase 2 creators reappear here, which is why they were
searched for first: Blayst, Classic Gho, Crix, Darkest, Drue, Fearstreet,
Griftin, Knot, Neuro, Sarthe, Simonize, World of Warcraft Curios, Wundy and ZGT.
Zatar is not among them and is new to this phase, which matters because Zatar
supplies the two densest recordings in the capture.

The count above was checked by hand after a substring match got it wrong, which
is the same defect this file warns about two sections up: matching Phase 2 file
name prefixes against Phase 3 channel names credits Zatar as returning, because
the prefix `classic` sits inside `Zatar (Classic Wow Builds)`.

**Holy Paladin has no Phase 3 recording in this capture.** Searching returns
only Tier 5 and Phase 6 material for that spec. The absence is recorded rather
than filled with an off-phase guide.

## How to re-capture

```bash
python3 tools/fetch_transcripts.py --search "TBC phase 3 rogue bis"   # list candidates
python3 tools/fetch_transcripts.py <video-id> --slug creator-topic     # capture one
```

Name the caption tracks rather than globbing them. `--sub-langs "en.*"` also
matches YouTube's machine-translated tracks, such as `en-zh-Hans`, which are a
translation of a translation; fetching them multiplies the requests, and the
first run of this tool was rate limited at video twelve for exactly that reason.
