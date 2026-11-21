# Generated with AI assistance (Claude, Anthropic) - reviewed and tested by the team
# (whole file written with AI help in Stage 1, Nov 2026)
"""Stage 1 checks: registration, login, consent, check-ins, history, chatbot
and "Why am I getting this response?".

It drives the real Streamlit app (app.py) with Streamlit's built-in test
tool, using a temporary database, so your real mindbridge.db is not touched.

Run:  python scripts/test_stage1.py
"""
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP_DIR = tempfile.mkdtemp()
os.environ["MINDBRIDGE_DB"] = str(Path(TMP_DIR) / "test.db")
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402

from mindbridge import db  # noqa: E402

APP = str(ROOT / "app.py")
results = []


def check(name, condition, detail=""):
    results.append(condition)
    print(f"[{'PASS' if condition else 'FAIL'}] {name}" + (f"  ({detail})" if detail and not condition else ""))


def texts(at):
    """All text shown on the page (markdown, alerts, captions)."""
    parts = [e.value for e in at.markdown] + [e.value for e in at.success] + [e.value for e in at.error]
    parts += [e.value for e in at.info] + [e.value for e in at.caption] + [e.value for e in at.warning]
    return "\n".join(str(p) for p in parts)


def new_app():
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    return at


def go_to(at, page):
    at.sidebar.radio[0].set_value(page).run()


# 1. Old database from the mid-term version is upgraded without losing data
old = sqlite3.connect(os.environ["MINDBRIDGE_DB"])
old.executescript("""
CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, display_name TEXT,
  role TEXT NOT NULL, pw_hash TEXT NOT NULL, salt TEXT NOT NULL, consent INTEGER DEFAULT 0, consent_at TEXT,
  created_at TEXT NOT NULL);
CREATE TABLE checkins (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, mood INTEGER,
  stress INTEGER, sleep INTEGER, energy INTEGER, wellbeing REAL, created_at TEXT NOT NULL);
CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, role TEXT NOT NULL,
  content TEXT NOT NULL, created_at TEXT NOT NULL);
""")
old.close()
conn = db.connect()
db.init_db(conn)
cols = {r["name"] for r in conn.execute("PRAGMA table_info(checkins)")}
check("Old database upgraded with new check-in columns", {"concern", "note"} <= cols, str(cols))

# 2. Registration
at = new_app()
check("Login page loads without errors", not at.exception and len(at.tabs) == 2)
form = at.tabs[1]
form.text_input[0].input("asha")
form.text_input[1].input("Asha")
form.text_input[2].input("secret12")
form.text_input[3].input("different")
form.button[0].click().run()
check("Mismatched passwords are rejected", "do not match" in texts(at))
form = at.tabs[1]
form.text_input[3].input("secret12")
form.button[0].click().run()
check("Registration creates the account and logs in", at.session_state["user_id"] is not None)

# 3. Consent is required before anything else
check("Consent page is shown to a new student", "consent" in at.header[0].value.lower())
check("Continue is disabled until the box is ticked",
      any(b.label == "Continue" and b.disabled for b in at.button))
at.checkbox[0].check().run()
next(b for b in at.button if b.label == "Continue").click().run()
user = db.get_user(conn, at.session_state["user_id"])
check("Consent is saved in the database", user["consent"] == 1 and user["consent_at"] is not None)
check("Dashboard opens after consent", "Hello" in at.header[0].value)

# 4. Login with the new account (fresh session)
at = new_app()
at.tabs[0].text_input[0].input("asha")
at.tabs[0].text_input[1].input("wrong-pass")
at.tabs[0].button[0].click().run()
check("Wrong password is rejected", "Invalid username or password" in texts(at))
at.tabs[0].text_input[1].input("secret12")
at.tabs[0].button[0].click().run()
check("Correct password logs in to the dashboard", "Hello, Asha" in at.header[0].value)
check("Empty history state is shown", "No check-ins yet" in texts(at))

