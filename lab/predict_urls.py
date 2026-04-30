from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd


def read_urls(path: str, col: str) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() in [".csv", ".tsv"]:
        sep = "\t" if p.suffix.lower() == ".tsv" else ","
        df = pd.read_csv(p, sep=sep)
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found in {path}. Columns={list(df.columns)}")
        out = pd.DataFrame({"url": df[col].astype(str)})
        return out
    else:
        # treat as txt: one url per line
        urls = []
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                u = line.strip()
                if u:
                    urls.append(u)
        return pd.DataFrame({"url": pd.Series(urls, dtype="string")})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input txt (one URL per line) or CSV/TSV")
    ap.add_argument("--url-col", default="url", help="URL column name when input is CSV/TSV")
    ap.add_argument("--model", default="models/url_logreg.joblib")
    ap.add_argument("--threshold", type=float, default=0.154)
    ap.add_argument("--out", default="data/out/url_scores.csv")
    args = ap.parse_args()

    model = joblib.load(args.model)
    df = read_urls(args.input, args.url_col)
    df["url"] = df["url"].astype(str)

    proba = model.predict_proba(df["url"].to_numpy())[:, 1]
    df["phish_score"] = proba
    df["pred_label"] = (df["phish_score"] >= args.threshold).astype(int)

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(outp, index=False, encoding="utf-8")

    print(f"Saved → {outp} (threshold={args.threshold})")
    print("pred_label counts:")
    print(df["pred_label"].value_counts(dropna=False))


if __name__ == "__main__":
    main()