#!/usr/bin/env python3
"""
fix_dataset.py — Clean and enrich legal NLP dataset splits using structured metadata.

Fixes applied
─────────────
NER       : remove column-marker tokens (A–H), page-header runs, corrupted Unicode
            tokens; overlay entity tags from actual party/judge names in metadata.
Keypoints : filter fragment sentences (< 20 chars, abbreviations, citation-only);
            improve label heuristic with stronger keyword signals.
Summaries : strip page-header noise from source text; prepend structured metadata
            header (case name, case no, date, disposal) to every summary target.

All three datasets also receive an optional `meta` sidecar field per record so
downstream models can condition on structured metadata.

Usage
─────
  # Dry-run – inspect output, no files written:
  python fix_dataset.py --dry-run --limit 50

  # Only val & test (skip large train files):
  python fix_dataset.py --splits val test

  # Full run – overwrites all 9 JSONL split files in-place:
  python fix_dataset.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit(
        "beautifulsoup4 is required but not installed.\n"
        "Run: pip install beautifulsoup4"
    )

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
SPLITS_DIR = BASE / "data" / "processed" / "splits"
META_PREVIEW = BASE / "data" / "processed" / "metadata_preview.json"
RAW_JUDGMENTS = BASE / "data" / "raw_judgments"

# ── NER label indices (matches step2_prepare_supervision.py) ─────────────────
# 0=O  1=B-PETITIONER  2=B-RESPONDENT  3=B-JUDGE  4=B-SECTION_OF_LAW
# 5=B-DATE  6=B-PUNISHMENT  7=B-COURT_NAME
LABELS = [
    "O",
    "B-PETITIONER",
    "B-RESPONDENT",
    "B-JUDGE",
    "B-SECTION_OF_LAW",
    "B-DATE",
    "B-PUNISHMENT",
    "B-COURT_NAME",
]

# ── Noise / OCR patterns ──────────────────────────────────────────────────────
# Single uppercase column markers printed in SCR bound volumes (A–H columns)
_COLUMN_MARKER = re.compile(r"^[A-H]$")
# Corrupted tokens containing Unicode escape brackets like [U2022] or [U20B9]
_UNICODE_BRACKET = re.compile(r"\[U[0-9A-Fa-f]{4,6}\]")
# SCR citation opener: [YYYY]
_SCR_CITATION = re.compile(r"^\[\d{4}\]$")
# Standalone 3-4 digit page numbers
_PAGE_NUM = re.compile(r"^\d{3,4}$")
# Pure punctuation/symbol tokens that add no signal
_NOISE_SYMBOLS = frozenset({"•", "·", "∙", "∶", "…", "...", "::", "~~", "~·", "~", ";;"})

DATE_PATTERN = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")

MONTH_MAP: dict[str, str] = {
    "01": "JANUARY",  "02": "FEBRUARY", "03": "MARCH",
    "04": "APRIL",    "05": "MAY",      "06": "JUNE",
    "07": "JULY",     "08": "AUGUST",   "09": "SEPTEMBER",
    "10": "OCTOBER",  "11": "NOVEMBER", "12": "DECEMBER",
}

# ── Metadata HTML parsing ────────────────────────────────────────────────────

def _parse_raw_html(html: str) -> dict[str, Any]:
    """Extract structured fields from a judgment's raw_html snippet."""
    soup = BeautifulSoup(html, "html.parser")
    result: dict[str, Any] = {}

    # Case name from aria-label of the judgment PDF-link button.
    # The judgment button always has id="link_<N>"; the modal "Close" button
    # also carries an aria-label so we must be specific here.
    btn = soup.find("button", id=re.compile(r"^link_\d+$"))
    if btn is None:
        # Fallback: first button whose aria-label ends with " pdf" and has enough length
        for b in soup.find_all("button", attrs={"aria-label": True}):
            lbl = str(b.get("aria-label", "")).strip()
            if lbl.lower().endswith(" pdf") and len(lbl) > 20:
                btn = b
                break

    case_name = ""
    if btn:
        label = str(btn.get("aria-label", "")).strip()
        if label.lower().endswith(" pdf"):
            label = label[:-4].strip()
        case_name = label
    result["case_name"] = case_name

    # Petitioner / respondent: split on " versus " first, " v. " as fallback
    m = re.split(r"\s+versus\s+|\s+v\.\s+", result["case_name"], maxsplit=1, flags=re.IGNORECASE)
    result["petitioner"] = m[0].strip() if m else ""
    result["respondent"] = m[1].strip() if len(m) > 1 else ""

    # Judges from <strong>Coram : …</strong>
    judges: list[str] = []
    for strong in soup.find_all("strong"):
        raw = strong.get_text(" ", strip=True)
        if raw.startswith("Coram"):
            coram = re.sub(r"Coram\s*:\s*", "", raw).strip()
            coram = re.sub(r"\*", "", coram)          # strip author marker
            for name in re.split(r",\s*", coram):
                name = name.strip()
                if name:
                    judges.append(name)
            break
    result["judges"] = judges

    # Decision date, case no, disposal nature, bench from caseDetailsTD strong
    result.update({"decision_date": "", "case_no": "", "disposal_nature": "", "bench_size": ""})
    details = soup.find("strong", class_="caseDetailsTD")
    if details:
        fonts = [f.get_text(strip=True) for f in details.find_all("font")]
        keys = ["decision_date", "case_no", "disposal_nature", "bench_size"]
        for k, v in zip(keys, fonts):
            result[k] = v

    # CNR hidden input
    cnr_inp = soup.find("input", {"id": "cnr"})
    result["cnr"] = cnr_inp.get("value", "") if cnr_inp else ""

    return result


