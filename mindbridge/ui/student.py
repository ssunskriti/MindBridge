# Generated with AI assistance (Claude, Anthropic) - reviewed and tested by the team
# (whole file written with AI help in Stage 1, Nov 2026)
"""Student-facing pages. Nothing here is used by the admin side."""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from .. import config as C, db

NO_CONCERN = "Nothing specific"


# ------------------------------------------------------------- consent ---
def consent_page(conn, user):
    st.header("Before you start: consent")
    st.write("Please read how MindBridge uses your information. You can withdraw consent "
             "or delete your data at any time from your Profile.")
    st.table(pd.DataFrame(
        [
            ["Account", "Username, display name, hashed password; optional year and programme", "Login and profile"],
            ["Check-ins", "Mood, stress, sleep and energy (1-5), main concern, optional note", "Your dashboard and history; chatbot context"],
            ["Chat", "Your messages, the bot's replies and why each reply was chosen", "Showing your conversation and explanations"],
            ["Counsellor requests", "Only what you choose to send, with your name or anonymously", "Reaching the counsellor"],
        ],
        columns=["What", "Details", "Used for"],
    ).set_index("What"))
    st.markdown("""
- MindBridge is a **support tool, not a doctor or counsellor**. It does not diagnose or treat.
- Your **chats, notes and individual check-ins are never shown** to the admin. The admin page shows only
  group totals. *(These totals are not yet protected with differential privacy; that is planned for the next stage.)*
- A counsellor sees **only** the requests you send.
- If a message suggests you may be unsafe, MindBridge shows **crisis helplines** (Tele-MANAS 14416, 112).
- Data handling follows the principles of India's **DPDP Act, 2023**.
""")
    agreed = st.checkbox("I have read this and I agree")
    if st.button("Continue", type="primary", disabled=not agreed):
        db.set_consent(conn, user["id"])
        st.rerun()


# ----------------------------------------------------------- dashboard ---
def _concern_name(code):
    return C.LABEL_NAMES.get(code, NO_CONCERN) if code else NO_CONCERN


def checkin_form(conn, user):
    st.subheader("New wellbeing check-in")
    concern_options = [NO_CONCERN] + [C.LABEL_NAMES[c] for c in C.CONCERN_LABELS if c != "other"]
    with st.form("checkin", clear_on_submit=True):
        c1, c2 = st.columns(2)
        mood = c1.selectbox("How is your mood today?", list(C.MOOD_OPTIONS), index=2,
                            format_func=lambda v: f"{v} - {C.MOOD_OPTIONS[v]}")
        stress = c2.slider("Stress level (1 = very low, 5 = very high)", 1, 5, 3)
        c3, c4 = st.columns(2)
        sleep = c3.slider("Sleep quality (1 = very poor, 5 = very good)", 1, 5, 3)
        energy = c4.slider("Energy (1 = very low, 5 = very high)", 1, 5, 3)
        concern_label = st.selectbox("Main concern right now", concern_options)
        note = st.text_area("Short note (optional, only you can see it)",
                            max_chars=C.CHECKIN_NOTE_MAX_CHARS, placeholder="e.g. Two assignments due on Friday")
        if st.form_submit_button("Save check-in", type="primary"):
            concern = next((c for c, n in C.LABEL_NAMES.items() if n == concern_label), None)
            try:
                score = db.add_checkin(conn, user["id"], mood, stress, sleep, energy, concern=concern, note=note)
                st.success(f"Check-in saved. Your wellbeing score is {score}/5.")
            except Exception as err:
                st.error(f"Could not save your check-in: {err}")


def checkin_history(conn, user):
    st.subheader("My check-in history")
    rows = db.checkin_history(conn, user["id"])
    if not rows:
        st.info("No check-ins yet. Your saved check-ins will appear here.")
        return
    df = pd.DataFrame([dict(r) for r in rows])
    if len(df) >= 2:
        trend = df[["created_at", "wellbeing", "stress"]].copy()
        trend["created_at"] = pd.to_datetime(trend["created_at"])
        st.line_chart(trend.set_index("created_at"), height=220)
        st.caption("Wellbeing score (higher is better) and stress (higher is more stress), both on a 1-5 scale.")
    table = pd.DataFrame({
        "Date": pd.to_datetime(df["created_at"]).dt.strftime("%d %b %Y, %H:%M"),
        "Mood": df["mood"].map(lambda v: C.MOOD_OPTIONS.get(v, v)),
        "Stress": df["stress"],
        "Sleep": df["sleep"],
        "Energy": df["energy"],
        "Wellbeing": df["wellbeing"],
        "Main concern": df["concern"].map(_concern_name),
        "Note": df["note"].fillna(""),
    })
    st.dataframe(table, hide_index=True)


