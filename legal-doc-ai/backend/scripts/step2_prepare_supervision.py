#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from tqdm import tqdm

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
KEYPOINTS = ["FACT", "ISSUE", "ARGUMENT", "REASONING", "DECISION"]

DATE_PATTERN = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
SECTION_PATTERN = re.compile(r"\b(?:section|sec\.|article)\s+([0-9a-z()/-]+)", re.IGNORECASE)


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def pseudo_ner(tokens: list[str]) -> list[int]:
    tags = [0] * len(tokens)
    for i, tok in enumerate(tokens):
        low = tok.lower().strip(".,;:()[]{}")
        if low in {"petitioner", "appellant"}:
            tags[i] = 1
        elif low in {"respondent"}:
            tags[i] = 2
        elif low in {"justice", "judge"}:
            tags[i] = 3
        elif low in {"section", "sec", "article"}:
            tags[i] = 4
        elif DATE_PATTERN.fullmatch(low):
            tags[i] = 5
        elif low in {"imprisonment", "sentence", "fine"}:
            tags[i] = 6
        elif low in {"supreme", "high", "court"}:
            tags[i] = 7
    return tags


def pseudo_key_label(sentence: str) -> str:
    low = sentence.lower()
    if "issue" in low or "question" in low:
        return "ISSUE"
    if "submitted" in low or "contended" in low or "argued" in low:
        return "ARGUMENT"
    if "because" in low or "therefore" in low or "held" in low:
        return "REASONING"
    if "ordered" in low or "dismissed" in low or "allowed" in low or "appeal" in low:
        return "DECISION"
    return "FACT"


def easy_sentence(sentence: str) -> str:
    pairs = {
        "petitioner": "person who filed the case",
        "respondent": "person answering the case",
        "appellant": "person making the appeal",
        "hereinafter": "from now on",
        "therefore": "so",
    }
    out = sentence
    for a, b in pairs.items():
        out = re.sub(rf"\b{re.escape(a)}\b", b, out, flags=re.IGNORECASE)
    return out


def year_from_doc_id(doc_id: str) -> int:
    try:
        return int(doc_id.split("_")[0])
    except Exception:
        return 0


def choose_split(year: int) -> str:
    if year >= 2020:
        return "test"
    if year >= 2016:
        return "val"
    return "train"


def save_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Step2: build supervision datasets and splits")
    parser.add_argument("--documents", type=Path, default=Path("data/processed/documents.json"))
    parser.add_argument("--out-dir", type=Path, default=Path("data/processed/splits"))
    parser.add_argument("--report-dir", type=Path, default=Path("reports"))
    parser.add_argument("--max-docs", type=int, default=42294)
    args = parser.parse_args()

    docs = json.loads(args.documents.read_text(encoding="utf-8"))
    docs = [d for d in docs if d.get("text")][: args.max_docs]

    ner_rows: dict[str, list[dict]] = defaultdict(list)
    key_rows: dict[str, list[dict]] = defaultdict(list)
    sum_rows: dict[str, list[dict]] = defaultdict(list)
    split_counts = Counter()
    key_counts = Counter()

    random.seed(42)
    for doc in tqdm(docs, desc="Preparing supervision", unit="doc"):
        doc_id = doc["doc_id"]
        year = year_from_doc_id(doc_id)
        split = choose_split(year)
        split_counts[split] += 1

        text = " ".join(doc.get("text", "").split())
        if len(text) < 200:
            continue

        tokens = text[:5000].split()
        tags = pseudo_ner(tokens)
        ner_rows[split].append({"doc_id": doc_id, "tokens": tokens, "tags": tags})

        sents = split_sentences(text[:7000])
        for sent in sents[:80]:
            label = pseudo_key_label(sent)
            key_counts[label] += 1
            key_rows[split].append({"doc_id": doc_id, "sentence": sent, "label": label})

        chosen = [s for s in sents if pseudo_key_label(s) in {"ISSUE", "REASONING", "DECISION"}][:8]
        if len(chosen) < 3:
            chosen = sents[:5]
        source = " ".join(sents[:20])
        target = " ".join(easy_sentence(s) for s in chosen)
        sum_rows[split].append({"doc_id": doc_id, "source": source[:3500], "target": target[:700]})

    for split in ["train", "val", "test"]:
        save_jsonl(args.out_dir / f"ner_{split}.jsonl", ner_rows[split])
        save_jsonl(args.out_dir / f"keypoints_{split}.jsonl", key_rows[split])
        save_jsonl(args.out_dir / f"summary_{split}.jsonl", sum_rows[split])

    args.report_dir.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(6, 4))
    plt.bar(list(split_counts.keys()), list(split_counts.values()), color=["#31572C", "#4F772D", "#B98B73"])
    plt.title("Document Split by Year Rules")
    plt.ylabel("Document Count")
    plt.tight_layout()
    plt.savefig(args.report_dir / "split_distribution.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 4))
    plt.bar(KEYPOINTS, [key_counts[k] for k in KEYPOINTS], color="#31572C")
    plt.title("Pseudo Key-Point Label Distribution")
    plt.ylabel("Sentence Count")
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.savefig(args.report_dir / "keypoint_distribution.png", dpi=180)
    plt.close()

    summary = {
        "docs_used": len(docs),
        "split_counts": dict(split_counts),
        "keypoint_counts": dict(key_counts),
    }
    (args.report_dir / "step2_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
