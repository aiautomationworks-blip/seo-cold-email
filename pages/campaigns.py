"""Campaigns page — create, manage, and monitor email campaigns."""

import json
import streamlit as st

from core.campaigns import (
    CampaignManager, Campaign, SequenceStep, build_default_sequence,
)
from core.database_v2 import load_leads, load_email_accounts
from outreach.templates import TEMPLATES, template_names


def render(settings):
    st.markdown("## Campaigns")

    tab1, tab2 = st.tabs(["My Campaigns", "Create Campaign"])

    with tab1:
        _render_campaign_list()

    with tab2:
        _render_create_campaign(settings)


def _render_campaign_list():
    """Show all campaigns with stats."""
    campaigns = CampaignManager.list_campaigns()

    if not campaigns:
        st.info("No campaigns yet. Create your first campaign to get started.")
        return

    for campaign in campaigns:
        stats = CampaignManager.get_stats(campaign.id)
        status_colors = {
            "draft": "gray", "active": "green",
            "paused": "orange", "completed": "blue",
        }
        color = status_colors.get(campaign.status, "gray")

        with st.expander(f"{campaign.name} — {campaign.status.upper()}", expanded=campaign.status == "active"):
            # Stats row
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Leads", stats.get("total_leads", 0))
            col2.metric("Sent", stats.get("sent", 0))
            col3.metric("Replied", stats.get("replied", 0))
            col4.metric("Bounced", stats.get("bounced", 0))
            col5.metric("Reply Rate", f"{stats.get('reply_rate', 0)}%")

            # Campaign info
            st.caption(
                f"Template: {campaign.template} | "
                f"Steps: {len(campaign.sequence)} | "
                f"Account: {campaign.account_email or 'Default'} | "
                f"Created: {campaign.created_at[:10] if campaign.created_at else 'N/A'}"
            )

            # Sequence steps
            if campaign.sequence:
                st.markdown("**Sequence Steps:**")
                for i, step in enumerate(campaign.sequence):
                    delay_text = f" (wait {step.delay_days}d)" if step.delay_days > 0 else " (immediate)"
                    ab_text = " [A/B]" if step.variant_b_subject else ""
                    st.markdown(f"  {i+1}. {step.subject[:60]}...{delay_text}{ab_text}")

            # Actions
            col1, col2, col3 = st.columns(3)
            with col1:
                if campaign.status == "draft":
                    if st.button("Activate", key=f"act_{campaign.id}", use_container_width=True):
                        CampaignManager.activate_campaign(campaign.id)
                        st.success("Campaign activated!")
                        st.rerun()
                elif campaign.status == "active":
                    if st.button("Pause", key=f"pause_{campaign.id}", use_container_width=True):
                        CampaignManager.pause_campaign(campaign.id)
                        st.success("Campaign paused")
                        st.rerun()
                elif campaign.status == "paused":
                    if st.button("Resume", key=f"resume_{campaign.id}", use_container_width=True):
                        CampaignManager.resume_campaign(campaign.id)
                        st.success("Campaign resumed!")
                        st.rerun()

            with col2:
                if campaign.status in ("active", "paused"):
                    if st.button("Complete", key=f"done_{campaign.id}", use_container_width=True):
                        CampaignManager.complete_campaign(campaign.id)
                        st.success("Campaign completed")
                        st.rerun()

            # Detail view — per-step stats
            if stats.get("sent", 0) > 0:
                st.markdown("---")
                st.markdown("**Per-Step Performance:**")
                from core.database_v2 import get_connection, _ensure_db
                _ensure_db()
                conn = get_connection()
                try:
                    for i, step in enumerate(campaign.sequence):
                        step_sent = conn.execute(
                            "SELECT COUNT(*) FROM sent_emails WHERE campaign_id=? AND sequence_step=?",
                            (campaign.id, i),
                        ).fetchone()[0]
                        step_replied = conn.execute(
                            "SELECT COUNT(*) FROM replies WHERE campaign_id=? AND is_bounce=0",
                            (campaign.id,),
                        ).fetchone()[0] if i == 0 else 0  # Simplified

                        step_rate = round(step_replied / step_sent * 100, 1) if step_sent > 0 else 0
                        st.markdown(
                            f"  Step {i+1}: {step_sent} sent"
                            f"{f' | {step_replied} replied ({step_rate}%)' if step_replied else ''}"
                        )
                finally:
                    conn.close()


def _render_create_campaign(settings):
    """Campaign creation wizard."""
    st.markdown("### Create New Campaign")

    with st.form("create_campaign"):
        # Step 1: Name
        name = st.text_input("Campaign Name *", placeholder="e.g., Dentists Hyderabad Q1")

        # Step 2: Template
        tmpl_name = st.selectbox("Base Template", template_names())

        # Step 3: Account
        accounts = settings.get("email_accounts", [])
        db_accounts = load_email_accounts()
        all_account_emails = list({
            a.get("email", "") for a in accounts if a.get("email")
        } | {
            a.get("email", "") for a in db_accounts if a.get("email")
        })

        account_email = ""
        if all_account_emails:
            account_email = st.selectbox("Send From", all_account_emails)
        else:
            st.warning("No email accounts configured. Add one in Settings first.")

        # Step 4: Daily limit
        daily_limit = st.number_input("Daily send limit for this campaign", 1, 50, 5)

        # Step 5: Customize sequence
        st.markdown("---")
        st.markdown("**Email Sequence**")
        st.caption("The sequence is auto-built from your template. You can customize delays.")

        default_steps = build_default_sequence(tmpl_name)
        delays = []
        for i, step in enumerate(default_steps):
            if i == 0:
                st.markdown(f"**Step 1:** Initial outreach (sent immediately)")
                delays.append(0)
            else:
                d = st.number_input(
                    f"Step {i+1}: Wait days after previous",
                    1, 30, step.delay_days,
                    key=f"delay_{i}",
                )
                delays.append(d)

        # Step 6: Select leads
        st.markdown("---")
        st.markdown("**Assign Leads**")
        leads_df = load_leads()

        lead_filter = "new"
        if len(leads_df) > 0:
            available_statuses = ["new"] + sorted(
                [s for s in leads_df["status"].dropna().unique() if s != "new"]
            )
            lead_filter = st.selectbox("Lead status to include", available_statuses)

        submitted = st.form_submit_button("Create Campaign", type="primary", use_container_width=True)

    if submitted:
        if not name:
            st.error("Please enter a campaign name")
            return

        # Build sequence with custom delays
        sequence = build_default_sequence(tmpl_name)
        for i, step in enumerate(sequence):
            if i < len(delays):
                step.delay_days = delays[i]

        # Create campaign
        campaign = CampaignManager.create_campaign(
            name=name,
            template=tmpl_name,
            sequence=sequence,
            account_email=account_email,
            daily_limit=daily_limit,
        )

        # Assign leads
        if len(leads_df) > 0:
            matching = leads_df[leads_df["status"].fillna("new") == lead_filter]
            matching = matching[matching["email"].notna() & (matching["email"] != "")]
            if len(matching) > 0:
                CampaignManager.assign_leads(
                    campaign.id,
                    matching["email"].tolist(),
                )
                st.success(
                    f"Campaign '{name}' created with {len(matching)} leads "
                    f"and {len(sequence)} sequence steps!"
                )
            else:
                st.success(f"Campaign '{name}' created. No matching leads found to assign.")
        else:
            st.success(f"Campaign '{name}' created. Add leads to assign them later.")

        st.rerun()
