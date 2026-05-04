from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from llmw.core.config import load_config
from llmw.core.fs import utc_now_iso
from llmw.core.paths import WikiPaths
from llmw.search.providers import build_search_service, recommend_search_strategy


def start_daemon(paths: WikiPaths, *, deep: bool = False, default_limit: int = 5, timeout_seconds: float = 15) -> dict[str, Any]:
    current = daemon_status(paths)
    if current["running"]:
        return {**current, "already_running": True}
    _cleanup_runtime(paths)
    _daemon_dir(paths).mkdir(parents=True, exist_ok=True)
    log_file = _log_path(paths).open("ab")
    command = [
        sys.executable,
        "-m",
        "llmw.search.daemon",
        "--serve",
        "--root",
        paths.root.as_posix(),
        "--limit",
        str(default_limit),
    ]
    if deep:
        command.append("--deep")
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=log_file,
        stderr=log_file,
        start_new_session=True,
        env=_subprocess_env(),
    )
    log_file.close()
    metadata = {
        "pid": process.pid,
        "root": paths.root.as_posix(),
        "deep": deep,
        "default_limit": default_limit,
        "started_at": utc_now_iso(),
        "socket_path": _socket_path(paths).as_posix(),
        "log_path": _log_path(paths).as_posix(),
        "command": command,
    }
    _metadata_path(paths).write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Search daemon exited during startup with code {process.returncode}")
        try:
            ping_daemon(paths)
            return daemon_status(paths)
        except Exception as exc:
            last_error = str(exc)
            time.sleep(0.1)
    raise RuntimeError(f"Search daemon did not become ready: {last_error}")


def daemon_status(paths: WikiPaths) -> dict[str, Any]:
    metadata = _load_metadata(paths)
    running = bool(metadata and _pid_running(int(metadata.get("pid", -1))))
    return {
        "running": running,
        "pid": metadata.get("pid") if metadata else None,
        "root": metadata.get("root") if metadata else paths.root.as_posix(),
        "deep": metadata.get("deep") if metadata else None,
        "default_limit": metadata.get("default_limit") if metadata else None,
        "started_at": metadata.get("started_at") if metadata else None,
        "socket_path": _socket_path(paths).as_posix(),
        "log_path": _log_path(paths).as_posix(),
    }


def stop_daemon(paths: WikiPaths, *, timeout_seconds: float = 10) -> dict[str, Any]:
    status = daemon_status(paths)
    pid = status.get("pid")
    if not status["running"] or pid is None:
        _cleanup_runtime(paths)
        return {**status, "stopped": False}
    os.kill(int(pid), signal.SIGTERM)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _pid_running(int(pid)):
            _cleanup_runtime(paths)
            return {**daemon_status(paths), "stopped": True, "pid": pid}
        time.sleep(0.1)
    os.kill(int(pid), signal.SIGKILL)
    _cleanup_runtime(paths)
    return {**daemon_status(paths), "stopped": True, "pid": pid, "forced": True}


def query_daemon(paths: WikiPaths, query: str, *, limit: int = 5, deep: bool | None = None) -> dict[str, Any]:
    request: dict[str, Any] = {"query": query, "limit": limit}
    if deep is not None:
        request["deep"] = deep
    return _request(paths, request)


def query_deep_daemon_if_running(paths: WikiPaths, query: str, *, limit: int = 5) -> dict[str, Any] | None:
    status = daemon_status(paths)
    if not status.get("running") or status.get("deep") is not True:
        return None
    try:
        payload = query_daemon(paths, query, limit=limit, deep=True)
    except Exception:
        return None
    if payload.get("ok") is False:
        return None
    payload["served_by"] = "search-daemon"
    return payload


def ping_daemon(paths: WikiPaths) -> dict[str, Any]:
    return _request(paths, {"action": "ping"})


def serve_daemon(paths: WikiPaths, *, deep: bool = False, default_limit: int = 5) -> None:
    _daemon_dir(paths).mkdir(parents=True, exist_ok=True)
    socket_path = _socket_path(paths)
    if socket_path.exists():
        socket_path.unlink()
    stop = False

    def _handle_signal(signum, frame) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    config = load_config(paths)
    service = build_search_service(paths, config.qmd_collection, use_qmd=deep)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(socket_path.as_posix())
        server.listen(10)
        server.settimeout(0.2)
        while not stop:
            try:
                connection, _ = server.accept()
            except TimeoutError:
                continue
            with connection:
                payload = _handle_connection(connection, service, default_limit=default_limit, deep=deep)
                connection.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
    if socket_path.exists():
        socket_path.unlink()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--root", default=".")
    parser.add_argument("--deep", action="store_true")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)
    if not args.serve:
        parser.error("--serve is required")
    serve_daemon(WikiPaths.from_root(args.root), deep=args.deep, default_limit=args.limit)


def _handle_connection(connection: socket.socket, service, *, default_limit: int, deep: bool) -> dict[str, Any]:
    raw = b""
    while not raw.endswith(b"\n"):
        chunk = connection.recv(65536)
        if not chunk:
            break
        raw += chunk
    try:
        request = json.loads(raw.decode("utf-8"))
        if not isinstance(request, dict):
            raise ValueError("request must be a JSON object")
        action = str(request.get("action") or "search")
        if action == "ping":
            return {"ok": True, "pong": True}
        query = str(request.get("query") or "").strip()
        if not query:
            raise ValueError("request.query must not be empty")
        limit = int(request.get("limit") or default_limit)
        request_deep = bool(request.get("deep", deep))
        results, warning = service.search(query, limit=limit, deep=request_deep)
        return {
            "ok": True,
            "query": query,
            "warning": warning,
            "strategy": recommend_search_strategy(query, deep=request_deep),
            "results": [result.model_dump() for result in results],
        }
    except Exception as exc:
        return {"ok": False, "error": {"code": "search-daemon-failed", "message": str(exc)}}


def _request(paths: WikiPaths, payload: dict[str, Any]) -> dict[str, Any]:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(5)
        client.connect(_socket_path(paths).as_posix())
        client.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
        raw = b""
        while not raw.endswith(b"\n"):
            chunk = client.recv(65536)
            if not chunk:
                break
            raw += chunk
    return json.loads(raw.decode("utf-8"))


def _pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _cleanup_runtime(paths: WikiPaths) -> None:
    for path in [_socket_path(paths), _metadata_path(paths)]:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass


def _load_metadata(paths: WikiPaths) -> dict[str, Any]:
    path = _metadata_path(paths)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _daemon_dir(paths: WikiPaths) -> Path:
    return paths.state / "search-server"


def _metadata_path(paths: WikiPaths) -> Path:
    return _daemon_dir(paths) / "pid.json"


def _socket_path(paths: WikiPaths) -> Path:
    digest = hashlib.sha256(paths.root.as_posix().encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"llmw-search-{digest}.sock"


def _log_path(paths: WikiPaths) -> Path:
    return _daemon_dir(paths) / "server.log"


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    src_path = Path(__file__).resolve().parents[2]
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{current}" if current else src_path.as_posix()
    return env


if __name__ == "__main__":
    main()
