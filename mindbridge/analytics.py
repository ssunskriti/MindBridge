# Generated with AI assistance (Claude, Anthropic) - reviewed and tested by the team
# (whole file written with AI help in Stage 1, Nov 2026)
"""Institution (admin) numbers.

Kept separate from db.py so the admin side never needs the functions that
read a single student's check-ins, notes or chats. Every query here returns
group-level counts or averages only.

IMPORTANT: these are plain totals. Differential privacy is NOT applied yet.
In Stage 2 the admin dashboard should read noisy, stored releases from a
privacy engine instead of calling these functions directly (see
DEVELOPMENT_STATUS.md).
"""
from __future__ import annotations


def agg_overview(conn):
    q = lambda sql: conn.execute(sql).fetchone()[0]
    return {
        "students": q("SELECT COUNT(*) FROM users WHERE role='student'"),
        "checkins": q("SELECT COUNT(*) FROM checkins"),
        "avg_wellbeing": q("SELECT ROUND(AVG(wellbeing),2) FROM checkins"),
        "conversations": q("SELECT COUNT(*) FROM events"),
        "requests": q("SELECT COUNT(*) FROM counsellor_requests"),
        "pending": q("SELECT COUNT(*) FROM counsellor_requests WHERE status='Pending'"),
        "crisis_routes": q("SELECT COUNT(*) FROM events WHERE pathway=4"),
    }


def agg_concerns(conn):
    return conn.execute("SELECT concern, COUNT(*) AS n FROM events GROUP BY concern ORDER BY n DESC").fetchall()


def agg_pathways(conn):
    return conn.execute("SELECT pathway, COUNT(*) AS n FROM events GROUP BY pathway ORDER BY pathway").fetchall()


def agg_weekly_wellbeing(conn):
    return conn.execute(
        "SELECT strftime('%Y-W%W', created_at) AS week, ROUND(AVG(wellbeing),2) AS avg_wb, COUNT(*) AS n "
        "FROM checkins GROUP BY week ORDER BY week"
    ).fetchall()
