"""Reference recitation: find every half-verse in a human recitation of the poem and measure how it is recited, so
our recordings can be compared with it verse by verse. Used only to measure (never to train or clone a voice).
    python -m ar.reference AUDIO NAME   -> books/muallaqat/imru_al_qays/reference/NAME.json

How: the ClArTTS letter recogniser transcribes the recording in 20 s windows; its letters (with times) are aligned
to the letters of our script, which gives each half-verse a start and end. Then per half: duration, pace (letters/s),
pauses inside it, the pause after it, how long the last letter is held, pitch range and movement, loudness.
"""
import difflib, json, os, re, sys
import numpy as np, librosa
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, REPO)
from ar import text_rules as tr
from ar.autojudge import _ctc, norm, MARKS

SR = 16000


def transcribe(a, win=20.0):
    p, m, torch = _ctc()
    out = []  # (letter, time)
    step = int(win * SR)
    for s in range(0, len(a), step):
        seg = a[s:s + step]
        if len(seg) < SR // 2:
            break
        x = p.feature_extractor(seg, sampling_rate=SR, return_tensors='pt').input_values
        with torch.no_grad():
            ids = m(x).logits.argmax(-1)[0].numpy()
        toks = p.tokenizer.convert_ids_to_tokens(ids.tolist())
        fps = len(ids) / (len(seg) / SR)
        prev = None
        for i, t in enumerate(toks):
            if ids[i] != prev and ids[i] != p.tokenizer.pad_token_id and t not in ('|', ' ') and not all(c in MARKS for c in t):
                for ch in t:
                    if ch not in MARKS:
                        out.append((ch, s / SR + i / fps))
            prev = ids[i]
        print(f'{s / SR / 60:.1f} min', flush=True)
    return out


def letters(t):
    return re.sub(f'[{MARKS} ]', '', norm(re.sub(r'(ُ)و(?=\s|$)|(ِ)ي(?=\s|$)', lambda m: m.group(1) or m.group(2), t)))


def main():
    audio, name = sys.argv[1], sys.argv[2]
    a, _ = librosa.load(audio, sr=SR, mono=True)
    heard = transcribe(a)
    script = tr.load_script(os.path.join(REPO, 'books/muallaqat/imru_al_qays/original.txt'))
    ref_chars, owner = [], []
    for n, x, y in script:
        for h, t in (('a', x), ('b', y)):
            L = letters(tr.split_tag(t)[1].replace('اا', 'ا'))
            ref_chars += list(L); owner += [(n, h)] * len(L)
    hl = ''.join(c for c, _ in heard)
    sm = difflib.SequenceMatcher(None, ''.join(ref_chars), hl, autojunk=False)
    times = {}
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            times.setdefault(owner[blk.a + k], []).append(heard[blk.b + k][1])
    hop = 160
    rms = librosa.feature.rms(y=a, frame_length=640, hop_length=hop)[0]
    db = 20 * np.log10(rms + 1e-9)
    speech_floor = np.percentile(db, 5) + 8  # just above the room noise between phrases
    res = {}
    keys = [(n, h) for n, _, _ in script for h in 'ab']
    for k in keys:
        n_letters = sum(1 for o in owner if o == k)
        t = times.get(k, [])
        if len(t) < max(4, 0.5 * n_letters):  # too little of this half found: not in this recitation, or missed
            res[f'{k[0]}{k[1]}'] = None
            continue
        t0, t1 = float(np.percentile(t, 2)), float(np.percentile(t, 98))
        i0, i1 = int(t0 * 100), int(t1 * 100)
        # end of sound after the last letter (the held final vowel)
        j = i1
        while j < len(db) and db[j] > speech_floor:
            j += 1
        end = j / 100
        seg_db = db[i0:j]
        quiet = seg_db < speech_floor
        runs, cur = 0, 0
        for q in quiet:
            cur = cur + 1 if q else 0
            runs += cur == 18
        f0, vf, _ = librosa.pyin(a[int(t0 * SR):int(end * SR)], fmin=70, fmax=350, sr=SR, frame_length=1024, hop_length=hop)
        st = 12 * np.log2(f0[~np.isnan(f0)] / 100) if np.any(~np.isnan(f0)) else np.array([0.0])
        res[f'{k[0]}{k[1]}'] = {'start': round(t0, 2), 'end': round(end, 2), 'found': round(len(t) / n_letters, 2),
                                'rate': round(n_letters / max(0.3, t1 - t0), 2), 'inner_pauses': int(runs),
                                'final_hold': round(end - t1, 2), 'pitch_median': round(float(np.median(st)), 2),
                                'pitch_range': round(float(np.percentile(st, 95) - np.percentile(st, 5)), 2),
                                'pitch_move': round(float(np.std(st)), 2), 'loud': round(float(np.median(seg_db)), 1)}
    # pauses between consecutive found halves
    prev = None
    for k in keys:
        r = res[f'{k[0]}{k[1]}']
        if r and prev and res[prev]:
            res[prev]['pause_after'] = round(max(0.0, r['start'] - res[prev]['end']), 2)
        prev = f'{k[0]}{k[1]}'
    out_dir = os.path.join(REPO, 'books/muallaqat/imru_al_qays/reference')
    os.makedirs(out_dir, exist_ok=True)
    json.dump({'source': audio, 'halves': res}, open(os.path.join(out_dir, f'{name}.json'), 'w'), indent=1)
    found = [v for v in res.values() if v]
    print(f'{len(found)} of {len(res)} half-verses found')
    if found:
        med = lambda k: round(float(np.median([v[k] for v in found if k in v])), 2)
        pa = [v['pause_after'] for kk, v in res.items() if v and 'pause_after' in v and kk.endswith('a')]
        pb = [v['pause_after'] for kk, v in res.items() if v and 'pause_after' in v and kk.endswith('b')]
        print('median: rate', med('rate'), 'letters/s; final hold', med('final_hold'), 's; pitch range', med('pitch_range'),
              'st; pause after first half', round(float(np.median(pa)), 2) if pa else None,
              's; after verse', round(float(np.median(pb)), 2) if pb else None, 's; halves with inner pauses',
              sum(v['inner_pauses'] > 0 for v in found))


if __name__ == '__main__':
    main()
