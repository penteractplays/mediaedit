# mediaedit

Automatiserad videoklippning med Claude Code, inspirerad av Christian Peverellis
arbetsflöde ("I Fully Automated My Video Editing Using Claude Code").
Claude är redigeraren: den läser ett tidsstämplat transkript, skriver en
klipplista (EDL), renderar med ffmpeg och lär sig din stil via feedback.

```
projects/<slug>/raw/      råmaterial (rörs aldrig)
projects/<slug>/transcript/  transcript.json / .srt / .txt
projects/<slug>/edl/      rough.json, v1.json, v2.json ... (klipplistor)
projects/<slug>/out/      renderade videor
config/channel-style.md   kanalens stilprofil = Claudes minne
.claude/skills/youtube-edit/  skillen Claude följer (/youtube-edit)
scripts/                  probe, transcribe, silence_cut, render, qc
docs/edl-format.md        EDL-formatet
```

## Installation

Krav: Python 3.10+, ffmpeg, Claude Code.

```bash
# macOS
brew install ffmpeg
# Ubuntu/Debian
sudo apt install ffmpeg
```

```bash
git clone https://github.com/penteractplays/mediaedit && cd mediaedit
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt            # faster-whisper (fungerar överallt)
# Mac med Apple Silicon, snabbare och bättre tidsstämplar:
pip install parakeet-mlx
```

Fyll i `config/channel-style.md` så gott du kan. Det är den filen som styr
hur Claude klipper.

## Använda

1. Lägg råfilen i `projects/<slug>/raw/`, t.ex. `projects/avsnitt-12/raw/kamera.mp4`.
2. Starta `claude` i repot och skriv:

   ```
   /youtube-edit klipp projects/avsnitt-12/raw/kamera.mp4 till ca 10 minuter
   ```

3. Claude transkriberar, grovklipper tystnad, finklipper utifrån transkriptet,
   renderar och kör QC. Du får en rapport med vad som togs bort och varför.
4. Ge feedback i klartext ("3:12 är hackigt", "kortare intro"). Claude gör
   `v2`, `v3` ... Säg "spara det" när något ska gälla framöver, då hamnar det i
   stilprofilen.
5. Shorts: `/youtube-edit gör en short av delen om X`.

## Skripten var för sig

```bash
python3 scripts/probe.py projects/demo/raw/video.mp4
python3 scripts/transcribe.py projects/demo/raw/video.mp4 --language sv
python3 scripts/silence_cut.py projects/demo/raw/video.mp4 --min-silence 0.6 --pad 0.15
python3 scripts/render.py projects/demo/edl/v1.json            # skarp, -14 LUFS
python3 scripts/render.py projects/demo/edl/v1.json --preview  # snabb 720p
python3 scripts/render.py projects/demo/edl/short.json --vertical
python3 scripts/qc.py projects/demo/out/v1.mp4 --expect-min 480 --expect-max 720
```

Render stöder klipp med hastighet, loopad bakgrundsmusik med duckning,
ljudeffekter på givna tider och inbrända undertexter. Se `docs/edl-format.md`.

## Vad som inte ingår (än)
- Motion graphics/titlar (HyperFrames eller Remotion kan kopplas på som nästa steg).
- Export till Final Cut/Premiere/DaVinci. EDL:en är enkel JSON, en FCPXML-export
  är rakt fram att lägga till.
- Bundlad musik eller ljudeffekter. Peka på egna filer (t.ex. Epidemic Sound).
