# Handoff: AI recitation of Imru' al-Qays's Mu'allaqa

Owner: Mohammed (native Arabic speaker; judges by ear). Goal: a recitation he rates 9–10/10. First a measured style (al-Manṣūr level); melodic chanting later.
Two products: (1) the original poem, recited; (2) a modern Arabic rendering of it, recited in the same voice.
Repo: `white-nights-audiobook`, branch `arabic-pipeline`. Book folder: `books/muallaqat/imru_al_qays/`.

---

## Part 1: What exists (A–Z, short)

**Voice and generation**
- TTS: Chatterbox Multilingual (VoiceTorch), voice sample `voices/clartts_male_ref.wav` (ClArTTS speaker). Settings: `cfg_weight` 0.3, exaggeration 0.35, tempo 0.8 applied after.
- Unit = one half-verse. 6 takes each; the best is kept by `pick_score` (letter judge: words, letters, vowel marks; penalties for a doubled ending or doubled letters).
- Style tags in the script (`{sad}`, `{playful}`, `{proud}`, `{awe}`, `{suspense}`) switch the voice sample and exaggeration. No pitch or speed shift (removed, rule 38).

**Text rules** (`ar/text_rules.py`)
- Original: no pause inside a half; end of the first half lengthened (ishbāʿ); rhyme written once (ـلِي), never doubled.
- Tajwīd spelling: tanwin written out (ن، م before ب); plain shadda (written-out shadda doubled stop letters).
- Modern: same recitation rules, plus `inner_pauses: 'breath'` (one pause at the middle comma of a half of 7+ words). Not yet approved.

**Audio cleanup** (`ar/assemble.py`)
- Cut junk after the last letter (CTC timing); 50 Hz hum filter; noise reduction; soft gate in pauses; declick; per-clip stretch; two-pass loudnorm.
- Tone matching (`ar/tone.py`): every clip brought to one brightness (takes differ by ~10 dB above 4 kHz).
- Rests: 0.7 s after a half, 1.0 s after a verse (as heard); longer (1.0/1.5 s) in the night (44–47) and horse (52–62) sections.

**Tests**
- Letter judges: ClArTTS wav2vec2 CTC (biased toward this voice; its letter-swap alarms proved false 14/14) and a second ASR (Cohere).
- Section tests `ar/sections.py`: grammar, letters, tajwīd timing, delivery, flow. `ar/precheck.py`: noise gate before anything is played to Mohammed (hiss in pauses < −80 dB).
- References, used only to measure and compare by ear, never to train or clone: al-Manṣūr and ʿAbd al-Raḥmān Āl Rashī (archive.org). Timings in `reference/*.json`.
- Ear checks: blind A/B pages (one claude.ai artifact with a small database); answer keys in `ar/judge_cal/`.

**Maps and plans**
- Poem map, 5 layers (`ar/poem_map.py`): text, i'rab, metre, recitation, results. I'rab map from al-Durra's فتح الكبير المتعال (526/802 words).
- Commentary: al-Zawzani, all verses (`/root/irab/zawzani.json`, rebuildable).
- `roadmap.json` (goal, rules, 6 sections, regression checks, run history), `issues.json` (40 issues), `RULEBOOK.md` (rules 1–39).

**Cloud runs** (GitHub Actions)
- Push to branch `make-audio` → workflow "Arabic audio". The job file comes from `export/JOB`. 27 shards of 3 verses; a part-poem run takes ~45 min. Results go to branch `audio-results`.
- Clip export: push `export-clips` with `export/RUN_ID`.

**Status**
- Original, 25-verse portion (1–10, 43–53, 69–72): approved as "good enough". Full 81-verse run not yet done.
- Modern rendering v2 (`modern_v2.txt`), verses 1–22: text accepted. It follows al-Zawzani, keeps the original's single rhyme (ـلِ), balanced halves, imagery instead of explanation, and the original's frankness in the love scenes.
- Its delivery is not approved: read as prose it sounded "AI" and noisy. A/B pending: shorter halves with one breath.

