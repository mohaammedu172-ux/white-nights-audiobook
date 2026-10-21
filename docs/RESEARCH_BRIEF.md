# Research brief: making AI dramatized audiobooks sound like real actors

**Audience:** an AI research agent. **Your job:** find better methods, models and tools for the *next* audiobook
project, based on what worked and what failed in the first one (below). Recommend only things that can be
tested in a small 10–30 second sample, and say what each costs (time, money, compute, licence).

---

## 1. The project

- **What it is:** a fully dramatized, multi-voice AI audiobook of Dostoevsky's *White Nights* (Constance Garnett
  translation, 1918, Project Gutenberg #36034). It's about 19,600 spoken words, 795 lines and 1 h 35 min across 6 chapters, with 5 characters.
  It's published on YouTube with still public-domain paintings as the picture.
- **Owner:** a single non-programmer working from a phone, a home laptop and a work laptop. Everything lives in a GitHub repo
  (`mohaammedu172-ux/white-nights-audiobook`); heavy jobs run on free Kaggle notebooks (2× T4 GPU) or on CPU.
- **Future projects:** more public-domain novels, possibly in **Arabic** later.

### The owner's quality bar (in his words, summarized)
1. Sounds like **real actors**, not a robot: natural pace, natural pauses and breaths, no sudden voice changes.
2. **No speech tags read aloud** ("I said", "said the girl"). The voices must carry who is speaking.
3. **No background noise.** Only quiet music under the voice is fine.
4. Narration addresses the **listener**, not the "reader".
5. No gibberish, clicks, ticks, clipped first words or muffled audio. Each of these was heard and rejected at some point.
6. He picks voices and pictures **by ear and by eye**. Automated scores alone are not trusted (see §5).

### Hard constraints
- **Free:** no paid APIs. Free Kaggle (T4 ×2, about 30 GPU h/week, Python 3.13) or a CPU Linux box.
- **Open licences** that allow publishing on YouTube: model weights *and* voices.
- **No cloning of real people** without a licence. Built-in model voices are fine. Public-domain or CC text, images and music only.
- The workflow must be **repeatable from a repo** and runnable by a non-programmer (one setting changed, then "Run").

---

## 2. Timeline of approaches

| # | Approach | Outcome |
|---|---|---|
| 0 | Colab notebook with Chatterbox; "Alice's tea party" multi-voice test | Proof of concept only; moved to a real book |
| 1 | **VibeVoice 1.5B** (Microsoft, MIT), voices cloned from LibriTTS-R readers (CC BY 4.0), long blocks per generation | Gibberish and drift in long passages; a crowd scene came out as nonsense |
| 2 | VibeVoice + inline acting cues (`[teasing]`) and per-emotion reference clips ("emotion bank", v3) | Wrong emotions, uneven speed, spontaneous music. Abandoned: "stop engineering emotion by editing the sound" |
| 3 | VibeVoice, one line (≤45 words) per generation, 3 seeds, Whisper QC picks the best take, retakes (v4–v5) | Dreamer acceptable. **Nastenka always bad**: ticks, lag, muffled, sounds old |
| 4 | VibeVoice settings sweep for Nastenka: 10/25/50 diffusion steps, bf16 vs fp32, 3 reference voices | No setting fixed her |
| 5 | Model comparison: Kokoro (`bf_emma`, `bf_isabella`, `af_heart`) vs Chatterbox (cloned) | **Kokoro `af_heart` chosen by ear** |
| 6 | **Kokoro 82M** (Apache-2.0) via `kokoro-onnx`, built-in voices, CPU | Clean audio, but new problems (§3.2) |
| 7 | Kokoro + fixed style row + hidden lead-in cut at exact phoneme timings | **Accepted.** Whole book generated on CPU |
| 8 | Mix: light room reverb, ±1.2 dB per-line level variation, real interruptions (overlap) | All three accepted ("surprisingly work") |
| 9 | YouTube: 8 public-domain 19th-century paintings, "white night" colour grade, 2 s dissolves | Published |

---

## 3. Problems faced: symptom, cause, fix

