"""Section reports (scorecard test plan, sections 1 and 2): measure every word and letter of a full run.
    python -m ar.sections RUN_DIR [--part original]  -> RUN_DIR/sections.json + SECTIONS.md
RUN_DIR holds state.json and the clip wavs (a run's out dir, or merged shard artifacts).

Section 1, grammar and text: words dropped, added or repeated (C3); the vowel on each word's last letter, i.e. case
  and mood endings (C1); pronoun suffixes (E6); dual and plural endings (E5); vowels inside the word, i.e. verb and
  noun patterns (C2, E1); tanwin heard as tanwin (B2 cross-check).
Section 2, letters: every written consonant vs what the letter recogniser heard, with a score per letter and the
  swaps it made (A1-A16).
The recogniser is a machine listener (ClArTTS, classical recitation). It is strict and sometimes wrong, so the scores
are best read as relative: which letters and endings fail most often.
"""
import argparse, collections, difflib, glob, json, os, re, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ar.autojudge import hear, norm, MARKS

SUFFIX_PRON = re.compile(r'(ه|ها|هما|هم|هن|ك|كما|كم|كن|نا|ي)$')
DUAL_PLURAL = re.compile(r'(ان|ين|ون|ات|اتي)$')


def strip_added_long(t):
    """Take out the long letters we add for recitation (sila هُو / هِي, ishbāʿ, the long rhyme ـِي) and the doubled
    vowel letters of emphasis (قِفَاا), so the comparison is against the grammar, not the recitation spelling."""
    t = re.sub(r'(ُ)و(?=\s|$)', r'\1', t)
    t = re.sub(r'(ِ)ي(?=\s|$)', r'\1', t)
    t = re.sub(r'اا', 'ا', t)
    return t


def words_with_marks(t):
    out = []
    for w in norm(t).split():
        letters, marks = [], []
        for ch in w:
            if ch in MARKS:
                if marks:
                    marks[-1] += ch
            else:
                letters.append(ch); marks.append('')
        if letters:
            out.append((''.join(letters), marks))
    return out


def same_mark(a, b):
    return set(a) == set(b)


