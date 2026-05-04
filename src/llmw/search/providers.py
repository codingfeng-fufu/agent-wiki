from __future__ import annotations

import importlib
import json
import math
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from llmw.core.markdown import extract_summary, extract_title, read_markdown
from llmw.core.fs import sha256_file
from llmw.core.paths import WikiPaths
from llmw.core.search_result import SearchResult


class SearchProvider(ABC):
    name: str

    @abstractmethod
    def available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str, *, limit: int = 10, deep: bool = False) -> list[SearchResult]:
        raise NotImplementedError


class QmdSearchProvider(SearchProvider):
    name = "qmd"

    def __init__(
        self,
        paths: WikiPaths,
        collection: str,
        executable: str | None = None,
        timeout_seconds: float | None = None,
    ):
        self.paths = paths
        self.collection = collection
        self.executable = executable or shutil.which("qmd") or _sibling_executable("qmd")
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else _qmd_timeout_seconds()
        self._qmd_collection = None

    def available(self) -> bool:
        if os.environ.get("LLMW_DISABLE_QMD") == "1":
            return False
        return self._sdk_available() or bool(self.executable)

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        if not self.executable:
            raise RuntimeError("qmd executable not found")
        self.paths.qmd_db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            return subprocess.run(
                [self.executable, "--db-path", str(self.paths.qmd_db_path), *args],
                cwd=self.paths.root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            command = " ".join(args[:3])
            raise RuntimeError(f"qmd command timed out after {self.timeout_seconds:g}s: {command}") from exc

    def ensure_index(self) -> None:
        manifest = self._load_manifest()
        current: dict[str, str] = {}
        changed: list[Path] = []

        if self.paths.wiki.exists():
            for page in sorted(self.paths.wiki.rglob("*.md")):
                if _is_special_page(page, self.paths):
                    continue
                document_id = _relative(page, self.paths.root)
                digest = sha256_file(page)
                current[document_id] = digest
                if manifest.get(document_id) != digest:
                    changed.append(page)

        if self._sdk_available():
            self._ensure_index_sdk(current, changed, manifest)
            return

        self._ensure_index_cli(current, changed, manifest)

    def search(self, query: str, *, limit: int = 10, deep: bool = False) -> list[SearchResult]:
        self.ensure_index()
        if self._sdk_available():
            return self._search_sdk(query, limit=limit, deep=deep)
        return self._search_cli(query, limit=limit, deep=deep)

    def _ensure_index_sdk(self, current: dict[str, str], changed: list[Path], manifest: dict[str, str]) -> None:
        collection = self._collection_sdk()
        removed = set(manifest) - set(current)
        if hasattr(collection, "list_documents"):
            removed.update(set(collection.list_documents()) - set(current))
        for document_id in removed:
            _ignore_missing_document(lambda document_id=document_id: collection.delete_document(document_id))

        documents: list[dict] = []
        for page in changed:
            document_id = _relative(page, self.paths.root)
            _ignore_missing_document(lambda document_id=document_id: collection.delete_document(document_id))
            metadata, body = read_markdown(page)
            documents.append(
                {
                    "document_id": document_id,
                    "markdown": page.read_text(encoding="utf-8", errors="replace"),
                    "metadata": {
                        "path": document_id,
                        "title": extract_title(page, body, metadata),
                    },
                }
            )
        if documents:
            collection.add_documents(documents)

        if removed or changed or not self.paths.qmd_manifest_path.exists():
            self._save_manifest(current)

    def _ensure_index_cli(self, current: dict[str, str], changed: list[Path], manifest: dict[str, str]) -> None:
        removed = sorted(set(manifest) - set(current))
        for document_id in removed:
            self._run(["document", "delete", "--collection", self.collection, "--document-id", document_id])

        for page in changed:
            document_id = _relative(page, self.paths.root)
            self._run(["document", "delete", "--collection", self.collection, "--document-id", document_id])
            add = self._run(
                [
                    "document",
                    "add",
                    "--collection",
                    self.collection,
                    "--document-id",
                    document_id,
                    "--markdown-file",
                    document_id,
                ]
            )
            if add.returncode != 0:
                raise RuntimeError(add.stderr.strip() or add.stdout.strip() or f"qmd document add failed: {document_id}")

        if removed or changed or not self.paths.qmd_manifest_path.exists():
            self._save_manifest(current)

    def _search_sdk(self, query: str, *, limit: int, deep: bool) -> list[SearchResult]:
        top_k = max(limit * 3, limit)
        rerank = bool(deep and os.environ.get("LLMW_QMD_RERANK") == "1")
        search_query = _qmd_safe_query(query)
        try:
            raw_results = self._collection_sdk().hybrid_search(search_query, top_k=top_k, rerank=rerank)
        except sqlite3.OperationalError:
            if search_query == query:
                raise
            raw_results = self._collection_sdk().hybrid_search(query, top_k=top_k, rerank=rerank)
        return _parse_qmd_sdk_results(
            raw_results,
            provider=self.name,
            query=query,
            limit=limit,
        )

    def _search_cli(self, query: str, *, limit: int, deep: bool) -> list[SearchResult]:
        search_query = _qmd_safe_query(query)
        args = ["search", "--collection", self.collection, "--query", search_query, "--top-k", str(limit)]
        if deep and os.environ.get("LLMW_QMD_RERANK") == "1":
            args.append("--rerank")
        result = self._run(args)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "qmd search failed")
        return _parse_qmd_json(result.stdout, provider=self.name)

    def _sdk_available(self) -> bool:
        if os.environ.get("LLMW_QMD_BACKEND") == "cli":
            return False
        try:
            importlib.import_module("qmd")
        except ImportError:
            return False
        return True

    def _collection_sdk(self):
        if self._qmd_collection is None:
            self.paths.qmd_db_path.parent.mkdir(parents=True, exist_ok=True)
            qmd = importlib.import_module("qmd")
            client = qmd.connect(
                self.paths.qmd_db_path,
                config_overrides={"embedding": {"batch_size": 16}},
            )
            self._qmd_collection = client.collection(self.collection)
        return self._qmd_collection

    def _load_manifest(self) -> dict[str, str]:
        if not self.paths.qmd_manifest_path.exists():
            return {}
        try:
            data = json.loads(self.paths.qmd_manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(key): str(value) for key, value in data.items()}

    def _save_manifest(self, manifest: dict[str, str]) -> None:
        self.paths.qmd_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.paths.qmd_manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


