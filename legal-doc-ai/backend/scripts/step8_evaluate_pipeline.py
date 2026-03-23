#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from rouge_score import rouge_scorer
from tqdm import tqdm

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.entity_extractor import EntityExtractionService
from app.services.keypoint_extractor import KeyPointExtractionService
from app.services.summarizer import SummarizationService
from app.utils.text import remove_boilerplate


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Step8: evaluate pipeline components")
    parser.add_argument("--split-dir", type=Path, default=Path("data/processed/splits"))
    parser.add_argument("--report-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    key_test = load_jsonl(args.split_dir / "keypoints_test.jsonl")
    sum_test = load_jsonl(args.split_dir / "summary_test.jsonl")

    ent = EntityExtractionService()
    key = KeyPointExtractionService()
    summ = SummarizationService()

    key_scores = []
    judge_detect_rate = []
    section_detect_rate = []
    decision_capture_rate = []
    grouped = {}
    for row in key_test:
        grouped.setdefault(row["doc_id"], []).append(row)

    for doc_id, rows in tqdm(list(grouped.items())[:400], desc="Keypoint eval", unit="doc"):
        text = " ".join(r["sentence"] for r in rows)
        pred = key.extract(text)
        pred_labels = {p.label for p in pred}
        gold_labels = {r["label"] for r in rows}
        inter = len(pred_labels & gold_labels)
        precision = inter / max(1, len(pred_labels))
        recall = inter / max(1, len(gold_labels))
        f1 = 2 * precision * recall / max(1e-8, precision + recall)
        key_scores.append(f1)

        ext = ent.extract(text)
        judge_detect_rate.append(float(len(ext.judges) > 0))
        section_detect_rate.append(float(len(ext.legal_sections_cited) > 0))
        decision_capture_rate.append(
            float(
                ext.final_order is not None
                and any(k in ext.final_order.value.lower() for k in ["allowed", "dismissed", "directed", "modified", "ordered", "released"])
            )
        )

    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    rouge_vals = []
    for row in tqdm(sum_test[:300], desc="Summary eval", unit="doc"):
        pred = summ.summarize_abstractive(remove_boilerplate(row["source"]))
        rouge_vals.append(scorer.score(row["target"], pred))

    rouge = {
        "rouge1": float(np.mean([s["rouge1"].fmeasure for s in rouge_vals])) if rouge_vals else 0.0,
        "rouge2": float(np.mean([s["rouge2"].fmeasure for s in rouge_vals])) if rouge_vals else 0.0,
        "rougeL": float(np.mean([s["rougeL"].fmeasure for s in rouge_vals])) if rouge_vals else 0.0,
    }

    result = {
        "keypoint_f1_mean": float(np.mean(key_scores)) if key_scores else 0.0,
        "judge_detect_rate": float(np.mean(judge_detect_rate)) if judge_detect_rate else 0.0,
        "section_detect_rate": float(np.mean(section_detect_rate)) if section_detect_rate else 0.0,
        "decision_capture_rate": float(np.mean(decision_capture_rate)) if decision_capture_rate else 0.0,
        **rouge,
    }

    args.report_dir.mkdir(parents=True, exist_ok=True)
    (args.report_dir / "evaluation_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    plt.figure(figsize=(6, 4))
    plt.bar(["ROUGE-1", "ROUGE-2", "ROUGE-L"], [rouge["rouge1"], rouge["rouge2"], rouge["rougeL"]], color="#4F772D")
    plt.title("Summarization Quality")
    plt.tight_layout()
    plt.savefig(args.report_dir / "rouge_scores.png", dpi=180)
    plt.close()

    plt.figure(figsize=(6, 4))
    plt.hist(key_scores, bins=20, color="#B98B73")
    plt.title("Keypoint F1 Distribution")
    plt.xlabel("F1")
    plt.ylabel("Doc count")
    plt.tight_layout()
    plt.savefig(args.report_dir / "keypoint_f1_hist.png", dpi=180)
    plt.close()

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
