"""Tick detector (D5): short clicks inside speech, such as splice ticks. A tick is a 1-3 ms burst of high-frequency
energy far above the few milliseconds around it. Calibrated on the long-vowel check of 1 Nov (ear-flagged takes)."""
import numpy as np
import scipy.signal as ss


def ticks(a, sr, hp=4000, frame=0.001, ctx=0.012, jump_db=12, min_db=-60):
    if a.ndim > 1:
        a = a.mean(1)
    b, c = ss.butter(4, hp / (sr / 2), 'high')
    h = ss.lfilter(b, c, a)
    w = max(1, int(frame * sr))
    e = 10 * np.log10(np.add.reduceat(h ** 2, np.arange(0, len(h) - w, w)) / w + 1e-12)
    k = int(ctx / frame)
    med = ss.medfilt(e, 2 * k + 1)
    hit = (e - med > jump_db) & (e > min_db)
    # count runs, not frames
    idx = np.flatnonzero(hit)
    if not len(idx):
        return []
    runs = np.split(idx, np.flatnonzero(np.diff(idx) > 3) + 1)
    return [round(r[0] * frame, 3) for r in runs]
