import matplotlib.pyplot as plt

# 数据（更新为 clean 版本）
methods = ['TF-IDF + LR', 'LLM-only', 'LLM + RAG',
           'PhishLLM', 'Qwen-MM\n(Screenshot)']
recall = [0.6329, 0.4557, 0.5823, 0.6203, 0.3291]
f1 = [0.7407, 0.6154, 0.7302, 0.7656, 0.4952]

# 创建图表
fig, ax = plt.subplots(figsize=(10, 3.5))
ax.axis('off')
ax.axis('tight')

# 准备表格数据（已删除 Modality）
table_data = [[m.replace('\n', ' '), f'{r:.4f}', f'{f:.4f}']
              for m, r, f in zip(methods, recall, f1)]
columns = ['Method', 'Recall', 'F1-Score']  # 只剩3列

# 创建表格
table = ax.table(cellText=table_data, colLabels=columns, loc='center',
                  cellLoc='center', colWidths=[0.5, 0.2, 0.2])

# 样式
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1.2, 1.6)

# 表头样式
for i in range(3):
    table[(0, i)].set_facecolor('#4472C4')
    table[(0, i)].set_text_props(weight='bold', color='white', fontsize=11)

# 本方案高亮（通过方法名查找）
highlight_row = None  # table row index (0=header, 1=first data row)
for i, m in enumerate(methods):
    if m.replace('\n', ' ') == 'LLM + RAG':
        highlight_row = i + 1  # +1 because table row 0 is the header
        break
if highlight_row is not None:
    for col in range(3):
        table[(highlight_row, col)].set_facecolor('#D55E00')
        table[(highlight_row, col)].set_text_props(weight='bold', color='white')

# 交替行底色（跳过高亮行）
for row in range(1, len(methods) + 1):
    if row == highlight_row:
        continue
    if row % 2 == 0:
        for col in range(3):
            table[(row, col)].set_facecolor('#F5F5F5')

plt.title('Table: Performance Comparison of Phishing Detection Methods',
          fontsize=13, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig('results/table_performance.png', dpi=300, bbox_inches='tight')
print("Table generated: results/table_performance.png")