#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import signal
from pathlib import Path

import pandas as pd
import pdfplumber
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from tqdm import tqdm


def parse_metadata(raw_dir: Path) -> pd.DataFrame:
    rows = []
    for meta_path in raw_dir.rglob("metadata/*"):
        if meta_path.suffix.lower() == ".csv":
            try:
                df = pd.read_csv(meta_path)
            except Exception:
                continue
            df["source_file"] = str(meta_path)
            rows.append(df)
        elif meta_path.suffix.lower() == ".json":
            try:
                payload = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(payload, dict):
                payload["source_file"] = str(meta_path)
                rows.append(pd.DataFrame([payload]))

    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def text_to_pdf(text_path: Path, pdf_path: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4
    y = height - 50

    for raw in text_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw[:150]
        c.drawString(40, y, line)
        y -= 14
        if y < 50:
            c.showPage()
            y = height - 50
    c.save()


class PDFTimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):  # type: ignore[no-untyped-def]
    raise PDFTimeoutError("PDF extraction timed out")


def extract_pdf_text(pdf_path: Path, timeout_sec: int = 45) -> str:
    old_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(timeout_sec)
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            pages = [(p.extract_text() or "") for p in pdf.pages]
        signal.alarm(0)
    except Exception:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        return ""
    signal.signal(signal.SIGALRM, old_handler)
    return " ".join(" ".join(pages).split())


def collect_documents(raw_dir: Path, out_dir: Path, timeout_sec: int, progress_step: int) -> None:
    corpus = []
    txt_count = 0
    pdf_count = 0

    for txt_path in raw_dir.rglob("*.txt"):
        txt_count += 1
        doc_id = txt_path.stem
        text = txt_path.read_text(encoding="utf-8", errors="ignore")
        text = " ".join(text.split())
        if not text:
            continue

        pdf_target = out_dir / "pdf_from_txt" / f"{doc_id}.pdf"
        if not pdf_target.exists():
            text_to_pdf(txt_path, pdf_target)

        corpus.append(
            {
                "doc_id": doc_id,
                "source_path": str(txt_path),
                "pdf_path": str(pdf_target),
                "text": text,
            }
        )

    pdf_files = [p for p in raw_dir.rglob("*.pdf") if p.parent.name == "english"]
    skipped_pdf = 0
    print(f"Found {len(pdf_files)} English PDFs. Starting extraction...")
    for idx, pdf_path in enumerate(tqdm(pdf_files, desc="PDF extraction", unit="pdf"), start=1):
        pdf_count += 1
        doc_id = pdf_path.stem
        text = extract_pdf_text(pdf_path, timeout_sec=timeout_sec)
        if not text:
            skipped_pdf += 1
            continue
        corpus.append(
            {
                "doc_id": doc_id,
                "source_path": str(pdf_path),
                "pdf_path": str(pdf_path),
                "text": text,
            }
        )
        if idx % progress_step == 0:
            print(
                f"Progress: {idx}/{len(pdf_files)} PDFs processed | "
                f"documents kept: {len(corpus)} | skipped PDFs: {skipped_pdf}"
            )

    (out_dir / "documents.json").write_text(json.dumps(corpus, ensure_ascii=False), encoding="utf-8")
    print(
        f"Collected {len(corpus)} documents "
        f"(from {txt_count} txt files, {pdf_count} pdf files, skipped PDFs: {skipped_pdf})."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocess judgments dataset")
    parser.add_argument("--raw-dir", type=Path, default=Path("backend/data/raw_judgments"))
    parser.add_argument("--processed-dir", type=Path, default=Path("backend/data/processed"))
    parser.add_argument("--pdf-timeout-sec", type=int, default=45)
    parser.add_argument("--progress-step", type=int, default=200)
    args = parser.parse_args()

    args.processed_dir.mkdir(parents=True, exist_ok=True)

    metadata = parse_metadata(args.raw_dir)
    metadata_out = args.processed_dir / "metadata.parquet"
    if not metadata.empty:
        metadata.to_parquet(metadata_out, index=False)
        metadata.head(1000).to_json(
            args.processed_dir / "metadata_preview.json",
            orient="records",
            force_ascii=False,
            indent=2,
        )

    collect_documents(
        args.raw_dir,
        args.processed_dir,
        timeout_sec=max(5, args.pdf_timeout_sec),
        progress_step=max(1, args.progress_step),
    )


if __name__ == "__main__":
    main()
