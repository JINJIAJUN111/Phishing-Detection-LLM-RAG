#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成 Figure5: 纯文本方法对比图
"""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# Global style
plt.rcParams.update({
    "font.family": "Times New Roman",
    "axes.titlesize": 20,
    "axes.titleweight": "bold",
    "axes.labelsize": 18,
    "axes.labelweight": "bold",
    "xtick.labelsize": 15,
    "ytick.labelsize": 16,
    "legend.fontsize": 12,
    "legend.title_fontsize": 13,
})

def style_axes(ax):
    """thick black border like academic figures"""
    for spine in ax.spines.values():
        spine.set_linewidth(2.2)
        spine.set_color("black")
    ax.tick_params(width=2.0, length=6)
    ax.grid(True, axis="y", linestyle=":", linewidth=1.0, alpha=0.25)

# Create results directory
Path("results").mkdir(exist_ok=True)

# 纯文本方法数据（从 summary_table.txt）
text_methods = [
    "TF-IDF + LR",
    "LLM-only",
    "LLM + RAG\n(NoSelf, clean)"
]

text_rec = [0.7848, 0.4557, 0.5823]
text_f1 = [0.8611, 0.6154, 0.7302]

# Colors
C_REC = "#55A868"  # green
C_F1 = "#8172B2"   # purple

x = np.arange(len(text_methods))
fig, ax = plt.subplots(figsize=(10, 6))
w = 0.38

bars_rec = ax.bar(x - w/2, text_rec, width=w, color=C_REC,
                  edgecolor="black", linewidth=1.5, label="Recall")
bars_f1 = ax.bar(x + w/2, text_f1, width=w, color=C_F1,
                 edgecolor="black", linewidth=1.5, alpha=0.85, label="F1-Score")

ax.set_xticks(x)
ax.set_xticklabels(text_methods, rotation=0, ha="center", fontsize=14)
ax.set_ylim(0, 1.0)
ax.set_ylabel("Score", fontsize=18, fontweight="bold")
ax.set_title("Figure 5: Text-Only Methods Comparison",
             pad=14, fontsize=20, fontweight="bold")

style_axes(ax)
ax.legend(loc="upper left", frameon=True, edgecolor="black", fontsize=12)

# Value labels
for i, v in enumerate(text_rec):
    ax.text(i - w/2, v + 0.015, f"{v:.4f}",
            ha="center", fontsize=13, fontweight="bold")
for i, v in enumerate(text_f1):
    ax.text(i + w/2, v + 0.015, f"{v:.4f}",
            ha="center", fontsize=13, fontweight="bold")

fig.subplots_adjust(bottom=0.14)
fig.tight_layout()
fig.savefig("results/Figure5_TextOnly_Comparison.png", dpi=300)
print("Figure 5 generated: results/Figure5_TextOnly_Comparison.png")

