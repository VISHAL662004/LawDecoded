from __future__ import annotations

import numpy as np

from app.config import settings
from app.schemas.analysis import KeyPoint, SourceSpan
from app.utils.text import remove_boilerplate, sentence_split

LABELS = ["FACT", "ISSUE", "ARGUMENT", "REASONING", "DECISION"]
SECTION_ANCHORS = ["order", "decision", "in view of the above", "accordingly"]


class KeyPointExtractionService:
    def __init__(self) -> None:
        self._bundle = None
        self._attempted = False

    def extract(self, text: str) -> list[KeyPoint]:
        cleaned = remove_boilerplate(text)
        sentences = sentence_split(cleaned)
        if not sentences:
            return []

        structural_boost = self._structural_boost(sentences)

        self._load_model()
        if not self._bundle:
            return self._heuristic(sentences, cleaned, structural_boost)

        vectorizer = self._bundle["vectorizer"]
        classifier = self._bundle["classifier"]

        x = vectorizer.transform(sentences)
        prob = classifier.predict_proba(x)
        if isinstance(prob, list):
            prob = np.stack([p[:, 1] for p in prob], axis=1)

        points: list[KeyPoint] = []
        for i, sent in enumerate(sentences):
            label_idx = int(np.argmax(prob[i]))
            conf = float(prob[i][label_idx]) + structural_boost[i]
            if conf < 0.42:
                continue
            label = LABELS[label_idx]
            points.append(self._build(label, sent, cleaned, min(conf, 0.99)))

        if not points:
            return self._heuristic(sentences, cleaned, structural_boost)

        points = sorted(points, key=lambda p: p.confidence, reverse=True)[:12]
        return points

    def _load_model(self) -> None:
        if self._attempted:
            return
        self._attempted = True
        model_path = settings.checkpoints_dir / "scratch" / "keypoint" / "classifier.joblib"
        if not model_path.exists():
            return
        try:
            from joblib import load

            self._bundle = load(model_path)
        except Exception:
            self._bundle = None

    def _structural_boost(self, sentences: list[str]) -> list[float]:
        boosts = [0.0] * len(sentences)
        active = False
        for i, sent in enumerate(sentences):
            low = sent.lower()
            if any(anchor in low for anchor in SECTION_ANCHORS):
                active = True
                boosts[i] += 0.18
            if active:
                boosts[i] += 0.08
            if i > 0 and boosts[i - 1] > 0:
                boosts[i] += 0.05
        return boosts

    def _heuristic(self, sentences: list[str], full_text: str, structural_boost: list[float]) -> list[KeyPoint]:
        out: list[KeyPoint] = []
        for i, sent in enumerate(sentences):
            low = sent.lower()
            label = None
            conf = 0.5 + structural_boost[i]
            if "facts" in low or "background" in low:
                label = "FACT"
            elif "issue" in low or "question" in low:
                label = "ISSUE"
            elif "submitted" in low or "contended" in low:
                label = "ARGUMENT"
            elif "because" in low or "therefore" in low or "held" in low or "in view of the above" in low:
                label = "REASONING"
            elif any(k in low for k in ["ordered", "appeal", "petition", "dismissed", "allowed", "accordingly"]):
                label = "DECISION"
            if label:
                out.append(self._build(label, sent, full_text, min(conf, 0.95)))
        return out[:10]

    def _build(self, label: str, sentence: str, text: str, conf: float) -> KeyPoint:
        start = text.lower().find(sentence.lower())
        end = start + len(sentence) if start >= 0 else 0
        return KeyPoint(
            label=label,
            sentence=sentence,
            confidence=conf,
            source=SourceSpan(text=sentence, start_char=max(0, start), end_char=end, page=None),
        )
