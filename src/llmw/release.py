from __future__ import annotations

import re
import shutil
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Any

from llmw.core.fs import utc_now_iso
from llmw.core.paths import WikiPaths
from llmw.doctor import run_doctor
from llmw.health.checks import HealthChecker
from llmw.search.benchmark import assert_benchmark_gates, run_search_benchmark


ALLOWED_RAW_PLACEHOLDERS = {
    "raw/assets/.gitkeep",
    "raw/inbox/.gitkeep",
    "raw/processed/.gitkeep",
}
ALLOWED_WIKI_TEMPLATES = {
    "wiki/index.md",
    "wiki/log.md",
}
ALLOWED_SECRET_PLACEHOLDERS = {
    "from-file",
    "from-test",
    "mock-placeholder-key",
    "test-key",
    "your-dashscope-api-key",
}
SECRET_VALUE_RE = re.compile(
    r"""(?ix)
    (?:
      \b[A-Z][A-Z0-9_]*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|ACCESS[_-]?KEY|PRIVATE[_-]?KEY)\b
      ["'\]]*\s*(?:(?<![=!<>])=(?!=)|:)\s*
    )
    ["']?([^'"\s,}]+)
    """
)


def run_release_check(
    paths: WikiPaths,
    *,
    include_tests: bool = True,
    include_benchmark: bool = True,
    include_sdist: bool = False,
    include_codex: bool = True,
    probe_mcp: bool = False,
    strict: bool = True,
    search_provider: str = "python",
    search_top_k: int = 5,
    fail_under_f1: float | None = 0.20,
    fail_under_recall: float | None = 0.60,
    fail_under_hit_rate: float | None = 0.60,
    timeout_seconds: float = 180,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    checks.append(_doctor_check(paths, include_codex=include_codex, probe_mcp=probe_mcp, strict=strict))
    checks.append(_health_check(paths, strict=strict))
    if include_tests:
        checks.append(_pytest_check(paths, timeout_seconds=timeout_seconds))
    else:
        checks.append(_skip_check("tests", "Unit tests", "Skipped by --no-tests."))
    if include_benchmark:
        checks.append(
            _benchmark_check(
                paths,
                provider=search_provider,
                top_k=search_top_k,
                fail_under_f1=fail_under_f1,
                fail_under_recall=fail_under_recall,
                fail_under_hit_rate=fail_under_hit_rate,
            )
        )
    else:
        checks.append(_skip_check("search.benchmark", "Search benchmark", "Skipped by --no-benchmark."))
    if include_sdist:
        checks.append(_sdist_check(paths, timeout_seconds=timeout_seconds))
    else:
        checks.append(_skip_check("package.sdist", "Source distribution", "Skipped by --no-sdist."))

    ok = all(check["status"] in {"pass", "skip"} for check in checks)
    return {
        "ok": ok,
        "readiness": "ready" if ok else "blocked",
        "strict": strict,
        "checked_at": utc_now_iso(),
        "root": paths.root.as_posix(),
        "summary": {
            "pass": sum(1 for check in checks if check["status"] == "pass"),
            "warn": sum(1 for check in checks if check["status"] == "warn"),
            "fail": sum(1 for check in checks if check["status"] == "fail"),
            "skip": sum(1 for check in checks if check["status"] == "skip"),
        },
        "checks": checks,
    }


def format_release_report(result: dict[str, Any]) -> str:
    lines = [
        "LLM Wiki Release Check",
        f"Root: {result['root']}",
        f"Readiness: {result['readiness']}",
        f"Checks: {result['summary']['pass']} pass, {result['summary']['warn']} warn, {result['summary']['fail']} fail, {result['summary']['skip']} skip",
        "",
    ]
    for check in result["checks"]:
        marker = {"pass": "PASS", "warn": "WARN", "fail": "FAIL", "skip": "SKIP"}.get(check["status"], check["status"].upper())
        lines.append(f"[{marker}] {check['title']}: {check['message']}")
    return "\n".join(lines)


def _doctor_check(paths: WikiPaths, *, include_codex: bool, probe_mcp: bool, strict: bool) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = run_doctor(paths, include_codex=include_codex, probe_mcp=probe_mcp, strict=strict)
    except Exception as exc:
        return _check("doctor", "Doctor", "fail", f"Doctor failed: {exc}", started=started)
    return _check(
        "doctor",
        "Doctor",
        "pass" if result["ok"] else "fail",
        f"Doctor readiness is {result['readiness']}.",
        details=result,
        started=started,
    )


def _health_check(paths: WikiPaths, *, strict: bool) -> dict[str, Any]:
    started = time.monotonic()
    issues = HealthChecker(paths).run()
    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity == "warning"]
    if errors or (strict and warnings):
        status = "fail"
    elif warnings:
        status = "warn"
    else:
        status = "pass"
    return _check(
        "health",
        "Structural health",
        status,
        f"{len(errors)} error(s), {len(warnings)} warning(s), {len(issues) - len(errors) - len(warnings)} info issue(s).",
        details={"issues": [issue.model_dump() for issue in issues]},
        started=started,
    )


