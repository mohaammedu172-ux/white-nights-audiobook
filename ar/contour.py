"""Pitch shape from the reference reciters (issue: flat pitch, every line, 1 Nov).

The reciters are used only to MEASURE: how their pitch moves across a half-verse, in semitones relative to their
own median, sampled at fixed points along the half (0 = first sound, 1 = last). Nothing of their voice is copied.
Our approved take keeps its words, timing and voice; WORLD changes only its pitch line toward that shape.

shape(path)                         -> relative pitch at N points (semitones, median 0)
reshape(a, sr, target, strength, from_pos)  -> our take with its pitch moved toward the target shape
"""
import numpy as np
import pyworld as pw

N = 12


def _f0(a, sr):
    x = a.astype(np.float64)
    f0, t = pw.harvest(x, sr, f0_floor=60, f0_ceil=400, frame_period=5.0)
    return f0, t


def _voiced_span(f0):
    v = np.flatnonzero(f0 > 0)
    return (v[0], v[-1]) if len(v) > 10 else (None, None)


def shape(a, sr, n=N):
    """Relative pitch (semitones from the half's median) at n evenly spaced points over the voiced span."""
    f0, _ = _f0(a, sr)
    i, j = _voiced_span(f0)
    if i is None:
        return None
    st = np.full(len(f0), np.nan)
    st[f0 > 0] = 12 * np.log2(f0[f0 > 0] / np.median(f0[f0 > 0]))
    pts = np.linspace(i, j, n + 1)
    out = []
    for k in range(n):
        seg = st[int(pts[k]):int(pts[k + 1]) + 1]
        seg = seg[~np.isnan(seg)]
        out.append(np.median(seg) if len(seg) else np.nan)
    out = np.array(out)
    if np.isnan(out).all():
        return None
    idx = np.arange(n)
    ok = ~np.isnan(out)
    s = np.interp(idx, idx[ok], out[ok])
    s = s - 12 * np.round(s / 12)  # octave jumps of the pitch tracker are errors, not melody
    return s - np.median(s)


def reshape(a, sr, target, strength=1.0, from_pos=0.0, limit=3.0):
    """Move our pitch line toward `target` (relative shape, semitones) by `strength`.
    Only the part of the half after `from_pos` (0-1) changes; the change fades in over the first 10%."""
    f0, t = _f0(a, sr)
    x = a.astype(np.float64)
    sp = pw.cheaptrick(x, f0, t, sr)
    ap = pw.d4c(x, f0, t, sr)
    i, j = _voiced_span(f0)
    if i is None:
        return a
    ours = shape(a, sr, len(target))
    delta = np.clip((np.asarray(target) - ours) * strength, -limit, limit)
    pos = np.clip((np.arange(len(f0)) - i) / max(1, j - i), 0, 1)
    centers = (np.arange(len(target)) + 0.5) / len(target)
    d = np.interp(pos, centers, delta)
    ramp = np.clip((pos - from_pos) / 0.1, 0, 1)
    d = d * ramp
    # smooth so the line moves like a voice, not in steps
    k = 21
    d = np.convolve(np.pad(d, k // 2, mode='edge'), np.ones(k) / k, mode='valid')
    f1 = np.where(f0 > 0, f0 * 2 ** (d / 12), 0)
    y = pw.synthesize(f1, sp, ap, sr, frame_period=5.0)[:len(a)]
    y = np.pad(y, (0, len(a) - len(y)))
    # keep the original sound wherever the pitch is not changed (unvoiced letters, pauses, untouched part):
    # WORLD resynthesis adds a faint breathiness there (+1 to +4 dB of noise, measured 8 Nov)
    m = ((f0 > 0) & (np.abs(d) > 0.05)).astype(float)
    m = np.convolve(m, np.ones(5) / 5, mode='same')  # ~25 ms crossfades
    m = np.interp(np.arange(len(a)), t * sr, m)
    return (a * (1 - m) + y * m).astype(np.float32)
