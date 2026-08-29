"""
User profile CRUD in MongoDB Atlas.
Each document is the single source of truth for a user's identity,
portfolio, watchlist, preferences, and risk profile.
Falls back to SQLite auth_service when MongoDB is unavailable.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from app.db.mongo import is_available, users_col

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Schema ───────────────────────────────────────────────────────────────────

def _new_user_doc(
    username: str,
    password_hash: str,
    email: Optional[str] = None,
    google_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "google_id": google_id,
        # Portfolio & watchlist stored directly on the user document
        "portfolio": [],        # [{"ticker": "AAPL", "quantity": 10, "avg_price": 150.0}]
        "watchlist": [],        # ["AAPL", "NVDA", ...]
        # Risk & preference profile
        "risk_tolerance": "moderate",   # low | moderate | high
        "preferred_sectors": [],        # ["technology", "energy"]
        "alert_threshold": 0.05,        # minimum impact % to surface an alert
        # Usage stats (incremented on each analysis run)
        "analysis_count": 0,
        "last_analysis_at": None,
        # Timestamps
        "created_at": _now(),
        "last_login": _now(),
    }


# ── Writes ────────────────────────────────────────────────────────────────────

async def create_user(
    username: str,
    password_hash: str,
    email: Optional[str] = None,
    google_id: Optional[str] = None,
) -> Dict[str, Any]:
    col = users_col()
    doc = _new_user_doc(username, password_hash, email, google_id)
    result = await col.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return _serialize(doc)


async def get_by_username(username: str) -> Optional[Dict[str, Any]]:
    col = users_col()
    doc = await col.find_one({"username": username})
    return _serialize(doc) if doc else None


async def get_by_email(email: str) -> Optional[Dict[str, Any]]:
    col = users_col()
    doc = await col.find_one({"email": email})
    return _serialize(doc) if doc else None


async def get_by_google_id(google_id: str) -> Optional[Dict[str, Any]]:
    col = users_col()
    doc = await col.find_one({"google_id": google_id})
    return _serialize(doc) if doc else None


async def update_last_login(username: str):
    col = users_col()
    await col.update_one({"username": username}, {"$set": {"last_login": _now()}})


async def update_portfolio(username: str, holdings: List[Dict]) -> bool:
    """Replace the user's portfolio array with new holdings list."""
    col = users_col()
    result = await col.update_one(
        {"username": username},
        {"$set": {"portfolio": holdings}}
    )
    return result.modified_count > 0


async def update_watchlist(username: str, tickers: List[str]) -> bool:
    col = users_col()
    result = await col.update_one(
        {"username": username},
        {"$addToSet": {"watchlist": {"$each": tickers}}}
    )
    return result.modified_count > 0


async def update_risk_profile(
    username: str,
    risk_tolerance: Optional[str] = None,
    preferred_sectors: Optional[List[str]] = None,
    alert_threshold: Optional[float] = None,
) -> bool:
    updates: Dict[str, Any] = {}
    if risk_tolerance:
        updates["risk_tolerance"] = risk_tolerance
    if preferred_sectors is not None:
        updates["preferred_sectors"] = preferred_sectors
    if alert_threshold is not None:
        updates["alert_threshold"] = alert_threshold
    if not updates:
        return False
    col = users_col()
    result = await col.update_one({"username": username}, {"$set": updates})
    return result.modified_count > 0


async def increment_analysis_count(username: str):
    col = users_col()
    await col.update_one(
        {"username": username},
        {"$inc": {"analysis_count": 1}, "$set": {"last_analysis_at": _now()}}
    )


async def link_google_id(username: str, google_id: str, email: Optional[str] = None):
    col = users_col()
    patch: Dict[str, Any] = {"google_id": google_id}
    if email:
        patch["email"] = email
    await col.update_one({"username": username}, {"$set": patch})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _serialize(doc: Optional[Dict]) -> Optional[Dict]:
    if doc is None:
        return None
    d = dict(doc)
    if "_id" in d:
        d["_id"] = str(d["_id"])
    for k in ("created_at", "last_login", "last_analysis_at"):
        if isinstance(d.get(k), datetime):
            d[k] = d[k].isoformat()
    return d


def get_portfolio_tickers(user_doc: Dict) -> List[str]:
    return [h["ticker"] for h in user_doc.get("portfolio", [])]
