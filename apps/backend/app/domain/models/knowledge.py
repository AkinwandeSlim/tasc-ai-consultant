"""Knowledge base domain models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RetrievedChunk:
    """A single retrieved knowledge chunk with metadata."""

    chunk_id: str
    doc_id: str
    doc_title: str
    section: str
    content: str
    similarity: float = 0.0
    service_codes: list[str] = field(default_factory=list)
    industry_tags: list[str] = field(default_factory=list)
    doc_type: str = ""
    is_public_reference: bool = False
    is_indicative_pricing: bool = False
    last_reviewed: str = ""
    token_count: int = 0


@dataclass
class RetrievalResult:
    """Result of a retrieval operation."""

    chunks: list[RetrievedChunk] = field(default_factory=list)
    query: str = ""
    retrieval_performed: bool = False
    deferral_mode: bool = False
    latency_ms: float = 0.0
