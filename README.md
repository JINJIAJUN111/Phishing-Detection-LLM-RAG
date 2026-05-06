# 钓鱼网站检测课程设计（LLM / RAG / 多模态对比复现包）

> **课程设计交付说明**：本项目实现并评估了多种钓鱼网站检测方法，包括传统机器学习、纯 LLM、检索增强生成（RAG），以及多模态方法。本仓库同时提供靶场环境（Docker）与离线评测脚本，便于复现实验结果与生成报告图表。

---

## 1. 项目概述

### 1.1 主要功能
- **钓鱼网站检测**：对给定 URL 的页面证据进行分类，输出是否为钓鱼（phish / benign）及置信度与解释。
- **多方法对比评测**：统一输出为 `.jsonl` 预测文件，并用同一套评估脚本计算 `Accuracy / Precision / Recall / F1`。
- **日志统计**：统计模型推理延迟（mean、p50、p95），用于报告“性能-成本”分析。
- **靶场搭建**：提供 `lab-docker/` 目录用于本地启动钓鱼页面（用于攻击/防御过程演示与截图）。

### 1.2 方法列表（5种）
1. **TF-IDF + Logistic Regression**（传统机器学习基线）
2. **LLM-only**（纯文本 LLM 基线）
3. **PhishLLM (MM baseline)**（参考 USENIX Security 2024 的多模态基线）
4. **Qwen-MM (img+text)**（多模态基线：文本 + 页面截图）
5. **LLM + RAG (NoSelf, clean)**（本文核心方案：纯文本 + 检索增强生成）

> 注：多模态方法依赖网页截图；本实验截图覆盖率为 `424/434 = 97.7%`，无截图样本会自动退化为文本推理。

---

## 2. 目录结构（提交版）

```
.
├── llm/                       # 推理与预测生成脚本（LLM/RAG/MM）
├── eval/                      # 评估脚本（evaluate.py / summary_table.py）
├── tools/                     # 画图、检查等辅助脚本
├── data/
│   ├── evidence/              # 证据文件（CSV）
│   └── predictions/           # 预测结果（5个jsonl）
├── lab-docker/                # 靶场环境（Docker + Nginx + HTML）
├── results/                   # 输出表格与图表（Figure1-4）
│   └── screenshots/           # 靶场页面截图（用于报告）
├── report/                    # 课程设计报告（docx/pdf）
├── demo.ps1                   # 验收演示脚本
├── requirements.txt           # Python 依赖
└── README.md                  # 使用说明（本文档）
```

---

## 3. 环境要求

- **操作系统**：Windows 10/11（推荐），Linux/macOS 亦可（需自行调整脚本）
- **Python**：`>= 3.10`（推荐 3.10/3.11）
- **网络**：如需在线调用 LLM API（DashScope），需可访问外网
- **可选**：Docker Desktop（用于运行靶场 `lab-docker/`）

---

## 4. 安装与初始化

### 4.1 创建虚拟环境（推荐）
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

### 4.2 配置 API Key（如需重新推理）
本项目的多模态/LLM 推理默认使用 DashScope 兼容 OpenAI 接口模式。请使用**环境变量**配置密钥（不要写入代码与提交包）。

PowerShell：
```powershell
$env:DASHSCOPE_API_KEY = "YOUR_KEY_HERE"
```

如需永久生效：
```powershell
setx DASHSCOPE_API_KEY "YOUR_KEY_HERE"
```

> 若仅需复现评测与图表（使用已提供的 `data/predictions/*.jsonl`），**不需要配置 API Key**。

---

## 5. 快速复现（推荐：无需调用模型）

本提交包已包含最终预测文件与结果图表。你可以直接重新生成对比表与图表以验证一致性。

### 5.1 一键运行（Windows）
PowerShell：
```powershell
.\demo.ps1
```

CMD：
```bat
powershell -File demo.ps1
```

输出：
- `results/summary_table.txt`
- `results/Figure1_*.png` ~ `results/Figure4_*.png`

---

## 6. 评测脚本说明

### 6.1 单个预测文件评测
```powershell
python eval/evaluate.py --preds data/predictions/mix_rag_noself_clean_full.jsonl
```

脚本输出包含：
- n、bad_json
- acc / prec / rec / f1
- latency mean / p50 / p95（如果预测文件含 `_latency_ms` 字段）

### 6.2 生成总体对比表 + 同模态子表
```powershell
python eval/summary_table.py
```

输出包含三部分：
1. **总体对比表（5种方法）**
2. **同模态对比（多模态：PhishLLM / Qwen-MM）**
3. **同模态对比（纯文本：TF-IDF / LLM-only / RAG）**

---

## 7. 生成论文图表（Figure 1–4）

```powershell
python tools/make_plots_final.py
```

生成：
- `results/Figure1_Performance_AllMethods.png`
- `results/Figure2_Recall_F1_AllMethods.png`
- `results/Figure3_Latency_AllMethods.png`
- `results/Figure4_Multimodal_Fair_Comparison.png`

