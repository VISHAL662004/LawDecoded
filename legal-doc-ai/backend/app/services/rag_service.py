from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np

from app.config import settings
from app.schemas.analysis import RetrievalHit


@dataclass
class CorpusDoc:
    doc_id: str
    text: str


class RAGService:
    def __init__(self) -> None:
        self.vectorizer = None
        self.matrix = None
        self.corpus: list[CorpusDoc] = []
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        self._loaded = True

        if not (
            settings.retrieval_vectorizer_path.exists()
            and settings.retrieval_matrix_path.exists()
            and settings.corpus_meta_path.exists()
        ):
            return

        try:
            from joblib import load
            from scipy import sparse

            self.vectorizer = load(settings.retrieval_vectorizer_path)
            self.matrix = sparse.load_npz(settings.retrieval_matrix_path)
            raw = json.loads(settings.corpus_meta_path.read_text(encoding="utf-8"))
            self.corpus = [CorpusDoc(**item) for item in raw]
        except Exception:
            self.vectorizer = None
            self.matrix = None
            self.corpus = []

    def search(self, query: str, top_k: int | None = None) -> list[RetrievalHit]:
        self.load()
        if self.vectorizer is None or self.matrix is None or not self.corpus:
            return []

        k = top_k or settings.retrieval_top_k
        q = self.vectorizer.transform([query])
        scores = (self.matrix @ q.T).toarray().ravel()
        if scores.size == 0:
            return []

        top_idx = np.argsort(scores)[::-1][:k]
        hits: list[RetrievalHit] = []
        for idx in top_idx:
            score = float(scores[idx])
            if score <= 0:
                continue
            doc = self.corpus[int(idx)]
            hits.append(
                RetrievalHit(
                    doc_id=doc.doc_id,
                    score=score,
                    snippet=doc.text[:600],
                )
            )
        return hits
