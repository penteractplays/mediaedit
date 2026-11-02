# mediaedit

Filbaserat videoklippsflöde där Claude Code är redigeraren. Se README.md för
installation och `.claude/skills/youtube-edit/SKILL.md` för själva arbetsflödet.

## Regler för agenten
- Skriv aldrig över filer i `projects/<slug>/raw/`. Allt genererat går till
  `transcript/`, `edl/` och `out/` i projektmappen.
- Alla klipp beskrivs först i en EDL (`edl/*.json`) och renderas sedan med
  `scripts/render.py`. Kör inte ffmpeg-kommandon "för hand" mot råmaterialet.
- Läs `config/channel-style.md` innan du föreslår ett klipp. Uppdatera filen
  bara när användaren uttryckligen säger "spara", "lär dig" eller "kom ihåg".
- Kör `scripts/qc.py` på varje färdig render innan du rapporterar klart.
- Svara användaren på svenska.
