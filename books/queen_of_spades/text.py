"""
Build the spoken script for The Queen of Spades (Pushkin, Twitchell tr., Gutenberg #23058).
v2 — fixes header/footer, nested quotes, before/after tags, alternation.
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
}

SPEECH_VERBS = r"(?:said|asked|replied|answered|cried|exclaimed|observed|remarked|continued|added|muttered|whispered|shouted|repeated|inquired|returned|remonstrated|insisted|murmured|interrupted|put in|went on|broke in)"


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
    # Strip anything before the START marker (or before "The Queen of Spades" title)
    start = re.search(r"\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", text, re.I)
    if start:
        text = text[start.end():]
    else:
        # Fallback: find the first real paragraph
        m = re.search(r"(AT the house of Naroumov|The Queen of Spades)", text)
        if m:
            text = text[m.start():]

    # Strip anything from the END marker onward
    end = re.search(r"\*\*\*\s*END OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", text, re.I)
    if end:
        text = text[:end.start()]
    else:
        # Fallback: cut at the first "End of the Project Gutenberg" or "*** END"
        m = re.search(r"(End of (the )?Project Gutenberg|\*\*\*\s*END)", text, re.I)
        if m:
            text = text[:m.start()]

    # Drop copyright line, transcriber notes, etc.
    text = re.sub(r"^Copyright,?\s+\d{4}.*$", "", text, flags=re.M)
    text = re.sub(r"^\s*Transcriber'?s? Note.*$", "", text, flags=re.M)
    return text.strip()


def split_paragraphs(text: str) -> list[str]:
    paras = re.split(r"\n\s*\n", text)
    out = []
    for p in paras:
        p = " ".join(p.split())
        if p and len(p.split()) > 2:  # skip 1-2 word fragments
            out.append(p)
    return out


def find_name_in(text: str) -> int | None:
    """Look for a character name in text. Prefer the one closest to the speech verb."""
    low = text.lower()
    best_role = None
    best_pos = None
    for name, role in NAME_TO_ROLE.items():
        idx = low.find(name)
        if idx >= 0:
            # Prefer a name immediately preceded by a speech verb
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


def split_nested(quote_text: str) -> list[tuple[int | None, str]]:
    """
    Split a double-quoted passage into segments, treating single-quoted
    inner speech as a nested speaker (Saint-Germain inside Tomsky, etc.).
    Returns list of (role_hint, text). role_hint None = outer speaker.
    """
    parts: list[tuple[int | None, str]] = []
    pattern = re.compile(r"'([^']*)'")
    last_end = 0
    for m in pattern.finditer(quote_text):
        before = quote_text[last_end:m.start()]
        if before.strip():
            parts.append((None, before.strip()))
        inner = m.group(1).strip()
        if inner:
            after = quote_text[m.end():m.end() + 60].lower()
            role = find_name_in(after)
            if role is None:
                role = SAINT_GERMAIN  # default for the Tomsky anecdote
            parts.append((role, inner))
        last_end = m.end()
    rest = quote_text[last_end:].strip()
    if rest:
        parts.append((None, rest))
    return parts


def parse_paragraph(para: str, state: dict) -> list[dict]:
    lines: list[dict] = []

    if is_letter_paragraph(para):
        lines.append({"role": NARRATOR, "text": para, "guessed": False, "is_letter": True})
        return lines

    quote_re = re.compile(r'"([^"]*)"')
    last_end = 0
    for m in quote_re.finditer(para):
        before = para[last_end:m.start()]
        quote = m.group(1).strip()
        after = para[m.end():]

        if not quote:
            last_end = m.end()
            continue

        # Determine the outer speaker
        speaker = find_name_in(after) or find_name_in(before)
        guessed = False
        if speaker is None:
            speaker = state.get("expected_next") or state.get("last_speaker") or NARRATOR
            guessed = True

        # Nested single quotes inside this quote
        segments = split_nested(quote)
        for role_hint, seg_text in segments:
            role = role_hint if role_hint is not None else speaker
            seg_guessed = guessed if role_hint is None else True
            lines.append({"role": role, "text": seg_text, "guessed": seg_guessed, "is_letter": False})
            state["last_speaker"] = role

        # Update alternation state: the person just addressed
        after_low = after.lower()
        for name, role in NAME_TO_ROLE.items():
            if name in after_low and role != speaker:
                state["expected_next"] = role
                break

        last_end = m.end()

    # Remaining narration outside quotes
    trailing = para[last_end:].strip()
    # Also narration before the first quote
    first_quote = quote_re.search(para)
    leading = para[:first_quote.start()].strip() if first_quote else ""

    for nar in (leading, trailing):
        if nar and len(nar.split()) > 7:
            lines.append({"role": NARRATOR, "text": nar, "guessed": False, "is_letter": False})
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
    """Apply manual corrections from _fixes.json (role by line id, or text replace)."""
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


def build() -> None:
    raw = fetch_book()
    body = strip_gutenberg(raw)
    paras = split_paragraphs(body)
    state = {"last_speaker": None, "expected_next": None}
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

    all_lines = apply_fixes(all_lines)

    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    (SCRIPT_DIR / "queen_of_spades_lines.json").write_text(
        json.dumps(all_lines, indent=2, ensure_ascii=False), encoding="utf-8")

    md = ["# The Queen of Spades — script review (v2)\n",
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
