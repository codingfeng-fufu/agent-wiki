from __future__ import annotations

import html
import json
import os
import subprocess
import sys
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "reports" / "qa-demo"
PROVIDER_PATH = OUT_DIR / "mock-provider.json"
PORT = 8776


@dataclass(frozen=True)
class QAItem:
    id: str
    question: str
    answer: str


QA_ITEMS = [
    QAItem(
        "qa01",
        "Agent guardrails 主要解决什么问题？",
        "Agent guardrails 用来在输入、输出和工具调用周围建立验证边界，减少不安全输入、格式错误输出和工具滥用风险。相关证据见 Agent Guardrails、Input Guardrails 和 Output Guardrails。",
    ),
    QAItem(
        "qa02",
        "Agent tracing 和 tool-call logs 对调试有什么帮助？",
        "Tracing 让开发者看到 agent 的步骤、工具调用和中间状态；tool-call logs 记录具体工具请求与结果，方便复现、审计和定位失败。相关证据见 Agent Tracing、Tool Call Logs 和 Agent Observability。",
    ),
    QAItem(
        "qa03",
        "Long-running agents 如何在中断后恢复？",
        "长运行 agent 需要持久化执行状态、检查点和可重放记录；中断后可以从最近状态恢复，而不是从头重新读取和推理。相关证据见 Durable Agent Execution、Agent Checkpointing 和 Replayable Agent Runs。",
    ),
    QAItem(
        "qa04",
        "MCP tools 和 A2A 协议的边界是什么？",
        "MCP 更偏向把工具、资源和 prompts 暴露给模型或 agent runtime；A2A 更偏向 agent 与 agent 之间跨边界交换任务、状态和消息。相关证据见 Model Context Protocol、MCP Tools、Agent2Agent Protocol 和 MCP vs A2A。",
    ),
    QAItem(
        "qa05",
        "如何降低 tool-using agents 的 prompt injection 风险？",
        "要降低 prompt injection 风险，应限制工具权限、隔离不可信输入、验证工具参数和输出，并保持最小权限原则。相关证据见 Prompt Injection、Tool Safety、Least Privilege 和 Agent Security。",
    ),
    QAItem(
        "qa06",
        "为什么不要把 sensitive data 放进 traces 或 logs？",
        "Traces 和 logs 常用于调试、共享和长期保存；如果写入 secrets 或私有信息，会扩大暴露面并增加审计风险。相关证据见 Sensitive Data Exposure、Agent Tracing 和 Tool Call Logs。",
    ),
    QAItem(
        "qa07",
        "Planner-executor pattern 适合什么场景？",
        "Planner-executor pattern 适合需要先拆解任务、再由执行步骤逐项完成的 agent workflow，尤其适合复杂、多步骤或需要检查执行结果的任务。相关证据见 Planner Executor Pattern、Coordinator Agent 和 Reviewer Agent。",
    ),
    QAItem(
        "qa08",
        "Fan-out gather pattern 如何帮助 multi-agent 协作？",
        "Fan-out gather pattern 会把工作并行分发给多个 agent，再收集和合并结果，适合需要并行探索、比较多个答案或汇总多个子任务的场景。相关证据见 Fan-Out Gather Pattern、Coordinator Agent 和 Multi-Agent Systems。",
    ),
    QAItem(
        "qa09",
        "Human-in-the-loop 在 agent workflow 中有什么作用？",
        "Human-in-the-loop 用于在高风险、低置信度或需要业务判断的节点加入人工审批，让 agent workflow 不必完全自动化执行。相关证据见 Human In The Loop、Durable Agent Execution 和 Agent State Graph。",
    ),
    QAItem(
        "qa10",
        "Agent evaluation 和 regression testing 如何保持行为稳定？",
        "Agent evaluation 用来衡量行为是否安全、有用和可复现；regression testing 则把关键行为固定成测试，防止模型、prompt 或工具变更造成退化。相关证据见 Agent Evaluation、Agent Regression Testing 和 Agent Observability。",
    ),
]


class MockQueryHandler(BaseHTTPRequestHandler):
    calls = 0

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", "0"))
        data = json.loads(self.rfile.read(length).decode("utf-8"))
        user_prompt = str(data["messages"][-1]["content"])
        MockQueryHandler.calls += 1
        answer = answer_for_prompt(user_prompt)
        payload = {
            "model": "mock-qa-model",
            "choices": [{"message": {"content": answer}}],
            "usage": {"total_tokens": 256},
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_provider_config()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), MockQueryHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        results = [run_qa(item) for item in QA_ITEMS]
    finally:
        server.shutdown()
        server.server_close()
    write_report(results)
    print(OUT_DIR / "ten-qa-report.md")


