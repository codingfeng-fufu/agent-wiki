from __future__ import annotations

import json
import os
import html
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "reports" / "ingest-simulation"
PROJECT = OUT_DIR / "workspace"
TRANSCRIPT = OUT_DIR / "terminal-transcript.txt"
TERMINAL_HTML = OUT_DIR / "terminal-user-experience.html"

SOURCE_ID = "zh-long-memory-1234"


VALID_PAYLOAD = {
    "pages": [
        {
            "path": "wiki/sources/not-the-source-id.md",
            "content": "---\ntitle: 中文长期记忆资料\ntype: source\nstatus: draft\nsources: [\"zh-long-memory-1234\"]\ntags: []\n---\n\n# 中文长期记忆资料\n\n关联 [[Coding Agent]] 和 [[长期记忆层]]。",
        },
        {
            "path": "wiki/concepts/Coding_Agent.md",
            "content": "---\ntitle: Coding Agent\ntype: concept\nstatus: draft\nsources: [\"zh-long-memory-1234\"]\ntags: []\n---\n\n# Coding Agent\n\nCoding agent 会从长期记忆层复用项目上下文。",
        },
        {
            "path": "wiki/concepts/Long-Term_Memory_Layer.md",
            "content": "---\ntitle: 长期记忆层\ntype: concept\nstatus: draft\nsources: [\"zh-long-memory-1234\"]\ntags: []\n---\n\n# 长期记忆层\n\n长期记忆层帮助 coding agent 减少重复读取项目上下文，并通过 [[Coding Agent]] 形成项目记忆。",
        },
    ],
    "log_note": "模拟 ingest 完成。",
}


class MockLLMHandler(BaseHTTPRequestHandler):
    calls = 0

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", "0"))
        self.rfile.read(length)
        MockLLMHandler.calls += 1
        if MockLLMHandler.calls == 1:
            content = "我已经整理好了，但这不是 JSON。"
        else:
            content = json.dumps(VALID_PAYLOAD, ensure_ascii=False)
        payload = {
            "model": "mock-llm",
            "choices": [{"message": {"content": content}}],
            "usage": {"total_tokens": 123},
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if PROJECT.exists():
        shutil.rmtree(PROJECT)
    PROJECT.mkdir(parents=True)

    server = ThreadingHTTPServer(("127.0.0.1", 0), MockLLMHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}/v1"

    try:
        transcript = run_demo(base_url)
    finally:
        server.shutdown()
        server.server_close()

    TRANSCRIPT.write_text(transcript, encoding="utf-8")
    TERMINAL_HTML.write_text(render_terminal_html(transcript), encoding="utf-8")
    print(TRANSCRIPT)


def run_demo(base_url: str) -> str:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env["MOCK_LLM_API_KEY"] = "mock-key"
    env["LLMW_DISABLE_QMD"] = "1"

    lines: list[str] = []

    run(lines, env, ["llmw", "init", "--root", str(PROJECT)])

    provider_path = PROJECT / "system" / "providers" / "mock.json"
    provider_path.write_text(
        json.dumps(
            {
                "default_provider": "mock",
                "providers": {
                    "mock": {
                        "type": "openai_compatible",
                        "model": "mock-llm",
                        "base_url": base_url,
                        "api_key_env": "MOCK_LLM_API_KEY",
                        "timeout_seconds": 10,
                        "max_retries": 0,
                        "usage": {
                            "ingest": {
                                "system_prompt_file": "system/prompts/ingest.md",
                                "temperature": 0.7,
                                "max_tokens": 4096,
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
    append_file(lines, "配置 mock provider", provider_path.relative_to(PROJECT).as_posix())

    source = PROJECT / "raw" / "inbox" / "zh-long-memory.md"
    source.write_text(
        "# 中文长期记忆资料\n\n长期记忆层让 coding agent 少重复读取项目上下文。\n",
        encoding="utf-8",
    )
    append_file(lines, "准备中文 raw source", source.relative_to(PROJECT).as_posix())

    run(lines, env, ["llmw", "source", "add", "raw/inbox/zh-long-memory.md", "--root", str(PROJECT), "--json"])
    force_source_id(lines)

    existing = PROJECT / "wiki" / "concepts" / "coding-agent.md"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text(
        "---\ntitle: Coding Agent\ntype: concept\nstatus: draft\nsources: []\ntags: []\n---\n\n"
        "# Coding Agent\n\nExisting page that should be reused.\n",
        encoding="utf-8",
    )
    run(lines, env, ["llmw", "index", "rebuild", "--root", str(PROJECT), "--json"])
    append_file(lines, "预置已有概念页", existing.relative_to(PROJECT).as_posix())

    run(
        lines,
        env,
        [
            "llmw",
            "ingest",
            "run",
            SOURCE_ID,
            "--root",
            str(PROJECT),
            "--provider-config",
            str(provider_path),
            "--json",
        ],
    )
    run(lines, env, ["llmw", "health", "check", "--root", str(PROJECT), "--json"])
    run(lines, env, ["llmw", "search", "这个项目为什么需要一个长期记忆层？", "--root", str(PROJECT), "--json"])

    append_check(lines, "mock LLM calls", str(MockLLMHandler.calls))
    append_check(lines, "duplicate page exists", str((PROJECT / "wiki" / "concepts" / "Coding_Agent.md").exists()))
    append_check(lines, "Chinese concept exists", str((PROJECT / "wiki" / "concepts" / "长期记忆层.md").exists()))
    return "\n".join(lines).rstrip() + "\n"


def run(lines: list[str], env: dict[str, str], args: list[str]) -> None:
    command = " ".join(args)
    lines.append(f"$ {command}")
    exec_args = [sys.executable, "-m", "llmw", *args[1:]] if args and args[0] == "llmw" else args
    result = subprocess.run(
        exec_args,
        cwd=PROJECT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = result.stdout.strip()
    if output:
        lines.extend(output.splitlines())
    lines.append(f"# exit {result.returncode}")
    lines.append("")
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {command}")


def force_source_id(lines: list[str]) -> None:
    registry_path = PROJECT / ".llmw" / "sources.json"
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    record = next(iter(data["sources"].values()))
    old_id = record["source_id"]
    old_rel_path = record["path"]
    record["source_id"] = SOURCE_ID
    record["path"] = record["path"].replace(old_id, SOURCE_ID)
    old_path = PROJECT / old_rel_path
    new_path = PROJECT / record["path"]
    if old_path.exists() and old_path != new_path:
        new_path.parent.mkdir(parents=True, exist_ok=True)
        old_path.rename(new_path)
    data["sources"] = {SOURCE_ID: record}
    registry_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines.append(f"# normalize source_id: {old_id} -> {SOURCE_ID}")
    lines.append("")


def append_file(lines: list[str], label: str, path: str) -> None:
    lines.append(f"# {label}: {path}")
    lines.append("")


def append_check(lines: list[str], label: str, value: str) -> None:
    lines.append(f"# {label}: {value}")


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
    padding: 32px;
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
    font: 15px/1.48 "DejaVu Sans Mono", "Noto Sans CJK SC", monospace;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }}
</style>
</head>
<body>
  <section class="terminal">
    <div class="bar"><span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span><span class="title">LLM Wiki 用户终端模拟</span></div>
    <pre>{escaped}</pre>
  </section>
</body>
</html>
"""


if __name__ == "__main__":
    main()
