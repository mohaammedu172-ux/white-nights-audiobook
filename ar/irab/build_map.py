"""Word-by-word and sentence i'rab map: al-Durra's analysis (OCR) linked to each word of our script.
Stores short labels (role, case, sign), not the book's prose."""
import re, json, sys
sys.path.insert(0, '/home/claude/white-nights-audiobook')
from ar import text_rules as tr
exec(open('/root/irab/work/align.py').read().split('heads = []')[0])  # sk, forms, verses, blocks
amap = json.load(open('/root/irab/work/map.json'))['map']
ROLES = ['نائب فاعل', 'فاعل', 'مفعول به', 'مفعول مطلق', 'مفعول لأجله', 'مفعول معه', 'مفعول فيه', 'ظرف زمان', 'ظرف مكان',
         'حال', 'تمييز', 'مبتدأ', 'خبر', 'اسم كان', 'خبر كان', 'اسم إن', 'اسم أن', 'اسم كأن', 'اسمها', 'خبرها', 'مضاف إليه',
         'صفة', 'نعت', 'معطوف', 'بدل', 'توكيد', 'منادى', 'جار ومجرور', 'اسم مجرور', 'حرف جر', 'حرف عطف', 'حرف نفي', 'حرف شرط',
         'حرف مشبه بالفعل', 'فعل ماض', 'فعل مضارع', 'فعل أمر', 'ضمير متصل', 'ضمير منفصل', 'اسم موصول', 'اسم إشارة',
         'ظرف', 'أداة', 'حرف', 'مستثنى', 'فعل']
CASE = [('مرفوع', 'رفع'), ('منصوب', 'نصب'), ('مجرور', 'جر'), ('مجزوم', 'جزم'), ('مبني على الفتح', 'مبني فتح'),
        ('مبني على الضم', 'مبني ضم'), ('مبني على الكسر', 'مبني كسر'), ('مبني على السكون', 'مبني سكون'),
        ('مبني على حذف النون', 'مبني حذف النون'), ('رفعه', 'رفع'), ('نصبه', 'نصب'), ('جره', 'جر'), ('جزمه', 'جزم'),
        ('في محل رفع', 'محل رفع'), ('في محل نصب', 'محل نصب'), ('في محل جر', 'محل جر')]
SIGN = [('ضمة مقدرة', 'ضمة مقدرة'), ('فتحة مقدرة', 'فتحة مقدرة'), ('كسرة مقدرة', 'كسرة مقدرة'), ('الفتحة نيابة عن الكسرة', 'فتحة بدل الكسرة (ممنوع من الصرف)'),
        ('حذف حرف العلة', 'حذف حرف العلة'), ('حذف النون', 'حذف النون')]
def first(desc, table):
    hits = [(desc.find(k), v) for k, v in table if k in desc]
    return min(hits)[1] if hits else ''
def role_of(desc):
    hits = [(desc.find(k), -len(k), k) for k in ROLES if k in desc]
    return min(hits)[2] if hits else ''
def entries(block):
    b = re.sub(r'\s+', ' ', block)
    b = re.sub(r'^ال\S{0,2}عراب\s*[:8;؛]\s*', '', b)
    parts = re.split(r'(?:(?<=[.»›،])|^)\s*([^\s:.»›،()]{1,15})\s*:\s*', ' ' + b)
    out = []
    for k in range(1, len(parts) - 1, 2):
        head, desc = parts[k], parts[k + 1].strip()
        # 'وسقط مضاف واللوى مضاف إليه مجرور ...': give the mudaf ilayh word its own entry, and stop the owner's
        # description there so its sign isn't mixed up with the next word's
        m = re.search(r'\s?و\S+\s+مضاف\s*و(\S+)\s+مضاف إليه([^.»›]*)', desc)
        if m:
            out.append((head, desc[:m.start()].strip()))
            out.append((m.group(1), 'مضاف إليه' + m.group(2) + ' ' + desc[m.end():m.end() + 80]))
        else:
            out.append((head, desc))
    return out
def sentences(block):
    b = re.sub(r'\s+', ' ', block)
    res = []
    for m in re.finditer(r'(?:وال|و)?جمل[ةه]\s*(الفعلية|الاسمية)?\s*(\([^)]{1,60}\))?[^.»]{0,60}?(لا محل لها من ال\S{0,2}عراب|في محل (?:رفع|نصب|جر|جزم)\s*[^.»،(]{0,25})', b):
        kind = m.group(1) or ''
        what = (m.group(2) or '').strip('() ').replace(' . . . ألخ', '…').replace('. . . ألخ', '…')
        label = re.sub(r'ال\S{0,2}عراب', 'الإعراب', m.group(3)).strip()
        why = ''
        pre = b[max(0, m.start() - 0):m.end() + 40]
        for k in ('مستأنفة', 'ابتدائية', 'صلة الموصول', 'جواب الشرط', 'جواب الطلب', 'جواب إذا', 'جواب لما', 'معطوفة', 'اعتراضية', 'تفسيرية', 'جواب القسم'):
            if k in pre: why = k; break
        res.append({'جملة': ((('الجملة ' + kind) if kind else 'الجملة') + (f' ({what})' if what else '')).strip(), 'محلها': label, 'سبب': why})
    return res
