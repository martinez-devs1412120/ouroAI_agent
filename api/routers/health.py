"""GET /health — liveness + a one-line status snapshot.

Returns 200 even when the database is unreachable. That's deliberate
for a health check: a separate `database_reachable` field reports the
DB status. Liveness probes (k8s, load balancers) care about the
process, not the data layer. If you want strict 'all systems go',
add a separate /ready endpoint that does check the DB.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.database import get_engine
from api.schemas import HealthResponse

router = APIRouter(tags=["health"])

API_VERSION = "0.1.0"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db_ok = False
    try:
        # get_engine() is lazy; this is the first place that actually
        # tries to connect. Connect-timeout 5s keeps a down DB from
        # making the health endpoint slow.
        with get_engine().connect() as _:
            db_ok = True
    except Exception:
        # Health endpoint is allowed to lie about the DB; the call
        # already raised and the response just reports False.
        db_ok = False
    return HealthResponse(status="ok", version=API_VERSION, database_reachable=db_ok)
