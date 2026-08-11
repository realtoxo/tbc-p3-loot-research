#!/usr/bin/env python3
"""Capture the full transcript of a creator video, for the record.

WHY THIS EXISTS. The Phase 2 repository holds twenty-nine transcripts and NOT
ONE video id, URL or timestamp beside them, so a claim taken from one of those
files cannot be pointed back at the moment a creator said it. The guild lead
asked on 10 August 2026 for commentary carrying timestamped references, which
that library cannot supply. This tool captures the id, the URL and the caption
timing at the same moment as the words, so the citation exists before anyone
needs it.

WHAT IT WRITES, per video, under data/research/creator-transcripts/:
    <slug>.txt   the flat transcript, one paragraph, matching Phase 2
    <slug>.tsv   start, duration, text per caption line, matching Phase 2
    manifest.yaml  one entry per capture: id, url, channel, title, date,
                   duration, track, and the slug the files carry

CAPTION TIMING IS THE POINT, so the tsv start column is what a citation quotes.
YouTube emits a URL fragment of `&t=<seconds>s`, and the manifest records the
watch URL that fragment attaches to.

A MANUAL CAPTION TRACK BEATS AN AUTOMATIC ONE and the manifest records which
was taken, because an automatic track mishears item names and a reader deciding
whether to trust a quote needs to know which they are reading.

Usage:
    python3 tools/fetch_transcripts.py --search "TBC phase 3 rogue bis"
    python3 tools/fetch_transcripts.py <video-id-or-url> --slug drue-shadow-p3
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

OUT = Path("data/research/creator-transcripts")
MANIFEST = OUT / "manifest.yaml"


def run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip().splitlines()[-1] if proc.stderr
                           else f"exit {proc.returncode}")
    return proc.stdout


def slugify(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def search(query: str, count: int) -> list[dict]:
    """Candidate videos for a query, as id, channel, title and duration."""
    out = run(["yt-dlp", "--no-update", "--flat-playlist", "--print",
               "%(id)s\t%(channel)s\t%(duration)s\t%(title)s",
               f"ytsearch{count}:{query}"])
    rows = []
    for line in out.strip().splitlines():
        parts = line.split("\t")
        if len(parts) != 4:
            continue
        vid, channel, duration, title = parts
        rows.append({"id": vid, "channel": channel, "title": title,
                     "duration": None if duration == "NA" else int(float(duration))})
    return rows


def lines(track: Path) -> list[tuple[float, float, str]]:
    """Caption lines as start seconds, duration seconds and text.

    SKIPS THE ROLLUP. An automatic track repeats the previous line as an
    `aAppend` event carrying a lone newline, so taking every event doubles the
    transcript and puts a blank line at half the timestamps.
    """
    data = json.loads(track.read_text())
    out = []
    for event in data.get("events") or []:
        segs = event.get("segs")
        if not segs or event.get("aAppend"):
            continue
        text = "".join(seg.get("utf8", "") for seg in segs)
        text = " ".join(text.split())
        if not text:
            continue
        out.append((event["tStartMs"] / 1000,
                    event.get("dDurationMs", 0) / 1000, text))
    return out


def capture(target: str, slug: str | None) -> dict:
    url = target if target.startswith("http") else (
        f"https://www.youtube.com/watch?v={target}")

    meta = json.loads(run(["yt-dlp", "--no-update", "--skip-download",
                           "--dump-json", url]))
    slug = slug or f"{slugify(meta.get('channel') or 'unknown')}-{slugify(meta['title'])[:40]}"

    with tempfile.TemporaryDirectory() as tmp:
        stem = Path(tmp) / "sub"
        # NAME THE TRACKS, DO NOT GLOB THEM. `en.*` also matches the machine
        # TRANSLATED tracks YouTube offers, such as en-zh-Hans, which are a
        # translation of a translation and read nothing like what was said.
        # Fetching them also multiplies the requests, and the first run of this
        # tool was rate limited at video twelve for exactly that reason.
        run(["yt-dlp", "--no-update", "--skip-download", "--write-subs",
             "--write-auto-subs", "--sub-langs", "en,en-orig,en-US,en-GB",
             "--sub-format", "json3", "--sleep-requests", "1",
             "--retries", "5", "-o", str(stem), url])
        tracks = sorted(Path(tmp).glob("sub.*.json3"))
        if not tracks:
            raise RuntimeError("no English caption track")
        # A manual track is written under the plain language tag; an automatic
        # one carries -orig. Where both exist they are the same file, so the
        # automatic marker is what the subtitles listing says, recorded below.
        manual = set((meta.get("subtitles") or {}))
        track = next((t for t in tracks if t.suffixes[-2].lstrip(".") in manual),
                     tracks[0])
        rows = lines(track)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{slug}.tsv").write_text(
        "".join(f"{s:.2f}\t{d:.2f}\t{t}\n" for s, d, t in rows))
    (OUT / f"{slug}.txt").write_text(" ".join(t for _, _, t in rows) + "\n")

    return {"slug": slug, "id": meta["id"], "url": url,
            "channel": meta.get("channel"), "title": meta["title"],
            "upload_date": meta.get("upload_date"),
            "duration_seconds": meta.get("duration"),
            "caption_track": "manual" if track.suffixes[-2].lstrip(".") in manual
                             else "automatic",
            "caption_lines": len(rows)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("targets", nargs="*", help="video ids or URLs")
    ap.add_argument("--slug", help="name the files, for a single target")
    ap.add_argument("--search", help="list candidates instead of capturing")
    ap.add_argument("--count", type=int, default=10)
    args = ap.parse_args()

    if args.search:
        for row in search(args.search, args.count):
            mins = "?" if row["duration"] is None else f"{row['duration'] // 60}m"
            print(f"{row['id']}\t{mins}\t{row['channel']}\t{row['title']}")
        return 0

    if args.slug and len(args.targets) != 1:
        print("--slug names one file, so pass one target", file=sys.stderr)
        return 2

    entries = yaml.safe_load(MANIFEST.read_text()) if MANIFEST.is_file() else {}
    entries = entries or {}
    captured = entries.setdefault("transcripts", [])
    known = {e["id"] for e in captured}

    failed = 0
    for target in args.targets:
        try:
            entry = capture(target, args.slug)
        except Exception as exc:  # noqa: BLE001 - the reason is what matters
            print(f"FAILED {target}: {exc}", file=sys.stderr)
            failed += 1
            continue
        if entry["id"] in known:
            captured[:] = [e for e in captured if e["id"] != entry["id"]]
        captured.append(entry)
        print(f"{entry['slug']}: {entry['caption_lines']} lines, "
              f"{entry['caption_track']} captions, {entry['channel']}")

    captured.sort(key=lambda e: e["slug"])
    entries["captured"] = "2026-08-10"
    entries["how"] = "tools/fetch_transcripts.py, yt-dlp json3 caption tracks"
    OUT.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(yaml.safe_dump(entries, sort_keys=False, width=88))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
