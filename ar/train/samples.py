"""Before/after listening test: the same problem lines with the original voice and with the retrained adapter.

    python -m ar.train.samples --adapter /kaggle/working/adapter/adapter_latest.pt --out /kaggle/working/samples
Writes one mp3: each line twice (original, then retrained), 2 s apart, 4 s between lines.
"""
import argparse, gc, json, os, sys
import torch

LINES = [  # chosen for the sounds Mohammed flagged: tanwin, shadda on ي, hamza, emphatics, ع, qalqala
    ('v1a',  '، قِفَاا! نَبْكِ مِنْ ذِكْرَى حَبِيبٍ وَمَنْزِلِي'),
    ('v14a', 'تَقُولُ وَقَدْ مَالَ الْغَبِيطُ بِنَا مَعًا'),
    ('v14b', 'عَقَرْتَ بَعِيرِي يَا امْرَأَ الْقَيْسِ فَانْزِلِي!'),
    ('v24b', 'عَلَيَّ حِرَاصًا لَوْ يُسِرُّونَ مَقْتَلِي'),
    ('v44a', 'وَلَيْلٍ كَمَوْجِ الْبَحْرِ أَرْخَى سُدُولَهُ'),
    ('v44b', 'عَلَيَّ بِأَنْوَاعِ الْهُمُومِ لِيَبْتَلِي'),
    ('v53a', 'مِكَرٍّ مِفَرٍّ مُقْبِلٍ مُدْبِرٍ مَعًا'),
    ('v77a', 'كَأَنَّ ثَبِيرًا فِي عَرَانِينِ وَبْلِهِ'),
]


def main():
    """Variants: 'name=adapter_path@temperature' (adapter 'none' = original voice), heard in that order for each line."""
    ap = argparse.ArgumentParser()
    ap.add_argument('--adapter', default=None, help='shortcut: compare the original voice with this adapter')
    ap.add_argument('--variant', action='append', default=[], help='name=adapter_path@temperature, repeatable')
    ap.add_argument('--out', required=True)
    ap.add_argument('--ref', default=None)
    args = ap.parse_args()
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    sys.path.insert(0, repo)
    from ar.tts_torch import VoiceTorch
    from ar.assemble import build_voice, to_mp3
    ref = args.ref or os.path.join(repo, 'voices', 'clartts_male_ref.wav')
    variants = []
    for v in args.variant:
        name, rest = v.split('=', 1)
        path, _, temp = rest.partition('@')
        variants.append((name, None if path in ('', 'none') else path, float(temp or 0.7)))
    if not variants:
        variants = [('base', None, 0.7), ('retrained', args.adapter, 0.7)]
    variants = [v for v in variants if v[1] is None or os.path.exists(v[1])]
    os.makedirs(args.out, exist_ok=True)
    res = {}
    for name, adapter, temp in variants:
        v = VoiceTorch(ref, adapter=adapter, temperature=temp)
        for k, t in LINES:
            w = os.path.join(args.out, f'{k}_{name}.wav')
            res[f'{k}_{name}'] = v.say(t, w, exaggeration=0.35, seed=1)
            print(k, name, res[f'{k}_{name}'], flush=True)
        del v; gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    files, pads = [], []
    for k, _ in LINES:
        for i, (name, _, _) in enumerate(variants):
            files.append(os.path.join(args.out, f'{k}_{name}.wav'))
            pads.append(2.0 if i < len(variants) - 1 else 4.0)
    build_voice(files, pads, os.path.join(args.out, 'before_after.wav'))
    to_mp3(os.path.join(args.out, 'before_after.wav'), os.path.join(args.out, 'before_after.mp3'))
    json.dump({'order': [v[0] for v in variants], 'clips': res},
              open(os.path.join(args.out, 'samples.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print('SAMPLES DONE; order per line:', ', '.join(v[0] for v in variants), flush=True)


if __name__ == '__main__':
    main()