---

## 8. 靶场环境（lab-docker）运行方式

> 用途：在本地启动钓鱼页面（如仿登录页）用于展示攻击过程、采集证据截图、记录访问日志等。

```powershell
# 启动靶场容器
docker run --name phishing-lab --rm -d -p 8080:8080 `
  -v "${PWD}\lab-docker\site:/usr/share/nginx/html:ro" `
  -v "${PWD}\lab-docker\logs:/var/log/nginx" `
  nginx:alpine

# 查看容器状态
docker ps

# 停止容器
docker stop phishing-lab
```

然后在浏览器访问 `http://localhost:8080`。

### 8.1 靶场页面清单

启动靶场后，可访问以下页面：

| 页面 | URL | 类型 | 说明 |
|------|-----|------|------|
| 主页 | `http://localhost:8080/` | 导航 | 靶场入口 |
| Outlook钓鱼 | `http://localhost:8080/phish/outlook/` | 传统钓鱼 | 仿Outlook登录页 |
| Bank钓鱼 | `http://localhost:8080/phish/bank/` | 传统钓鱼 | 仿银行登录页 |
| 良性新闻 | `http://localhost:8080/benign/news/` | 正常 | 真实新闻内容 |
| **二维码钓鱼** | `http://localhost:8080/phish/outlook/qr_login.html` | 多模态扩展 | 诱导扫码验证 |
| **iframe嵌套钓鱼** | `http://localhost:8080/phish/iframe_phish.html` | 多模态扩展 | 隐藏地址栏欺骗 |

> 二维码和iframe页面用于验证多模态方法对新型钓鱼攻击的检测能力。

### 8.2 靶场页面截图

多模态扩展页面截图保存在 `results/screenshots/` 目录下：
- `qr_page.png`：二维码钓鱼页面
- `iframe_page.png`：iframe嵌套钓鱼页面

---

## 9. 输出文件格式说明（JSONL）

每一行是一条样本预测结果（JSON 对象），核心字段通常包括：
- `url`：样本 URL
- `label`：真实标签（0=benign, 1=phish）
- `llm_out.is_phish`：模型预测（0/1）
- `llm_out.confidence`：置信度（0~1）
- `llm_out.reasons`：解释（数组）
- `llm_out._latency_ms`：推理耗时（毫秒）

---

## 10. 复现实验的建议流程（从零开始跑全流程，可选）

如需重新生成预测（会消耗 API 调用）：
1. 证据准备：`data/evidence/combined_evidence_mm.csv`
2. 依次运行各方法推理脚本，生成 `data/predictions/*.jsonl`
3. 运行：
   - `python eval/summary_table.py`
   - `python tools/make_plots_final.py`

> 注意：多模态方法在极少数样本上可能触发内容安全拦截（如 `DataInspectionFailed`）。本项目实现了“去图/截断文本”的降级重试策略，确保最终输出完整覆盖所有样本。

---

## 11. 常见问题（FAQ）

### Q1：没有 API Key 能不能跑？
能。评测与画图只依赖 `data/predictions/*.jsonl`，提交包已包含这些文件。

### Q2：为什么多模态方法 Precision=1.0 但 Recall 偏低？
这说明模型在当前提示词/阈值设定下偏保守：几乎不误报（FP≈0），但会漏报部分钓鱼样本（FN较多）。报告中需结合混淆矩阵或召回率进行分析。

### Q3：截图数据太大怎么办？
提交包默认提供证据 CSV 与预测结果，若完整截图体积过大可不打包；报告中说明截图覆盖率及无图退化策略即可。

### Q4：二维码和iframe页面如何访问？
确保 Docker 容器运行后，在浏览器访问：
- QR页面：`http://localhost:8080/phish/outlook/qr_login.html`
- iframe页面：`http://localhost:8080/phish/iframe_phish.html`

### Q5：PhishLLM 是什么模态？
PhishLLM 原本是纯文本模型（参考 USENIX Security 2024），本实验将其扩展为多模态基线（MM baseline），使用文本+截图输入。

---

## 12. 核心实验结果

| 方法 | Recall | F1-Score |
|------|--------|----------|
| TF-IDF + LR | 0.7848 | 0.8611 |
| LLM-only | 0.4557 | 0.6154 |
| PhishLLM (MM baseline) | 0.6203 | 0.7656 |
| Qwen-MM (img+text) | 0.6076 | 0.7559 |
| **LLM + RAG (NoSelf, clean)** | **0.5823** | **0.7302** |

注：clean版本移除了自引用样本，F1从0.8828降至0.7302，但实验更加严格。LLM+RAG相比LLM-only，召回率仍提升12.66个百分点。

---

## 13. 许可与声明
本项目仅用于课程设计与教学实验目的。样本数据与页面仅用于安全研究与检测实验，不用于任何非法用途。
