from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score


def load_df(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "url" not in df.columns or "label" not in df.columns:
        raise ValueError(f"{path} must contain columns: url,label (got {list(df.columns)})")
    df = df.dropna(subset=["url", "label"]).copy()
    df["url"] = df["url"].astype(str)
    df["label"] = df["label"].astype(int)
    return df


def metrics_at_threshold(y_true: np.ndarray, p1: np.ndarray, thr: float):
    y_pred = (p1 >= thr).astype(int)
    prec, rec, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0
    )
    acc = (y_pred == y_true).mean()
    return acc, prec, rec, f1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--val", default="data/split/val.csv", help="Validation CSV with url,label")
    ap.add_argument("--model", default="models/url_logreg.joblib", help="Saved sklearn Pipeline")
    ap.add_argument("--min-recall", type=float, default=0.995, help="Target recall for phish(1)")
    ap.add_argument("--out", default="", help="Optional: save full sweep CSV")
    args = ap.parse_args()

    df = load_df(args.val)
    model = joblib.load(args.model)

    y = df["label"].to_numpy()
    p1 = model.predict_proba(df["url"].to_numpy())[:, 1]

    auc = roc_auc_score(y, p1)
    print(f"val AUC: {auc:.6f}")
    print(f"samples: {len(df)}  label_rate={df['label'].mean():.6f}")

    # Sweep thresholds
    thresholds = np.unique(np.quantile(p1, np.linspace(0, 1, 2001)))
    rows = []
    best_f1 = (-1.0, None)
    best_min_recall = (-1.0, None)

    for thr in thresholds:
        acc, prec, rec, f1 = metrics_at_threshold(y, p1, float(thr))
        rows.append((float(thr), acc, prec, rec, f1))

        if f1 > best_f1[0]:
            best_f1 = (f1, float(thr))

        if rec >= args.min_recall:
            # among those meeting recall, pick highest precision (tie-breaker: higher f1)
            if best_min_recall[1] is None:
                best_min_recall = (prec, float(thr))
            else:
                cur_best_prec = best_min_recall[0]
                if prec > cur_best_prec:
                    best_min_recall = (prec, float(thr))

    sweep = pd.DataFrame(rows, columns=["threshold", "acc", "precision", "recall", "f1"])
    print("\nBest F1 threshold:")
    thr_f1 = best_f1[1]
    acc, prec, rec, f1 = metrics_at_threshold(y, p1, thr_f1)
    print(f"  thr={thr_f1:.6f}  acc={acc:.6f}  prec={prec:.6f}  rec={rec:.6f}  f1={f1:.6f}")

    print(f"\nBest threshold with recall >= {args.min_recall}:")
    if best_min_recall[1] is None:
        print("  (no threshold can meet the target recall; lower --min-recall)")
    else:
        thr_r = best_min_recall[1]
        acc, prec, rec, f1 = metrics_at_threshold(y, p1, thr_r)
        print(f"  thr={thr_r:.6f}  acc={acc:.6f}  prec={prec:.6f}  rec={rec:.6f}  f1={f1:.6f}")

    if args.out:
        outp = Path(args.out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        sweep.to_csv(outp, index=False, encoding="utf-8")
        print(f"\nSaved sweep → {outp}")


if __name__ == "__main__":
    main()