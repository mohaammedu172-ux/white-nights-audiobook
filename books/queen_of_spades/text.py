"""
Build the spoken script for The Queen of Spades (Pushkin, Twitchell tr., Gutenberg #23058).
v3 — fixes apostrophes, unmatched quotes, nested anecdote, adds conversation-state inference.
v4 — writes the format wn/run.py reads (id, speaker, p, kind, pause_before, interrupts, text) to
     script/queen_of_spades_lines.json (source of truth) and a copy at <repo>/script/ (transient, git-ignored).
     Reads the book from source/gutenberg_23058.txt (downloads it there if missing).

    python books/queen_of_spades/text.py        or        python -m books.queen_of_spades.text
"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT_DIR = HERE / "script"
SOURCE = HERE / "source" / "gutenberg_23058.txt"
REPO_SCRIPT_DIR = HERE.parent.parent / "script"            # where wn/run.py reads <chapter>_lines.json
CHAPTER = "queen_of_spades"
DRAMATIC = {82, 84, 85}                                     # line ids that get a 1.4 s pause before them
PAUSE = {"same": 0.6, "reply": 0.75, "new_paragraph": 1.0, "dramatic": 1.4}
GUTENBERG_URL = "https://www.gutenberg.org/cache/epub/23058/pg23058.txt"

NARRATOR = 1
HERMAN = 2
TOMSKY = 3
LISAVETA = 4
COUNTESS = 5
TCHEKALINSKY = 6
NAROUMOV = 7
SOURINE = 8
SAINT_GERMAIN = 9

ROLE_NAMES = {
    NARRATOR: "Narrator", HERMAN: "Herman", TOMSKY: "Tomsky",
    LISAVETA: "Lisaveta", COUNTESS: "Countess", TCHEKALINSKY: "Tchekalinsky",
    NAROUMOV: "Naroumov", SOURINE: "Sourine", SAINT_GERMAIN: "Saint-Germain",
}

NAME_TO_ROLE = {
    "herman": HERMAN, "hermann": HERMAN,
    "tomsky": TOMSKY, "tomski": TOMSKY,
    "lisaveta": LISAVETA, "lizaveta": LISAVETA, "lisa": LISAVETA,
    "countess": COUNTESS, "anna fedorovna": COUNTESS, "anna fedotovna": COUNTESS,
    "tchekalinsky": TCHEKALINSKY, "chekalinsky": TCHEKALINSKY,
    "naroumov": NAROUMOV, "narumov": NAROUMOV,
    "sourine": SOURINE, "surin": SOURINE,
    "saint-germain": SAINT_GERMAIN, "saint germain": SAINT_GERMAIN,
    "st. germain": SAINT_GERMAIN, "st germain": SAINT_GERMAIN,
    "the count": SAINT_GERMAIN,  # inside Tomsky's anecdote only
}

SPEECH_VERBS = r"(?:said|asked|replied|answered|cried|exclaimed|observed|remarked|continued|added|muttered|whispered|shouted|repeated|inquired|returned|remonstrated|insisted|murmured|interrupted|put in|went on|broke in|reflected)"


def fetch_book() -> str:
    if not SOURCE.exists():
        SOURCE.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {GUTENBERG_URL} -> {SOURCE}")
        req = urllib.request.Request(GUTENBERG_URL, headers={"User-Agent": "Mozilla/5.0"})
        SOURCE.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    return SOURCE.read_bytes().decode("utf-8-sig", errors="replace").replace("\r\n", "\n").replace("\r", "\n")


def strip_gutenberg(text: str) -> str:
    start = re.search(r"\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", text, re.I)
    if start:
        text = text[start.end():]
    else:
        m = re.search(r"(AT the house of Naroumov)", text)
        if m:
            text = text[m.start():]
    end = re.search(r"\*\*\*\s*END OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", text, re.I)
    if end:
        text = text[:end.start()]
    else:
        m = re.search(r"(End of (the )?Project Gutenberg|\*\*\*\s*END)", text, re.I)
        if m:
            text = text[:m.start()]
    text = re.sub(r"\n\s*End of (the )?Project Gutenberg.*\Z", "", text, flags=re.I | re.S)   # old-style footer line
    text = re.sub(r"^Copyright,?\s+\d{4}.*$", "", text, flags=re.M)
    text = re.sub(r"^\s*Transcriber'?s? Note.*$", "", text, flags=re.M)
    return text.strip()


def split_paragraphs(text: str) -> list[str]:
    paras = re.split(r"\n\s*\n", text)
    out = []
    for p in paras:
        p = " ".join(p.split())
        if p and len(p.split()) > 2:
            out.append(p)
    return out


def find_name_in(text: str) -> int | None:
    low = text.lower()
    best_role = None
    best_pos = None
    for name, role in NAME_TO_ROLE.items():
        idx = low.find(name)
        if idx >= 0:
            before = low[max(0, idx - 30):idx]
            is_tagged = re.search(SPEECH_VERBS + r"\s*$", before) is not None
            score = (0 if is_tagged else 1, idx)
            if best_pos is None or score < best_pos:
                best_pos = score
                best_role = role
    return best_role


def is_letter_paragraph(para: str) -> bool:
    low = para.lower()
    markers = ["dear ", "my dear", "i am writing", "i write to you",
               "yours truly", "your obedient", "i have the honour",
               "i have the honor"]
    return any(m in low for m in markers)


def is_apostrophe(text: str, pos: int) -> bool:
    """True if the ' at pos is an apostrophe inside a word, not a quote."""
    before = text[pos - 1] if pos > 0 else " "
    after = text[pos + 1] if pos + 1 < len(text) else " "
    return before.isalpha() and after.isalpha()


