import matplotlib.pyplot as plt

# 数据（更新为 clean 版本）
methods = ['TF-IDF + LR', 'LLM-only', 'PhishLLM\n(MM baseline)',
           'Qwen-MM\n(img+text)', 'LLM + RAG\n(NoSelf, clean)']
recall = [0.7848, 0.4557, 0.6203, 0.6076, 0.5823]
f1 = [0.8611, 0.6154, 0.7656, 0.7559, 0.7302]

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

# 本方案高亮（最后一行）
for i in range(3):
    table[(4, i)].set_facecolor('#D55E00')
    table[(4, i)].set_text_props(weight='bold', color='white')

# 交替行底色
for i in range(1, 5):
    if i % 2 == 1 and i != 4:
        for j in range(3):
            table[(i, j)].set_facecolor('#F5F5F5')

plt.title('Table: Performance Comparison of Phishing Detection Methods',
          fontsize=13, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig('results/table_performance.png', dpi=300, bbox_inches='tight')
print("Table generated: results/table_performance.png")