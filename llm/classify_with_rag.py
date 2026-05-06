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


PROMPT = """你是网络安全方向的检测助手。给定一个网页的证据（URL、标题、文本片段、表单特征）以及检索到的参考案例/知识条目，请判断该网页是否为钓鱼网站。

要求：
- 只输出严格 JSON，不要输出多余文字
- JSON 键固定为：
  - is_phish: 0或1
  - confidence: 0到1之间小数
  - reasons: 字符串列表（<=5条，每条<=30字）
  - used_refs: 整数列表（引用了哪些 ref_idx）

网页证据：
{evidence}

参考资料：
{refs}
"""

def _safe_str(x) -> str:
    if x is None:
        return ""
    # pandas NaN: float and x!=x
    if isinstance(x, float) and x != x:
        return ""
    return str(x)

def load_index(index_dir: str):
    idx = faiss.read_index(str(Path(index_dir) / "index.faiss"))
    meta_lines = Path(index_dir).joinpath("meta.jsonl").read_text(encoding="utf-8").splitlines()
    meta = [json.loads(l) for l in meta_lines]
    return idx, meta


def embed_query(client: OpenAI, text: str, embed_model: str) -> np.ndarray:
    resp = client.embeddings.create(model=embed_model, input=[text])
    v = np.array(resp.data[0].embedding, dtype="float32").reshape(1, -1)  # (1, dim)
    faiss.normalize_L2(v)
    return v


def call_llm_json(client: OpenAI, model: str, prompt: str) -> dict:
    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是严谨的 JSON 输出器。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
    )
    dt_ms = int((time.perf_counter() - t0) * 1000)
    content = resp.choices[0].message.content or ""

    try:
        data = json.loads(content)
        if isinstance(data, dict):
            data["_latency_ms"] = dt_ms
            return data
    except Exception:
        pass
    return {"raw_output": content, "_latency_ms": dt_ms}


def make_evidence_text(r: dict, max_text_chars: int) -> str:
    url = _safe_str(r.get("final_url") or r.get("url"))
    title = _safe_str(r.get("title"))
    text = _safe_str(r.get("text_snippet"))[:max_text_chars]

    feats = (
        f"form_count={r.get('form_count')} "
        f"has_password_input={r.get('has_password_input')} "
        f"has_email_input={r.get('has_email_input')} "
        f"external_form_action={r.get('external_form_action')}"
    )
    return f"URL: {url}\nTITLE: {title}\nTEXT: {text}\nFEATURES: {feats}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", required=True, help="Evidence CSV")
    ap.add_argument("--index-dir", required=True)
    ap.add_argument("--embed-model", required=True, help="Embedding model (same family as index)")
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "qwen-plus"))
    ap.add_argument("--out", required=True, help="Output JSONL")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-text-chars", type=int, default=2000)
    args = ap.parse_args()

    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    api_key = os.environ.get("OPENAI_API_KEY", "").strip() or None
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY env var")
    client = OpenAI(api_key=api_key, base_url=base_url)

    idx, meta = load_index(args.index_dir)

    df = pd.read_csv(args.evidence)
    if args.limit and args.limit > 0:
        df = df.head(args.limit)

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)

    # --------- 断点续跑：读取已完成的 url ---------
    done_urls = set()
    if outp.exists() and outp.stat().st_size > 0:
        with open(outp, "r", encoding="utf-8") as rf:
            for line in rf:
                line = line.strip()
                if not line:
                    continue
                try:
                    j = json.loads(line)
                    u = j.get("url")
                    if u:
                        done_urls.add(u)
                except Exception:
                    # 如果尾部有半行坏行，不影响续跑
                    pass

    mode = "a" if done_urls else "w"
    print(f"Resume mode: {mode}, done={len(done_urls)} samples")

    with open(outp, mode, encoding="utf-8") as f:
        for _, row in df.iterrows():
            rowd = row.to_dict()
            url = rowd.get("url")
            if url in done_urls:
                continue

            evidence_text = make_evidence_text(rowd, max_text_chars=args.max_text_chars)

            qv = embed_query(client, evidence_text, embed_model=args.embed_model)
            D, I = idx.search(qv, args.topk)

            refs_lines = []
            for ref_idx in I[0].tolist():
                if 0 <= ref_idx < len(meta):
                    m = meta[ref_idx]
                    refs_lines.append(f"ref_idx={ref_idx} url={m.get('url')}")
            refs_text = "\n".join(refs_lines) if refs_lines else "(none)"
            if "label=" in refs_text:
                raise RuntimeError("Leakage detected: refs_text contains label=")

            prompt = PROMPT.format(evidence=evidence_text, refs=refs_text)

            try:
                out_json = call_llm_json(client, model=args.model, prompt=prompt)
            except Exception as e:
                # 如果额度/网络失败，先落盘错误，便于续跑与排查
                out_json = {"error": str(e)}

            rec = {
                "url": url,
                "label": int(rowd.get("label", 0)),
                "llm_out": out_json,
                "topk_indices": I[0].tolist(),
                "topk_scores": [float(x) for x in D[0].tolist()],
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()

    print(f"Saved → {outp}")


if __name__ == "__main__":
    main()