def find_closing_single(text: str, start: int) -> int:
    """From start+1, find a ' that is not an apostrophe. Return -1 if none."""
    i = start + 1
    while i < len(text):
        if text[i] == "'" and not is_apostrophe(text, i):
            return i
        i += 1
    return -1


def split_nested(quote_text: str, outer_role: int) -> list[tuple[int, str]]:
    """
    Split a double-quoted passage into segments.
    Single quotes '...' inside are nested speech.
    Outer speech = outer_role; nested = find name in following 60 chars or default Saint-Germain.
    """
    parts: list[tuple[int, str]] = []
    i = 0
    buf_start = 0
    while i < len(quote_text):
        if quote_text[i] == "'" and not is_apostrophe(quote_text, i):
            close = find_closing_single(quote_text, i)
            if close > i + 1:
                # flush outer text
                if quote_text[buf_start:i].strip():
                    parts.append((outer_role, quote_text[buf_start:i].strip()))
                inner = quote_text[i + 1:close].strip()
                if inner:
                    after = quote_text[close + 1:close + 80].lower()
                    role = find_name_in(after)
                    if role is None:
                        role = COUNTESS if "grandmother" in after or "she" in after[:20] else SAINT_GERMAIN
                    parts.append((role, inner))
                buf_start = close + 1
                i = close + 1
                continue
        i += 1
    if quote_text[buf_start:].strip():
        parts.append((outer_role, quote_text[buf_start:].strip()))
    return parts


def clean_quotes(text: str) -> str:
    """Remove unmatched leading/trailing double quotes."""
    text = text.strip()
    while text.startswith('"') and text.count('"') == 1:
        text = text[1:].strip()
    while text.endswith('"') and text.count('"') == 1:
        text = text[:-1].strip()
    return text


def parse_paragraph(para: str, state: dict) -> list[dict]:
    lines: list[dict] = []

    if is_letter_paragraph(para):
        lines.append({"role": NARRATOR, "text": para, "guessed": False, "is_letter": True})
        return lines

    # Tomsky anecdote special case: paragraph starts with a quote and contains nested "'...'"
    has_nested = bool(re.search(r"\"'.*?'", para))
    if has_nested:
        outer = find_name_in(para[:80]) or state.get("last_speaker") or TOMSKY
        # strip outer quotes
        inner_text = para.strip()
        if inner_text.startswith('"'):
            inner_text = inner_text[1:]
        if inner_text.endswith('"'):
            inner_text = inner_text[:-1]
        for role, seg in split_nested(inner_text, outer):
            lines.append({"role": role, "text": clean_quotes(seg),
                          "guessed": role != outer, "is_letter": False})
        state["last_speaker"] = outer
        return lines

    quote_re = re.compile(r'"([^"]*)"')
    last_end = 0
    first_quote = quote_re.search(para)

    # leading narration
    if first_quote:
        leading = para[:first_quote.start()].strip()
        if leading and len(leading.split()) > 7:
            lines.append({"role": NARRATOR, "text": leading, "guessed": False, "is_letter": False})

    for m in quote_re.finditer(para):
        before = para[last_end:m.start()]
        quote = m.group(1).strip()
        after = para[m.end():]

        if not quote:
            last_end = m.end()
            continue

        # nested single quotes inside this double quote?
        if "'" in quote and any(not is_apostrophe(quote, j) for j, c in enumerate(quote) if c == "'"):
            outer = find_name_in(after) or find_name_in(before) or state.get("last_speaker") or NARRATOR
            for role, seg in split_nested(quote, outer):
                lines.append({"role": role, "text": clean_quotes(seg),
                              "guessed": role != outer, "is_letter": False})
                state["last_speaker"] = role
        else:
            speaker = find_name_in(after) or find_name_in(before)
            guessed = False
            if speaker is None:
                # Plan A: infer from conversation state
                speaker = state.get("expected_next") or state.get("last_speaker") or NARRATOR
                guessed = True
            lines.append({"role": speaker, "text": clean_quotes(quote),
                          "guessed": guessed, "is_letter": False,
                          "interrupts": bool(re.match(r"\W*(\w+\s+){0,3}(interrupted|broke in)", after, re.I))})
            state["last_speaker"] = speaker

        # update expected_next: person addressed in the "after" text
        after_low = after.lower()
        for name, role in NAME_TO_ROLE.items():
            if name in after_low and role != state.get("last_speaker"):
                state["expected_next"] = role
                break

        last_end = m.end()

    trailing = para[last_end:].strip()
    if trailing and len(trailing.split()) > 7:
        lines.append({"role": NARRATOR, "text": trailing, "guessed": False, "is_letter": False})

    return lines


