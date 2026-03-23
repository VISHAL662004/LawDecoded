#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


def main() -> None:
    parser = argparse.ArgumentParser(description="Create FAISS index for RAG")
    parser.add_argument("--input", type=Path, default=Path("backend/data/processed/documents.json"))
    parser.add_argument("--index-out", type=Path, default=Path("backend/data/processed/faiss.index"))
    parser.add_argument("--meta-out", type=Path, default=Path("backend/data/processed/faiss_corpus.json"))
    parser.add_argument("--model", type=str, default="sentence-transformers/all-MiniLM-L6-v2")
    args = parser.parse_args()

    docs = json.loads(args.input.read_text(encoding="utf-8"))
    corpus = [{"doc_id": d["doc_id"], "text": d["text"][:2000]} for d in docs if d.get("text")]
    texts = [d["text"] for d in corpus]

    model = SentenceTransformer(args.model)
    embeddings = model.encode(texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.asarray(embeddings, dtype="float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    args.index_out.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(args.index_out))
    args.meta_out.write_text(json.dumps(corpus, ensure_ascii=False), encoding="utf-8")

    print(f"Indexed {len(corpus)} documents")


if __name__ == "__main__":
    main()
