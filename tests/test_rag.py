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
    assert {chunk["document"] for chunk in chunks} == {"Employee Expense Policy"}
    assert chunks[0]["chunk_id"] == "expense-policy:v2.0:section-1"
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
    assert len(result["retrieved_chunks"]) == 3
    assert all(
        set(chunk) == {"section", "distance"} and isinstance(chunk["distance"], float)
        for chunk in result["retrieved_chunks"]
    )


def test_citation_comes_from_retrieved_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    hits = [
        {
            "chunk_id": "expense-policy:v2.0:section-1",
            "document": "Employee Expense Policy",
            "version": "2.0",
            "section": 1,
            "section_title": "Meals",
            "text": "Employees may claim up to $65 per day for meals.",
            "distance": 0.08,
        },
        {
            "chunk_id": "expense-policy:v2.0:section-2",
            "document": "Employee Expense Policy",
            "version": "2.0",
            "section": 2,
            "section_title": "Hotels",
            "text": "Hotels are reimbursable up to $225 per night.",
            "distance": 0.4,
        },
        {
            "chunk_id": "expense-policy:v2.0:section-5",
            "document": "Employee Expense Policy",
            "version": "2.0",
            "section": 5,
            "section_title": "Receipts",
            "text": "Receipts are required for individual expenses of $25 or more.",
            "distance": 0.5,
        },
    ]
    monkeypatch.setattr(
        "app.generate._select_section", lambda _question, _chunks: "1. Meals"
    )
    monkeypatch.setattr(
        "app.generate._answer_from",
        lambda _question, _chunk: "Employees may claim up to $65 per day for meals.",
    )
    result = generate("How much can I spend on food each day?", hits)
    assert result["citation"] == {
        "document": "Employee Expense Policy",
        "version": "2.0",
        "section": "1. Meals",
        "text": "Employees may claim up to $65 per day for meals.",
    }
    assert result["retrieved_chunks"] == [
        {"section": "1. Meals", "distance": 0.08},
        {"section": "2. Hotels", "distance": 0.4},
        {"section": "5. Receipts", "distance": 0.5},
    ]


def test_citation_follows_selected_section_not_distance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hits = [
        {
            "chunk_id": "expense-policy:v2.0:section-5",
            "document": "Employee Expense Policy",
            "version": "2.0",
            "section": 5,
            "section_title": "Receipts",
            "text": "Receipts are required for individual expenses of $25 or more.",
            "distance": 0.38,
        },
        {
            "chunk_id": "expense-policy:v2.0:section-4",
            "document": "Employee Expense Policy",
            "version": "2.0",
            "section": 4,
            "section_title": "Ground Transportation",
            "text": "Taxi, rideshare, train, and public-transit expenses are reimbursable.\nLuxury vehicle upgrades are not reimbursable.",
            "distance": 0.65,
        },
    ]
    monkeypatch.setattr(
        "app.generate._select_section",
        lambda _question, _chunks: "4. Ground Transportation",
    )
    monkeypatch.setattr(
        "app.generate._answer_from",
        lambda _question, _chunk: "No. Luxury vehicle upgrades are not reimbursable.",
    )
    result = generate("Can I claim a limousine upgrade?", hits)
    assert result["answer"] == "No. Luxury vehicle upgrades are not reimbursable."
    assert result["citation"] == {
        "document": "Employee Expense Policy",
        "version": "2.0",
        "section": "4. Ground Transportation",
        "text": "Luxury vehicle upgrades are not reimbursable.",
    }


@pytest.mark.parametrize("selection", ["NONE", "9", ""])
def test_unmatched_selection_refuses(
    monkeypatch: pytest.MonkeyPatch, selection: str
) -> None:
    hits = [
        {
            "chunk_id": "expense-policy:v2.0:section-6",
            "document": "Employee Expense Policy",
            "version": "2.0",
            "section": 6,
            "section_title": "Submission Deadline",
            "text": "Expense reports must be submitted within 30 days after travel ends.",
            "distance": 0.9,
        }
    ]
    monkeypatch.setattr(
        "app.generate._select_section", lambda _question, _chunks: selection
    )
    result = generate("Does the company reimburse gym memberships?", hits)
    assert result["answer"] == REFUSAL
    assert result["citation"] is None