def build_metadata_lookup() -> dict[str, dict[str, Any]]:
    """Return path_key→parsed_metadata for all available judgment metadata files.

    path_key matches the 'path' field (e.g. '2013_5_267_275') and is also the
    doc_id after stripping the language suffix (_EN, _HIN, etc.).
    """
    lookup: dict[str, dict[str, Any]] = {}

    # 1) Walk raw_judgments/YEAR/metadata/*.json  (primary source)
    raw_count = 0
    for meta_file in sorted(RAW_JUDGMENTS.rglob("metadata/*.json")):
        try:
            record: dict = json.loads(meta_file.read_text(encoding="utf-8", errors="replace"))
            path_key: str = record.get("path") or meta_file.stem
            parsed = _parse_raw_html(record.get("raw_html", ""))
            parsed["path"] = path_key
            parsed["scraped_at"] = record.get("scraped_at", "")
            parsed["citation_year"] = record.get("citation_year", "")
            lookup[path_key] = parsed
            raw_count += 1
        except Exception:
            pass
    print(f"  {raw_count} records from raw_judgments/")

    # 2) metadata_preview.json fills any gaps
    if META_PREVIEW.exists():
        try:
            preview = json.loads(META_PREVIEW.read_text(encoding="utf-8", errors="replace"))
            records: list[dict] = preview if isinstance(preview, list) else list(preview.values())
            added = 0
            for record in records:
                path_key = record.get("path", "")
                if path_key and path_key not in lookup:
                    parsed = _parse_raw_html(record.get("raw_html", ""))
                    parsed["path"] = path_key
                    parsed["scraped_at"] = record.get("scraped_at", "")
                    parsed["citation_year"] = record.get("citation_year", "")
                    lookup[path_key] = parsed
                    added += 1
            print(f"  {added} additional records from metadata_preview.json")
        except Exception as exc:
            print(f"  Warning: could not read metadata_preview.json – {exc}")

    return lookup


def get_meta(doc_id: str, lookup: dict[str, dict]) -> dict[str, Any] | None:
    """Map a doc_id like '2013_5_267_275_EN' to its parsed metadata record."""
    key = re.sub(r"_(EN|HIN|GUJ|PUN|MAR|TAM|TEL|KAN|ORI|BEN|ASS)$", "", doc_id)
    return lookup.get(key)


# ── Token-level cleaning ──────────────────────────────────────────────────────

def _is_noise_token(tok: str) -> bool:
    """Return True for tokens that carry no linguistic signal."""
    if _COLUMN_MARKER.match(tok):
        return True
    if _UNICODE_BRACKET.search(tok):
        return True
    if tok in _NOISE_SYMBOLS:
        return True
    return False


def _page_header_skip(tokens: list[str], i: int) -> int:
    """Return number of tokens to skip if position i starts an SCR page-header run.

    E.g.  [2016]  9  S.C.R.  771   →  skip 4 tokens
    """
    if i >= len(tokens) or not _SCR_CITATION.match(tokens[i]):
        return 0
    j = i + 1
    while j < len(tokens) and j < i + 5:
        t = tokens[j].upper()
        if t == "S.C.R." or _PAGE_NUM.match(t) or tokens[j].isdigit():
            j += 1
        else:
            break
    return j - i if j > i + 1 else 0


