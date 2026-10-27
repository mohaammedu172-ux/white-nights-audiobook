"""Blind listening test for Mohammed: 12 hard half-verses, each said by every voice (3 seeds each).
The judges only throw out broken takes (cut off, ran on, words missing); the best surviving seed of each voice
goes into the test. Voices are shuffled per line and announced only by number, so the ear decides blind.

    python -m ar.train.abtest --variant base=none --variant clartts=/path/a.pt --variant mix=/path/b.pt --out DIR
Writes DIR/blind_test.mp3 (line 1: take 1, take 2, take 3 ... ) and DIR/key.json (which take is which voice).
"""
import argparse, gc, json, os, random, sys
import numpy as np, soundfile as sf, torch

LINES = [  # every hard sound Mohammed flagged: tanwin, shadda (incl. on ي), hamza, ع, heavy letters, heavy ر, qalqala
    ('v1a',  '، قِفَاا! نَبْكِ مِنْ ذِكْرَى حَبِيبٍ وَمَنْزِلِي'),
    ('v3a',  'تَرَى بَعَرَ الْأَرْآمِ فِي عَرَصَاتِهَا'),
    ('v13b', 'فَقَالَتْ: لَكَ الْوَيْلَاتُ! إِنَّكَ مُرْجِلِي'),
    ('v14a', 'تَقُولُ وَقَدْ مَالَ الْغَبِيطُ بِنَا مَعًا'),
    ('v14b', 'عَقَرْتَ بَعِيرِي يَا امْرَأَ الْقَيْسِ فَانْزِلِي!'),
    ('v24b', 'عَلَيَّ حِرَاصًا لَوْ يُسِرُّونَ مَقْتَلِي'),
    ('v36a', 'غَدَائِرُهُ مُسْتَشْزِرَاتٌ إِلَى الْعُلَا'),
    ('v44a', 'وَلَيْلٍ كَمَوْجِ الْبَحْرِ أَرْخَى سُدُولَهُ'),
    ('v44b', 'عَلَيَّ بِأَنْوَاعِ الْهُمُومِ لِيَبْتَلِي'),
    ('v53a', 'مِكَرٍّ مِفَرٍّ مُقْبِلٍ مُدْبِرٍ مَعًا'),
    ('v59a', 'لَهُ أَيْطَلَا ظَبْيٍ وَسَاقَا نَعَامَةٍ'),
    ('v77a', 'كَأَنَّ ثَبِيرًا فِي عَرَانِينِ وَبْلِهِ'),
]
SEEDS = (1, 2, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--variant', action='append', default=[], help='name=adapter_path ("none" = original voice)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--lines', type=int, default=0, help='only the first N lines (quick test)')
    args = ap.parse_args()
    global LINES
    if args.lines:
        LINES = LINES[:args.lines]
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    sys.path.insert(0, repo)
    from ar import text_rules as tr
    from ar.tts_torch import VoiceTorch
    from ar.judge import run_cohere
    from ar.assemble import build_voice, to_mp3
    variants = []
    for v in args.variant:
        name, path = v.split('=', 1)
        path = None if path in ('', 'none') else path
        if path is None or os.path.exists(path):
            variants.append((name, path))
        else:
            print('skipping missing adapter', path, flush=True)
    os.makedirs(args.out, exist_ok=True)
    ref = os.path.join(repo, 'voices', 'clartts_male_ref.wav')
    takes = {}
    for name, adapter in variants:
        voice = VoiceTorch(ref, adapter=adapter)
        for k, t in LINES:
            said = tr.tajweed(t, {'tanwin': True})  # approved by ear (rule 23); same for every voice
            for s in SEEDS:
                w = os.path.join(args.out, f'{k}_{name}_s{s}.wav')
                takes[(k, name, s)] = {**voice.say(said, w, exaggeration=0.35, seed=1000 * s + sum(map(ord, k))), 'wav': w}
            print(k, name, flush=True)
        del voice; gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    keys = list(takes)
    heard = run_cohere([takes[x]['wav'] for x in keys])
    for x, h in zip(keys, heard):
        takes[x]['heard'] = h
        takes[x]['words'] = tr.compare(dict(LINES)[x[0]], h)['word_acc']
    # judges as a filter only: prefer takes that stopped properly, then most words heard
    rng = random.Random(7)
    key, files, pads = {}, [], []
    beep = os.path.join(args.out, '_tick.wav')
    sr = 24000
    tt = np.arange(int(0.12 * sr)) / sr
    sf.write(beep, (0.15 * np.sin(2 * np.pi * 880 * tt)).astype(np.float32), sr)
    for i, (k, _) in enumerate(LINES, 1):
        order = [n for n, _ in variants]
        rng.shuffle(order)
        key[str(i)] = {'line': k, 'takes': {}}
        files.append(beep); pads.append(1.0)
        for j, n in enumerate(order, 1):
            best = max(SEEDS, key=lambda s: (takes[(k, n, s)]['hit_stop'], takes[(k, n, s)]['words']))
            key[str(i)]['takes'][str(j)] = {'voice': n, 'seed': best, 'words': takes[(k, n, best)]['words']}
            files.append(takes[(k, n, best)]['wav']); pads.append(1.5 if j < len(order) else 3.0)
    build_voice(files, pads, os.path.join(args.out, 'blind_test.wav'))
    to_mp3(os.path.join(args.out, 'blind_test.wav'), os.path.join(args.out, 'blind_test.mp3'))
    json.dump({'lines': dict(LINES), 'key': key,
               'takes': {'|'.join(map(str, x)): v for x, v in takes.items()}},
              open(os.path.join(args.out, 'key.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print('BLIND TEST READY:', len(LINES), 'lines x', len(variants), 'takes; a tick sound starts each line', flush=True)


if __name__ == '__main__':
    main()
