"""Dashboard page — overview, funnel, revenue projection, lead score distribution."""

import pandas as pd
import streamlit as st

from core.database import load_leads, load_sent
from core.constants import NICHE_PROFILES


def render(settings):
    st.markdown("## Dashboard")

    if not settings.get("your_name"):
        st.warning("Go to **Settings** first to set up your name, email account, and targets.")
        st.stop()

    leads_df = load_leads()
    sent_df = load_sent()

    # ─── Top Metrics ───
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Leads", len(leads_df))
    with col2:
        st.metric("Emails Sent", len(sent_df))
    with col3:
        replied = len(leads_df[leads_df["status"] == "replied"]) if len(leads_df) > 0 and "status" in leads_df.columns else 0
        st.metric("Replies", replied)
    with col4:
        won = len(leads_df[leads_df["status"] == "won"]) if len(leads_df) > 0 and "status" in leads_df.columns else 0
        st.metric("Clients Won", won)

    st.markdown("---")

    # ─── Conversion Funnel ───
    if len(leads_df) > 0 and "status" in leads_df.columns:
        st.markdown("### Conversion Funnel")

        total = len(leads_df)
        contacted = len(leads_df[leads_df["status"].isin(["contacted", "followed_up", "replied", "call_booked", "proposal_sent", "won"])])
        followed = len(leads_df[leads_df["status"].isin(["followed_up", "replied", "call_booked", "proposal_sent", "won"])])
        replied_count = len(leads_df[leads_df["status"].isin(["replied", "call_booked", "proposal_sent", "won"])])
        won_count = len(leads_df[leads_df["status"] == "won"])

        funnel_data = {
            "Stage": ["Total Leads", "Contacted", "Followed Up", "Replied", "Won"],
            "Count": [total, contacted, followed, replied_count, won_count],
        }
        funnel_df = pd.DataFrame(funnel_data)
        st.bar_chart(funnel_df.set_index("Stage"))

        # Conversion rates
        col1, col2, col3 = st.columns(3)
        with col1:
            rate = (contacted / total * 100) if total > 0 else 0
            st.metric("Contact Rate", f"{rate:.0f}%")
        with col2:
            rate = (replied_count / contacted * 100) if contacted > 0 else 0
            st.metric("Reply Rate", f"{rate:.0f}%")
        with col3:
            rate = (won_count / replied_count * 100) if replied_count > 0 else 0
            st.metric("Close Rate", f"{rate:.0f}%")

    # ─── Lead Score Distribution ───
    if len(leads_df) > 0 and "lead_score" in leads_df.columns:
        scores = pd.to_numeric(leads_df["lead_score"], errors="coerce").dropna()
        if len(scores) > 0:
            st.markdown("### Lead Score Distribution")
            col1, col2, col3 = st.columns(3)
            with col1:
                a_leads = len(scores[scores >= 80])
                st.metric("A-Grade Leads (80+)", a_leads)
            with col2:
                b_leads = len(scores[(scores >= 60) & (scores < 80)])
                st.metric("B-Grade Leads (60-79)", b_leads)
            with col3:
                avg = scores.mean()
                st.metric("Avg Lead Score", f"{avg:.0f}")

    # ─── Revenue Projection ───
    if len(leads_df) > 0:
        st.markdown("### Revenue Projection")
        st.markdown("*Based on industry averages and your pipeline*")

        # Calculate based on niche profiles
        total_projected = 0
        niche_counts = leads_df["niche"].value_counts() if "niche" in leads_df.columns else pd.Series()

        for niche_name, count in niche_counts.items():
            niche_lower = str(niche_name).lower().replace(" ", "_")
            for key, profile in NICHE_PROFILES.items():
                if key in niche_lower or niche_lower in key:
                    avg_deal = profile.get("avg_deal_value", 1000)
                    # Assume 2% conversion from lead to client
                    projected = count * 0.02 * avg_deal
                    total_projected += projected
                    break

        if total_projected > 0:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Pipeline Value (est.)", f"${total_projected:,.0f}")
            with col2:
                st.metric("At 2% Close Rate", f"${total_projected:,.0f}/year")

    # ─── Pipeline Chart ───
    if len(leads_df) > 0 and "status" in leads_df.columns:
        st.markdown("### Pipeline Status")
        status_counts = leads_df["status"].fillna("new").value_counts()
        st.bar_chart(status_counts)

    # ─── Recent Emails ───
    if len(sent_df) > 0:
        st.markdown("### Recent Emails Sent")
        display_cols = [c for c in ["to_email", "business_name", "template", "followup_num", "sent_at", "status"]
                       if c in sent_df.columns]
        recent = sent_df.tail(10)
        if "sent_at" in sent_df.columns:
            recent = sent_df.sort_values("sent_at", ascending=False).head(10)
        st.dataframe(recent[display_cols], use_container_width=True, hide_index=True)

    # ─── Quick Actions ───
    st.markdown("### Quick Actions")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.button("Find New Leads", use_container_width=True, key="dash_find")
    with col2:
        st.button("Send Emails", use_container_width=True, key="dash_send")
    with col3:
        st.button("Send Follow-ups", use_container_width=True, key="dash_followup")
