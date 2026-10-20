"""Kokoro with three fixes that came out of listening tests (2026-10-20):

1. Fixed speaking style: Kokoro normally picks its style by text length, so pieces of different length had
   different pace. One style row is used for everything.
2. Hidden lead-in: each piece is generated after a lead-in (the previous sentence, or a neutral one) which is
   then cut off, so no piece starts with Kokoro's high, rushed "fresh start".
3. Gentle trim: only true silence is cut, so first sounds stay whole.

The cut point is found by matching the start of a plain take inside the lead-in take (DTW on MFCCs).
Every cut is checked: if the cut piece is much shorter/longer than the plain take, the plain take is used and the
line is flagged.
"""
import os, re
import numpy as np, librosa

SR, HOP = 24000, 240
MODEL_DIR = "/tmp/wn"
NEUTRAL = "I remember it well."
NEUTRALS = ["I remember it well.", "It was late, and the street was quiet.", "And so it went on."]
INNER_PAUSE = {"!": 0.35, "?": 0.35, ".": 0.45, "…": 0.55}            # between sentences of one line
_k = None


def model():
    global _k
    if _k is None:
        import urllib.request
        from kokoro_onnx import Kokoro
        base = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
        os.makedirs(MODEL_DIR, exist_ok=True)
        for f in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
            if not os.path.exists(f"{MODEL_DIR}/{f}"): urllib.request.urlretrieve(base + f, f"{MODEL_DIR}/{f}")
        _k = Kokoro(f"{MODEL_DIR}/kokoro-v1.0.onnx", f"{MODEL_DIR}/voices-v1.0.bin")
    return _k


def soft_trim(y, pre=0.06, post=0.15):
    i = np.where(np.abs(y) > 0.001)[0]
    if not len(i): return y
    a, b = max(0, i[0] - int(pre * SR)), min(len(y), i[-1] + int(post * SR))
    y = y[a:b].astype(np.float64).copy(); f = int(0.02 * SR)
    y[:f] *= np.linspace(0, 1, f); y[-f:] *= np.linspace(1, 0, f)
    return y


class Voice:
    def __init__(self, name, style_row=250, speed=1.0):
        k = model(); base = k.get_voice_style(name)
        self.style = np.repeat(base[style_row][None], len(base), axis=0).astype(np.float32)
        self.lang = "en-gb" if name.startswith("b") else "en-us"; self.speed = speed

    def plain(self, text):
        return soft_trim(model().create(text, self.style, speed=self.speed, lang=self.lang, trim=False)[0])

    def say_robust(self, text, lead_ins):
        """Try each lead-in until a cut passes the check; plain take only if all fail."""
        for li in lead_ins:
            y, ok = self.say(text, li)
            if ok: return y, True
        return self.plain(text), False

    def say_line(self, text, prev_text=None):
        """A whole script line: every sentence generated with its own lead-in, joined with natural pauses."""
        sents = [x for x in re.split(r'(?<=[.!?…])\s+', text.strip()) if x]
        parts, ok_all, before = [], True, prev_text
        for i, s in enumerate(sents):
            lead = ([last_sentences(before)] if before else []) + NEUTRALS
            y, ok = self.say_robust(s, lead); ok_all &= ok
            if i:
                end = sents[i - 1].rstrip()[-1]; end = "…" if sents[i - 1].rstrip().endswith("...") else end
                parts.append(np.zeros(int(INNER_PAUSE.get(end, 0.4) * SR)))
            parts.append(y); before = s
        return np.concatenate(parts), ok_all

    def say(self, text, lead_in=None):
        """Returns (audio, ok). lead_in=None uses the neutral lead-in."""
        lead_in = lead_in or NEUTRAL
        alone, both, ctx = self.plain(text), self.plain(lead_in + " " + text), self.plain(lead_in)
        mf = lambda y: librosa.feature.mfcc(y=y.astype("float32"), sr=SR, n_mfcc=20, hop_length=HOP)
        lo = int(0.6 * len(ctx))
        X, Y = mf(alone[:int(0.8 * SR)]), mf(both[lo:lo + int(0.8 * len(ctx)) + 2 * SR])
        _, wp = librosa.sequence.dtw(X, Y, subseq=True)
        s = lo + wp[-1][1] * HOP
        seg = both[max(0, s - int(0.04 * SR)):].copy(); f = int(0.03 * SR); seg[:f] *= np.linspace(0, 1, f) ** 2
        # check: the cut piece vs the plain take. Read in context, a short sentence is naturally shorter
        # (no end-of-utterance slow-down), so short pieces get a wider lower bound.
        ratio = len(seg) / max(1, len(alone)); d = len(alone) / SR
        lo_ok = 0.6 if d < 1.5 else (0.78 if d < 2.5 else 0.85)
        if not lo_ok <= ratio <= 1.12: return alone, False
        return seg, True


def last_sentences(text, n=1):
    return " ".join(re.split(r'(?<=[.!?])\s+', text.strip())[-n:])
