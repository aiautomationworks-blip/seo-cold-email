"""Unified Inbox — check for replies, view conversations, take actions."""

import streamlit as st
from datetime import datetime

from core.database_v2 import load_replies, load_email_accounts, update_lead_status
from outreach.inbox_monitor import InboxMonitor


def render(settings):
    st.markdown("## Inbox")

    # ─── Check for Replies ───
    col1, col2 = st.columns([3, 1])
    with col1:
        days_back = st.number_input("Check last N days", 1, 30, 7, key="inbox_days")
    with col2:
        st.markdown("")
        st.markdown("")
        check = st.button("Check for Replies", type="primary", use_container_width=True)

    if check:
        accounts = settings.get("email_accounts", [])
        db_accounts = load_email_accounts()
        all_accounts = accounts + [a for a in db_accounts if a["email"] not in {ac.get("email") for ac in accounts}]

        if not all_accounts:
            st.error("No email accounts configured. Add your Gmail in Settings first.")
        else:
            total_replies = 0
            total_bounces = 0
            for acc in all_accounts:
                # Need IMAP credentials (same as SMTP for Gmail)
                imap_acc = {
                    "email": acc.get("email", ""),
                    "password": acc.get("password", ""),
                    "imap_server": acc.get("imap_server", "imap.gmail.com"),
                    "imap_port": acc.get("imap_port", 993),
                }
                monitor = InboxMonitor(imap_acc)
                with st.spinner(f"Checking {acc.get('email', '')}..."):
                    replies, err = monitor.check_replies(since_days=days_back)
                    bounces, err2 = monitor.check_bounces(since_days=days_back)

                    if err:
                        st.warning(f"Error for {acc.get('email', '')}: {err}")
                    if err2:
                        st.warning(f"Bounce check error: {err2}")

                    all_found = replies + bounces
                    if all_found:
                        new_replies, bounce_count = monitor.process_replies(all_found)
                        total_replies += new_replies
                        total_bounces += bounce_count

                    monitor.disconnect()

            if total_replies or total_bounces:
                st.success(f"Found {total_replies} new replies and {total_bounces} bounces")
            else:
                st.info("No new replies found")

    st.markdown("---")

    # ─── Reply List ───
    replies = load_replies()

    if not replies:
        st.info("No replies yet. Click 'Check for Replies' above to scan your inbox.")
        return

    # Stats
    total = len(replies)
    actual_replies = sum(1 for r in replies if not r.get("is_bounce") and not r.get("is_auto_reply"))
    bounces = sum(1 for r in replies if r.get("is_bounce"))
    auto_replies = sum(1 for r in replies if r.get("is_auto_reply"))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total", total)
    col2.metric("Replies", actual_replies)
    col3.metric("Bounces", bounces)
    col4.metric("Auto-replies", auto_replies)

    # Calculate reply rate
    from core.database_v2 import load_sent
    sent_df = load_sent()
    unique_sent = len(sent_df["to_email"].unique()) if len(sent_df) > 0 else 0
    if unique_sent > 0:
        reply_rate = round(actual_replies / unique_sent * 100, 1)
        st.metric("Reply Rate", f"{reply_rate}%")

    st.markdown("---")

    # Filter
    filter_type = st.selectbox("Show", ["All", "Replies Only", "Bounces Only", "Auto-replies"])

    filtered = replies
    if filter_type == "Replies Only":
        filtered = [r for r in replies if not r.get("is_bounce") and not r.get("is_auto_reply")]
    elif filter_type == "Bounces Only":
        filtered = [r for r in replies if r.get("is_bounce")]
    elif filter_type == "Auto-replies":
        filtered = [r for r in replies if r.get("is_auto_reply")]

    # Display replies
    for i, reply in enumerate(filtered[:50]):
        is_bounce = reply.get("is_bounce")
        is_auto = reply.get("is_auto_reply")
        sentiment = reply.get("sentiment", "")

        if is_bounce:
            prefix = "[BOUNCE]"
        elif is_auto:
            prefix = "[AUTO]"
        elif sentiment == "positive":
            prefix = "[+]"
        elif sentiment == "negative":
            prefix = "[-]"
        else:
            prefix = ""

        label = f"{prefix} {reply.get('from_email', 'Unknown')} — {reply.get('subject', 'No subject')[:50]}"
        date_str = reply.get("received_at", "")[:10]
        if date_str:
            label += f" ({date_str})"

        with st.expander(label):
            st.markdown(f"**From:** {reply.get('from_email', '')}")
            st.markdown(f"**Date:** {reply.get('received_at', '')}")
            st.markdown(f"**Subject:** {reply.get('subject', '')}")
            if reply.get("campaign_id"):
                st.markdown(f"**Campaign:** {reply.get('campaign_id', '')}")
            if sentiment:
                st.markdown(f"**Sentiment:** {sentiment}")

            st.markdown("---")
            body = reply.get("body", "No content")
            st.text(body[:1000])

            # Quick actions
            if not is_bounce:
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("Mark as Won", key=f"won_{i}"):
                        update_lead_status(reply["from_email"], "won")
                        st.success("Marked as won!")
                with col2:
                    if st.button("Book Call", key=f"call_{i}"):
                        update_lead_status(reply["from_email"], "call_booked")
                        st.success("Marked as call booked!")
                with col3:
                    if st.button("Not Interested", key=f"lost_{i}"):
                        update_lead_status(reply["from_email"], "lost")
                        st.success("Marked as lost")
