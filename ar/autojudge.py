"""Automatic judge: measures every take on the scorecard criteria a machine can check, so Mohammed only has to make
the final call. Each measure is checked against his past ratings (ar/judge_cal) before it is trusted.

    python -m ar.autojudge take1.wav take2.wav --text "النص المشكول"      -> JSON per take

Measures (higher is better unless marked "lower"):
  letters      letter accuracy (consonants only), from the ClArTTS letter recogniser
  marks        vowel-mark accuracy (fatha, kasra, damma, sukun, shadda, tanwin)
  shadda       share of written shaddas that were heard
  confusions   lower: heavy/light and near-letter swaps heard (ت→ط, ق→ك, س→ص ...)
  hnr          harmonics-to-noise ratio, dB (smooth, clean voice)
  jitter       lower: pitch roughness, %
  shimmer      lower: loudness roughness, %
  pitch_range  pitch range over the line, semitones (5th-95th percentile): flat lines score low
  pitch_move   pitch movement, semitones standard deviation
  rate         letters per second of speech (pace)
  pauses       lower: silences longer than 0.18 s inside the line
  tail         lower: seconds of sound after the last letter (junk the voice adds)
  noise        lower: noise floor in the quietest parts, dB
  stress_peak  how far the most prominent word stands out (loudness dB + pitch semitones): flat = low
  stress_shape spread of word prominence: every word the same weight = low
  shadda_hold  a doubled letter held relative to an ordinary letter (> 1 = held)
"""
import argparse, difflib, json, re
import numpy as np, librosa

MARKS = 'ًٌٍَُِّْ'
NEAR = {('ت', 'ط'), ('ط', 'ت'), ('ق', 'ك'), ('ك', 'ق'), ('س', 'ص'), ('ص', 'س'), ('د', 'ض'), ('ض', 'د'),
        ('ذ', 'ظ'), ('ظ', 'ذ'), ('ذ', 'ز'), ('ث', 'س'), ('ح', 'ه'), ('ه', 'ح'), ('ع', 'ء'), ('ء', 'ع'), ('ع', 'ا'),
        ('غ', 'ر'), ('ر', 'غ'), ('ض', 'ظ'), ('ظ', 'ض')}
_M = {}


def _ctc():
    if not _M:
        import torch
        from transformers import AutoProcessor, Wav2Vec2ForCTC
        repo = "rufaelfekadu/diactc-wav2vec2-clartts"
        _M['p'] = AutoProcessor.from_pretrained(repo)
        _M['m'] = Wav2Vec2ForCTC.from_pretrained(repo).eval()
        _M['torch'] = torch
    return _M['p'], _M['m'], _M['torch']


