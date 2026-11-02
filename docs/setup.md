# Setup-anteckningar

## Transkribering
| Motor | Plattform | Installation | Kommentar |
|---|---|---|---|
| parakeet-mlx | Mac M1+ | `pip install parakeet-mlx` | Snabbast lokalt, bra ordtider. Modell laddas ner första gången (~1 GB). |
| faster-whisper | alla | `pip install faster-whisper` | `--model small` default. `large-v3` ger bäst svenska men är långsam på CPU. |

`scripts/transcribe.py` väljer automatiskt: parakeet på Mac om installerad,
annars whisper. Tvinga med `--backend`.

## Kostnad
Allt körs lokalt utom Claude. En 20-minutersvideo med 2–3 feedbackrundor
hamnar typiskt på några dollar i Claude-användning.

## Felsökning
- `ffmpeg hittades inte`: installera och starta om terminalen.
- Transkriptet tar lång tid på CPU: använd `--model base` eller kör på Mac med parakeet.
- QC klagar på loudness: kontrollera att du inte renderat med `--no-normalize`.
- Undertexter syns inte: `--preview` hoppar över dem, rendera skarpt.