def clean_token_sequence(
    tokens: list[str], tags: list[int]
) -> tuple[list[str], list[int]]:
    """Drop noise/corruption tokens while keeping their associated tags aligned."""
    out_toks: list[str] = []
    out_tags: list[int] = []
    # Normalise tag list length
    tags = list(tags) + [0] * max(0, len(tokens) - len(tags))
    tags = tags[: len(tokens)]

    i = 0
    while i < len(tokens):
        skip = _page_header_skip(tokens, i)
        if skip:
            i += skip
            continue
        if _is_noise_token(tokens[i]):
            i += 1
            continue
        out_toks.append(tokens[i])
        out_tags.append(tags[i])
        i += 1
    return out_toks, out_tags


# ── NER entity enrichment ────────────────────────────────────────────────────

_STOP_NAME_TOKENS = frozenset({
    "of", "and", "the", "by", "in", "at", "for", "vs", "v", "versus",
    "d", "lrs", "ors", "anr", "oths", "others",
    "mr", "mrs", "ms", "dr", "sri", "shri", "smt",
    "justice", "judge", "honble", "hon'ble", "chief", "jj", "cj", "j",
})


def _name_keywords(name: str) -> list[str]:
    """Extract significant tokens from a metadata name string for entity matching."""
    if not name:
        return []
    parts = re.split(r"[\s,]+", name.strip())
    out: list[str] = []
    for p in parts:
        clean = re.sub(r"[.()\[\]&'*]", "", p).strip().upper()
        if len(clean) > 2 and clean.lower() not in _STOP_NAME_TOKENS:
            out.append(clean)
    return out


def enrich_ner_tags(
    tokens: list[str], tags: list[int], meta: dict[str, Any]
) -> list[int]:
    """Overlay metadata-derived entity spans on existing pseudo-NER tags.

    Existing non-zero tags are preserved; metadata enrichment adds labels where
    the pseudo-NER keyword approach missed actual entity tokens.
    """
    new_tags = list(tags)

    pet_kw = set(_name_keywords(meta.get("petitioner", "")))
    resp_kw = set(_name_keywords(meta.get("respondent", "")))
    judge_kw: set[str] = set()
    for jname in meta.get("judges", []):
        judge_kw.update(_name_keywords(jname))

    for i, tok in enumerate(tokens):
        tok_clean = re.sub(r"[.,;:()\[\]{}\-'\"*•·~]", "", tok).strip().upper()
        if len(tok_clean) < 3:
            continue
        # Judge tokens take priority (most distinctive names)
        if tok_clean in judge_kw:
            new_tags[i] = 3  # B-JUDGE
        elif tok_clean in pet_kw and new_tags[i] == 0:
            new_tags[i] = 1  # B-PETITIONER
        elif tok_clean in resp_kw and new_tags[i] == 0:
            new_tags[i] = 2  # B-RESPONDENT

    # Validate DATE tags against actual decision date from metadata
    ddm = meta.get("decision_date", "")
    if ddm:
        parts = re.split(r"[-/]", ddm)
        if len(parts) == 3:
            month_name = MONTH_MAP.get(parts[1], "")
            year = parts[2]
            for i, tok in enumerate(tokens):
                tok_up = tok.upper().strip(".,;:")
                # Tag the year token when preceded by the matching month name
                if tok_up == year and i > 0:
                    prev = tokens[i - 1].upper().strip(".,;:")
                    if prev == month_name:
                        new_tags[i] = 5  # B-DATE

    return new_tags


# ── Keypoints utilities ───────────────────────────────────────────────────────

_FRAGMENT_PATTERNS = [
    re.compile(r"^[A-Z]\.$"),          # single letter abbreviation: "A." "B."
    re.compile(r"^v\.$", re.I),        # "v." (versus abbreviation)
    re.compile(r"^\d+[.):]?$"),        # bare numbers: "1" "2." "3)"
    re.compile(r"^\[\d{4}\]\s*\d"),    # "[2016] 9 …" citation header
    re.compile(r"^[IVX]+\.$"),         # Roman numerals: "I." "II." "IV."
]


def is_valid_sentence(sentence: str) -> bool:
    """Return False for fragment or noise sentences that should be dropped."""
    s = sentence.strip()
    if len(s) < 20:
        return False
    for pat in _FRAGMENT_PATTERNS:
        if pat.match(s):
            return False
    # Require at least 4 whitespace-delimited words
    if len(s.split()) < 4:
        return False
    return True


