#!/usr/bin/env python3
"""Record how far each captured recording reached, as views and likes.

WHY THIS IS NOT IN THE MANIFEST. `data/research/creator-transcripts/manifest.yaml`
is a CAPTURE, and nothing under `data/research/` is edited after capture. A view
count is not a property of the recording as captured; it is an outside fact that
changes every day. It therefore lives here, with the date it was observed, and a
reader can see how stale it is.

WHAT REACH IS FOR, AND WHAT IT IS NOT FOR. It orders which remarks an item page
shows when there are more than it can display. It is a proxy for how widely a
view circulated in the community, which is worth knowing when a council is
weighing what "people are saying".

IT IS NOT A MEASURE OF WHETHER A CLAIM IS RIGHT. A popular channel repeating a
mistake reaches more people than a careful one correcting it, and a long-form
item-by-item breakdown is watched by fewer people than a ten-minute tier list
while containing far more of the reasoning a council needs. Reach never
suppresses a dissenting view: the selection in `tools/extract_commentary.py`
seeds one remark from every stance BEFORE it fills the remaining slots by reach,
so a minority view cannot be outvoted off the page.

Usage:
    python3 tools/fetch_reach.py --out data/facts/creator-reach.yaml
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

MANIFEST = Path("data/research/creator-transcripts/manifest.yaml")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("data/facts/creator-reach.yaml"))
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    args = ap.parse_args()

    recordings = yaml.safe_load(args.manifest.read_text())["transcripts"]
    rows, failed = [], []
    for entry in recordings:
        try:
            proc = subprocess.run(
                ["yt-dlp", "--no-update", "--skip-download", "--print",
                 "%(view_count)s\t%(like_count)s\t%(channel_follower_count)s",
                 entry["url"]],
                capture_output=True, text=True, timeout=90)
            parts = proc.stdout.strip().splitlines()[-1].split("\t")
            views, likes, subs = (None if p in ("NA", "None", "") else int(p)
                                  for p in parts)
        except Exception as exc:  # noqa: BLE001 - the reason is what matters
            failed.append(f"{entry['slug']}: {exc}")
            continue
        rows.append({"slug": entry["slug"], "video_id": entry["id"],
                     "channel": entry["channel"], "views": views,
                     "likes": likes, "channel_subscribers": subs})
        print(f"  {entry['slug']}: {views} views", file=sys.stderr)

    rows.sort(key=lambda r: -(r["views"] or 0))
    doc = {
        "meta": {
            "observed": str(date.today()),
            "source": "YouTube, via yt-dlp, one request per recording",
            "recordings": len(rows),
            "total_views": sum(r["views"] or 0 for r in rows),
            "note": ("Reach orders which remarks a crowded item page shows. It "
                     "is not evidence that a claim is correct, and it never "
                     "removes a dissenting view. See the module docstring."),
        },
        "recordings": rows,
    }
    if failed:
        doc["meta"]["not_resolved"] = failed
    args.out.write_text(yaml.safe_dump(doc, sort_keys=False, width=88,
                                       allow_unicode=True))
    print(f"{len(rows)} recording(s) resolved, {len(failed)} failed -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
