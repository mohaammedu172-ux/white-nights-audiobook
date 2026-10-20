"""Per-line quality checks. A take passes only if every check passes; failures are retaken, then flagged.

clarity   share of the script's words that speech recognition hears (word alignment, 0-1)
rate      words per second; flags takes far faster/slower than that speaker's usual pace
length    duration far beyond what the text needs = the model rambled, looped or added sounds
"""
import difflib, re
import numpy as np, soundfile as sf

_asr = None
norm = lambda s: re.sub(r"[^a-z0-9' ]", " ", s.lower()).split()


def asr():
    global _asr
    if _asr is None:
        import whisper
        _asr = whisper.load_model("small", device="cuda")
    return _asr


def speech_span(y, sr, thr=0.01):
    idx = np.where(np.abs(y) > thr)[0]
    return (idx[0], idx[-1]) if len(idx) else (0, len(y))


def check(path, text):
    y, sr = sf.read(path)
    a, b = speech_span(y, sr); dur = (b - a) / sr
    heard = asr().transcribe(path, language="en", condition_on_previous_text=False)["text"].strip()
    want, got = norm(text), norm(heard)
    sm = difflib.SequenceMatcher(None, want, got, autojunk=False)
    clarity = sum(m.size for m in sm.get_matching_blocks()) / max(1, len(want))
    extra = max(0, len(got) - len(want)) / max(1, len(want))          # words heard that are not in the script
    return dict(clarity=round(clarity, 3), extra=round(extra, 3), seconds=round(dur, 2),
                rate=round(len(want) / max(dur, 0.1), 2), heard=heard)


def verdict(r, rates, min_clarity=0.85, max_extra=0.25):
    """rates = typical words/sec for this speaker. Returns list of problems (empty = pass)."""
    why = []
    if r["clarity"] < min_clarity: why.append(f"unclear ({r['clarity']:.2f})")
    if r["extra"] > max_extra: why.append(f"extra words/sounds ({r['extra']:.2f})")
    med = float(np.median(rates)) if rates else r["rate"]
    if r["rate"] > med * 1.35: why.append(f"rushed ({r['rate']:.1f} w/s vs {med:.1f})")
    if r["rate"] < med * 0.65: why.append(f"dragging ({r['rate']:.1f} w/s vs {med:.1f})")
    return why
