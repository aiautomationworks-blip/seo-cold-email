#!/usr/bin/env python3
"""
SEO Cold Email Outreach System — Complete Dashboard App
Modular architecture with 15 lead sources, lead scoring, 8 templates,
multi-channel outreach, and autopilot automation.
"""

import streamlit as st

from core.settings import load_settings, save_settings
from core.database import load_leads, load_sent

# ============================================================
# APP CONFIG
# ============================================================
st.set_page_config(
    page_title="SEO Cold Email System",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header { font-size: 1.8rem; font-weight: 700; margin-bottom: 0.5rem; }
    .metric-card { background: #f0f2f6; border-radius: 10px; padding: 1rem; text-align: center; }
    .stButton>button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# LOAD SETTINGS
# ============================================================
if "settings" not in st.session_state:
    st.session_state.settings = load_settings()

settings = st.session_state.settings

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.title("SEO Cold Email System")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    [
        "Dashboard",
        "Find Leads",
        "My Leads",
        "SEO Audit",
        "Send Emails",
        "Follow-ups",
        "Autopilot",
        "Multi-Channel",
        "Niche Setup",
        "Backup & Restore",
        "Settings",
    ],
    index=0,
)

st.sidebar.markdown("---")
leads_df = load_leads()
sent_df = load_sent()
st.sidebar.metric("Total Leads", len(leads_df))
st.sidebar.metric("Emails Sent", len(sent_df))

# Lead score summary in sidebar
if len(leads_df) > 0 and "lead_grade" in leads_df.columns:
    import pandas as pd
    grades = leads_df["lead_grade"].value_counts()
    a_count = grades.get("A", 0)
    b_count = grades.get("B", 0)
    if a_count or b_count:
        st.sidebar.metric("A/B Leads", f"{a_count}A / {b_count}B")

st.sidebar.markdown("---")
st.sidebar.caption("v2.0 — 15 Sources | Lead Scoring | Autopilot")

# ============================================================
# PAGE ROUTER
# ============================================================
if page == "Dashboard":
    from pages.dashboard import render
    render(settings)

elif page == "Find Leads":
    from pages.find_leads import render
    render(settings)

elif page == "My Leads":
    from pages.my_leads import render
    render(settings)

elif page == "SEO Audit":
    from pages.seo_audit import render
    render(settings)

elif page == "Send Emails":
    from pages.send_emails import render
    render(settings)

elif page == "Follow-ups":
    from pages.followups import render
    render(settings)

elif page == "Autopilot":
    from pages.autopilot import render
    render(settings)

elif page == "Multi-Channel":
    from pages.multichannel import render
    render(settings)

elif page == "Niche Setup":
    from pages.niche_setup import render
    render(settings)

elif page == "Backup & Restore":
    from pages.backup import render
    render(settings)

elif page == "Settings":
    from pages.settings_page import render
    render(settings)
