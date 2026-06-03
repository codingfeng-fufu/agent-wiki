# LLM Wiki 项目学习路线

## 前言

LLM Wiki 是一个本地、Agent 驱动的 Markdown Wiki 工具。它的价值不止于功能本身，更在于围绕 **"Agent 如何维护长期知识"** 这个核心问题的设计思路。

学习这个项目可以同时掌握：Agent 工作流设计、MCP 协议实践、知识管理架构、搜索系统实现、以及 Python CLI 工具工程化。

---

## 阶段一：理念与架构（理解"为什么"）

**目标**：理解这个项目解决了什么问题，以及它的核心架构边界。

### 阅读清单

| 文档 | 位置 | 说明 |
|------|------|------|
| 项目起源 | `docs/origin.md` | Karpathy 的原始想法，这个实现加入了什么 |
| 核心哲学 | `docs/philosophy.md` | Agent 不该每次都重新检索，而应该维护知识 |
| 中文哲学 | `docs/philosophy.zh-CN.md` | 中文版，更精炼地复述了核心思想 |
| 架构文档 | `docs/architecture.md` | **[关键] 三层边界模型** |
| 系统架构 | `system/architecture.md` | 系统级架构描述 |
| 目标状态 | `system/target-state.md` | 完整工作流的理想形态 |

### 看完后要能回答

1. 为什么不直接用 RAG 而是维护一个 wiki？
2. `raw/` 和 `wiki/` 的边界是什么？为什么 `raw/` 不可变？
3. Plan/Apply 的安全模型如何防止 Agent 越权？

### 核心看点

- **不可变证据层 vs 可维护知识层的分离**：整个项目最核心的设计决策。`raw/` 是只读的，Agent 永远不能改写原始材料；`wiki/` 是 Agent 维护的知识层，可以增删改查。
- **Plan → Dry-run → Apply 的安全写入模型**：不靠 Agent 自律，靠工具约束。任何写操作必须先产生计划，再 dry-run 预览，确认无误后才真正执行。
- **`strategy` 字段**：搜索返回结果中的字段，搜索引擎自己告诉 Agent 是否需要深度搜索，而不是让 Agent 自己猜。

---

## 阶段二：体验完整流程（端到端使用）

**目标**：亲手跑一遍从 raw 到 wiki 的全流程，感受实际操作方法。

### 阅读清单

| 文档 | 位置 |
|------|------|
| 快速开始 | `docs/quickstart.md` |
| Demo 流程 | `docs/demo.md` |
| Agent 循环示例 | `examples/agent-loop.md` |

### 动手步骤

```bash
# 1. 安装依赖
uv sync --extra dev

# 2. 初始化项目
.venv/bin/llmw init

# 3. 运行诊断，确认环境就绪
.venv/bin/llmw doctor --json

# 4. 查看当前项目状态（Agent 进入项目的第一件事就是这个）
.venv/bin/llmw context --json

# 5. 体验搜索
.venv/bin/llmw search "prompt injection" --limit 5 --json

# 6. 查看维护建议
.venv/bin/llmw maintain --no-audit --no-save-plan --json

# 7. 生成一个维护计划并 dry-run 预览
.venv/bin/llmw plan "rebuild index" --json --save --preview
.venv/bin/llmw apply .llmw/plans/<plan_id>.json --dry-run --json

# 8. 跑健康检查
.venv/bin/llmw health check --json
```

### 看完后要能回答

1. `context --json` 的输出包含哪些信息？
2. `search` 返回的 `strategy` 字段是什么意思？
3. `plan` + `apply --dry-run` 是怎么配合的？
4. `health check` 检查哪些东西？

### 核心看点

- `context --json` 的输出结构：这就是 Agent 进入项目时看到的一整套信息——wiki 页数、源数量、健康问题、推荐命令。
- `search --json` 的 `strategy` 字段：返回 `direct` 或 `needs_deep`，让上游决定是否值得花时间深度搜索。
- `plan` + `apply --dry-run`：先看计划再执行，安全机制的核心。
- `health check` 检测的内容：死链、孤儿页面、frontmatter 缺失、索引过期等。

---

## 阶段三：深入 wiki 内容与质量体系（理解"好 wiki"的样子）

**目标**：理解 LLM 生成的 wiki 页面长什么样，以及质量保障机制怎么运作。

### 阅读清单

| 内容 | 位置 | 说明 |
|------|------|------|
| 自动生成索引 | `wiki/index.md` | 48 个页面的索引 |
| 维护日志 | `wiki/log.md` | 每次 ingest 的记录 |
| 源页面 | `wiki/sources/` | 8 个源页面模板 |
| 概念页面 | `wiki/concepts/` | 读 5-8 个，理解原子性和链接密度 |
| 分析页面 | `wiki/analyses/agent-development-knowledge-map.md` | 跨页面综合 |
| Agent 协议 | `AGENTS.md` | Agent 应该遵守的操作规则 |

