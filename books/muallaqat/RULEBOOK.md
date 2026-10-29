# Mu'allaqat recitation rulebook — v1

These rules decide how the scripts are written so the voice model (Chatterbox, male ClArTTS reference) says every word correctly and reads the poems the way poetry is read rather than like prose. Each rule was learned by listening. When something new goes wrong, add it here and, if it's a word-level fix, to `problem_words.csv`.

## Script format
- One verse per line: `N|first half|second half`. Lines starting with `#` are comments.
- The voice is generated **one half-verse at a time**, with a short breath between halves and a longer one between verses.

## Vowelling (tashkīl)
1. **Every consonant carries a mark**: a vowel, sukun or shadda. Unmarked letters get guessed, and guesses go wrong.
2. **Standard "al-" spelling**: sukun on the lam before moon letters (الْقَمَرُ), shadda on the sun letter after a silent lam (الشَّمْسُ). Do **not** use the merged prosodic spellings (لْلِوَى، دْدَخُولِ، لْكَثِيبِ): the model reads doubled letters twice and turns a merged lam into "al-a…".
3. **Tanwīn is written as the mark** (ـٌ ـٍ ـً), never spelled out as a ن.
4. **Dagger alif** in هَٰذَا، هَٰذِهِ، ذَٰلِكَ، لَٰكِنَّ.
5. **Check the original verses against the metre** (ṭawīl: faʿūlun mafāʿīlun faʿūlun mafāʿilun). The metre settles doubtful vowels, e.g. مُهَرَاقَةٌ not مُهْرَاقَةٌ.
6. No full Unicode decomposition. The program splits only the hamza letters (أ إ آ ؤ ئ) for the model; that happens automatically.

## Poem style (both versions)
7. **Half-verse endings keep their vowel**: don't put a sukun at the end of a half.
8. **The end of each verse is stretched** (the rhyme vowel is written out long):
   - Original: the long rhyme is written in full (ـلِي) on every verse.
   - Modern: the last vowel is lengthened in writing (وَحَوْمَلَا، الشَّمَالِي، فُلْفُلِي).
9. **Stretch the pronoun هُ to هُو** where a reader would lengthen it (تَكْشِفُهُو), mainly at half and verse ends.

## Fixes learned by ear
10. **The very first word needs a lead-in**: verse 1 starts with `، ` so قِفَا is said with its kasra (without it the model said قَفَا).
11. **A comma separates short words that run together** and get misheard: لَمْ يَعْفُ، رَسْمُهَا (was heard as "yaʿthur ismuhā").
12. **Don't open a half with one word cut off by a colon or comma** (اُنْظُرْ: … / نَشِيطٌ، …). The voice says that word and then babbles until it's cut off. Join the word to what follows, or give it a subject (هُوَ نَشِيطٌ). Found in the first full run: modern 3a, 55a.
13. **A leading "، " rescues a half that keeps running on**, the same trick as verse 1 (original 39b, modern 31a). The automatic last retry now adds it.
14. Long sentences run away or get cut off. One half-verse per generation solves this. If a half is still very long, add a comma at a natural breath.

## Emotion and emphasis (التنغيم)
The written text doesn't carry the melody of the sentence; reciters add it. Our voice model only reacts to spelling and punctuation, so we mark the key word:
15. **Command (أمر), call (نداء), plea (التماس):** write the key long vowel twice and put "!" after it: قِفَاا!، أَفَااطِمَ مَهْلًا!، أَلَاا انْجَلِي!. Chosen by ear (call 1B, plea 2B). The 4-alif version قِفَاااا was rejected.
16. **Wonder (تعجّب):** stretch the vowel and trail off with "..." instead of "!": فَيَاا لَكَ مِنْ لَيْلٍ... (chosen 3C).
17. **Mood styles.** A tag at the start of a half sets that half's voice. The settings live in job.json under "styles", and each was chosen by ear in round 2:
    | Tag | Mood | Reference voice | Expressiveness | Shaping after |
    |---|---|---|---|---|
    | (none) | longing, commands, plain | standard | 0.35 | — |
    | `{playful}` | flirting, teasing (v10–17) | lively | 0.4 | — |
    | `{suspense}` | the night visit (v23–29) | calm | 0.25 | 4 dB quieter |
    | `{awe}` | the storm (v70–81, not 70a) | calm | 0.35 | 0.92× speed, 1 semitone lower |
    | `{sad}` | weeping, the night (v4, 6, 9, 44, 45) + "..." at the end of the first half | calm | 0.25 | 0.92× speed, ½ semitone lower |
    | `{proud}` | the horse (v52–62) | lively | 0.45 | 1.08× speed, 2 dB louder |