def chunk_line(text: str, max_words: int = 45) -> list[str]:
    if len(text.split()) <= max_words:
        return [text]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out, buf = [], ""
    for s in sentences:
        if not buf:
            buf = s
        elif len((buf + " " + s).split()) <= max_words:
            buf += " " + s
        else:
            out.append(buf)
            buf = s
    if buf:
        out.append(buf)
    return out


def apply_fixes(lines: list[dict]) -> list[dict]:
    fixes_path = SCRIPT_DIR / "queen_of_spades_fixes.json"
    if not fixes_path.exists():
        return lines
    fixes = json.loads(fixes_path.read_text(encoding="utf-8"))
    by_id = {l["id"]: l for l in lines}
    for fid, role in fixes.get("roles", {}).items():
        if int(fid) in by_id:
            by_id[int(fid)]["role"] = role
            by_id[int(fid)]["speaker"] = ROLE_NAMES[role]
            by_id[int(fid)]["guessed"] = False
    for fid, new_text in fixes.get("replace", {}).items():
        if int(fid) in by_id:
            by_id[int(fid)]["text"] = new_text
    return lines


def pause_for(line: dict, prev: dict | None) -> float:
    if prev is None:
        return 0.0
    if line["n"] in DRAMATIC:
        return PAUSE["dramatic"]
    if line["role"] != prev["role"]:
        return PAUSE["reply"]
    if line["p"] != prev["p"]:
        return PAUSE["new_paragraph"]
    return PAUSE["same"]


def build() -> list[dict]:
    raw = fetch_book()
    body = strip_gutenberg(raw)
    paras = split_paragraphs(body)
    state = {"last_speaker": None, "expected_next": None}
    work: list[dict] = []
    for i, para in enumerate(paras):
        for line in parse_paragraph(para, state):
            for k, chunk in enumerate(chunk_line(line["text"])):
                work.append({"id": len(work) + 1, "paragraph": i + 1, "role": line["role"],
                             "speaker": ROLE_NAMES[line["role"]], "text": chunk, "guessed": line["guessed"],
                             "interrupts": bool(line.get("interrupts")) and k == 0})

    work = apply_fixes(work)                       # fixes are keyed by the numeric line id (v3 numbering)

    lines, prev = [], None
    for w in work:
        line = {"n": w["id"], "p": w["paragraph"], "role": w["role"]}
        out = {
            "id": str(w["id"]),
            "speaker": str(w["role"]),
            "p": w["paragraph"],
            "kind": "narr" if w["role"] == NARRATOR else "say",
            "pause_before": pause_for(line, prev),
            "interrupts": w["interrupts"],
            "text": w["text"],
            "guessed": w["guessed"],
            "role": w["role"],
            "speaker_name": ROLE_NAMES[w["role"]],
        }
        lines.append(out); prev = line

    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(lines, indent=2, ensure_ascii=False)
    (SCRIPT_DIR / f"{CHAPTER}_lines.json").write_text(payload, encoding="utf-8")
    REPO_SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    (REPO_SCRIPT_DIR / f"{CHAPTER}_lines.json").write_text(payload, encoding="utf-8")   # copy for wn/run.py

    md = ["# The Queen of Spades — script review (v4)\n",
          "Guessed speakers are marked **(guessed)**. `⏸` = silence before the line in seconds.\n"]
    for l in lines:
        tag = " **(guessed)**" if l["guessed"] else ""
        cut = " [interrupts]" if l["interrupts"] else ""
        md.append(f"**{l['id']}. {l['speaker_name']}**{tag}{cut} `⏸ {l['pause_before']:.2f}s`  \n> {l['text']}\n")
    md.append("\n---\nFields in `queen_of_spades_lines.json`: `id` (string), `speaker` (role number as a string, the key in "
              "config.json `voices`), `p` (paragraph), `kind` (`narr` for the Narrator, `say` for everyone else), "
              "`pause_before` (s: 0.6 same speaker, 0.75 reply, 1.0 new paragraph by the same speaker, 1.4 lines "
              + ", ".join(map(str, sorted(DRAMATIC))) + "), `interrupts`, `text`, `guessed`, `role` (int), `speaker_name`.\n")
    (SCRIPT_DIR / f"{CHAPTER}_script.md").write_text("\n".join(md), encoding="utf-8")

    print(f"Wrote {len(lines)} lines to {SCRIPT_DIR} (copy: {REPO_SCRIPT_DIR / (CHAPTER + '_lines.json')})")
    print(f"Guessed speakers: {sum(1 for l in lines if l['guessed'])} / {len(lines)}")
    return lines


if __name__ == "__main__":
    build()