class RgSearchProvider(SearchProvider):
    name = "rg"

    def __init__(self, paths: WikiPaths, executable: str | None = None, *, include_special: bool = False):
        self.paths = paths
        self.executable = executable if executable is not None else shutil.which("rg")
        self.include_special = include_special
        self._python_documents: list[tuple[Path, dict, str]] | None = None
        self._rank_index: _RankIndex | None = None

    def available(self) -> bool:
        return bool(self.executable) or self.paths.wiki.exists()

    def search(self, query: str, *, limit: int = 10, deep: bool = False) -> list[SearchResult]:
        if self.executable and not _prefer_python_scan(query):
            return self._search_rg(query, limit=limit)
        return self._search_python(query, limit=limit)

    def _search_rg(self, query: str, *, limit: int) -> list[SearchResult]:
        candidate_limit = max(limit * 5, limit)
        result = subprocess.run(
            [self.executable or "rg", "-n", "--json", query, str(self.paths.wiki)],
            cwd=self.paths.root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode not in {0, 1}:
            raise RuntimeError(result.stderr.strip() or "rg search failed")

        hits: list[SearchResult] = []
        seen: set[str] = set()
        for line in result.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "match":
                continue
            data = event.get("data") or {}
            path = Path(data.get("path", {}).get("text", ""))
            if self._is_special_page(path):
                continue
            rel = _relative(path, self.paths.root)
            if rel in seen:
                continue
            seen.add(rel)
            snippet = (data.get("lines") or {}).get("text", "").strip()
            hits.append(SearchResult(path=rel, title=path.stem, snippet=snippet, provider=self.name))
            if len(hits) >= candidate_limit:
                break
        if not hits and len(_query_terms(query)) > 1:
            return self._search_python(query, limit=limit)
        return _rerank_results(query, hits, limit=limit)

    def _search_python(self, query: str, *, limit: int) -> list[SearchResult]:
        return search_rank_index(self._python_rank_index(), query, limit=limit)

    def _python_scan_documents(self) -> list[tuple[Path, dict, str]]:
        if self._python_documents is None:
            documents: list[tuple[Path, dict, str]] = []
            for path in sorted(self.paths.wiki.rglob("*.md")) if self.paths.wiki.exists() else []:
                if self._is_special_page(path):
                    continue
                metadata, body = read_markdown(path)
                documents.append((path, metadata, body))
            self._python_documents = documents
        return self._python_documents

    def _is_special_page(self, path: Path) -> bool:
        if self.include_special:
            return False
        special = {self.paths.index_path, self.paths.log_path}
        if path in special:
            return True
        special_resolved = {self.paths.index_path.resolve(), self.paths.log_path.resolve()}
        return path.resolve() in special_resolved

    def _python_rank_index(self) -> "_RankIndex":
        if self._rank_index is None:
            manifest = self._python_cache_manifest()
            self._rank_index = self._load_rank_index_cache(manifest)
            if self._rank_index is None:
                self._rank_index = _build_rank_index(self._python_scan_documents(), root=self.paths.root)
                self._save_rank_index_cache(manifest, self._rank_index)
        return self._rank_index

    def _python_cache_manifest(self) -> dict[str, dict[str, int]]:
        manifest: dict[str, dict[str, int]] = {}
        for path in sorted(self.paths.wiki.rglob("*.md")) if self.paths.wiki.exists() else []:
            if self._is_special_page(path):
                continue
            stat = path.stat()
            manifest[_relative(path, self.paths.root)] = {
                "mtime_ns": stat.st_mtime_ns,
                "size": stat.st_size,
            }
        return manifest

    def _rank_index_cache_path(self) -> Path:
        suffix = "with-special" if self.include_special else "content"
        return self.paths.state / "cache" / f"python-rank-{suffix}.json"

    def _load_rank_index_cache(self, manifest: dict[str, dict[str, int]]) -> "_RankIndex | None":
        if os.environ.get("LLMW_DISABLE_SEARCH_CACHE") == "1":
            return None
        cache_path = self._rank_index_cache_path()
        if not cache_path.exists():
            return None
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        if data.get("version") != _RANK_INDEX_CACHE_VERSION:
            return None
        if data.get("include_special") != self.include_special:
            return None
        if data.get("manifest") != manifest:
            return None
        return _rank_index_from_cache_payload(data)

    def _save_rank_index_cache(self, manifest: dict[str, dict[str, int]], index: "_RankIndex") -> None:
        if os.environ.get("LLMW_DISABLE_SEARCH_CACHE") == "1":
            return
        cache_path = self._rank_index_cache_path()
        payload = _rank_index_cache_payload(index, manifest=manifest, include_special=self.include_special)
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        except OSError:
            return


class SearchService:
    def __init__(self, primary: SearchProvider, fallback: SearchProvider):
        self.primary = primary
        self.fallback = fallback

    def search(self, query: str, *, limit: int = 10, deep: bool = False) -> tuple[list[SearchResult], str | None]:
        warning: str | None = None
        if self.primary.available():
            try:
                return self.primary.search(query, limit=limit, deep=deep), None
            except Exception as exc:
                warning = f"{self.primary.name} failed; fell back to {self.fallback.name}: {exc}"
        else:
            warning = f"{self.primary.name} is not available; fell back to {self.fallback.name}."
        return self.fallback.search(query, limit=limit, deep=deep), warning


def build_search_service(paths: WikiPaths, collection: str, *, use_qmd: bool = False) -> SearchService:
    fallback = RgSearchProvider(paths)
    if not use_qmd:
        return SearchService(fallback, fallback)
    return SearchService(QmdSearchProvider(paths, collection), fallback)


def search_python_documents(
    documents: list[tuple[Path, dict, str]],
    query: str,
    *,
    root: Path,
    limit: int,
) -> list[SearchResult]:
    return search_rank_index(_build_rank_index(documents, root=root), query, limit=limit)


def search_rank_index(index: "_RankIndex", query: str, *, limit: int) -> list[SearchResult]:
    query_terms = _query_terms(query)
    if not query_terms:
        return []
    phrase = query.strip().lower()
    scored: list[SearchResult] = []

    for document in index.documents:
        score = _score_document(document, query_terms, phrase, index.stats)
        if score <= 0:
            continue
        scored.append(
            SearchResult(
                path=document.path,
                title=document.title,
                score=score,
                snippet=document.summary,
                provider="python-scan",
            )
        )
    return _rerank_results(query, scored, limit=limit)


def recommend_search_strategy(query: str, *, deep: bool = False) -> dict[str, object]:
    terms = _query_terms(query)
    needs_high_recall = _needs_high_recall(query, terms)
    if deep:
        return {
            "mode": "deep",
            "deep_recommended": True,
            "reason": "Using qmd hybrid search for higher recall. For repeated calls, prefer `llmw search-server --deep`.",
            "fast_command": f"llmw search {json.dumps(query, ensure_ascii=False)} --json",
            "deep_command": f"llmw search {json.dumps(query, ensure_ascii=False)} --deep --json",
            "server_command": "llmw search-server --deep",
        }
    return {
        "mode": "fast",
        "deep_recommended": needs_high_recall,
        "reason": (
            "Fast rg/Python search is the default. Use `--deep` or `search-server --deep` when recall matters across multiple concepts."
            if needs_high_recall
            else "Fast rg/Python search is appropriate for exact titles, source lookup, and low-latency agent calls."
        ),
        "fast_command": f"llmw search {json.dumps(query, ensure_ascii=False)} --json",
        "deep_command": f"llmw search {json.dumps(query, ensure_ascii=False)} --deep --json",
        "server_command": "llmw search-server --deep",
    }


def _parse_qmd_sdk_results(raw_results, *, provider: str, query: str, limit: int) -> list[SearchResult]:
    results: list[SearchResult] = []
    seen: set[str] = set()
    for item in raw_results:
        chunk_ref = getattr(item, "chunk_ref", None)
        metadata = getattr(item, "metadata", None) or {}
        metadata_path = metadata.get("path") if isinstance(metadata, dict) else None
        path = metadata_path or getattr(chunk_ref, "document_id", "") or getattr(item, "document_id", "")
        if not path or path in seen:
            continue
        seen.add(str(path))
        title = metadata.get("title") if isinstance(metadata, dict) else None
        results.append(
            SearchResult(
                path=str(path),
                title=str(title or Path(str(path)).stem),
                snippet=str(getattr(item, "text", "") or ""),
                score=getattr(item, "score", None),
                provider=provider,
            )
        )
        if len(results) >= max(limit * 3, limit):
            break
    return results[:limit]


def _parse_qmd_json(raw: str, *, provider: str) -> list[SearchResult]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return _parse_qmd_lines(raw, provider=provider)

    if isinstance(parsed, dict):
        candidates = parsed.get("results") or parsed.get("items") or parsed.get("documents") or []
    elif isinstance(parsed, list):
        candidates = parsed
    else:
        candidates = []

    results: list[SearchResult] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        chunk_ref = item.get("chunk_ref") if isinstance(item.get("chunk_ref"), dict) else {}
        path = (
            item.get("filepath")
            or item.get("path")
            or item.get("file")
            or item.get("uri")
            or chunk_ref.get("document_id")
            or ""
        )
        title = item.get("title") or Path(str(path)).stem
        snippet = item.get("snippet") or item.get("text") or item.get("content") or item.get("summary") or ""
        score = item.get("score")
        results.append(SearchResult(path=str(path), title=str(title), snippet=str(snippet), score=score, provider=provider))
    return results


def _parse_qmd_lines(raw: str, *, provider: str) -> list[SearchResult]:
    results: list[SearchResult] = []
    for line in raw.splitlines():
        text = line.strip()
        if not text:
            continue
        results.append(SearchResult(path=text, title=Path(text).stem, provider=provider))
    return results


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        pass
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _is_special_page(path: Path, paths: WikiPaths) -> bool:
    special = {paths.index_path.resolve(), paths.log_path.resolve()}
    return path.resolve() in special


def _ignore_missing_document(operation) -> None:
    try:
        operation()
    except Exception as exc:
        message = str(exc).lower()
        if "not found" not in message and "missing" not in message and "no such" not in message:
            raise


def _rerank_results(query: str, results: list[SearchResult], *, limit: int) -> list[SearchResult]:
    terms = set(_query_terms(query))
    phrase = query.strip().lower()

    def rank_key(result: SearchResult) -> tuple[float, str]:
        title = result.title.lower()
        path = result.path.lower()
        snippet = result.snippet.lower()
        title_terms = set(_query_terms(title.replace("-", " ")))
        path_terms = set(_query_terms(path.replace("/", " ").replace("-", " ")))
        overlap = len(terms & title_terms)
        path_overlap = len(terms & path_terms)
        score = float(result.score or 0.0)
        score += overlap * 6
        score += path_overlap * 3
        score += sum(snippet.count(term) for term in terms) * 0.2
        if phrase and phrase in title:
            score += 40
        if phrase and phrase in path:
            score += 20
        if "/concepts/" in path:
            score += 0.75
        return (-score, result.path.lower())

    return sorted(results, key=rank_key)[:limit]


def _needs_high_recall(query: str, terms: list[str]) -> bool:
    lowered = query.lower()
    if "?" in query or len(terms) >= 6:
        return True
    triggers = [
        "compare",
        "difference",
        "how should",
        "how to",
        "what helps",
        "which pattern",
        "coordinate",
        "debug",
        "recover",
        "reduce",
        "risk",
        "across",
    ]
    return any(trigger in lowered for trigger in triggers)


def _prefer_python_scan(query: str) -> bool:
    terms = _query_terms(query)
    return len(terms) > 1 or bool(re.search(r"[?¿!]", query))


def _sibling_executable(name: str) -> str | None:
    suffixes = [".exe"] if sys.platform == "win32" else [""]
    for suffix in suffixes:
        candidate = Path(sys.executable).with_name(f"{name}{suffix}")
    if candidate.exists():
        return str(candidate)
    return None


def _qmd_timeout_seconds() -> float:
    raw = os.environ.get("LLMW_QMD_TIMEOUT_SECONDS", "20").strip()
    try:
        value = float(raw)
    except ValueError:
        return 20
    return max(value, 1)


def _qmd_safe_query(query: str) -> str:
    cleaned = re.sub(r"[^\w\s\"'-]+", " ", query, flags=re.UNICODE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or query


def _query_terms(query: str) -> list[str]:
    terms = _tokenize(query)
    filtered = [term for term in terms if term not in _STOPWORDS]
    return filtered or terms


@dataclass(frozen=True)
class _RankDocument:
    path: str
    title: str
    summary: str
    fields: dict[str, list[str]]
    field_counts: dict[str, Counter[str]]
    unique_terms: set[str]


@dataclass(frozen=True)
class _RankIndex:
    documents: list[_RankDocument]
    stats: "_CorpusStats"


@dataclass(frozen=True)
class _CorpusStats:
    documents: int
    document_frequency: Counter[str]
    average_lengths: dict[str, float]


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "before",
    "by",
    "can",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "llmw",
    "of",
    "or",
    "page",
    "pages",
    "should",
    "that",
    "the",
    "then",
    "to",
    "use",
    "uses",
    "using",
    "what",
    "when",
    "where",
    "which",
    "why",
    "wiki",
    "with",
}


_FIELD_WEIGHTS = {
    "title": 9.0,
    "path": 4.5,
    "summary": 2.5,
    "body": 1.0,
}

_RANK_INDEX_CACHE_VERSION = 2


def _build_rank_index(documents: list[tuple[Path, dict, str]], *, root: Path) -> _RankIndex:
    ranked_documents = [_build_rank_document(path, metadata, body, root=root) for path, metadata, body in documents]
    return _RankIndex(documents=ranked_documents, stats=_build_corpus_stats(ranked_documents))


def _build_rank_document(path: Path, metadata: dict, body: str, *, root: Path) -> _RankDocument:
    rel_path = _relative(path, root)
    title = extract_title(path, body, metadata)
    summary = extract_summary(body, max_chars=220)
    path_text = rel_path.replace("/", " ").replace("-", " ").replace("_", " ")
    fields = {
        "title": _tokenize(title),
        "path": _tokenize(path_text),
        "summary": _tokenize(summary),
        "body": _tokenize(body),
    }
    field_counts = {name: Counter(tokens) for name, tokens in fields.items()}
    unique_terms = set().union(*(set(tokens) for tokens in fields.values()))
    return _RankDocument(
        path=rel_path,
        title=title,
        summary=summary,
        fields=fields,
        field_counts=field_counts,
        unique_terms=unique_terms,
    )


def _build_corpus_stats(documents: list[_RankDocument]) -> _CorpusStats:
    document_frequency: Counter[str] = Counter()
    for document in documents:
        document_frequency.update(document.unique_terms)
    average_lengths: dict[str, float] = {}
    for field in _FIELD_WEIGHTS:
        lengths = [len(document.fields[field]) for document in documents]
        average_lengths[field] = sum(lengths) / len(lengths) if lengths else 0.0
    return _CorpusStats(
        documents=len(documents),
        document_frequency=document_frequency,
        average_lengths=average_lengths,
    )


def _rank_index_cache_payload(
    index: _RankIndex,
    *,
    manifest: dict[str, dict[str, int]],
    include_special: bool,
) -> dict[str, object]:
    return {
        "version": _RANK_INDEX_CACHE_VERSION,
        "include_special": include_special,
        "manifest": manifest,
        "stats": {
            "documents": index.stats.documents,
            "document_frequency": dict(index.stats.document_frequency),
            "average_lengths": index.stats.average_lengths,
        },
        "documents": [
            {
                "path": document.path,
                "title": document.title,
                "summary": document.summary,
                "fields": document.fields,
                "field_counts": {
                    name: dict(counts) for name, counts in document.field_counts.items()
                },
                "unique_terms": sorted(document.unique_terms),
            }
            for document in index.documents
        ],
    }


def _rank_index_from_cache_payload(data: dict) -> _RankIndex | None:
    try:
        stats_data = data["stats"]
        document_items = data["documents"]
    except KeyError:
        return None
    if not isinstance(stats_data, dict) or not isinstance(document_items, list):
        return None
    try:
        stats = _CorpusStats(
            documents=int(stats_data["documents"]),
            document_frequency=Counter({str(k): int(v) for k, v in stats_data["document_frequency"].items()}),
            average_lengths={str(k): float(v) for k, v in stats_data["average_lengths"].items()},
        )
        documents = [
            _RankDocument(
                path=str(item["path"]),
                title=str(item["title"]),
                summary=str(item["summary"]),
                fields={str(k): [str(term) for term in v] for k, v in item["fields"].items()},
                field_counts={
                    str(k): Counter({str(term): int(count) for term, count in v.items()})
                    for k, v in item["field_counts"].items()
                },
                unique_terms={str(term) for term in item["unique_terms"]},
            )
            for item in document_items
            if isinstance(item, dict)
        ]
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
    return _RankIndex(documents=documents, stats=stats)


def _score_document(document: _RankDocument, query_terms: list[str], phrase: str, stats: _CorpusStats) -> float:
    query_counts = Counter(query_terms)
    distinct_terms = set(query_terms)
    score = 0.0
    matched_terms: set[str] = set()
    matched_fields = 0

    for field, weight in _FIELD_WEIGHTS.items():
        field_score = 0.0
        counts = document.field_counts[field]
        for term, query_count in query_counts.items():
            frequency = counts.get(term, 0)
            if not frequency:
                continue
            matched_terms.add(term)
            field_score += _bm25_term_score(
                term,
                frequency=frequency,
                query_count=query_count,
                field_length=len(document.fields[field]),
                average_length=stats.average_lengths[field],
                stats=stats,
            )
        if field_score:
            matched_fields += 1
            score += field_score * weight

    if not matched_terms:
        return 0.0

    coverage = len(matched_terms) / max(len(distinct_terms), 1)
    score += coverage * 5.0
    if coverage >= 0.75:
        score += 3.0
    score += matched_fields * 0.6
    score += _phrase_boost(document, phrase)
    if "/concepts/" in document.path:
        score += 0.75
    return score


def _bm25_term_score(
    term: str,
    *,
    frequency: int,
    query_count: int,
    field_length: int,
    average_length: float,
    stats: _CorpusStats,
) -> float:
    k1 = 1.2
    b = 0.75
    document_count = max(stats.documents, 1)
    df = stats.document_frequency.get(term, 0)
    idf = math.log(1 + (document_count - df + 0.5) / (df + 0.5))
    normalized_length = field_length / average_length if average_length else 1.0
    denominator = frequency + k1 * (1 - b + b * normalized_length)
    return idf * ((frequency * (k1 + 1)) / denominator) * query_count


def _phrase_boost(document: _RankDocument, phrase: str) -> float:
    if not phrase:
        return 0.0
    score = 0.0
    title = document.title.lower()
    path = document.path.lower()
    summary = document.summary.lower()
    if phrase in title:
        score += 35.0
    if phrase in path:
        score += 20.0
    if phrase in summary:
        score += 8.0
    return score


def _tokenize(text: str) -> list[str]:
    expanded = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    expanded = expanded.replace("-", " ").replace("_", " ")
    normalized: list[str] = []
    for term in re.findall(r"[\w]+", expanded, flags=re.UNICODE):
        if not term.strip():
            continue
        normalized.extend(_tokenize_term(term))
    return normalized


def _tokenize_term(term: str) -> list[str]:
    pieces: list[str] = []
    for segment in _split_cjk_segments(term.lower()):
        if _is_cjk_text(segment):
            pieces.extend(_cjk_ngrams(segment))
            continue
        value = _normalize_term(segment)
        if value:
            pieces.append(value)
    return pieces


def _split_cjk_segments(term: str) -> list[str]:
    segments: list[str] = []
    current: list[str] = []
    current_is_cjk: bool | None = None
    for char in term:
        is_cjk = _is_cjk_char(char)
        if current and is_cjk != current_is_cjk:
            segments.append("".join(current))
            current = []
        current.append(char)
        current_is_cjk = is_cjk
    if current:
        segments.append("".join(current))
    return segments


def _cjk_ngrams(value: str) -> list[str]:
    if len(value) <= 3:
        return [value]
    grams: list[str] = []
    for size in (2, 3):
        grams.extend(value[index : index + size] for index in range(len(value) - size + 1))
    return grams


def _is_cjk_text(value: str) -> bool:
    return bool(value) and all(_is_cjk_char(char) for char in value)


def _is_cjk_char(char: str) -> bool:
    code = ord(char)
    return (
        0x3400 <= code <= 0x4DBF
        or 0x4E00 <= code <= 0x9FFF
        or 0xF900 <= code <= 0xFAFF
        or 0x20000 <= code <= 0x2A6DF
        or 0x2A700 <= code <= 0x2B73F
        or 0x2B740 <= code <= 0x2B81F
        or 0x2B820 <= code <= 0x2CEAF
    )


def _normalize_term(term: str) -> str:
    if len(term) <= 3:
        return term
    for suffix in ("ization", "ations", "ation", "ments", "ment", "ness", "able", "ible"):
        if term.endswith(suffix) and len(term) > len(suffix) + 3:
            return term[: -len(suffix)]
    for suffix in ("ing", "ers", "ies", "ied", "ed", "es", "s"):
        if term.endswith(suffix) and len(term) > len(suffix) + 3:
            if suffix == "ies":
                return term[: -len(suffix)] + "y"
            if suffix == "ied":
                return term[: -len(suffix)] + "y"
            return term[: -len(suffix)]
    return term
