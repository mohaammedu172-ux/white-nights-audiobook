"""Script builder for the chapters after the First Night (several characters, nested quotes).

    python -m wn.text2 second_night      (or: nastenkas_history, third_night, fourth_night, morning, all)

Who speaks is worked out automatically, then corrected by hand in script/<chapter>_fixes.json:
  - a quote's speaker comes from its speech tag ("I said" = Dreamer, "said Nastenka" = Nastenka, ...),
    otherwise speakers alternate; such lines are marked "guessed" in the review file
  - a quotation that runs on into the next paragraph keeps its speaker
  - quotes inside a quote ('...') get their own speaker (Grandmother, Lodger, ...), found the same way
  - speech tags are removed, real narration is kept (Dreamer = narrator; inside Nastenka's story, she narrates)
"""
import json, os, re, sys
from .text import ROOT, S, book, clean, chunks

CHAPTERS = {  # key: (heading, next heading, characters who can speak in quotes)
    "second_night": ("SECOND NIGHT", "NASTENKA'S HISTORY", (1, 2)),
    "nastenkas_history": ("NASTENKA'S HISTORY", "THIRD NIGHT", (1, 2)),
    "third_night": ("THIRD NIGHT", "FOURTH NIGHT", (1, 2)),
    "fourth_night": ("FOURTH NIGHT", "MORNING", (1, 2)),
    "morning": ("MORNING", None, (1, 5)),
}
NAME = {1: "Dreamer", 2: "Nastenka", 3: "Grandmother", 4: "Lodger", 5: "Matrona"}
VERBS = r"(said|says|say|cried|answered|asked|interrupted|replied|added|began|exclaimed|whispered|went on|continued|repeated|observed|murmured|shouted|thought|called out|echoed|told \w+)"
WHO_RE = r"(I|she|he|the girl|Nastenka|grandmother|granny|the lodger|our lodger|Matrona|my companion)"
TAG = re.compile(rf"^\W*(and\s+)?(({WHO_RE}\s+{VERBS})|({VERBS}\s+{WHO_RE}))\b(\s+(to|at)\s+(her|him|me|the girl|grandmother))?\W*", re.I)
WHO_OF = [(r"\bI\s+" + VERBS + r"|" + VERBS + r"\s+I\b", "I"), (r"Nastenka|the girl|\bshe\b", "she"),
          (r"grandmother|granny", "grandmother"), (r"lodger|\bhe\b", "he"), (r"Matrona", "matrona")]


def tag_speaker(text, narrator_is):
    """Speaker named by a speech tag in `text`; narrator_is = who 'I' is here (Dreamer, or Nastenka in her story)."""
    m = re.search(rf"({WHO_RE}\s+{VERBS}|{VERBS}\s+{WHO_RE})", text, re.I)
    if not m: return None
    w = m.group(0).lower()
    if re.search(r"\bi\b", w): return narrator_is
    if "grandmother" in w or "granny" in w: return 3
    if "lodger" in w: return 4
    if "matrona" in w: return 5
    if re.search(r"nastenka|the girl", w): return 2
    if re.search(r"\bshe\b", w): return 3 if narrator_is == 2 else 2      # inside Nastenka's story "she" = grandmother
    if re.search(r"\bhe\b", w): return 4
    return None


def split_nested(s):
    """'...' quotes inside a quote -> [(is_nested, text)]; apostrophes inside words are left alone."""
    out, buf, inside = [], "", False
    for i, ch in enumerate(s):
        prev = s[i - 1] if i else " "; nxt = s[i + 1] if i + 1 < len(s) else " "
        if ch == "'" and not inside and not prev.isalpha() and (nxt.isalpha() or nxt in "_"):
            if buf.strip(): out.append((False, buf))
            buf, inside = "", True; continue
        if ch == "'" and inside and not nxt.isalpha() and not prev.isspace():
            out.append((True, buf)); buf, inside = "", False; continue
        buf += ch
    if buf.strip(): out.append((inside, buf))
    return out


