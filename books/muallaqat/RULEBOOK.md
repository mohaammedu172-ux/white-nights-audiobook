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
12. Long sentences run away or get cut off. One half-verse per generation solves this. If a half is still very long, add a comma at a natural breath.

## Audio settings (approved)
- Speed 80% (`tempo 0.8`). 1 second of silence before the voice.
- Pauses (before the speed change): 0.3 s between halves, 0.75 s between verses, 1.3 s between the original and the modern version.
- Gentle trimming: -50 dB threshold, 0.12 s kept before and 0.18 s after, short fades. Aggressive trimming caused ticks and swallowed word starts.
- Music: -10 dB under the voice, ducked lightly while he speaks (threshold 0.05, ratio 2), 2 s fade-in, 3.5 s fade-out, voice starts about 3 s in. Loudness -16 LUFS.

## The judges
- **Cohere-Speech-Tashkeel-2B** transcribes every clip with vowels.
- **diactc-wav2vec2-clartts** (trained on classical recitation) also checks the original verses.
- A clip passes when the judges hear at least 75% of the words. A clip that fails is redone with a different setting (problem-word fixes, then more and less expressive). The best take is kept, and anything still weak is listed in `QA_REPORT.md` for a human ear. When the judges disagree, trust your ear.