MARK_OF = {'ُ': 'ضمة', 'ٌ': 'ضمة', 'َ': 'فتحة', 'ً': 'فتحة', 'ِ': 'كسرة', 'ٍ': 'كسرة', 'ْ': 'سكون'}
def our_end(w, before_suffix=False):
    w = re.sub(r'(ُ)و$', r'\1', w); w = re.sub(r'(ِ)ي$', r'\1', w); w = re.sub('اا', 'ا', w)
    if before_suffix:  # the case sits on the letter before an attached pronoun
        w = re.sub('(ه[\u064e\u064f\u0650]?(م[\u0652\u064e]?|ا|ن[\u0651]?[\u064e]?)?|ك[\u064e\u064f\u0650]?(م[\u0652]?)?|ن[\u064e]?ا)$', '', w)
    marks = [c for c in w if c in MARK_OF]
    return MARK_OF.get(marks[-1], '') if marks else ''
def expect(case, sign):
    if 'مقدرة' in sign or 'نيابة' in sign or 'حذف' in sign or sign in ('الياء', 'الواو', 'الألف') or case.startswith('محل') or not case: return ''
    if 'بدل الكسرة' in sign: return 'فتحة'
    return {'رفع': 'ضمة', 'نصب': 'فتحة', 'جر': 'كسرة', 'جزم': 'سكون', 'مبني فتح': 'فتحة', 'مبني ضم': 'ضمة', 'مبني كسر': 'كسرة', 'مبني سكون': 'سكون'}.get(case, '')
out = []
for n, text in verses:
    bl = amap.get(str(n), [])
    ents = [e for i in bl for e in entries(blocks[i])]
    sents = [s for i in bl for s in sentences(blocks[i])]
    words = []
    used = set()
    for w in re.sub(r'[،:!.…؛]', ' ', text).split():
        fw = forms(w)
        hit = next(((i, h, d) for i, (h, d) in enumerate(ents) if i not in used and forms(h) & fw), None)
        if not hit:  # OCR-damaged headword: closest unused entry by spelling, near the expected position
            import difflib
            best = max(((difflib.SequenceMatcher(None, sk(h), x).ratio(), i, h, d) for i, (h, d) in enumerate(ents)
                        if i not in used for x in fw if len(sk(h)) > 1), default=None)
            if best and best[0] >= 0.75:
                hit = best[1:]
        if hit:
            used.add(hit[0])
            d1 = re.split(r'\s[.»›]\s|\s[.»›]$', hit[2] + ' .')[0]  # this word's own description only
            role, case = role_of(d1), first(d1, CASE)
            full = re.sub(r'\s+', ' ', hit[2][:220]); sign = first(full, SIGN)
            if re.search('مقدرة|نيابة|الأفعال الخمسة|الشبيه بالزائد|الزائد|ضرورة|ثبوت النون', full): sign = sign or 'مقدرة/نيابة'
            if case and not re.search('مبني|محل|حذف', d1) and case.startswith('مبني'):
                case = ''
            if not case:
                for k, v in (('خبر كان', 'نصب'), ('خبر ليس', 'نصب'), ('خبر إن', 'رفع'), ('خبر أن', 'رفع'), ('خبر كأن', 'رفع'),
                             ('اسم كان', 'رفع'), ('اسم إن', 'نصب'), ('اسم أن', 'نصب'), ('اسم كأن', 'نصب'), ('نائب فاعل', 'رفع'),
                             ('فاعل', 'رفع'), ('مبتدأ', 'رفع'), ('خبر', 'رفع'), ('مفعول', 'نصب'), ('حال', 'نصب'), ('تمييز', 'نصب'),
                             ('ظرف', 'نصب'), ('مضاف إليه', 'جر')):
                    if d1.startswith(k):
                        case = v; break
            has_suffix = bool(re.search(r'(ها|هم|هما|هن|كم|نا|ه|ك)$', sk(w))) and not sk(w).startswith(('ال', 'وال', 'فال', 'بال', 'لل')) and sk(w) not in ('الله', 'المسك') and role not in ('فعل ماض', 'فعل مضارع', 'فعل أمر')
            exp, ours = expect(case, sign), our_end(w, has_suffix)
            if role in ('جار ومجرور', 'حرف جر', 'حرف عطف', 'ضمير متصل', 'ضمير منفصل', 'اسم موصول', 'اسم إشارة', 'فعل ماض', 'فعل أمر', 'ظرف', 'أداة', 'حرف') or 'مبني' in case:
                exp = ''  # built words, and words whose own ending isn't the case-bearing one
            words.append({'word': w, 'role': role, 'case': case, 'sign': sign, 'expected_end': exp, 'our_end': ours,
                          'check': ('✓' if exp == ours else '✗') if exp and ours else ''})
        else:
            words.append({'word': w, 'role': '', 'case': '', 'sign': '', 'expected_end': '', 'our_end': our_end(w), 'check': ''})
    out.append({'verse': n, 'text': text, 'source_blocks': bl, 'words': words, 'sentences': sents})
json.dump(out, open('/root/irab/work/irab_map.json', 'w'), ensure_ascii=False, indent=1)
tot = sum(len(v['words']) for v in out); lab = sum(1 for v in out for w in v['words'] if w['role'])
chk = [(v['verse'], w) for v in out for w in v['words'] if w['check']]
bad = [(n, w['word'], w['role'], w['case'], w['expected_end'], w['our_end']) for n, w in chk if w['check'] == '✗']
print('words', tot, 'with i\'rab', lab, '| checked endings', len(chk), 'mismatches', len(bad), '| sentences', sum(len(v['sentences']) for v in out))
for b in bad: print(b)
