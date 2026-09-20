import json
from pathlib import Path

from app.db import DatabaseAdapter
from app.generate import generate
from app.retrieve import search

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "tests" / "output.json"

ANSWERABLE = [
    ("How much can I spend on food each day?", 1, "Meals"),
    ("Can I book first-class airfare?", 3, "Airfare"),
    ("Can I stay at a hotel that costs $250 per night?", 2, "Hotels"),
    ("Do I need a receipt for a $20 taxi?", 5, "Receipts"),
    ("Can I expense a limousine upgrade?", 4, "Ground Transportation"),
]
GYM_QUESTION = "Are gym memberships reimbursable?"
QUESTIONS = [question for question, _section, _title in ANSWERABLE] + [GYM_QUESTION]


def run(adapter: DatabaseAdapter, output_path: Path | None = None) -> list[dict]:
    path = output_path or OUTPUT_PATH
    results = []
    for question in QUESTIONS:
        result = generate(question, search(question, adapter))
        results.append({"question": question, **result})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return results
