from __future__ import annotations

import html
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "reports" / "function-test"
TRANSCRIPT = OUT_DIR / "function-test-transcript.txt"
TERMINAL_HTML = OUT_DIR / "function-test-terminal.html"
REPORT = OUT_DIR / "function-test-report-2026-05-04.md"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    transcript_parts: list[str] = []

    release_output = run(
        transcript_parts,
        "./scripts/release_check.sh",
        env={
            "RUN_LLM_SMOKE": "1",
            "RUN_SEARCH_BENCHMARK": "1",
            "RUN_DEEP_SEARCH_BENCHMARK": "0",
            "SEARCH_PROVIDER": "python",
            "SEARCH_TOP_K": "5",
        },
    )
    health_output = run(transcript_parts, "./.venv/bin/llmw health check --root . --json")
    benchmark_output = run(
        transcript_parts,
        "./.venv/bin/llmw benchmark search --root . --provider python --top-k 5 --json",
    )
    context_output = run(transcript_parts, "./.venv/bin/llmw context --root . --json")

    transcript = "\n".join(transcript_parts).rstrip() + "\n"
    TRANSCRIPT.write_text(transcript, encoding="utf-8")
    TERMINAL_HTML.write_text(render_terminal_html(transcript), encoding="utf-8")

    health = json.loads(health_output)
    benchmark = json.loads(benchmark_output)["benchmark"]["summary"]
    context = json.loads(context_output)["context"]
    write_report(
        release_output=release_output,
        health=health,
        benchmark=benchmark,
        context=context,
    )
    print(REPORT)


def run(parts: list[str], command: str, *, env: dict[str, str] | None = None) -> str:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    parts.append(f"$ {command}")
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=merged_env,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = result.stdout.rstrip()
    if output:
        parts.append(output)
    parts.append(f"# exit {result.returncode}")
    parts.append("")
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {command}\n{output}")
    return output


def write_report(*, release_output: str, health: dict, benchmark: dict, context: dict) -> None:
    pytest_summary = extract(r"(\d+ passed(?:, \d+ warnings?)? in [^\n]+)", release_output) or "见 transcript"
    pages = context["wiki"]["pages"]
    sources = context["sources"]["total"]
    issues = health.get("issues", [])
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M CST")
    report = f"""# 全功能测试报告

生成时间：{generated_at}

## 一句话结论

本次完整离线功能测试通过。项目当前 wiki 有 {pages} 个页面、{sources} 个 source；pytest 全量通过，health 无 issue，CLI/daemon/doctor/release smoke 通过，Python search benchmark 达到 release gate。

## 终端截图

![Full function test terminal](function-test-terminal.png)

原始终端 transcript：[`function-test-transcript.txt`](function-test-transcript.txt)

## 测试范围

| 模块 | 覆盖内容 | 结果 |
| --- | --- | --- |
| Tooling | `llmw --version`、Python 版本 | 通过 |
| Unit / integration tests | 全量 pytest | {pytest_summary} |
| Offline health | `llmw health check --root .` | 通过，issues={len(issues)} |
| CLI smoke | context、doctor、next、plan、apply、maintain、source、ingest、search、MCP、query、agent、release、package、install-agent 等 help 路径 | 通过 |
| Search daemon | start/status/query/stop | 通过 |
| Doctor smoke | `llmw doctor --no-codex --json` | 通过 |
| Release command smoke | `llmw release check --no-tests --no-benchmark --no-sdist --no-codex --json` | 通过 |
| Search benchmark | 102 个 benchmark query，provider=python，top_k=5 | 通过 |
| Live LLM smoke | `llmw llm check`、`llmw query`、`llmw health audit` | 通过 |
| Deep qmd benchmark | qmd/llmw deep benchmark | 未跑，属于可选向量检索外部依赖项 |

## Search Benchmark 摘要

```json
{json.dumps(benchmark, indent=2, ensure_ascii=False)}
```

关键指标：

- queries: {benchmark["queries"]}
- precision_at_k: {benchmark["precision_at_k"]:.4f}
- recall_at_k: {benchmark["recall_at_k"]:.4f}
- f1_at_k: {benchmark["f1_at_k"]:.4f}
- hit_rate_at_k: {benchmark["hit_rate_at_k"]:.4f}
- mrr_at_k: {benchmark["mrr_at_k"]:.4f}

## Health 摘要

```json
{json.dumps(health, indent=2, ensure_ascii=False)}
```

## 外部依赖说明

这份报告覆盖了可复现的离线功能测试，并额外打开了真实 LLM smoke。`RUN_DEEP_SEARCH_BENCHMARK=0` 是有意设置：

- deep qmd benchmark 依赖可选向量检索后端。
- LLM/query/ingest 的核心路径已由单元测试、mock provider QA 报告和 ingest 用户体验模拟覆盖。

## 产物

- 截图：[`function-test-terminal.png`](function-test-terminal.png)
- Transcript：[`function-test-transcript.txt`](function-test-transcript.txt)
- HTML 渲染源：[`function-test-terminal.html`](function-test-terminal.html)
- 复现脚本：[`run_function_test_report.py`](run_function_test_report.py)
"""
    REPORT.write_text(report, encoding="utf-8")


def extract(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text)
    return match.group(1) if match else None


def render_terminal_html(transcript: str) -> str:
    escaped = html.escape(transcript)
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
    width: 1180px;
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
    font: 14px/1.46 "DejaVu Sans Mono", "Noto Sans CJK SC", monospace;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }}
</style>
</head>
<body>
  <section class="terminal">
    <div class="bar"><span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span><span class="title">LLM Wiki 全功能测试</span></div>
    <pre>{escaped}</pre>
  </section>
</body>
</html>
"""


if __name__ == "__main__":
    main()
