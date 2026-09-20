"""Heading-based chunking for the expense policy.

Pure function: does not read files or touch Postgres.
"""

from __future__ import annotations

import re

HEADING_RE = re.compile(r"^## (\d+)\. (.+)$", re.MULTILINE)
H1_RE = re.compile(r"^# (.+?)\s+[—–-]\s+Version\s+(\S+)", re.MULTILINE)


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def split(markdown: str) -> list[dict]:
    """Split markdown on numbered H2 headings into exactly six chunk dicts."""
    h1 = H1_RE.search(markdown)
    if not h1:
        raise ValueError("Could not parse document title and version from H1")

    document = _slug(h1.group(1))
    version = h1.group(2).strip()

    headings = list(HEADING_RE.finditer(markdown))
    if not headings:
        raise ValueError("No numbered H2 sections found")

    chunks: list[dict] = []
    for i, match in enumerate(headings):
        section = int(match.group(1))
        section_title = match.group(2).strip()
        start = match.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(markdown)
        text = markdown[start:end].strip()
        chunks.append(
            {
                "chunk_id": f"{document}:v{version}:section-{section}",
                "document": document,
                "version": version,
                "section": section,
                "section_title": section_title,
                "text": text,
            }
        )

    if len(chunks) != 6:
        raise ValueError(f"Expected 6 chunks, got {len(chunks)}")
    return chunks
