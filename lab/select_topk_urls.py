from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CSV with columns: url, phish_score (from predict_urls.py)")
    ap.add_argument("--k", type=int, default=2000, help="Top K urls to output")
    ap.add_argument("--min-score", type=float, default=None, help="Optional: only keep score >= this")
    ap.add_argument("--out", required=True, help="Output txt: one url per line")
    args = ap.parse_args()

    df = pd.read_csv(args.input)
    need_cols = {"url", "phish_score"}
    if not need_cols.issubset(df.columns):
        raise ValueError(f"{args.input} must contain columns {need_cols}, got {set(df.columns)}")

    df = df.dropna(subset=["url", "phish_score"]).copy()
    df["url"] = df["url"].astype(str)
    df["phish_score"] = df["phish_score"].astype(float)

    if args.min_score is not None:
        df = df[df["phish_score"] >= args.min_score]

    df = df.sort_values("phish_score", ascending=False)
    df = df.drop_duplicates(subset=["url"])

    top = df.head(args.k)

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with open(outp, "w", encoding="utf-8") as f:
        for u in top["url"].tolist():
            f.write(u + "\n")

    print(f"Saved → {outp}")
    print(f"selected: {len(top)} / available: {len(df)}")
    if len(top) > 0:
        print("score range:",
              float(top['phish_score'].min()),
              "to",
              float(top['phish_score'].max()))


if __name__ == "__main__":
    main()