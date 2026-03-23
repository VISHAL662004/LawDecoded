#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.entity_extractor import EntityExtractionService
from app.services.summarizer import SummarizationService
from app.utils.text import remove_boilerplate


def main() -> None:
    parser = argparse.ArgumentParser(description="Step8-manual: create 20-doc manual review pack")
    parser.add_argument("--documents", type=Path, default=Path("data/processed/documents.json"))
    parser.add_argument("--out", type=Path, default=Path("reports/manual_review_20.json"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    docs = json.loads(args.documents.read_text(encoding="utf-8"))
    docs = [d for d in docs if d.get("text")]

    random.seed(args.seed)
    sample = random.sample(docs, min(20, len(docs)))

    extractor = EntityExtractionService()
    summarizer = SummarizationService()

    items = []
    for d in sample:
        text = remove_boilerplate(d["text"])
        ext = extractor.extract(text)
        summ = summarizer.summarize_extractive(text, max_sentences=5)

        items.append(
            {
                "doc_id": d["doc_id"],
                "checks": {
                    "judge_extraction_correct": None,
                    "final_decision_captured": None,
                    "section_extraction_correct": None,
                    "summary_faithful": None,
                },
                "predictions": {
                    "judges": [j.value for j in ext.judges],
                    "final_order": ext.final_order.value if ext.final_order else "",
                    "sections": [s.value for s in ext.legal_sections_cited],
                    "summary": summ,
                },
                "evidence_preview": text[:1200],
                "reviewer_notes": "",
            }
        )

    report = {
        "review_set_size": len(items),
        "instructions": "Mark each check as true/false and add notes. Compute manual accuracy after review.",
        "items": items,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote manual review pack: {args.out}")


if __name__ == "__main__":
    main()
