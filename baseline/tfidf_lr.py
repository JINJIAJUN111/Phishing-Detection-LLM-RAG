# baselines/tfidf_lr.py
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


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
    # 尽量贴近你 LLM 的证据：URL + title + snippet
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

    # labels
    y = df["label"].astype(int).to_numpy()

    # text
    texts = [build_text(r) for r in df.to_dict(orient="records")]
    vec = TfidfVectorizer(
        max_features=args.max_features,
        ngram_range=(1, 2),
        min_df=2,
        strip_accents=None,
        lowercase=True,
    )
    X_text = vec.fit_transform(texts)

    # numeric/bool features (结构化特征)
    # 注意：external_form_action / has_* 可能是 True/False / 0/1 / "True"
    def as_num(col, default=0.0):
        s = df.get(col)
        if s is None:
            return np.full(len(df), default, dtype=np.float32)
        return pd.to_numeric(s, errors="coerce").fillna(default).astype(np.float32).to_numpy()

    X_num = np.vstack([
        as_num("form_count", 0.0),
        as_num("has_password_input", 0.0),
        as_num("has_email_input", 0.0),
        as_num("external_form_action", 0.0),
        as_num("status_code", 0.0),
        as_num("elapsed_ms", 0.0),
    ]).T
    X_num = csr_matrix(X_num)

    X = hstack([X_text, X_num], format="csr")

    # Train on full set, then predict on full set (与你当前 evaluate.py 的用法一致)
    clf = LogisticRegression(
        C=args.C,
        max_iter=2000,
        n_jobs=None,
        solver="liblinear",
    )
    clf.fit(X, y)

    prob = clf.predict_proba(X)[:, 1]
    pred = (prob >= 0.5).astype(int)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        for i, row in enumerate(df.to_dict(orient="records")):
            url = safe_str(row.get("final_url") or row.get("url")).strip()
            rec = {
                "url": url,
                "label": int(row["label"]),
                "llm_out": {  # 复用 evaluate.py 读取字段
                    "is_phish": int(pred[i]),
                    "confidence": float(prob[i]),
                    "reasons": [
                        "TF-IDF(text) + structured features baseline (LogisticRegression)"
                    ],
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