### 3.1 VibeVoice era
| Symptom heard | Cause (found or suspected) | Fix / status |
|---|---|---|
| Gibberish in long passages, crowd scene nonsense | One generation of hundreds of words; model drifts | Cut into lines of ≤45 whole-sentence words. Fixed the drift |
| Emotion cues read or turned into noise | 1.5B model doesn't follow inline tags | Removed all cues; emotion only from text and reference |
| Weird voice from "soft" reference | Reference stitched from many short quiet clips | Use one continuous clean reference clip |
| Ticks between lines (v4) | Hard splices and looped room tone in the pauses | True digital silence plus short fades inside the silence (v5). Fixed |
| Nastenka: ticks, lag, muffled, aged voice | Model ceiling for that voice type; not fixed by steps or precision | **Dropped VibeVoice for her**, then for everyone |
| `cfg_scale` 1.5 sounded more artificial | — | Keep 1.3 |
| QC score 97% on garbled audio | Whole-part scoring hides bad lines | QC per line |

### 3.2 Kokoro era (the accepted pipeline)
| Symptom heard | Cause | Fix |
|---|---|---|
| Voice changes dramatically after ~15 s / between chunks | Kokoro picks a **style vector by phoneme count**, so text length changes pace and pitch | **Fixed style row per voice**: repeat one row of the voice pack for every length (Dreamer `am_puck` row 60, others row 250) |
| First seconds of every line childish, high, rushed | Kokoro's "fresh start" prosody at utterance start | **Hidden lead-in:** generate the previous line's last sentence (or "I remember it well.") plus the line, then cut the lead-in off |
| Cut-off words ("You will make me" lost), scraps ("littles"), deeper voice | Lead-in cut by guessing (DTW sound matching), plus one generation per short sentence | Use the **model-files-v1.1** ONNX export, which returns **phoneme timings**. Cut exactly at the first phoneme of the real line, 40 ms early, inside the silence. One generation per line, not per sentence |
| Row 250 made the Dreamer deeper and slower than auditioned | Different style rows are different voices | Owner picked row 60 by ear |
| Dreamer slightly fast | — | Kokoro's own `speed` 0.9 (no time-stretching). No artefacts |
| First word half-clipped | Trim threshold cut soft onsets | Soft trim: cut only below 0.001 amplitude, keep 60 ms before, fade inside the silence |
| New sentence inside a line rushed | Kokoro's default inter-sentence gap | `create_timed(sentence_pause=0.35, clause_pause=0.1)` |
| Short sentences sound "disconnected and connected" | Gaps between very short sentences | Partly solved by the above. **Still a mild issue** |
| Punctuation "spice" (`!!!!`, `???????`, `;`) | Kokoro barely reacts | No real difference; abandoned |
| Music swells in every short break | Ducking 15 dB under speech | Duck only 3 dB with a 2.5 s hold, so only long breaks rise |
| Lines flat and same level | Every line normalized identically | ±1.2 dB random per-line level |
| Voices sound pasted together | Dry voices, nothing shared | Shared light room reverb (RT60 0.32 s, wet −16 dB) |
| Interruptions sound like polite turn-taking | Fixed pause before every line | Line whose dropped tag said "interrupted" starts 0.35 s *before* the previous ends; previous fades out |

### 3.3 Script problems (text to lines)
| Problem | Fix |
|---|---|
| Speech tags read aloud | Regex tag removal; narration fragments of ≤7 words left after removal are dropped |
| Wrong speaker (alternation guess), Nastenka's letter given to Matrona, quotes inside quotes (Grandmother or the Lodger inside Nastenka's story) | Auto attribution plus **hand-checked override files** per chapter (`script/<chapter>_fixes.json`); nested `'...'` quotes get their own speaker |
| Dropping "she laughed" and adding "The girl laughed" | Sounded like tags again; voices must carry it |
| "reader" in narration | Replaced with "listener" |
| Scripts need human-level review | Exported side-by-side review files (`*_script.md`) and had other AI agents review them |

### 3.4 Infrastructure problems
- Kaggle: "Are you still there?" idle prompt; notebook imported as a script (raw JSON) unless imported by raw GitHub URL; Python 3.13 broke the `kokoro` pip package (so `kokoro-onnx` is used); a file named `chatterbox.py` shadowed the package.
- Sandboxed cloud shell can't reach Hugging Face or Wikimedia. GitHub and PyPI work. Music had to be supplied as a local file.
- Without a GPU there is no Whisper QC, only a speech-rate check. So 10 flagged lines remain unverified by ASR.

### 3.5 Publishing problems
- Pictures first came from a Google search: copyrighted modern works. They were replaced with paintings by artists who died more than 70 years ago (Sadovnikov, Aivazovsky, P. Vereshchagin).
- The paintings are day scenes. A "white night" grade (desaturate, cool tint, lifted blacks) made them fit.
- Music: a Tchaikovsky *June* recording from Wikimedia Commons (CC BY-SA). Performer and licence version are still to be confirmed.
- YouTube: description links aren't clickable until the account is verified (24 h). Auto-captions were "not available" right after upload (processing).