def write_provider_config() -> None:
    PROVIDER_PATH.write_text(
        json.dumps(
            {
                "default_provider": "mock",
                "providers": {
                    "mock": {
                        "type": "openai_compatible",
                        "model": "mock-qa-model",
                        "base_url": f"http://127.0.0.1:{PORT}/v1",
                        "api_key_env": "MOCK_LLM_API_KEY",
                        "timeout_seconds": 10,
                        "max_retries": 0,
                        "usage": {
                            "query": {
                                "system_prompt_file": "system/prompts/query.md",
                                "temperature": 0.0,
                                "max_tokens": 512,
                            }
                        },
                    }
                },
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def answer_for_prompt(user_prompt: str) -> str:
    for item in QA_ITEMS:
        if item.question in user_prompt:
            return item.answer
    return "未找到匹配问题；请检查 mock QA 配置。"


def run_qa(item: QAItem) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env["MOCK_LLM_API_KEY"] = "mock-key"
    env["LLMW_DISABLE_QMD"] = "1"
    command = [
        "llmw",
        "query",
        item.question,
        "--root",
        ".",
        "--provider-config",
        PROVIDER_PATH.relative_to(ROOT).as_posix(),
        "--limit",
        "3",
        "--max-page-chars",
        "1600",
    ]
    exec_command = [sys.executable, "-m", "llmw", *command[1:]]
    output_lines = [f"$ {' '.join(command)}"]
    result = subprocess.run(
        exec_command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.stdout.strip():
        output_lines.extend(result.stdout.strip().splitlines())
    output_lines.append(f"# exit {result.returncode}")
    transcript = "\n".join(output_lines).rstrip() + "\n"
    if result.returncode != 0:
        raise RuntimeError(transcript)

    txt_path = OUT_DIR / f"{item.id}.txt"
    html_path = OUT_DIR / f"{item.id}.html"
    txt_path.write_text(transcript, encoding="utf-8")
    html_path.write_text(render_terminal_html(item, transcript), encoding="utf-8")
    return {
        "id": item.id,
        "question": item.question,
        "answer": item.answer,
        "txt": txt_path.name,
        "html": html_path.name,
        "png": f"{item.id}.png",
        "evidence": evidence_from_transcript(transcript),
    }


def evidence_from_transcript(transcript: str) -> str:
    lines = transcript.splitlines()
    evidence = [line.strip()[2:] for line in lines if line.startswith("- ")]
    return "; ".join(evidence[:3])


def render_terminal_html(item: QAItem, transcript: str) -> str:
    escaped = html.escape(transcript)
    title = html.escape(f"{item.id.upper()} 用户终端 QA")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 28px;
    background: #e7e9ee;
    font-family: "Inter", "Noto Sans CJK SC", "Noto Sans", Arial, sans-serif;
  }}
  .terminal {{
    width: 1120px;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 22px 60px rgba(15, 23, 42, 0.22);
    background: #0b1020;
  }}
  .bar {{
    height: 42px;
    background: #171d2f;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 16px;
    color: #b7c0d6;
    font-size: 14px;
  }}
  .dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
  .red {{ background: #ff5f57; }}
  .yellow {{ background: #ffbd2e; }}
  .green {{ background: #28c840; }}
  .title {{ margin-left: 12px; }}
  pre {{
    margin: 0;
    padding: 22px 24px 28px;
    color: #d8e1ff;
    background: #0b1020;
    font: 15px/1.48 "DejaVu Sans Mono", "Noto Sans CJK SC", monospace;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }}
</style>
</head>
<body>
  <section class="terminal">
    <div class="bar"><span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span><span class="title">{title}</span></div>
    <pre>{escaped}</pre>
  </section>
</body>
</html>
"""


def write_report(results: list[dict[str, str]]) -> None:
    sections = []
    rows = ["| ID | 问题 | 证据页 | 截图 |", "| --- | --- | --- | --- |"]
    for result in results:
        rows.append(
            f"| {result['id'].upper()} | {result['question']} | {result['evidence']} | [{result['png']}]({result['png']}) |"
        )
        sections.append(
            f"""## {result['id'].upper()}：{result['question']}

![{result['id'].upper()} terminal screenshot]({result['png']})

Transcript：[`{result['txt']}`]({result['txt']})
"""
        )

    report = f"""# 十个 QA 用户体验报告

生成时间：2026-05-04 15:10 CST

## 说明

这份报告从用户终端视角验证 `llmw query` 的问答体验。每个 QA 都通过真实 CLI 命令执行，检索证据来自当前 `wiki/`；LLM 回答由本地 mock OpenAI-compatible API 返回，保证报告可复现且不消耗真实模型额度。

执行形式：

```text
llmw query "<question>" --root . --provider-config reports/qa-demo/mock-provider.json --limit 3 --max-page-chars 1600
```

## 总览

{chr(10).join(rows)}

## QA 截图

{chr(10).join(sections)}

## 产物

- Mock provider：[`mock-provider.json`](mock-provider.json)
- 复现脚本：[`run_ten_qa_demo.py`](run_ten_qa_demo.py)
- 每个 QA 的原始终端输出：`qa01.txt` 到 `qa10.txt`
- 每个 QA 的终端截图：`qa01.png` 到 `qa10.png`

## 结论

这 10 个问题覆盖 guardrails、tracing、durable execution、MCP/A2A、prompt injection、sensitive data、planner-executor、fan-out gather、human-in-the-loop、evaluation/regression testing 等核心概念。终端输出中每个回答都带有 Evidence pages，说明用户能看到答案来源，而不只是得到一段无来源文本。
"""
    (OUT_DIR / "ten-qa-report.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
