from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_demo_script_runs_read_only_loop() -> None:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["LLMW"] = str(root / ".venv" / "bin" / "llmw")

    result = subprocess.run(
        [str(root / "scripts" / "demo.sh"), str(root)],
        cwd=root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "LLM Wiki demo" in result.stdout
    assert "prompt injection tool safety" in result.stdout
    assert '"action": "index_rebuild"' in result.stdout
    assert '"dry_run": true' in result.stdout
    assert '"issues": []' in result.stdout
