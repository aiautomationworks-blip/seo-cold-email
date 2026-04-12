"""Campaign Analytics page — per-campaign funnel, A/B results, insights."""

import streamlit as st

from core.campaigns import CampaignManager
from core.database_v2 import (
    get_connection, _ensure_db, load_sent, load_replies,
)


def render(settings):
    st.markdown("## Campaign Analytics")

    campaigns = CampaignManager.list_campaigns()
    if not campaigns:
        st.info("No campaigns yet. Create one in the Campaigns page.")
        return

    # Campaign selector
    campaign_names = {c.id: c.name for c in campaigns}
    selected_id = st.selectbox(
        "Select Campaign",
        list(campaign_names.keys()),
        format_func=lambda x: campaign_names[x],
    )

    campaign = CampaignManager.get_campaign(selected_id)
    if not campaign:
        st.error("Campaign not found")
        return

    stats = CampaignManager.get_stats(selected_id)

    # ─── Funnel Metrics ───
    st.markdown("### Campaign Funnel")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Leads", stats.get("total_leads", 0))
    col2.metric("Emails Sent", stats.get("sent", 0))
    col3.metric("Delivered", stats.get("sent", 0) - stats.get("bounced", 0))
    col4.metric("Replied", stats.get("replied", 0))

    # Calculate won from leads
    from core.database_v2 import get_leads_for_campaign
    leads_df = get_leads_for_campaign(selected_id)
    won = len(leads_df[leads_df["status"] == "won"]) if len(leads_df) > 0 else 0
    col5.metric("Won", won)

    # Rates
    sent = stats.get("sent", 0)
    if sent > 0:
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.metric("Reply Rate", f"{stats.get('reply_rate', 0)}%")
        col2.metric("Bounce Rate", f"{stats.get('bounce_rate', 0)}%")

        conversion = round(won / stats["total_leads"] * 100, 1) if stats["total_leads"] > 0 else 0
        col3.metric("Conversion Rate", f"{conversion}%")

    # ─── Per-Step Performance ───
    if campaign.sequence and sent > 0:
        st.markdown("---")
        st.markdown("### Per-Step Performance")

        _ensure_db()
        conn = get_connection()
        try:
            for i, step in enumerate(campaign.sequence):
                step_sent = conn.execute(
                    "SELECT COUNT(*) FROM sent_emails WHERE campaign_id=? AND sequence_step=?",
                    (selected_id, i),
                ).fetchone()[0]

                if step_sent == 0:
                    st.markdown(f"**Step {i+1}:** {step.subject[:50]}... — Not sent yet")
                    continue

                # A/B variant breakdown
                variant_a = conn.execute(
                    "SELECT COUNT(*) FROM sent_emails WHERE campaign_id=? AND sequence_step=? AND (variant='A' OR variant='')",
                    (selected_id, i),
                ).fetchone()[0]
                variant_b = conn.execute(
                    "SELECT COUNT(*) FROM sent_emails WHERE campaign_id=? AND sequence_step=? AND variant='B'",
                    (selected_id, i),
                ).fetchone()[0]

                ab_text = ""
                if variant_b > 0:
                    ab_text = f" (A: {variant_a} | B: {variant_b})"

                st.markdown(f"**Step {i+1}:** {step_sent} sent{ab_text}")
        finally:
            conn.close()

    # ─── Reply Analysis ───
    replies = load_replies()
    campaign_replies = [r for r in replies if r.get("campaign_id") == selected_id and not r.get("is_bounce")]

    if campaign_replies:
        st.markdown("---")
        st.markdown("### Reply Breakdown")

        sentiments = {"positive": 0, "negative": 0, "neutral": 0}
        for r in campaign_replies:
            s = r.get("sentiment", "neutral")
            sentiments[s] = sentiments.get(s, 0) + 1

        col1, col2, col3 = st.columns(3)
        col1.metric("Positive", sentiments["positive"])
        col2.metric("Neutral", sentiments["neutral"])
        col3.metric("Negative", sentiments["negative"])

    # ─── Best Performing Templates ───
    st.markdown("---")
    st.markdown("### Template Performance (All Campaigns)")

    import pandas as pd
    sent_df = load_sent()
    if len(sent_df) > 0 and "template" in sent_df.columns:
        template_stats = []
        for tmpl in sent_df["template"].dropna().unique():
            tmpl_sent = sent_df[sent_df["template"] == tmpl]
            t_count = len(tmpl_sent)
            t_emails = set(tmpl_sent["to_email"].tolist())
            t_replies = sum(
                1 for r in replies
                if r.get("from_email") in t_emails and not r.get("is_bounce")
            )
            rate = round(t_replies / t_count * 100, 1) if t_count > 0 else 0
            template_stats.append({
                "Template": tmpl,
                "Sent": t_count,
                "Replies": t_replies,
                "Reply Rate": f"{rate}%",
            })

        if template_stats:
            template_stats.sort(key=lambda x: x["Replies"], reverse=True)
            st.dataframe(pd.DataFrame(template_stats), use_container_width=True, hide_index=True)

    # ─── Revenue Attribution ───
    if won > 0 and len(leads_df) > 0:
        st.markdown("---")
        st.markdown("### Revenue Attribution")
        won_leads = leads_df[leads_df["status"] == "won"]
        total_value = won_leads["deal_value"].sum() if "deal_value" in won_leads.columns else 0
        if total_value > 0:
            st.metric("Total Revenue", f"${total_value:,.0f}")
            cost_per_lead = 0  # Free tools
            st.metric("Cost per Won Lead", "$0 (free tools)")
