"""Poem map: one record per verse with five layers, the join key for every tool (see the scorecard's test plan).
    python -m ar.poem_map  -> books/muallaqat/imru_al_qays/poem_map.json

  1 text       the vowelled verse (our script)
  2 grammar    from the i'rab map (al-Durra), word and sentence i'rab
  3 metre      ṭawīl feet per half, from ar/metre.py
  4 recitation how it should be said; every rule names its source (RECITE_SOURCES)
  5 results    filled by the section tests after a recording (ar/sections.py)

Layer 4 rules and their sources:
  sections and moods      the poem's thematic parts (Mawdoo3 commentary; boundaries set on our 81-verse text)
  sentence tone           Arabic intonation patterns (statement, call, wh-question fall; yes/no question rises;
                          wish and reproach rise; resignation and sorrow fall with a lowered voice)
                          (lecture on التنغيم citing تمام حسان, Mustansiriyah University)
  pauses and ishbāʿ       RULEBOOK rule 32 (al-Akhfash; المرشد الوافي; العروض وموسيقا الشعر)
  verse joins             where al-Durra's i'rab carries the sentence into the next verse (تضمين), the voice
                          shouldn't settle: shorter pause, the rhyme lengthened, pitch kept up (Tsur, "The
                          performance of enjambments"); where the sentence ends, the voice falls and rests longer
"""
import itertools, json, os, re, sys
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, REPO)
from ar import text_rules as tr
from ar.metre import phon

SECTIONS = [  # (first, last, name, mood, pace, pitch) pace and pitch relative to the plain voice
    (1, 9, 'الوقوف على الأطلال', 'حنين وبكاء', 'بطيء', 'منخفض'),
    (10, 43, 'الذكريات والغزل', 'رقة ومرح', 'متوسط', 'متوسط'),
    (44, 47, 'الليل', 'حزن وهمّ', 'بطيء', 'منخفض'),
    (48, 51, 'الوادي والذئب', 'جلد وتوتر', 'متوسط', 'متوسط'),
    (52, 62, 'الفرس', 'فخر وإعجاب', 'سريع', 'مرتفع'),
    (63, 69, 'الصيد', 'حيوية', 'سريع', 'مرتفع'),
    (70, 81, 'البرق والسيل', 'رهبة', 'بطيء', 'منخفض عريض'),
]
FEET = {'u--': 'فعولن', 'u-u': 'فعولُ', 'u---': 'مفاعيلن', 'u-u-': 'مفاعلن'}
CONTINUES = {2, 9, 11, 12, 15, 25, 30, 32, 34, 35, 39, 68}  # i'rab carries on from the previous verse (al-Durra)


def feet(half):
    p = phon(half)
    p = p[:-1] + '-'  # final syllable anceps (stretched)
    for combo in itertools.product(['u--', 'u-u'], ['u---', 'u-u-'], ['u--', 'u-u'], ['u-u-', 'u---', 'u--']):
        if ''.join(combo) == p:
            return [FEET.get(f, f) for f in combo], p
    return None, p


def tone(half):
    """Sentence type and its tune (falling / rising / level), from the words that mark it."""
    t = tr.split_tag(half)[1]
    plain = re.sub('[ً-ْ]', '', t)
    if re.search(r'(^|\s)،?\s*(أ?لا+|يا+|أي+ها)\s', ' ' + plain) or re.search(r'أفا+طم|أصا+ح', plain):
        return 'نداء', 'هابطة بعد ارتفاع على المنادى'
    if re.search(r'(^|\s)فيا+ لك', plain):
        return 'تعجب', 'صاعدة ثم ممدودة'
    if re.search(r'(^|\s)ف?هل\s', plain):
        return 'استفهام (هل)', 'صاعدة'
    if re.search(r'(^|\s)(قفا+|سيري|دعي|انجلي|انزلي|خلّي|سلي)', plain):
        return 'أمر', 'هابطة حاسمة'
    if re.search(r'كأن', plain):
        return 'تشبيه', 'مستوية ثم هابطة'
    return 'خبر', 'هابطة'


def key_word(half):
    """The word the recitation leans on: a stretched (emphasis) word, else the opening particle of a call or
    command, else none."""
    t = tr.split_tag(half)[1]
    for w in re.sub(r'[،:!.…]', ' ', t).split():
        if re.search(r'([اوي])\1', w):
            return w
    return ''


def main():
    base = os.path.join(REPO, 'books/muallaqat/imru_al_qays')
    irab = {v['verse']: v for v in json.load(open(os.path.join(base, 'irab', 'irab_map.json')))}
    verses = tr.load_script(os.path.join(base, 'original.txt'))
    recite = json.load(open(os.path.join(base, 'job.json')))['parts'][0].get('recite')
    out = []
    for n, a, b in verses:
        sec = next(s for s in SECTIONS if s[0] <= n <= s[1])
        tag = tr.split_tag(a)[0] or tr.split_tag(b)[0]
        fa, pa = feet(a)
        fb, pb = feet(b)
        nxt_continues = (n + 1) in CONTINUES
        ta, tb = tone(a), tone(b)
        rec = {
            'section': sec[2], 'mood': sec[3], 'pace': sec[4], 'pitch': sec[5], 'style_tag_now': tag or '',
            'first_half': {'tone': ta[0], 'tune': ta[1], 'key_word': key_word(a),
                           'end': 'إشباع (مدّ آخره)، وقفة قصيرة', 'inner_pauses': 'لا وقف داخل الشطر'},
            'second_half': {'tone': tb[0], 'tune': tb[1], 'key_word': key_word(b),
                            'end': 'القافية ممدودة (ـلِي)'},
            'join_to_next': ('الجملة تستمر في البيت التالي (تضمين): لا يهبط الصوت، وقفة أقصر، وتُمدّ القافية'
                             if nxt_continues else
                             ('آخر القصيدة: هبوط تام' if n == len(verses) else
                              'تمام المعنى: يهبط الصوت ويستقر، ثم وقفة كاملة')),
            'carries_from_previous': n in CONTINUES,
        }
        if recite:
            rec['first_half']['said'] = tr.recite(a, 'a', recite)
            rec['second_half']['said'] = tr.recite(b, 'b', recite)
        out.append({
            'verse': n,
            'text': {'a': tr.split_tag(a)[1], 'b': tr.split_tag(b)[1]},
            'grammar': {'words': irab.get(n, {}).get('words', []), 'sentences': irab.get(n, {}).get('sentences', [])},
            'metre': {'a': {'feet': fa, 'pattern': pa}, 'b': {'feet': fb, 'pattern': pb}},
            'recitation': rec,
            'results': {},
        })
    json.dump(out, open(os.path.join(base, 'poem_map.json'), 'w'), ensure_ascii=False, indent=1)
    off = [r['verse'] for r in out if not (r['metre']['a']['feet'] and r['metre']['b']['feet'])]
    tones = {}
    for r in out:
        for h in ('first_half', 'second_half'):
            tones[r['recitation'][h]['tone']] = tones.get(r['recitation'][h]['tone'], 0) + 1
    print(len(out), 'verses; metre not split:', off, '; tones:', tones)


if __name__ == '__main__':
    main()
