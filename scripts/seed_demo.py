# Partly generated with AI assistance (Claude, Anthropic): demo check-ins with concern/note updated with AI help
"""Create demo accounts + sample history so dashboards have data to show.
Run:  python scripts/seed_demo.py
"""
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mindbridge import db  # noqa: E402
from mindbridge.config import DB_PATH  # noqa: E402

random.seed(7)
if DB_PATH.exists():
    DB_PATH.unlink()
conn = db.connect()
db.init_db(conn)

sid = db.create_user(conn, "student", "student123", "student", "Demo Student")
db.set_consent(conn, sid)
db.create_user(conn, "counsellor", "counsel123", "counsellor", "Dr. Counsellor")
db.create_user(conn, "admin", "admin123", "admin", "NCU Admin")

concerns = ["academic_stress", "sleep_difficulty", "loneliness", "burnout", "self_esteem",
            "relationship_social", "emotional_distress", "other"]
for k in range(12):  # extra anonymous-looking demo students for aggregates
    uid = db.create_user(conn, f"demo{k}", "demo12345", "student", f"Student {k}")
    db.set_consent(conn, uid)
    for d in range(0, 28, random.randint(3, 6)):
        at = (datetime.now() - timedelta(days=28 - d)).isoformat(timespec="seconds")
        db.add_checkin(conn, uid, random.randint(2, 5), random.randint(1, 5), random.randint(2, 5), random.randint(2, 5), at)
        c = random.choices(concerns, weights=[6, 4, 3, 3, 2, 2, 2, 2])[0]
        lvl = random.choices([1, 2, 3], weights=[6, 3, 1])[0]
        db.log_event(conn, uid, c, 0.8, lvl, lvl, False, ["seeded demo data"], at)

db.update_profile(conn, sid, "Demo Student", "4th year", "B.Tech CSE")
demo_checkins = [
    (4, 2, 4, 4, None, None),
    (3, 3, 3, 3, "academic_stress", "Mid-sem exams next week"),
    (3, 4, 2, 3, "sleep_difficulty", "Slept late three nights in a row"),
    (2, 4, 2, 2, "academic_stress", "Project deadline and viva on the same day"),
]
for d, (m, s, sl, e, concern, note) in enumerate(demo_checkins):
    at = (datetime.now() - timedelta(days=10 - 3 * d)).isoformat(timespec="seconds")
    db.add_checkin(conn, sid, m, s, sl, e, at, concern=concern, note=note)
db.log_event(conn, sid, "academic_stress", 0.7, 1, 0, False, ["seeded"],
             (datetime.now() - timedelta(days=5)).isoformat(timespec="seconds"))
db.create_request(conn, uid, True, "Academic stress", "I have been very stressed about placements and can't sleep.")
print("Demo DB ready:", DB_PATH)
print("Logins -> student/student123  counsellor/counsel123  admin/admin123")