def improved_key_label(sentence: str, meta: dict[str, Any] | None = None) -> str:
    """Return a keypoint label with stronger signals than the original heuristic."""
    low = sentence.lower()

    # Strong DECISION: disposition verb + case type noun together
    if re.search(r"\b(dismiss|allow|quash|set aside|affirm|uphold|overrule)\b", low):
        if re.search(r"\b(appeal|petition|writ|suit|complaint|application)\b", low):
            return "DECISION"

    # REASONING trigger: "Held :" or "HELD :"
    if re.search(r"\bheld\s*:", low):
        return "REASONING"

    # Sentence opening with a judge surname from metadata
    if meta:
        for jname in meta.get("judges", []):
            parts = jname.split()
            surname = parts[-1].strip(".") if parts else ""
            if surname and len(surname) > 3 and low.startswith(surname.lower()):
                return "REASONING"

    # Fall back to original pseudo_key_label logic
    if "issue" in low or "question" in low:
        return "ISSUE"
    if "submitted" in low or "contended" in low or "argued" in low:
        return "ARGUMENT"
    if "because" in low or "therefore" in low or "held" in low:
        return "REASONING"
    if "ordered" in low or "dismissed" in low or "allowed" in low or "appeal" in low:
        return "DECISION"
    return "FACT"


# ── Summary utilities ─────────────────────────────────────────────────────────

_HEADER_NOISE = re.compile(
    r"\d{3,4}\s+SUPREME\s+COURT\s+REPORTS\s+\[\d{4}\]\s+\d+\s+S\.C\.R\.",
    re.IGNORECASE,
)
_INLINE_COLUMN = re.compile(r"(?<!\w)\s+[A-H]\s+(?!\w)")