18. **The calm voice breaks on commands with "!"** (قِفَاا! with the calm voice babbled), so commands always use the standard voice. That's why v70a, a call, has no `{awe}` tag. "!" after every word also broke the voice.
19. **Question (استفهام):** undecided, so questions stay plain for now. "..." straight after هَلْ broke the voice.
20. When the marked word opens a half, keep the leading "، " (rules 10 and 13). Don't go above 0.45 expressiveness: at 0.6 it babbled every time.
21. The listening models often drop stretched words, so the comparison counts a doubled vowel as one. Your ear is the final check on these lines.
Style tags go at the very start of a half: `{sad} وَلَيْلٍ كَمَوْجِ الْبَحْرِ...`. The calm and lively reference voices are joined from the same ClArTTS reader's calmest and liveliest clips, picked by measuring pitch movement, speed and loudness range (voices/CREDITS.md).

## Recitation rules from تجويد (pronunciation)
22. **Text preparation:** Chatterbox was trained on NFKD-normalized text (vowel mark before hamza: ـَٔ). Our first workaround put the hamza before the vowel, which the model may not recognize. Set `"text_prep": "nfkd"` in job.json for the ONNX voice. The torch voice always does this itself. The score improved on 2 of 4 hamza lines and tied on the rest (pending Mohammed's ear).
23. **Tanwin is a real noon.** Spelled out it's said reliably: مَعًا → مَعَنْ, وَلَيْلٍ → وَلَيْلِنْ, and م before ب (إقلاب). Approved by ear. Automatic with `"tajweed": {"tanwin": true}`.
24. **Shadda on ي/و** = a held glide, then release (عَ-لَيْ-يَ). The spelling options are `"shadda_y": "split"` (عَلَيْ يَ) or `"double"` (عَلَيْيَّ). The old عَلَيْيَ was rejected. Waiting for Mohammed's pick from the al-Ḥuṣarī comparison.
25. **همزة الوصل** drops in joined speech: يَا امْرَأَ → يَمْرَأَ (`"wasl": true`). Waiting for Mohammed's pick.
26. **Heavy letters, heavy ر, ع and قلقلة can't be fixed by spelling.** That's the job of retraining the voice (kaggle/train_voice.ipynb).
27. **Retraining, run 1** (ClArTTS + 6 h al-Ḥuṣarī, rank 32, 3000 steps): improvement stopped at about 2000 steps. Step 3000 roughly tied the original voice. It was better on tanwin and words and worse on shadda and hamza, and its lines came out faster. **Round-trip test:** real ClArTTS and al-Ḥuṣarī recordings were turned into speech tokens and rebuilt by the decoder. Mohammed heard them as 95% the same, and the judge kept 53/53 heavy letters. So the decoder can make these sounds, and the part to train is T3. **Run 2** follows two independent reviews and changes one thing only, the share of Quran recitation: al-Ḥuṣarī weight 0 vs 0.15, both at rank 32 for 2000 steps. It is judged blind by ear (`ar/train/abtest.py`: 12 hard lines, 3 seeds per voice, with the judges used only to drop broken takes). We don't switch voices from line to line inside a poem.
28. **Run 2 blind result (Mohammed's ear, 12 lines, 1–5):** the original voice averaged 3.7 and won 6 lines outright. The ClArTTS-only adapter averaged 3.1, and the mix adapter 3.0 with one gibberish take (v36a). Retraining T3 with LoRA on this data does not help, so it's paused. What's still missing is stress/نبر: a held shadda and ي, ringing ل, ق that doesn't drift toward ك, stronger ر and ع. The best takes show the voice can do it (v59a ظَبْيٍ).
29. **Round 2 blind result (original voice vs SILMA TTS, 3 takes each per line):** the original voice averaged 3.9, and 4.3 when the best of its 3 takes per line is kept. It won 4 lines, tied 7 and lost 1. SILMA averaged 3.3 and had 8 bad takes (gibberish, repeated words, missing shadda). Decision: keep the original Chatterbox voice and make several takes per half-verse. Still asked for: a held shadda, clearer ق ت ر, and purer letters.
30. **Checked against al-Zawzanī and the metre.** Fixes: v9 دَمْعِيَ; v72 بَعْدَ. The pronoun is stretched (هُو / هِي) wherever the ṭawīl needs it: v3, 34, 36, 43, 45, 50, 55, 57, 58, 59, 60, 69, 72, 73. Recension choices follow al-Zawzanī (v32 غَيْرُ, v65 تُزَيَّلِ, v66 يَنْضَحْ), except v57, where the metre requires عَنْ. Run `python ar/metre.py <script>` after any edit; only v10 (kaff) and v27 (hidden alif in اللّه) are known false alarms.
31. **Clean clips and joins (on by default; `"smooth_joins": false` turns it off).** Mohammed heard noise and ticks in the full run, and three causes were found and fixed by ear (verses 1–3, "no noise"):
    - **Junk after the last word.** The voice often keeps going for 0.7–1.9 s after the line ends (buzz, hiss, clicks). The ClArTTS letter judge marks the last letter, and the clip is cut there, keeping a stretched final vowel.
    - **50 Hz hum.** The main reference recording has mains hum, and the voice copies it louder. It's cut with a steep filter below 75 Hz plus narrow notches at 100 and 150 Hz. The stationary hiss is removed per clip (noisereduce).
    - **Clicks from slowing down and from the volume step.** ffmpeg's atempo clicks where sound meets silence, so each clip is slowed on its own with rubberband before joining. Single-pass loudnorm turned up the hiss in every pause, so it now runs in two passes with one steady gain. Short pops at clip edges are turned down (declick), and fades are soft (raised cosine).
    - A faint room tone between clips was tried and rejected: it only added noise.
32. **Pauses and waqf (original verses; `"recite"` in job.json).** Mohammed heard the voice stop where the grammar doesn't allow it, without the waqf form (round 5, 29 Oct). Rules:
    - **No pause inside a half-verse.** A reciter never stops on a vowelled letter mid-phrase, and a pause there breaks the grammar (لَمْ يَعْفُ، رَسْمُهَا: verb cut from its subject) and the metre. Commas, colons, "!" and "..." inside a half are removed; the stretched vowel of a command or call stays (قِفَاا). This replaces rule 11's comma for the original verses.
    - **The end of the first half gets ishbāʿ, never a sukun.** The vowelled letter at the end of the ʿarūḍ and the ḍarb is lengthened (المرشد الوافي; العروض وموسيقا الشعر; المنجد; quoted in Yamama Literary Forum, 2021), and al-Akhfash's Kitāb al-Qawāfī says chanters lengthen line ends. So زِمَامَهُ → زِمَامَهُو, التَّدَلُّلِ → التَّدَلُّلِي. Tanwin and sukun endings stay as written (the metre counts tanwin as ن).
    - Pauses fall only between the halves and between verses. The modern version keeps its punctuation for now (it isn't metrical).
33. **Round 1 timing (approved by ear, B over A, 29 Oct).** Targets from two human reciters (al-Manṣūr and Āl Rashī; `ar/reference.py`): the voice is made at the slower setting (`"cfg_weight": 0.3`), and the rests are 0.56 s between halves and 0.8 s between verses before the 80% slowing (about 0.7 s and 1.0 s heard). Stretching the voice after it is made (more slowing, or stretching the final vowel) blurred the endings and tanwin (tanwin 88% → 71-75% by the judge), so it is not used. The rhyme is held by spelling, not by editing the audio; writing the final letter twice (ـلِيي) was heard as ي ي (Mohammed), so the spelling is still being tested (`ar/endcheck.py` tells one held vowel from two).
Reference for listening: al-Ḥuṣarī's murattal (Tarteel EveryAyah dataset), on verses with the same sounds: إِيَّاكَ (1:5), عَلَيَّ (15:41), امْرَأَتُ (28:9), حَرِيصٌ / رَءُوفٌ رَحِيمٌ (9:128).

## Pronunciation score
`python -m ar.score clips.json`. Every QA report now includes it. It listens with the classical-Arabic listening model and checks each tanwin, shadda, hamza and heavy letter. It catches clear misses (مَعًا heard مَعَ, ع heard as ا), but it's lenient on subtle hamza and can't read slow تجويد recitation. Your ear stays the final judge.

## Audio settings (approved)
- Speed 80% (`tempo 0.8`). 1 second of silence before the voice.
- Pauses (before the speed change): 0.3 s between halves, 0.75 s between verses, 1.3 s between the original and the modern version.
- Trimming: rule 31 (cut at the last letter, 0.08 s kept before the first sound, soft 70 ms / 160 ms fades).
- Music: -10 dB under the voice, ducked lightly while he speaks (threshold 0.05, ratio 2), 2 s fade-in, 3.5 s fade-out, voice starts about 3 s in. Loudness -16 LUFS.

## The judges
- **Cohere-Speech-Tashkeel-2B** transcribes every clip with vowels.
- **diactc-wav2vec2-clartts** (trained on classical recitation) also checks the original verses.
- A clip passes when the judges hear at least 75% of the words. A clip that fails is redone with a different setting (problem-word fixes, then more and less expressive). The best take is kept, and anything still weak is listed in `QA_REPORT.md` for a human ear. When the judges disagree, trust your ear.
