#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    report_dir = Path("reports")
    out_file = report_dir / "pipeline_report.md"

    ner = read_json(Path("models/checkpoints/scratch/ner/metrics.json"))
    key = read_json(Path("models/checkpoints/scratch/keypoint/metrics.json"))
    decision = read_json(Path("models/checkpoints/scratch/decision/metrics.json"))
    summ = read_json(Path("models/checkpoints/scratch/summarizer/metrics.json"))
    eval_sum = read_json(report_dir / "evaluation_summary.json")

    md = f"""# Legal Document AI - Training Report

## Core Metrics
- NER Precision: {ner.get('precision', 'NA')}
- NER Recall: {ner.get('recall', 'NA')}
- NER F1: {ner.get('f1', 'NA')}
- Keypoint Macro F1: {key.get('macro avg', {}).get('f1-score', 'NA')}
- Decision Sentence F1: {decision.get('1', {}).get('f1-score', 'NA')}
- ROUGE-1: {summ.get('rouge1', 'NA')}
- ROUGE-2: {summ.get('rouge2', 'NA')}
- ROUGE-L: {summ.get('rougeL', 'NA')}

## End-to-End Evaluation
```json
{json.dumps(eval_sum, indent=2)}
```

## Manual Review Pack
- `reports/manual_review_20.json`

## Visualizations
- `reports/split_distribution.png`
- `reports/keypoint_distribution.png`
- `reports/ner_loss_curve.png`
- `reports/keypoint_confusion_matrix.png`
- `reports/decision_confusion_matrix.png`
- `reports/summarizer_loss_curve.png`
- `reports/rouge_scores.png`
- `reports/keypoint_f1_hist.png`
"""
    out_file.write_text(md, encoding="utf-8")
    print(f"Wrote {out_file}")


if __name__ == "__main__":
    main()
