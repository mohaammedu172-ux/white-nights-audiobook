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


def hear(path):
    """Letter recogniser: text heard, plus time of first and last letter."""
    p, m, torch = _ctc()
    a, _ = librosa.load(path, sr=16000)
    x = p.feature_extractor(a, sampling_rate=16000, return_tensors='pt').input_values
    with torch.no_grad():
        ids = m(x).logits.argmax(-1)[0].numpy()
    toks = p.tokenizer.convert_ids_to_tokens(ids.tolist())
    fps = len(ids) / (len(a) / 16000)
    let = [i for i, t in enumerate(toks) if ids[i] != p.tokenizer.pad_token_id and t not in ('|', ' ')]
    return p.tokenizer.decode(ids.tolist()), (let[0] / fps if let else 0.0), (let[-1] / fps if let else len(a) / 16000)


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
    heard, t0, t1 = hear(path)
    out = {'heard': heard, **text_scores(ref, heard), **voice_scores(path, t0, t1)}
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
