#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
钓鱼网站检测系统 - 离线演示程序（推荐最终版）
- 读取 data/predictions 下四份 jsonl
- 计算 acc/prec/rec/f1 + latency p50/p95
- 不需要 API Key / 网络 / Docker
- 不依赖 eval/summary_table.py 或 .venv
- 支持多种目录结构，不会跑到 _MEIxxxx 临时目录
- p50/p95 计算方式与 evaluate.py 完全一致
- 修复双加号显示问题
- 召回率增量使用 pp（百分点）而非 %
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load_preds(path: Path) -> tuple[list[int], list[int], list[int], int]:
    """
    Returns (y_true, y_pred, lat_ms, bad_json_count)
    Expected jsonl format per line:
      {"label":0/1, "llm_out":{"is_phish":0/1, "_latency_ms":123}}  # LLM/RAG
      OR {"label":0/1, "pred":0/1} etc. (we'll try a few fallbacks)
    """
    y_true: list[int] = []
    y_pred: list[int] = []
    lat: list[int] = []
    bad = 0

    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            bad += 1
            continue

        y_true.append(int(r.get("label", 0)))

        pred: int | None = None
        out = r.get("llm_out")

        if isinstance(out, dict) and "is_phish" in out:
            pred = int(out["is_phish"])
            if "_latency_ms" in out:
                try:
                    lat.append(int(out["_latency_ms"]))
                except Exception:
                    pass
        elif "is_phish" in r:
            pred = int(r["is_phish"])
        elif "pred" in r:
            pred = int(r["pred"])
        elif "y_pred" in r:
            pred = int(r["y_pred"])

        if pred is None:
            bad += 1
            pred = 0

        y_pred.append(pred)

    return y_true, y_pred, lat, bad


def metrics(y_true: list[int], y_pred: list[int]) -> tuple[float, float, float, float]:
    """binary classification, positive=1"""
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)

    acc = (tp + tn) / max(1, len(y_true))
    prec = tp / max(1, (tp + fp))
    rec = tp / max(1, (tp + fn))
    f1 = (2 * prec * rec) / max(1e-12, (prec + rec))
    return acc, prec, rec, f1