### 看完后要能回答

1. Frontmatter 有哪些字段？各有什么含义？
2. Wiki 页面之间是如何通过 `[[links]]` 互相连接的？
3. 一个概念页面如何追溯到它依赖的原始源文件？
4. 为什么 Input Guardrails 和 Output Guardrails 要分两个页面？

### 核心看点

- **Frontmatter 规范**：每个页面以 YAML 开头，`title`、`type`（source/concept/analysis）、`status`（当前全部是 draft）、`sources`（追溯到原始文件）、`tags`。
- **Wiki 链接密度**：几乎所有名词都有 `[[link]]`，形成可导航的知识图谱。例如 Agent Guardrails → Input Guardrails → Prompt Injection → Tool Safety → Agent Guardrails，形成一个闭环。
- **源追溯性**：每个概念页面的 frontmatter 里都有 `sources` 字段，指向 `raw/processed/` 中的具体文件。
- **页面原子性**：一个概念一个页面，不合并。Durable Agent Execution 和 Idempotent Tool Calls 是分开的。
- **所有页面都是 draft**：这是真实项目中的真实状态，展示了一个正在建设中的知识库，而不是造假成"已审核"。

---

## 阶段四：阅读核心源码（理解"怎么做到"）

**目标**：深入阅读核心模块的实现代码。建议按以下顺序阅读。

---

### 4.1 搜索系统（约 1 天）

**文件**：

| 文件 | 说明 |
|------|------|
| `src/llmw/search/providers.py` | **[亮点]** 搜索提供者：RgSearchProvider、QmdSearchProvider、SearchService |
| `src/llmw/search/benchmark.py` | 102 查询基准测试 |
| `src/llmw/search/daemon.py` | Unix socket 搜索守护进程 |

**要看什么**：

- `RgSearchProvider`：用 `ripgrep` 做快速文本搜索，Python BM25 作为回退。BM25 实现包含领域权重（标题匹配加分）、短语加分（引号检测）、归一化、680 词停用词表。
- `SearchService`：回退链设计——主提供者失败时自动切换到备用提供者，确保搜索永远可用。
- `QmdSearchProvider`：深度搜索，支持 CLI 和 Python SDK 两种模式。
- 基准测试：102 个查询分布在 7 个类别（concept-title、concept-paraphrase、source-title、source-paraphrase、analysis-title、analysis-paraphrase、cross-cutting），用 Precision/Recall/F1/MRR/HitRate 评估。
- 搜索守护进程：Unix socket 通信，保持 qmd 后端 warm，避免冷启动。

---

### 4.2 MCP 服务器（约 1 天）

**文件**：

| 文件 | 说明 |
|------|------|
| `src/llmw/mcp/server.py` | **[亮点]** 完整的 MCP stdio 服务器实现 |

**要看什么**：

- **9 个 MCP 工具**：`llmw_context`、`llmw_next`、`llmw_search`、`llmw_query`、`llmw_maintain`、`llmw_benchmark_search`、`llmw_health_check`、`llmw_plan`、`llmw_apply`。
- **7+ 资源 URI**：静态资源（`llmw://context`、`llmw://project/agents`、`llmw://wiki/index` 等）+ 动态模板 `llmw://wiki/page/{path}`。
- **5 个 Prompt**：`llmw_agent_router`、`llmw_ingest`、`llmw_query`、`llmw_health_audit`、`llmw_maintain_runbook`。
- **协议自动检测**：同时支持 JSONL 和 Content-Length 两种帧协议。
- **深度搜索三级回退**：尝试重用已有 daemon → 子进程执行 deep search（35s 超时）→ 快速搜索回退。

---

### 4.3 LLM 集成（约半天）

**文件**：

| 文件 | 说明 |
|------|------|
| `src/llmw/llm/client.py` | OpenAI 兼容 HTTP 客户端（httpx + 重试） |
| `src/llmw/llm/ingest.py` | LLM 生成 wiki 页面，含路径安全检查 |
| `src/llmw/llm/health.py` | 语义审计（矛盾检测、过时声明、孤儿页面） |
| `src/llmw/llm/query.py` | 从 wiki 证据回答问题，支持 `--save` 持久化 |
| `src/llmw/llm/config.py` | ProviderConfig + ProviderRegistry |

**要看什么**：

