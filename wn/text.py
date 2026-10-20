"""Book text -> performance script (lines with speaker and pause before each line).

    python -m wn.text first_night        # rebuilds script/first_night_lines.json + the review .md

Edit script/<chapter>_fixes.json to change the script, never the generated files.
"""
import json, os, re, sys, urllib.request
from functools import reduce

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = lambda *p: os.path.join(ROOT, "script", *p)
BOOK_URL = "https://www.gutenberg.org/cache/epub/36034/pg36034.txt"
CHAPTERS = {"first_night": ("FIRST NIGHT", "SECOND NIGHT", set(range(0, 15)) | {56})}   # chapter: start, end, storytelling paragraphs
PAUSE_S = {"quick": .45, "normal": .6, "answer": .75, "reflective": 1.0, "dramatic": 1.4, "scene": 2.0}
NAME = {1: "Dreamer", 2: "Nastenka"}

SPOKEN = {"to-morrow": "tomorrow", "To-morrow": "Tomorrow", "to-day": "today", "Good-bye": "Goodbye",
          "Good-night": "Goodnight", "--": ", ", "....": "..."}
VERBS = r"(said|say|cried|answered|asked|interrupted|replied|added|began|exclaimed|whispered|went on|continued|repeated|observed|murmured|shouted|thought)"
WHOM = r"(I|she|he|the girl|Nastenka|my companion)"
TAG = re.compile(rf"^\W*({WHOM}\s+{VERBS}|{VERBS}\s+{WHOM})\b(\s+(to|at)\s+(her|him|me|the girl))?\W*", re.I)


def book(cache=None):
    cache = cache or os.path.join(ROOT, ".cache", "white_nights_gutenberg.txt")
    if not os.path.exists(cache):
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        req = urllib.request.Request(BOOK_URL, headers={"User-Agent": "Mozilla/5.0"})
        open(cache, "w", encoding="utf-8").write(urllib.request.urlopen(req, timeout=60).read().decode("utf-8-sig"))
    return open(cache, encoding="utf-8").read().replace("\r", "")


def paragraphs(chapter, text=None):
    start, end, _ = CHAPTERS[chapter]
    full = text or book()
    a = full.index(start) + len(start); b = full.index(end, a)
    return [p for p in (re.sub(r"\s*\n\s*", " ", p).strip() for p in re.split(r"\n\s*\n", full[a:b])) if p]


