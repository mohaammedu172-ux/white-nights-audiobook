"""Voice body and word emphasis (8 Nov: Mohammed hears the voice as thin and every word as equal).

warmth(a, sr)             low-mid lift (+3 dB around 220 Hz) and gentle 2:1 compression: a fuller, closer voice
emphasise(a, sr, span)    one key word made a little louder (+2.5 dB) and longer (x1.12, one continuous stretch pass)
key_span(seq, word)       where the judge heard that word (start, end in seconds)
"""
import difflib
import re

import numpy as np
import scipy.signal as ss

from .madd import lengthen_map


def _peak(a, sr, f0, gain_db, q=0.8):
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * f0 / sr
    al = np.sin(w) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w), 1 - al * A]
    d = [1 + al / A, -2 * np.cos(w), 1 - al / A]
    return ss.lfilter(np.array(b) / d[0], np.array(d) / d[0], a)


def warmth(a, sr, lift_db=3.0, ratio=2.0, thr_db=-24.0):
    y = _peak(a.astype(np.float64), sr, 220, lift_db)
    env = np.sqrt(np.convolve(y ** 2, np.ones(int(0.02 * sr)) / int(0.02 * sr), mode='same')) + 1e-9
    lvl = 20 * np.log10(env / (np.abs(y).max() + 1e-9))
    over = np.maximum(lvl - thr_db, 0)
    g = 10 ** (-(over - over / ratio) / 20)
    g = np.convolve(g, np.ones(int(0.01 * sr)) / int(0.01 * sr), mode='same')
    y = y * g
    return (y / (np.abs(y).max() + 1e-9) * np.abs(a).max()).astype(np.float32)


def key_span(seq, word):
    words, cur = [], []
    for t, tm in seq:
        if t in ('|', ' '):
            if cur:
                words.append(cur); cur = []
        else:
            cur.append((t, tm))
    if cur:
        words.append(cur)
    bare = lambda s: re.sub('[ً-ْٰ]', '', s)
    target = bare(word)
    best = max(range(len(words)), key=lambda i: difflib.SequenceMatcher(None, bare(''.join(t for t, _ in words[i])), target).ratio())
    s = words[best][0][1]
    e = words[best + 1][0][1] if best + 1 < len(words) else words[best][-1][1] + 0.15
    return s, e


def emphasise(a, sr, span, gain_db=2.5, longer=1.12):
    s, e = span
    i, j = int(s * sr), int(e * sr)
    env = np.ones(len(a), np.float32)
    n = int(0.03 * sr)
    seg = np.ones(max(1, j - i), np.float32) * 10 ** (gain_db / 20)
    seg[:n] = np.linspace(1, seg[0], min(n, len(seg)))[:len(seg[:n])]
    seg[-n:] = np.linspace(seg[-1], 1, min(n, len(seg)))[-len(seg[-n:]):]
    env[i:i + len(seg)] = seg[:len(env[i:])]
    y = a * env
    return lengthen_map(y, sr, [(s, e)], longer)
