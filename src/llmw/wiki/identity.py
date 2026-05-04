from __future__ import annotations

import unicodedata


def canonical_page_key(value: str) -> str:
    """Return a stable comparison key for wiki page titles and filenames."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(char for char in normalized if _is_letter_or_number(char))


def wiki_slugify(value: str, *, fallback: str = "page") -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    parts: list[str] = []
    previous_separator = False
    for char in normalized:
        if _is_letter_or_number(char):
            parts.append(char)
            previous_separator = False
            continue
        if parts and not previous_separator:
            parts.append("-")
            previous_separator = True
    slug = "".join(parts).strip("-")
    return slug or fallback


def _is_letter_or_number(char: str) -> bool:
    return unicodedata.category(char)[0] in {"L", "N"}
