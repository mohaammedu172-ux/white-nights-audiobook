# The Queen of Spades (Pushkin)

H. Twitchell translation, Project Gutenberg #23058 (public domain). A dramatized audiobook made with the same method as White Nights.

**Each book follows this layout. Copy this structure for any new book.**

## Build and run
```bash
python books/queen_of_spades/text.py                       # or: python -m books.queen_of_spades.text
WN_CONFIG=books/queen_of_spades/config.json WN_OUT=$PWD/out python -m wn.run chapter
```
`text.py` must run first on every fresh checkout. It writes the script here and a copy at `<repo>/script/queen_of_spades_lines.json`,
which is where `wn/run.py` reads it. That copy is git-ignored. For a short test, point `WN_CONFIG` at a copy of `config.json`
with `"paragraphs": [a, b]`.

## Folders

### `config.json`
Voices, style rows, speeds and mix settings, picked by Mohammed by ear.

| Role | Voice | Style row | Speed |
|---|---|---|---|
| 1 Narrator | am_michael | 250 | 0.95 |
| 2 Herman | am_fenrir | 250 | 1.0 |
| 3 Tomsky | am_puck | 60 | 0.92 |
| 4 Lisaveta | af_bella | 250 | 1.0 |
| 5 Countess (and ghost) | af_nicole | 250 | 0.92 |
| 6 Tchekalinsky | bm_lewis | 250 | 0.95 |
| 7 Naroumov | am_santa | 250 | 1.0 |
| 8 Sourine | am_onyx | 250 | 1.0 |
| 9 Saint-Germain | bm_fable | 250 | 0.92 |

### `source/`
`gutenberg_23058.txt` is the raw book text, so the build needs no network. `text.py` reads it, or downloads it here from
`https://www.gutenberg.org/cache/epub/23058/pg23058.txt` if it is missing.

### `script/`: the source of truth
- `queen_of_spades_fixes.json`: manual corrections (`roles`: line id → role; `replace`: line id → text). Edit this, never the generated files.
- `queen_of_spades_lines.json`: generated. One entry per spoken line: `id` (string), `speaker` (role number as a string),
  `p`, `kind` (`narr`/`say`), `pause_before` (s), `interrupts`, `text`, `guessed`, `role`, `speaker_name`.
- `queen_of_spades_script.md`: generated human review view, with the field notes in a footer.

Pauses: 0.6 s for the same speaker continuing, 0.75 s for a reply, 1.0 s for a new paragraph by the same speaker, 1.4 s before lines 82, 84 and 85.

### `audio/`
Only sounds Mohammed downloaded and approved. `ambience/` holds beds, `sfx/` holds effects, `music/` is intentionally empty.
`audio/README.md` lists which scene each sound is for. Credits and licences are in `audio/ambience/CREDITS.md`.

### `mixing/`
Placeholder for the mix stage. No code until Mohammed asks.

### `video/`
Placeholder for the YouTube video. No code until Mohammed asks.

### `samples/`
Voice auditioning: 121 MP3s (every English Kokoro voice per role), `README.md` (picks marked), `casting_page.html`
(listen and pick in a browser), and `audition_lines.json` (the lines used).

### `tools/`
Setup helpers, not part of the build. Only rerun them if voices change.
- `audition_voices.py`: renders the current cast reading `samples/audition_lines.json`.
- `casting/`: `make_samples.py` (all voices × roles) and `make_page.py` + `template.html` (the casting page).

### `text.py`
The script builder for this book (v4).

## Current status
- Script: 168 lines, 0 guessed, fixes applied ✓
- Voices: picked by Mohammed, encoded in config.json ✓
- Audio generation: works via `WN_CONFIG=books/queen_of_spades/config.json python -m wn.run chapter` ✓
- Mix stage: not started
- Video stage: not started

## Known issues
- Several sound assets need licence verification (see `audio/ambience/CREDITS.md`).
- `sfx/sfx_door_open.wav` needs a listen check before use.
- `sfx/sfx_men_murmur.wav` is a 1930s optical transfer; verify the noise level before use.
- `sfx/sfx_pistol_cock.wav` is a modern semi-auto slide; a period-appropriate alternative is pending.
- `wn/run.py` names the output `white_nights_queen_of_spades.mp3` (its file-name prefix is fixed). Rename after generating if needed.
