from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import List

import faiss
import numpy as np
import pandas as pd
from openai import OpenAI


def _safe_str(x) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and x != x:  # NaN
        return ""
    return str(x)


def make_doc_text(row: dict) -> str:
    parts = []
    parts.append(f"URL: {_safe_str(row.get('final_url')) or _safe_str(row.get('url'))}")
    parts.append(f"LABEL: {int(row.get('label', 0))}")

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


def embed_texts(client: OpenAI, texts: List[str], model: str) -> np.ndarray:
    embs = []
    B = 10
    for i in range(0, len(texts), B):
        batch = texts[i : i + B]
        resp = client.embeddings.create(model=model, input=batch)
        for item in resp.data:
            embs.append(item.embedding)
    arr = np.array(embs, dtype="float32")
    faiss.normalize_L2(arr)
    return arr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--embed-model", required=True)
    ap.add_argument("--chunk-size", type=int, default=1200)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY environment variable")

    out_dir = Path(args.out_dir)
    print(f"[build_index] input={args.input}")
    print(f"[build_index] out_dir={out_dir.resolve()}")
    print(f"[build_index] base_url={base_url}")
    print(f"[build_index] embed_model={args.embed_model}")

    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.input)
    if args.limit and args.limit > 0:
        df = df.head(args.limit)

    docs = []
    meta = []
    for _, r in df.iterrows():
        row = r.to_dict()
        full = make_doc_text(row)
        s = full
        if len(s) <= args.chunk_size:
            docs.append(s)
            meta.append({"url": row.get("url"), "label": int(row.get("label", 0))})
        else:
            i = 0
            while i < len(s):
                docs.append(s[i : i + args.chunk_size])
                meta.append({"url": row.get("url"), "label": int(row.get("label", 0))})
                i += args.chunk_size

    print(f"[build_index] chunks={len(docs)}")

    client = OpenAI(api_key=api_key, base_url=base_url)
    vecs = embed_texts(client, docs, model=args.embed_model)
    dim = vecs.shape[1]
    print(f"[build_index] embedding_dim={dim}")

    index = faiss.IndexFlatIP(dim)
    index.add(vecs)

    index_path = out_dir / "index.faiss"
    meta_path = out_dir / "meta.jsonl"

    faiss.write_index(index, str(index_path))
    with open(meta_path, "w", encoding="utf-8") as f:
        for m in meta:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    print(f"[build_index] wrote {index_path}")
    print(f"[build_index] wrote {meta_path}")


if __name__ == "__main__":
    main()