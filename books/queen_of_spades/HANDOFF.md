# Handoff: The Queen of Spades, for the agent building the book

Status as of 2026-10-22. Read this first, then `README.md` (this folder), `/RECIPE.md` and `/docs/REPLICATE.md`.

## 1. Rules from the owner (Mohammed)
- **Don't change White Nights:** leave `/config.json`, `/script/`, `/youtube/` and the published book's files alone.
  This book lives in `books/queen_of_spades/` and runs through `WN_CONFIG`.
- **Test small first:** a 10–30 s sample, which the owner judges by ear, before any long run. Never generate the whole book first.
- **Voices are chosen by the owner by ear.** Don't change a voice without asking. Speed and style-row tweaks should be offered as A/B samples.
- **No music in this book.** Ambience and SFX are staged in `audio/` but **not part of any pipeline yet**. Don't wire them in until
  the owner asks for the mix step.
- **Free and open only:** no paid APIs, and no cloning of real people's voices.
- **Speech:** tags are never read aloud ("said Herman"). Narration says "listener", not "reader".
- **Methods proven to fail** are listed in `/RECIPE.md` ("Never again"). Don't retry them.

## 2. What is done

| Item | Where | State |
|---|---|---|
| Text | Gutenberg #23058, H. Twitchell tr. | Public domain. Third-person narrator |
| Voice map | `config.json` | **Final, picked by ear** (table below) |
| Voice samples | `samples/` (121 MP3), `casting_page.html` | All English Kokoro voices per role |
| Script builder | `text.py` (v3, by the previous agent) | Writes 168 lines to `script/`. **Output format doesn't fit the generator yet** (§4) |
| Speaker fixes | `script/queen_of_spades_fixes.json` | `roles` (line id → role) and `replace` |
| Sound assets | `audio/ambience/` + `audio/README.md` + `CREDITS.md` | 8 of 13 files uploaded, licences mostly unconfirmed |

