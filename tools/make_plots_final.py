from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# -----------------------------
# Global style (match your figures)
# -----------------------------
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

# -----------------------------
# Metrics (from your summary_table output)
# 更新为 clean 版本数据
# -----------------------------
methods = [
    "TF-IDF + LR",
    "LLM-only",
    "LLM + RAG (NoSelf, clean)",
    "PhishLLM (MM baseline)",
    "Qwen-MM (img+text)",
]

acc = [0.9539, 0.8963, 0.9217, 0.9309, 0.9286]
prec = [0.9538, 0.9474, 0.9787, 1.0000, 1.0000]
rec = [0.7848, 0.4557, 0.5823, 0.6203, 0.6076]
f1 = [0.8611, 0.6154, 0.7302, 0.7656, 0.7559]

# Latency (ms) - only methods that call LLM
lat_methods = ["LLM-only", "LLM + RAG (NoSelf, clean)", "PhishLLM (MM baseline)", "Qwen-MM (img+text)"]
lat_mean = [1789.9, 850.1, 2298.5, 2556.5]
lat_p50 = [1758, 762, 2205, 2450]
lat_p95 = [2506, 949, 3240, 3380]

# -----------------------------
# Colors (academic, colorblind-friendly)
# -----------------------------
C_ACC = "#4C72B0"  # blue
C_PREC = "#DD8452"  # orange
C_REC = "#55A868"  # green
C_F1 = "#8172B2"  # purple (different from Accuracy)
C_P50 = "#DD8452"  # orange
C_P95 = "#D55E00"  # dark orange
C_MEAN = "#E5AE38"  # gold

# -----------------------------
# Figure 1: Performance Comparison (Acc/Prec/Rec/F1)
# -----------------------------
x = np.arange(len(methods))
w = 0.18

fig, ax = plt.subplots(figsize=(18, 8))

bars1 = ax.bar(x - 1.5 * w, acc, width=w, color=C_ACC, edgecolor="black", linewidth=1.5, label="Accuracy")
bars2 = ax.bar(x - 0.5 * w, prec, width=w, color=C_PREC, edgecolor="black", linewidth=1.5, label="Precision")
bars3 = ax.bar(x + 0.5 * w, rec, width=w, color=C_REC, edgecolor="black", linewidth=1.5, label="Recall")
bars4 = ax.bar(x + 1.5 * w, f1, width=w, color=C_F1, edgecolor="black", linewidth=1.5, alpha=0.85, label="F1-Score")

ax.set_xticks(x)
ax.set_xticklabels(methods, rotation=18, ha="right", fontsize=14)
ax.set_ylim(0, 1.05)
ax.set_ylabel("Performance Score", fontsize=18, fontweight="bold")
ax.set_xlabel("Detection Methods", fontsize=18, fontweight="bold")
ax.set_title("Figure 1: Performance Comparison of Phishing Detection Methods", pad=18, fontsize=20, fontweight="bold")

style_axes(ax)
# 图例放在右上角，避免左侧拥挤
ax.legend(title="Metrics", loc="upper right", frameon=True, edgecolor="black")


# Value labels
def label_bars(bars, fmt="{:.4f}", dy=0.012, fs=11):
    for b in bars:
        h = b.get_height()
        if h > 0:
            ax.text(b.get_x() + b.get_width() / 2, h + dy, fmt.format(h),
                    ha="center", va="bottom", fontsize=fs)


label_bars(bars1, fs=11)
label_bars(bars2, fs=11)
label_bars(bars3, fs=11)
label_bars(bars4, fs=11)

fig.subplots_adjust(bottom=0.18)
fig.tight_layout()
fig.savefig("results/Figure1_Performance_AllMethods.png", dpi=300)
plt.close(fig)

# -----------------------------
# Figure 2: Recall & F1 Comparison (with 0.8 baseline)
# -----------------------------
fig, ax = plt.subplots(figsize=(18, 8))
w2 = 0.35

bars_r = ax.bar(x - w2 / 2, rec, width=w2, color=C_REC, edgecolor="black", linewidth=1.5, label="Recall")
bars_f = ax.bar(x + w2 / 2, f1, width=w2, color=C_F1, edgecolor="black", linewidth=1.5, alpha=0.85, label="F1-Score")

ax.axhline(0.8, color="gray", linestyle="--", linewidth=2.0, alpha=0.7, label="0.8 Baseline")

ax.set_xticks(x)
ax.set_xticklabels(methods, rotation=18, ha="right", fontsize=14)
ax.set_ylim(0, 1.0)
ax.set_ylabel("Score", fontsize=18, fontweight="bold")
ax.set_xlabel("Detection Methods", fontsize=18, fontweight="bold")
ax.set_title("Figure 2: Recall and F1-Score Comparison", pad=18, fontsize=20, fontweight="bold")

style_axes(ax)
ax.legend(loc="upper left", frameon=True, edgecolor="black", fontsize=12)

# Bold value labels
for b in bars_r:
    h = b.get_height()
    ax.text(b.get_x() + b.get_width() / 2, h + 0.012, f"{h:.4f}",
            ha="center", va="bottom", fontsize=13, fontweight="bold")
for b in bars_f:
    h = b.get_height()
    ax.text(b.get_x() + b.get_width() / 2, h + 0.012, f"{h:.4f}",
            ha="center", va="bottom", fontsize=13, fontweight="bold")

