"""Kokoro with the fixes that came out of listening tests (2026-10-20):

1. Fixed speaking style: Kokoro normally picks its style by text length, so pieces of different length had
   different pace. One style row is used for everything.
2. Hidden lead-in, cut EXACTLY: each line is generated after a lead-in (the previous sentence, or a neutral one)
   so it doesn't start with Kokoro's high, rushed "fresh start". The model-files-v1.1 export reports the time of
   every phoneme, so the lead-in is cut at the first phoneme of the real line (no guessing).
3. Sentence pauses inside a line come from Kokoro's own timings (sentence 0.35 s, clause 0.1 s), so short
   sentences are neither glued together nor chopped apart.
4. Gentle trim: only true silence is cut, so first sounds stay whole.
"""
import os
import numpy as np

SR = 24000
MODEL_DIR = "/tmp/wn/kokoro11"
RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/"
NEUTRAL = "I remember it well."
SENTENCE_PAUSE, CLAUSE_PAUSE = 0.35, 0.1
_k = None


def model():
    global _k
    if _k is None:
        import urllib.request
        from kokoro_onnx import Kokoro
        os.makedirs(MODEL_DIR, exist_ok=True)
        for f in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
            if not os.path.exists(f"{MODEL_DIR}/{f}"): urllib.request.urlretrieve(RELEASE + f, f"{MODEL_DIR}/{f}")
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

    def _timed(self, text):
        return model().create_timed(text, self.style, speed=self.speed, lang=self.lang, trim=False,
                                    sentence_pause=SENTENCE_PAUSE, clause_pause=CLAUSE_PAUSE)

    def _phonemes(self, text):
        return model()._prepare(text, self.style, self.speed, self.lang, False, SENTENCE_PAUSE, CLAUSE_PAUSE)[1]

    def plain(self, text):
        return soft_trim(self._timed(text)[0])

    def say(self, text, lead_in=None):
        """Returns (audio, ok). ok=False means the lead-in could not be cut exactly and the plain take is used."""
        lead_in = lead_in or NEUTRAL
        pl, pa = self._phonemes(lead_in), self._phonemes(lead_in + " " + text)
        if not pa.startswith(pl): return self.plain(text), False
        audio, sr, t = self._timed(lead_in + " " + text)
        seq = "".join(x.phoneme for x in t)
        if not seq.startswith(pl) or len(t) <= len(pl): return self.plain(text), False
        i = len(pl)
        while i < len(t) and not t[i].phoneme.strip(): i += 1               # skip the space after the lead-in
        if i >= len(t): return self.plain(text), False
        gap_start = t[len(pl) - 1].end                                       # end of the lead-in's last mark
        start = t[i].start
        cut = max(gap_start, start - 0.04)                                   # inside the silence, never inside a word
        seg = audio[int(cut * SR):].astype(np.float64).copy()
        f = min(int(0.02 * SR), max(1, int((start - cut) * SR)))
        seg[:f] *= np.linspace(0, 1, f)
        i_end = np.where(np.abs(seg) > 0.001)[0]
        seg = seg[: i_end[-1] + int(0.15 * SR)] if len(i_end) else seg
        g = int(0.02 * SR); seg[-g:] *= np.linspace(1, 0, g)
        return seg, True


def last_sentences(text, n=1):
    import re
    return " ".join(re.split(r'(?<=[.!?])\s+', text.strip())[-n:])
