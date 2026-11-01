"""Tone matching (D2/D4, issue: "muffled / far away"): the voice comes out duller in some takes than others (energy
above 4 kHz varies by ~10 dB from take to take: median -27 dB, 32 of 144 kept clips below -30 dB). A dull take
next to a bright one sounds muffled or distant, and the change at a join makes the poem sound like separate blocks.
Each clip gets a gentle high shelf that brings its brightness to one target, so every line has the same colour."""
import numpy as np
import scipy.signal as ss

TARGET_DB = -26.5  # median brightness of the kept clips (run of 30 Oct)


def brightness(a, sr, cut=4000):
    a = a[np.abs(a) > 0.01 * (np.abs(a).max() + 1e-9)]
    if len(a) < sr // 10:
        return None
    f, p = ss.welch(a, sr, nperseg=2048)
    return float(10 * np.log10(p[f > cut].sum() / p.sum()))


def high_shelf(a, sr, gain_db, f0=3500, q=0.7):
    """RBJ cookbook high shelf."""
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * f0 / sr
    al = np.sin(w) / (2 * q)
    c = np.cos(w)
    b = [A * ((A + 1) + (A - 1) * c + 2 * np.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * c),
         A * ((A + 1) + (A - 1) * c - 2 * np.sqrt(A) * al)]
    d = [(A + 1) - (A - 1) * c + 2 * np.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - 2 * np.sqrt(A) * al]
    return ss.lfilter(np.array(b) / d[0], np.array(d) / d[0], a).astype(np.float32)


def match(a, sr, target=TARGET_DB, limit=6.0):
    """Bring the clip's brightness to the target (at most +-limit dB of shelf)."""
    b = brightness(a, sr)
    if b is None:
        return a, 0.0
    g = float(np.clip(target - b, -limit, limit))
    # the shelf only moves part of the >4 kHz band, so iterate once to land near the target
    y = high_shelf(a, sr, g)
    b2 = brightness(y, sr)
    if b2 is not None and abs(target - b2) > 1:
        g = float(np.clip(g + (target - b2), -limit * 1.5, limit * 1.5))
        y = high_shelf(a, sr, g)
    return y, g
