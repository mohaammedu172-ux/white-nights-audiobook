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
Reference for listening: al-Ḥuṣarī's murattal (Tarteel EveryAyah dataset), on verses with the same sounds: إِيَّاكَ (1:5), عَلَيَّ (15:41), امْرَأَتُ (28:9), حَرِيصٌ / رَءُوفٌ رَحِيمٌ (9:128).

## Pronunciation score
`python -m ar.score clips.json`. Every QA report now includes it. It listens with the classical-Arabic listening model and checks each tanwin, shadda, hamza and heavy letter. It catches clear misses (مَعًا heard مَعَ, ع heard as ا), but it's lenient on subtle hamza and can't read slow تجويد recitation. Your ear stays the final judge.

## Audio settings (approved)
- Speed 80% (`tempo 0.8`). 1 second of silence before the voice.
- Pauses (before the speed change): 0.3 s between halves, 0.75 s between verses, 1.3 s between the original and the modern version.
- Gentle trimming: -50 dB threshold, 0.12 s kept before and 0.18 s after, short fades. Aggressive trimming caused ticks and swallowed word starts.
- Music: -10 dB under the voice, ducked lightly while he speaks (threshold 0.05, ratio 2), 2 s fade-in, 3.5 s fade-out, voice starts about 3 s in. Loudness -16 LUFS.

## The judges
- **Cohere-Speech-Tashkeel-2B** transcribes every clip with vowels.
- **diactc-wav2vec2-clartts** (trained on classical recitation) also checks the original verses.
- A clip passes when the judges hear at least 75% of the words. A clip that fails is redone with a different setting (problem-word fixes, then more and less expressive). The best take is kept, and anything still weak is listed in `QA_REPORT.md` for a human ear. When the judges disagree, trust your ear.
