"""
MongoDB Atlas connection via Motor (async).
Graceful fallback to SQLite-only mode when MONGODB_URI is not set.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_client = None
_db = None
_available = False


async def init_mongo() -> bool:
    """Initialize Motor client. Returns True if connection succeeded."""
    global _client, _db, _available

    uri = os.getenv("MONGODB_URI", "").strip()
    db_name = os.getenv("MONGODB_DB_NAME", "marketpulse")

    if not uri:
        logger.warning("MONGODB_URI not set — running in SQLite-only mode (user data in SQLite).")
        return False

    try:
        import certifi
        from motor.motor_asyncio import AsyncIOMotorClient
        _client = AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=8000,
            tlsCAFile=certifi.where(),   # Fix macOS / Python 3.13 TLS handshake
        )
        # Ping to verify connection
        await _client.admin.command("ping")
        _db = _client[db_name]
        _available = True

        # Ensure indexes
        await _db.users.create_index("username", unique=True)
        await _db.users.create_index("email", sparse=True)
        await _db.agent_memory.create_index([("user_id", 1), ("ticker", 1)])
        await _db.analysis_sessions.create_index([("user_id", 1), ("created_at", -1)])

        logger.info(f"✅ MongoDB Atlas connected → {db_name}")
        return True

    except Exception as e:
        logger.warning(f"MongoDB unavailable ({e}) — falling back to SQLite for user data.")
        _available = False
        return False


def is_available() -> bool:
    return _available


def get_db():
    """Return the Motor database handle (or None if not connected)."""
    return _db


def users_col():
    return _db["users"] if _db is not None else None


def profiles_col():
    return _db["user_profiles"] if _db is not None else None


def memory_col():
    return _db["agent_memory"] if _db is not None else None


def sessions_col():
    return _db["analysis_sessions"] if _db is not None else None


async def close_mongo():
    global _client, _available
    if _client:
        _client.close()
        _available = False
