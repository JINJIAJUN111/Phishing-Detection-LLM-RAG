#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键生成所有图表（Figure 1-5 + table_performance.png）
"""
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
PY = sys.executable

scripts = [
    ("Figure 1-4", BASE / "make_plots_final.py"),
    ("Figure 5", BASE / "make_figure5_textonly.py"),
    ("Table", BASE.parent / "draw_table.py"),
]

print("=" * 60)
print("Generate All Figures")
print("=" * 60)
print()

for name, script in scripts:
    print(f"[{name}] Running {script.name}...")
    try:
        subprocess.run([PY, str(script)], check=True, capture_output=True, text=True)
        print(f"  [OK] {name} generated successfully")
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] {name} generation failed")
        print(f"    Error: {e.stderr}")
        sys.exit(1)
    print()

print("=" * 60)
print("All figures generated successfully!")
print("=" * 60)
print()
print("Generated files:")
print("  - results/Figure1_Performance_AllMethods.png")
print("  - results/Figure2_Recall_F1_AllMethods.png")
print("  - results/Figure3_Latency_AllMethods.png")
print("  - results/Figure4_Multimodal_Fair_Comparison.png")
print("  - results/Figure5_TextOnly_Comparison.png")
print("  - results/table_performance.png")
print()
