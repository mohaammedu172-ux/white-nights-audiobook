# Replicate the White Nights audiobook, A to Z

**Audience:** an AI agent with a Linux shell (or a Kaggle notebook). Follow the steps in order and you will rebuild the
published YouTube video: 6 chapter MP3s (1 h 35 min), then one 1920×1080 MP4 with 8 paintings, plus the YouTube description.
Read `RECIPE.md` before changing any setting: it lists what was tried and failed.

Everything here was run and checked on 2026-10-21, from a fresh clone, Python 3.13, CPU only.

---

## 0. What you are rebuilding

| Part | Result |
|---|---|
| Text | Dostoevsky, *White Nights*, Garnett translation, Project Gutenberg #36034 (public domain) |
| Script | 795 spoken lines, 19,644 words, 5 speakers, speech tags removed, "reader" → "listener" |
| Voices | Kokoro 82M (Apache-2.0) built-in voices via `kokoro-onnx`; no cloning |
| Audio | `white_nights_<chapter>.mp3`, 24 kHz mono 128 kbps; voice −20 dBFS RMS, peaks −3 dBFS, quiet Tchaikovsky *June* bed |
| Video | `white_nights_audiobook_youtube.mp4`, 1920×1080, 4 fps, H.264 + AAC 160k, about 128 MB, 1:35:22 |

| Chapter | Lines | Minutes | Starts in video |
|---|---|---|---|
| first_night | 149 | 19.4 | 0:00 |
| second_night | 177 | 24.4 | 19:27 |
| nastenkas_history | 164 | 19.5 | 43:57 |
| third_night | 110 | 11.3 | 1:03:29 |
| fourth_night | 163 | 16.2 | 1:14:50 |
| morning | 32 | 4.3 | 1:31:05 |

---

## 1. Get the code

```bash
git clone https://github.com/mohaammedu172-ux/white-nights-audiobook
cd white-nights-audiobook
```

| Path | Role |
|---|---|
| `config.json` | **All settings**: voice per speaker, style row, speed, mix levels, chapter, optional paragraph range |
| `wn/text.py` | Book → script for **First Night** (uses `script/first_night_tags.json`, `_score.json`, `_fixes.json`) |
| `wn/text2.py` | Book → script for the **other 5 chapters** (auto speakers + `script/<chapter>_fixes.json`) |
| `script/<chapter>_lines.json` | **The approved scripts** (committed). Generation reads these |
| `script/<chapter>_script.md` | Human-review view: book paragraph next to spoken lines |
| `wn/kokoro_ctx.py` | Kokoro with fixed style row + hidden lead-in cut at exact phoneme timings |
| `wn/assemble.py` | Pauses, interruptions, level variation, room reverb, master, music bed |
| `wn/run.py` | Jobs: `chapter`, `book` (plus old test jobs `audition`, `settings`, `models`) |
| `wn/qc.py` | Per-line checks: Whisper clarity (GPU only), speech-rate outliers |
| `youtube/` | `make_video.py`, `grade.py`, `scenes.json`, `images/` (8 graded paintings), `description.txt` |
| `kaggle/runner.ipynb`, `kaggle/install.sh` | Same jobs on Kaggle |
| `wn/tts.py`, `wn/voices.py`, `wn/alt_models.py` | VibeVoice / Chatterbox paths. **Not used** for the published book |

---

## 2. Environment

**Option A: Linux/CPU (what the published book used).** Python 3.10+ (tested on 3.13), ffmpeg on PATH, outbound access to GitHub and PyPI.

```bash
pip install kokoro-onnx soundfile numpy scipy pydub pillow      # add --break-system-packages if pip refuses
# Python 3.13 only: pydub needs  pip install audioop-lts
ffmpeg -version
```

The Kokoro model (`kokoro-v1.0.onnx` and `voices-v1.0.bin`, from the kokoro-onnx GitHub release **model-files-v1.1**) downloads
itself to `/tmp/wn/kokoro11` on first use. **It must be v1.1**: only that export returns phoneme timings, and the lead-in cut depends on them.

