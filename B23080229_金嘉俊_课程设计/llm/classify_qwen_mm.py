import argparse
import base64
import json
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
from openai import OpenAI

# --- 配置区 ---
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3.5-omni-plus-2026-03-15"  # 确保这是你控制台里有的模型


# --- 工具函数 ---
def norm_text(s: str) -> str:
    """标准化文本：清理换行、多余空格和不可见字符"""
    if not isinstance(s, str):
        s = str(s)
    # 替换控制字符
    s = s.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    # 压缩多余空格
    return " ".join(s.split())


def to_data_url(image_path: str) -> str:
    """将图片路径转为 Data URL"""
    p = Path(image_path)
    ext = p.suffix.lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def extract_json(text: str) -> dict:
    """
    从模型输出的任意文本中提取 JSON 对象。
    能处理 ```json{...}``` 这种包裹情况。
    """
    text = (text or "").strip()

    # 尝试移除 Markdown 代码块标记
    if text.startswith("```"):
        # 匹配 ```json{...}``` 或 ```{...}```
        code_block = re.search(r"```(?:json)?\s*({.*})\s*```", text, re.DOTALL | re.IGNORECASE)
        if code_block:
            text = code_block.group(1)

    # 提取最外层的大括号内容
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if not json_match:
        raise ValueError(f"No JSON object found in response: {text[:200]}")

    try:
        return json.loads(json_match.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON Decode Error: {e} | Raw text: {text[:200]}")


# --- 核心逻辑 ---
def build_prompt(row: dict) -> str:
    """
    构建 Prompt。
    注意：为了防止乱码，这里强制使用英文指令，并要求模型输出英文理由。
    """
    url = str(row.get("url", ""))
    title = str(row.get("title", ""))
    snippet = str(row.get("text_snippet", row.get("snippet", "")))
    form_feat = str(row.get("form_features", row.get("form", "")))

    return (
        # --- 关键修改：使用英文 Prompt 防止乱码 ---
        "You are a Phishing Website Detector. Analyze BOTH the TEXT EVIDENCE and the SCREENSHOT.\n"
        "Output a STRICT JSON object only (no explanation, no markdown, no code fences):\n"
        "{\n"
        "  \"is_phish\": 0 or 1,\n"
        "  \"confidence\": float (0.0 to 1.0),\n"
        "  \"reasons\": [\"Brief reason 1\", \"Brief reason 2\"],\n"
        "  \"used_refs\": []\n"
        "}\n"
        # --- 关键约束：强制 ASCII 输出 ---
        "CONSTRAINTS:\n"
        "- Write 'reasons' in ENGLISH only.\n"
        "- Use ASCII characters only. NO emojis, NO special symbols.\n"
        "- Keep each reason under 30 words.\n\n"

        f"URL: {url}\n"
        f"Page Title: {title}\n"
        f"Text Snippet: {snippet}\n"
        f"Form Features: {form_feat}\n"
    )


# --- 主程序 ---
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to combined_evidence_mm.csv")
    ap.add_argument("--out", required=True, help="Output JSONL file path")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="Model name")
    ap.add_argument("--max-rows", type=int, default=0, help="Limit rows for testing (0=all)")
    args = ap.parse_args()

    # 1. 初始化 Client
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise SystemExit("ERROR: Please set DASHSCOPE_API_KEY environment variable.")

    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    # 2. 读取输入数据
    try:
        df = pd.read_csv(args.input)
        if args.max_rows > 0:
            df = df.head(args.max_rows)
        print(f"Loaded {len(df)} samples from {args.input}")
    except Exception as e:
        raise SystemExit(f"Failed to read CSV: {e}")

    # 3. 创建输出目录
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 4. 处理循环
    with out_path.open("w", encoding="utf-8") as f:
        for idx, row in df.iterrows():
            url = str(row.get("url", "N/A"))
            label = row.get("label")  # 可能为 NaN
            screenshot_path = str(row.get("screenshot_path", "")).strip()

            # 构建多模态消息
            content = [
                {"type": "text", "text": build_prompt(row)}
            ]

            # 检查并添加图片
            p_img = Path(screenshot_path) if screenshot_path else None
            if p_img and p_img.is_file():
                content.append({
                    "type": "image_url",
                    "image_url": {"url": to_data_url(str(p_img))}
                })
            else:
                # 如果没有截图，显式告诉模型
                content.append({
                    "type": "text",
                    "text": "[WARNING] No screenshot available. Please judge based on text evidence only."
                })

            messages = [{"role": "user", "content": content}]

            # 调用模型
            t0 = time.time()
            try:
                resp = client.chat.completions.create(
                    model=args.model,
                    messages=messages,
                    temperature=0.1,  # 稍微有一点随机性避免死板，也可以设为 0
                )
                latency_ms = int((time.time() - t0) * 1000)
                raw_response = resp.choices[0].message.content or ""

                # 解析 JSON
                j = extract_json(raw_response)

                # ====================== 你要求的修改 ======================
                # 处理 reasons：获取 → 标准化 → 保留前2条
                reasons = j.get("reasons", [])
                reasons = [norm_text(x) for x in reasons][:2]

                # 清理 confidence
                try:
                    conf = float(j.get("confidence", 0.5))
                    conf = max(0.0, min(1.0, conf))
                except:
                    conf = 0.5

                # 构造 llm_out（直接使用处理后的 reasons）
                llm_out = {
                    "is_phish": int(j.get("is_phish", 0)),
                    "confidence": conf,
                    "reasons": reasons,
                    "used_refs": j.get("used_refs", []),
                    "_latency_ms": latency_ms,
                }
                # ==========================================================

                rec = {
                    "url": url,
                    "label": label if pd.notna(label) else None,
                    "llm_out": llm_out,
                    "topk_indices": [],
                    "topk_scores": [],
                }

            except Exception as e:
                # 异常处理：记录错误信息
                latency_ms = int((time.time() - t0) * 1000)
                error_msg = norm_text(f"EXCEPTION: {type(e).__name__}: {str(e)}")

                rec = {
                    "url": url,
                    "label": label if pd.notna(label) else None,
                    "llm_out": {
                        "is_phish": 0,
                        "confidence": 0.0,
                        "reasons": [error_msg],
                        "used_refs": [],
                        "_latency_ms": latency_ms,
                    },
                    "topk_indices": [],
                    "topk_scores": [],
                }

            # 写入文件
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()  # 立即写入磁盘，防止程序中断丢失数据

            print(f"[{idx + 1}/{len(df)}] {url} | Latency: {rec['llm_out']['_latency_ms']}ms")


if __name__ == "__main__":
    main()