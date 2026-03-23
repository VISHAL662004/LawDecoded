from __future__ import annotations

import re

BOILERPLATE_PATTERNS = [
    re.compile(r"digitally signed", re.IGNORECASE),
    re.compile(r"qr code", re.IGNORECASE),
    re.compile(r"downloaded from", re.IGNORECASE),
    re.compile(r"indian kanoon", re.IGNORECASE),
    re.compile(r"dhc server", re.IGNORECASE),
    re.compile(r"\bpage\s+\d+\b", re.IGNORECASE),
    re.compile(r"^\s*\d+\s*$"),
    re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+at\s+\d{1,2}:\d{2}:\d{2}\b", re.IGNORECASE),
]


def sanitize_text(text: str) -> str:
    clean = text.replace("\x00", " ")
    clean = clean.replace("(cid:128)", "Rs.")
    clean = re.sub(r"[\t\r]+", " ", clean)
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    clean = re.sub(r"\s{2,}", " ", clean)
    return clean.strip()


def sentence_split(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+", text)
    return [c.strip() for c in chunks if c.strip()]


def is_boilerplate_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    for pat in BOILERPLATE_PATTERNS:
        if pat.search(s):
            return True
    return False


def remove_boilerplate(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines()]
    filtered = [ln for ln in lines if not is_boilerplate_line(ln)]
    return "\n".join(filtered).strip()
