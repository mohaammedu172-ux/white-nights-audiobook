"""
Build the spoken script for The Queen of Spades (Pushkin, Twitchell tr., Gutenberg #23058).

Run:  python -m books.queen_of_spades.text
Writes:
  books/queen_of_spades/script/queen_of_spades_lines.json
  books/queen_of_spades/script/queen_of_spades_script.md
"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT_DIR = HERE / "script"
CACHE_DIR = HERE / ".cache"
GUTENBERG_URL = "https://www.gutenberg.org/cache/epub/23058/pg23058.txt"

# Role numbers, must match config.json "cast"
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

# Speech tags: (regex, role). Checked against the text after the closing quote.
TAG_PATTERNS = [
    (r"\bHerman\b", HERMAN),
    (r"\bTomsky\b", TOMSKY),
    (r"\bLisaveta\b|\bLizaveta\b", LISAVETA),
    (r"\bCountess\b|\bold woman\b|\bAnna Fedotovna\b", COUNTESS),
    (r"\bTchekalinsky\b|\bChekalinsky\b", TCHEKALINSKY),
    (r"\bNaroumov\b|\bNarumov\b", NAROUMOV),
    (r"\bSourine\b|\bSurin\b", SOURINE),
    (r"\bSaint[- ]Germain\b|\bSt\.? Germain\b", SAINT_GERMAIN),
]


def fetch_book() -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / "queen_of_spades_gutenberg.txt"
    if cache.exists():
        return cache.read_text(encoding="utf-8", errors="replace")
    print(f"Downloading {GUTENBERG_URL} ...")
    data = urllib.request.urlopen(GUTENBERG_URL, timeout=60).read()
    text = data.decode("utf-8", errors="replace")
    cache.write_text(text, encoding="utf-8")
    return text


def strip_gutenberg(text: str) -> str:
    start = re.search(r"\*\*\* ?START OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", text, re.I)
    end = re.search(r"\*\*\* ?END OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", text, re.I)
    if start:
        text = text[start.end():]
    if end:
        text = text[:end.start()]
    return text.strip()


def split_paragraphs(text: str) -> list[str]:
    paras = re.split(r"\n\s*\n", text)
    out = []
    for p in paras:
        p = " ".join(p.split())
        if p:
            out.append(p)
    return out


def find_speaker_after(text_after: str) -> int | None:
    snippet = text_after[:120]
    for pattern, role in TAG_PATTERNS:
        if re.search(pattern, snippet):
            return role
    return None


def find_speaker_before(text_before: str) -> int | None:
    snippet = text_before[-120:]
    for pattern, role in TAG_PATTERNS:
        if re.search(pattern, snippet):
            return role
    return None


def is_letter_paragraph(para: str) -> bool:
    low = para.lower()
    markers = ["dear ", "my dear", "i am writing", "i write to you", "yours truly", "your obedient", "i have the honour"]
    return any(m in low for m in markers)


def parse_paragraph(para: str, state: dict) -> list[dict]:
    """Return a list of {role, text, guessed, is_letter}."""
    lines: list[dict] = []
    if is_letter_paragraph(para):
        lines.append({"role": NARRATOR, "text": para, "guessed": False, "is_letter": True})
        return lines

    quote_re = re.compile(r'"([^"]*)"')
    last_end = 0
    for m in quote_re.finditer(para):
        quote = m.group(1).strip()
        before = para[last_end:m.start()]
        after = para[m.end():]
        if quote:
            speaker = find_speaker_after(after) or find_speaker_before(before)
            guessed = False
            if speaker is None:
                speaker = state["last_speaker"] if state["last_speaker"] else NARRATOR
                guessed = True
            lines.append({"role": speaker, "text": quote, "guessed": guessed, "is_letter": False})
            state["last_speaker"] = speaker
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
    final = []
    for c in out:
        if len(c.split()) > max_words * 2:
            parts = re.split(r"(?<=[,;:])\s+", c)
            acc = ""
            for p in parts:
                if not acc:
                    acc = p
                elif len((acc + " " + p).split()) <= max_words:
                    acc += " " + p
                else:
                    final.append(acc)
                    acc = p
            if acc:
                final.append(acc)
        else:
            final.append(c)
    return final


def build() -> None:
    raw = fetch_book()
    body = strip_gutenberg(raw)
    paras = split_paragraphs(body)
    state = {"last_speaker": None}
    all_lines: list[dict] = []
    for i, para in enumerate(paras):
        for line in parse_paragraph(para, state):
            for chunk in chunk_line(line["text"]):
                all_lines.append({
                    "id": len(all_lines) + 1,
                    "paragraph": i + 1,
                    "role": line["role"],
                    "speaker": ROLE_NAMES[line["role"]],
                    "text": chunk,
                    "guessed": line["guessed"],
                    "is_letter": line["is_letter"],
                })

    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    (SCRIPT_DIR / "queen_of_spades_lines.json").write_text(
        json.dumps(all_lines, indent=2, ensure_ascii=False), encoding="utf-8")

    md = ["# The Queen of Spades — script review\n",
          "Guessed speakers are marked **(guessed)**. Check those first.\n"]
    for line in all_lines:
        tag = " **(guessed)**" if line["guessed"] else ""
        letter = " [letter]" if line["is_letter"] else ""
        md.append(f"**{line['id']}. {line['speaker']}**{tag}{letter}  \n> {line['text']}\n")
    (SCRIPT_DIR / "queen_of_spades_script.md").write_text("\n".join(md), encoding="utf-8")

    print(f"Wrote {len(all_lines)} lines to {SCRIPT_DIR}")
    guessed = sum(1 for l in all_lines if l["guessed"])
    print(f"Guessed speakers: {guessed} / {len(all_lines)}")


if __name__ == "__main__":
    build()
