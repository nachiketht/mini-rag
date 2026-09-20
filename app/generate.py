import json
import re
import urllib.error
import urllib.request

from app.config import OLLAMA_HOST, OLLAMA_MODEL
from app.schemas import AskResult, Citation, PolicyChunk, RetrievedChunk

REFUSAL = "The provided policy does not answer this question."
NO_MATCH = "NONE"

SELECT_SYSTEM_PROMPT = """You match a question to policy excerpts.
Pick the one excerpt heading whose rules cover the question's topic.
A question is covered even when it uses different words than the excerpt:
a specific item belongs to the excerpt for its general category
(a specific vehicle type is ground transportation, a specific food is meals).
Pick NONE only if no excerpt covers the question's topic.
"""

SELECT_USER_PROMPT = """Policy excerpts:
{excerpts}

Question: {question}

Choices:
{choices}

Return JSON:
{{"supporting_section": "<exactly one choice>"}}
"""

ANSWER_SYSTEM_PROMPT = """Answer the question using only the policy excerpt below.
Write one or two complete sentences.
Include any dollar cap or approval requirement stated in the excerpt.
"""

ANSWER_USER_PROMPT = """Policy excerpt:
{excerpt}

Question: {question}

Return JSON:
{{"answer": "<one or two sentences>"}}
"""


def _section_label(chunk: PolicyChunk) -> str:
    return f"{chunk['section']}. {chunk['section_title']}"


def _output_chunks(retrieved_chunks: list[PolicyChunk]) -> list[RetrievedChunk]:
    return [
        {"section": _section_label(chunk), "distance": float(chunk["distance"])}
        for chunk in retrieved_chunks
    ]


def _is_refusal(answer: str) -> bool:
    return (
        answer.rstrip(".") == REFUSAL.rstrip(".")
        or "does not answer this question" in answer.lower()
    )


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9$]+", text.lower()))


def _policy_line(chunk: PolicyChunk, question: str, answer: str) -> str:
    parts = [
        part.strip()
        for part in re.split(r"\n+|(?<=[.!?])\s+", chunk["text"])
        if part.strip()
    ]
    if not parts:
        return chunk["text"].strip()
    if len(parts) == 1:
        return parts[0]
    scored = _tokens(question) | _tokens(answer)
    return max(parts, key=lambda part: len(scored & _tokens(part)))


def _citation(chunk: PolicyChunk, question: str, answer: str) -> Citation:
    return {
        "document": chunk["document"],
        "version": chunk["version"],
        "section": _section_label(chunk),
        "text": _policy_line(chunk, question, answer),
    }


def _chat(system: str, user: str, num_predict: int) -> dict:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "format": "json",
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_ctx": 2048, "num_predict": num_predict},
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


def _select_section(question: str, retrieved_chunks: list[PolicyChunk]) -> str:
    labels = [_section_label(chunk) for chunk in retrieved_chunks]
    excerpts = "\n\n".join(
        f"{label}\n{chunk['text']}"
        for chunk, label in zip(retrieved_chunks, labels, strict=True)
    )
    choices = "\n".join([*labels, NO_MATCH])
    parsed = _chat(
        SELECT_SYSTEM_PROMPT,
        SELECT_USER_PROMPT.format(
            excerpts=excerpts, question=question, choices=choices
        ),
        num_predict=64,
    )
    return str(parsed.get("supporting_section", "") or "").strip()


def _match_chunk(
    selection: str, retrieved_chunks: list[PolicyChunk]
) -> PolicyChunk | None:
    if not selection or selection.upper() == NO_MATCH:
        return None
    for chunk in retrieved_chunks:
        label = _section_label(chunk)
        if selection.lower() == label.lower() or selection == str(chunk["section"]):
            return chunk
    return None


def _answer_from(question: str, chunk: PolicyChunk) -> str:
    excerpt = f"{_section_label(chunk)}\n{chunk['text']}"
    parsed = _chat(
        ANSWER_SYSTEM_PROMPT,
        ANSWER_USER_PROMPT.format(excerpt=excerpt, question=question),
        num_predict=256,
    )
    answer = str(parsed.get("answer", "")).strip()
    if not answer or _is_refusal(answer):
        return _policy_line(chunk, question, "")
    return answer


def generate(question: str, retrieved_chunks: list[PolicyChunk]) -> AskResult:
    output_chunks = _output_chunks(retrieved_chunks)
    if not retrieved_chunks:
        return {
            "answer": REFUSAL,
            "citation": None,
            "retrieved_chunks": output_chunks,
        }

    selection = _select_section(question, retrieved_chunks)
    cited = _match_chunk(selection, retrieved_chunks)
    if cited is None:
        return {
            "answer": REFUSAL,
            "citation": None,
            "retrieved_chunks": output_chunks,
        }

    answer = _answer_from(question, cited)
    return {
        "answer": answer,
        "citation": _citation(cited, question, answer),
        "retrieved_chunks": output_chunks,
    }
