import json
import re
import urllib.error
import urllib.request

from app.config import OLLAMA_HOST, OLLAMA_MODEL
from app.schemas import AskResult, RetrievedChunk

REFUSAL = "The provided policy does not answer this question."

SYSTEM_PROMPT = """You answer employee expense-policy questions using ONLY the provided policy excerpts.

Return a JSON object with:
- "answer": string
- "citation": string or null

Citation must be exactly one of the provided section labels (for example "1. Meals"), or null.
Do not invent policy rules. Do not cite a section that was not provided.

If the excerpts do not contain enough information to answer, return:
{"answer": "The provided policy does not answer this question.", "citation": null}
"""


def _citation_label(chunk: RetrievedChunk) -> str:
    return f"{chunk['section']}. {chunk['section_title']}"


def _parse_citation(raw: object, allowed: dict[int, str]) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in {"null", "none"}:
        return None
    labels = set(allowed.values())
    if text in labels:
        return text
    match = re.match(r"^(?:section\s+|§\s*)?(\d+)", text, re.IGNORECASE)
    if match:
        return allowed.get(int(match.group(1)))
    return None


def _chat(question: str, retrieved_chunks: list[RetrievedChunk]) -> dict:
    excerpts = "\n\n".join(
        f"## {_citation_label(chunk)}\n{chunk['text']}" for chunk in retrieved_chunks
    )
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Question: {question}\n\nPolicy excerpts:\n{excerpts}",
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
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return {"answer": REFUSAL, "citation": None}

    content = body.get("message", {}).get("content", "")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {"answer": REFUSAL, "citation": None}
    if not isinstance(parsed, dict):
        return {"answer": REFUSAL, "citation": None}
    return parsed


def generate(question: str, retrieved_chunks: list[RetrievedChunk]) -> AskResult:
    """Grounded Ollama JSON. Citations come from retrieved row metadata only."""
    allowed = {chunk["section"]: _citation_label(chunk) for chunk in retrieved_chunks}
    parsed = _chat(question, retrieved_chunks)
    answer = str(parsed.get("answer", "")).strip() or REFUSAL
    citation = _parse_citation(parsed.get("citation"), allowed)

    if (
        answer.rstrip(".") == REFUSAL.rstrip(".")
        or "does not answer this question" in answer.lower()
    ):
        return {
            "answer": REFUSAL,
            "citation": None,
            "retrieved_chunks": retrieved_chunks,
        }

    return {
        "answer": answer,
        "citation": citation,
        "retrieved_chunks": retrieved_chunks,
    }
