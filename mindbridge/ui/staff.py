# Generated with AI assistance (Claude, Anthropic) - reviewed and tested by the team
# (whole file written with AI help in Stage 1, Nov 2026)
"""Counsellor and admin pages.

The admin page uses analytics.py only (group totals). It must never call the
db.py functions that read one student's check-ins, notes or chats.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import analytics, config as C, db


def counsellor_page(conn):
    st.header("Counsellor view (demo)")
    st.caption("Anonymous requests show only the ticket ID, category and message, never the student's name.")
    queue = db.counsellor_queue(conn)
    if not queue:
        st.info("No requests yet.")
    for r in queue:
        with st.container(border=True):
            who = "Anonymous" if r["anonymous"] else r["student_name"]
            st.write(f"**{r['ticket']}** · {who} · {r['category']} · {r['created_at']} · **{r['status']}**")
            st.write(r["message"])
            if r["status"] == "Pending":
                rep = st.text_area("Reply", key=f"rep_{r['ticket']}")
                if st.button("Send reply", key=f"btn_{r['ticket']}") and rep.strip():
                    db.reply_request(conn, r["ticket"], rep.strip())
                    st.rerun()
            else:
                st.info(r["reply"])


def admin_page(conn):
    st.header("Institutional dashboard")
    st.caption("Group totals only. No chats, notes or individual check-ins are shown.")
    st.warning("These are plain totals. Differential privacy is not implemented yet; this page will be "
               "replaced by privacy-protected monthly reports in the next stage.")
    o = analytics.agg_overview(conn)
    cols = st.columns(4)
    cols[0].metric("Students", o["students"])
    cols[1].metric("Avg wellbeing (1-5)", o["avg_wellbeing"] or "-")
    cols[2].metric("Counsellor requests", o["requests"], f"{o['pending']} pending", delta_color="off")
    cols[3].metric("Crisis routes", o["crisis_routes"])
    c1, c2 = st.columns(2)
    con = pd.DataFrame([dict(r) for r in analytics.agg_concerns(conn)])
    if not con.empty:
        con["concern"] = con["concern"].map(C.LABEL_NAMES)
        c1.subheader("Concerns")
        c1.bar_chart(con.set_index("concern"))
    pw = pd.DataFrame([dict(r) for r in analytics.agg_pathways(conn)])
    if not pw.empty:
        pw["pathway"] = pw["pathway"].map(lambda lvl: C.PATHWAYS[lvl][0])
        c2.subheader("Support pathways")
        c2.bar_chart(pw.set_index("pathway"))
    wk = pd.DataFrame([dict(r) for r in analytics.agg_weekly_wellbeing(conn)])
    if not wk.empty:
        st.subheader("Average wellbeing per week")
        st.line_chart(wk.set_index("week")["avg_wb"])
    if con.empty and pw.empty and wk.empty:
        st.info("No data yet.")