def latency_stats(lat: list[int]) -> tuple[float, int, int]:
    """
    计算延迟统计，与 evaluate.py 完全一致：
    - mean: 平均值
    - p50: 中位数（len//2）
    - p95: int(len * 0.95) 位置的索引，防止越界
    """
    if not lat:
        return 0.0, 0, 0

    lat_sorted = sorted(lat)
    n = len(lat_sorted)
    mean_ms = sum(lat_sorted) / n

    # 与 evaluate.py 完全一致
    p50 = lat_sorted[n // 2]
    p95_idx = int(n * 0.95)
    # 防止越界（当 n=1 时 int(1*0.95)=0，安全；极端情况 n=0 已处理）
    p95 = lat_sorted[min(p95_idx, n - 1)]

    return mean_ms, p50, p95


def find_predictions_dir() -> Path | None:
    """
    智能查找 predictions 目录，支持多种提交包结构。
    完全不依赖 _MEIPASS，不会跑到 Temp 目录。

    策略：
    1. 优先使用当前工作目录（cwd）
    2. 其次使用 exe 所在目录
    3. 再次使用 exe 的父目录（适配 01_可执行文件/ 结构）
    """
    exe_dir = Path(sys.argv[0]).resolve().parent  # demo_offline.exe 所在目录
    cwd = Path.cwd().resolve()  # 当前工作目录

    candidates = [
        # 1) 在当前工作目录下（最常见：在解压目录运行）
        cwd / "data" / "predictions",
        cwd / "03_数据文件" / "data" / "predictions",

        # 2) 在 exe 所在目录下（双击运行时常见）
        exe_dir / "data" / "predictions",
        exe_dir / "03_数据文件" / "data" / "predictions",

        # 3) exe 的父目录（如果 exe 在 01_可执行文件/，数据在同级 03_数据文件/）
        exe_dir.parent / "data" / "predictions",
        exe_dir.parent / "03_数据文件" / "data" / "predictions",
    ]

    # 去重，保留顺序
    seen = set()
    unique_candidates = []
    for p in candidates:
        if p not in seen:
            seen.add(p)
            unique_candidates.append(p)

    for p in unique_candidates:
        if p.exists() and p.is_dir():
            # 检查是否包含关键文件
            required = ["mix_tfidf_lr_full.jsonl", "mix_llmonly_full.jsonl", "mix_rag_noself_full.jsonl", "mix_phishllm_mm_full.jsonl"]
            if all((p / f).exists() for f in required):
                return p

    # 都找不到，打印调试信息
    print("[ERROR] 找不到 predictions 目录。请确认提交包目录结构正确。")
    print("尝试过的路径:")
    for p in unique_candidates:
        if p.exists():
            print(f"  - {p} (存在但缺少必要文件)")
        else:
            print(f"  - {p} (不存在)")
    print("\n期望的结构（任选其一）：")
    print("  方案1: ./data/predictions/")
    print("  方案2: ./03_数据文件/data/predictions/")
    print("  方案3: 01_可执行文件/同级目录下的 03_数据文件/data/predictions/")
    return None


def main() -> int:
    print("=" * 60)
    print("    钓鱼网站检测系统 - 离线演示程序")
    print("=" * 60)
    print()

    # 查找 predictions 目录
    print("[1/3] 查找预测文件目录...")
    pred_dir = find_predictions_dir()
    if pred_dir is None:
        input("按回车键退出...")
        return 2
    print(f"  [OK] 找到: {pred_dir}")
    print()

    # 定义预测文件（4种方法）
    files = [
        ("TF-IDF + LR", pred_dir / "mix_tfidf_lr_full.jsonl"),
        ("LLM-only", pred_dir / "mix_llmonly_full.jsonl"),
        ("LLM + RAG (NoSelf)", pred_dir / "mix_rag_noself_full.jsonl"),
        ("PhishLLM (MM baseline)", pred_dir / "mix_phishllm_mm_full.jsonl"),
    ]

    print("[2/3] 检查预测文件...")
    for name, p in files:
        if not p.exists():
            print(f"  [MISSING] {name}: {p}")
            print("\n[ERROR] 缺少预测文件")
            input("按回车键退出...")
            return 2
        size_kb = p.stat().st_size / 1024
        print(f"  [OK] {name}: {p.name} ({size_kb:.1f} KB)")
    print()

    print("[3/3] 计算并输出对比结果（离线）...")
    print()

    rows = []
    for name, p in files:
        y_true, y_pred, lat, bad = load_preds(p)
        acc, prec, rec, f1 = metrics(y_true, y_pred)
        mean_ms, p50, p95 = latency_stats(lat)

        rows.append({
            "name": name,
            "n": len(y_true),
            "bad": bad,
            "acc": acc,
            "prec": prec,
            "rec": rec,
            "f1": f1,
            "mean_ms": mean_ms,
            "p50": p50,
            "p95": p95,
        })

    # 输出表格
    print("=" * 100)
    print("钓鱼网站检测 - 四种方法性能对比（离线复现）")
    print("=" * 100)
    print(
        f"{'Method':<22} | {'n':>4} | {'bad':>3} | {'acc':>6} | {'prec':>6} | {'rec':>6} | {'f1':>6} | {'mean_ms':>8} | {'p50':>5} | {'p95':>5}")
    print(
        "-" * 22 + "-+-" + "-" * 4 + "-+-" + "-" * 3 + "-+-" + "-" * 6 + "-+-" + "-" * 6 + "-+-" + "-" * 6 + "-+-" + "-" * 6 + "-+-" + "-" * 8 + "-+-" + "-" * 5 + "-+-" + "-" * 5)

    for r in rows:
        print(
            f"{r['name']:<22} | {r['n']:>4} | {r['bad']:>3} | {r['acc']:.4f} | {r['prec']:.4f} | {r['rec']:.4f} | {r['f1']:.4f} | {r['mean_ms']:>8.1f} | {r['p50']:>5} | {r['p95']:>5}")

    print("=" * 100)
    print()

    # 输出核心结论
    llm = next(r for r in rows if r["name"] == "LLM-only")
    rag = next(r for r in rows if r["name"] == "LLM + RAG (NoSelf)")
    lr = next(r for r in rows if r["name"] == "TF-IDF + LR")
    mm = next(r for r in rows if r["name"] == "PhishLLM (MM baseline)")

    recall_gain_pp = (rag["rec"] - llm["rec"]) * 100
    f1_gain = rag["f1"] - llm["f1"]
    latency_gain = rag["p50"] - llm["p50"]

    print("=" * 60)
    print("核心结论")
    print("=" * 60)
    print(f"LLM + RAG (NoSelf) 相比 LLM-only：")
    print(f"  - 召回率 (Recall) : {llm['rec'] * 100:.2f}% -> {rag['rec'] * 100:.2f}% ({recall_gain_pp:+.2f} pp)")
    print(f"  - F1 分数          : {llm['f1']:.4f} -> {rag['f1']:.4f} ({f1_gain:+.4f})")
    print(f"  - 优于传统 TF-IDF+LR (F1={lr['f1']:.4f})")
    print(f"  - 延迟代价：p50 {llm['p50']}ms -> {rag['p50']}ms ({latency_gain:+.0f}ms)")
    print()
    print(f"PhishLLM (MM baseline) 结果：")
    print(f"  - 准确率: {mm['acc']:.4f}")
    print(f"  - 召回率: {mm['rec']*100:.2f}%")
    print(f"  - F1分数: {mm['f1']:.4f}")
    print("=" * 60)
    print()
    print("演示完成。")
    print("说明：本程序为离线演示，使用已生成的预测结果文件，无需 API Key。")

    return 0


def wait_for_exit():
    """仅在交互式终端中等待按键，双击运行时自动退出"""
    if sys.stdin is not None and sys.stdin.isatty():
        try:
            input("\n按回车键退出...")
        except EOFError:
            pass


if __name__ == "__main__":
    exit_code = main()
    wait_for_exit()
    sys.exit(exit_code)