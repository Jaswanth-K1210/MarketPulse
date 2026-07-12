"""
Authentication service — MongoDB Atlas primary, SQLite fallback.

JWT tokens are issued the same way regardless of which store is used.
The token payload carries {user_id (str), username} so downstream code
doesn't need to know which backend resolved the user.
"""
import logging
import os
import sqlite3
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "marketpulse-x-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 h


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _make_token(user_id: str, username: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"user_id": str(user_id), "username": username, "exp": exp},
                      SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[Dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"user_id": payload.get("user_id"), "username": payload.get("username")}
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except Exception as e:
        logger.error(f"Token error: {e}")
        return None


# ── MongoDB path ───────────────────────────────────────────────────────────────

async def mongo_create_user(username: str, password: str, email: Optional[str] = None) -> Dict:
    from app.db.user_profile import create_user, get_by_username
    existing = await get_by_username(username)
    if existing:
        raise ValueError("username_taken")
    doc = await create_user(username, _hash(password), email)
    return {"id": doc["_id"], "username": doc["username"], "email": doc.get("email")}


async def mongo_authenticate(username: str, password: str) -> Optional[Dict]:
    from app.db.user_profile import get_by_username, update_last_login
    doc = await get_by_username(username)
    if not doc or not _verify(password, doc.get("password_hash", "")):
        return None
    await update_last_login(username)
    return {"id": doc["_id"], "username": doc["username"], "email": doc.get("email")}


async def mongo_get_or_create(username: str) -> Dict:
    from app.db.user_profile import get_by_username, create_user
    doc = await get_by_username(username)
    if doc:
        return {"id": doc["_id"], "username": doc["username"], "email": doc.get("email")}
    doc = await create_user(username, _hash("demo123"), None)
    return {"id": doc["_id"], "username": doc["username"], "email": None}


async def mongo_google_auth(google_id: str, email: str, name: str) -> Dict:
    """Find or create a user by Google identity."""
    from app.db.user_profile import (
        get_by_google_id, get_by_email, create_user, link_google_id
    )
    # 1. Try Google ID lookup
    doc = await get_by_google_id(google_id)
    if doc:
        return {"id": doc["_id"], "username": doc["username"], "email": doc.get("email")}
    # 2. Existing account with same email → link Google
    doc = await get_by_email(email)
    if doc:
        await link_google_id(doc["username"], google_id, email)
        return {"id": doc["_id"], "username": doc["username"], "email": email}
    # 3. Brand-new user
    safe_username = name.replace(" ", "_").lower()[:20] or email.split("@")[0]
    doc = await create_user(safe_username, _hash(os.urandom(24).hex()), email, google_id)
    return {"id": doc["_id"], "username": doc["username"], "email": email}


# ── SQLite fallback path ───────────────────────────────────────────────────────

class _SqliteAuthService:
    """Thin wrapper around the original SQLite auth logic — used as fallback."""

    def __init__(self):
        self._ensure_table()

    def _ensure_table(self):
        from app.services.database import get_db_connection
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            google_id TEXT,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME
        )''')
        try:
            c.execute("ALTER TABLE holdings ADD COLUMN user_id INTEGER")
        except sqlite3.OperationalError:
            pass
        conn.commit()
        conn.close()

    def _row(self, username: str) -> Optional[Dict]:
        from app.services.database import get_db_connection
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def create_user(self, username: str, password: str, email: Optional[str] = None) -> Dict:
        from app.services.database import get_db_connection
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username,email,password_hash) VALUES (?,?,?)",
                      (username, email, _hash(password)))
            uid = c.lastrowid
            conn.commit()
            return {"id": uid, "username": username, "email": email}
        except sqlite3.IntegrityError:
            raise ValueError("username_taken")
        finally:
            conn.close()

    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        from app.services.database import get_db_connection
        row = self._row(username)
        if not row or not _verify(password, row["password_hash"]):
            return None
        conn = get_db_connection()
        conn.execute("UPDATE users SET last_login=? WHERE id=?", (datetime.now(), row["id"]))
        conn.commit()
        conn.close()
        return {"id": row["id"], "username": row["username"], "email": row.get("email")}

    def get_or_create_user(self, username: str) -> Dict:
        row = self._row(username)
        if row:
            return {"id": row["id"], "username": row["username"], "email": row.get("email")}
        return self.create_user(username, "demo123")

    def google_auth(self, google_id: str, email: str, name: str) -> Dict:
        from app.services.database import get_db_connection
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=?", (email,))
        row = c.fetchone()
        if row:
            conn.close()
            r = dict(row)
            return {"id": r["id"], "username": r["username"], "email": email}
        safe = name.replace(" ", "_").lower()[:20] or email.split("@")[0]
        c.execute("INSERT INTO users (username,email,google_id,password_hash) VALUES (?,?,?,?)",
                  (safe, email, google_id, _hash(os.urandom(24).hex())))
        uid = c.lastrowid
        conn.commit()
        conn.close()
        return {"id": uid, "username": safe, "email": email}

    # Keep legacy name so existing routes don't break
    def create_access_token(self, user_id, username: str) -> str:
        return _make_token(str(user_id), username)

    def verify_token(self, token: str) -> Optional[Dict]:
        return verify_token(token)


# Global SQLite fallback (synchronous — always available)
auth_service = _SqliteAuthService()


# ── Unified async API ─────────────────────────────────────────────────────────

async def register_user(username: str, password: str, email: Optional[str] = None) -> Dict:
    from app.db.mongo import is_available
    if is_available():
        return await mongo_create_user(username, password, email)
    return auth_service.create_user(username, password, email)


async def login_user(username: str, password: str) -> Optional[Dict]:
    from app.db.mongo import is_available
    if is_available():
        return await mongo_authenticate(username, password)
    return auth_service.authenticate(username, password)


async def google_login(google_id: str, email: str, name: str) -> Dict:
    from app.db.mongo import is_available
    if is_available():
        return await mongo_google_auth(google_id, email, name)
    return auth_service.google_auth(google_id, email, name)


async def get_or_create(username: str) -> Dict:
    from app.db.mongo import is_available
    if is_available():
        return await mongo_get_or_create(username)
    return auth_service.get_or_create_user(username)


def make_token(user_id: str, username: str) -> str:
    return _make_token(str(user_id), username)
