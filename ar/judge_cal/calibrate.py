"""Check each automatic measure against Mohammed's past ratings (rounds 2-4, ratings.json).

Ratings are relative within a line (he heard the takes of one line side by side), so the test is pairwise: for two
takes of the same line that he rated differently, does the measure point the same way? 50% = chance.
    python -m ar.judge_cal.calibrate        -> scores.json + report.md
"""
import json, os, re, sys
import numpy as np

HERE = os.path.dirname(__file__)
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, REPO)
from ar import text_rules as tr
from ar.autojudge import judge

LOWER = {'confusions', 'jitter', 'shimmer', 'pauses', 'tail', 'noise'}


def line_texts():
    out = {}
    for n, a, b in tr.load_script(os.path.join(REPO, 'books/muallaqat/imru_al_qays/original.txt')):
        out[f'v{n}a'], out[f'v{n}b'] = tr.split_tag(a)[1], tr.split_tag(b)[1]
    return out


def main():
    rows = json.load(open(os.path.join(HERE, 'ratings.json')))
    texts = line_texts()
    cache_p = os.path.join(HERE, 'scores.json')
    cache = json.load(open(cache_p)) if os.path.exists(cache_p) else {}
    for r in rows:
        if r['rating'] is None or r['file'] in cache:
            continue
        lid = re.search(r'(v\d+[ab])', os.path.basename(r['file'])).group(1)
        cache[r['file']] = judge(r['file'], texts[lid])
        print(lid, r['rating'], {k: v for k, v in cache[r['file']].items() if k != 'heard'}, flush=True)
        json.dump(cache, open(cache_p, 'w'), ensure_ascii=False, indent=1)
    rated = [r for r in rows if r['rating'] is not None]
    feats = [k for k in next(iter(cache.values())) if k != 'heard']
    res = {}
    for f in feats:
        agree = total = 0
        for i, a in enumerate(rated):
            for b in rated[i + 1:]:
                if (a['round'], a['line']) != (b['round'], b['line']) or a['rating'] == b['rating']:
                    continue
                va, vb = cache[a['file']].get(f), cache[b['file']].get(f)
                if va is None or vb is None or va == vb:
                    continue
                better_by_ear = a['rating'] > b['rating']
                better_by_measure = (va < vb) if f in LOWER else (va > vb)
                agree += better_by_ear == better_by_measure
                total += 1
        res[f] = (agree, total)
    md = ['# Automatic judge vs Mohammed\'s ear', '',
          f'{len(rated)} rated takes (rounds 2-4). For every pair of takes of the same line that he rated differently,',
          'does the measure prefer the same take? 50% is chance; trust a measure only well above it on enough pairs.', '',
          '| Measure | Agrees with ear | Pairs |', '|---|---|---|']
    for f, (ag, tot) in sorted(res.items(), key=lambda kv: -(kv[1][0] / kv[1][1] if kv[1][1] else 0)):
        md.append(f'| {f} | {100 * ag / tot:.0f}% | {tot} |' if tot else f'| {f} | – | 0 |')
    open(os.path.join(HERE, 'report.md'), 'w').write('\n'.join(md) + '\n')
    print('\n'.join(md))


if __name__ == '__main__':
    main()
