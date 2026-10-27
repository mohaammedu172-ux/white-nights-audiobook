"""Voice bake-off on 40 half-verses: every voice variant says every line, both judges score every take,
then we see (a) each voice's average and (b) what "best take per line" gets when the pipeline may pick
between voices. Also writes a 5-verse listening sample built from the best takes.

    python -m ar.train.bakeoff --variant base=none --variant b2000=/kaggle/working/adapter_b/adapter_2000.pt \
        --out /kaggle/working/bakeoff [--verses 1-20] [--plain]

Every variant except 'plain' gets the tajweed spellings (tanwin as a written noon, RULEBOOK rule 23).
--plain adds the original voice without those spellings, to measure what the spellings alone are worth.
Line score = average of words heard (Cohere) and pronunciation features said (ClArTTS judge, ar.score).
"""
import argparse, gc, itertools, json, os, sys
import torch

TAJWEED = {'tanwin': True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--variant', action='append', default=[], help='name=adapter_path ("none" = original voice)')
    ap.add_argument('--plain', action='store_true')
    ap.add_argument('--verses', default='1-20')
    ap.add_argument('--sample-verses', type=int, default=5)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    sys.path.insert(0, repo)
    from ar import text_rules as tr
    from ar.tts_torch import VoiceTorch
    from ar.judge import run_cohere, run_clartts
    from ar.score import score_pair
    from ar.assemble import build_voice, to_mp3

    lo, hi = (int(x) for x in args.verses.split('-'))
    script = [v for v in tr.load_script(os.path.join(repo, 'books/muallaqat/imru_al_qays/original.txt')) if lo <= v[0] <= hi]
    lines = []
    for n, a, b in script:
        for half, t in (('a', a), ('b', b)):
            lines.append((f'v{n}{half}', tr.split_tag(t)[1]))
    variants = []
    if args.plain:
        variants.append(('plain', None, False))
    for v in args.variant:
        name, path = v.split('=', 1)
        path = None if path in ('', 'none') else path
        if path is None or os.path.exists(path):
            variants.append((name, path, True))
        else:
            print('skipping missing adapter', path, flush=True)
    os.makedirs(args.out, exist_ok=True)
    ref = os.path.join(repo, 'voices', 'clartts_male_ref.wav')

    takes = {}  # (line, variant) -> info
    for name, adapter, spell in variants:
        voice = VoiceTorch(ref, adapter=adapter)
        for k, t in lines:
            said = tr.tajweed(t, TAJWEED) if spell else t
            w = os.path.join(args.out, f'{k}_{name}.wav')
            info = voice.say(said, w, exaggeration=0.35, seed=sum(map(ord, k)))
            takes[(k, name)] = {**info, 'wav': w, 'said': said}
            print(k, name, info, flush=True)
        del voice; gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    keys = list(takes)
    wavs = [takes[x]['wav'] for x in keys]
    heard_c = run_cohere(wavs)
    heard_w = run_clartts(wavs)
    script_of = dict(lines)
    for x, hc, hw in zip(keys, heard_c, heard_w):
        tk = takes[x]
        s = script_of[x[0]]
        word = max(tr.compare(s, hc)['word_acc'], tr.compare(tk['said'], hc)['word_acc'])
        feats, miss = score_pair(s, hw)
        got, tot = sum(a for a, _ in feats.values()), sum(b for _, b in feats.values())
        pron = got / tot if tot else None
        if not tk['hit_stop']:
            word *= 0.5  # a clip that ran on or was cut is unusable whatever the judges say
        tk.update(heard_cohere=hc, heard_clartts=hw, word=round(word, 3), feats=feats, misses=miss,
                  pron=None if pron is None else round(pron, 3),
                  score=round(word if pron is None else (word + pron) / 2, 3))

    names = [v[0] for v in variants]

    def board(group):
        """Average over lines, letting the pipeline keep the best of `group` for each line."""
        sc, wd, ft = 0.0, 0.0, {k: [0, 0] for k in ('tanwin', 'shadda', 'hamza', 'heavy')}
        picks = {}
        for k, _ in lines:
            best = max(group, key=lambda n: takes[(k, n)]['score'])
            picks[k] = best
            tk = takes[(k, best)]
            sc += tk['score']; wd += tk['word']
            for f, (a, b) in tk['feats'].items():
                ft[f][0] += a; ft[f][1] += b
        n = len(lines)
        row = {'score': round(100 * sc / n, 1), 'words': round(100 * wd / n, 1)}
        row.update({f: (round(100 * a / b) if b else None) for f, (a, b) in ft.items()})
        return row, picks

    rows = {}
    for n in names:
        rows[n] = board([n])[0]
    spelled = [n for n, _, s in variants if s]
    combos = {}
    for r in range(2, len(spelled) + 1):
        for g in itertools.combinations(spelled, r):
            row, picks = board(list(g))
            combos['best of ' + ' + '.join(g)] = (row, picks)
            rows['best of ' + ' + '.join(g)] = row
    top = max(combos, key=lambda c: combos[c][0]['score']) if combos else None

    # listening samples: the first verses from the best combination, and from the original voice alone
    def sample(pick, out_name):
        files, pads = [], []
        for k, _ in lines[:2 * args.sample_verses]:
            files.append(takes[(k, pick(k))]['wav'])
            pads.append(0.3 if k.endswith('a') else 0.75)
        build_voice(files, pads, os.path.join(args.out, out_name + '.wav'))
        to_mp3(os.path.join(args.out, out_name + '.wav'), os.path.join(args.out, out_name + '.mp3'))

    if top:
        sample(lambda k: combos[top][1][k], 'best_takes_5_verses')
    if 'base' in names:
        sample(lambda k: 'base', 'original_voice_5_verses')

    md = ['# Voice bake-off', '', f'{len(lines)} half-verses (verses {args.verses}), every voice says every line once.',
          'Score = average of words heard and pronunciation features said. "best of" = keep the higher-scoring take per line.', '',
          '| Voice | Score | Words | Tanwin | Shadda | Hamza | Heavy |', '|---|---|---|---|---|---|---|']
    for n, r in sorted(rows.items(), key=lambda kv: -kv[1]['score']):
        md.append(f"| {n} | {r['score']} | {r['words']} | {r['tanwin']} | {r['shadda']} | {r['hamza']} | {r['heavy']} |")
    if top:
        from collections import Counter
        md += ['', f'Best combination: **{top}**. Lines won: ' +
               ', '.join(f'{n} {c}' for n, c in Counter(combos[top][1].values()).most_common()), '',
               'Picks for the 5-verse sample: ' + ', '.join(f'{k}={combos[top][1][k]}' for k, _ in lines[:2 * args.sample_verses])]
    open(os.path.join(args.out, 'report.md'), 'w', encoding='utf8').write('\n'.join(md) + '\n')
    json.dump({f'{k}|{n}': v for (k, n), v in takes.items()}, open(os.path.join(args.out, 'takes.json'), 'w', encoding='utf8'),
              ensure_ascii=False, indent=1)
    print('\n'.join(md), flush=True)


if __name__ == '__main__':
    main()
