"""Shared helpers for the mediaedit scripts."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        die(f"'{name}' hittades inte i PATH. Installera ffmpeg (brew install ffmpeg / apt install ffmpeg).")
    return path


def run(cmd: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=False, capture_output=capture, text=True)


def ffprobe_json(path: Path) -> dict:
    require_tool("ffprobe")
    res = run([
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ])
    if res.returncode != 0:
        die(f"ffprobe misslyckades: {res.stderr.strip()}")
    return json.loads(res.stdout)


def duration_of(path: Path) -> float:
    info = ffprobe_json(path)
    return float(info["format"]["duration"])


def fmt_ts(seconds: float) -> str:
    """Seconds -> HH:MM:SS,mmm (SRT style)."""
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