def dashboard_page(conn, user):
    st.header(f"Hello, {user['display_name']}")
    last = db.latest_checkin(conn, user["id"])
    if last:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Last check-in", pd.to_datetime(last["created_at"]).strftime("%d %b"))
        m2.metric("Mood", C.MOOD_OPTIONS.get(last["mood"], last["mood"]))
        m3.metric("Stress", f"{last['stress']}/5")
        m4.metric("Wellbeing score", f"{last['wellbeing']}/5")
    else:
        st.info("Start with your first check-in below. It takes less than a minute.")

    checkin_form(conn, user)
    st.divider()
    checkin_history(conn, user)

    plan = db.latest_plan(conn, user["id"])
    if plan:
        st.divider()
        st.subheader("My wellness support plan")
        st.caption(f"For: {C.LABEL_NAMES.get(plan['concern'], plan['concern'])} · "
                   f"suggested follow-up check-in on {plan['followup_on']}")
        st.markdown(plan["content"])


# ---------------------------------------------------------------- chat ---
def render_explanation(exp: dict):
    """The "Why am I getting this response?" panel. Shows only recorded inputs and rules."""
    if exp.get("low_confidence"):
        st.markdown(f"**Detected concern:** not clear. The classifier's best guess was "
                    f"*{exp['model_guess']}*, but its confidence ({exp['confidence']:.2f}) was below "
                    f"{C.MIN_CONCERN_CONFIDENCE:.2f}, so MindBridge did not assume a topic.")
    else:
        st.markdown(f"**Detected concern:** {exp['concern_name']} (classifier confidence {exp['confidence']:.2f})")
    if exp.get("key_words"):
        st.markdown("**Words in your message most linked to this concern:** " + ", ".join(exp["key_words"]))
    st.markdown(f"**Safety check:** {exp['safety']}")
    if exp.get("diagnosis_request"):
        st.markdown("**Diagnosis or medication question:** yes, so a fixed safety reply was used")
    ci = exp.get("checkin")
    if ci:
        concern = f", main concern: {ci['concern']}" if ci.get("concern") else ""
        st.markdown(f"**Your latest check-in ({ci['date']}):** mood {ci['mood']}, stress {ci['stress']}/5, "
                    f"wellbeing score {ci['wellbeing']}/5{concern}")
    else:
        st.markdown("**Your latest check-in:** none yet")
    st.markdown(f"**Support level chosen:** {exp['pathway']}")
    for reason in exp.get("reasons", []):
        st.markdown(f"- {reason}")
    st.markdown(f"**How the reply was written:** {exp['reply_source']}")
    if exp.get("sources"):
        st.markdown("**Knowledge-base sources:** " + "; ".join(
            f"[{t}]({u})" if u else t for t, u in exp["sources"]))
    st.caption("This panel lists the inputs and rules MindBridge used. It does not show hidden AI reasoning. "
               "The confidence is a model score, not a medical judgement.")


def _show_assistant_message(text: str, explanation: dict | None):
    if explanation and explanation.get("level") == 4:
        st.error("Crisis support")
    st.markdown(text)
    if explanation:
        with st.expander("Why am I getting this response?"):
            render_explanation(explanation)


def chat_page(conn, user, bot):
    st.header("Chat with MindBridge")
    st.caption(C.AI_DISCLAIMER)
    if db.latest_checkin(conn, user["id"]) is None:
        st.info("Tip: do a check-in on the Dashboard first, so MindBridge can take it into account.")

    history = db.get_messages(conn, user["id"])
    if not history:
        st.write("You can write about anything on your mind, such as exams, sleep, friends or how you feel.")
    for m in history:
        with st.chat_message(m["role"]):
            if m["role"] == "assistant":
                _show_assistant_message(m["content"], json.loads(m["explanation"]) if m["explanation"] else None)
            else:
                st.markdown(m["content"])

    msg = st.chat_input("Type your message")
    if msg and msg.strip():
        msg = msg.strip()
        db.add_message(conn, user["id"], "user", msg)
        with st.chat_message("user"):
            st.markdown(msg)
        with st.chat_message("assistant"):
            try:
                with st.spinner("MindBridge is replying..."):
                    reply = bot.handle(conn, user["id"], msg)
            except Exception as err:
                st.error(f"Sorry, something went wrong while replying ({err}). Please try again. "
                         "If you need help now, call Tele-MANAS 14416.")
                return
            _show_assistant_message(reply.text, reply.explanation)
        db.add_message(conn, user["id"], "assistant", reply.text, json.dumps(reply.explanation))


