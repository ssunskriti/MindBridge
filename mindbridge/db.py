# Partly generated with AI assistance (Claude, Anthropic): functions marked below were added/changed with AI help
"""SQLite storage layer: users, consent, check-ins, chat, pathways,
wellness plans and counsellor requests.

This module holds PERSONAL data and is used by the student and counsellor
pages. Admin / institution numbers live in analytics.py, which only reads
group-level totals.

Privacy notes (DPDP Act 2023 principles):
  * minimum data: no phone, address or real name required beyond a display name
  * passwords are salted + hashed (PBKDF2-SHA256)
  * institution dashboard only reads aggregate functions in this module
  * students can delete all their own data (delete_user_data)
"""
from __future__ import annotations

import hashlib
import os
import random
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    display_name  TEXT,
    role          TEXT NOT NULL CHECK(role IN ('student','counsellor','admin')),
    pw_hash       TEXT NOT NULL,
    salt          TEXT NOT NULL,
    consent       INTEGER DEFAULT 0,
    consent_at    TEXT,
    year_of_study TEXT,
    programme     TEXT,
    created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS checkins (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mood       INTEGER, stress INTEGER, sleep INTEGER, energy INTEGER,
    wellbeing  REAL,
    concern    TEXT,                   -- main concern chosen by the student
    note       TEXT,                   -- optional short note (never shown to admin)
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role       TEXT NOT NULL,          -- 'user' or 'assistant'
    content    TEXT NOT NULL,
    explanation TEXT,                  -- JSON for "Why am I getting this response?"
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    concern    TEXT, confidence REAL,
    pathway    INTEGER, score INTEGER,
    safety_flag INTEGER DEFAULT 0,
    reasons    TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS plans (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    concern    TEXT, content TEXT,
    followup_on TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS counsellor_requests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket      TEXT UNIQUE NOT NULL,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    anonymous   INTEGER NOT NULL,
    category    TEXT, message TEXT,
    status      TEXT DEFAULT 'Pending',
    reply       TEXT,
    created_at  TEXT NOT NULL,
    replied_at  TEXT
);
"""


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def connect(path=DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Columns added in Stage 1. Older databases get them through ALTER TABLE,
# so existing accounts and data are kept.
MIGRATIONS = [
    ("users", "year_of_study", "TEXT"),
    ("users", "programme", "TEXT"),
    ("checkins", "concern", "TEXT"),
    ("checkins", "note", "TEXT"),
    ("messages", "explanation", "TEXT"),
]


# Generated with AI assistance (Claude)


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    for table, column, col_type in MIGRATIONS:
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    conn.commit()


# ------------------------------------------------------------------ auth ---
def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 120_000).hex()


def create_user(conn, username: str, password: str, role: str = "student",
                display_name: Optional[str] = None) -> int:
    salt = os.urandom(16).hex()
    cur = conn.execute(
        "INSERT INTO users(username, display_name, role, pw_hash, salt, created_at) VALUES (?,?,?,?,?,?)",
        (username.strip().lower(), display_name or username, role, _hash(password, salt), salt, now()),
    )
    conn.commit()
    return cur.lastrowid


def authenticate(conn, username: str, password: str) -> Optional[sqlite3.Row]:
    row = conn.execute("SELECT * FROM users WHERE username=?", (username.strip().lower(),)).fetchone()
    if row and _hash(password, row["salt"]) == row["pw_hash"]:
        return row
    return None


def get_user(conn, user_id: int):
    return conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()


def set_consent(conn, user_id: int, value: bool = True) -> None:
    conn.execute("UPDATE users SET consent=?, consent_at=? WHERE id=?", (int(value), now(), user_id))
    conn.commit()


# Generated with AI assistance (Claude)


def withdraw_consent(conn, user_id: int) -> None:
    """The student can use MindBridge again only after giving consent again."""
    conn.execute("UPDATE users SET consent=0, consent_at=NULL WHERE id=?", (user_id,))
    conn.commit()


# Generated with AI assistance (Claude)


def update_profile(conn, user_id: int, display_name: str, year_of_study: str, programme: str) -> None:
    conn.execute(
        "UPDATE users SET display_name=?, year_of_study=?, programme=? WHERE id=?",
        (display_name.strip(), year_of_study, programme.strip(), user_id),
    )
    conn.commit()


def delete_user_data(conn, user_id: int, delete_account: bool = False) -> None:
    """Right to erasure: removes all personal records of the student."""
    for t in ("checkins", "messages", "events", "plans", "counsellor_requests"):
        conn.execute(f"DELETE FROM {t} WHERE user_id=?", (user_id,))
    if delete_account:
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()


# -------------------------------------------------------------- check-ins ---
def wellbeing_score(mood: int, stress: int, sleep: int, energy: int) -> float:
    """All on 1-5. Stress is reversed so that higher = better wellbeing."""
    return round((mood + (6 - stress) + sleep + energy) / 4.0, 2)


# Generated with AI assistance (Claude)


def add_checkin(conn, user_id, mood, stress, sleep, energy, at: Optional[str] = None,
                concern: Optional[str] = None, note: Optional[str] = None) -> float:
    for name, value in (("mood", mood), ("stress", stress), ("sleep", sleep), ("energy", energy)):
        if not 1 <= int(value) <= 5:
            raise ValueError(f"{name} must be between 1 and 5")
    note = (note or "").strip() or None
    wb = wellbeing_score(mood, stress, sleep, energy)
    conn.execute(
        "INSERT INTO checkins(user_id,mood,stress,sleep,energy,wellbeing,concern,note,created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (user_id, mood, stress, sleep, energy, wb, concern, note, at or now()),
    )
    conn.commit()
    return wb


def latest_checkin(conn, user_id):
    return conn.execute(
        "SELECT * FROM checkins WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (user_id,)
    ).fetchone()


def recent_checkins(conn, user_id, n=3):
    return conn.execute(
        "SELECT * FROM checkins WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, n)
    ).fetchall()


# Generated with AI assistance (Claude)


def checkin_history(conn, user_id, limit=50):
    """Newest first, for the history table on the student dashboard."""
    return conn.execute(
        "SELECT created_at, mood, stress, sleep, energy, wellbeing, concern, note "
        "FROM checkins WHERE user_id=? ORDER BY created_at DESC, id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()


def checkin_timeline(conn, user_id):
    return conn.execute(
        "SELECT created_at, mood, stress, sleep, energy, wellbeing FROM checkins WHERE user_id=? ORDER BY created_at",
        (user_id,),
    ).fetchall()


# --------------------------------------------------------------- messages ---
# Generated with AI assistance (Claude)
def add_message(conn, user_id, role, content, explanation: Optional[str] = None):
    conn.execute("INSERT INTO messages(user_id,role,content,explanation,created_at) VALUES (?,?,?,?,?)",
                 (user_id, role, content, explanation, now()))
    conn.commit()


def get_messages(conn, user_id, limit=50):
    rows = conn.execute(
        "SELECT role, content, explanation, created_at FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return list(reversed(rows))


# ----------------------------------------------------------------- events ---
def log_event(conn, user_id, concern, confidence, pathway, score, safety_flag, reasons, at=None):
    conn.execute(
        "INSERT INTO events(user_id,concern,confidence,pathway,score,safety_flag,reasons,created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (user_id, concern, confidence, pathway, score, int(safety_flag), "; ".join(reasons), at or now()),
    )
    conn.commit()


def recent_concerns(conn, user_id, days=14):
    since = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
    rows = conn.execute(
        "SELECT concern FROM events WHERE user_id=? AND created_at>=?", (user_id, since)
    ).fetchall()
    return [r["concern"] for r in rows]


def user_events(conn, user_id):
    return conn.execute(
        "SELECT created_at, concern, pathway, score, reasons FROM events WHERE user_id=? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()


# ------------------------------------------------------------------ plans ---
def save_plan(conn, user_id, concern, content, followup_days=3):
    follow = (datetime.now() + timedelta(days=followup_days)).date().isoformat()
    conn.execute("INSERT INTO plans(user_id,concern,content,followup_on,created_at) VALUES (?,?,?,?,?)",
                 (user_id, concern, content, follow, now()))
    conn.commit()


def latest_plan(conn, user_id):
    return conn.execute("SELECT * FROM plans WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()


# --------------------------------------------------- counsellor requests ---
def _new_ticket(conn) -> str:
    while True:
        t = f"MB-{random.randint(1000, 9999)}"
        if not conn.execute("SELECT 1 FROM counsellor_requests WHERE ticket=?", (t,)).fetchone():
            return t


def create_request(conn, user_id, anonymous: bool, category: str, message: str) -> str:
    ticket = _new_ticket(conn)
    conn.execute(
        "INSERT INTO counsellor_requests(ticket,user_id,anonymous,category,message,created_at) VALUES (?,?,?,?,?,?)",
        (ticket, user_id, int(anonymous), category, message, now()),
    )
    conn.commit()
    return ticket


def student_requests(conn, user_id):
    return conn.execute(
        "SELECT * FROM counsellor_requests WHERE user_id=? ORDER BY id DESC", (user_id,)
    ).fetchall()


def counsellor_queue(conn):
    """Counsellor view. For anonymous requests the identity is NOT joined."""
    return conn.execute(
        """SELECT r.ticket, r.anonymous, r.category, r.message, r.status, r.reply, r.created_at,
                  CASE WHEN r.anonymous=1 THEN NULL ELSE u.display_name END AS student_name
           FROM counsellor_requests r JOIN users u ON u.id = r.user_id
           ORDER BY CASE r.status WHEN 'Pending' THEN 0 ELSE 1 END, r.id DESC"""
    ).fetchall()


def reply_request(conn, ticket, reply):
    conn.execute("UPDATE counsellor_requests SET reply=?, status='Responded', replied_at=? WHERE ticket=?",
                 (reply, now(), ticket))
    conn.commit()
