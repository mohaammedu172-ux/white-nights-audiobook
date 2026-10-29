import re, json, sys
sys.path.insert(0, '/home/claude/white-nights-audiobook')
from ar import text_rules as tr
blocks = json.load(open('/root/irab/work/blocks.json'))
D = re.compile('[ً-ْٰـ]')
def sk(w):
    w = D.sub('', w); w = re.sub('[أإآٱ]', 'ا', w).replace('ى', 'ي').replace('ة', 'ه')
    w = re.sub(r'[^ء-ي]', '', w)
    return w
def forms(w):
    w = sk(w); out = {w}
    for p in ('و', 'ف', 'ب', 'ل', 'ك'):
        if w.startswith(p) and len(w) > 3: out.add(w[1:])
    out |= {x[2:] for x in list(out) if x.startswith('ال') and len(x) > 4}
    return out
verses = [(n, tr.split_tag(a)[1] + ' ' + tr.split_tag(b)[1]) for n, a, b in tr.load_script('/home/claude/white-nights-audiobook/books/muallaqat/imru_al_qays/original.txt')]
vf = [set().union(*[forms(w) for w in t.split()]) for _, t in verses]
heads = []
for b in blocks:
    hw = re.findall(r'(?:^|[.»›،]\s*|\n)\s*([^\s:.»›،]{2,15})\s*:', b)
    heads.append([h for h in hw if sk(h) and sk(h) != 'الاعراب'])
S = [[sum(1 for h in hs if forms(h) & vf[j]) for j in range(len(verses))] for hs in heads]
# monotonic alignment: each block -> a verse index (non-decreasing), maximise score; blocks may share a verse
import math
nb, nv = len(blocks), len(verses)
dp = [[-1e9] * nv for _ in range(nb)]; bp = [[0] * nv for _ in range(nb)]
for j in range(nv): dp[0][j] = S[0][j] - 0.5 * j
for i in range(1, nb):
    best, arg = -1e9, 0
    for j in range(nv):
        if dp[i - 1][j] > best: best, arg = dp[i - 1][j], j
        # allow same verse (j) or advance by any amount with penalty on jumps >1
        cands = [(dp[i - 1][k] - 0.5 * max(0, j - k - 1), k) for k in range(max(0, j - 4), j + 1)]
        v, k = max(cands)
        dp[i][j] = v + S[i][j]; bp[i][j] = k
j = max(range(nv), key=lambda x: dp[nb - 1][x]); path = [j]
for i in range(nb - 1, 0, -1):
    j = bp[i][j]; path.append(j)
path = path[::-1]
amap = {}
for i, j in enumerate(path):
    amap.setdefault(verses[j][0], []).append(i)
weak = [(i, verses[j][0], S[i][j], len(heads[i])) for i, j in enumerate(path) if S[i][j] < max(2, len(heads[i]) // 4)]
missing = [n for n, _ in verses if n not in amap]
print('verses mapped:', len(amap), 'missing:', missing)
print('weak matches (block, verse, hits, heads):', weak)
json.dump({'map': amap, 'path': path}, open('/root/irab/work/map.json', 'w'))
