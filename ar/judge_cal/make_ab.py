"""Build the quick A/B round: 40 pairs of takes of the same line (original voice), cleaned the same way the
pipeline now cleans clips, so noise doesn't decide. Sides and order are shuffled; the key stays in ab1_key.json.
    python -m ar.judge_cal.make_ab OUT_DIR
"""
import json, os, random, sys
import soundfile as sf
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..')))
from ar.assemble import load_smooth, stretch, to_mp3

T = '/root/tts'
LINES = ['v1a', 'v3a', 'v13b', 'v14a', 'v14b', 'v24b', 'v36a', 'v44a', 'v44b', 'v53a', 'v59a', 'v77a']
pairs = []
for l in LINES:
    for a, b in ((1, 2), (3, 4), (5, 6)):
        pairs.append((l, f'{T}/takes/{l}_s{a}.wav', f'{T}/takes/{l}_s{b}.wav'))
for l, a, b in (('v53a', 'splitkeep_s1', 'split_s1'), ('v77a', 'splitkeep_s1', 'split_s1'),
                ('v13b', 'splitkeep_s3', 'now_s1'), ('v24b', 'splitkeep_s1', 'now_s2')):
    pairs.append((l, f'{T}/r5/{l}_{a}.wav', f'{T}/r5/{l}_{b}.wav'))
rng = random.Random(29)
rng.shuffle(pairs)
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
key = {}
for i, (l, a, b) in enumerate(pairs, 1):
    if rng.random() < 0.5:
        a, b = b, a
    key[str(i)] = {'line': l, 'A': a, 'B': b}
    for side, f in (('A', a), ('B', b)):
        w = f'{out}/p{i}{side}.wav'
        sf.write(w, stretch(load_smooth(f, 44100), 44100, 0.8), 44100)
        to_mp3(w, w[:-4] + '.mp3')
        os.remove(w)
    print(i, l, flush=True)
json.dump(key, open(os.path.join(HERE, 'ab1_key.json'), 'w'), indent=1)
