#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess


STEPS = [
    ["python", "scripts/step1_define_outputs.py"],
    ["python", "scripts/step2_prepare_supervision.py"],
    ["python", "scripts/step3_train_tokenizer.py"],
    ["python", "scripts/step4_train_ner_from_scratch.py"],
    ["python", "scripts/step5_train_keypoints_from_scratch.py"],
    ["python", "scripts/step5b_train_decision_classifier.py"],
    ["python", "scripts/step6_train_summarizer_from_scratch.py"],
    ["python", "scripts/step7_build_retrieval_index.py"],
    ["python", "scripts/step8_evaluate_pipeline.py"],
    ["python", "scripts/step8_manual_review.py"],
]


def run(cmd: list[str]) -> None:
    print(f"\n>>> Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full from-scratch training pipeline")
    parser.add_argument("--skip-heavy", action="store_true", help="Skip summarizer training")
    args = parser.parse_args()

    for cmd in STEPS:
        if args.skip_heavy and "step6_train_summarizer_from_scratch.py" in cmd[-1]:
            continue
        run(cmd)

    print("\nPipeline complete. Run step9 and step10 manually after choosing a sample PDF.")


if __name__ == "__main__":
    main()
