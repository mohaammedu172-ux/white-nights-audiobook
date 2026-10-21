# Experiment: The Queen of Spades (Pushkin)

Text: H. Twitchell translation, Project Gutenberg #23058 (public domain).
Purpose: a second book run by another agent, to compare results with White Nights.
The White Nights settings (`/config.json`) are **not** changed by this experiment.

## Voice map (picked by ear by Mohammed, 2026-10-21, from `samples/`)

| ID | Character | Voice | Style row | Speed |
|---|---|---|---|---|
| 1 | Narrator (third person) | `am_michael` | 250 | 0.95 |
| 2 | Herman | `am_fenrir` | 250 | 1.0 |
| 3 | Tomsky | `am_puck` | 60 | 1.0 |
| 4 | Lisaveta | `af_bella` | 250 | 1.0 |
| 5 | Countess (and her ghost) | `af_nicole` | 250 | 0.88 |
| 6 | Tchekalinsky | `bm_lewis` | 250 | 0.95 |
| 7 | Naroumov | `am_santa` | 250 | 1.0 |
| 8 | Sourine | `am_onyx` | 250 | 1.0 |
| 9 | Saint-Germain (inside Tomsky's story) | `bm_fable` | 250 | 0.92 |

Claude's first suggestions were the same except Countess `bf_emma`, Tchekalinsky `bm_george`, Naroumov `am_echo`, Sourine `bm_lewis`.

Style rows other than Puck's 60 are the default and haven't been tuned by ear. If a voice sounds too deep or too fast,
try rows 60–150 before changing the voice (see `RECIPE.md`).

## Audition
```bash
python tools/audition_voices.py books/queen_of_spades/config.json books/queen_of_spades/audition_lines.json out/qos_voices.mp3
```
Lines 1–6 are from the book. Lines 7–10 (Tchekalinsky, Naroumov, Sourine, Saint-Germain) are **test lines, not book text**.

## Running the book with this config
`wn/text2.py` is written for White Nights (its chapter headings and speech-tag names). A Queen of Spades script builder
must write `script/queen_of_spades_lines.json` in the same format (`id, p, speaker, kind, text, pause_before`), with
speaker IDs from the table above and narration as speaker 1. Then:
```bash
WN_CONFIG=books/queen_of_spades/config.json WN_OUT=$PWD/out python -m wn.run chapter
```

## All voice options
`samples/` has 121 short MP3s: every English Kokoro voice reading each character's line (13 male voices per male role,
15 female voices per female role), listed in `samples/README.md`. `casting_page.html` is a self-contained listening and
picking page (open it in a browser). Rebuild both with `tools/casting/`.
