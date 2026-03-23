#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.analysis_pipeline import analysis_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Step9: smoke test inference and safety checks")
    parser.add_argument("--sample-pdf", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("reports/smoke_result.json"))
    args = parser.parse_args()

    payload = args.sample_pdf.read_bytes()
    result = analysis_pipeline.run(payload)

    out = {
        "summary_extractive_preview": result.summary_extractive[:400],
        "summary_abstractive_preview": result.summary_abstractive[:400],
        "entities_found": {
            "parties": len(result.extraction.parties),
            "judges": len(result.extraction.judges),
            "sections": len(result.extraction.legal_sections_cited),
            "dates": len(result.extraction.important_dates),
            "punishment": len(result.extraction.punishment_sentence),
        },
        "key_points": len(result.key_points),
        "retrieval_hits": len(result.retrieval_context),
        "disclaimer": result.disclaimer,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
