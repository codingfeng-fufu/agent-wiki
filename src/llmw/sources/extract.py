from __future__ import annotations

from pathlib import Path


TEXT_EXTENSIONS = {".md", ".markdown", ".txt", ".text"}
PDF_EXTENSIONS = {".pdf"}


def media_type_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return "text/markdown"
    if suffix in {".txt", ".text"}:
        return "text/plain"
    if suffix == ".pdf":
        return "application/pdf"
    return "application/octet-stream"


def extract_source_text(path: Path, *, max_chars: int = 12000) -> tuple[str, str | None]:
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars], None
    if suffix in PDF_EXTENSIONS:
        try:
            from pypdf import PdfReader
        except Exception as exc:  # pragma: no cover - depends on optional install state
            return "", f"pypdf is not available: {exc}"

        chunks: list[str] = []
        try:
            reader = PdfReader(str(path))
            for page in reader.pages:
                chunks.append(page.extract_text() or "")
                if sum(len(chunk) for chunk in chunks) >= max_chars:
                    break
        except Exception as exc:
            return "", f"PDF extraction failed: {exc}"
        return "\n\n".join(chunks)[:max_chars], None
    return "", f"Unsupported source type: {path.suffix}"
