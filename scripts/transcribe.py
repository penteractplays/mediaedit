#!/usr/bin/env python3
"""Transcribe a video/audio file to a timestamped transcript.

Backends (auto-detected, or pick with --backend):
  parakeet  - parakeet-mlx, Apple Silicon (pip install parakeet-mlx)
  whisper   - faster-whisper, works everywhere (pip install faster-whisper)

Output (in --out dir, default projects/<slug>/transcript/):
  transcript.json  - segments + words with start/end in seconds
  transcript.srt   - subtitles
  transcript.txt   - plain text with [mm:ss] markers per segment

Usage:
  python3 scripts/transcribe.py projects/demo/raw/video.mp4 --language sv
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import tempfile
from pathlib import Path

from common import die, fmt_ts, require_tool, run, save_json


def extract_audio(src: Path) -> Path:
    require_tool("ffmpeg")
    tmp = Path(tempfile.mkdtemp(prefix="mediaedit_")) / "audio.wav"
    res = run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", str(tmp)])
    if res.returncode != 0:
        die(f"ffmpeg kunde inte extrahera ljud: {res.stderr.strip()}")
    return tmp


def has(mod: str) -> bool:
    return importlib.util.find_spec(mod) is not None


def pick_backend(requested: str) -> str:
    if requested != "auto":
        return requested
    if sys.platform == "darwin" and has("parakeet_mlx"):
        return "parakeet"
    if has("faster_whisper"):
        return "whisper"
    die("Ingen transkriberingsmotor hittades. Kör: pip install faster-whisper  (eller parakeet-mlx på Mac).")
    return ""


def run_whisper(audio: Path, language: str | None, model: str) -> list[dict]:
    from faster_whisper import WhisperModel  # type: ignore

    m = WhisperModel(model, device="auto", compute_type="auto")
    segs, _ = m.transcribe(str(audio), language=language, word_timestamps=True, vad_filter=True)
    out = []
    for s in segs:
        out.append({
            "start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip(),
            "words": [{"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)}
                      for w in (s.words or [])],
        })
    return out


def run_parakeet(audio: Path, model: str) -> list[dict]:
    from parakeet_mlx import from_pretrained  # type: ignore

    m = from_pretrained(model if model != "default" else "mlx-community/parakeet-tdt-0.6b-v2")
    result = m.transcribe(str(audio))
    out = []
    for s in result.sentences:
        out.append({
            "start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip(),
            "words": [{"word": t.text.strip(), "start": round(t.start, 3), "end": round(t.end, 3)}
                      for t in s.tokens],
        })
    return out


def write_outputs(segments: list[dict], out_dir: Path, source: Path, backend: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    save_json(out_dir / "transcript.json", {"source": str(source), "backend": backend, "segments": segments})
    with open(out_dir / "transcript.srt", "w", encoding="utf-8") as f:
        for i, s in enumerate(segments, 1):
            f.write(f"{i}\n{fmt_ts(s['start'])} --> {fmt_ts(s['end'])}\n{s['text']}\n\n")
    with open(out_dir / "transcript.txt", "w", encoding="utf-8") as f:
        for s in segments:
            m, sec = divmod(int(s["start"]), 60)
            f.write(f"[{m:02d}:{sec:02d}] {s['text']}\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", type=Path)
    ap.add_argument("--out", type=Path, help="utmapp (default: <projekt>/transcript)")
    ap.add_argument("--backend", choices=["auto", "parakeet", "whisper"], default="auto")
    ap.add_argument("--language", default=None, help="t.ex. sv, en (whisper; auto om utelämnad)")
    ap.add_argument("--model", default="default", help="whisper: tiny/base/small/medium/large-v3 (default: small)")
    a = ap.parse_args()

    if not a.file.exists():
        die(f"filen finns inte: {a.file}")
    out_dir = a.out or (a.file.parent.parent / "transcript")
    backend = pick_backend(a.backend)
    audio = extract_audio(a.file)
    print(f"transkriberar med {backend} ...", file=sys.stderr)
    if backend == "whisper":
        segments = run_whisper(audio, a.language, "small" if a.model == "default" else a.model)
    else:
        segments = run_parakeet(audio, a.model)
    write_outputs(segments, out_dir, a.file, backend)
    total = sum(len(s["words"]) for s in segments)
    print(f"klart: {len(segments)} segment, {total} ord -> {out_dir}/transcript.{{json,srt,txt}}")


if __name__ == "__main__":
    main()
