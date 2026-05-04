from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class SearchResult:
    path: str
    title: str = ""
    score: float | None = None
    snippet: str = ""
    provider: str = ""

    def model_dump(self) -> dict[str, object]:
        return asdict(self)