def clean(t):
    t = reduce(lambda s, kv: s.replace(*kv), SPOKEN.items(), t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\breader\b", "listener", t)                       # heard, not read
    t = re.sub(r"([!?])\.(?!\.)", r"\1", t)
    return re.sub(r"([!?]),", r"\1", t)


def turns_for(chapter, paras):
    tags = {t["p"]: t for t in json.load(open(S(f"{chapter}_tags.json")))["tags"] if "p" in t}
    narrative = CHAPTERS[chapter][2]
    turns, dropped = [], {}
    for p, t in enumerate(paras):
        for old, new in tags[p].get("say", []): t = t.replace(old, new)
        spk = 1 if tags[p]["speaker"] == "dreamer" else 2
        if p in narrative:                                         # storytelling: read in full
            turns.append([1, "say", clean(t.replace('"', "")), p]); continue
        parts = re.split(r'"', t)
        if len(parts) == 1:
            turns.append([spk, "say", clean(t), p]); continue
        for i, seg in enumerate(parts):
            seg = clean(seg)
            if not seg or not re.search(r"\w", seg): continue
            if i % 2 == 1:                                         # inside quotes: speech
                if turns and turns[-1][0] == spk and turns[-1][1] == "say" and turns[-1][3] == p:
                    prev = turns[-1][2]
                    if prev.endswith(",") and seg[:1].isupper() and not seg.startswith("I "): prev = prev[:-1] + "."
                    turns[-1][2] = prev + " " + seg
                else:
                    turns.append([spk, "say", seg, p])
            else:                                                  # outside quotes: speech tag or real narration
                rest = TAG.sub("", seg).strip(" ,;.-")
                if len(rest.split()) <= 7: dropped.setdefault(p, []).append(seg.strip(" ,;."))
                else:
                    rest = rest[0].upper() + rest[1:]
                    turns.append([1, "narr", rest.rstrip(",;") + ("" if rest.endswith((".", "!", "?")) else "."), p])
    fix = lambda x: x if x.endswith((".", "!", "?", "...")) else x.rstrip(",;: ") + "."
    return [[s, k, fix(x), p] for s, k, x, p in turns], dropped


def apply_fixes(chapter, turns):
    fx = json.load(open(S(f"{chapter}_fixes.json")))
    missing = []
    for p, old, new in fx["replace"]:
        hit = [t for t in turns if t[3] == p and old in t[2]]
        if hit: hit[0][2] = hit[0][2].replace(old, new)
        else: missing.append((p, old))
    for t in turns:
        for old, new in fx["global"]: t[2] = t[2].replace(old, new)
    out = []
    for t in turns:
        ins = [x for x in fx["insert_narration_after"] if x[0] == t[3] and x[1] in t[2]]
        if not ins: out.append(t); continue
        p, at, narr = ins[0]; a, b = t[2].split(at, 1)
        out += [[t[0], t[1], (a + at).strip(), p], [1, "narr", narr, p]] + ([[t[0], t[1], b.strip(), p]] if b.strip() else [])
    if missing: raise SystemExit(f"fixes that no longer match the text: {missing}")
    return out


def sentences(t):
    return [p for p in re.split(r'(?<=[.!?…])\s+(?=[A-Z"“(])', t) if p.strip()]


def chunks(t, cap=45):
    """Short pieces for the voice model: whole sentences, <= cap words; only very long sentences split at ; or :"""
    out, cur = [], []
    for s in sentences(t):
        w = len(s.split())
        if cur and sum(len(x.split()) for x in cur) + w > cap: out.append(" ".join(cur)); cur = []
        if w > 90:
            buf = []
            for b in re.split(r'(?<=[;:])\s+', s):
                if buf and sum(len(x.split()) for x in buf) + len(b.split()) > cap: out.append(" ".join(buf)); buf = []
                buf.append(b)
            cur += buf
        else: cur.append(s)
    if cur: out.append(" ".join(cur))
    return out


def lines_for(chapter, turns):
    score = {l["p"]: l for l in json.load(open(S(f"{chapter}_score.json")))["lines"]}
    breath = lambda w: 0.5 if w < 15 else (0.7 if w > 35 else 0.6)
    lines, prev = [], None
    for s, k, txt, p in turns:
        pieces = [(j, c) for j, part in enumerate(txt.split("|")) for c in chunks(part.strip())]
        for i, (j, c) in enumerate(pieces):
            c = c.replace("~", " ")
            if prev is None: pause = 0.0
            elif i > 0: pause = 1.4 if j != pieces[i - 1][0] else (0.35 if prev["text"].endswith((";", ":")) else breath(len(prev["text"].split())))
            elif prev["p"] != p:
                pause = PAUSE_S[score[p]["pause"]]
                if prev["speaker"] == s: pause = max(pause, 1.0)
            else: pause = 0.6
            prev = dict(id=f"{chapter}_{len(lines):03d}", p=p, speaker=s, kind=k, text=c, pause_before=pause)
            lines.append(prev)
    return lines


def mark_interruptions(lines, dropped):
    """The first line of a paragraph whose speech tag said 'interrupted' cuts in over the previous line."""
    firsts = {}
    for l in lines: firsts.setdefault(l["p"], l)
    for p, tags in dropped.items():
        if any("interrupt" in x.lower() for x in tags) and int(p) in firsts: firsts[int(p)]["interrupts"] = True


def review_md(chapter, paras, lines, dropped):
    tags = {t["p"]: t for t in json.load(open(S(f"{chapter}_tags.json")))["tags"] if "p" in t}
    words = sum(len(l["text"].split()) for l in lines)
    md = [f"# White Nights — {chapter.replace('_', ' ').title()}: performance script\n",
          f"{len(lines)} lines, {words:,} words. Generated by `python -m wn.text {chapter}` — edit `script/{chapter}_fixes.json`, not this file.\n",
          "`⏸ 0.60s` = silence before the line. Breaths 0.5–0.7 s (0.35 s inside a split long sentence); replies 0.45–0.75 s; "
          "new paragraph ≥ 1.0 s; dramatic beats 1.4 s.\n\n---"]
    for p in range(len(paras)):
        pl = [l for l in lines if l["p"] == p]
        if not pl: continue
        md.append(f"\n### ¶{p} · {'Dreamer' if tags[p]['speaker'] == 'dreamer' else 'Nastenka'}\n\n> **Book:** {paras[p]}\n")
        md += [f"- `⏸ {l['pause_before']:.2f}s` **{NAME[l['speaker']]}{' (narration)' if l['kind'] == 'narr' else ''}:** {l['text']}" for l in pl]
        if dropped.get(p): md.append("\n*Removed (not spoken):* " + " · ".join(f'"{x}"' for x in dropped[p]))
    return "\n".join(md) + "\n"


def build(chapter):
    paras = paragraphs(chapter)
    turns, dropped = turns_for(chapter, paras)
    lines = lines_for(chapter, apply_fixes(chapter, turns))
    mark_interruptions(lines, dropped)
    json.dump(lines, open(S(f"{chapter}_lines.json"), "w"), indent=1, ensure_ascii=False)
    open(S(f"{chapter}_script.md"), "w").write(review_md(chapter, paras, lines, dropped))
    return lines


if __name__ == "__main__":
    ch = sys.argv[1] if len(sys.argv) > 1 else "first_night"
    L = build(ch)
    print(f"{ch}: {len(L)} lines, {sum(len(l['text'].split()) for l in L)} words")
