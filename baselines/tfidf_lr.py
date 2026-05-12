import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold


def safe_str(x) -> str:
    if x is None:
        return ""
    return str(x)


def jsonl_safe_dumps(obj) -> str:
    s = json.dumps(obj, ensure_ascii=False)
    return (
        s.replace("\r", "\\r")
         .replace("\n", "\\n")
         .replace("\u2028", "\\u2028")
         .replace("\u2029", "\\u2029")
    )


def build_text(row) -> str:
    url = safe_str(row.get("final_url") or row.get("url")).strip()
    title = safe_str(row.get("title")).strip()
    snip = safe_str(row.get("text_snippet")).strip()
    return f"URL: {url}\nTITLE: {title}\nSNIPPET: {snip}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phish", required=True)
    ap.add_argument("--benign", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-features", type=int, default=50000)
    ap.add_argument("--C", type=float, default=2.0)
    args = ap.parse_args()

    df_p = pd.read_csv(args.phish)
    df_b = pd.read_csv(args.benign)
    df = pd.concat([df_b, df_p], ignore_index=True)

    y = df["label"].astype(int).to_numpy()
    texts = [build_text(r) for r in df.to_dict(orient="records")]

    # Build numerical feature matrix (keep dense for CV indexing)
    def as_num(col, default=0.0):
        s = df.get(col)
        if s is None:
            return np.full(len(df), default, dtype=np.float32)
        return pd.to_numeric(s, errors="coerce").fillna(default).astype(np.float32).to_numpy()

    X_num = np.column_stack([
        as_num("form_count", 0.0),
        as_num("has_password_input", 0.0),
        as_num("has_email_input", 0.0),
        as_num("external_form_action", 0.0),
        as_num("status_code", 0.0),
        as_num("elapsed_ms", 0.0),
    ])

    # Stratified 5-fold cross-validation (out-of-fold predictions)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    all_prob = np.zeros(len(df), dtype=np.float64)

    for train_idx, test_idx in skf.split(texts, y):
        texts_train = [texts[i] for i in train_idx]
        texts_test  = [texts[i] for i in test_idx]

        vec = TfidfVectorizer(
            max_features=args.max_features,
            ngram_range=(1, 2),
            min_df=2,
            lowercase=True,
        )
        X_text_train = vec.fit_transform(texts_train)
        X_text_test  = vec.transform(texts_test)

        X_num_train = X_num[train_idx]
        X_num_test  = X_num[test_idx]

        X_train = hstack([X_text_train, csr_matrix(X_num_train)], format="csr")
        X_test  = hstack([X_text_test,  csr_matrix(X_num_test)],  format="csr")

        clf = LogisticRegression(C=args.C, max_iter=2000, solver="liblinear", random_state=42)
        clf.fit(X_train, y[train_idx])

        prob = clf.predict_proba(X_test)[:, 1]
        all_prob[test_idx] = prob

    pred = (all_prob >= 0.5).astype(int)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        for i, row in enumerate(df.to_dict(orient="records")):
            url = safe_str(row.get("final_url") or row.get("url")).strip()
            rec = {
                "url": url,
                "label": int(row["label"]),
                "llm_out": {
                    "is_phish": int(pred[i]),
                    "confidence": float(all_prob[i]),
                    "reasons": ["TF-IDF(text)+structured features LogisticRegression baseline"],
                    "used_refs": [],
                    "_latency_ms": 0,
                },
                "topk_indices": [],
                "topk_scores": [],
            }
            f.write(jsonl_safe_dumps(rec) + "\n")

    print(f"Saved -> {out_path}")
    print(f"n={len(df)} phish={int(y.sum())} benign={int((1-y).sum())}")


if __name__ == "__main__":
    main()
