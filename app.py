#!/usr/bin/env python3
"""
SEO Cold Email Outreach System — Complete Dashboard App
Modular architecture with campaigns, sequences, reply detection,
email verification, A/B testing, deliverability tools, and autopilot.
"""

import streamlit as st

from core.settings import load_settings, save_settings
from core.database import load_leads, load_sent

# ============================================================
# APP CONFIG
# ============================================================
st.set_page_config(
    page_title="SEO Cold Email System",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Professional dark-accent theme */
    .main-header { font-size: 1.8rem; font-weight: 700; margin-bottom: 0.5rem; }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px; padding: 1.2rem; text-align: center;
        color: white; margin-bottom: 0.5rem;
    }
    .metric-card h3 { color: white; margin: 0; font-size: 0.85rem; opacity: 0.9; }
    .metric-card p { color: white; margin: 0; font-size: 1.6rem; font-weight: 700; }
    .stButton>button { width: 100%; }
    .grade-a { color: #22c55e; font-weight: 700; }
    .grade-b { color: #3b82f6; font-weight: 700; }
    .grade-c { color: #f97316; font-weight: 700; }
    .grade-d { color: #ef4444; font-weight: 700; }
    .sidebar-section { font-size: 0.7rem; color: #6b7280; text-transform: uppercase;
        letter-spacing: 0.05em; margin-top: 1rem; margin-bottom: 0.25rem; font-weight: 600; }
    div[data-testid="stSidebarNav"] { padding-top: 0; }
    section[data-testid="stSidebar"] > div { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# LOAD SETTINGS
# ============================================================
if "settings" not in st.session_state:
    st.session_state.settings = load_settings()

settings = st.session_state.settings

# ============================================================
# SIDEBAR — Grouped Navigation
# ============================================================
st.sidebar.markdown("### SEO Cold Email System")
st.sidebar.markdown("---")

# Group: Lead Generation
st.sidebar.markdown('<p class="sidebar-section">LEAD GENERATION</p>', unsafe_allow_html=True)
lead_gen_pages = ["Dashboard", "Find Leads", "My Leads", "SEO Audit", "Pipeline"]

# Group: Outreach
st.sidebar.markdown('<p class="sidebar-section">OUTREACH</p>', unsafe_allow_html=True)
outreach_pages = ["Campaigns", "Send Emails", "Follow-ups", "Inbox"]

# Group: Analytics
st.sidebar.markdown('<p class="sidebar-section">ANALYTICS</p>', unsafe_allow_html=True)
analytics_pages = ["Campaign Analytics", "Email Health"]

# Group: Settings
st.sidebar.markdown('<p class="sidebar-section">SYSTEM</p>', unsafe_allow_html=True)
system_pages = [
    "Workflows", "Autopilot", "Multi-Channel", "Niche Setup",
    "Backup & Restore", "Settings",
]

all_pages = lead_gen_pages + outreach_pages + analytics_pages + system_pages

page = st.sidebar.radio(
    "Navigate",
    all_pages,
    index=0,
    label_visibility="collapsed",
)

st.sidebar.markdown("---")

# Sidebar metrics
leads_df = load_leads()
sent_df = load_sent()

col1, col2 = st.sidebar.columns(2)
col1.metric("Leads", len(leads_df))
col2.metric("Sent", len(sent_df))

if len(leads_df) > 0 and "lead_grade" in leads_df.columns:
    grades = leads_df["lead_grade"].value_counts()
    a_count = grades.get("A", 0)
    b_count = grades.get("B", 0)
    if a_count or b_count:
        st.sidebar.metric("A/B Grade Leads", f"{a_count}A / {b_count}B")

# Campaign count
try:
    from core.campaigns import CampaignManager
    active_campaigns = [c for c in CampaignManager.list_campaigns() if c.status == "active"]
    if active_campaigns:
        st.sidebar.metric("Active Campaigns", len(active_campaigns))
except Exception:
    pass

# Reply count
try:
    from core.database_v2 import load_replies
    replies = load_replies()
    reply_count = sum(1 for r in replies if not r.get("is_bounce"))
    if reply_count:
        st.sidebar.metric("Replies", reply_count)
except Exception:
    pass

st.sidebar.markdown("---")
st.sidebar.caption("v3.0 — Campaigns | Sequences | Reply Detection | AI")

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

elif page == "Pipeline":
    from pages.pipeline import render
    render(settings)

elif page == "Campaigns":
    from pages.campaigns import render
    render(settings)

elif page == "Send Emails":
    from pages.send_emails import render
    render(settings)

elif page == "Follow-ups":
    from pages.followups import render
    render(settings)

elif page == "Inbox":
    from pages.inbox import render
    render(settings)

elif page == "Campaign Analytics":
    from pages.campaign_analytics import render
    render(settings)

elif page == "Email Health":
    from pages.email_health import render
    render(settings)

elif page == "Workflows":
    from pages.workflows import render
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