**Rules of work**
- One section at a time; problems found elsewhere go to the issue log.
- Max 3 attempts per issue, then park it.
- Every change must pass its own measure, break no regression check, and not be contradicted by Mohammed's ear.
- Test on a small portion before any full run.
- Mohammed's ear only to finalize: short blind checks (≤12 ratings), with the reference reciters alongside.
- Never: Quran audio, cloning a real voice, training on the references, storing the GitHub token, force-pushing.

---

## Part 2: Issues and what was tried

| Issue | Tried | Result |
|---|---|---|
| Noise, ticks, junk after words | CTC tail cut, hum filter, denoise, declick, 2-pass loudnorm; room tone tried and rejected | Fixed |
| Noise in test files sent to the ear | No check on local tests | Fixed: `precheck.py` gate + soft gate in pauses |
| Doubled rhyme (ـلِيي heard "ي ي") | Write the ending once | Fixed. A longer hold of the rhyme is parked: spelling and stretching both failed |
| Shadda said as two letters (حط طه) | Written-out shadda, sonorant-only, plain shadda | Plain shadda; 10/10 by ear vs the reciters |
| Tanwin missing (6a عبرتو) | Spelling variants, removing the sad style | Fixed: plain voice for 6a. Tanwin 10/10 by ear |
| Letter-swap alarms (ظ/ض، ق/ك، ط/ت) | Ear checks | Judge false alarms; swaps no longer count in picking |
| Endings and tanwin accuracy | Pick takes by letters and marks | Endings 89→95%, tanwin 84→97% |
| Long vs short vowels (1.29× vs reciters' 1.7×) | Splice stretch (ticks); one-pass stretch (no ticks) | No audible gain. Parked |
| Qalqala weak (9/10) | Drop the sukun; echo vowel; louder release | No clear win. Parked; retest after pace |
| "Too fast" | Slower voice sample (6.3 letters/s); lower cfg | Not preferred. "Fast" meant short rests, short endings and even pace: rests now set by section; held endings rejected |
| Pauses inside a half | Remove inner punctuation | Mostly fixed; confirm in a full run |
| Flat pitch (every line, vs the reciters) | Not yet | **Biggest open gap** |
| Even pace, no shape in a line | Not yet | Open |
| Muffled or distant voice; deep "awe" voice at 70b | Found: take-to-take brightness, plus a pitch drop in the style | Tone matching, no pitch or speed shifts; approved in the portion |
| "Separate blocks" feel | Tone matching helps; whole-verse takes untested | Open |
| Heavy ر, v15a ز vowel, v51 يهزل, i'rab gaps (v21, 38, 42, 52, 73, 75, 77) | Logged | Open |
| Modern sounds "AI" | Prose reading (commas) → original's recitation rules → shorter halves + one breath | Pending A/B |

---

## Part 3: Research prompts for the next AI

1. **Pitch.** How do human reciters of classical Arabic poetry (inshād, measured style) shape pitch across a ṭawīl half-verse? Give measurable targets: range in semitones, rise and fall points, and the end-of-half contour. How can a TTS like Chatterbox be pushed toward them: text cues, reference-sample choice, prosody transfer, or post-hoc pitch editing (WORLD/PSOLA) without artifacts?
2. **Shape within a line.** What makes a recitation "breathe": slowing on key words, stress on كَأَنَّ and the emphasised word, the hold before the rhyme? Find measurable features from recorded reciters (al-Manṣūr, Āl Rashī or others), and a way to steer a TTS toward them per word.
3. **Better voice or model.** Which open Arabic TTS or voice-conversion models (2025–2026) handle Classical Arabic with full vowels, long vowels and prosody control better than Chatterbox Multilingual? Rank them by Classical Arabic quality, control over duration and pitch, and CPU cost. Exclude anything that clones a real person without consent.
4. **Judging.** What open models can score Arabic recitation quality automatically (pronunciation, prosody, naturalness: a MOS predictor or tajwīd checkers) so fewer ear checks are needed? Note which are reliable on non-Quranic poetry.
5. **Modern rendering.** What principles do published modern Arabic verse renderings of the Mu'allaqāt follow (rhyme, metre, register)? Name good examples. How should a modern prose-poem be recited so it doesn't sound like a TTS reading text aloud?
6. **Qalqala and long vowels.** Is there a reliable way to get audible qalqala and longer madd from a TTS: phoneme-level duration control, a fine-tuned model, or a specific spelling? Cite evidence.
