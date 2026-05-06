from __future__ import annotations

import argparse
import json
from pathlib import Path

import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


def _safe_str(x) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and x != x:  # NaN
        return ""
    return str(x)


def make_doc_text(row: dict) -> str:
    parts = []
    parts.append(f"URL: {_safe_str(row.get('final_url')) or _safe_str(row.get('url'))}")

    title = _safe_str(row.get("title")).strip()
    if title:
        parts.append(f"TITLE: {title}")

    text = _safe_str(row.get("text_snippet")).strip()
    if text:
        parts.append("TEXT: " + (text[:2000] + "..." if len(text) > 2000 else text))

    feats = []
    for k in ("form_count", "has_password_input", "has_email_input", "external_form_action", "content_type"):
        v = row.get(k)
        if v is None:
            continue
        if isinstance(v, float) and v != v:
            continue
        feats.append(f"{k}={v}")
    if feats:
        parts.append("FEATURES: " + ", ".join(feats))

    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--local-model", default="all-MiniLM-L6-v2")
    ap.add_argument("--chunk-size", type=int, default=1200)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[local_build] input={args.input}")
    print(f"[local_build] out_dir={out_dir.resolve()}")
    print(f"[local_build] local_model={args.local_model}")

    df = pd.read_csv(args.input)
    if args.limit and args.limit > 0:
        df = df.head(args.limit)

    docs, meta = [], []
    for _, r in df.iterrows():
        row = r.to_dict()
        full = make_doc_text(row)
        if len(full) <= args.chunk_size:
            docs.append(full)
            meta.append({"url": row.get("url"), "label": int(row.get("label", 0))})
        else:
            i = 0
            while i < len(full):
                docs.append(full[i : i + args.chunk_size])
                meta.append({"url": row.get("url"), "label": int(row.get("label", 0))})
                i += args.chunk_size

    print(f"[local_build] chunks={len(docs)}")

    model = SentenceTransformer(args.local_model)
    vecs = model.encode(
        docs,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    vecs = np.asarray(vecs, dtype="float32")
    dim = vecs.shape[1]
    print(f"[local_build] embedding_dim={dim}")

    index = faiss.IndexFlatIP(dim)
    index.add(vecs)

    faiss.write_index(index, str(out_dir / "index.faiss"))
    (out_dir / "local_model.txt").write_text(args.local_model, encoding="utf-8")
    with open(out_dir / "meta.jsonl", "w", encoding="utf-8") as f:
        for m in meta:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    print(f"[local_build] wrote {out_dir/'index.faiss'}")
    print(f"[local_build] wrote {out_dir/'meta.jsonl'}")


if __name__ == "__main__":
    main()