### Voice map (from `config.json`; config is the source of truth)
| ID | Role | Voice | Style row | Speed |
|---|---|---|---|---|
| 1 | Narrator | am_michael | 250 | 0.95 |
| 2 | Herman | am_fenrir | 250 | 1.0 |
| 3 | Tomsky | am_puck | 60 | 0.92 |
| 4 | Lisaveta | af_bella | 250 | 1.0 |
| 5 | Countess (and ghost) | af_nicole | 250 | 0.92 |
| 6 | Tchekalinsky | bm_lewis | 250 | 0.95 |
| 7 | Naroumov | am_santa | 250 | 1.0 |
| 8 | Sourine | am_onyx | 250 | 1.0 |
| 9 | Saint-Germain (only inside Tomsky's story) | bm_fable | 250 | 0.92 |

Puck and Nicole speeds were changed by the owner on GitHub after picking (from 1.0 and 0.88). Speed is set per **voice name**,
so two roles can't share a voice at different speeds.

## 3. How generation works (unchanged White Nights method)
`WN_CONFIG=books/queen_of_spades/config.json WN_OUT=$PWD/out python -m wn.run chapter`

This uses `config.json` → `"chapter": "queen_of_spades"`. Each line goes through Kokoro (kokoro-onnx, model-files-v1.1) with a fixed style row,
a hidden lead-in (the previous line's last sentence) cut at the exact phoneme time, and soft trim. Lines are joined with exact pauses
of true silence, light room reverb, ±1.2 dB per-line level, overlap for interruptions, then mastered to −20 dBFS RMS and −3 dBFS peak.
QC report: `out/queen_of_spades/qc_report.md`. For a quick test, set `"paragraphs": [a, b]` in this folder's `config.json` (then set it back to `null`).

## 4. Blockers: fix these before the first audio test

**4.1 Wrong location.** `wn/run.py` reads `<repo>/script/<chapter>_lines.json` (line ~165), but `text.py` writes
`books/queen_of_spades/script/queen_of_spades_lines.json`. Don't write into `/script/`, which belongs to White Nights. Instead add an optional
`"script_dir"` key to the config and have `run.py` use it when present (default: `/script`). Keep the change minimal, and run
`python tools/smoke_test.py` afterwards to prove White Nights still works.

**4.2 Wrong fields.** `run.py` needs, per line:

| Field | Type | text.py now | Needed |
|---|---|---|---|
| `id` | string, unique, used in file names | int `1` | `"queen_of_spades_000"` |
| `speaker` | **int role id**, a key of `voices` | role name `"Narrator"`, with the id in `role` | `1` |
| `p` | int paragraph index | `paragraph` | `p` |
| `kind` | `"narr"` or `"say"` | missing | add |
| `pause_before` | seconds of silence before the line | missing | add (rules below) |
| `interrupts` | optional bool | missing | true when the dropped tag was "interrupted" / "broke in" |

The fixes file keys line ids as ints matching v3 numbering. If you change `id`, keep the fixes working (map by position, or keep a numeric `n`).

**4.3 Pause rules (proven on White Nights).** First line 0.0 s. Next piece of the same passage: 0.5 s (<15 words), 0.6 s, 0.7 s (>35 words).
Reply to another speaker: 0.6 s. New paragraph by the same speaker: 1.0 s. Dramatic beats: 1.4 s, by hand.
Scene breaks: 2.0 s. After `;` or `:` inside a split sentence: 0.35 s.

**4.4 Chunks:** ≤45 words of whole sentences. Split at `;`/`:` only for sentences over 90 words. Never generate one short sentence
on its own (it sounds choppy and deeper).

**4.5 Speaker review:** after `text.py` runs, give the owner `script/queen_of_spades_script.md` showing each book paragraph beside its spoken
lines, with guessed speakers marked. The owner has other AI agents review it. Corrections go in `queen_of_spades_fixes.json`, never in the generated files.

## 5. Suggested order
1. Fix 4.1 and 4.2, then run `text.py` and commit `queen_of_spades_lines.json` and `_script.md`.
2. Owner reviews the speakers, and the fixes are applied.
3. **Sample:** one 20–30 s passage with the Narrator plus 2–3 speakers (e.g. the card table opening), set via `"paragraphs"`. The owner listens.
4. Adjust speed or style row only if the owner asks (offer A/B).
5. Full story, then the owner listens to the lines flagged in `qc_report.md`.
6. Mix step with ambience and SFX: **only when asked**. Build it as a separate module and keep the voice track untouched.

## 6. Sound assets (staged, not used yet)
See `audio/README.md` for scenes and `audio/ambience/CREDITS.md` for credits.
- **Uploaded:** `amb_pirita_night.flac`, `amb_room_tone.wav`, `sfx_cards.aif`, `sfx_deal.wav`, `sfx_chips.wav`, `sfx_men_murmur.wav`,
  `sfx_door_open.wav`, `sfx_pistol_cock.wav`.
- **Not uploaded yet:** `amb_winter_quiet.wav`, `amb_snow_city.wav`, `amb_horror_cellar.wav`, `amb_city_cold.flac`, `amb_berlin_wind.wav`.
- **Licences:** most are unconfirmed. Each credit has its Freesound link. Don't publish anything that uses a sound whose licence still says "check".
- **Line numbers in `audio/README.md`** (e.g. "line 83", "line 123") refer to v3 script numbering. Recheck them if the script changes.
- **White Nights lessons for the mix:** keep background beds very low (music sat at −40 dB). Heavy ducking made the bed swell in every
  short break, so duck gently (3 dB, 2.5 s hold). Never loop noise into the pauses between lines: that caused ticks.

## 7. Environment notes
- Python 3.13 works. `pip install kokoro-onnx soundfile numpy scipy pydub pillow` (plus `audioop-lts` on 3.13). ffmpeg is needed.
- Kaggle: import `kaggle/runner.ipynb` by its raw GitHub URL. It must pass `WN_CONFIG` for this book (the runner doesn't yet; add a cell variable).
- Commit small, descriptive changes. The owner works from several devices and also edits files on GitHub directly, so always pull first.
