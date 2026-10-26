"""Text preparation for the voice model, and text comparison for the judges.

The vowelling itself is done by hand in the script files (see books/muallaqat/RULEBOOK.md).
This module only applies the mechanical fixes the model needs, plus the learned
problem-word substitutions in books/muallaqat/problem_words.csv.
"""
import csv, os, re, difflib

# Chatterbox's tokenizer has no ids for precomposed hamza letters: split them.
HAMZA_FIX = {'أ': 'أ', 'آ': 'آ', 'إ': 'إ', 'ؤ': 'ؤ', 'ئ': 'ئ'}
DIAC = re.compile('[ً-ْٓ-ٰٕـ]')
PUNCT = re.compile(r'[،,.؛;:!?؟"«»()\-–—]')


TAG = re.compile(r'^\{(\w+)\}\s*')


def split_tag(text):
    """'{sad} text' -> ('sad', 'text'). Tags set the voice style for that half-verse (see job.json "styles")."""
    m = TAG.match(text)
    return (m.group(1), text[m.end():]) if m else (None, text)


def for_model(text: str) -> str:
    return ''.join(HAMZA_FIX.get(c, c) for c in text)


def load_problem_words(path):
    rows = []
    if path and os.path.exists(path):
        with open(path, encoding='utf8') as f:
            for r in csv.DictReader(f):
                if r.get('find'):
                    rows.append(r)
    return rows


def apply_problem_words(text, rows, scope):
    for r in rows:
        if r.get('scope', 'all') in ('all', scope):
            text = text.replace(r['find'], r['replace'])
    return text


def load_script(path):
    """Lines 'N|half1|half2' -> list of (verse_no, half1, half2)."""
    out = []
    with open(path, encoding='utf8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            n, a, b = line.split('|')
            out.append((int(n), a.strip(), b.strip()))
    return out


BREAK_BEFORE = re.compile('^(?:[وف]|بَيْنَ|عَلَى|عِنْدَ|إِلَى|مِنْ|فِي|كَأَنَّ|حَتَّى|لَمَّا|إِذَا|إِنْ|لَوْ)')


def add_breath(text):
    """A long half-verse with no comma tends to run on: add one at a natural break near the middle
    (before و / ف or a preposition when possible, never inside a phrase like بَيْنَ الدَّخُولِ)."""
    body = text.lstrip('، ')
    words = body.split()
    if '،' in body or len(words) < 4:
        return text
    mid, pos, cands = len(body) / 2, 0, []
    for i, w in enumerate(words[:-1]):
        pos += len(w) + 1
        nice = bool(BREAK_BEFORE.match(words[i + 1])) and not w.startswith(('بَيْنَ', 'عِنْدَ', 'عَلَى', 'إِلَى', 'مِنْ', 'فِي'))
        cands.append((0 if nice else 1, abs(pos - mid), i))
    i = min(c for c in cands if c[1] < len(body) * 0.3 or c[0] == 1)[2]
    words[i] += '،'
    return text[:len(text) - len(body)] + ' '.join(words)


# ---------- comparison ----------
def normalize_letters(t):
    """Bare letters only: no vowels, no punctuation, unified alif/ya/ta-marbuta forms."""
    t = re.sub(r'\{\w+\}', ' ', t)
    t = DIAC.sub('', t)
    t = PUNCT.sub(' ', t)
    t = re.sub(r'([اوي])\1+', r'\1', t)  # stretched vowels written twice (قِفَاا) count as one
    for a, b in (('أ', 'ا'), ('إ', 'ا'), ('آ', 'ا'), ('ٱ', 'ا'), ('ى', 'ي'), ('ة', 'ه'), ('ؤ', 'و'), ('ئ', 'ي')):
        t = t.replace(a, b)
    return ' '.join(t.split())


def strip_stretch(w):
    # the stretched verse/half endings (ـلِي، ـهُو، ـلَا) are recitation marks; compare without the long vowel
    return re.sub('[اوي]$', '', w) if len(w) > 3 else w


def normalize_marks(t):
    t = re.sub(r'\{\w+\}', ' ', t)
    t = PUNCT.sub(' ', t)
    t = t.replace('ٱ', 'ا')
    return ' '.join(t.split())


def compare(script, heard):
    """Return dict with word accuracy on letters, a vowel-mark similarity, and the list of mismatched words."""
    s = [strip_stretch(w) for w in normalize_letters(script).split()]
    h = [strip_stretch(w) for w in normalize_letters(heard).split()]
    sm = difflib.SequenceMatcher(a=s, b=h, autojunk=False)
    ok = sum(m.size for m in sm.get_matching_blocks())
    words = ok / max(1, len(s))
    bad = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != 'equal':
            bad.append({'expected': ' '.join(s[i1:i2]), 'heard': ' '.join(h[j1:j2])})
    marks = difflib.SequenceMatcher(a=normalize_marks(script), b=normalize_marks(heard), autojunk=False).ratio()
    return {'word_acc': round(words, 3), 'mark_sim': round(marks, 3), 'mismatch': bad}
