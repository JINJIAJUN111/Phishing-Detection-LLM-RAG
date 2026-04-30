from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

from src.feature_pipeline import build_page_features
from src.schemas import DetectionResult, ModelName

from tqdm import tqdm

from src.schemas import DetectionResult, ModelName

def detect_placeholder(url: str) -> DetectionResult:
    pf = build_page_features(url)
    return DetectionResult(
        url=url,
        model_name=ModelName.PLACEHOLDER,
        is_phishing=False,
        confidence=0.01,
        suspected_brand="unknown",
        reasons=["features extracted (classification not implemented yet)"],
        evidence={"page_features": pf.model_dump()},
    )


def read_urls(input_path: str | None, url: str | None) -> list[str]:
    if url:
        return [url]

    if not input_path:
        raise SystemExit("Either --url or --input must be provided.")

    urls: list[str] = []
    with open(input_path, "r", encoding="utf-8") as f:
        # 允许两种格式：纯URL每行一个，或CSV带url列
        first = f.readline()
        f.seek(0)
        if "," in first and "url" in first.lower():
            reader = csv.DictReader(f)
            for row in reader:
                u = (row.get("url") or "").strip()
                if u:
                    urls.append(u)
        else:
            for line in f:
                u = line.strip()
                if u:
                    urls.append(u)
    return urls


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--url", type=str, default=None)
    parser.add_argument("--input", type=str, default=None, help="txt (one url per line) or csv(with url column)")
    parser.add_argument("--output", type=str, default="results/preds.csv")
    parser.add_argument("--log", type=str, default="logs/run.jsonl")
    args = parser.parse_args()

    urls = read_urls(args.input, args.url)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    results: list[DetectionResult] = []

    with open(log_path, "a", encoding="utf-8") as log_f:
        for u in tqdm(urls, desc="detect"):

            t0 = time.time()
            r = detect_placeholder(u)
            r.latency_ms = int((time.time() - t0) * 1000)

            log_f.write(json.dumps(r.model_dump(), ensure_ascii=False) + "\n")
            results.append(r)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["url", "model_name", "is_phishing", "confidence", "suspected_brand", "reasons", "latency_ms", "error"],
        )
        writer.writeheader()
        for r in results:
            writer.writerow(
                {
                    "url": r.url,
                    "model_name": r.model_name,
                    "is_phishing": r.is_phishing,
                    "confidence": r.confidence,
                    "suspected_brand": r.suspected_brand,
                    "reasons": " | ".join(r.reasons),
                    "latency_ms": r.latency_ms,
                    "error": r.error or "",
                }
            )

    print(f"Wrote {len(results)} results to: {out_path}")
    print(f"Appended logs to: {log_path}")


if __name__ == "__main__":
    main()