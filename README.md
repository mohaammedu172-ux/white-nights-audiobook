# White Nights — dramatized audiobook

Dostoevsky's *White Nights* (Constance Garnett translation, 1918, Project Gutenberg #36034) as a two-voice AI audiobook:
the **Dreamer** (narrator and male lead) and **Nastenka**. Voices: VibeVoice 1.5B (MIT) cloned from LibriTTS-R readers (CC BY 4.0).

## How to run (any computer or phone browser)
1. Open the Kaggle notebook **White Nights runner** (made once from `kaggle/runner.ipynb`).
2. Set `JOB` in the first cell: `audition` or `chapter`.
3. **Save Version → Save & Run All**. Close the tab if you like; it runs on Kaggle.
4. Results: the notebook's **Output** tab → `out/…` (mp3s play on the phone).

The runner always pulls the latest version of this repo, so nothing needs re-uploading.

## Layout
| Path | What |
|---|---|
| `config.json` | Chosen voices, model settings, QC thresholds, mix levels, optional paragraph range for quick tests |
| `script/first_night_fixes.json` | **Edit this** to change the script (text fixes, restored actions, forced breaks) |
| `script/first_night_lines.json` | Generated: every spoken line with speaker and pause before it |
| `script/first_night_script.md` | Generated: book text beside the spoken lines, for review |
| `script/first_night_tags.json`, `_score.json` | Who speaks each paragraph; pause class per paragraph |
| `wn/text.py` | Book → script (`python -m wn.text first_night`) |
| `wn/voices.py` | Builds the voice references |
| `wn/tts.py` | VibeVoice, one line per generation, both GPUs |
| `wn/qc.py` | Per-line checks: clarity, extra sounds, rushed/dragging |
| `wn/assemble.py` | Exact pauses, click-free joins, master + quiet music |
| `wn/run.py` | Jobs: `audition`, `chapter` |
| `RECIPE.md` | What works, what doesn't, and why — read before changing anything |

## Credits
Text: Project Gutenberg (public domain). Voices: LibriTTS-R (CC BY 4.0), readers 8230 and 4214.
Music: Tchaikovsky, *The Seasons* — June, Wikimedia Commons recording (CC BY-SA; replace before publishing).
