#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch
from sklearn.metrics import precision_recall_fscore_support
from torch import nn
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.models.scratch_models import BiLSTMTagger
from app.utils.device import get_torch_device

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


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def build_vocab(rows: list[dict], min_freq: int = 2) -> dict[str, int]:
    freq = Counter()
    for row in rows:
        freq.update(tok.lower() for tok in row["tokens"])
    vocab = {"<pad>": 0, "<unk>": 1}
    for tok, cnt in freq.items():
        if cnt >= min_freq:
            vocab[tok] = len(vocab)
    return vocab


class NERDataset(Dataset):
    def __init__(self, rows: list[dict], vocab: dict[str, int], max_len: int = 256) -> None:
        self.rows = rows
        self.vocab = vocab
        self.max_len = max_len

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        row = self.rows[idx]
        ids = [self.vocab.get(tok.lower(), 1) for tok in row["tokens"][: self.max_len]]
        tags = row["tags"][: self.max_len]
        return {
            "input_ids": torch.tensor(ids, dtype=torch.long),
            "labels": torch.tensor(tags, dtype=torch.long),
        }


def collate(batch: list[dict[str, torch.Tensor]]) -> dict[str, torch.Tensor]:
    max_len = max(x["input_ids"].shape[0] for x in batch)
    input_ids = torch.zeros((len(batch), max_len), dtype=torch.long)
    labels = torch.full((len(batch), max_len), -100, dtype=torch.long)
    for i, item in enumerate(batch):
        n = item["input_ids"].shape[0]
        input_ids[i, :n] = item["input_ids"]
        labels[i, :n] = item["labels"]
    return {"input_ids": input_ids, "labels": labels}


def evaluate(model: nn.Module, loader: DataLoader, device: str) -> dict[str, object]:
    model.eval()
    y_true, y_pred = [], []
    with torch.no_grad():
        for batch in loader:
            ids = batch["input_ids"].to(device)
            labels = batch["labels"].to(device)
            logits = model(ids)
            pred = logits.argmax(dim=-1)
            mask = labels != -100
            y_true.extend(labels[mask].detach().cpu().tolist())
            y_pred.extend(pred[mask].detach().cpu().tolist())

    precision_micro, recall_micro, f1_micro, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(1, len(LABELS))),
        average="micro",
        zero_division=0,
    )

    precision_macro, recall_macro, f1_macro, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(1, len(LABELS))),
        average="macro",
        zero_division=0,
    )
    per_p, per_r, per_f1, per_s = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(1, len(LABELS))),
        average=None,
        zero_division=0,
    )
    per_class = {
        LABELS[i + 1]: {
            "precision": float(per_p[i]),
            "recall": float(per_r[i]),
            "f1": float(per_f1[i]),
            "support": int(per_s[i]),
        }
        for i in range(len(per_p))
    }
    return {
        "precision_micro": float(precision_micro),
        "recall_micro": float(recall_micro),
        "f1_micro": float(f1_micro),
        "precision_macro": float(precision_macro),
        "recall_macro": float(recall_macro),
        "f1_macro": float(f1_macro),
        "per_class": per_class,
    }


def compute_class_weights(rows: list[dict]) -> torch.Tensor:
    counts = Counter()
    for row in rows:
        counts.update(int(t) for t in row["tags"])
    weights = []
    for cls in range(len(LABELS)):
        c = counts.get(cls, 1)
        if cls == 0:
            weights.append(0.35)
        else:
            weights.append(1.0 / (c ** 0.5))
    tensor = torch.tensor(weights, dtype=torch.float32)
    tensor = tensor / tensor.mean()
    return tensor


def main() -> None:
    parser = argparse.ArgumentParser(description="Step4: train NER from scratch")
    parser.add_argument("--split-dir", type=Path, default=Path("data/processed/splits"))
    parser.add_argument("--out-dir", type=Path, default=Path("models/checkpoints/scratch/ner"))
    parser.add_argument("--report-dir", type=Path, default=Path("reports"))
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    train_rows = load_jsonl(args.split_dir / "ner_train.jsonl")
    val_rows = load_jsonl(args.split_dir / "ner_val.jsonl")

    vocab = build_vocab(train_rows)
    train_ds = NERDataset(train_rows, vocab)
    val_ds = NERDataset(val_rows, vocab)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, collate_fn=collate)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, collate_fn=collate)

    device = get_torch_device()
    model = BiLSTMTagger(vocab_size=len(vocab), emb_dim=128, hidden_dim=128, num_labels=len(LABELS)).to(device)
    class_weights = compute_class_weights(train_rows).to(device)
    criterion = nn.CrossEntropyLoss(ignore_index=-100, weight=class_weights)
    optim = torch.optim.Adam(model.parameters(), lr=1e-3)

    loss_curve = []
    best_f1 = -1.0
    args.out_dir.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, args.epochs + 1):
        model.train()
        running = 0.0
        for batch in tqdm(train_loader, desc=f"NER Epoch {epoch}/{args.epochs}", unit="batch"):
            ids = batch["input_ids"].to(device)
            labels = batch["labels"].to(device)
            logits = model(ids)
            loss = criterion(logits.view(-1, logits.size(-1)), labels.view(-1))
            optim.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optim.step()
            running += float(loss.item())

        avg_loss = running / max(1, len(train_loader))
        metrics = evaluate(model, val_loader, device)
        print(f"Epoch {epoch}: loss={avg_loss:.4f} val_f1_macro={metrics['f1_macro']:.4f}")
        loss_curve.append(avg_loss)

        if float(metrics["f1_macro"]) > best_f1:
            best_f1 = float(metrics["f1_macro"])
            torch.save(model.state_dict(), args.out_dir / "model.pt")

    (args.out_dir / "vocab.json").write_text(json.dumps(vocab, indent=2), encoding="utf-8")
    (args.out_dir / "labels.json").write_text(json.dumps(LABELS, indent=2), encoding="utf-8")

    final_metrics = evaluate(model, val_loader, device)
    (args.out_dir / "metrics.json").write_text(json.dumps(final_metrics, indent=2), encoding="utf-8")

    args.report_dir.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(6, 4))
    plt.plot(range(1, len(loss_curve) + 1), loss_curve, marker="o", color="#31572C")
    plt.title("NER Training Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.tight_layout()
    plt.savefig(args.report_dir / "ner_loss_curve.png", dpi=180)
    plt.close()

    print(json.dumps(final_metrics, indent=2))


if __name__ == "__main__":
    main()
