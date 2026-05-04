from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from llmw.core.search_result import SearchResult
from llmw.core.settings import LLMWConfig


SourceStatus = Literal["registered", "ingested", "failed"]
PageType = Literal["source", "entity", "concept", "analysis", "output", "index", "log", "other"]
IssueSeverity = Literal["info", "warning", "error"]


class SourceRecord(BaseModel):
    source_id: str
    title: str
    path: str
    original_path: str
    media_type: str
    sha256: str
    size_bytes: int
    status: SourceStatus = "registered"
    created_at: str
    updated_at: str
    summary: str = ""
    pages: list[str] = Field(default_factory=list)
    error: str | None = None


class SourceRegistry(BaseModel):
    version: int = 1
    sources: dict[str, SourceRecord] = Field(default_factory=dict)


class WikiPageMeta(BaseModel):
    title: str
    type: PageType = "other"
    status: str = "draft"
    created: str | None = None
    updated: str | None = None
    sources: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    path: str | None = None


class HealthIssue(BaseModel):
    severity: IssueSeverity
    code: str
    message: str
    path: str | None = None


class IngestRecord(BaseModel):
    source_id: str
    pages: list[str] = Field(default_factory=list)
    note: str = ""


def normalize_page_path(path: str | Path) -> str:
    return Path(path).as_posix()
