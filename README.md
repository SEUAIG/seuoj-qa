# SEUOJ Agentend (seuoj-qa)

基于 Python 3.10 / FastAPI 的智能问答与备课智能体服务，为 SEUOJ 提供 RAG 问答、知识图谱、代码辅导和 PPT 备课功能。

## 技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn（uvloop） |
| LLM 框架 | Camel-AI（PEV 三阶段智能体） |
| 向量检索 | FAISS（faiss-cpu） |
| 关键词检索 | BM25（rank-bm25）+ jieba 分词 |
| 聊天存储 | SQLite（4 表：session/message/citation/message_citation） |
| 备课 | python-pptx（PPT 解析）、Marp（幻灯片生成） |
| 其他 | LangChain Core、Pydantic、aiohttp、loguru |

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 复制配置文件并填写 API Key
cp config/example.yaml config/base.yaml

# 启动服务（端口 8002）
uvicorn src.api_server:app --host 0.0.0.0 --port 8002
```

聊天 SQLite 默认路径为 `/app/data/chat.db`（目录和文件会自动创建）。
如需自定义路径，可设置环境变量 `CHAT_DB_PATH`。

> 在 Docker 部署中，通过 Nginx `/agent/*` 路由代理访问。

## 配置

配置文件为 `config/base.yaml`（从 `config/example.yaml` 复制）。

**LLM 配置**（`llm.use` 选择 provider）：
- `dmxapi` / `dmxapi_gemini` / `deepseek` / `siliconflow` / `ollama-deepseek-r1` / `deepseek-r1`
- 每个 provider 需配置 `api_key`、`api_base`、`model`、`temperature`

**Embedding 配置**（`embedding.use` 选择 provider）：
- `siliconflow` / `tongyi` / `openai` / `nomic-embed-text`
- 每个 provider 需配置 `api_key`、`api_base`、`model`

## 项目结构

```
src/
├── api_server.py              # FastAPI 应用入口，路由注册
├── agent.py                   # PEV 智能体（Planner-Executor-Verifier 三阶段）
├── controller.py              # 智能推荐控制器
├── database.py                # SQLite 聊天会话持久化
├── embedder.py                # 离线工具：文档切分 + FAISS 索引构建
├── init_db.py                 # 数据库初始化
├── knowledge_graph_qa.py      # 知识图谱问答
├── main.py                    # 旧版 RAG 入口（保留兼容）
├── prompt.py                  # Prompt 模板
├── base_processor.py          # 基础处理器
├── utils.py                   # 工具函数
│
├── retrieval/                 # 检索模块
│   ├── retrieval.py           #   FAISS + BM25 混合检索、前置知识搜索
│   └── qa_retrieval/          #   题库高级检索
│       └── qa_retrieval_advanced.py
│
├── preparation/               # PPT 备课智能体
│   ├── api.py                 #   备课 API 入口
│   ├── config.py              #   备课配置
│   ├── pipeline.py            #   四步流水线（解析→决策→检索→优化）
│   ├── parser/                #   文档解析（PPT/PDF/Markdown）
│   │   ├── ppt_parser.py
│   │   ├── document_splitter.py
│   │   └── mineru_parser.py
│   ├── logic/                 #   业务逻辑
│   │   ├── lesson_planner.py  #     课程规划
│   │   ├── content_generator.py #   内容生成
│   │   ├── page_optimizer.py  #     页面优化
│   │   └── style_adapter.py   #     风格适配
│   ├── marp/                  #   Marp 幻灯片生成
│   │   ├── marp_generator.py
│   │   └── ppt_converter.py
│   └── retrieval/             #   备课专用检索
│       ├── keyword_extractor.py
│       ├── policy_fetcher.py
│       └── reranker.py
│
├── program/                   # 代码相关
│   ├── code_generator.py      #   代码生成（暂停用）
│   ├── code_runner.py         #   代码运行（调用外部服务）
│   └── problem_bank.py        #   题库数据
│
└── recommendation/            # 推荐模块
```

## API 接口

所有接口挂载在 `/agent` 前缀下。

### RAG / 搜索

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/agent/` | 健康检查 |
| POST | `/agent/faiss_search` | FAISS 向量搜索 |
| POST | `/agent/bm25_search` | BM25 关键词搜索 |
| POST | `/agent/rag_answer` | RAG 回答（带引用） |
| POST | `/agent/pre_knowledge_search` | 前置知识搜索 |
| POST | `/agent/qa_search` | 题库高级检索 |
| POST | `/agent/smart_answer` | 智能回答（自动推荐前置知识+相关题目） |

### 代码 / 题库

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/agent/code_generation` | 代码生成 |
| GET | `/agent/problem/list` | 题目列表 |
| GET | `/agent/problem/detail/{id}` | 题目详情 |
| POST | `/agent/code_runner` | 代码运行 |

### PPT 备课（四步流水线）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/agent/ppt_optimizer/ppt_parser` | Step 1：解析文档 |
| POST | `/agent/ppt_optimizer/decide` | Step 2：决策集成点 |
| POST | `/agent/ppt_optimizer/retrieve` | Step 3：检索内容 |
| POST | `/agent/ppt_optimizer/optimize` | Step 4：优化生成 |
| POST | `/agent/ppt_optimizer/run` | 一键全流程 |

### 聊天会话（SQLite 持久化）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/agent/api/rag/sessions` | 创建会话 |
| GET | `/agent/api/rag/sessions` | 会话列表 |
| GET | `/agent/api/rag/sessions/{id}` | 会话详情 |
| PUT | `/agent/api/rag/sessions/{id}` | 更新会话标题 |
| DELETE | `/agent/api/rag/sessions/{id}` | 删除会话 |
| GET | `/agent/api/rag/sessions/{id}/messages` | 获取消息 |
| POST | `/agent/api/rag/messages` | 创建消息（支持引用） |
| POST | `/agent/api/rag/messages/rag_answer` | RAG 回答并持久化 |

## 数据目录

在 Docker 部署中，以下目录通过 volume 挂载：

| 路径 | 内容 |
|------|------|
| `data/faiss/` | FAISS 向量索引文件 |
| `data/knowledge_graph/` | 知识图谱 JSON 数据 |
| `data/qa_bank/` | 题库 JSON 数据 |
| `data/agent/` | SQLite 聊天数据库 |