**Option B: Kaggle** (adds Whisper clarity QC on GPU). Import the notebook from its raw GitHub URL, `https://raw.githubusercontent.com/mohaammedu172-ux/white-nights-audiobook/main/kaggle/runner.ipynb`,
using File → Import Notebook → Link. Don't upload the file, or it opens as raw JSON. Settings: GPU T4 ×2, Internet on. Set `JOB = "book"`,
then Save Version → Save & Run All. Results appear in the Output tab under `out/`.

---

## 3. Book text and scripts (already done; rebuild only to check or change)

The approved scripts are committed, so **you can skip to step 4**. To rebuild them:

```bash
python -m wn.text first_night      # downloads the Gutenberg text to .cache/ on first run
python -m wn.text2 all
git status --short                 # empty = identical to the approved scripts (verified)
```

If Gutenberg is unreachable, save `https://www.gutenberg.org/cache/epub/36034/pg36034.txt` as `.cache/white_nights_gutenberg.txt`.

How the script is made (so you can do the same for another book):
1. Split the book into paragraphs per chapter heading.
2. Inside `"..."` is speech. The speaker comes from the speech tag ("I said" = Dreamer, "said Nastenka", "grandmother said", ...),
   otherwise from alternation (marked *guessed*). A quote that runs into the next paragraph keeps its speaker. Nested `'...'` quotes get their
   own speaker (inside Nastenka's story, "I" is Nastenka and "she" is Grandmother).
3. Tags are deleted. Narration left over after a tag is spoken by the Dreamer only if it is more than 7 words.
4. `clean()`: "to-morrow" → "tomorrow", `--` → comma, **"reader" → "listener"**, stray `!.`/`?,` fixed.
5. Lines are cut into chunks of **≤45 words of whole sentences** (split at `;`/`:` only for sentences over 90 words).
6. Pause before each line: breath 0.5–0.7 s inside a passage, 0.6 s replies, ≥1.0 s new paragraph by the same speaker,
   First Night uses per-paragraph classes (quick 0.45, normal 0.6, answer 0.75, reflective 1.0, dramatic 1.4, scene 2.0).
7. A line whose dropped tag contained "interrupt" is marked `interrupts` (it overlaps the previous line).
8. **Every speaker guess was checked by hand.** Corrections live in `script/<chapter>_fixes.json`:
   `speaker` (paragraph → 1 Dreamer, 2 Nastenka, 3 Grandmother, 4 Lodger, 5 Matrona), `nested` (speakers of nested quotes in order),
   `book` (fix the source text, e.g. a missing quote mark), `replace` and `global` (text edits). Never edit `_lines.json` by hand.

---

## 4. Generate the audio

### 4.1 Music (optional, but in the published mix)
The bed is Tchaikovsky, *The Seasons*, June, from Wikimedia Commons (`File:Tchaikovsky_the_Seasons_June.ogg`, CC BY-SA).
`assemble.music()` downloads it if Wikimedia is reachable. If not, download it in a browser and point to it:

```bash
export WN_MUSIC=/path/to/Tchaikovsky_the_Seasons_June.ogg
```
To build without music, set `"mix": {"music": false}` in `config.json`.

### 4.2 Quick test first (about 1 min)
```bash
# in config.json:  "chapter": "first_night", "paragraphs": [15, 24]
WN_OUT=$PWD/out python -m wn.run chapter
```
Listen to `out/first_night/white_nights_first_night_p15-24.mp3`. Then set `"paragraphs": null` again.

### 4.3 The whole book (about 1.5–2 h on CPU)
```bash
WN_OUT=$PWD/out python -u -m wn.run book
```
This writes `out/<chapter>/white_nights_<chapter>.mp3`, `qc_report.md/json` and `takes/*.wav` for each chapter.
`book` **skips chapters whose MP3 already exists**. To rebuild one chapter, set `"chapter"` in `config.json` and run `python -m wn.run chapter`.

### 4.4 Settings that must match (in `config.json`)
| Speaker | Voice | Style row | Speed |
|---|---|---|---|
| 1 Dreamer (narrator) | `am_puck` | 60 | 0.9 |
| 2 Nastenka | `af_heart` | 250 | 1.0 |
| 3 Grandmother | `af_nicole` | 250 | 0.9 |
| 4 Lodger | `am_echo` | 250 | 1.0 |
| 5 Matrona | `af_kore` | 250 | 0.95 |

Mix: `music_db −40, duck_db 3, voice_rms_db −20, peak_db −3, room_rt60 0.32, room_wet_db −16, vary_db 1.2, interrupt_overlap 0.35`.

### 4.5 What the generator does per line (`wn/kokoro_ctx.py` + `wn/run.py: kokoro_takes`)
1. **Fixed style:** Kokoro normally picks a style vector by phoneme count, so pace and pitch change with line length.
   One row of the voice pack (`base[row]`) is repeated for all lengths.
2. **Hidden lead-in:** generate `<last sentence of the previous line> + " " + <line>` (first line of a chapter: "I remember it well.").
   This avoids Kokoro's high, rushed "fresh start".
3. **Exact cut:** `create_timed(..., trim=False, sentence_pause=0.35, clause_pause=0.1)` returns each phoneme's start and end time.
   Check that the combined phonemes start with the lead-in's phonemes, find the first non-space phoneme of the real line,
   and cut at `max(end of lead-in, start − 0.04 s)`, then fade in over ≤20 ms inside the silence. If the check fails,
   use a plain take and flag the line "lead-in not cut".
4. **Soft trim:** remove only samples below 0.001 amplitude, keep 60 ms before and 150 ms after, with 20 ms fades.
5. **Cache:** `takes/<id>_<md5(text, voice, row, speed, lead-in)[:8]>.wav`. Edit one line's text and only that line (and the
   line after it, whose lead-in changed) regenerates. Re-running gives near-identical but **not bit-identical** audio (ONNX).
   Keep `takes/` to reproduce exactly.
