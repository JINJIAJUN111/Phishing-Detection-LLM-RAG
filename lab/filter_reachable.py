from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from src.fetcher import fetch_url


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/raw/candidates_benign.txt")
    ap.add_argument("--out", default="data/split/benign_reachable.csv")
    ap.add_argument("--max", type=int, default=200)
    ap.add_argument("--timeout", type=float, default=10.0)

    # 新增：可指定输出标签（0=benign, 1=phish）
    ap.add_argument("--label", type=int, default=0)

    args = ap.parse_args()

    inp = Path(args.input)
    urls = [u.strip() for u in inp.read_text(encoding="utf-8").splitlines() if u.strip()]
    urls = urls[: args.max]

    ok = []
    fail_reasons = Counter()

    for url in tqdm(urls, desc="probe"):
        fr = fetch_url(url, timeout_s=args.timeout)
        if fr.html and fr.status_code and 200 <= fr.status_code < 400:
            ok.append({"url": url, "label": int(args.label)})
        else:
            fail_reasons[fr.error or f"status:{fr.status_code}"] += 1

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(ok).to_csv(outp, index=False, encoding="utf-8")

    print(f"Reachable label={args.label}:", len(ok), "/", len(urls))
    if fail_reasons:
        print("Top failure reasons:")
        for k, v in fail_reasons.most_common(20):
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()