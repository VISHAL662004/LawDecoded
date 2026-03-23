#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from joblib import dump
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import ConfusionMatrixDisplay, classification_report

DECISION_CUES = ["allowed", "dismissed", "directed", "modified", "released", "granted", "ordered"]


def load_jsonl(path: Path) -> list[dict]:
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            out.append(json.loads(line))
    return out


def weak_label(sentence: str) -> int:
    low = sentence.lower()
    return int(any(k in low for k in DECISION_CUES))


def main() -> None:
    parser = argparse.ArgumentParser(description="Step5b: train decision sentence classifier")
    parser.add_argument("--split-dir", type=Path, default=Path("data/processed/splits"))
    parser.add_argument("--out-dir", type=Path, default=Path("models/checkpoints/scratch/decision"))
    parser.add_argument("--report-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    train = load_jsonl(args.split_dir / "keypoints_train.jsonl")
    val = load_jsonl(args.split_dir / "keypoints_val.jsonl")

    x_train = [r["sentence"] for r in train]
    y_train = [weak_label(s) for s in x_train]
    x_val = [r["sentence"] for r in val]
    y_val = [weak_label(s) for s in x_val]

    vectorizer = TfidfVectorizer(max_features=60000, ngram_range=(1, 2), min_df=2)
    x_train_vec = vectorizer.fit_transform(x_train)
    x_val_vec = vectorizer.transform(x_val)

    clf = LogisticRegression(max_iter=400, class_weight="balanced", random_state=42)
    clf.fit(x_train_vec, y_train)

    pred = clf.predict(x_val_vec)
    report = classification_report(y_val, pred, output_dict=True, zero_division=0)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    dump({"vectorizer": vectorizer, "classifier": clf}, args.out_dir / "classifier.joblib")
    (args.out_dir / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    args.report_dir.mkdir(parents=True, exist_ok=True)
    disp = ConfusionMatrixDisplay.from_predictions(y_val, pred, display_labels=["NOT_DECISION", "DECISION"])
    disp.figure_.set_size_inches(6, 5)
    plt.tight_layout()
    plt.savefig(args.report_dir / "decision_confusion_matrix.png", dpi=180)
    plt.close()

    print(json.dumps({"decision_f1": report.get("1", {}).get("f1-score", 0.0)}, indent=2))


if __name__ == "__main__":
    main()