6. **QC:** with a GPU, Whisper "small" word-match clarity ≥0.85 and extra words ≤0.25. Always: speech rate within
   0.65–1.35× of that speaker's median (skipped for lines under 2.5 s). Flagged lines are listed with timestamps in `qc_report.md`. **Listen to them.**

### 4.6 Assembly and mix (`wn/assemble.py`)
1. Lines in order with their exact `pause_before` of **true digital silence**. Never loop room tone or noise (it caused ticks).
2. `interrupts` lines start 0.35 s before the previous line ends; the previous line fades out under it.
3. Each line gets a random level of ±1.2 dB (seed 7).
4. Master: 75 Hz high-pass, light room reverb (synthetic exponentially decaying noise IR, RT60 0.32 s, wet −16 dB),
   voice RMS to −20 dBFS, 2.5 s lead and 4 s tail.
5. Music: mono, looped to length, RMS −40 dB, **ducked only 3 dB** while voice is present (2.5 s hold, 1.5 s smoothing),
   3 s fade in, 5 s fade out. Peak limited to −3 dBFS. Exported as MP3 128k.

---

## 5. Build the YouTube video

```bash
python youtube/make_video.py --book out --dst white_nights_audiobook_youtube.mp4 --seconds 40   # test, ~1 min
python youtube/make_video.py --book out --dst white_nights_audiobook_youtube.mp4                # full: allow up to ~30 min
```
What it does:
1. Joins the 6 chapter MP3s with **3 s of silence** between them and prints the chapter timestamps (floored to the second):
   0:00, 19:27, 43:57, 1:03:29, 1:14:50, 1:31:05. These are also saved to `*_chapters.json`.
2. Shows the pictures from `youtube/scenes.json` at fixed seconds: 0, 468, 615, 1167, 2637, 3809, 4490, 5465.
   Each change is a **2 s dissolve** made of 8 blended frames, 0.25 s apart.
