"""Tawil metre check: python ar/metre.py <script.txt> lists half-verses whose short/long syllables do not fit. Known false alarms: kaff (مفاعيلُ) in v10, the hidden alif of اللّه in v27."""
import re,sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))))
from ar import text_rules as tr
SH='ّ'; SK='ْ'; V={'َ':'a','ُ':'u','ِ':'i'}; TN={'ً':'a','ٌ':'u','ٍ':'i'}
def phon(half):
    """vowelled half-verse -> list of segments: consonant 'C' and vowels 'v' short/'V' long, in connected speech."""
    t=tr.split_tag(half)[1]
    t=re.sub(r'[،,!:؟.…]','',t).replace('...','').strip()
    t=re.sub(r'([اوي])\1+',r'\1',t)  # stretched marks
    t=t.replace('آ','ءَا').replace('أ','ء').replace('إ','ء').replace('ؤ','ء').replace('ئ','ء').replace('ٰ','ا')
    words=t.split()
    seq=[]  # tokens: 'C','v','V'
    for wi,w in enumerate(words):
        # hamzat wasl / article: initial bare alif followed by consonant
        if w.startswith('ا') and wi>0:
            w=w[1:]
            # assimilated sun letter: ال + letter with shadda -> drop ل
            if w.startswith('ل') and len(w)>2 and SH in w[1:4] and w[1]!='ْ':
                w=w[1:]
        elif w.startswith('ا') and wi==0:
            w='ء'+w[1:]
        i=0; chars=list(w)
        while i<len(chars):
            c=chars[i]
            if not re.match('[ء-ي]',c): i+=1; continue
            marks=''
            j=i+1
            while j<len(chars) and re.match('[ً-ْ]',chars[j]): marks+=chars[j]; j+=1
            nxt=chars[j] if j<len(chars) else ''
            if c in 'اى' and not marks:   # long a
                if seq and seq[-1]=='v': seq[-1]='V'
                elif c=='ا' and seq and seq[-1]=='C': pass
                i=j; continue
            if c in 'وي' and not marks and seq and seq[-1]=='v':
                seq[-1]='V'; i=j; continue
            if c=='ة': c='ت'
            if SH in marks: seq+=['C','C']
            else: seq.append('C')
            if any(m in marks for m in TN): seq+=['v','C']
            elif any(m in V for m in marks): seq.append('v')
            i=j
    # syllabify: weight per vowel: long V -> '-', short v followed by C then (C or end) -> '-', else 'u'
    pat=''
    for k,x in enumerate(seq):
        if x=='V': pat+='-'
        elif x=='v':
            if k+1<len(seq) and seq[k+1]=='C' and (k+2>=len(seq) or seq[k+2]=='C'): pat+='-'
            else: pat+='u'
    return pat
# tawil half: فعولن مفاعيلن فعولن مفاعلن/مفاعيلن ; فعولن may be فعول (u-u); مفاعيلن may be مفاعلن
F=['u--','u-u']; M=['u---','u-u-']
import itertools
def ok(p, last_opts):
    for a,b,c,d in itertools.product(F,M,F,last_opts):
        if p==a+b+c+d: return True
    return False
if __name__=='__main__':
    bad=[]
    for n,a,b in tr.load_script(sys.argv[1]):
        pa,pb=phon(a),phon(b)
        # final syllable of each half anceps (rhyme stretch makes it long)
        oka=ok(pa[:-1]+'-',['u-u-','u---']) ; okb=ok(pb[:-1]+'-',['u-u-','u---','u--'])
        if not (oka and okb): bad.append((n,pa,oka,pb,okb))
    for x in bad: print(x)
    print(len(bad),'verses off-metre')
