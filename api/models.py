"""api/models.py — SQLAlchemy ORM models for the StudyRAG API.

The CLI uses an on-disk TF-IDF store (skills/studyrag/code.py). The
API is being prepared for Postgres so that multiple processes (the CLI
on a laptop, the API in a container, a future web UI) can share a
single source of truth. The schema here mirrors the CLI's data
shape: documents, chunks, and queries.

These models are NOT yet used by any route — they're the foundation
that future CRUD endpoints will sit on. Importing this module does
NOT connect to a database; only Base.metadata.create_all(engine)
would, and that's not called at startup either."""

from __future__ import annotations

import datetime as _dt

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Document(Base):
    """A user-uploaded source file: PDF, PPTX, etc. The CLI's vector
    store keeps the source filename in metadata; we keep it here so
    the API can list/delete/re-ingest documents without re-parsing
    the TF-IDF store."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    created_at: Mapped[_dt.datetime] = mapped_column(
        DateTime, default=_dt.datetime.utcnow
    )

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Chunk(Base):
    """A piece of a document. The TF-IDF vectors themselves stay in
    the on-disk store (loaded by query_studyrag); this row holds the
    metadata that goes with each chunk."""

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    chunk_id: Mapped[int] = mapped_column(Integer)  # index within the source doc
    text: Mapped[str] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)

    document: Mapped[Document] = relationship(back_populates="chunks")


class QueryLog(Base):
    """Audit trail: every query the API answers, with the question and
    the top match. Useful for understanding how the API is used, and
    for a future 'most-asked-about' view."""

    __tablename__ = "query_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    top_source: Mapped[str | None] = mapped_column(String(512), nullable=True)
    top_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[_dt.datetime] = mapped_column(
        DateTime, default=_dt.datetime.utcnow
    )