def paragraphs(chapter, text=None):
    start, end, _ = CHAPTERS[chapter]
    full = text or book()
    a = full.index(start, full.index("FIRST NIGHT")) + len(start)
    b = full.index(end, a) if end else full.index("\n\n\n\n", a + 200)
    return [p for p in (re.sub(r"\s*\n\s*", " ", p).strip() for p in re.split(r"\n\s*\n", full[a:b])) if p and not set(p) <= set("* ")]


def build_turns(chapter, paras, overrides, nested_over=None):
    nested_over = {int(k): list(v) for k, v in (nested_over or {}).items()}
    cast = CHAPTERS[chapter][2]
    turns, dropped, guessed = [], {}, set()
    open_spk, last_q = None, None
    for p, t in enumerate(paras):
        t = t.replace("_", "")
        parts = t.split('"')
        cont = t.startswith('"') and open_spk is not None
        narr_text = " ".join(parts[0::2])
        spk = overrides.get(str(p))
        if spk is None:
            if cont: spk = open_spk
            else:
                spk = tag_speaker(narr_text, 1)
                if spk is None and len(parts) > 1:
                    spk = [c for c in cast if c != 1][0] if last_q == 1 else 1
                    if last_q is None: spk = cast[0]
                    guessed.add(p)
        last_nested = None
        for i, seg in enumerate(parts):
            if not re.search(r"\w", seg): continue
            if i % 2 == 0:                                            # narration outside quotes: Dreamer
                rest = TAG.sub("", clean(seg)).strip(" ,;.-")
                if len(rest.split()) <= 7:
                    if rest or seg.strip(" ,;."): dropped.setdefault(p, []).append(seg.strip(" ,;."))
                    continue
                turns.append([1, "narr", rest[0].upper() + rest[1:], p, False]); continue
            # speech by spk; it may contain nested quotes
            narrator = spk                                            # inside this speech, "I" = the speaker
            pieces = split_nested(seg)
            for j, (nested, txt) in enumerate(pieces):
                if not nested:
                    rest = TAG.sub("", clean(txt)).strip(" ,;:-")
                    if len(rest.split()) <= 7 and len(pieces) > 1 and TAG.search(clean(txt)):
                        dropped.setdefault(p, []).append(txt.strip(" ,;:")); continue
                    if rest: turns.append([spk, "say", rest, p, p in guessed])
                    continue
                # nested speaker: tag right after, then right before, then cues, then alternation
                after = pieces[j + 1][1][:60] if j + 1 < len(pieces) and not pieces[j + 1][0] else ""
                before = pieces[j - 1][1][-60:] if j and not pieces[j - 1][0] else ""
                ns = tag_speaker(after, narrator) or tag_speaker(before, narrator)
                g = False
                if nested_over.get(p): ns = nested_over[p].pop(0)
                elif ns is None and chapter != "nastenkas_history":
                    ns = narrator                                   # a quote within a speech, said by the speaker
                elif ns is None:
                    if re.search(r",\s*(grandmother|granny)\b|\bgrandmother[?!.]", txt, re.I): ns = narrator
                    elif re.search(r"\bNastenka\b", txt): ns = 3 if "grandmother" in t.lower() and last_nested != 3 else (last_nested if last_nested not in (None, narrator) else 3)
                    elif last_nested is not None: ns = narrator if last_nested != narrator else (last_q_nested if (last_q_nested := getattr(build_turns, "_lqn", None)) else 3)
                    else: ns = narrator
                    g = True
                if ns != narrator: build_turns._lqn = ns
                turns.append([ns, "say", clean(txt).strip(" ,"), p, g]); last_nested = ns
        if len(parts) > 1: last_q = spk
        open_spk = spk if (t.count('"') % 2 == 1) else None
    # a quote interrupted only by a speech tag ("'Listen,' he said, 'you are a good girl'") becomes one line again
    merged = []
    for t in turns:
        if not re.search(r"\w", t[2]): continue
        if merged and t[0] == merged[-1][0] and t[3] == merged[-1][3] and t[1] == merged[-1][1] and t[2][:1].islower():
            merged[-1][2] = merged[-1][2].rstrip(" .,;") + ", " + t[2]; continue
        merged.append(t)
    fix = lambda x: x if x.endswith((".", "!", "?", "...")) else x.rstrip(",;: ") + "."
    return [[s, k, fix(x), p, g] for s, k, x, p, g in merged], dropped


