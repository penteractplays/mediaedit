#!/usr/bin/env python3
"""Print a compact technical summary of a media file.

Usage: python3 scripts/probe.py projects/<slug>/raw/video.mp4 [--json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ffprobe_json


def summarize(path: Path) -> dict:
    info = ffprobe_json(path)
    out = {"file": str(path), "duration_s": round(float(info["format"]["duration"]), 3),
           "size_mb": round(int(info["format"]["size"]) / 1_048_576, 1), "video": None, "audio": []}
    for s in info["streams"]:
        if s["codec_type"] == "video" and out["video"] is None:
            num, den = s.get("r_frame_rate", "0/1").split("/")
            out["video"] = {"codec": s["codec_name"], "width": s["width"], "height": s["height"],
                            "fps": round(int(num) / max(int(den), 1), 3)}
        elif s["codec_type"] == "audio":
            out["audio"].append({"codec": s["codec_name"], "sample_rate": int(s.get("sample_rate", 0)),
                                 "channels": s.get("channels")})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", type=Path)
    ap.add_argument("--json", action="store_true", help="skriv ut som JSON")
    a = ap.parse_args()
    s = summarize(a.file)
    if a.json:
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return
    v = s["video"] or {}
    print(f"{s['file']}: {s['duration_s']} s, {s['size_mb']} MB")
    if v:
        print(f"  video: {v['codec']} {v['width']}x{v['height']} @ {v['fps']} fps")
    for a_ in s["audio"]:
        print(f"  audio: {a_['codec']} {a_['sample_rate']} Hz, {a_['channels']} ch")


if __name__ == "__main__":
    main()