def analyse(ref, heard, acc):
    R, H = words_with_marks(strip_added_long(ref)), words_with_marks(strip_added_long(heard))
    sm = difflib.SequenceMatcher(None, [w for w, _ in R], [w for w, _ in H], autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'delete':
            acc['words_dropped'] += i2 - i1
        elif op == 'insert':
            acc['words_added'] += j2 - j1
        elif op == 'replace':
            acc['words_changed'] += max(i2 - i1, j2 - j1)
        acc['words_total'] += i2 - i1
        if op != 'equal':
            continue
        for k in range(i2 - i1):
            (rw, rm), (hw, hm) = R[i1 + k], H[j1 + k]
            end_r, end_h = rm[-1], hm[-1]
            if end_r:
                cat = 'pronoun_suffix' if SUFFIX_PRON.search(rw) and len(rw) > 2 else \
                      'dual_plural' if DUAL_PLURAL.search(rw) and len(rw) > 3 else 'case_ending'
                acc[cat + '_total'] += 1
                acc[cat + '_ok'] += same_mark(end_r, end_h)
                if any(c in end_r for c in 'ًٌٍ'):
                    acc['tanwin_total'] += 1
                    acc['tanwin_ok'] += same_mark(end_r, end_h)
            for a, b in zip(rm[:-1], hm[:-1]):
                if a:
                    acc['inner_vowel_total'] += 1
                    acc['inner_vowel_ok'] += same_mark(a, b)
    # letters, across the whole half-verse
    rl = ''.join(w for w, _ in R)
    hl = ''.join(w for w, _ in H)
    sm = difflib.SequenceMatcher(None, rl, hl, autojunk=False)
    per, swaps = acc['letters'], acc['swaps']
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        for k in range(i1, i2):
            per[rl[k]][1] += 1
        if op == 'equal':
            for k in range(i1, i2):
                per[rl[k]][0] += 1
        elif op == 'replace':
            for a, b in zip(rl[i1:i2], hl[j1:j2]):
                swaps[f'{a}→{b}'] += 1


LONG_AFTER = {'ا': 'َ', 'و': 'ُ', 'ي': 'ِ'}


def ref_letters(t):
    """Each written letter with its marks, in order (spaces dropped): [(letter, marks), ...]."""
    out = []
    for ch in norm(t).replace(' ', ''):
        if ch in MARKS:
            if out:
                out[-1] = (out[-1][0], out[-1][1] + ch)
        else:
            out.append((ch, ''))
    return out


def timing(ref, seq, acc):
    """Section 3 timings from the letter recogniser: each letter's onset, matched to the written letter.
    B5 vowel length: a consonant followed by a long vowel letter (madd) should last clearly longer than one with a
      short vowel. Recorded as the ratio of their median durations. Reference: the ClArTTS reader (human, classical
      prose) measures 1.33; recitation should be at least that. No poetry-recital reference yet.
    B1 shadda hold, B4 nasal (غنة) hold: duration of a doubled letter, and of doubled ن/م, vs the median letter."""
    R = ref_letters(ref)
    H = [(t, tm) for t, tm in seq if t not in ('|', ' ') and not all(c in MARKS for c in t)]
    if len(H) < 4:
        return
    rl, hl = ''.join(l for l, _ in R), ''.join(t for t, _ in H)
    dur_h = [H[i + 1][1] - H[i][1] for i in range(len(H) - 1)] + [None]
    sm = difflib.SequenceMatcher(None, rl, hl, autojunk=False)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            i, j = blk.a + k, blk.b + k
            d = dur_h[j]
            if d is None or i + 1 >= len(R):
                continue
            letter, marks = R[i]
            nxt, nxt_marks = R[i + 1]
            # consonant + its vowel: long if the next written letter is the matching long vowel letter
            if marks and marks[-1] in 'َُِ' and 'ّ' not in marks:
                if LONG_AFTER.get(nxt) == marks[-1] and not nxt_marks:
                    d2 = dur_h[j + 1] if j + 1 < len(dur_h) and dur_h[j + 1] is not None and hl[j + 1:j + 2] == nxt else 0
                    acc['syl_long'].append(d + d2)
                elif nxt not in LONG_AFTER or nxt_marks:
                    acc['syl_short'].append(d)
            if 'ّ' in marks:
                (acc['hold_nasal'] if letter in 'نم' else acc['hold_shadda']).append(d)
            acc['all_letters'].append(d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run_dir')
    ap.add_argument('--part', default='original')
    a = ap.parse_args()
    state = json.load(open(os.path.join(a.run_dir, 'state.json')))
    wav_of = {os.path.basename(p): p for p in glob.glob(os.path.join(a.run_dir, '**', '*.wav'), recursive=True)}
    acc = collections.defaultdict(int)
    acc['letters'] = collections.defaultdict(lambda: [0, 0])
    acc['swaps'] = collections.Counter()
    tim = collections.defaultdict(list)
    n = 0
    for key, s in sorted(state.items()):
        if s['part'] != a.part or s.get('chosen') not in wav_of:
            continue
        heard, _, _, seq = hear(wav_of[s['chosen']], timings=True)
        from ar import text_rules as tr
        analyse(tr.split_tag(s['script'])[1], heard, acc)
        timing(tr.split_tag(s['script'])[1], seq, tim)
        n += 1
    pct = lambda ok, tot: round(100 * acc[ok] / acc[tot]) if acc[tot] else None
    sec1 = {
        'C3 words': {'dropped': acc['words_dropped'], 'added': acc['words_added'], 'changed': acc['words_changed'],
                     'of': acc['words_total']},
        'C1 case and mood endings %': pct('case_ending_ok', 'case_ending_total'),
        'E6 pronoun suffixes %': pct('pronoun_suffix_ok', 'pronoun_suffix_total'),
        'E5 dual and plural endings %': pct('dual_plural_ok', 'dual_plural_total'),
        'C2/E1 vowels inside words %': pct('inner_vowel_ok', 'inner_vowel_total'),
        'B2 tanwin %': pct('tanwin_ok', 'tanwin_total'),
    }
    letters = {l: {'ok%': round(100 * ok / tot), 'n': tot} for l, (ok, tot) in acc['letters'].items() if tot >= 5}
    import numpy as np
    med = lambda x: float(np.median(x)) if x else None
    ml = med(tim['all_letters'])
    sec3 = {
        'B5 long vs short vowel (duration ratio; human ClArTTS prose reading 1.33)': round(med(tim['syl_long']) / med(tim['syl_short']), 2)
            if tim['syl_long'] and tim['syl_short'] else None,
        'B1 shadda hold vs ordinary letter (human prose 1.4)': round(med(tim['hold_shadda']) / ml, 2) if tim['hold_shadda'] and ml else None,
        'B4 doubled ن/م (ghunna) hold vs ordinary letter (few cases; unreliable)': round(med(tim['hold_nasal']) / ml, 2) if tim['hold_nasal'] and ml else None,
        'counts': {k: len(v) for k, v in tim.items()},
    }
    out = {'clips': n, 'section1': sec1, 'section3': sec3, 'section2_letters': dict(sorted(letters.items(), key=lambda kv: kv[1]['ok%'])),
           'section2_swaps': dict(acc['swaps'].most_common(25))}
    json.dump(out, open(os.path.join(a.run_dir, 'sections.json'), 'w'), ensure_ascii=False, indent=1)
    md = [f'# Sections 1 and 2 ({a.part}, {n} half-verses)', '', '## Section 1: grammar and text', '',
          '| Check | Result |', '|---|---|']
    md += [f'| {k} | {v} |' for k, v in sec1.items()]
    md += ['', '## Section 3: tajwid timing', '', '| Check | Result |', '|---|---|']
    md += [f'| {k} | {v} |' for k, v in sec3.items()]
    md += ['', '## Section 2: letters (weakest first)', '', '| Letter | Heard right | Occurrences |', '|---|---|---|']
    md += [f'| {l} | {v["ok%"]}% | {v["n"]} |' for l, v in out['section2_letters'].items()]
    md += ['', 'Most common swaps: ' + ', '.join(f'{k} ×{v}' for k, v in out['section2_swaps'].items())]
    open(os.path.join(a.run_dir, 'SECTIONS.md'), 'w').write('\n'.join(md) + '\n')
    print('\n'.join(md))


if __name__ == '__main__':
    main()