def clean_source_text(text: str) -> str:
    """Remove SCR page-header noise and stray column markers from source text."""
    text = _HEADER_NOISE.sub(" ", text)
    text = _INLINE_COLUMN.sub(" ", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def build_summary_target(original: str, meta: dict[str, Any] | None) -> str:
    """Prepend a structured metadata header to the existing summary target."""
    if not meta:
        return original

    parts: list[str] = []
    if meta.get("case_name"):
        parts.append(meta["case_name"])
    if meta.get("case_no"):
        parts.append(f"({meta['case_no']})")
    if meta.get("decision_date"):
        parts.append(meta["decision_date"])
    if meta.get("disposal_nature"):
        parts.append(f"[{meta['disposal_nature']}]")

    header = " – ".join(p for p in parts if p)
    if header:
        return f"{header}. {original}"
    return original


# ── JSONL sidecar helper ──────────────────────────────────────────────────────

def _meta_sidecar(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_name":       meta.get("case_name", ""),
        "petitioner":      meta.get("petitioner", ""),
        "respondent":      meta.get("respondent", ""),
        "judges":          meta.get("judges", []),
        "decision_date":   meta.get("decision_date", ""),
        "case_no":         meta.get("case_no", ""),
        "disposal_nature": meta.get("disposal_nature", ""),
    }


# ── Atomic file write ─────────────────────────────────────────────────────────

def _atomic_write(dst: Path, lines: list[str]) -> None:
    """Write lines to a sibling temp file then atomically rename to dst."""
    fd, tmp = tempfile.mkstemp(dir=dst.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for line in lines:
                fh.write(line + "\n")
        os.replace(tmp, dst)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ── Per-split processing ──────────────────────────────────────────────────────

def process_ner(
    split: str,
    lookup: dict[str, dict],
    dry_run: bool,
    limit: int,
) -> dict[str, Any]:
    path = SPLITS_DIR / f"ner_{split}.jsonl"
    if not path.exists():
        return {"skipped": True, "reason": "file not found"}

    stats: dict[str, Any] = {
        "total": 0, "meta_hit": 0,
        "tokens_before": 0, "tokens_after": 0,
        "tags_enriched": 0,
    }
    out: list[str] = []

    with path.open(encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.rstrip("\n")
            if not line:
                continue
            stats["total"] += 1
            if limit and stats["total"] > limit:
                break
            try:
                rec: dict = json.loads(line)
            except json.JSONDecodeError:
                continue

            tokens: list[str] = rec.get("tokens", [])
            tags: list[int] = rec.get("tags", [0] * len(tokens))

            stats["tokens_before"] += len(tokens)
            tokens, tags = clean_token_sequence(tokens, tags)
            stats["tokens_after"] += len(tokens)

            meta = get_meta(rec["doc_id"], lookup)
            if meta:
                stats["meta_hit"] += 1
                before_nz = sum(1 for t in tags if t != 0)
                tags = enrich_ner_tags(tokens, tags, meta)
                after_nz = sum(1 for t in tags if t != 0)
                stats["tags_enriched"] += max(0, after_nz - before_nz)
                rec["meta"] = _meta_sidecar(meta)

            rec["tokens"] = tokens
            rec["tags"] = tags
            out.append(json.dumps(rec, ensure_ascii=False))

    if not dry_run:
        _atomic_write(path, out)
    return stats


def process_keypoints(
    split: str,
    lookup: dict[str, dict],
    dry_run: bool,
    limit: int,
) -> dict[str, Any]:
    path = SPLITS_DIR / f"keypoints_{split}.jsonl"
    if not path.exists():
        return {"skipped": True, "reason": "file not found"}

    stats: dict[str, Any] = {"total": 0, "kept": 0, "filtered": 0, "meta_hit": 0}
    out: list[str] = []

    with path.open(encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.rstrip("\n")
            if not line:
                continue
            stats["total"] += 1
            if limit and stats["total"] > limit:
                break
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            if not is_valid_sentence(rec.get("sentence", "")):
                stats["filtered"] += 1
                continue

            meta = get_meta(rec["doc_id"], lookup)
            if meta:
                stats["meta_hit"] += 1
                rec["label"] = improved_key_label(rec["sentence"], meta)
                rec["meta"] = {
                    "case_name":       meta.get("case_name", ""),
                    "disposal_nature": meta.get("disposal_nature", ""),
                    "decision_date":   meta.get("decision_date", ""),
                }
            else:
                rec["label"] = improved_key_label(rec["sentence"])

            stats["kept"] += 1
            out.append(json.dumps(rec, ensure_ascii=False))

    if not dry_run:
        _atomic_write(path, out)
    return stats


def process_summary(
    split: str,
    lookup: dict[str, dict],
    dry_run: bool,
    limit: int,
) -> dict[str, Any]:
    path = SPLITS_DIR / f"summary_{split}.jsonl"
    if not path.exists():
        return {"skipped": True, "reason": "file not found"}

    stats: dict[str, Any] = {"total": 0, "meta_hit": 0}
    out: list[str] = []

    with path.open(encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.rstrip("\n")
            if not line:
                continue
            stats["total"] += 1
            if limit and stats["total"] > limit:
                break
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            rec["source"] = clean_source_text(rec.get("source", ""))

            meta = get_meta(rec["doc_id"], lookup)
            if meta:
                stats["meta_hit"] += 1
                rec["target"] = build_summary_target(rec.get("target", ""), meta)
                rec["meta"] = _meta_sidecar(meta)

            out.append(json.dumps(rec, ensure_ascii=False))

    if not dry_run:
        _atomic_write(path, out)
    return stats


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Clean and enrich legal NLP dataset splits using structured metadata."
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="Process everything but do NOT write any files.",
    )
    ap.add_argument(
        "--limit", type=int, default=0,
        help="Stop after this many records per split file (0 = all).",
    )
    ap.add_argument(
        "--splits", nargs="+", default=["train", "val", "test"],
        choices=["train", "val", "test"],
        help="Which splits to process (default: all three).",
    )
    ap.add_argument(
        "--datasets", nargs="+", default=["ner", "keypoints", "summary"],
        choices=["ner", "keypoints", "summary"],
        help="Which dataset types to process (default: all three).",
    )
    args = ap.parse_args()

    if args.dry_run:
        print("── DRY-RUN mode – no files will be modified ──\n")

    print("Building metadata lookup …")
    lookup = build_metadata_lookup()
    print(f"  Total entries in lookup: {len(lookup)}\n")

    for split in args.splits:
        print(f"── Split: {split} {'─' * 40}")
        if "ner" in args.datasets:
            s = process_ner(split, lookup, args.dry_run, args.limit)
            print(f"  NER       : {s}")
        if "keypoints" in args.datasets:
            s = process_keypoints(split, lookup, args.dry_run, args.limit)
            print(f"  Keypoints : {s}")
        if "summary" in args.datasets:
            s = process_summary(split, lookup, args.dry_run, args.limit)
            print(f"  Summary   : {s}")

    print()
    if args.dry_run:
        print("Dry-run complete. No files were modified.")
    else:
        print("All files updated successfully.")


if __name__ == "__main__":
    main()
