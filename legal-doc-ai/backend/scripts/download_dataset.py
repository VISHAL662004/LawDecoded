#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

import requests
from tqdm import tqdm

BASE_URLS = [
    "https://indian-supreme-court-judgments.s3.amazonaws.com",
    "https://s3.amazonaws.com/indian-supreme-court-judgments",
]
REPO_URL = "https://github.com/vanga/indian-supreme-court-judgments.git"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, check=True, cwd=cwd)


def clone_repo(repo_dir: Path) -> None:
    if repo_dir.exists() and (repo_dir / ".git").exists():
        print(f"Repository already exists at {repo_dir}")
        return
    run(["git", "clone", REPO_URL, str(repo_dir)])


def download_file(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        print(f"Skipping existing file: {target}")
        return

    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        with target.open("wb") as f, tqdm(
            desc=target.name,
            total=total,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))


def download_with_fallback(paths: list[str], target: Path) -> str:
    last_error: Exception | None = None
    for base in BASE_URLS:
        for rel_path in paths:
            url = f"{base}/{rel_path.lstrip('/')}"
            print(f"Downloading {url}")
            try:
                download_file(url, target)
                return url
            except (requests.HTTPError, requests.ConnectionError) as exc:
                last_error = exc
                print(f"Failed {url}: {exc}")
    if last_error:
        raise last_error
    raise RuntimeError("No download candidates were generated")


def extract_tar(archive_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    run(["tar", "-xf", str(archive_path), "-C", str(out_dir)])


def build_entries(year: int, include_regional: bool) -> list[tuple[str, str, str]]:
    entries = [
        (
            "english",
            f"data/tar/year={year}/english/english.tar",
            "english.tar",
        ),
        (
            "metadata",
            f"metadata/tar/year={year}/metadata.tar",
            "metadata.tar",
        ),
    ]
    if include_regional:
        entries.append(
            (
                "regional",
                f"data/tar/year={year}/regional/regional.tar",
                "regional.tar",
            )
        )
    return entries


def sync_year(year: int, dst: Path, include_regional: bool) -> None:
    for group, rel_path, tar_name in build_entries(year, include_regional):
        archive = dst / "archives" / str(year) / tar_name
        try:
            download_with_fallback([rel_path], archive)
            extract_tar(archive, dst / str(year) / group)
        except requests.HTTPError as exc:
            print(f"Missing {group} for year {year}: {exc}")
        except requests.ConnectionError as exc:
            print(f"Network issue for {group} in year {year}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Indian Supreme Court judgments dataset")
    parser.add_argument("--start-year", type=int, default=1950)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--repo-dir", type=Path, default=Path("backend/data/indian-supreme-court-judgments"))
    parser.add_argument("--output-dir", type=Path, default=Path("backend/data/raw_judgments"))
    parser.add_argument("--include-regional", action="store_true")
    parser.add_argument("--clean-archives", action="store_true")
    args = parser.parse_args()

    clone_repo(args.repo_dir)

    for year in range(args.start_year, args.end_year + 1):
        sync_year(year, args.output_dir, args.include_regional)

    if args.clean_archives:
        shutil.rmtree(args.output_dir / "archives", ignore_errors=True)


if __name__ == "__main__":
    main()
