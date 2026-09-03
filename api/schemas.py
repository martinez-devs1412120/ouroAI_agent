"""api/schemas.py — Pydantic request/response models (DTOs).

Pydantic v2. The split between models.py (SQLAlchemy ORM, persistent
shape) and schemas.py (Pydantic, API surface) is the standard FastAPI
pattern — never expose the ORM directly over HTTP. Schemas are what
the wire format looks like."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    version: str = Field(examples=["0.1.0"])
    # True when the database engine has been created (first request
    # touches it; the flag catches the case where the URL is set but
    # Postgres is unreachable, so the operator sees the real status
    # without guessing).
    database_reachable: bool = False


class DocumentOut(BaseModel):
    id: int
    source: str
    created_at: str


class ChunkOut(BaseModel):
    id: int
    document_id: int
    chunk_id: int
    text: str
    score: Optional[float] = None


class AskRequest(BaseModel):
    """Shape of the future POST /ask endpoint. Not wired yet — defined
    here so the schema is reviewable before implementation."""
    question: str = Field(min_length=1, max_length=1000, examples=["definition of recursion"])
    top_k: int = Field(default=4, ge=1, le=20)


class AskResponse(BaseModel):
    question: str
    answer: str  # synthesized; for now a stub, later the model's call
    sources: list[ChunkOut]