---

## 4. What works (keep) and what doesn't (avoid)

**Works**
- Kokoro 82M via kokoro-onnx with model-files-v1.1: clean, free, CPU (one chapter in about 20 min), Apache-2.0.
- Fixed style row per voice, a hidden lead-in cut at exact phoneme timings, and Kokoro's own `speed`.
- One line (≤45 words of whole sentences) per generation, with a cache keyed by text, voice, settings and lead-in, so edits regenerate only changed lines.
- Tags removed; pauses set by rules (breath 0.5–0.7 s, reply 0.45–0.75 s, new paragraph ≥1.0 s, dramatic 1.4 s).
- True silence between lines; light shared reverb; per-line level variation; overlapped interruptions.
- Mix: voice RMS −20 dBFS, peaks −3 dBFS, music −40 dB with gentle 3 dB ducking.
- Hand-checked speaker overrides; external AI review of scripts.
- GitHub repo plus a Kaggle runner notebook that `git pull`s and runs one job.
- Small A/B samples, judged by the owner's ear.

**Doesn't work**
- Long generations; inline emotion tags; emotion reference banks; audio-effect "emotion"; punctuation tricks.
- VibeVoice 1.5B for young female voices; stitched references.
- Sound-matching (DTW) cuts; one generation per short sentence.
- Heavy music ducking; whole-file QC scores.

---

## 5. Open problems: what to research

Ranked by how much they limit quality:

1. **Acting / emotion.** Kokoro is clean but emotionally narrow. It reads tears, laughter and anger in the same tone.
   *Find:* open-licence TTS (or speech-to-speech) that gives **controllable emotion or style** without the artefacts VibeVoice had, runs on 2× T4 or CPU, and has **built-in or licensable voices**. For each candidate: licence, voice licence, VRAM, speed, known artefacts, and whether it returns timings. Candidates to verify yourself, not endorsements: StyleTTS 2 descendants, F5-TTS, Chatterbox (emotion "exaggeration"), Zonos, IndexTTS2, Orpheus, Dia, Sesame CSM, Higgs Audio, Kokoro fine-tunes.
2. **Dialogue flow between voices.** Turn-taking still sounds like separate recordings joined together. *Find:* multi-speaker dialogue models or prosody-transfer methods that condition a reply on the previous speaker's audio.
3. **Short sentences.** A run of very short sentences still sounds slightly disconnected. *Find:* prosody or phrasing control, and text normalization tricks backed by evidence.
4. **Automatic QC that matches a human ear.** ASR clarity misses "sounds weird" and "voice changed". *Find:* free metrics (e.g. UTMOS or other MOS predictors, speaker-similarity drift between lines, pitch or rate outlier detection) that would have caught the failures in §3, and runtimes on CPU or T4.
5. **Speaker attribution.** Needed hand fixes in every chapter. *Find:* reliable LLM-based or BookNLP-style quote attribution for novels, including nested quotes, ideally with confidence scores.
6. **Arabic.** Open TTS with natural Modern Standard Arabic (and dialect) voices, diacritization needs, licences.
7. **Video.** Cheap ways to add gentle motion to still paintings (slow pan/zoom, parallax) without looking AI-generated. Also a reliable public-domain image search with licence metadata.
8. **Music.** A source of public-domain or CC0 **recordings** (not just compositions) with clear licence metadata.

### How proposals will be tested
Each idea is tried on the same 10–30 s passages (a Dreamer narration passage and a Nastenka emotional line),
compared A/B against the current pipeline by ear, then on one full chapter. Please give for each recommendation:
what it fixes from §3/§5, how to try it in a few lines of code, licence, compute, and risks.

---

## 6. Facts to rely on
- Current settings: `config.json`. Method details: `RECIPE.md` and `docs/REPLICATE.md`.
- Voices: Dreamer `am_puck` (row 60, speed 0.9), Nastenka `af_heart` (250, 1.0), Grandmother `af_nicole` (250, 0.9),
  Lodger `am_echo` (250, 1.0), Matrona `af_kore` (250, 0.95).
- Chapter lengths (min): First Night 19.4, Second Night 24.4, Nastenka's History 19.5, Third Night 11.3, Fourth Night 16.2, Morning 4.3.
- Lines still flagged by the rate check (not ASR-verified): First Night 5:25; Second Night 0:05, 5:51, 6:47, 7:37, 18:01; Fourth Night 0:55, 2:53, 4:24, 13:05.
