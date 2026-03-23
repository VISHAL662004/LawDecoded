from __future__ import annotations

import json
from typing import Any

import torch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import settings
from app.models.scratch_models import Seq2SeqSummarizer
from app.utils.device import get_torch_device
from app.utils.text import remove_boilerplate, sentence_split

DECISION_KEYWORDS = ["allowed", "dismissed", "directed", "modified", "released", "granted", "ordered"]


class SummarizationService:
    def __init__(self) -> None:
        self._model: Seq2SeqSummarizer | None = None
        self._tokenizer = None
        self._meta: dict[str, int] | None = None
        self._decision_bundle: dict[str, Any] | None = None
        self._attempted = False

    def summarize_extractive(self, text: str, max_sentences: int = 6) -> str:
        cleaned = remove_boilerplate(text)
        sentences = sentence_split(cleaned)
        if not sentences:
            return ""

        ranked = self._rank_sentences(sentences)
        selected: list[str] = []
        for sent, _ in ranked:
            if self._is_redundant(sent, selected, threshold=0.82):
                continue
            selected.append(sent)
            if len(selected) >= max_sentences:
                break

        ordered = [self._simplify_sentence(s) for s in sentences if s in set(selected)]
        return " ".join(ordered)

    def summarize_abstractive(self, text: str) -> str:
        self._load_model()
        cleaned = remove_boilerplate(text)
        if self._model is None or self._tokenizer is None or self._meta is None:
            return self.summarize_extractive(cleaned, max_sentences=4)

        try:
            src = self._tokenizer.encode(cleaned[:3500], out_type=int)
            src = src[: self._meta["src_max_len"] - 1]
            src_ids = torch.tensor([src], dtype=torch.long, device=get_torch_device())
            out = self._model.generate(
                src_ids,
                bos_id=self._meta["bos_id"],
                eos_id=self._meta["eos_id"],
                max_len=self._meta["tgt_max_len"],
            )
            ids = out[0].detach().cpu().tolist()
            if self._meta["eos_id"] in ids:
                ids = ids[: ids.index(self._meta["eos_id"])]
            text_out = self._tokenizer.decode(ids)
            text_out = " ".join(text_out.split())
            return text_out or self.summarize_extractive(cleaned, max_sentences=4)
        except Exception:
            return self.summarize_extractive(cleaned, max_sentences=4)

    def _rank_sentences(self, sentences: list[str]) -> list[tuple[str, float]]:
        vectorizer = TfidfVectorizer(max_features=15000, ngram_range=(1, 2))
        mat = vectorizer.fit_transform(sentences)
        doc_vec = mat.mean(axis=0)
        doc_vec = getattr(doc_vec, "A", doc_vec)
        sim = cosine_similarity(mat, doc_vec).reshape(-1)

        self._load_decision_classifier()
        decision_probs = self._decision_probabilities(sentences)

        ranked: list[tuple[str, float]] = []
        n = len(sentences)
        for i, sent in enumerate(sentences):
            low = sent.lower()
            similarity_score = float(sim[i])
            decision_keyword_score = 1.0 if any(k in low for k in DECISION_KEYWORDS) else 0.0
            if decision_probs is not None:
                decision_keyword_score = max(decision_keyword_score, float(decision_probs[i]))
            position_score = 0.5 if i >= int(0.75 * n) else 0.0

            final_score = (
                0.5 * similarity_score
                + 0.3 * decision_keyword_score
                + 0.2 * position_score
            )
            ranked.append((sent, final_score))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    def _is_redundant(self, sentence: str, selected: list[str], threshold: float = 0.82) -> bool:
        if not selected:
            return False
        vec = TfidfVectorizer(max_features=8000).fit_transform(selected + [sentence])
        sims = cosine_similarity(vec[-1], vec[:-1]).ravel()
        return bool((sims >= threshold).any())

    def _decision_probabilities(self, sentences: list[str]) -> list[float] | None:
        if not self._decision_bundle:
            return None
        vectorizer = self._decision_bundle["vectorizer"]
        classifier = self._decision_bundle["classifier"]
        x = vectorizer.transform(sentences)
        proba = classifier.predict_proba(x)
        if proba.ndim == 2 and proba.shape[1] >= 2:
            return [float(v) for v in proba[:, 1]]
        return None

    def _load_decision_classifier(self) -> None:
        if self._decision_bundle is not None:
            return
        model_path = settings.checkpoints_dir / "scratch" / "decision" / "classifier.joblib"
        if not model_path.exists():
            return
        try:
            from joblib import load

            self._decision_bundle = load(model_path)
        except Exception:
            self._decision_bundle = None

    def _load_model(self) -> None:
        if self._attempted:
            return
        self._attempted = True

        base = settings.checkpoints_dir / "scratch" / "summarizer"
        model_path = base / "model.pt"
        meta_path = base / "meta.json"
        spm_path = base / "tokenizer.model"
        if not model_path.exists() or not meta_path.exists() or not spm_path.exists():
            return

        try:
            import sentencepiece as spm

            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            model = Seq2SeqSummarizer(vocab_size=meta["vocab_size"], emb_dim=meta["emb_dim"], hidden_dim=meta["hidden_dim"])
            state = torch.load(model_path, map_location=get_torch_device())
            model.load_state_dict(state)
            model.to(get_torch_device())
            model.eval()

            sp = spm.SentencePieceProcessor(model_file=str(spm_path))
            self._model = model
            self._tokenizer = sp
            self._meta = meta
        except Exception:
            self._model = None
            self._tokenizer = None
            self._meta = None

    def _simplify_sentence(self, sentence: str) -> str:
        replacements = {
            "hereinafter": "from now on",
            "therefore": "so",
            "aforesaid": "above",
            "petitioner": "person filing the case",
            "respondent": "person answering the case",
            "appellant": "person making the appeal",
        }
        out = sentence
        for src, tgt in replacements.items():
            out = out.replace(src, tgt).replace(src.title(), tgt)
        return out