def norm(t):
    t = re.sub(r'\{[^}]*\}', ' ', t)
    t = t.replace('ٰ', 'ا').replace('ٱ', 'ا')
    t = re.sub('[أإآ]', 'ا', t)
    t = re.sub(r'[^ء-يً-ْ ]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def letters_of(t):
    return re.sub(f'[{MARKS} ]', '', t)


def hear(path, timings=False):
    """Letter recogniser: text heard, plus time of first and last letter (and, with timings=True, each emitted
    symbol with its time)."""
    p, m, torch = _ctc()
    a, _ = librosa.load(path, sr=16000)
    x = p.feature_extractor(a, sampling_rate=16000, return_tensors='pt').input_values
    with torch.no_grad():
        ids = m(x).logits.argmax(-1)[0].numpy()
    toks = p.tokenizer.convert_ids_to_tokens(ids.tolist())
    fps = len(ids) / (len(a) / 16000)
    let = [i for i, t in enumerate(toks) if ids[i] != p.tokenizer.pad_token_id and t not in ('|', ' ')]
    res = (p.tokenizer.decode(ids.tolist()), (let[0] / fps if let else 0.0), (let[-1] / fps if let else len(a) / 16000))
    if timings:
        seq, prev = [], None
        for i, t in enumerate(toks):
            if ids[i] != prev and ids[i] != p.tokenizer.pad_token_id:
                seq.append((t, i / fps))
            prev = ids[i]
        return res + (seq,)
    return res


def _is_mark(t):
    return all(ch in MARKS for ch in t)


def stress_scores(path, seq, t0, t1):
    """Stress (نبر): how much the line's peaks stand out, and how long doubled letters are held.
    words: split the heard symbols at word breaks; each word's prominence = loudness + pitch above the line's median.
      stress_peak  the most prominent word's lead over the median word (dB + semitones): low = flat, no stress
      stress_shape spread of word prominence: low = every word the same weight
      shadda_hold  doubled letter's time to the next letter, relative to the median letter: > 1 = held
    """
    a, sr = librosa.load(path, sr=16000)
    hop = 160
    rms = librosa.feature.rms(y=a, frame_length=640, hop_length=hop)[0]
    db = 20 * np.log10(rms + 1e-9)
    f0, vf, _ = librosa.pyin(a, fmin=70, fmax=350, sr=sr, frame_length=1024, hop_length=hop)
    st = 12 * np.log2(np.where(vf, f0, np.nan) / 100)
    words, cur = [], []
    for t, tm in seq:
        if t in ('|', ' '):
            if cur:
                words.append(cur); cur = []
        else:
            cur.append((t, tm))
    if cur:
        words.append(cur)
    prom = []
    for k, w in enumerate(words):
        s = w[0][1]
        e = words[k + 1][0][1] if k + 1 < len(words) else t1 + 0.1
        i0, i1 = int(s * 100), max(int(s * 100) + 1, int(e * 100))
        d = np.percentile(db[i0:i1], 90)
        p_ = np.nanmax(st[i0:i1]) if np.any(~np.isnan(st[i0:i1])) else np.nan
        prom.append((d, p_))
    out = {'stress_peak': None, 'stress_shape': None, 'shadda_hold': None}
    if len(prom) >= 3:
        d = np.array([x[0] for x in prom]); p_ = np.array([x[1] for x in prom])
        z = (d - np.median(d)) + np.nan_to_num(p_ - np.nanmedian(p_))
        out['stress_peak'] = round(float(np.max(z)), 2)
        out['stress_shape'] = round(float(np.std(z)), 2)
    letters = [(t, tm) for t, tm in seq if t not in ('|', ' ') and not _is_mark(t)]
    durs = [letters[i + 1][1] - letters[i][1] for i in range(len(letters) - 1)]
    if durs:
        med = np.median(durs)
        held = []
        sym = [(t, tm) for t, tm in seq if t not in ('|', ' ')]
        for i, (t, tm) in enumerate(sym):
            if '\u0651' in t:  # shadda (often joined with its vowel): the letter before it and how long it lasts
                prev = [k for k in range(i) if not _is_mark(sym[k][0])]
                j = prev[-1] if prev else None
                if j is not None:
                    nxt = next((sym[k][1] for k in range(i + 1, len(sym)) if not _is_mark(sym[k][0])), None)
                    if nxt:
                        held.append((nxt - sym[j][1]) / med)
        if held:
            out['shadda_hold'] = round(float(np.mean(held)), 2)
    return out


def text_scores(ref, heard):
    r, h = norm(ref), norm(heard)
    rl, hl = letters_of(r), letters_of(h)
    sm = difflib.SequenceMatcher(None, rl, hl, autojunk=False)
    letters = sm.ratio()
    conf = 0
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'replace':
            for a, b in zip(rl[i1:i2], hl[j1:j2]):
                conf += (a, b) in NEAR
    # marks: compare the mark sequence on matched letters
    def marks_per_letter(t):
        out, cur = [], None
        for ch in t.replace(' ', ''):
            if ch in MARKS:
                if out:
                    out[-1] += ch
            else:
                out.append('')
        return out
    rm, hm = marks_per_letter(r), marks_per_letter(h)
    ok = tot = sh_ref = sh_hit = 0
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            a, b = rm[blk.a + k], hm[blk.b + k]
            if a:
                tot += 1
                ok += set(a) == set(b)
                if 'ّ' in a:
                    sh_ref += 1
                    sh_hit += 'ّ' in b
    return {'letters': round(letters, 3), 'marks': round(ok / tot, 3) if tot else None,
            'shadda': round(sh_hit / sh_ref, 3) if sh_ref else None, 'confusions': conf}


def voice_scores(path, t0, t1):
    import parselmouth
    from parselmouth.praat import call
    snd = parselmouth.Sound(path)
    end = min(snd.duration, t1 + 0.3)
    part = snd.extract_part(from_time=max(0, t0 - 0.05), to_time=end)
    pitch = part.to_pitch_ac(pitch_floor=70, pitch_ceiling=350)
    f0 = pitch.selected_array['frequency']
    f0 = f0[f0 > 0]
    st = 12 * np.log2(f0 / 100) if len(f0) else np.array([0.0])
    harm = part.to_harmonicity_cc()
    hv = harm.values[harm.values > -100]
    pp = call(part, "To PointProcess (periodic, cc)", 70, 350)
    jit = call(pp, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3) * 100
    shim = call([part, pp], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6) * 100
    a, sr = librosa.load(path, sr=16000)
    seg = a[int(t0 * sr):int(t1 * sr)]
    hop = 160
    db = 20 * np.log10(librosa.feature.rms(y=seg, frame_length=640, hop_length=hop)[0] + 1e-9) if len(seg) > 640 else np.zeros(1)
    quiet = db < (np.median(db) - 25)
    runs, n = 0, 0
    for q in quiet:
        n = n + 1 if q else 0
        runs += n == 18  # 0.18 s
    full = 20 * np.log10(librosa.feature.rms(y=a, frame_length=640, hop_length=hop)[0] + 1e-9)
    return {'hnr': round(float(np.mean(hv)), 2) if len(hv) else None, 'jitter': round(float(jit), 3),
            'shimmer': round(float(shim), 3),
            'pitch_range': round(float(np.percentile(st, 95) - np.percentile(st, 5)), 2),
            'pitch_move': round(float(np.std(st)), 2), 'pauses': int(runs),
            'tail': round(float(max(0.0, len(a) / sr - t1 - 0.25)), 2),
            'noise': round(float(np.percentile(full, 5) - full.max()), 1)}


def judge(path, ref):
    heard, t0, t1, seq = hear(path, timings=True)
    out = {'heard': heard, **text_scores(ref, heard), **voice_scores(path, t0, t1), **stress_scores(path, seq, t0, t1)}
    n_letters = len(letters_of(norm(ref)))
    out['rate'] = round(n_letters / max(0.3, t1 - t0), 2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('wavs', nargs='+')
    ap.add_argument('--text', required=True)
    a = ap.parse_args()
    print(json.dumps({w: judge(w, a.text) for w in a.wavs}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
