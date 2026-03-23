#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from joblib import dump
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from tqdm import tqdm


def main() -> None:
    parser = argparse.ArgumentParser(description="Step7: build TF-IDF retrieval index")
    parser.add_argument("--documents", type=Path, default=Path("data/processed/documents.json"))
    parser.add_argument("--vectorizer-out", type=Path, default=Path("data/processed/tfidf_vectorizer.joblib"))
    parser.add_argument("--matrix-out", type=Path, default=Path("data/processed/tfidf_matrix.npz"))
    parser.add_argument("--meta-out", type=Path, default=Path("data/processed/tfidf_corpus.json"))
    parser.add_argument("--max-docs", type=int, default=40000)
    args = parser.parse_args()

    docs = json.loads(args.documents.read_text(encoding="utf-8"))
    docs = [d for d in docs if d.get("text")][: args.max_docs]

    corpus = []
    texts = []
    for doc in tqdm(docs, desc="Preparing retrieval corpus", unit="doc"):
        snippet = " ".join(doc["text"].split())[:4000]
        corpus.append({"doc_id": doc["doc_id"], "text": snippet})
        texts.append(snippet)

    vectorizer = TfidfVectorizer(max_features=120000, ngram_range=(1, 2), min_df=2)
    matrix = vectorizer.fit_transform(texts)

    args.vectorizer_out.parent.mkdir(parents=True, exist_ok=True)
    dump(vectorizer, args.vectorizer_out)
    sparse.save_npz(args.matrix_out, matrix)
    args.meta_out.write_text(json.dumps(corpus, ensure_ascii=False), encoding="utf-8")

    print(f"Indexed {len(corpus)} docs with shape={matrix.shape}")


if __name__ == "__main__":
    main()