# Annotation: LLM-only -> RAG recall improvement
try:
    i_llm = methods.index("LLM-only")
    i_rag = methods.index("LLM + RAG (NoSelf, clean)")
    delta_pp = (rec[i_rag] - rec[i_llm]) * 100.0

    y_start = rec[i_llm]
    y_end = rec[i_rag]
    y_mid = (y_start + y_end) / 2
    annotate_y = y_mid if y_mid > 0.6 else 0.55

    ax.annotate(
        f"+{delta_pp:.2f} pp",
        xy=(i_rag, y_end),
        xytext=(i_rag - 0.25, annotate_y - 0.03),
        arrowprops=dict(arrowstyle="->", color="#D55E00", lw=2.5),
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="black", lw=1.5),
        color="#D55E00",
        fontsize=13,
        fontweight="bold",
        ha="center"
    )
except Exception:
    pass

fig.subplots_adjust(bottom=0.18)
fig.tight_layout()
fig.savefig("results/Figure2_Recall_F1_AllMethods.png", dpi=300)
plt.close(fig)

# -----------------------------
# Figure 3: Inference Latency Comparison (p50/p95/mean)
# -----------------------------
y = np.arange(len(lat_methods))
h = 0.26

fig, ax = plt.subplots(figsize=(18, 8))

b_p50 = ax.barh(y - h, lat_p50, height=h, color=C_P50, edgecolor="black", linewidth=1.5, label="p50 (Median)")
b_p95 = ax.barh(y, lat_p95, height=h, color=C_P95, edgecolor="black", linewidth=1.5, label="p95")
b_mean = ax.barh(y + h, lat_mean, height=h, color=C_MEAN, edgecolor="black", linewidth=1.5, label="Mean")

ax.set_yticks(y)
ax.set_yticklabels(lat_methods, fontsize=15)
ax.invert_yaxis()

# Auto-extend x-axis to accommodate labels
max_latency = max(lat_p95) + 350
ax.set_xlim(0, max_latency)

ax.set_xlabel("Latency (milliseconds)", fontsize=18, fontweight="bold")
ax.set_title("Figure 3: Inference Latency Comparison", pad=18, fontsize=20, fontweight="bold")

# Style axes
for spine in ax.spines.values():
    spine.set_linewidth(2.2)
    spine.set_color("black")
ax.tick_params(width=2.0, length=6)
ax.grid(True, axis="x", linestyle=":", linewidth=1.0, alpha=0.25)

# 图例放右上角，半透明背景
leg = ax.legend(loc="upper right", frameon=True, edgecolor="black", fontsize=12)
leg.get_frame().set_alpha(0.9)


# Value labels
def label_barh(bars, dx=40, fs=13):
    for b in bars:
        wv = b.get_width()
        ax.text(wv + dx, b.get_y() + b.get_height() / 2, f"{int(round(wv))} ms",
                va="center", ha="left", fontsize=fs)


label_barh(b_mean, dx=50, fs=13)
label_barh(b_p95, dx=45, fs=13)
label_barh(b_p50, dx=40, fs=13)

fig.subplots_adjust(left=0.22)
fig.tight_layout()
fig.savefig("results/Figure3_Latency_AllMethods.png", dpi=300)
plt.close(fig)

# -----------------------------
# Figure 4: Multimodal Only (PhishLLM vs Qwen-MM) Fair Comparison
# -----------------------------
# 使用两行标签，紧凑排版
mm_methods_short = ["PhishLLM\n(MM baseline)", "Qwen-MM\n(img+text)"]
mm_rec = [0.6203, 0.6076]
mm_f1 = [0.7656, 0.7559]

x2 = np.arange(len(mm_methods_short))
fig, ax = plt.subplots(figsize=(10, 6))
w_mm = 0.38

bars_mm_rec = ax.bar(x2 - w_mm / 2, mm_rec, width=w_mm, color=C_REC, edgecolor="black", linewidth=1.5, label="Recall")
bars_mm_f1 = ax.bar(x2 + w_mm / 2, mm_f1, width=w_mm, color=C_F1, edgecolor="black", linewidth=1.5, alpha=0.85,
                    label="F1-Score")

ax.set_xticks(x2)
ax.set_xticklabels(mm_methods_short, rotation=0, ha="center", fontsize=14)
ax.set_ylim(0, 1.0)
ax.set_ylabel("Score", fontsize=18, fontweight="bold")
ax.set_title("Figure 4: Multimodal Fair Comparison (Text + Screenshot)", pad=14, fontsize=20, fontweight="bold")

style_axes(ax)
ax.legend(loc="upper left", frameon=True, edgecolor="black", fontsize=12)

# Value labels
for i, v in enumerate(mm_rec):
    ax.text(i - w_mm / 2, v + 0.015, f"{v:.4f}", ha="center", fontsize=13, fontweight="bold")
for i, v in enumerate(mm_f1):
    ax.text(i + w_mm / 2, v + 0.015, f"{v:.4f}", ha="center", fontsize=13, fontweight="bold")

fig.subplots_adjust(bottom=0.14)
fig.tight_layout()
fig.savefig("results/Figure4_Multimodal_Fair_Comparison.png", dpi=300)
plt.close(fig)

print("=" * 60)
print("Four figures generated in results/ directory:")
print("=" * 60)
print(" - Figure1_Performance_AllMethods.png      (Performance comparison)")
print(" - Figure2_Recall_F1_AllMethods.png        (Recall & F1 comparison)")
print(" - Figure3_Latency_AllMethods.png          (Latency comparison)")
print(" - Figure4_Multimodal_Fair_Comparison.png  (Multimodal fair comparison)")
print("=" * 60)
