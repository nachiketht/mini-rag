from typing import TypedDict


class RetrievedChunk(TypedDict):
    chunk_id: str
    document: str
    version: str
    section: int
    section_title: str
    text: str
    distance: float


class AskResult(TypedDict):
    answer: str
    citation: str | None
    retrieved_chunks: list[RetrievedChunk]
