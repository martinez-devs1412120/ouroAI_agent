"""api/ — a FastAPI backend for StudyRAG.

This package is fully incremental: it lives alongside the existing CLI
and Streamlit UI without modifying either. The CLI is the primary
client; this API is a thin HTTP wrapper for browser/mobile/integration
use cases. They share the same data layer (the on-disk TF-IDF store
in studpart/data/chroma_db) and the same query code
(skills/studyrag/code.py) — one source of truth, two entry points.

Run with:
    uvicorn api.main:app --reload
"""
