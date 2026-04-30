from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd


def get_domain(url: str) -> str:
    try:
        host = urlsplit(url).netloc.lower()
        if ":" in host:
            host = host.split(":", 1)[0]
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CSV with columns url,phish_score (from predict_urls.py)")
    ap.add_argument("--k", type=int, default=2000, help="How many URLs to output")
    ap.add_argument("--per-domain", type=int, default=1, help="Max URLs per domain")
    ap.add_argument("--max-score", type=float, default=None, help="Optional: only keep score <= this")
    ap.add_argument("--out", required=True, help="Output txt, one url per line")
    args = ap.parse_args()

    df = pd.read_csv(args.input)
    if not {"url", "phish_score"}.issubset(df.columns):
        raise ValueError(f"Need columns url, phish_score. Got {list(df.columns)}")

    df = df.dropna(subset=["url", "phish_score"]).copy()
    df["url"] = df["url"].astype(str)
    df["phish_score"] = df["phish_score"].astype(float)
    df["domain"] = df["url"].map(get_domain)

    df = df[df["domain"] != ""]

    if args.max_score is not None:
        df = df[df["phish_score"] <= args.max_score]

    # benign: pick lowest-risk first
    df = df.sort_values("phish_score", ascending=True)

    df["rank_in_domain"] = df.groupby("domain").cumcount() + 1
    df = df[df["rank_in_domain"] <= args.per_domain]

    df = df.drop_duplicates(subset=["url"])
    top = df.head(args.k)

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with open(outp, "w", encoding="utf-8") as f:
        for u in top["url"].tolist():
            f.write(u + "\n")

    print(f"Saved → {outp}")
    print(f"selected: {len(top)}")
    print(f"unique domains in selected: {top['domain'].nunique()}")
    if len(top) > 0:
        print("score range:",
              float(top["phish_score"].min()),
              "to",
              float(top["phish_score"].max()))


if __name__ == "__main__":
    main()