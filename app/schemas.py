from typing import TypedDict


class PolicyChunk(TypedDict):
    chunk_id: str
    document: str
    version: str
    section: int
    section_title: str
    text: str
    distance: float


class Citation(TypedDict):
    document: str
    version: str
    section: str
    text: str


class RetrievedChunk(TypedDict):
    section: str
    distance: float


class AskResult(TypedDict):
    answer: str
    citation: Citation | None
    retrieved_chunks: list[RetrievedChunk]
