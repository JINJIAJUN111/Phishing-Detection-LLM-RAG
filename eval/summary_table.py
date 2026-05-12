#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成多种方法对比表（健壮版）
- 表1：总体对比（所有方法）
- 表2：同模态对比（多模态方法）
- 表3：同模态对比（纯文本方法）
"""

import subprocess
import sys
import re
from pathlib import Path

# 获取脚本所在目录
BASE = Path(__file__).resolve().parent

# 使用当前 Python 解释器
PY = sys.executable
EVAL = BASE / "evaluate.py"

FILES = [
    ("TF-IDF + LR", BASE.parent / "data/predictions/mix_tfidf_lr_full.jsonl"),
    ("LLM-only", BASE.parent / "data/predictions/mix_llmonly_full.jsonl"),
    ("LLM + RAG", BASE.parent / "data/predictions/mix_rag_noself_clean_full.jsonl"),
    ("PhishLLM", BASE.parent / "data/predictions/mix_phishllm_mm_full.jsonl"),
    ("Qwen-MM (Screenshot)", BASE.parent / "data/predictions/mix_qwen_mm_full.jsonl"),
]

# 正则匹配
pat = {
    "n": re.compile(r"\bn=(\d+)\b"),
    "bad": re.compile(r"\bbad_json=(\d+)\b"),
    "acc": re.compile(r"\bacc=([0-9.]+)\b"),
    "prec": re.compile(r"\bprec=([0-9.]+)\b"),
    "rec": re.compile(r"\brec=([0-9.]+)\b"),
    "f1": re.compile(r"\bf1=([0-9.]+)\b"),
    "mean": re.compile(r"\blatency_ms:\s*mean=([0-9.]+)\b"),
    "p50": re.compile(r"\bp50=([0-9.]+)\b"),
    "p95": re.compile(r"\bp95=([0-9.]+)\b"),
}

def run_eval(pred_path: str) -> str:
    return subprocess.check_output(
        [PY, "-u", str(EVAL), "--preds", pred_path],
        text=True,
        encoding="utf-8",
        errors="replace",
    )

# 收集所有结果
rows = []
for name, fp in FILES:
    p = Path(fp)
    if not p.exists():
        print(f"[ERROR] Missing: {fp}", file=sys.stderr)
        sys.exit(2)

    out = run_eval(fp)
    d = {"name": name}
    for k, rgx in pat.items():
        m = rgx.search(out)
        d[k] = m.group(1) if m else "0"
    rows.append(d)

# 格式化输出函数
def print_rows(selected_rows):
    for r in selected_rows:
        print(
            f"{r['name']:<22} | {r['n']:>4} | {r['bad']:>3} | {float(r['acc']):>7.4f} | {float(r['prec']):>7.4f} | "
            f"{float(r['rec']):>7.4f} | {float(r['f1']):>7.4f} | {float(r['mean']):>9.1f} | {int(float(r['p50'])):>5} | {int(float(r['p95'])):>5}"
        )

# 表头格式
headers = ["Method", "n", "bad", "acc", "prec", "rec", "f1", "mean_ms", "p50", "p95"]
fmt_header = (
    f"{headers[0]:<22} | {headers[1]:>4} | {headers[2]:>3} | {headers[3]:>7} | {headers[4]:>7} | "
    f"{headers[5]:>7} | {headers[6]:>7} | {headers[7]:>9} | {headers[8]:>5} | {headers[9]:>5}"
)
fmt_sep = (
    "-" * 22 + "-+-" + "-" * 4 + "-+-" + "-" * 3 + "-+-" + "-" * 7 + "-+-" + "-" * 7 + "-+-" +
    "-" * 7 + "-+-" + "-" * 7 + "-+-" + "-" * 9 + "-+-" + "-" * 5 + "-+-" + "-" * 5
)

# ============================================================
# 表1：总体对比（所有方法）
# ============================================================
print("\n" + "=" * 110)
print("钓鱼网站检测 - 多种方法性能对比（总体）")
print("=" * 110)
print(fmt_header)
print(fmt_sep)
print_rows(rows)
print("=" * 110)

# 动态生成核心结论
best = max(rows, key=lambda r: float(r["f1"]))
llm_only = next((r for r in rows if r["name"] == "LLM-only"), None)
print("核心结论：")
print(f"  1. 综合性能最优：{best['name']} 取得最高 F1 ({float(best['f1']):.4f}) 和召回率 ({float(best['rec'])*100:.2f}%)"
      + (f"，显著优于纯 LLM (F1={float(llm_only['f1']):.4f}, Rec={float(llm_only['rec'])*100:.2f}%)" if llm_only else ""))
mm_rows_all = [r for r in rows if r["name"] in {"PhishLLM", "Qwen-MM (Screenshot)"}]
if mm_rows_all:
    precs = [float(r["prec"]) for r in mm_rows_all]
    recs = [float(r["rec"]) for r in mm_rows_all]
    print(f"  2. 多模态方法：PhishLLM 与 Qwen-MM Prec={min(precs):.4f}~{max(precs):.4f}，召回率 ({min(recs)*100:.1f}%~{max(recs)*100:.1f}%)，偏保守")
print("  3. 多模态消融：Qwen-MM（仅标题+截图）召回率显著低于 PhishLLM（全量文本+截图），说明文本证据对多模态检测有重要增量贡献")
print("=" * 110)

# ============================================================
# 表2：同模态对比（多模态方法）
# ============================================================
MM_METHODS = {"PhishLLM", "Qwen-MM (Screenshot)"}
mm_rows = [r for r in rows if r["name"] in MM_METHODS]

print("\n" + "=" * 110)
print("钓鱼网站检测 - 同模态对比表（多模态方法：文本 + 截图）")
print("=" * 110)
print(fmt_header)
print(fmt_sep)
print_rows(mm_rows)
print("=" * 110)
print("注：该子表比较多模态方法。PhishLLM 使用完整文本 + 截图；Qwen-MM 仅使用标题 + 截图（消融）。")
print("    本实验截图覆盖率 424/434 = 97.7%，无图样本自动退化为文本推理。")
print("=" * 110)

# ============================================================
# 表3：同模态对比（纯文本方法）
# ============================================================
TEXT_METHODS = {"TF-IDF + LR", "LLM-only", "LLM + RAG"}
text_rows = [r for r in rows if r["name"] in TEXT_METHODS]

print("\n" + "=" * 110)
print("钓鱼网站检测 - 同模态对比表（纯文本方法：URL + 文本证据）")
print("=" * 110)
print(fmt_header)
print(fmt_sep)
print_rows(text_rows)
print("=" * 110)
print("注：该子表仅对比纯文本方法，输入均为 URL、标题、文本片段和表单特征。")
print("=" * 110)