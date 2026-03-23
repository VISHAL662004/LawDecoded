from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.utils.device import get_torch_device
from app.utils.text import sentence_split


@dataclass
class Segment:
    label: str
    text: str


class RhetoricalSegmentationService:
    """
    Uses an optional BIO-tagging checkpoint when available, with heuristic fallback.
    """

    def __init__(self) -> None:
        self._pipe = None
        self._load_attempted = False

    def segment(self, text: str) -> list[Segment]:
        if not text:
            return []

        self._load_bio_pipeline()
        if self._pipe is not None:
            try:
                return self._segment_with_bio(text)
            except Exception:
                pass
        return self._segment_heuristic(text)

    def _load_bio_pipeline(self) -> None:
        if self._load_attempted:
            return
        self._load_attempted = True

        ckpt = settings.checkpoints_dir / "rhetorical-bio"
        if not ckpt.exists():
            return

        try:
            from transformers import pipeline

            device = get_torch_device()
            device_id = 0 if device == "cuda" else -1
            self._pipe = pipeline(
                "token-classification",
                model=str(ckpt),
                tokenizer=str(ckpt),
                aggregation_strategy="simple",
                device=device_id,
            )
        except Exception:
            self._pipe = None

    def _segment_with_bio(self, text: str) -> list[Segment]:
        preds = self._pipe(text[:12000])
        segments: list[Segment] = []
        for pred in preds:
            label = pred.get("entity_group", "FACT")
            token_text = pred.get("word", "").strip()
            if token_text:
                segments.append(Segment(label=label, text=token_text))
        return segments or self._segment_heuristic(text)

    def _segment_heuristic(self, text: str) -> list[Segment]:
        sentences = sentence_split(text)
        out: list[Segment] = []
        for sentence in sentences:
            label = "FACT"
            lower = sentence.lower()
            if "held" in lower or "ordered" in lower:
                label = "DECISION"
            elif "issue" in lower or "question" in lower:
                label = "ISSUE"
            elif "because" in lower or "therefore" in lower:
                label = "REASONING"
            out.append(Segment(label=label, text=sentence))
        return out
