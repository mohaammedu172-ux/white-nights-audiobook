"""Agreement of each automatic measure with Mohammed's A/B picks (ab1). 'Same' and skipped pairs are left out.
    python -m ar.judge_cal.check_ab
"""
import json, os, re, sys
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..')))
from ar.autojudge import judge
from ar.judge_cal.calibrate import line_texts, LOWER

key = json.load(open(os.path.join(HERE, 'ab1_key.json')))
picks = json.load(open(os.path.join(HERE, 'ab1_picks.json')))
picks = picks.get('data', picks)['picks']
cache_p = os.path.join(HERE, 'scores.json')
cache = json.load(open(cache_p)) if os.path.exists(cache_p) else {}
texts = line_texts()
for i, k in key.items():
    for f in (k['A'], k['B']):
        if f not in cache:
            cache[f] = judge(f, texts[k['line']])
            json.dump(cache, open(cache_p, 'w'), ensure_ascii=False, indent=1)
            print('scored', os.path.basename(f), flush=True)
pairs = [(key[i], p['v']) for i, p in picks.items() if p.get('v') in ('A', 'B')]
feats = [f for f in cache[pairs[0][0]['A']] if f != 'heard']
rows = []
for f in feats:
    ag = tot = 0
    for k, v in pairs:
        a, b = cache[k['A']].get(f), cache[k['B']].get(f)
        if a is None or b is None or a == b:
            continue
        a_better = (a < b) if f in LOWER else (a > b)
        ag += a_better == (v == 'A'); tot += 1
    rows.append((f, ag, tot))
md = ['# Automatic judge vs A/B picks (round ab1)', '', f'{len(pairs)} pairs with a clear pick. 50% = chance.', '',
      '| Measure | Agrees | Pairs |', '|---|---|---|']
for f, ag, tot in sorted(rows, key=lambda r: -(r[1] / r[2] if r[2] else 0)):
    md.append(f'| {f} | {100 * ag / tot:.0f}% | {tot} |' if tot else f'| {f} | – | 0 |')
open(os.path.join(HERE, 'report_ab1.md'), 'w').write('\n'.join(md) + '\n')
print('\n'.join(md))
