# Moneki Analytics · 门店经营数据看板（可信 AI 问答）

> 一个基于**真实结构化数据查询**的可信 AI 经营分析看板：LLM 只负责理解问题和组织语言，所有经营数字都经**统一 Analytics Service** 真实查询获得，前端带「数据依据」展示，并用自动化测试证明 **AI 回答的数字 == 数据库查出的数字**。

## 功能概览

- **第一关 · 数据看板**：日期区间筛选 + KPI（净营业额 / 订单数 / 客单价）+ 营业额趋势 + Top 10 商品 + 门店品类营业额
- **第二关 · AI 数据问答**：自然语言提问 → 受控 Tool Calling → 真实 SQL → 带证据的回答（拒绝编造、查无兜底、模糊匹配纠错）
- **第三关 · 让它可信**：对话上下文（「那五月呢？」）、AI 数字自动化测试、自然语言直接出图、AI 主动经营洞察（异常预警 / 周末效应 / 环比 / 会员储值）

## 架构

```
data/*.csv
   │  scripts/init_db.py（清洗 + 去重 + 归一化 + 脏外键处理）
   │  产出 data/moneki.db 与 data/data_quality.json
   ▼
SQLite  ── stores / products / sales
   ▲
   │  services/analytics.py  ←── 统一统计口径（唯一数字权威）
   ├──────────────┬──────────────────┐
   ▼              ▼                  ▼
Dashboard API   AI Tools（真实 SQL）  Insights（规则计算）
/api/dashboard   /api/chat           /api/insights
   │              │
   │              └─ LLM(DeepSeek) 只负责：选工具 + 传参 + 组织回答
   ▼
Frontend（Vue3 + ECharts）：看板图表 + AI 对话框（带 Evidence 数据依据）
```

关键点：**Dashboard API 与 AI Tool 复用同一套 `services/analytics.py`**，保证「第一关接口数字」与「AI 回答数字」严格一致——这正是题目「拿第一关数字对照 AI 回答」的直接解法。

## 技术选型 & 理由

| 层 | 选型 | 理由 |
|---|---|---|
| 后端 | FastAPI + SQLAlchemy + SQLite | 数据约 1.2 万行，SQLite 零部署、clone 即跑；FastAPI 自带 OpenAPI 文档、类型友好 |
| 清洗 | Python + 标准库（csv / re） | 数据量小，标准库足够，减少依赖；清洗规则透明可审计 |
| AI | DeepSeek（OpenAI 兼容 function calling） | 便宜、支持工具调用；模型名走环境变量，可替换 |
| 前端 | Vue3 + TS + Vite + Element Plus + ECharts | 轻量、开发快；ECharts 做趋势/排行图 |
| 测试 | pytest + FastAPI TestClient | 证明「AI 数字 == 数据库数字」 |

## 快速开始（3 步）

前置：Python ≥ 3.12、Node ≥ 18。

```bash
# 1. 配置 DeepSeek API Key
cp backend/.env.example backend/.env      # 编辑 backend/.env，填入 DEEPSEEK_API_KEY

# 2. 初始化数据（清洗 + 建库，产出 moneki.db 与 data_quality.json）
cd backend && python scripts/init_db.py

# 3. 启动前后端
# 终端 A（后端）：
cd backend && uvicorn app.main:app --port 8000
# 终端 B（前端）：
cd frontend && npm install && npm run dev    # 打开 http://localhost:5173
```

> 一键启动（可选）：Windows 下运行 `./start.ps1`，自动创建 venv、安装依赖、建库、起前后端。

> Docker：`docker compose up --build`（见下文）。

## 统计口径（重要，README 必需说明）

| 指标 | 口径 |
|---|---|
| 营业额 | `SUM(amount)`，负数（退款）自然扣减，即**净营业额** |
| 订单数 | `COUNT(DISTINCT order_id)`（一笔订单多行商品，必须去重） |
| 客单价 | `净营业额 / 有效订单数`（有效订单数 = 至少有一条有效 amount 的 order_id，避免空金额订单拉低客单价） |

这些口径封装在 `services/analytics.py` 的 `_summary_core`，Dashboard 与 AI Tool 全复用。

## 数据清洗（data_quality.json 记录全过程）

原始 12131 行销售流水，含真实脏数据，处理如下：

| 问题 | 数量 | 处理 |
|---|---|---|
| 完全重复行 | 76 | 删除 |
| 日期三种格式（`YYYY-MM-DD` / `YYYY/MM/DD` / `DD-MM-YYYY`） | 150 | 统一为 `YYYY-MM-DD` |
| amount 带货币符号（¥/￥/元） | 40 | 剥离 |
| amount 为空 | 120 | 置 NULL，不参与金额统计 |
| amount 为负（退款） | 49 | 保留，SUM 自然扣减 |
| qty 为负（退货） | 14 | 保留，质量报告注明 |
| `s01` → `S01` 大小写 | 9 | 归一化 |
| 脏外键 `S99` / `P99` | 7 / 30 | 保留事实表，维度统计用 INNER JOIN 自然剔除 |

> 两类指标口径：不依赖维表的指标（总营业额/每日/订单数）直接查 `sales`；依赖维表的（Top 商品/品类/门店）用 INNER JOIN，自然排除脏外键。清洗后 12055 行入库。

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/dashboard/summary` | KPI：净营业额/订单数/客单价 |
| GET | `/api/dashboard/daily` | 每日趋势 |
| GET | `/api/dashboard/top-products` | Top 商品（JOIN products） |
| GET | `/api/dashboard/store-category` | 门店品类营业额（JOIN stores） |
| GET | `/api/dashboard/store-rank` | 门店营业额排名 |
| GET | `/api/dashboard/payment` | 支付方式分布 |
| GET | `/api/insights` | 经营洞察（规则计算） |
| POST | `/api/chat` | AI 问答，返回 `{answer, data, evidence, tool_used}` |

## 测试

```bash
cd backend && pytest
```

- `tests/test_analytics.py`：第一关接口数字正确性
- `tests/test_ai_answers.py`：**证明 AI 回答数字 == 数据库数字**（工具链路真实 SQL + 真实 LLM 测试，无 key 时自动跳过真实 LLM 用例）
- `tests/test_insights.py`：洞察由真实数据计算

## 目录结构

```
backend/
  app/
    api/          # dashboard / chat / insights 路由
    ai/           # agent（LLM 循环）+ tools（受控工具）+ prompts
    services/     # analytics（统一口径）+ insights（经营洞察）
    models.py schemas.py config.py database.py main.py
  scripts/init_db.py   # 清洗 + 建库
  tests/
frontend/
  src/views/Dashboard.vue
  src/components/       # MetricCard / SalesTrend / TopProducts / StoreCategory / AIInsights / AIChat / MiniChart
data/                   # 原始 CSV + 生成的 moneki.db + data_quality.json
```