3. Uses the ffmpeg concat demuxer, `fps=4,tpad=stop_mode=clone` (so the last picture lasts to the end),
   `libx264 -tune stillimage -crf 20 -pix_fmt yuv420p` and AAC 160k, cut to the audio length.

The images in `youtube/images/` are **already graded**. Don't grade them again.

### New pictures (for another book)
Use only **public-domain** works: the artist died more than 70 years ago **and** the source labels it public domain
(Wikimedia Commons, museum open-access collections). Images from a Google search are usually copyrighted. Don't use AI-generated images
whose terms are unclear.
```bash
python youtube/grade.py painting.jpg youtube/images/09_x.png                    # day scene: full "white night" grade
python youtube/grade.py night.jpg   youtube/images/09_x.png --strength 0.35     # already a night scene: light grade
python youtube/grade.py scan.jpg    youtube/images/09_x.png --crop 0 40 0 60    # crop borders/colour strips first (L T R B px)
```
Grade: 55% colour + 45% grey, × [0.82, 0.84, 1.0] + [0.02, 0.02, 0.06], then 0.12 + 0.62·x^1.15. Fit: the whole picture at 94% of the
frame height over a blurred copy dimmed to 45%, with an unsharp mask if enlarged more than 2×.

| Image | Artist / work (public domain) | From |
|---|---|---|
| 01 | Novo-Mikhailovsky Palace on the Neva, coloured lithograph, with the title added | 0:00 |
| 02 | Ivan Aivazovsky, moonlit night | 7:48 |
| 03 | Vasily Sadovnikov, house on the Fontanka embankment | 10:15 |
| 04 | Vasily Sadovnikov, Illumination on the Moika | 19:27 |
| 05 | Vasily Sadovnikov, Voznesensky Prospekt | 43:57 |
| 06 | Bridge over the Neva (labelled "View of the Blagoveshchensky Bridge, 1851"; artist attribution unverified) | 1:03:29 |
| 07 | Ivan Aivazovsky, moonlit embankment | 1:14:50 |
| 08 | Pyotr Vereshchagin, View of the Neva Embankment | 1:31:05 |

---

## 6. Publish on YouTube

1. Upload the MP4. Description: `youtube/description.txt`
   (chapters, cast, credits, image list, hashtags). Chapter lines must start at `0:00` and be in order.
2. Audience: not made for kids. Altered or synthetic content: the description already says the voices are AI.
   No real person's voice was cloned.
3. Links in the description become clickable only after the channel is **phone-verified** (up to 24 h). The description has no links, so it can be posted at once.
4. Auto-captions can take hours on a long video. If they don't appear, build an `.srt` from each chapter's line start times
   (`voice_track` returns them; `qc_report.json` has them rounded to the second) plus the line text, offset by each chapter's start and upload it under Subtitles.
5. Before going public, open the music's Commons page and confirm the licence and performer. Credit them as the page asks
   (CC BY-SA needs a credit and a licence name).

---

## 7. Verify before you call it done
- [ ] `git status` after rebuilding scripts is empty (or your changes are intended).
- [ ] Chapter durations within ±0.2 min of the table in §0.
- [ ] `qc_report.md` flagged lines listened to. Known flags in the published build: First Night 5:25; Second Night 0:05, 5:51, 6:47,
      7:37, 18:01; Fourth Night 0:55, 2:53, 4:24, 13:05.
- [ ] Spot-listen: chapter starts, a Nastenka emotional passage, an interruption, a long pause. Check for no ticks, no clipped first words,
      no music swelling in short breaks, no speech tags.
- [ ] Video plays to the end. The picture changes at the listed times. The audio isn't shifted against the chapter timestamps.

## 8. Never do (each was tried and failed; details in RECIPE.md)
Long generations; inline emotion tags; emotion reference banks or effects; VibeVoice 1.5B for Nastenka; references stitched from
short clips; looped room tone in pauses; DTW/sound-matched lead-in cuts; one generation per short sentence; Kokoro style chosen
by length; punctuation "spice"; music ducking 15 dB; whole-file QC scores; re-adding "she laughed" narration; copyrighted pictures.
