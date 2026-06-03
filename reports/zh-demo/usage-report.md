# 中文示例试用报告

测试时间：2026-05-04

测试目标：使用 `raw/examples/zh-CN/` 里的中文合成源，验证从 raw source 到 wiki，再到中文 Q&A 的基本体验，并保存一组终端输出截图。

## 测试环境

- 原项目：`/path/to/agent-wiki`
- 临时项目：`/tmp/llmw-zh-demo`
- 产物目录：`reports/zh-demo/`
- Provider：`qwen_plus`，测试时已配置可用凭据
- 测试源：
  - `项目记忆设计备忘录.md`
  - `Agent安全审查记录.md`
  - `检索性能维护记录.md`

## 操作流程

1. 在 `/tmp/llmw-zh-demo` 初始化新项目。
2. 将三份中文 raw examples 复制到 `raw/inbox/`。
3. 复制 provider 和 prompt 配置。
4. 运行 `llmw source add` 注册三份源。
5. 运行 `llmw ingest run <source_id>` 自动摄取。
6. 使用 `llmw query` 做三组中文问答。
7. 将每组 Q&A 输出保存为 txt，并渲染为终端风格 PNG。

## 摄取结果

- `项目记忆设计备忘录.md`：摄取成功，约 27 秒。
  - 生成 `wiki/sources/item-696f6f97.md`
  - 生成 `wiki/concepts/long-term-memory-layer.md`
  - 生成 `wiki/concepts/coding-agent.md`
- `Agent安全审查记录.md`：摄取成功，约 22 秒。
  - 生成 `wiki/sources/agent-c0159bbf.md`
  - 生成 `wiki/concepts/Coding_Agent.md`
  - 生成 `wiki/concepts/Long-Term_Memory_Layer.md`
- `检索性能维护记录.md`：自动摄取失败，两次均返回 `LLM response did not contain a JSON object`。

## Q&A 截图

- [qa01.png](qa01.png)：长期记忆层为什么能减少重复读取上下文
- [qa02.png](qa02.png)：Prompt injection 和写入权限风险
- [qa03.png](qa03.png)：`raw/` 与 `wiki/` 的边界

对应原始终端文本：

- [qa01.txt](qa01.txt)
- [qa02.txt](qa02.txt)
- [qa03.txt](qa03.txt)

## 观察

### 好的地方

- 中文 raw source 可以成功注册。
- 前两份中文源可以通过 `ingest run` 生成 wiki 页面。
- `llmw query` 可以基于生成后的 wiki 给出中文回答，并列出 evidence pages。
- `raw/` 只读、`wiki/` 维护层、安全写入这些核心概念被回答正确。

### 问题

- 第三份中文源自动摄取不稳定：模型没有返回严格 JSON，导致 `ingest run` 失败。
- 自动摄取生成了重复概念页：`coding-agent.md` 和 `Coding_Agent.md`，`long-term-memory-layer.md` 和 `Long-Term_Memory_Layer.md`。
- 部分概念页标题和 slug 被英文标准化，中文源场景下可读性一般。
- 第一版自然中文 query `这个项目为什么需要一个长期记忆层？` 没找到相关页；改成包含 `long-term memory layer` 后可回答，说明中文检索召回还有提升空间。
- health check 对重复概念页只给 orphan info，没有识别大小写/slug 重复概念。

## 建议改进

1. 强化 `ingest run` 的 JSON 修复或重试策略：当模型返回非 JSON 时，尝试提取 JSON、重新提示或自动二次修复。
2. 为中文源增加 slug/title 规范：避免同一概念生成大小写不同的重复页面。
3. 增加中文检索 benchmark，覆盖纯中文 query、混合中英文 query、source title query。
4. 在 health check 中增加近似重复页面检测，例如 slug 大小写差异、title 相同、sources 相近。
5. 对 raw examples 提供一条推荐试用路径：先 `source add`，再 `ingest packet`，最后由 agent 手动维护，避免第一次体验被自动 JSON 格式问题打断。

## 结论

这套中文 examples 可以用于试用。注册、部分自动摄取、wiki 查询都能跑通，核心概念能被正确回答。

但自动摄取和中文检索还不够稳。对于公开 demo，建议优先展示 `scripts/demo.sh` 和已维护 example wiki；中文 examples 更适合作为手动试用材料，并在文档里说明自动摄取依赖模型输出格式。
