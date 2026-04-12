"""Backup & Restore page — download and restore data."""

import json
from datetime import datetime

import pandas as pd
import streamlit as st

from core.database import load_leads, save_leads, load_sent, save_sent
from core.settings import load_settings


def render(settings):
    st.markdown("## Backup & Restore")
    st.markdown("Download your data regularly so you never lose it.")

    # ─── Download ───
    st.markdown("### Download Backup")
    col1, col2, col3 = st.columns(3)

    with col1:
        leads_df = load_leads()
        if len(leads_df) > 0:
            st.download_button(
                f"Download Leads ({len(leads_df)})",
                leads_df.to_csv(index=False),
                f"leads_backup_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                use_container_width=True,
            )
        else:
            st.info("No leads to backup")

    with col2:
        sent_df = load_sent()
        if len(sent_df) > 0:
            st.download_button(
                f"Download Sent Emails ({len(sent_df)})",
                sent_df.to_csv(index=False),
                f"sent_backup_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                use_container_width=True,
            )
        else:
            st.info("No sent emails to backup")

    with col3:
        settings_copy = dict(load_settings())
        for acc in settings_copy.get("email_accounts", []):
            acc["password"] = "***HIDDEN***"
        st.download_button(
            "Download Settings",
            json.dumps(settings_copy, indent=2),
            "settings_backup.json",
            "application/json",
            use_container_width=True,
        )

    # ─── Restore ───
    st.markdown("---")
    st.markdown("### Restore from Backup")

    tab1, tab2 = st.tabs(["Restore Leads", "Restore Sent Emails"])

    with tab1:
        uploaded_leads = st.file_uploader("Upload leads CSV backup", type=["csv"], key="restore_leads")
        if uploaded_leads:
            try:
                restored = pd.read_csv(uploaded_leads)
                st.markdown(f"Found **{len(restored)} leads** in backup")
                st.dataframe(restored.head(5), use_container_width=True, hide_index=True)
                if st.button("Restore These Leads", type="primary"):
                    existing = load_leads()
                    combined = pd.concat([existing, restored], ignore_index=True)
                    combined = combined.drop_duplicates(subset=["email", "website"], keep="last")
                    save_leads(combined)
                    st.success(f"Restored! Total leads now: {len(combined)}")
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    with tab2:
        uploaded_sent = st.file_uploader("Upload sent emails CSV backup", type=["csv"], key="restore_sent")
        if uploaded_sent:
            try:
                restored_sent = pd.read_csv(uploaded_sent)
                st.markdown(f"Found **{len(restored_sent)} sent records** in backup")
                if st.button("Restore Sent Records", type="primary"):
                    existing_sent = load_sent()
                    combined_sent = pd.concat([existing_sent, restored_sent], ignore_index=True)
                    combined_sent = combined_sent.drop_duplicates(subset=["to_email", "sent_at"], keep="last")
                    save_sent(combined_sent)
                    st.success(f"Restored! Total sent records: {len(combined_sent)}")
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
