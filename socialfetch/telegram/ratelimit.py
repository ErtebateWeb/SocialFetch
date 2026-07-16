"""Rate limiting + referral system for SocialFetch bot."""

import secrets
import sqlite3
import time
from pathlib import Path

DB = Path("data/ratelimit.db")
DB.parent.mkdir(parents=True, exist_ok=True)

DAILY_LIMIT = 5
MONTHLY_LIMIT = 75
REFERRAL_GRANT_DAYS = 7
SUB_PRICE_TEXT = "$5/month"  # placeholder

_conn: sqlite3.Connection | None = None


def _get_db() -> sqlite3.Connection:
    global _conn
    if _conn is not None:
        return _conn
    _conn = sqlite3.connect(str(DB))
    _conn.execute("PRAGMA journal_mode=WAL")
    _conn.execute("""
        CREATE TABLE IF NOT EXISTS usage (
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,   -- YYYY-MM-DD
            month TEXT NOT NULL,  -- YYYY-MM
            count INTEGER DEFAULT 0,
            premium_until REAL DEFAULT 0,  -- unix ts, 0 = none
            PRIMARY KEY (user_id, date, month)
        )
    """)
    _conn.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            code TEXT PRIMARY KEY,
            owner_id INTEGER NOT NULL,
            used_by INTEGER DEFAULT NULL,
            created REAL DEFAULT (unixepoch())
        )
    """)
    _conn.commit()
    return _conn


def _ensure_user(user_id: int) -> tuple[str, str]:
    import datetime
    now = datetime.datetime.utcnow()
    date = now.strftime("%Y-%m-%d")
    month = now.strftime("%Y-%m")
    db = _get_db()
    db.execute(
        "INSERT OR IGNORE INTO usage (user_id, date, month, count) VALUES (?, ?, ?, 0)",
        (user_id, date, month),
    )
    db.commit()
    return date, month


def is_premium(user_id: int) -> bool:
    db = _get_db()
    row = db.execute(
        "SELECT premium_until FROM usage WHERE user_id=? LIMIT 1",
        (user_id,),
    ).fetchone()
    return row is not None and row[0] > time.time()


def remaining(user_id: int) -> dict:
    """Return daily/monthly remaining counts."""
    _ensure_user(user_id)
    db = _get_db()
    import datetime
    now = datetime.datetime.utcnow()
    date = now.strftime("%Y-%m-%d")
    month = now.strftime("%Y-%m")

    row = db.execute(
        "SELECT count FROM usage WHERE user_id=? AND date=?",
        (user_id, date),
    ).fetchone()
    daily_used = row[0] if row else 0

    row = db.execute(
        "SELECT SUM(count) FROM usage WHERE user_id=? AND month=?",
        (user_id, month),
    ).fetchone()
    monthly_used = row[0] if row and row[0] else 0

    return {
        "daily": max(0, DAILY_LIMIT - daily_used),
        "monthly": max(0, MONTHLY_LIMIT - monthly_used),
    }


def check_limit(user_id: int) -> bool:
    """True if user can download, False if rate-limited."""
    if is_premium(user_id):
        return True
    r = remaining(user_id)
    return r["daily"] > 0 and r["monthly"] > 0


def increment(user_id: int) -> None:
    _ensure_user(user_id)
    db = _get_db()
    import datetime
    now = datetime.datetime.utcnow()
    date = now.strftime("%Y-%m-%d")
    month = now.strftime("%Y-%m")
    db.execute(
        "UPDATE usage SET count = count + 1 WHERE user_id=? AND date=? AND month=?",
        (user_id, date, month),
    )
    db.commit()


def generate_referral(user_id: int) -> str:
    code = secrets.token_hex(4).upper()
    db = _get_db()
    db.execute(
        "INSERT INTO referrals (code, owner_id) VALUES (?, ?)",
        (code, user_id),
    )
    db.commit()
    return code


def use_referral(code: str, user_id: int) -> dict:
    """Apply a referral code. Returns {'ok': True, 'days': 7} or error."""
    db = _get_db()
    row = db.execute(
        "SELECT owner_id, used_by FROM referrals WHERE code=?",
        (code,),
    ).fetchone()
    if not row:
        return {"ok": False, "error": "Invalid referral code."}
    owner_id, used_by = row
    if used_by is not None:
        return {"ok": False, "error": "This code has already been used."}
    if owner_id == user_id:
        return {"ok": False, "error": "You can't use your own code."}
    db.execute("UPDATE referrals SET used_by=? WHERE code=?", (user_id, code))
    # Grant 7 days premium to owner
    now = time.time()
    db.execute(
        "UPDATE usage SET premium_until = MAX(premium_until, ?) + ? WHERE user_id=?",
        (now, REFERRAL_GRANT_DAYS * 86400, owner_id),
    )
    db.commit()
    return {"ok": True, "days": REFERRAL_GRANT_DAYS}
