"""Qalqala (criterion B6) at the sound level: lift the release burst of ق ط ب ج د when it carries a sukun.

Spelling did not help for a word-final stop (قَدْ: all versions bad, 1 Nov). Here the letter judge's timings place
the stop letter; inside the next ~150 ms the sharpest rise in energy is taken as the release, and a short
raised-cosine gain (about 60 ms) is applied there. Nothing else in the line changes."""
import numpy as np

QAL = 'قطبجد'


def spots(seq, only_words=None):
    """Times (letter onset, next symbol onset) of qalqala letters with sukun or at a word end.
    only_words: bare-letter words to limit it to (e.g. {'قد', 'وقد'})."""
    words, cur = [], []
    for t, tm in seq:
        if t in ('|', ' '):
            if cur:
                words.append(cur); cur = []
        else:
            cur.append((t, tm))
    if cur:
        words.append(cur)
    out = []
    flat_next = [tm for w in words for _, tm in w] + [None]
    k = 0
    for w in words:
        bare = ''.join(t for t, _ in w if t not in 'ًٌٍَُِّْ')
        for i, (t, tm) in enumerate(w):
            nxt = w[i + 1][0] if i + 1 < len(w) else None
            if t in QAL and (nxt == 'ْ' or nxt is None or (i == len(w) - 1)):
                if only_words is None or bare in only_words:
                    end = flat_next[k + 1]
                    out.append((tm, end if end is not None else tm + 0.15))
            k += 1
    return out


def lift(a, sr, places, db=6.0, look=0.15, width=0.06):
    a = a.astype(np.float32).copy()
    hop = int(0.002 * sr)
    g = 10 ** (db / 20)
    for s, e in places:
        i, j = int(s * sr), min(len(a), int((s + look) * sr))  # the judge's next symbol is often the sukun mark itself, so look a fixed window
        seg = a[i:j]
        if len(seg) < 4 * hop:
            continue
        en = np.array([np.sum(seg[x:x + hop] ** 2) for x in range(0, len(seg) - hop, hop)]) + 1e-9
        rise = np.diff(10 * np.log10(en))
        c = i + (int(np.argmax(rise)) + 1) * hop  # the release
        w = int(width * sr)
        lo, hi = max(0, c - w // 3), min(len(a), c + w)
        env = 1 + (g - 1) * np.sin(np.linspace(0, np.pi, hi - lo)) ** 2
        a[lo:hi] *= env
    return a
