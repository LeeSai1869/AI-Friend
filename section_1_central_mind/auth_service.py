"""Authentication service for AI Friend V1.

Wired into the WebSocket server (see server.py). Sessions are validated
on every protected request. Use a private, user-owned directory for its
database.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from contextlib import contextmanager
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path


_ROLES = {"administrator", "trainer", "user"}
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,64}$")
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SALT_BYTES = 16
_KEY_BYTES = 32
_DEFAULT_SESSION_SECONDS = 12 * 60 * 60


class AuthenticationError(Exception):
    """Authentication or authorization was denied."""


class AuthService:
    def __init__(
        self,
        database_path: str | Path,
        *,
        session_seconds: int = _DEFAULT_SESSION_SECONDS,
    ):
        self.database_path = Path(database_path).expanduser().resolve()
        if session_seconds < 60:
            raise ValueError("session_seconds must be at least 60")
        self.session_seconds = int(session_seconds)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.database_path.parent, 0o700)
        except OSError:
            pass
        self._initialize()

    @contextmanager
    def _connect(self):
        """Open one transaction-scoped SQLite connection and always close it."""
        db = sqlite3.connect(self.database_path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            yield db
        except BaseException:
            db.rollback()
            raise
        else:
            db.commit()
        finally:
            db.close()

    def _initialize(self):
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    role TEXT NOT NULL CHECK (
                        role IN ('administrator', 'trainer', 'user')
                    ),
                    password_salt BLOB NOT NULL,
                    password_hash BLOB NOT NULL,
                    active_token_hash TEXT,
                    session_expires REAL,
                    created_at REAL NOT NULL,
                    disabled INTEGER NOT NULL DEFAULT 0
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_admin
                    ON accounts(role) WHERE role = 'administrator';
                CREATE UNIQUE INDEX IF NOT EXISTS one_trainer
                    ON accounts(role) WHERE role = 'trainer';
                CREATE INDEX IF NOT EXISTS active_token_lookup
                    ON accounts(active_token_hash)
                    WHERE active_token_hash IS NOT NULL;
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    event TEXT NOT NULL,
                    actor TEXT,
                    subject TEXT,
                    detail TEXT NOT NULL
                );
                INSERT OR IGNORE INTO settings(key, value)
                    VALUES ('public_registration', 'false');
            """)
        try:
            os.chmod(self.database_path, 0o600)
        except OSError:
            pass

    @staticmethod
    def _password_material(password: str, salt: bytes) -> bytes:
        return hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=_SCRYPT_N,
            r=_SCRYPT_R,
            p=_SCRYPT_P,
            dklen=_KEY_BYTES,
        )

    @staticmethod
    def _check_credentials_input(username: str, password: str):
        if not isinstance(username, str) or not _USERNAME_RE.fullmatch(username):
            raise ValueError(
                "username must be 3-64 characters: letters, numbers, _, ., or -"
            )
        if not isinstance(password, str) or len(password) < 12:
            raise ValueError("password must contain at least 12 characters")
        if len(password) > 1024:
            raise ValueError("password is too long")

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _audit(db, event, actor=None, subject=None, detail=None):
        db.execute(
            "INSERT INTO audit(timestamp,event,actor,subject,detail) "
            "VALUES(?,?,?,?,?)",
            (time.time(), event, actor, subject,
             json.dumps(detail or {}, sort_keys=True)),
        )

    def _audit_committed(self, event, actor=None, subject=None, detail=None):
        """Write an audit event in its own committed transaction.

        Use this for denial paths that immediately raise. If a denial were
        written in the caller's transaction, the exception would roll the
        audit row back together with that transaction.
        """
        with self._connect() as audit_db:
            self._audit(
                audit_db,
                event,
                actor=actor,
                subject=subject,
                detail=detail,
            )

    @staticmethod
    def _account(row):
        if row is None:
            return None
        return {
            "id": row["id"],
            "username": row["username"],
            "role": row["role"],
            "created_at": row["created_at"],
            "disabled": bool(row["disabled"]),
        }

    def bootstrap_admin(self, username: str, password: str):
        """Create the first Administrator only when the account table is empty."""
        self._check_credentials_input(username, password)
        salt = secrets.token_bytes(_SALT_BYTES)
        password_hash = self._password_material(password, salt)

        with self._connect() as db:
            if db.execute("SELECT 1 FROM accounts LIMIT 1").fetchone():
                db.rollback()
                self._audit_committed(
                    "bootstrap_denied",
                    subject=username,
                    detail={"reason": "accounts_already_exist"},
                )
                raise AuthenticationError("bootstrap is already complete")

            now = time.time()
            db.execute(
                "INSERT INTO accounts(username,role,password_salt,password_hash,created_at) "
                "VALUES(?,?,?,?,?)",
                (username, "administrator", salt, password_hash, now),
            )
            self._audit(db, "bootstrap_admin_created", subject=username)
            return {"username": username, "role": "administrator"}

    def registration_enabled(self) -> bool:
        with self._connect() as db:
            row = db.execute(
                "SELECT value FROM settings WHERE key='public_registration'"
            ).fetchone()
            return bool(row and row["value"] == "true")

    def register(self, username: str, password: str):
        """Public registration creates ordinary users only; disabled by default."""
        self._check_credentials_input(username, password)
        salt = secrets.token_bytes(_SALT_BYTES)
        password_hash = self._password_material(password, salt)

        with self._connect() as db:
            setting = db.execute(
                "SELECT value FROM settings WHERE key='public_registration'"
            ).fetchone()
            if not setting or setting["value"] != "true":
                db.rollback()
                self._audit_committed(
                    "registration_denied",
                    subject=username,
                    detail={"reason": "registration_disabled"},
                )
                raise AuthenticationError("public registration is disabled")

            now = time.time()
            try:
                db.execute(
                    "INSERT INTO accounts(username,role,password_salt,password_hash,created_at) "
                    "VALUES(?,?,?,?,?)",
                    (username, "user", salt, password_hash, now),
                )
            except sqlite3.IntegrityError:
                db.rollback()
                self._audit_committed(
                    "registration_denied",
                    subject=username,
                    detail={"reason": "username_unavailable"},
                )
                raise AuthenticationError("username is unavailable") from None

            self._audit(db, "account_registered", subject=username,
                        detail={"role": "user"})
            return {"username": username, "role": "user"}

    def login(self, username: str, password: str) -> dict:
        if not isinstance(username, str) or not isinstance(password, str):
            raise AuthenticationError("invalid username or password")

        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM accounts WHERE username = ? COLLATE NOCASE",
                (username,),
            ).fetchone()

            # Use a dummy scrypt calculation for unknown usernames too.
            salt = row["password_salt"] if row else b"\0" * _SALT_BYTES
            expected = row["password_hash"] if row else b"\0" * _KEY_BYTES
            try:
                actual = self._password_material(password, salt)
            except (ValueError, TypeError, UnicodeError):
                actual = b"\1" * _KEY_BYTES

            valid = hmac.compare_digest(actual, expected)
            if row is None or not valid or row["disabled"]:
                db.rollback()
                self._audit_committed(
                    "login_denied",
                    subject=username,
                    detail={"reason": "invalid_credentials_or_disabled"},
                )
                raise AuthenticationError("invalid username or password")

            token = secrets.token_urlsafe(32)
            expires = time.time() + self.session_seconds
            db.execute(
                "UPDATE accounts SET active_token_hash=?, session_expires=? WHERE id=?",
                (self._token_hash(token), expires, row["id"]),
            )
            self._audit(db, "login_succeeded", actor=row["username"])
            return {
                "token": token,
                "expires_at": expires,
                "account": self._account(row),
            }

    def validate_session(self, token: str, allowed_roles=None) -> dict:
        if not isinstance(token, str) or not token:
            raise AuthenticationError("session required")

        with self._connect() as db:
            token_hash = self._token_hash(token)
            matched = db.execute(
                "SELECT * FROM accounts WHERE active_token_hash = ?",
                (token_hash,),
            ).fetchone()

            if (
                matched is None
                or matched["disabled"]
                or not matched["session_expires"]
                or matched["session_expires"] <= time.time()
            ):
                db.rollback()
                self._audit_committed(
                    "session_denied",
                    detail={"reason": "missing_expired_or_revoked"},
                )
                raise AuthenticationError("session is invalid or expired")

            if allowed_roles is not None and matched["role"] not in set(allowed_roles):
                db.rollback()
                self._audit_committed(
                    "authorization_denied",
                    actor=matched["username"],
                    detail={"required_roles": sorted(set(allowed_roles))},
                )
                raise AuthenticationError("permission denied")

            return self._account(matched)

    def logout(self, token: str):
        if not isinstance(token, str) or not token:
            return
        token_hash = self._token_hash(token)
        with self._connect() as db:
            rows = db.execute(
                "SELECT id,username,active_token_hash FROM accounts "
                "WHERE active_token_hash IS NOT NULL"
            ).fetchall()
            for row in rows:
                if hmac.compare_digest(row["active_token_hash"], token_hash):
                    db.execute(
                        "UPDATE accounts SET active_token_hash=NULL, "
                        "session_expires=NULL WHERE id=?", (row["id"],)
                    )
                    self._audit(db, "logout", actor=row["username"])
                    return

    def create_account(self, admin_token: str, username: str,
                       password: str, role: str = "user"):
        """Administrator creates a user or the single designated Trainer."""
        actor = self.validate_session(admin_token, {"administrator"})
        self._check_credentials_input(username, password)
        if role not in {"user", "trainer"}:
            self._audit_committed(
                "account_creation_denied",
                actor=actor["username"],
                subject=username,
                detail={
                    "role": role,
                    "reason": "invalid_role",
                },
            )
            raise AuthenticationError(
                "only user or trainer accounts can be created here"
            )

        salt = secrets.token_bytes(_SALT_BYTES)
        password_hash = self._password_material(password, salt)
        with self._connect() as db:
            try:
                db.execute(
                    "INSERT INTO accounts(username,role,password_salt,password_hash,created_at) "
                    "VALUES(?,?,?,?,?)",
                    (username, role, salt, password_hash, time.time()),
                )
            except sqlite3.IntegrityError:
                db.rollback()
                self._audit_committed(
                    "account_creation_denied",
                    actor=actor["username"],
                    subject=username,
                    detail={"role": role},
                )
                raise AuthenticationError(
                    "username unavailable or designated role already exists"
                ) from None

            self._audit(db, "account_created", actor=actor["username"],
                        subject=username, detail={"role": role})
            return {"username": username, "role": role}

    def set_registration_enabled(self, admin_token: str, enabled: bool):
        actor = self.validate_session(admin_token, {"administrator"})
        if type(enabled) is not bool:
            raise ValueError("enabled must be a boolean")
        with self._connect() as db:
            db.execute(
                "UPDATE settings SET value=? WHERE key='public_registration'",
                ("true" if enabled else "false",),
            )
            self._audit(db, "registration_setting_changed",
                        actor=actor["username"], detail={"enabled": enabled})

    def audit_events(self, admin_token: str, limit: int = 100) -> list[dict]:
        actor = self.validate_session(admin_token, {"administrator"})
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        with self._connect() as db:
            rows = db.execute(
                "SELECT timestamp,event,actor,subject,detail FROM audit "
                "ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {
                "timestamp": row["timestamp"],
                "event": row["event"],
                "actor": row["actor"],
                "subject": row["subject"],
                "detail": json.loads(row["detail"]),
            }
            for row in rows
        ]
