# Recipe — locked decisions

Change one thing at a time, test it on a short passage first (`config.json` → `"paragraphs": [15, 24]`), compare against the last approved version.

## Locked (proved to work)
- **Model:** VibeVoice 1.5B, `cfg_scale` 1.3, 10 steps, no sampling.
- **Dreamer voice:** LibriTTS-R reader 8230, consecutive sentences from one chapter (~12 s).
- **One line per generation** (≤ ~45 words, whole sentences), up to 3 takes, best take kept by QC.
- **Emotion comes from the voice reference and the text only.** No acting cues, no effects.
- **Speech tags removed in dialogue** ("I said", "said the girl"); storytelling paragraphs read in full.
- **"reader" → "listener".**
- **Pauses:** breath 0.5–0.7 s between pieces of a passage (0.35 s inside a split long sentence); replies 0.45–0.75 s;
  new paragraph ≥ 1.0 s; dramatic beats 1.4 s. Silence is true silence with 12 ms fades.
- **Mix:** voice RMS −20 dBFS, peaks ≤ −3 dBFS, music bed −40 dB ducked 15 dB under speech. No background noise.

## Open
- **Nastenka voice:** audition A (single recording) / B (lively run) / C (old stitched) — pick by ear, set `voices.2`.

## Known failures — never again
| Tried | Result |
|---|---|
| Inline acting cues (`[teasing]`) | Gibberish |
| `cfg_scale` 1.5 | Sounds more artificial |
| Per-beat emotion references / emotion bank (v3) | Uneven speed, wrong emotions, spontaneous music |
| Long blocks per generation (one part of 734 words) | Gibberish and drift in long passages |
| Stitched reference from many short quiet clips (Nastenka "soft") | Weird, unnatural voice |
| Hard cuts + looped room tone in pauses | Ticks between lines |
| Whole-part QC score | Hid garbled lines (97% "match" on bad audio) — QC is per line now |
| Dropping tags for laughs/cries and adding "The girl laughed" | Sounds like tags again — voices must carry it |

## If problems persist after all of the above
The ceiling is the 1.5B model. Next step: VibeVoice-Large (7B) across both T4s, slower but cleaner.
