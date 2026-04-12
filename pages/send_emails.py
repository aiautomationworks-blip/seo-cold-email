"""Send Emails page — select template, preview, and send cold emails."""

import random
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from core.database import load_leads, save_leads, load_sent, save_sent
from outreach.templates import TEMPLATES, format_template, template_names
from outreach.email_sender import send_one_email


def render(settings):
    st.markdown("## Send Cold Emails")

    if not settings.get("email_accounts"):
        st.warning("Set up your Gmail account in **Settings** first.")
        st.stop()

    leads_df = load_leads()
    sent_df = load_sent()

    # Filter unsent leads
    sent_emails = set(sent_df["to_email"].tolist()) if len(sent_df) > 0 else set()
    unsent = leads_df[
        (leads_df["email"].notna()) &
        (leads_df["email"] != "") &
        (~leads_df["email"].isin(sent_emails)) &
        (leads_df["status"].fillna("new").isin(["new"]))
    ]

    # Sort by lead score if available
    if "lead_score" in unsent.columns:
        unsent["lead_score"] = pd.to_numeric(unsent["lead_score"], errors="coerce")
        unsent = unsent.sort_values("lead_score", ascending=False)

    st.info(f"**{len(unsent)} leads** ready to email (sorted by lead score)")

    # Template selection
    template_name = st.selectbox("Choose email template", template_names())

    # Priority filter
    send_priority = st.selectbox(
        "Send to",
        ["All unsent leads", "A-grade leads only (80+)", "A & B-grade leads (60+)"],
    )

    if send_priority == "A-grade leads only (80+)" and "lead_score" in unsent.columns:
        unsent = unsent[unsent["lead_score"] >= 80]
    elif send_priority == "A & B-grade leads (60+)" and "lead_score" in unsent.columns:
        unsent = unsent[unsent["lead_score"] >= 60]

    # Preview
    st.markdown("### Preview")
    if len(unsent) > 0:
        preview_lead = unsent.iloc[0]
        variables = _build_variables(preview_lead, settings)
        subj, body = format_template(template_name, variables)
        st.markdown(f"**To:** {preview_lead.get('email', '')}")
        if "lead_score" in preview_lead.index:
            st.markdown(f"**Lead Score:** {preview_lead.get('lead_score', 'N/A')} ({preview_lead.get('lead_grade', '')})")
        st.markdown(f"**Subject:** {subj}")
        st.text_area("Email body", body, height=300, disabled=True)
    else:
        st.warning("No leads matching this filter.")

    # Send controls
    st.markdown("### Send")
    col1, col2 = st.columns(2)
    with col1:
        max_to_send = st.number_input(
            "How many to send now?",
            min_value=1,
            max_value=min(50, max(len(unsent), 1)),
            value=min(5, max(len(unsent), 1)),
        )
    with col2:
        account = settings["email_accounts"][0]
        st.text_input("Sending from", value=account["email"], disabled=True)

    if st.button("SEND EMAILS", type="primary", use_container_width=True):
        if len(unsent) == 0:
            st.warning("No leads to email.")
        else:
            progress = st.progress(0)
            status_area = st.empty()
            results_log = []

            for i, (idx, lead) in enumerate(unsent.head(max_to_send).iterrows()):
                progress.progress((i + 1) / max_to_send)
                to_email = str(lead["email"])
                status_area.text(f"Sending {i+1}/{max_to_send}: {to_email}...")

                variables = _build_variables(lead, settings)
                subj, body = format_template(template_name, variables)
                success, error = send_one_email(account, to_email, subj, body)

                # Log it
                sent_record = {
                    "to_email": to_email,
                    "business_name": str(lead.get("business_name", "")),
                    "subject": subj,
                    "template": template_name,
                    "followup_num": 0,
                    "from_email": account["email"],
                    "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "sent" if success else "failed",
                }
                sent_df = load_sent()
                sent_df = pd.concat([sent_df, pd.DataFrame([sent_record])], ignore_index=True)
                save_sent(sent_df)

                # Update lead status
                leads_df = load_leads()
                leads_df.loc[leads_df["email"] == to_email, "status"] = "contacted"
                save_leads(leads_df)

                status_emoji = "sent" if success else "FAILED"
                results_log.append(f"{status_emoji} -> {to_email}" + (f" ({error})" if error else ""))

                if i < max_to_send - 1:
                    delay = random.uniform(
                        settings.get("delay_min", 45),
                        settings.get("delay_max", 120),
                    )
                    status_area.text(f"Waiting {delay:.0f}s before next email...")
                    time.sleep(delay)

            progress.progress(1.0)
            status_area.text("")

            sent_count = sum(1 for r in results_log if r.startswith("sent"))
            st.success(f"Done! Sent {sent_count}/{max_to_send} emails.")

            for r in results_log:
                if r.startswith("sent"):
                    st.markdown(f"- {r}")
                else:
                    st.markdown(f"- :red[{r}]")


def _build_variables(lead, settings):
    """Build template variables from a lead row and settings."""
    return {
        "business_name": str(lead.get("business_name", "the business")),
        "website": str(lead.get("website", "")),
        "niche": str(lead.get("niche", "business")),
        "location": str(lead.get("location", "your area")),
        "seo_issues": str(lead.get("seo_issues", "a few SEO improvements")),
        "your_name": settings.get("your_name", ""),
        "your_company": settings.get("your_company", ""),
        "your_phone": settings.get("your_phone", ""),
        "your_calendly": settings.get("your_calendly", ""),
    }
