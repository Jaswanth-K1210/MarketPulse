"""
User Authentication & Session Management
Simple JWT-based authentication with user-specific portfolio isolation
"""
import logging
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict
from app.services.database import get_db_connection

logger = logging.getLogger(__name__)

# Secret key for JWT (in production, use environment variable)
SECRET_KEY = "marketpulse-x-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

class AuthService:
    def __init__(self):
        self._ensure_users_table()

    def _ensure_users_table(self):
        """Create users table if it doesn't exist."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME
            )
        ''')

        # Update holdings table to include user_id
        try:
            cursor.execute("ALTER TABLE holdings ADD COLUMN user_id INTEGER")
        except:
            pass  # Column already exists

        conn.commit()
        conn.close()

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

    def create_user(self, username: str, password: str, email: Optional[str] = None) -> Dict:
        """Create a new user."""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            password_hash = self.hash_password(password)

            cursor.execute("""
                INSERT INTO users (username, email, password_hash)
                VALUES (?, ?, ?)
            """, (username, email, password_hash))

            user_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"✅ User created: {username} (ID: {user_id})")

            return {
                "id": user_id,
                "username": username,
                "email": email
            }

        except Exception as e:
            conn.close()
            logger.error(f"Error creating user: {e}")
            raise ValueError(f"User creation failed: {e}")

    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user data."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            return None

        user_dict = dict(user)

        if not self.verify_password(password, user_dict['password_hash']):
            conn.close()
            return None

        # Update last login
        cursor.execute("UPDATE users SET last_login = ? WHERE id = ?",
                      (datetime.now(), user_dict['id']))
        conn.commit()
        conn.close()

        logger.info(f"✅ User authenticated: {username}")

        return {
            "id": user_dict['id'],
            "username": user_dict['username'],
            "email": user_dict['email']
        }

    def create_access_token(self, user_id: int, username: str) -> str:
        """Create JWT access token."""
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode = {
            "user_id": user_id,
            "username": username,
            "exp": expire
        }

        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return token

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token and return user data."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return {
                "user_id": payload.get("user_id"),
                "username": payload.get("username")
            }
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.JWTError as e:
            logger.error(f"Token verification failed: {e}")
            return None

    def get_or_create_user(self, username: str) -> Dict:
        """Get user by username or create if doesn't exist (simplified onboarding)."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user:
            user_dict = dict(user)
            conn.close()
            return {
                "id": user_dict['id'],
                "username": user_dict['username'],
                "email": user_dict.get('email')
            }

        # Create new user with default password (for demo)
        conn.close()
        return self.create_user(username, password="demo123", email=None)

# Global auth service instance
auth_service = AuthService()
