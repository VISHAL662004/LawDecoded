#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    out_dir = Path("data/annotations")
    out_dir.mkdir(parents=True, exist_ok=True)

    schema = {
        "entities": [
            "CASE_NAME",
            "PETITIONER",
            "RESPONDENT",
            "JUDGE",
            "SECTION_OF_LAW",
            "DATE",
            "PUNISHMENT",
            "COURT_NAME",
            "FINAL_ORDER",
        ],
        "key_point_labels": ["FACT", "ISSUE", "ARGUMENT", "REASONING", "DECISION"],
        "summary_output": {
            "easy_bullets": 8,
            "easy_paragraph": 1,
            "max_words": 220,
        },
    }

    guide = """# Annotation Guidelines

## Entity Span Rules
- Mark shortest exact span for each entity.
- Preserve legal abbreviations exactly as written.
- For `SECTION_OF_LAW`, include section identifier (example: `Section 302 IPC`).
- For `FINAL_ORDER`, capture final operative direction sentence.

## Key Point Rules
- `FACT`: background and chronology.
- `ISSUE`: legal questions framed by court.
- `ARGUMENT`: submissions by parties/counsel.
- `REASONING`: why court reached its conclusion.
- `DECISION`: operative result and relief.

## Easy Summary Rules
- Use plain words, short sentences.
- Explain legal terms in simple words.
- Mention who won, what order was passed, and what happens next.
"""

    template = {
        "doc_id": "",
        "entities": [],
        "key_points": [],
        "summary_easy": "",
        "reviewer": "",
    }

    (out_dir / "task_schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
    (out_dir / "annotation_guidelines.md").write_text(guide, encoding="utf-8")
    (out_dir / "annotation_template.json").write_text(json.dumps(template, indent=2), encoding="utf-8")

    print(f"Wrote schema/guidelines/templates to {out_dir}")


if __name__ == "__main__":
    main()
