"""Pronunciation score: did the voice actually say the tanwin, shadda, hamza and heavy letters?

Listens with the acoustic ClArTTS judge (rufaelfekadu/diactc-wav2vec2-clartts). It writes down vowelled letters
frame by frame without a language model, so it doesn't "fix" what it hears. Each script word is matched to the
heard word, and each feature in it is checked:
  tanwin  - heard word ends in a tanwin mark, or in ن after a short vowel
  shadda  - the doubled letter carries a shadda (or is heard twice)
  hamza   - a hamza letter is heard where the script has one (word-initial hamza is skipped: every vowel start has one)
  heavy   - ص ض ط ظ ق ع ح خ غ heard as themselves, not as their light twins (س د ت ذ ك ا ه ...)

    python -m ar.score clips.json [--out score.json]   (clips.json: [{"id","wav","script"}])
"""
import argparse, difflib, json, re, sys

DIAC = 'ً-ْٰٓ-ٕ'
TANWIN = 'ًٌٍ'
SHADDA = 'ّ'
HAMZA = 'ءأإؤئٕٔ'
HEAVY = 'صضطظقعحخغ'
LIGHT_TWIN = {'ص': 'س', 'ض': 'د', 'ط': 'ت', 'ظ': 'ذز', 'ق': 'ك', 'ع': 'اءأ', 'ح': 'ه', 'خ': 'ك', 'غ': 'ر'}


def letters(w):
    """[(letter, marks)] for a vowelled word, hamza seats split into their own letter."""
    w = w.replace('أ', 'اء').replace('إ', 'اء').replace('ؤ', 'وء').replace('ئ', 'يء').replace('ٔ', 'ء').replace('ٕ', 'ء')
    out = []
    for c in w:
        if re.match(f'[{DIAC}]', c):
            if out:
                out[-1][1] += c
        elif re.match('[ء-ي]', c):
            out.append([c, ''])
    return out


def skel(w):
    return ''.join(c for c, _ in letters(w)).replace('ى', 'ي').replace('ة', 'ه').replace('ء', '')


def words(t):
    t = re.sub(r'\{\w+\}', ' ', t)
    t = re.sub(r'[،,.؛;:!?؟"«»()\-–—]', ' ', t)
    return [w for w in t.split() if re.search('[ء-ي]', w)]


def features(word):
    L = letters(word)
    f = []
    if L and any(m in L[-1][1] for m in TANWIN) or (len(L) > 1 and L[-1][0] in 'اى' and any(m in L[-2][1] for m in TANWIN)):
        f.append(('tanwin', None))
    for i, (c, mk) in enumerate(L):
        if SHADDA in mk:
            f.append(('shadda', c))
        if c == 'ء' and i > 1:
            f.append(('hamza', None))
        if c in HEAVY:
            f.append(('heavy', c))
    return f


def realized(feat, arg, heard_word):
    L = letters(heard_word)
    hs = ''.join(c for c, _ in L)
    if feat == 'tanwin':
        if L and (any(m in L[-1][1] for m in TANWIN) or (len(L) > 1 and L[-1][0] in 'اى' and any(m in L[-2][1] for m in TANWIN))):
            return True
        return bool(L) and L[-1][0] == 'ن' and len(L) > 1
    if feat == 'shadda':
        return any(c == arg and SHADDA in mk for c, mk in L) or (arg * 2) in hs
    if feat == 'hamza':
        return 'ء' in hs[1:]
    if feat == 'heavy':
        return arg in hs
    return False


def score_pair(script, heard):
    sw, hw = words(script), words(heard)
    sm = difflib.SequenceMatcher(a=[skel(w) for w in sw], b=[skel(w) for w in hw], autojunk=False)
    match = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal' or (tag == 'replace' and i2 - i1 == j2 - j1):
            for k in range(i2 - i1):
                match[i1 + k] = j1 + k
    res = {'tanwin': [0, 0], 'shadda': [0, 0], 'hamza': [0, 0], 'heavy': [0, 0]}
    misses = []
    for i, w in enumerate(sw):
        for feat, arg in features(w):
            res[feat][1] += 1
            ok = i in match and realized(feat, arg, hw[match[i]])
            res[feat][0] += ok
            if not ok:
                misses.append({'word': w, 'feature': feat + (f' {arg}' if arg else ''), 'heard': hw[match[i]] if i in match else '-'})
    return res, misses


def summarize(results):
    tot = {k: [0, 0] for k in ('tanwin', 'shadda', 'hamza', 'heavy')}
    for r in results:
        for k, (a, b) in r['features'].items():
            tot[k][0] += a; tot[k][1] += b
    pct = {k: (round(100 * a / b) if b else None) for k, (a, b) in tot.items()}
    allok = sum(a for a, _ in tot.values()); alln = sum(b for _, b in tot.values())
    pct['overall'] = round(100 * allok / alln) if alln else None
    return pct, tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('clips')
    ap.add_argument('--out', default=None)
    args = ap.parse_args()
    sys.path.insert(0, __import__('os').path.join(__import__('os').path.dirname(__file__), '..'))
    from ar.judge import run_clartts
    clips = json.load(open(args.clips, encoding='utf8'))
    heard = run_clartts([c['wav'] for c in clips])
    results = []
    for c, h in zip(clips, heard):
        f, miss = score_pair(c['script'], h)
        results.append({**c, 'heard': h, 'features': f, 'misses': miss})
    pct, tot = summarize(results)
    print(json.dumps(pct, ensure_ascii=False))
    for r in results:
        if r['misses']:
            print(r['id'], '|', '; '.join(f"{m['word']} ({m['feature']}) heard {m['heard']}" for m in r['misses']))
    if args.out:
        json.dump({'percent': pct, 'counts': tot, 'clips': results}, open(args.out, 'w', encoding='utf8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
