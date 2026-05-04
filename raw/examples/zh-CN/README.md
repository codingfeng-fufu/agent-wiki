# 中文 Raw 示例源

这里放的是公开、合成的中文源文档，用来演示 LLM Wiki 的 `raw/` 证据层长什么样。

这些文件不是当前项目的活跃 source registry，也不是待摄取队列。你可以复制一份到 `raw/inbox/` 后自己试用：

```bash
cp raw/examples/zh-CN/项目记忆设计备忘录.md raw/inbox/
.venv/bin/llmw source add raw/inbox/项目记忆设计备忘录.md
.venv/bin/llmw ingest packet <source_id>
```

如果想让 LLM 自动摄取，并且 provider 已配置好：

```bash
.venv/bin/llmw ingest run <source_id>
```

建议第一次先用 `ingest packet`，让 agent 根据任务包手动维护 `wiki/`，这样更容易观察 `raw/` 和 `wiki/` 的边界。
