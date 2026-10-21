# Recipe — locked decisions

Change one thing at a time, test it on a short passage first (`config.json` → `"paragraphs": [15, 24]`), compare against the last approved version.

## Locked (proved to work)
- **Model:** Kokoro (see Voices). VibeVoice 1.5B kept as an option (`cfg_scale` 1.3, 10 steps).
- **One line per generation** (≤ ~45 words, whole sentences), up to 3 takes, best take kept by QC.
- **Emotion comes from the voice reference and the text only.** No acting cues, no effects.
- **Speech tags removed in dialogue** ("I said", "said the girl"); storytelling paragraphs read in full.
- **"reader" → "listener".**
- **Pauses:** breath 0.5–0.7 s between pieces of a passage (0.35 s inside a split long sentence); replies 0.45–0.75 s;
  new paragraph ≥ 1.0 s; dramatic beats 1.4 s. Silence is true silence with 12 ms fades.
- **Mix:** voice RMS −20 dBFS, peaks ≤ −3 dBFS, music bed −40 dB ducked only 3 dB under speech (2.5 s hold). Light room reverb (RT60 0.32 s, −16 dB), ±1.2 dB per-line level, interruptions overlap 0.35 s. No background noise.

## Voices (chosen by ear, 2026-10-20)
- **Dreamer `am_puck`, Nastenka `af_heart`, Grandmother `af_nicole`, Lodger `am_echo`, Matrona `af_kore`.** Kokoro 82M (Apache-2.0) via kokoro-onnx.
- Why: every VibeVoice take of Nastenka had ticks, lag, muffling or an aged voice, whichever reference was used and
  even at 50 steps / full precision. Kokoro's built-in voices are clean. Trade-off: no cloning of the cast readers.
- Kokoro runs on CPU (a whole chapter in ~20 min), so chapters no longer need Kaggle.
- **Fixed style row per voice** (`config.json` → `kokoro_style`): Puck 60 (closest to the auditioned voice; 250 sounded deeper), Heart 250. **Speed:** Puck 0.9 (Kokoro's own speed setting, not stretching), Heart 1.0.
- **Hidden lead-in, cut exactly:** each line is generated after the previous line's last sentence (first line: "I remember it well."),
  then cut at the first phoneme of the real line using Kokoro's phoneme timings (model-files-v1.1). Fixes the high, rushed fresh start.
- **Sentence pauses inside a line from Kokoro's timings:** 0.35 s after a sentence, 0.1 s after a clause.

## Known failures — never again
| Tried | Result |
|---|---|
| Inline acting cues (`[teasing]`) | Gibberish |
| `cfg_scale` 1.5 | Sounds more artificial |
| Per-beat emotion references / emotion bank (v3) | Uneven speed, wrong emotions, spontaneous music |
| Long blocks per generation (one part of 734 words) | Gibberish and drift in long passages |
| Stitched reference from many short quiet clips (Nastenka "soft") | Weird, unnatural voice |
| Hard cuts + looped room tone in pauses | Ticks between lines |
| VibeVoice 1.5B for Nastenka (any reference, 10–50 steps, bf16/fp32) | Ticks, lag, muffled, aged voice |
| Lead-in cut by matching sound (DTW) instead of timings | Clipped words ("…lose my timidity"), scraps ("littles") |
| One generation per short sentence | Choppy, deeper voice |
| Punctuation "spice" (!!!!, ???????) | No real difference |
| Music ducking 15 dB | Music swells in every short break; now 3 dB with a 2.5 s hold |
| Whole-part QC score | Hid garbled lines (97% "match" on bad audio) — QC is per line now |
| Dropping tags for laughs/cries and adding "The girl laughed" | Sounds like tags again — voices must carry it |

## If problems persist after all of the above
The ceiling is the 1.5B model. Next step: VibeVoice-Large (7B) across both T4s, slower but cleaner.