- `OpenAICompatibleClient`：httpx 实现的 chat completions 客户端，带指数退避重试。
- `run_ingest()`：发送源材料到 LLM → 解析返回 → 验证路径安全（拒绝路径穿越、异常路径）→ 写入文件 → 更新注册表。
- `run_health_audit()`：把 wiki 页面发给 LLM 做语义检查——找矛盾、过时声明、缺失交叉链接、孤儿页面、源覆盖缺口。
- `run_query()`：搜索 → 构建上下文 → LLM 回答 → 可选 `--save` 把答案写入 `wiki/outputs/`。
- Provider 配置中的 `usage` 模式：同一 API 对不同用途（ingest/query/health/agent）使用不同 temperature、max_tokens 和 system prompt。

---

### 4.4 Agent 与安全写入（约半天）

**文件**：

| 文件 | 说明 |
|------|------|
| `src/llmw/agent/tools.py` | **[亮点]** ToolPlan/ToolStep 模型，apply_plan 实现 |
| `src/llmw/agent/context.py` | 构建项目上下文 |
| `src/llmw/agent/maintain.py` | 维护规划，可选 LLM 语义审计 |
| `src/llmw/agent/session.py` | 交互式 REPL，自然语言路由 |

**要看什么**：

- `ToolPlan`/`ToolStep` 模型：每个步骤有 action、目标路径、风险等级（low/medium/high）、参数。支持 9 种操作：`source_add`、`ingest_record`、`query`、`query_save`、`health_audit_save`、`index_rebuild`、`wiki_patch`、`audit_issue_plan`。
- `apply_plan()`：支持 `dry_run` 模式。真实执行时每个步骤做路径安全验证。
- `wiki_patch` 的安全校验：拒绝绝对路径、拒绝 `../` 路径穿越、只允许写入 `wiki/` 和 `system/` 目录。`raw/` 永远不是合法目标。
- `build_context()`：收集 wiki 页面数、源数、健康状态、推荐命令——这是 Agent 的"眼睛"。

---

### 4.5 质量门禁（约半天）

**文件**：

| 文件 | 说明 |
|------|------|
| `src/llmw/health/checks.py` | 结构健康检查 |
| `src/llmw/doctor.py` | 综合性项目诊断 |
| `src/llmw/release.py` | 发布检查门禁 |
| `src/llmw/package.py` | 包构建 + 审计 |

**要看什么**：

- `HealthChecker`：YAML frontmatter 有效性、缺失必要元数据、未解析的 wiki 链接、孤儿页面、缺失源文件、未注册的 inbox 文件、索引过期、日志格式错误。
- `run_doctor()`：10+ 项检查——项目结构、配置、context 构建、搜索提供者、Codex 集成、MCP 探测。
- `run_release_check()`：组合 doctor + health check + pytest + 搜索基准测试 + sdist 审计作为发布门禁。
- `build_package()`：通过 release check 后，用 uv 构建 wheel 和 sdist，然后审计包内容——禁止包含 `.llmw/`、API key、私有数据。

---

### 4.6 其他值得看的模块

| 文件 | 说明 |
|------|------|
| `src/llmw/sources/registry.py` | SourceRegistry 的 CRUD：load/save/find/add/update |
| `src/llmw/sources/extract.py` | 文本提取：.md/.txt 直接读，.pdf 用 pypdf |
| `src/llmw/wiki/links.py` | Obsidian [[link]] 分析：出链、入链、坏链、双向计数 |
| `src/llmw/wiki/pages.py` | WikiPage 加载、页面类型推断 |
| `src/llmw/wiki/index.py` | 索引构建：build_index_content、rebuild_index、index_is_current |
| `src/llmw/wiki/log.py` | 日志追加和格式验证 |
| `src/llmw/core/markdown.py` | YAML frontmatter 解析、标题提取、摘要提取、链接提取 |
| `src/llmw/core/models.py` | 所有 Pydantic 数据模型定义 |
| `src/llmw/core/paths.py` | WikiPaths：所有标准路径的集中管理 |
| `src/llmw/core/config.py` | 项目配置的加载和写入 |
| `src/llmw/core/fs.py` | 文件系统工具：utc_now_iso、sha256_file、slugify |

---

## 阶段五：理解工程化实践（"怎么做出来"）

**目标**：学习这个项目在工程化方面的亮点，理解一个可发布的 Python 工具应该怎么组织。

### 看点清单

#### 1. pyproject.toml — 构建配置

`hatchling` 构建系统，关键策略在 `[tool.hatch.build.targets.wheel]` 的 `only-include` 和 `exclude`：

```toml
exclude = [".llmw", "raw/.*", "wiki/.*"]
```

防止本地运行时状态和私密知识库数据泄漏到发布包中。

