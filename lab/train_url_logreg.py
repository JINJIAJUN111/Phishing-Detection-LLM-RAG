from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.pipeline import Pipeline


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "url" not in df.columns or "label" not in df.columns:
        raise ValueError(f"{path} must contain columns: url,label (got {list(df.columns)})")
    df = df.dropna(subset=["url", "label"]).copy()
    df["url"] = df["url"].astype(str)
    df["label"] = df["label"].astype(int)
    return df


def eval_split(pipe: Pipeline, df: pd.DataFrame, name: str) -> None:
    y = df["label"].to_numpy()
    x = df["url"].to_numpy()

    pred = pipe.predict(x)
    proba = pipe.predict_proba(x)[:, 1]

    auc = roc_auc_score(y, proba)
    print(f"\n=== {name} ===")
    print(f"AUC: {auc:.6f}")
    print(classification_report(y, pred, digits=4))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default="data/split/train.csv")
    ap.add_argument("--val", default="data/split/val.csv")
    ap.add_argument("--test", default="data/split/test.csv")
    ap.add_argument("--model-out", default="models/url_logreg.joblib")

    ap.add_argument("--ngram-min", type=int, default=3)
    ap.add_argument("--ngram-max", type=int, default=5)
    ap.add_argument("--min-df", type=int, default=2)
    ap.add_argument("--max-features", type=int, default=300_000)

    ap.add_argument("--C", type=float, default=2.0)
    ap.add_argument("--max-iter", type=int, default=2000)
    args = ap.parse_args()

    train = load_csv(args.train)
    val = load_csv(args.val)
    test = load_csv(args.test)

    print("Loaded:")
    print(f"  train: {len(train)}  label_rate={train['label'].mean():.6f}")
    print(f"  val:   {len(val)}  label_rate={val['label'].mean():.6f}")
    print(f"  test:  {len(test)}  label_rate={test['label'].mean():.6f}")

    pipe = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    analyzer="char",
                    ngram_range=(args.ngram_min, args.ngram_max),
                    min_df=args.min_df,
                    max_features=args.max_features,
                    lowercase=False,  # URL 大小写通常不重要，但保留最安全
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=args.max_iter,
                    n_jobs=-1,
                    class_weight="balanced",
                    C=args.C,
                    solver="lbfgs",
                ),
            ),
        ]
    )

    print("\nTraining URL-only LogisticRegression (char TF-IDF)...")
    pipe.fit(train["url"], train["label"])

    eval_split(pipe, val, "val")
    eval_split(pipe, test, "test")

    outp = Path(args.model_out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, outp)
    print(f"\nSaved model → {outp}")


if __name__ == "__main__":
    main()