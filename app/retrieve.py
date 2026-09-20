from app.db import DatabaseAdapter
from app.embeddings import embed_query

SEARCH_SQL = """
SELECT
    chunk_id,
    document,
    version,
    section,
    section_title,
    text,
    (embedding <=> %s::vector) AS distance
FROM policy_chunks
ORDER BY embedding <=> %s::vector ASC
LIMIT 3
"""


def search(question: str, adapter: DatabaseAdapter) -> list[dict]:
    query_vector = embed_query(question)
    with adapter.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(SEARCH_SQL, (query_vector, query_vector))
            columns = [col[0] for col in cur.description]
            rows = cur.fetchall()
    results = []
    for row in rows:
        item = dict(zip(columns, row, strict=True))
        item["distance"] = float(item["distance"])
        results.append(item)
    return results
