from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import faiss
import numpy as np
import pandas as pd
from openai import OpenAI
from sentence_transformers import SentenceTransformer


def _safe_str(x) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and x != x:
        return ""
    return str(x)

def _jsonl_safe_dumps(obj) -> str:
    """
    Dump JSON that is safe for JSONL (one record per line).
    It neutralizes real line separators that could split a record across lines.
    """
    s = json.dumps(obj, ensure_ascii=False)
    return (
        s.replace("\r", "\\r")
         .replace("\n", "\\n")
         .replace("\u2028", "\\u2028")
         .replace("\u2029", "\\u2029")
    )


def _load_done_urls(out_path: Path) -> set[str]:
    done = set()
    if not out_path.exists():
        return done
    # best-effort: skip bad lines but keep progress
    with open(out_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            u = _safe_str(rec.get("url")).strip()
            if u:
                done.add(u)
    return done


def make_evidence_text(row: dict) -> str:
    url = _safe_str(row.get("final_url")) or _safe_str(row.get("url"))
    title = _safe_str(row.get("title")).strip()
    snippet = _safe_str(row.get("text_snippet")).strip()

    feats = []
    for k in ("form_count", "has_password_input", "has_email_input", "external_form_action", "content_type"):
        v = row.get(k)
        if v is None:
            continue
        if isinstance(v, float) and v != v:
            continue
        feats.append(f"{k}={v}")

    parts = [f"URL: {url}"]
    if title:
        parts.append(f"TITLE: {title}")
    if snippet:
        parts.append(f"TEXT: {snippet[:1500]}")
    if feats:
        parts.append("FEATURES: " + ", ".join(feats))
    return "\n".join(parts)


def build_prompt(evidence_text: str, refs: list[dict]) -> str:
    ref_block = "\n\n".join(
        [f"[REF {i}] url={r.get('url', '')}" for i, r in enumerate(refs)]
    )
    return f"""You are a phishing website detector.
Decide if the target URL is phishing (1) or benign (0).

Return STRICT JSON only:
{{"is_phish": 0 or 1, "confidence": 0-1, "reasons": [..], "used_refs": [..]}}

[TARGET]
{evidence_text}

[RETRIEVED_REFS]
{ref_block}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--index-dir", required=True)
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--model", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--local-embed-model", default=None)
    ap.add_argument("--no-rag", action="store_true", help="Disable retrieval; LLM-only baseline")
    args = ap.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY env var")

    index_dir = Path(args.index_dir)
    idx = faiss.read_index(str(index_dir / "index.faiss"))

    meta = []
    with open(index_dir / "meta.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            meta.append(json.loads(line))

    local_model_name = args.local_embed_model
    if local_model_name is None:
        lm_path = index_dir / "local_model.txt"
        if lm_path.exists():
            local_model_name = lm_path.read_text(encoding="utf-8").strip()
        else:
            local_model_name = "all-MiniLM-L6-v2"

    st = SentenceTransformer(local_model_name)
    client = OpenAI(api_key=api_key, base_url=base_url)

    df = pd.read_csv(args.evidence)
    if args.limit and args.limit > 0:
        df = df.head(args.limit)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 断点续跑：加载已处理的 URL
    done_urls = _load_done_urls(out_path)
    if done_urls:
        print(f"Resume enabled: found {len(done_urls)} completed URLs in {out_path}")

    # 追加模式写入
    with open(out_path, "a", encoding="utf-8", newline="\n") as f:
        for _, r in df.iterrows():
            row = r.to_dict()
            url = (_safe_str(row.get("final_url")) or _safe_str(row.get("url"))).strip()
            if not url:
                continue

            # 跳过已处理的 URL
            if url in done_urls:
                continue

            label = int(row.get("label", 0))
            evidence_text = make_evidence_text(row)

            qv = st.encode([evidence_text], normalize_embeddings=True)
            qv = np.asarray(qv, dtype="float32")

            # 检索并排除自身
            search_k = max(args.topk * 5, args.topk)
            D, I = idx.search(qv, search_k)

            target_url = (_safe_str(row.get("final_url")) or _safe_str(row.get("url"))).strip()

            refs = []
            topk_indices = []
            topk_scores = []

            if not args.no_rag:
                for score, idx_i in zip(D[0].tolist(), I[0].tolist()):
                    if idx_i < 0 or idx_i >= len(meta):
                        continue
                    ref = meta[idx_i]
                    ref_url = _safe_str(ref.get("url")).strip()
                    if ref_url == target_url:
                        continue

                    refs.append(ref)
                    topk_indices.append(idx_i)
                    topk_scores.append(score)

                    if len(refs) >= args.topk:
                        break

            prompt = build_prompt(evidence_text, refs)

            t0 = time.time()
            try:
                resp = client.chat.completions.create(
                    model=args.model,
                    messages=[
                        {"role": "system", "content": "You are a careful security classifier."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0,
                )
                dt_ms = int((time.time() - t0) * 1000)
                text = resp.choices[0].message.content
            except Exception as e:
                dt_ms = int((time.time() - t0) * 1000)
                text = ""
                llm_out = {"error": repr(e)}
            else:
                try:
                    llm_out = json.loads(text)
                except Exception:
                    llm_out = {"raw": text}

            if isinstance(llm_out, dict):
                llm_out["_latency_ms"] = dt_ms

            rec = {
                "url": url,
                "label": label,
                "llm_out": llm_out,
                "topk_indices": topk_indices,
                "topk_scores": topk_scores,
            }

            f.write(_jsonl_safe_dumps(rec) + "\n")
            f.flush()

            done_urls.add(url)

    print(f"Saved → {out_path}")


if __name__ == "__main__":
    main()