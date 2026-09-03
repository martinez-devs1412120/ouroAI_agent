"""api/main.py — FastAPI application entry point.

Run with:
    uvicorn api.main:app --reload

Notes:
- No DB connection at startup. api/database.py is lazy.
- Routers are mounted in this file. Add a new router in api/routers/
  and include it here.
- The CORS middleware is permissive (allow_origins=["*"]) because
  this is a local dev API. In production, set explicit origins.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.routers import health

app = FastAPI(
    title="StudyRAG API",
    version="0.1.0",
    description=(
        "HTTP wrapper around the StudyRAG knowledge base. "
        "See api/schemas.py for the wire format and api/database.py "
        "for the (lazy) Postgres connection."
    ),
)

# Permissive CORS for local development. Lock this down before any
# public deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)


@app.get("/", tags=["meta"])
def root() -> dict:
    """Tiny landing route so a browser hit to the host shows something
    useful instead of a 404."""
    return {
        "service": "StudyRAG API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    # Run as `python api/main.py` is supported for quick local checks.
    # The recommended way is `uvicorn api.main:app --reload`.
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
