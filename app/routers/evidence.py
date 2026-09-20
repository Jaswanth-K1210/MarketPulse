"""Liveness of every data source, in one call.

The point of this endpoint is that a dead feed becomes visible in a glance
rather than by someone noticing a suspiciously round zero on a dashboard.
"""
import time

from fastapi import APIRouter

from app.services.evidence import snapshot

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@router.get("/health")
async def evidence_health() -> dict:
    now = time.time()
    sources = {}
    for source_id, result in snapshot().items():
        sources[source_id] = {
            "available": result.available,
            "error": result.error,
            "as_of": result.as_of,
            "fetched_at": result.fetched_at,
            "age_seconds": result.age(now),
            "origin": result.origin,
        }
    return {
        "sources": sources,
        "live_count": sum(1 for s in sources.values() if s["available"]),
        "total_count": len(sources),
    }