# ------------------------------------------------------------- profile ---
def profile_page(conn, user):
    st.header("My profile")
    c1, c2 = st.columns(2)
    c1.markdown(f"**Username:** {user['username']}")
    c1.markdown(f"**Account created:** {user['created_at'][:10]}")
    c2.markdown(f"**Consent given on:** {user['consent_at'][:10] if user['consent_at'] else 'Not given'}")
    c2.markdown("**Role:** Student")

    with st.form("profile"):
        name = st.text_input("Display name (a nickname is fine)", value=user["display_name"] or "")
        year_now = user["year_of_study"] if user["year_of_study"] in C.YEAR_OPTIONS else "Not set"
        year = st.selectbox("Year of study", C.YEAR_OPTIONS, index=C.YEAR_OPTIONS.index(year_now))
        programme = st.text_input("Programme (optional)", value=user["programme"] or "",
                                  placeholder="e.g. B.Tech CSE")
        if st.form_submit_button("Save profile", type="primary"):
            if not name.strip():
                st.error("Display name cannot be empty.")
            else:
                db.update_profile(conn, user["id"], name, year, programme)
                st.success("Profile saved.")
                st.rerun()

    st.divider()
    st.subheader("Privacy and consent")
    with st.expander("Withdraw consent"):
        st.write("You will be asked to give consent again before using MindBridge. Your data is kept "
                 "unless you also delete it below.")
        if st.button("Withdraw my consent"):
            db.withdraw_consent(conn, user["id"])
            st.rerun()
    with st.expander("Delete my data"):
        st.write("This permanently removes your check-ins, chats, plans and counsellor requests.")
        confirm = st.checkbox("I understand this cannot be undone")
        if st.button("Delete all my data", type="primary", disabled=not confirm):
            db.delete_user_data(conn, user["id"])
            st.success("Your data has been deleted.")


# ---------------------------------------------------- counsellor request ---
def counsellor_request_page(conn, user):
    st.header("Talk to a Counsellor")
    st.caption("Prototype workflow, labelled as a demo until it is connected to the university counselling cell.")
    with st.form("req", clear_on_submit=True):
        anon = st.radio("How do you want to reach out?", ["Anonymous", "With my name"], horizontal=True) == "Anonymous"
        cat = st.selectbox("Category", [C.LABEL_NAMES[c] for c in C.CONCERN_LABELS])
        msg = st.text_area("What would you like the counsellor to know?")
        if st.form_submit_button("Send request", type="primary"):
            if not msg.strip():
                st.error("Please write a short message first.")
            else:
                t = db.create_request(conn, user["id"], anon, cat, msg.strip())
                st.success(f"Request sent. Your ID is **{t}**. "
                           + ("The counsellor will not see your name." if anon else ""))
    st.warning("Anonymity is not absolute: if there is a risk to your safety, safety comes first. "
               "Formal appointments may need your identity.")
    st.subheader("My requests")
    requests = db.student_requests(conn, user["id"])
    if not requests:
        st.info("You haven't sent any requests yet.")
    for r in requests:
        with st.container(border=True):
            st.write(f"**{r['ticket']}** · {r['category']} · {'Anonymous' if r['anonymous'] else 'Identified'} · "
                     f"Status: **{r['status']}**")
            st.write(r["message"])
            if r["reply"]:
                st.info(f"Counsellor reply: {r['reply']}")


def helplines_page(bot):
    st.header("Helplines and resources")
    for name, number, note in C.HELPLINES:
        st.markdown(f"**{name}:** {number} ({note})")
    st.subheader("Knowledge base used by the chatbot")
    for title, source, url in sorted({(c.title, c.source, c.url) for c in bot.retriever.chunks}):
        st.markdown(f"- **{title}** - {source}" + (f" ([link]({url}))" if url else ""))
