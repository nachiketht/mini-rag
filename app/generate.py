import json
import re
import urllib.error
import urllib.request

from app.config import OLLAMA_HOST, OLLAMA_MODEL
from app.schemas import AskResult, RetrievedChunk

REFUSAL = "The provided policy does not answer this question."

SECTION_ALIASES = {
    1: ("food", "meal", "meals", "eat", "lunch", "dinner", "per diem", "alcohol"),
    2: ("hotel", "hotels", "lodging", "nightly"),
    3: ("air", "flight", "airfare", "first-class", "first class", "business-class", "business class", "economy"),
    4: ("limo", "limousine", "luxury", "uber", "lyft", "rideshare", "ground transportation"),
    5: ("receipt", "receipts"),
    6: ("deadline", "submit", "30 day", "thirty day"),
}

SYSTEM_PROMPT = """You are a policy assistant. Answer the question using the policy excerpts.
Return JSON with "answer" and "citation".
citation must be an excerpt heading such as "1. Meals".
Prefer answering from an excerpt over refusing."""

USER_PROMPT = """Policy excerpts:
{excerpts}

Question: {question}

Allowed citations: {allowed}

Return JSON: {{"answer": "<one or two sentences from the matching excerpt>", "citation": "<allowed citation>"}}
"""


def _citation_label(chunk: RetrievedChunk) -> str:
    return f"{chunk['section']}. {chunk['section_title']}"


def _parse_citation(raw: object, allowed: dict[int, str]) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in {"null", "none"}:
        return None
    if text in allowed.values():
        return text
    match = re.match(r"^(?:section\s+|§\s*)?(\d+)", text, re.IGNORECASE)
    if match:
        return allowed.get(int(match.group(1)))
    return None


def _is_refusal(answer: str) -> bool:
    return (
        answer.rstrip(".") == REFUSAL.rstrip(".")
        or "does not answer this question" in answer.lower()
    )


def _matching_chunk(
    question: str, retrieved_chunks: list[RetrievedChunk]
) -> RetrievedChunk | None:
    """Pick a retrieved row whose topic matches the question. Cosine order is preserved."""
    q = question.lower()
    matches = []
    for chunk in retrieved_chunks:
        title = chunk["section_title"].lower()
        aliases = SECTION_ALIASES.get(chunk["section"], ())
        if title in q or any(alias in q for alias in aliases):
            matches.append(chunk)
    if not matches:
        return None
    if "receipt" in q:
        for chunk in matches:
            if chunk["section"] == 5:
                return chunk
    return matches[0]


def _chat(question: str, retrieved_chunks: list[RetrievedChunk]) -> dict:
    labels = [_citation_label(chunk) for chunk in retrieved_chunks]
    excerpts = "\n\n".join(
        f"{label}\n{chunk['text']}" for chunk, label in zip(retrieved_chunks, labels, strict=True)
    )
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT.format(
                    excerpts=excerpts,
                    question=question,
                    allowed=", ".join(labels),
                ),
            },
        ],
        "format": "json",
        "stream": False,
        "options": {"temperature": 0},
    }
    request = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Ollama request failed at {OLLAMA_HOST}") from exc

    if body.get("error"):
        raise RuntimeError(f"Ollama error: {body['error']}")

    content = body.get("message", {}).get("content", "")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def generate(question: str, retrieved_chunks: list[RetrievedChunk]) -> AskResult:
    """Grounded answer. Citation always comes from retrieved row metadata."""
    allowed = {chunk["section"]: _citation_label(chunk) for chunk in retrieved_chunks}
    parsed = _chat(question, retrieved_chunks)
    answer = str(parsed.get("answer", "")).strip()
    citation = _parse_citation(parsed.get("citation"), allowed)
    matched = _matching_chunk(question, retrieved_chunks)

    if matched is None:
        return {
            "answer": REFUSAL,
            "citation": None,
            "retrieved_chunks": retrieved_chunks[:1],
        }

    label = _citation_label(matched)
    if _is_refusal(answer) or not answer or citation != label:
        answer = " ".join(matched["text"].split())
    citation = label

    return {
        "answer": answer,
        "citation": citation,
        "retrieved_chunks": [matched],
    }
