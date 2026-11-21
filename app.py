# Partly generated with AI assistance (Claude, Anthropic): routing code rewritten with AI help: pages moved to mindbridge/ui/
"""MindBridge - Streamlit app (entry point).

Run:  streamlit run app.py      (Windows: python -m streamlit run app.py)
Demo logins (created by scripts/seed_demo.py):
   student / student123   counsellor / counsel123   admin / admin123

This file only handles login, consent and navigation. The pages are in
mindbridge/ui/student.py (students) and mindbridge/ui/staff.py (counsellor, admin).
"""
import streamlit as st

from mindbridge import config as C, db
from mindbridge.pipeline import MindBridge
from mindbridge.ui import staff, student

st.set_page_config(page_title="MindBridge", page_icon="🧠", layout="wide")


@st.cache_resource
def get_conn():
    conn = db.connect()
    db.init_db(conn)
    return conn


@st.cache_resource
def get_bot():
    return MindBridge()


conn = get_conn()
ss = st.session_state
ss.setdefault("user_id", None)


def login_page():
    st.title("MindBridge")
    st.caption("Student wellbeing support · The NorthCap University · Final-year project")
    login_tab, register_tab = st.tabs(["Login", "Register (student)"])
    with login_tab:
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login", type="primary"):
                row = db.authenticate(conn, username, password)
                if row:
                    ss.user_id = row["id"]
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
    with register_tab:
        with st.form("register"):
            username = st.text_input("Choose a username")
            name = st.text_input("Display name (a nickname is fine)")
            password = st.text_input("Password (at least 6 characters)", type="password")
            confirm = st.text_input("Confirm password", type="password")
            if st.form_submit_button("Create account", type="primary"):
                if len(username.strip()) < 3:
                    st.error("Username must have at least 3 characters.")
                elif len(password) < 6:
                    st.error("Password must have at least 6 characters.")
                elif password != confirm:
                    st.error("The two passwords do not match.")
                else:
                    try:
                        ss.user_id = db.create_user(conn, username, password, "student", name.strip() or username)
                        st.rerun()
                    except Exception:
                        st.error("That username is already taken.")
    st.info(C.AI_DISCLAIMER)


if ss.user_id is None:
    login_page()
    st.stop()

user = db.get_user(conn, ss.user_id)
if user is None:
    ss.user_id = None
    st.rerun()

STUDENT_PAGES = ["Dashboard", "Chat", "My Profile", "Talk to a Counsellor", "Helplines & Resources"]

with st.sidebar:
    st.markdown(f"### MindBridge\nLogged in as **{user['display_name']}** ({user['role']})")
    if user["role"] == "student":
        page = st.radio("Go to", STUDENT_PAGES, disabled=not user["consent"])
    elif user["role"] == "counsellor":
        page = "Counsellor"
    else:
        page = "Admin"
    if st.button("Logout"):
        ss.user_id = None
        st.rerun()
    st.divider()
    st.caption("Tele-MANAS: **14416** · Emergency: **112**")

if user["role"] == "student" and not user["consent"]:
    student.consent_page(conn, user)
elif page == "Dashboard":
    student.dashboard_page(conn, user)
elif page == "Chat":
    student.chat_page(conn, user, get_bot())
elif page == "My Profile":
    student.profile_page(conn, user)
elif page == "Talk to a Counsellor":
    student.counsellor_request_page(conn, user)
elif page == "Helplines & Resources":
    student.helplines_page(get_bot())
elif page == "Counsellor":
    staff.counsellor_page(conn)
else:
    staff.admin_page(conn)
