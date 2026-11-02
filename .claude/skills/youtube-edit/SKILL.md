---
name: youtube-edit
description: Klipp en YouTube-video (lång eller short) från råmaterial i projects/<slug>/ med transkript, EDL, ffmpeg-render och QC. Använd när användaren vill klippa, korta, transkribera, göra shorts av eller ge feedback på en video.
---

# /youtube-edit – klippa en video med Claude Code

Du är kanalens redigerare. Arbetet är filbaserat: transkript in, EDL ut,
render med skript. Du gissar aldrig tider, du läser dem i transkriptet.

## 0. Läs först
1. `config/channel-style.md` – kanalens stil och tidigare lärdomar.
2. `docs/edl-format.md` – hur en EDL ser ut.
3. Projektmappen `projects/<slug>/` (skapa om den saknas: `raw/ transcript/ edl/ out/`).

Om användaren inte angett vilken fil som ska klippas: lista `projects/*/raw/`
och fråga.

## 1. Analysera råmaterialet
```bash
python3 scripts/probe.py projects/<slug>/raw/<fil>
python3 scripts/transcribe.py projects/<slug>/raw/<fil> --language sv
```
Hoppa över transkribering om `transcript/transcript.json` redan finns och är
nyare än råfilen. Läs sedan `transcript/transcript.txt` i sin helhet och gör
en kort innehållsöversikt: delar, omtagningar, felsägningar, långa pauser,
tangentiella partier.

## 2. Grovklipp
```bash
python3 scripts/silence_cut.py projects/<slug>/raw/<fil>
```
Det ger `edl/rough.json`. Parametrarna (`--min-silence`, `--pad`) tas från
stilprofilen.

## 3. Finklipp (här sitter värdet)
Skapa `edl/v1.json` utifrån `rough.json` och transkriptet:
- Ta bort omtagningar (behåll den sista versionen), felsägningar och "vänta,
  jag tar om" – hitta dem via ordtiderna i `transcript.json`.
- Ta bort partier som inte för innehållet framåt, i linje med önskad slutlängd.
- Klipp i pauser, inte mitt i ord. Lägg 0.1–0.15 s andrum.
- Slå ihop klipp som bara är separerade av en kort paus om stilen säger
  "undvik jump cuts".
- Lägg musik/sfx/undertexter om stilprofilen säger det. Bundlade ljud saknas:
  använd filer användaren pekar ut (t.ex. `assets/`).
- Skriv i `note` vad som ändrats mot förra versionen.

Rendera en snabb förhandsvisning och sedan skarp version:
```bash
python3 scripts/render.py projects/<slug>/edl/v1.json --preview
python3 scripts/render.py projects/<slug>/edl/v1.json
python3 scripts/qc.py projects/<slug>/out/v1.mp4 --expect-min <s> --expect-max <s>
```
QC måste vara OK innan du rapporterar klart.

## 4. Rapportera
Ge användaren:
- utfilens sökväg och längd (före/efter),
- en punktlista över vad som klipptes bort och varför, med tidsstämplar i den
  **färdiga** videon,
- sådant du var osäker på och lät vara kvar.

## 5. Feedbackloop
När användaren ger feedback ("3:12 är för hackigt", "ta bort delen om X",
"kortare intro"):
1. Översätt tiden i utvideon till källtid via EDL:en (summera klipplängderna).
2. Skapa nästa version `edl/v2.json` (ändra aldrig en redan renderad EDL).
3. Rendera, QC, rapportera.

Om användaren säger **"spara"**, **"kom ihåg"**, **"lär dig"** eller
**"gör alltid så här"**: skriv en rad under "Lärdomar från feedback" i
`config/channel-style.md` med datum, och uppdatera relevant inställning
högre upp i filen. Gör inte det på eget initiativ.

## Shorts / reels
- Hitta 30–59 s som fungerar fristående: en poäng, en punchline, början mitt i
  handlingen.
- Egen EDL (`edl/short-<ämne>.json`), rendera med `--vertical`.
- Undertexter rekommenderas starkt: större typsnitt
  (`FontSize=28,MarginV=120`).

## Regler
- Rör aldrig `raw/`.
- Inga ffmpeg-kommandon för hand mot råfilen; allt via EDL + `render.py`.
- Lita på transkriptets tider, inte på uppskattningar.
- Svenska i all kommunikation med användaren.
