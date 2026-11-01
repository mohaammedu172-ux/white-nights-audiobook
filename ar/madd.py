"""Long vowels (madd, criterion B5): lengthen only the long vowel sounds inside a half-verse, after the voice is made.

The voice says long vowels too short (long vs short 1.29x; reciters 1.67-1.75x). Slowing the whole clip blurred the
endings and tanwin (rejected in round 1), so here only the stretch of sound where the letter judge hears a long
vowel (ا after fatha, و after damma, ي after kasra) is slowed, with short crossfades. Consonants, endings and the
last word (the rhyme, whose hold is a separate issue) are left alone."""
import numpy as np

from .assemble import stretch

PAIR = {'ا': 'َ', 'ى': 'َ', 'و': 'ُ', 'ي': 'ِ'}


def long_spans(seq, max_len=0.35):
    """(start, end) times of long vowels, from hear(..., timings=True) symbols. The last word is skipped."""
    words, cur = [], []
    for t, tm in seq:
        if t in ('|', ' '):
            if cur:
                words.append(cur); cur = []
        else:
            cur.append((t, tm))
    if cur:
        words.append(cur)
    flat = [(t, tm, wi) for wi, w in enumerate(words) for t, tm in w]
    last = len(words) - 1
    out = []
    for i in range(1, len(flat) - 1):
        t, tm, wi = flat[i]
        if wi == last or t not in PAIR or flat[i - 1][0] != PAIR[t]:
            continue
        end = flat[i + 1][1]
        if 0.03 < end - tm <= max_len:
            out.append((tm, end))
    return out


def lengthen(a, sr, spans, factor=1.4, xf=0.012):
    """Slow each span by `factor` (1.4 = 40% longer) and splice it back with equal-power crossfades."""
    if not spans:
        return a
    n = int(xf * sr)
    out, pos = [], 0
    for s, e in spans:
        i, j = int(s * sr), int(e * sr)
        if i - n < pos or j + n > len(a):
            continue
        seg = stretch(a[i - n:j + n].astype(np.float32), sr, 1 / factor)
        out.append(a[pos:i].copy())  # its last n samples overlap the stretched copy's first n
        out.append(seg)
        pos = j  # the next piece's first n samples overlap the stretched copy's last n
    out.append(a[pos:])
    # crossfade at every joint
    res = out[0]
    for piece in out[1:]:
        k = min(n, len(res), len(piece))
        if k > 0:
            w = np.sin(np.linspace(0, np.pi / 2, k)) ** 2
            res = np.r_[res[:-k], res[-k:] * (1 - w) + piece[:k] * w, piece[k:]]
        else:
            res = np.r_[res, piece]
    return res


def lengthen_map(a, sr, spans, factor=1.3, block=256):
    """Attempt 2: the same lengthening in ONE continuous pass of the stretcher (real-time mode, its speed changed
    while it runs: slower inside each long vowel, normal elsewhere), so there are no splices to tick. Needs pylibrb."""
    import pylibrb
    if not spans:
        return a
    O = pylibrb.Option
    st = pylibrb.RubberBandStretcher(sr, 1, O.PROCESS_REALTIME | O.ENGINE_FINER | O.FORMANT_PRESERVED
                                     | O.SMOOTHING_ON, initial_time_ratio=1.0)
    pad = st.get_preferred_start_pad()
    delay = st.get_start_delay()
    x = np.r_[np.zeros(pad, np.float32), a.astype(np.float32), np.zeros(int(0.3 * sr), np.float32)]
    inside = np.zeros(len(x), bool)
    for s, e in spans:
        inside[pad + int(s * sr):pad + int(e * sr)] = True
    out, pos = [], 0
    while pos < len(x):
        blk = x[pos:pos + block]
        st.time_ratio = factor if inside[pos:pos + len(blk)].mean() > 0.5 else 1.0
        st.process(blk[None, :].copy(), final=pos + block >= len(x))
        pos += block
        n = st.available()
        if n > 0:
            out.append(st.retrieve(n)[0])
    while True:
        n = st.available()
        if n <= 0:
            break
        out.append(st.retrieve(n)[0])
    y = np.concatenate(out)[delay:]
    want = len(a) + sum(int((e - s) * sr * (factor - 1)) for s, e in spans)
    return y[:want]
