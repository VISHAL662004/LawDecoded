# Legal Document AI - Training Report

## Core Metrics
- NER Precision: NA
- NER Recall: NA
- NER F1: NA
- Keypoint Macro F1: 0.8465471520769462
- Decision Sentence F1: 0.9813664596273292
- ROUGE-1: 0.32827085859276606
- ROUGE-2: 0.11169166537241491
- ROUGE-L: 0.24308286780240146

## End-to-End Evaluation
```json
{
  "keypoint_f1_mean": 0.8403571428571428,
  "judge_detect_rate": 0.3925,
  "section_detect_rate": 0.675,
  "decision_capture_rate": 0.6825,
  "rouge1": 0.4412314754703336,
  "rouge2": 0.3634409076662099,
  "rougeL": 0.37933873654115935
}
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
