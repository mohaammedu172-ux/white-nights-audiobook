"""Is the final vowel one smooth held sound, or said twice ('ي ي')?
    python -m ar.endcheck DIR   (a folder with state.json and clips)
For each clip: find the last letter (letter judge) and the real end of sound; inside that final stretch, a second
loudness peak after a dip of 6 dB or more means the vowel was re-articulated. Also reports the hold length."""
import json, os, sys
import numpy as np, librosa
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ar.autojudge import hear
from ar.assemble import speech_end


def check(path):
    heard, t0, t1, seq = hear(path, timings=True)
    end = speech_end(path) or t1 + 0.3
    a, sr = librosa.load(path, sr=16000)
    seg = a[int(t1 * sr):int(end * sr)]
    if len(seg) < 800:
        return {'hold': round(end - t1, 2), 'twice': False, 'heard_end': heard[-6:]}
    db = 20 * np.log10(librosa.feature.rms(y=seg, frame_length=400, hop_length=80)[0] + 1e-9)
    db = np.convolve(db, np.ones(3) / 3, 'same')
    twice = False
    peak = db[0]
    dipped = False
    for x in db[1:]:
        if x < peak - 6:
            dipped = True
        if dipped and x > peak - 2:
            twice = True
            break
        peak = max(peak, x) if not dipped else peak
    return {'hold': round(end - t1, 2), 'twice': twice, 'heard_end': heard[-6:]}


if __name__ == '__main__':
    d = sys.argv[1]
    st = json.load(open(os.path.join(d, 'state.json')))
    res = {k: check(os.path.join(d, v['chosen'])) for k, v in st.items()}
    holds = [r['hold'] for r in res.values()]
    print(f"{os.path.basename(d)}: hold median {np.median(holds):.2f} s; said twice {sum(r['twice'] for r in res.values())} of {len(res)}; endings heard:",
          ' | '.join(r['heard_end'] for r in res.values()))
