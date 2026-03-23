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
import sentencepiece as spm
import torch
from rouge_score import rouge_scorer
from torch import nn
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.models.scratch_models import Seq2SeqSummarizer
from app.utils.device import get_torch_device


class SummaryDataset(Dataset):
    def __init__(self, rows: list[dict], sp: spm.SentencePieceProcessor, src_max_len: int, tgt_max_len: int) -> None:
        self.rows = rows
        self.sp = sp
        self.src_max_len = src_max_len
        self.tgt_max_len = tgt_max_len

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        r = self.rows[idx]
        src = self.sp.encode(r["source"], out_type=int)[: self.src_max_len - 1]
        tgt = self.sp.encode(r["target"], out_type=int)[: self.tgt_max_len - 2]

        bos = self.sp.bos_id()
        eos = self.sp.eos_id()
        tgt_in = [bos] + tgt
        tgt_out = tgt + [eos]

        return {
            "src": torch.tensor(src, dtype=torch.long),
            "tgt_in": torch.tensor(tgt_in, dtype=torch.long),
            "tgt_out": torch.tensor(tgt_out, dtype=torch.long),
        }


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def collate(batch: list[dict[str, torch.Tensor]]) -> dict[str, torch.Tensor]:
    b = len(batch)
    src_len = max(x["src"].shape[0] for x in batch)
    tgt_len = max(x["tgt_in"].shape[0] for x in batch)

    src = torch.zeros((b, src_len), dtype=torch.long)
    tgt_in = torch.zeros((b, tgt_len), dtype=torch.long)
    tgt_out = torch.full((b, tgt_len), -100, dtype=torch.long)

    for i, x in enumerate(batch):
        ns = x["src"].shape[0]
        nt = x["tgt_in"].shape[0]
        src[i, :ns] = x["src"]
        tgt_in[i, :nt] = x["tgt_in"]
        tgt_out[i, :nt] = x["tgt_out"]

    return {"src": src, "tgt_in": tgt_in, "tgt_out": tgt_out}


def evaluate_rouge(model: Seq2SeqSummarizer, rows: list[dict], sp: spm.SentencePieceProcessor, device: str) -> dict[str, float]:
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    subset = rows[:200]
    scores = []
    model.eval()
    with torch.no_grad():
        for r in subset:
            src = sp.encode(r["source"], out_type=int)[:699]
            src_ids = torch.tensor([src], dtype=torch.long, device=device)
            out = model.generate(src_ids, bos_id=sp.bos_id(), eos_id=sp.eos_id(), max_len=120)
            ids = out[0].detach().cpu().tolist()
            if sp.eos_id() in ids:
                ids = ids[: ids.index(sp.eos_id())]
            pred = sp.decode(ids)
            scores.append(scorer.score(r["target"], pred))

    if not scores:
        return {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}

    return {
        "rouge1": float(np.mean([s["rouge1"].fmeasure for s in scores])),
        "rouge2": float(np.mean([s["rouge2"].fmeasure for s in scores])),
        "rougeL": float(np.mean([s["rougeL"].fmeasure for s in scores])),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Step6: train easy-language summarizer from scratch")
    parser.add_argument("--split-dir", type=Path, default=Path("data/processed/splits"))
    parser.add_argument("--tokenizer-dir", type=Path, default=Path("models/checkpoints/scratch/tokenizer"))
    parser.add_argument("--out-dir", type=Path, default=Path("models/checkpoints/scratch/summarizer"))
    parser.add_argument("--report-dir", type=Path, default=Path("reports"))
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=24)
    parser.add_argument("--src-max-len", type=int, default=700)
    parser.add_argument("--tgt-max-len", type=int, default=130)
    args = parser.parse_args()

    train_rows = load_jsonl(args.split_dir / "summary_train.jsonl")
    val_rows = load_jsonl(args.split_dir / "summary_val.jsonl")

    sp = spm.SentencePieceProcessor(model_file=str(args.tokenizer_dir / "tokenizer.model"))
    train_ds = SummaryDataset(train_rows, sp, args.src_max_len, args.tgt_max_len)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, collate_fn=collate)

    device = get_torch_device()
    model = Seq2SeqSummarizer(vocab_size=sp.vocab_size(), emb_dim=256, hidden_dim=384).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=5e-4)
    criterion = nn.CrossEntropyLoss(ignore_index=-100)

    losses = []
    for epoch in range(1, args.epochs + 1):
        model.train()
        running = 0.0
        for batch in tqdm(train_loader, desc=f"SUM Epoch {epoch}/{args.epochs}", unit="batch"):
            src = batch["src"].to(device)
            tgt_in = batch["tgt_in"].to(device)
            tgt_out = batch["tgt_out"].to(device)

            logits = model(src, tgt_in)
            loss = criterion(logits.view(-1, logits.size(-1)), tgt_out.view(-1))
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            running += float(loss.item())

        avg_loss = running / max(1, len(train_loader))
        losses.append(avg_loss)
        rouge = evaluate_rouge(model, val_rows, sp, device)
        print(f"Epoch {epoch}: loss={avg_loss:.4f} rougeL={rouge['rougeL']:.4f}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), args.out_dir / "model.pt")
    (args.out_dir / "meta.json").write_text(
        json.dumps(
            {
                "vocab_size": sp.vocab_size(),
                "emb_dim": 256,
                "hidden_dim": 384,
                "src_max_len": args.src_max_len,
                "tgt_max_len": args.tgt_max_len,
                "bos_id": sp.bos_id(),
                "eos_id": sp.eos_id(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (args.out_dir / "tokenizer.model").write_bytes((args.tokenizer_dir / "tokenizer.model").read_bytes())

    metrics = evaluate_rouge(model, val_rows, sp, device)
    (args.out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    args.report_dir.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(6, 4))
    plt.plot(range(1, len(losses) + 1), losses, marker="o", color="#B98B73")
    plt.title("Summarizer Training Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.tight_layout()
    plt.savefig(args.report_dir / "summarizer_loss_curve.png", dpi=180)
    plt.close()

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
