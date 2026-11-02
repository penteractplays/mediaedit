#!/usr/bin/env python3
"""Render an EDL (edit decision list) to a video file with ffmpeg.

Usage:
  python3 scripts/render.py projects/demo/edl/rough.json --out projects/demo/out/v1.mp4
  python3 scripts/render.py edl.json --preview        # fast, low quality, 720p
  python3 scripts/render.py edl.json --vertical       # 1080x1920 crop for shorts

EDL format: see docs/edl-format.md.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from common import die, duration_of, load_json, require_tool, run


def build_filter(edl: dict, vertical: bool, preview: bool) -> tuple[list[str], str, float]:
    clips = edl["clips"]
    if not clips:
        die("EDL:en har inga klipp")
    src = Path(edl["source"])
    if not src.exists():
        die(f"källfilen finns inte: {src}")

    inputs = ["-i", str(src)]
    parts = []
    out_len = 0.0
    for i, c in enumerate(clips):
        s, e = float(c["start"]), float(c["end"])
        if e <= s:
            die(f"klipp {i}: end ({e}) måste vara > start ({s})")
        speed = float(c.get("speed", 1.0))
        out_len += (e - s) / speed
        v = f"[0:v]trim=start={s}:end={e},setpts=(PTS-STARTPTS)/{speed}"
        a = f"[0:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS"
        if speed != 1.0:
            a += f",atempo={speed}"
        parts.append(f"{v}[v{i}];{a}[a{i}]")
    concat_in = "".join(f"[v{i}][a{i}]" for i in range(len(clips)))
    chain = ";".join(parts) + f";{concat_in}concat=n={len(clips)}:v=1:a=1[vc][ac]"

    vlabel = "[vc]"
    if vertical:
        chain += ";[vc]crop=ih*9/16:ih,scale=1080:1920[vv]"
        vlabel = "[vv]"
    elif preview:
        chain += ";[vc]scale=-2:720[vv]"
        vlabel = "[vv]"

    alabel = "[ac]"
    idx = 1
    music = edl.get("music")
    if music:
        inputs += ["-stream_loop", "-1", "-i", music["file"]]
        gain = float(music.get("gain_db", -18))
        duck = music.get("duck", True)
        chain += f";[{idx}:a]volume={gain}dB,atrim=0:{out_len},asetpts=PTS-STARTPTS[m0]"
        if duck:
            chain += f";{alabel}asplit[ad][am];[m0][am]sidechaincompress=threshold=0.05:ratio=8:attack=50:release=400[md]"
            chain += ";[ad][md]amix=inputs=2:duration=first:dropout_transition=0[am1]"
        else:
            chain += f";{alabel}[m0]amix=inputs=2:duration=first:dropout_transition=0[am1]"
        alabel = "[am1]"
        idx += 1
    for j, fx in enumerate(edl.get("sfx") or []):
        inputs += ["-i", fx["file"]]
        delay_ms = int(float(fx["at"]) * 1000)
        chain += f";[{idx}:a]volume={float(fx.get('gain_db', -14))}dB,adelay={delay_ms}|{delay_ms}[fx{j}]"
        chain += f";{alabel}[fx{j}]amix=inputs=2:duration=first:dropout_transition=0[as{j}]"
        alabel = f"[as{j}]"
        idx += 1
    chain += f";{alabel}aresample=48000[aout]"

    subs = edl.get("subtitles")
    if subs and not preview:
        style = subs.get("style", "FontName=Arial,FontSize=20,Outline=2,MarginV=40")
        chain += f";{vlabel}subtitles='{subs['file']}':force_style='{style}'[vout]"
    else:
        chain += f";{vlabel}null[vout]"
    return inputs, chain, out_len


def normalize_loudness(src: Path, dst: Path, target_i: float = -14.0, tp: float = -1.5, lra: float = 11.0) -> None:
    """Two-pass EBU R128 loudness normalisation; video is stream-copied."""
    measure = run(["ffmpeg", "-v", "info", "-i", str(src), "-af",
                   f"loudnorm=I={target_i}:TP={tp}:LRA={lra}:print_format=json", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", measure.stderr, re.S)
    if not m:
        die("kunde inte mäta loudness")
    d = json.loads(m.group(0))
    af = (f"loudnorm=I={target_i}:TP={tp}:LRA={lra}:measured_I={d['input_i']}:measured_TP={d['input_tp']}"
          f":measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:offset={d['target_offset']}"
          f":linear=true:print_format=summary,aresample=48000")
    res = run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-c:v", "copy", "-af", af,
               "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-movflags", "+faststart", str(dst)])
    if res.returncode != 0:
        die(f"loudness-normalisering misslyckades:\n{res.stderr}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edl", type=Path)
    ap.add_argument("--out", type=Path, help="utfil (default: <projekt>/out/<edl-namn>.mp4)")
    ap.add_argument("--preview", action="store_true", help="snabb lågkvalitetsrender i 720p")
    ap.add_argument("--vertical", action="store_true", help="9:16 1080x1920 (shorts/reels)")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--no-normalize", action="store_true", help="hoppa över loudness-normalisering (-14 LUFS)")
    a = ap.parse_args()

    require_tool("ffmpeg")
    edl = load_json(a.edl)
    out = a.out or (a.edl.parent.parent / "out" / (a.edl.stem + ("_preview" if a.preview else "") + ".mp4"))
    out.parent.mkdir(parents=True, exist_ok=True)
    inputs, chain, out_len = build_filter(edl, a.vertical, a.preview)

    cmd = ["ffmpeg", "-y", "-v", "error", "-stats", *inputs, "-filter_complex", chain,
           "-map", "[vout]", "-map", "[aout]",
           "-c:v", "libx264", "-preset", "ultrafast" if a.preview else "medium",
           "-crf", str(28 if a.preview else a.crf), "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-movflags", "+faststart"]
    normalize = not (a.no_normalize or a.preview)
    first_out = out.with_name(out.stem + "_unnormalized" + out.suffix) if normalize else out
    print(f"renderar {len(edl['clips'])} klipp (~{out_len:.1f}s) -> {out}")
    res = run(cmd + [str(first_out)], capture=True)
    if res.returncode != 0:
        die(f"ffmpeg misslyckades:\n{res.stderr}")
    if normalize:
        print("normaliserar loudness till -14 LUFS ...")
        normalize_loudness(first_out, out)
        first_out.unlink(missing_ok=True)
    print(f"klart: {out} ({duration_of(out):.1f}s)")


if __name__ == "__main__":
    main()
