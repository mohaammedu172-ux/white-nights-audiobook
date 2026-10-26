# White Nights — dramatized audiobook

Dostoevsky's *White Nights* (Constance Garnett translation, 1918, Project Gutenberg #36034) as a five-voice AI audiobook
(Dreamer, Nastenka, Grandmother, the Lodger, Matrona), 1 h 35 min, published on YouTube with public-domain paintings.
Voices: Kokoro 82M (Apache-2.0) built-in voices, no cloning.

| Read | For |
|---|---|
| `docs/REPLICATE.md` | Rebuild the published audiobook and video from scratch, step by step |
| `docs/RESEARCH_BRIEF.md` | Every method tried, every problem, what works and what doesn't, open research questions |
| `RECIPE.md` | Locked decisions and the "never again" list — read before changing settings |

## Quick start
```bash
pip install kokoro-onnx soundfile numpy scipy pydub pillow
WN_OUT=$PWD/out python -m wn.run book                                   # 6 chapter mp3s (CPU, ~1.5–2 h)
python youtube/make_video.py --book out --dst white_nights_audiobook_youtube.mp4
```
On Kaggle: import `kaggle/runner.ipynb` by its raw GitHub link, set `JOB`, Save & Run All.

## Credits
Text: Project Gutenberg (public domain). Voices: Kokoro TTS (Apache-2.0).
Music: Tchaikovsky, *The Seasons* — June, Wikimedia Commons recording (CC BY-SA).
Images: 19th-century public-domain paintings (list in `docs/REPLICATE.md`).

## Arabic poetry pipeline (Mu'allaqat)
`ar/` makes recited audio of the Seven Mu'allaqat, original verses and modern poem-style version, in a male classical voice:
Chatterbox Multilingual (ONNX) → two speech-recognition judges → automatic retries → assembly at 80% speed → background music → QA report.
- Scripts: `books/muallaqat/<poem>/original.txt`, `modern.txt` (`N|half1|half2`) and `job.json`
- Rules for writing the scripts: `books/muallaqat/RULEBOOK.md`; learned word fixes: `books/muallaqat/problem_words.csv`
- Run on Kaggle: `kaggle/arabic_runner.ipynb` (GPU T4, Internet on; add your music as a dataset)
- Run locally: `python -m ar.run books/muallaqat/imru_al_qays/job.json --verses 1-3 --music path/to/music.mp3`
- Voice credits: `voices/CREDITS.md`