def _pytest_check(paths: WikiPaths, *, timeout_seconds: float) -> dict[str, Any]:
    started = time.monotonic()
    if not (paths.root / "tests").exists():
        return _check("tests", "Unit tests", "skip", "No tests/ directory found.", started=started)
    pytest_bin = _local_executable(paths, "pytest") or shutil.which("pytest")
    if not pytest_bin:
        return _check("tests", "Unit tests", "fail", "pytest executable not found.", started=started)
    return _command_check("tests", "Unit tests", [pytest_bin, "-q"], paths.root, started=started, timeout_seconds=timeout_seconds)


def _benchmark_check(
    paths: WikiPaths,
    *,
    provider: str,
    top_k: int,
    fail_under_f1: float | None,
    fail_under_recall: float | None,
    fail_under_hit_rate: float | None,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        payload = run_search_benchmark(paths, provider=provider, top_k=top_k)
        assert_benchmark_gates(
            payload["summary"],
            fail_under_f1=fail_under_f1,
            fail_under_recall=fail_under_recall,
            fail_under_hit_rate=fail_under_hit_rate,
        )
    except Exception as exc:
        return _check("search.benchmark", "Search benchmark", "fail", f"Search benchmark failed: {exc}", started=started)
    summary = payload["summary"]
    return _check(
        "search.benchmark",
        "Search benchmark",
        "pass",
        f"F1@{summary['top_k']}={summary['f1_at_k']:.4f}, Recall@{summary['top_k']}={summary['recall_at_k']:.4f}, HitRate@{summary['top_k']}={summary['hit_rate_at_k']:.4f}.",
        details={
            "provider": payload["provider"],
            "summary": summary,
            "thresholds": {
                "fail_under_f1": fail_under_f1,
                "fail_under_recall": fail_under_recall,
                "fail_under_hit_rate": fail_under_hit_rate,
            },
        },
        started=started,
    )


def _sdist_check(paths: WikiPaths, *, timeout_seconds: float) -> dict[str, Any]:
    started = time.monotonic()
    uv_bin = shutil.which("uv")
    if not uv_bin:
        return _check("package.sdist", "Source distribution", "fail", "uv executable not found.", started=started)
    if not (paths.root / "pyproject.toml").exists():
        return _check("package.sdist", "Source distribution", "skip", "pyproject.toml not found.", started=started)

    with tempfile.TemporaryDirectory(prefix="llmw-sdist-") as temp:
        proc = subprocess.run(
            [uv_bin, "build", "--sdist", "--out-dir", temp],
            cwd=paths.root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
        if proc.returncode != 0:
            return _check(
                "package.sdist",
                "Source distribution",
                "fail",
                "uv build --sdist failed.",
                details={"stdout": _tail(proc.stdout), "stderr": _tail(proc.stderr), "returncode": proc.returncode},
                started=started,
            )
        sdist = next(Path(temp).glob("*.tar.gz"), None)
        if sdist is None:
            return _check("package.sdist", "Source distribution", "fail", "uv build did not produce a .tar.gz sdist.", started=started)
        violations = audit_sdist_artifact(sdist)["violations"]
        if violations:
            return _check(
                "package.sdist",
                "Source distribution",
                "fail",
                f"sdist has {len(violations)} packaging violation(s).",
                details={"violations": violations},
                started=started,
            )
        return _check(
            "package.sdist",
            "Source distribution",
            "pass",
            f"Built and audited {sdist.name}.",
            details={"artifact": sdist.name},
            started=started,
        )


def audit_sdist_artifact(sdist: Path) -> dict[str, Any]:
    violations = _sdist_violations(sdist)
    return {"artifact": sdist.as_posix(), "ok": not violations, "violations": violations}


def _sdist_violations(sdist: Path) -> list[str]:
    members = _sdist_members(sdist)
    violations: list[str] = []
    violations.extend(path for path in sorted(members) if path.startswith(".llmw/"))
    violations.extend(path for path in sorted(members) if path.startswith("raw/") and path not in ALLOWED_RAW_PLACEHOLDERS)
    violations.extend(path for path in sorted(members) if path.startswith("wiki/") and path not in ALLOWED_WIKI_TEMPLATES)
    violations.extend(path for path in sorted(members) if path.endswith(".env") or "/.env" in path)
    for path, content in _sdist_text_contents(sdist).items():
        violations.extend(_secret_value_violations(path, content))
    return violations


def _secret_value_violations(path: str, content: str) -> list[str]:
    violations: list[str] = []
    for match in SECRET_VALUE_RE.finditer(content):
        value = match.group(1).removesuffix("\\n")
        if _looks_like_safe_placeholder(value):
            continue
        violations.append(f"unexpected secret-like value in {path}")
    return violations


def _looks_like_safe_placeholder(value: str) -> bool:
    normalized = value.strip().strip("'\"")
    lowered = normalized.lower()
    if normalized in ALLOWED_SECRET_PLACEHOLDERS:
        return True
    return any(token in lowered for token in ["example", "fake", "mock", "placeholder", "your-"])


def _sdist_members(sdist: Path) -> set[str]:
    with tarfile.open(sdist) as archive:
        return {_strip_sdist_prefix(member.name) for member in archive.getmembers() if member.isfile()}


def _sdist_text_contents(sdist: Path) -> dict[str, str]:
    contents: dict[str, str] = {}
    with tarfile.open(sdist) as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            extracted = archive.extractfile(member)
            if extracted is None:
                continue
            data = extracted.read()
            try:
                contents[_strip_sdist_prefix(member.name)] = data.decode("utf-8")
            except UnicodeDecodeError:
                continue
    return contents


def _strip_sdist_prefix(path: str) -> str:
    return path.split("/", 1)[1] if "/" in path else path


def _command_check(
    check_id: str,
    title: str,
    command: list[str],
    cwd: Path,
    *,
    started: float,
    timeout_seconds: float,
) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return _check(check_id, title, "fail", f"Command timed out after {timeout_seconds:g}s.", details={"command": command, "stdout": _tail(exc.stdout), "stderr": _tail(exc.stderr)}, started=started)
    return _check(
        check_id,
        title,
        "pass" if proc.returncode == 0 else "fail",
        "Command passed." if proc.returncode == 0 else f"Command failed with exit code {proc.returncode}.",
        details={"command": command, "returncode": proc.returncode, "stdout": _tail(proc.stdout), "stderr": _tail(proc.stderr)},
        started=started,
    )


def _skip_check(check_id: str, title: str, message: str) -> dict[str, Any]:
    return _check(check_id, title, "skip", message, started=time.monotonic())


def _check(
    check_id: str,
    title: str,
    status: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    started: float,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "title": title,
        "status": status,
        "message": message,
        "duration_seconds": round(time.monotonic() - started, 3),
        "details": details or {},
    }


def _local_executable(paths: WikiPaths, name: str) -> str | None:
    suffix = ".exe" if _is_windows() else ""
    candidate = paths.root / ".venv" / ("Scripts" if _is_windows() else "bin") / f"{name}{suffix}"
    return candidate.as_posix() if candidate.exists() else None


def _is_windows() -> bool:
    import sys

    return sys.platform == "win32"


def _tail(value: str | bytes | None, *, max_chars: int = 4000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return value[-max_chars:]
