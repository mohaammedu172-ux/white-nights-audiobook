# Experiment: The Queen of Spades (Pushkin)

Text: H. Twitchell translation, Project Gutenberg #23058 (public domain).
Purpose: a second book run by another agent, to compare results with White Nights.
The White Nights settings (`/config.json`) are **not** changed by this experiment.

## Voice map (Kokoro built-in voices, same method as White Nights)

| ID | Character | Voice | Style row | Speed | Why |
|---|---|---|---|---|---|
| 1 | **Narrator** | `am_michael` | 250 | 0.95 | The story has a **third-person narrator**, so narration needs its own voice. Calm and warm, and it doesn't compete with Herman |
| 2 | Herman | `am_fenrir` | 250 | 1.0 | Deeper and harder than the narrator: intense, obsessive |
| 3 | Tomsky | `am_puck` | 60 | 1.0 | Light, joking young officer. Approved by ear on White Nights; here at normal speed |
| 4 | Lisaveta | `af_bella` | 250 | 1.0 | Young and emotional; one of Kokoro's best-rated female voices. Different from Nastenka |
| 5 | Countess (and her ghost) | `bf_emma` | 250 | 0.88 | British, dry, older-sounding, slowed. Kokoro has no truly old voices |
| 6 | Tchekalinsky | `bm_george` | 250 | 0.95 | Polished older host and banker |
| 7 | Naroumov | `am_echo` | 250 | 1.0 | Minor card player |
| 8 | Sourine | `bm_lewis` | 250 | 1.0 | One line; just needs to sound different |
| 9 | Saint-Germain | `bm_fable` | 250 | 0.92 | Only inside Tomsky's story (nested quotes): an older foreign aristocrat |

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
