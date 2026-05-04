from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

from llmw.core.fs import utc_now_iso
from llmw.core.paths import WikiPaths
from llmw.release import audit_sdist_artifact, run_release_check


def build_package(
    paths: WikiPaths,
    *,
    out_dir: Path,
    sdist: bool = True,
    wheel: bool = True,
    check: bool = True,
    probe_mcp: bool = False,
    strict: bool = True,
    timeout_seconds: float = 180,
) -> dict[str, Any]:
    if not sdist and not wheel:
        raise ValueError("At least one package format must be enabled")
    started = time.monotonic()
    output_dir = out_dir if out_dir.is_absolute() else paths.root / out_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    release_result: dict[str, Any] | None = None
    if check:
        release_result = run_release_check(
            paths,
            include_tests=True,
            include_benchmark=True,
            include_sdist=False,
            include_codex=True,
            probe_mcp=probe_mcp,
            strict=strict,
            timeout_seconds=timeout_seconds,
        )
        if not release_result["ok"]:
            return {
                "ok": False,
                "checked_at": utc_now_iso(),
                "root": paths.root.as_posix(),
                "out_dir": output_dir.as_posix(),
                "artifacts": [],
                "audits": [],
                "release": release_result,
                "error": "release check failed",
                "duration_seconds": round(time.monotonic() - started, 3),
            }

    uv_bin = shutil.which("uv")
    if not uv_bin:
        raise RuntimeError("uv executable not found")
    if not (paths.root / "pyproject.toml").exists():
        raise FileNotFoundError(paths.root / "pyproject.toml")

    with tempfile.TemporaryDirectory(prefix="llmw-package-") as temp:
        command = [uv_bin, "build", "--out-dir", temp]
        if sdist:
            command.append("--sdist")
        if wheel:
            command.append("--wheel")
        proc = subprocess.run(
            command,
            cwd=paths.root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "uv build failed")

        artifacts = []
        audits = []
        for artifact in sorted(Path(temp).iterdir()):
            if not artifact.is_file() or artifact.suffix not in {".gz", ".whl"}:
                continue
            target = output_dir / artifact.name
            shutil.copy2(artifact, target)
            artifact_payload = {
                "path": target.as_posix(),
                "name": target.name,
                "size_bytes": target.stat().st_size,
            }
            artifacts.append(artifact_payload)
            if target.name.endswith(".tar.gz"):
                audits.append(audit_sdist_artifact(target))
            elif target.suffix == ".whl":
                audits.append(audit_wheel_artifact(target))

    ok = all(audit["ok"] for audit in audits)
    payload = {
        "ok": ok,
        "checked_at": utc_now_iso(),
        "root": paths.root.as_posix(),
        "out_dir": output_dir.as_posix(),
        "artifacts": artifacts,
        "audits": audits,
        "release": release_result,
        "duration_seconds": round(time.monotonic() - started, 3),
    }
    report_path = output_dir / "llmw-package-report.json"
    payload["report_path"] = report_path.as_posix()
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def audit_wheel_artifact(wheel: Path) -> dict[str, Any]:
    violations: list[str] = []
    with zipfile.ZipFile(wheel) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        violations.extend(name for name in names if name.startswith(".llmw/"))
        violations.extend(name for name in names if name.startswith("raw/"))
        violations.extend(name for name in names if name.startswith("wiki/"))
        violations.extend(name for name in names if name.endswith(".env") or "/.env" in name)
        for name in names:
            try:
                content = archive.read(name).decode("utf-8")
            except UnicodeDecodeError:
                continue
            for match in re.finditer(r"DASHSCOPE_API_KEY\s*=\s*['\"]?([^'\"\s]+)", content):
                value = match.group(1).removesuffix("\\n")
                if value not in {"your-dashscope-api-key", "from-file"}:
                    violations.append(f"unexpected API-key-like value in {name}")
    return {"artifact": wheel.as_posix(), "ok": not violations, "violations": violations}


def format_package_report(payload: dict[str, Any]) -> str:
    lines = [
        "LLM Wiki Package",
        f"Output: {payload['out_dir']}",
        f"Status: {'ready' if payload['ok'] else 'blocked'}",
        f"Artifacts: {len(payload['artifacts'])}",
    ]
    for artifact in payload["artifacts"]:
        lines.append(f"- {artifact['name']} ({artifact['size_bytes']} bytes)")
    for audit in payload["audits"]:
        status = "pass" if audit["ok"] else "fail"
        lines.append(f"[{status}] audit {Path(audit['artifact']).name}")
        for violation in audit["violations"]:
            lines.append(f"  - {violation}")
    if payload.get("report_path"):
        lines.append(f"Report: {payload['report_path']}")
    return "\n".join(lines)
