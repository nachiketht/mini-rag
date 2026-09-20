from pathlib import Path

from app.chunking import split
from app.config import POLICY_PATH
from app.db import DatabaseAdapter
from app.embeddings import embed_texts

UPSERT_SQL = """
INSERT INTO policy_chunks (
    chunk_id, document, version, section, section_title, text, embedding
) VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (chunk_id) DO UPDATE SET
    document = EXCLUDED.document,
    version = EXCLUDED.version,
    section = EXCLUDED.section,
    section_title = EXCLUDED.section_title,
    text = EXCLUDED.text,
    embedding = EXCLUDED.embedding
"""


def run(adapter: DatabaseAdapter, policy_path: Path | None = None) -> int:
    """Read policy.md, chunk, embed text only, upsert into policy_chunks."""
    path = policy_path or POLICY_PATH
    chunks = split(path.read_text(encoding="utf-8"))
    embeddings = embed_texts([chunk["text"] for chunk in chunks])

    with adapter.connect() as conn:
        with conn.cursor() as cur:
            for chunk, embedding in zip(chunks, embeddings, strict=True):
                cur.execute(
                    UPSERT_SQL,
                    (
                        chunk["chunk_id"],
                        chunk["document"],
                        chunk["version"],
                        chunk["section"],
                        chunk["section_title"],
                        chunk["text"],
                        embedding,
                    ),
                )
            cur.execute("SELECT COUNT(*) FROM policy_chunks")
            count = cur.fetchone()[0]
        assert count == 6, f"Expected 6 chunks in policy_chunks, got {count}"
        conn.commit()

    return count