#### 2. scripts/release_check.sh — 发布前检验

一个 shell 脚本，整合了多项检查：
- pytest 运行测试
- `llmw health check` 结构验证
- CLI 冒烟测试（24 条命令）
- 搜索 daemon 冒烟测试
- 搜索基准测试（可配置门限）
- 可选 LLM 和深度搜索测试

#### 3. `.llmw/` 目录设计

把所有运行时状态放在一个目录下：

```
.llmw/
├── config.json      # 项目配置
├── sources.json     # 源注册表
├── .env            # API key（已 gitignore）
├── plans/          # 生成的计划文件
├── sessions/       # Agent 会话记录
├── caches/         # 缓存
└── qmd/            # qmd 深度搜索数据
```

好处：一个目录就是全部状态，可以整体 gitignore，发布时整体排除。

#### 4. Provider 配置的 `usage` 模式

`system/providers/qwen-plus.json` 为同一个 API 定义多套配置：

```json
{
  "usage": {
    "ingest": { "temperature": 0.2, "system_prompt_file": "system/prompts/ingest.md" },
    "query": { "temperature": 0.0, "system_prompt_file": "system/prompts/query.md" },
    "health": { "temperature": 0.0, "system_prompt_file": "system/prompts/health-audit.md" },
    "agent": { "temperature": 0.1, "system_prompt_file": "system/prompts/agent-router.md" }
  }
}
```

不同用途需要不同的创造性和 system prompt。

#### 5. JSON 契约

所有命令支持 `--json`，返回一致的格式：

```json
// 成功
{"ok": true, ...payload...}
// 失败
{"ok": false, "error": {"code": "...", "message": "..."}}
```

这样 Agent 和 CLI 用户都能以同样的方式解析输出。

#### 6. CI/CD

`.github/workflows/ci.yml` 包含：
- `pytest` 测试
- `llmw health check` 结构验证
- `llmw benchmark search` 检索质量基准
- sdist 审计（防止发布包泄漏私有数据）

`.github/workflows/release.yml`：构建并上传本地发布 artifacts；PyPI 发布是后续预留步骤。

#### 7. 文档结构设计

```
docs/            # 深度文档（理念、架构、用法、性能）
examples/        # 示例（agent-loop 示例）
plugins/         # MCP 插件配置模板
system/          # 系统定义（架构、目标状态、prompt 模板）
```

文档分层：README 能快速理解项目是什么 → docs/ 给需要深度了解的人 → examples/ 给想实操的人。

---

## 项目亮点速查表

| 亮点 | 代码位置 | 为什么值得学 |
|------|---------|------------|
| 三层边界模型 | `docs/architecture.md` | 知识层分离的核心洞察 |
| BM25 搜索 + 回退链 | `src/llmw/search/providers.py` | 工业级搜索实现，含短语检测、领域权重、停用词 |
| MCP 完整实现 | `src/llmw/mcp/server.py` | 构建 MCP 服务器的完整参考（工具+资源+prompt） |
| Plan/Apply 安全写入 | `src/llmw/agent/tools.py` | 不靠 Agent 自律，靠工具约束的安全模型 |
| 源可追溯性 | 整个 `wiki/` | Frontmatter 的 `sources` 字段连接回原始文件 |
| 质量门禁链 | doctor → health → benchmark → release | 层层递进的质量保障 |
| 发布审计 | `src/llmw/package.py` | 防止私有数据泄漏到 wheel/sdist |
| 自指涉示例 | `wiki/`（agent-dev 主题） | 用 Agent 开发知识来测试自己的工具 |
| Provider usage 模式 | `system/providers/qwen-plus.json` | 同一 API 不同用途不同配置 |
| JSON 契约 | 所有 CLI 命令 | Agent 和 CLI 用户一致的输出格式 |

---

## 知道更多了吗？

走完这 5 个阶段后，你应该能回答以下全部问题：

1. 为什么不直接用 RAG 而是维护 wiki？
2. `raw/` 和 `wiki/` 的边界是什么？为什么 `raw/` 不可变？
3. Plan/Apply 的安全模型是如何防止 Agent 越权的？
4. 搜索系统在什么情况下会从 rg 回退到 Python BM25？
5. MCP 深度搜索的三级回退策略是什么？
6. 一个新源文件从 `raw/inbox/` 到 `wiki/` 需要经过哪些步骤？
7. 发布前如何确保私有数据不会泄漏到包中？
8. Provider 配置中的 `usage` 是做什么用的？
9. MCP 服务器暴露了哪些工具和资源？
10. wiki 页面的 Frontmatter 有哪些字段，各有什么作用？

---

*文档生成时间：2026-05-02*
