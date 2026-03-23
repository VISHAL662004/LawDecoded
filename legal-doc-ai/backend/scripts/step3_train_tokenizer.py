#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tqdm import tqdm


def main() -> None:
    parser = argparse.ArgumentParser(description="Step3: train SentencePiece tokenizer from scratch")
    parser.add_argument("--documents", type=Path, default=Path("data/processed/documents.json"))
    parser.add_argument("--out-dir", type=Path, default=Path("models/checkpoints/scratch/tokenizer"))
    parser.add_argument("--vocab-size", type=int, default=16000)
    parser.add_argument("--max-docs", type=int, default=30000)
    args = parser.parse_args()

    import sentencepiece as spm

    args.out_dir.mkdir(parents=True, exist_ok=True)

    docs = json.loads(args.documents.read_text(encoding="utf-8"))
    docs = [d for d in docs if d.get("text")][: args.max_docs]

    corpus_path = args.out_dir / "spm_corpus.txt"
    with corpus_path.open("w", encoding="utf-8") as f:
        for doc in tqdm(docs, desc="Writing tokenizer corpus", unit="doc"):
            f.write(" ".join(doc["text"].split()) + "\n")

    model_prefix = args.out_dir / "tokenizer"
    cmd = (
        f"--input={corpus_path} --model_prefix={model_prefix} --vocab_size={args.vocab_size} "
        "--model_type=bpe --character_coverage=0.9995 --pad_id=0 --unk_id=1 --bos_id=2 --eos_id=3"
    )
    spm.SentencePieceTrainer.Train(cmd)

    (args.out_dir / "tokenizer_meta.json").write_text(
        json.dumps({"vocab_size": args.vocab_size, "docs_used": len(docs)}, indent=2),
        encoding="utf-8",
    )
    print(f"Tokenizer artifacts saved in {args.out_dir}")


if __name__ == "__main__":
    main()
