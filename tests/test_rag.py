import pytest

from app.chunking import split
from app.config import POLICY_PATH
from app.eval import ANSWERABLE, GYM_QUESTION
from app.generate import REFUSAL, generate
from app.pgadapter import PgAdapter
from app.retrieve import search

EXPECTED_TITLES = [
    "Meals",
    "Hotels",
    "Airfare",
    "Ground Transportation",
    "Receipts",
    "Submission Deadline",
]


@pytest.fixture(scope="session")
def adapter() -> PgAdapter:
    pg = PgAdapter()
    try:
        with pg.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM policy_chunks")
                count = cur.fetchone()[0]
    except Exception as exc:
        pytest.skip(f"Postgres is not available: {exc}")
    if count != 6:
        pytest.skip("Expected 6 ingested chunks; run python -m app ingest first")
    return pg


def test_chunk_count_and_metadata() -> None:
    chunks = split(POLICY_PATH.read_text(encoding="utf-8"))
    assert len(chunks) == 6
    assert [chunk["section"] for chunk in chunks] == list(range(1, 7))
    assert [chunk["section_title"] for chunk in chunks] == EXPECTED_TITLES
    assert {chunk["version"] for chunk in chunks} == {"2.0"}
    assert chunks[0]["chunk_id"] == "employee-expense-policy:v2.0:section-1"
    assert "65" in chunks[0]["text"]
    assert "Alcohol is not reimbursable." in chunks[0]["text"]


def test_cosine_ascending_and_limit_3(adapter: PgAdapter) -> None:
    hits = search("How much can I spend on food each day?", adapter)
    assert len(hits) == 3
    distances = [hit["distance"] for hit in hits]
    assert distances == sorted(distances)
    assert all(isinstance(distance, float) for distance in distances)


@pytest.mark.parametrize("question, section, title", ANSWERABLE)
def test_expected_section_in_top3(
    adapter: PgAdapter, question: str, section: int, title: str
) -> None:
    hits = search(question, adapter)
    assert len(hits) == 3
    sections = {hit["section"] for hit in hits}
    titles = {hit["section_title"] for hit in hits}
    assert section in sections
    assert title in titles


def test_gym_refusal_has_no_citation(adapter: PgAdapter) -> None:
    hits = search(GYM_QUESTION, adapter)
    result = generate(GYM_QUESTION, hits)
    assert result["answer"] == REFUSAL
    assert result["citation"] is None
    assert len(result["retrieved_chunks"]) == 1
