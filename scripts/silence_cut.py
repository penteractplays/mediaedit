#!/usr/bin/env python3
"""Detect silence and produce a first-pass EDL that keeps only the spoken parts.

Usage:
  python3 scripts/silence_cut.py projects/demo/raw/video.mp4 \
      --min-silence 0.6 --threshold -35 --pad 0.15 --out projects/demo/edl/rough.json

The EDL format is documented in docs/edl-format.md. Open the result, adjust
(merge, drop, trim clips) and render with scripts/render.py.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from common import duration_of, require_tool, run, save_json

SIL_START = re.compile(r"silence_start: ([\d.]+)")
SIL_END = re.compile(r"silence_end: ([\d.]+)")


def detect_silences(src: Path, threshold_db: float, min_silence: float) -> list[tuple[float, float]]:
    require_tool("ffmpeg")
    res = run(["ffmpeg", "-v", "info", "-i", str(src), "-af",
               f"silencedetect=noise={threshold_db}dB:d={min_silence}", "-f", "null", "-"])
    starts = [float(m.group(1)) for m in SIL_START.finditer(res.stderr)]
    ends = [float(m.group(1)) for m in SIL_END.finditer(res.stderr)]
    sil = list(zip(starts, ends))
    if len(starts) > len(ends):  # silence runs to end of file
        sil.append((starts[-1], duration_of(src)))
    return sil


def silences_to_clips(silences, total: float, pad: float, min_clip: float) -> list[dict]:
    clips, cursor = [], 0.0
    for s_start, s_end in silences:
        end = min(s_start + pad, total)
        if end - cursor >= min_clip:
            clips.append({"start": round(cursor, 3), "end": round(end, 3)})
        cursor = max(s_end - pad, cursor)
    if total - cursor >= min_clip:
        clips.append({"start": round(cursor, 3), "end": round(total, 3)})
    # merge clips that overlap because of padding
    merged: list[dict] = []
    for c in clips:
        if merged and c["start"] <= merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], c["end"])
        else:
            merged.append(dict(c))
    return merged


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", type=Path)
    ap.add_argument("--out", type=Path, help="EDL-fil att skriva (default: <projekt>/edl/rough.json)")
    ap.add_argument("--min-silence", type=float, default=0.6, help="sekunder tystnad som räknas som paus")
    ap.add_argument("--threshold", type=float, default=-35.0, help="dB-nivå under vilken det räknas som tyst")
    ap.add_argument("--pad", type=float, default=0.15, help="andrum som behålls på varje sida av tal")
    ap.add_argument("--min-clip", type=float, default=0.3, help="kasta klipp kortare än detta")
    a = ap.parse_args()

    total = duration_of(a.file)
    silences = detect_silences(a.file, a.threshold, a.min_silence)
    clips = silences_to_clips(silences, total, a.pad, a.min_clip)
    kept = sum(c["end"] - c["start"] for c in clips)
    out = a.out or (a.file.parent.parent / "edl" / "rough.json")
    edl = {
        "source": str(a.file),
        "note": f"auto silence cut: {len(silences)} pauser hittade, {total - kept:.1f}s borttaget",
        "clips": clips,
        "music": None,
        "sfx": [],
        "subtitles": None,
    }
    save_json(out, edl)
    print(f"{len(silences)} pauser, {len(clips)} klipp kvar, {kept:.1f}s av {total:.1f}s ({kept / total:.0%}) -> {out}")


if __name__ == "__main__":
    main()
