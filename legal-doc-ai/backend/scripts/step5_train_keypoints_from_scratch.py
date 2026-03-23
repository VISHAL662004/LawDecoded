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
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import ConfusionMatrixDisplay, classification_report
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import LabelEncoder
from tqdm import tqdm


def load_jsonl(path: Path) -> list[dict]:
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            out.append(json.loads(line))
    return out


def batched(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def main() -> None:
    parser = argparse.ArgumentParser(description="Step5: train key-point classifier from scratch")
    parser.add_argument("--split-dir", type=Path, default=Path("data/processed/splits"))
    parser.add_argument("--out-dir", type=Path, default=Path("models/checkpoints/scratch/keypoint"))
    parser.add_argument("--report-dir", type=Path, default=Path("reports"))
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--epochs", type=int, default=7)
    args = parser.parse_args()

    train = load_jsonl(args.split_dir / "keypoints_train.jsonl")
    val = load_jsonl(args.split_dir / "keypoints_val.jsonl")

    x_train = [r["sentence"] for r in train]
    y_train = [r["label"] for r in train]
    x_val = [r["sentence"] for r in val]
    y_val = [r["label"] for r in val]

    le = LabelEncoder()
    y_train_ids = le.fit_transform(y_train)
    y_val_ids = le.transform(y_val)

    vectorizer = TfidfVectorizer(max_features=60000, ngram_range=(1, 2), min_df=2)
    x_train_vec = vectorizer.fit_transform(x_train)
    x_val_vec = vectorizer.transform(x_val)

    base = SGDClassifier(loss="log_loss", alpha=1e-5, random_state=42)
    model = OneVsRestClassifier(base)

    classes = list(range(len(le.classes_)))
    for epoch in range(1, args.epochs + 1):
        print(f"Epoch {epoch}/{args.epochs}")
        # OneVsRestClassifier does not expose partial_fit cleanly for each head,
        # so we refit every epoch for deterministic behavior.
        # tqdm shown for vector build + fit stage visibility.
        for _ in tqdm(range(1), desc="Fitting classifier", unit="stage"):
            model.fit(x_train_vec, y_train_ids)

    pred = model.predict(x_val_vec)
    report = classification_report(y_val_ids, pred, target_names=list(le.classes_), output_dict=True, zero_division=0)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    dump({"vectorizer": vectorizer, "classifier": model, "labels": list(le.classes_)}, args.out_dir / "classifier.joblib")
    (args.out_dir / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    args.report_dir.mkdir(parents=True, exist_ok=True)
    disp = ConfusionMatrixDisplay.from_predictions(y_val_ids, pred, display_labels=le.classes_, xticks_rotation=20)
    disp.figure_.set_size_inches(9, 7)
    plt.tight_layout()
    plt.savefig(args.report_dir / "keypoint_confusion_matrix.png", dpi=180)
    plt.close()

    print(json.dumps({"macro_f1": report["macro avg"]["f1-score"]}, indent=2))


if __name__ == "__main__":
    main()
