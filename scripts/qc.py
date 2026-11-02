#!/usr/bin/env python3
"""Quality-check a rendered video: duration, resolution, loudness, black frames.

Usage: python3 scripts/qc.py projects/demo/out/v1.mp4 [--expect-min 480 --expect-max 720]
Exit code 1 if any check fails.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from common import ffprobe_json, require_tool, run


def loudness(path: Path) -> dict | None:
    res = run(["ffmpeg", "-v", "info", "-i", str(path), "-af", "loudnorm=print_format=json", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", res.stderr, re.S)
    return json.loads(m.group(0)) if m else None


def black_frames(path: Path) -> list[str]:
    res = run(["ffmpeg", "-v", "info", "-i", str(path), "-vf", "blackdetect=d=0.5:pix_th=0.10", "-f", "null", "-"])
    return re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", res.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", type=Path)
    ap.add_argument("--expect-min", type=float, help="minsta godkända längd i sekunder")
    ap.add_argument("--expect-max", type=float, help="största godkända längd i sekunder")
    ap.add_argument("--target-lufs", type=float, default=-14.0)
    a = ap.parse_args()
    require_tool("ffmpeg")

    info = ffprobe_json(a.file)
    dur = float(info["format"]["duration"])
    vid = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    aud = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    fails: list[str] = []

    print(f"fil: {a.file}")
    print(f"längd: {dur:.1f}s")
    if a.expect_min and dur < a.expect_min:
        fails.append(f"för kort ({dur:.1f}s < {a.expect_min}s)")
    if a.expect_max and dur > a.expect_max:
        fails.append(f"för lång ({dur:.1f}s > {a.expect_max}s)")
    if vid:
        print(f"video: {vid['codec_name']} {vid['width']}x{vid['height']}")
    else:
        fails.append("ingen videoström")
    if not aud:
        fails.append("ingen ljudström")
    else:
        l = loudness(a.file)
        if l:
            i, tp = float(l["input_i"]), float(l["input_tp"])
            print(f"loudness: {i:.1f} LUFS, true peak {tp:.1f} dBTP")
            if abs(i - a.target_lufs) > 2:
                fails.append(f"loudness {i:.1f} LUFS avviker >2 från {a.target_lufs}")
            if tp > -1.0:
                fails.append(f"true peak {tp:.1f} dBTP över -1.0")
    blacks = black_frames(a.file)
    if blacks:
        print(f"svarta partier: {', '.join(f'{s}-{e}s' for s, e in blacks)}")
        fails.append(f"{len(blacks)} svarta partier (>0.5s)")

    if fails:
        print("\nQC MISSLYCKADES:")
        for f in fails:
            print(f"  - {f}")
        raise SystemExit(1)
    print("\nQC OK")


if __name__ == "__main__":
    main()
