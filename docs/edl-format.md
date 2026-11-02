# EDL-format (edit decision list)

En EDL är en JSON-fil i `projects/<slug>/edl/` som beskriver ett klipp. Claude
skriver och ändrar EDL:er, `scripts/render.py` renderar dem. Tider anges i
sekunder (decimaler ok) i **källfilens** tidslinje för `clips`, och i den
**färdiga videons** tidslinje för `sfx`.

```json
{
  "source": "projects/demo/raw/video.mp4",
  "note": "v2: kortade intro, tog bort omtagning vid 4:12",
  "clips": [
    { "start": 0.0,   "end": 12.4 },
    { "start": 15.1,  "end": 48.0, "speed": 1.15 },
    { "start": 52.3,  "end": 120.0 }
  ],
  "music": { "file": "assets/music/lofi.mp3", "gain_db": -18, "duck": true },
  "sfx": [
    { "at": 12.4, "file": "assets/sfx/whoosh.wav", "gain_db": -14 }
  ],
  "subtitles": {
    "file": "projects/demo/transcript/final.srt",
    "style": "FontName=Arial,FontSize=20,Outline=2,MarginV=40"
  }
}
```

| Fält | Krävs | Beskrivning |
|---|---|---|
| `source` | ja | Råfilen. Alla `clips` refererar till den. |
| `clips[]` | ja | Ordnad lista. Varje klipp har `start` < `end`. Valfritt `speed` (1.25 = 25 % snabbare, ljudet pitch-bevaras). |
| `music` | nej | Loopas och klipps till videons längd. `duck: true` sänker musiken när rösten hörs. |
| `sfx[]` | nej | `at` = tid i den färdiga videon. Mixas efter duckningen. |
| `subtitles` | nej | SRT som bränns in. `style` är en libass `force_style`-sträng. Hoppas över i `--preview`. |
| `note` | nej | Fritext, bra för versionshistorik. |

Rendering normaliserar alltid ljudet till -14 LUFS (YouTube) om inte
`--no-normalize` anges. Utfil: `projects/<slug>/out/<edl-namn>.mp4`.

## Tips vid klippning från transkript
- `transcript.json` innehåller ord med `start`/`end`. En klippgräns bör ligga
  i en paus: lägg `end` ~0.1–0.15 s efter sista ordets `end`, och `start`
  ~0.1 s före första ordets `start`.
- Omtagning: om samma mening sägs två gånger, behåll den senare (den är oftast
  bäst) och klipp bort den första inklusive pausen före.
- Undertexter efter klipp: tiderna i `transcript.srt` gäller råfilen. Skapa en
  ny SRT för den klippta tidslinjen genom att dra bort borttagen tid, eller
  transkribera om den färdiga videon.