def build(chapter):
    fx_path = S(f"{chapter}_fixes.json")
    fx = json.load(open(fx_path)) if os.path.exists(fx_path) else {"speaker": {}, "replace": [], "global": [[" ... ", "... "], [" ...", "..."]]}
    if not os.path.exists(fx_path): json.dump(fx, open(fx_path, "w"), indent=1)
    paras = paragraphs(chapter)
    for p, old, new in fx.get("book", []):                      # fixes to the book text itself (e.g. a missing quote mark)
        if old not in paras[p]: raise SystemExit(f"book fix no longer matches: ¶{p} {old!r}")
        paras[p] = paras[p].replace(old, new)
    turns, dropped = build_turns(chapter, paras, fx.get("speaker", {}), fx.get("nested", {}))
    for p, old, new in fx.get("replace", []):
        hit = [t for t in turns if t[3] == p and old in t[2]]
        if not hit: raise SystemExit(f"fix no longer matches: ¶{p} {old!r}")
        hit[0][2] = hit[0][2].replace(old, new)
    for t in turns:
        for old, new in fx.get("global", []): t[2] = t[2].replace(old, new)
    lines, prev = [], None
    for s, k, txt, p, g in turns:
        for i, c in enumerate(chunks(txt)):
            if prev is None: pause = 0.0
            elif i: pause = 0.6
            elif prev["p"] != p: pause = 1.0 if prev["speaker"] == s else 0.6
            else: pause = 0.5
            prev = dict(id=f"{chapter}_{len(lines):03d}", p=p, speaker=s, kind=k, text=c, pause_before=pause, guessed=g)
            lines.append(prev)
    json.dump(lines, open(S(f"{chapter}_lines.json"), "w"), indent=1, ensure_ascii=False)
    md = [f"# White Nights — {chapter.replace('_', ' ').title()}: performance script\n",
          f"{len(lines)} lines. **(guessed)** = speaker worked out by alternation, please check. "
          f"Corrections go in `script/{chapter}_fixes.json` (`speaker`: paragraph → 1 Dreamer, 2 Nastenka, 3 Grandmother, 4 Lodger, 5 Matrona).\n\n---"]
    for p in range(len(paras)):
        pl = [l for l in lines if l["p"] == p]
        if not pl: continue
        md.append(f"\n### ¶{p}\n\n> **Book:** {paras[p]}\n")
        md += [f"- `⏸ {l['pause_before']:.2f}s` **{NAME[l['speaker']]}{' (narration)' if l['kind'] == 'narr' else ''}{' (guessed)' if l['guessed'] else ''}:** {l['text']}" for l in pl]
        if dropped.get(p): md.append("\n*Removed (not spoken):* " + " · ".join(f'"{x}"' for x in dropped[p]))
    open(S(f"{chapter}_script.md"), "w").write("\n".join(md) + "\n")
    return lines


if __name__ == "__main__":
    chs = list(CHAPTERS) if sys.argv[1:] in ([], ["all"]) else sys.argv[1:]
    for ch in chs:
        L = build(ch)
        by = {}
        for l in L: by[NAME[l["speaker"]]] = by.get(NAME[l["speaker"]], 0) + 1
        print(f"{ch}: {len(L)} lines, {sum(len(l['text'].split()) for l in L)} words, guessed {sum(l['guessed'] for l in L)}, by speaker {by}")