# 5. Check-in is saved and shown in history
at.selectbox[0].set_value(2)                       # mood: Low
at.slider[0].set_value(4)                          # stress
at.slider[1].set_value(2)                          # sleep
at.slider[2].set_value(3)                          # energy
at.selectbox[1].set_value("Academic stress")
at.text_area[0].input("Two assignments due Friday")
next(b for b in at.button if b.label == "Save check-in").click().run()
check("Check-in success message", "Check-in saved" in texts(at), texts(at)[:200])
row = db.latest_checkin(conn, user["id"])
check("Check-in saved with all fields",
      row is not None and (row["mood"], row["stress"], row["sleep"], row["energy"], row["concern"], row["note"])
      == (2, 4, 2, 3, "academic_stress", "Two assignments due Friday"), str(dict(row) if row else None))
history = at.dataframe[0].value
check("History table shows the check-in",
      len(history) == 1 and history.iloc[0]["Main concern"] == "Academic stress"
      and history.iloc[0]["Mood"] == "Low" and history.iloc[0]["Note"] == "Two assignments due Friday")
db.add_checkin(conn, user["id"], 4, 2, 4, 4, at="2020-01-01T10:00:00")
at.run()
history = at.dataframe[0].value
check("History lists check-ins newest first", len(history) == 2 and history.iloc[1]["Date"].startswith("01 Jan 2020"))

# 6. Chatbot replies and explanation
go_to(at, "Chat")
check("Chat page opens", "Chat with MindBridge" in at.header[0].value)
at.chat_input[0].set_value("I have exams next week and I can't focus at all").run()
reply = at.chat_message[1].markdown[0].value if len(at.chat_message) > 1 else ""
check("Chatbot replies to an exam-stress message", "A few things that may help" in reply, reply[:120])
saved = db.get_messages(conn, user["id"])
exp = json.loads(saved[-1]["explanation"]) if saved and saved[-1]["explanation"] else {}
check("Concern detected as academic stress", exp.get("concern") == "academic_stress", str(exp.get("concern")))
check("Explanation includes words from the message", "exams" in exp.get("key_words", []), str(exp.get("key_words")))
check("Explanation uses the latest check-in", exp.get("checkin", {}).get("stress") == 4)
check("'Why am I getting this response?' expander shown",
      any(e.label == "Why am I getting this response?" for e in at.expander))

at.chat_input[0].set_value("hello").run()
last = json.loads(db.get_messages(conn, user["id"])[-1]["explanation"])
check("Unclear message is not forced into a topic", last["concern"] == "other" and last["low_confidence"])

at.chat_input[0].set_value("am I depressed?").run()
last = db.get_messages(conn, user["id"])[-1]
check("Diagnosis question gets the no-diagnosis reply", "can't tell you whether you have a condition" in last["content"])

at.chat_input[0].set_value("I don't want to live anymore").run()
last = db.get_messages(conn, user["id"])[-1]
check("Crisis message shows helplines", "14416" in last["content"] and "112" in last["content"])

at = AppTest.from_file(APP, default_timeout=120)
at.session_state["user_id"] = user["id"]
at.run()
go_to(at, "Chat")
check("Explanations still available after reloading the chat",
      sum(e.label == "Why am I getting this response?" for e in at.expander) == 4)

# 7. Profile and consent withdrawal
go_to(at, "My Profile")
at.selectbox[0].set_value("4th year")
at.text_input[1].input("B.Tech CSE")
next(b for b in at.button if b.label == "Save profile").click().run()
user = db.get_user(conn, user["id"])
check("Profile saved", user["year_of_study"] == "4th year" and user["programme"] == "B.Tech CSE")
next(b for b in at.button if b.label == "Withdraw my consent").click().run()
check("Withdrawing consent shows the consent page again", "consent" in at.header[0].value.lower())

# 8. Admin page shows only totals
admin_id = db.create_user(conn, "admin", "admin123", "admin", "Admin")
at = AppTest.from_file(APP, default_timeout=120)
at.session_state["user_id"] = admin_id
at.run()
page = texts(at)
check("Admin page has no notes or chat text",
      "Two assignments due Friday" not in page and "exams next week" not in page and not at.dataframe)
check("Admin page says differential privacy is not implemented yet", "not implemented yet" in page)

print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
