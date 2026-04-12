"""Follow-ups page — send scheduled follow-up emails."""

import random
import time
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from core.database import load_leads, save_leads, load_sent, save_sent
from outreach.templates import TEMPLATES, format_template
from outreach.email_sender import send_one_email


def render(settings):
    st.markdown("## Follow-ups")

    if not settings.get("email_accounts"):
        st.warning("Set up your Gmail account in **Settings** first.")
        st.stop()

    sent_df = load_sent()
    leads_df = load_leads()

    if len(sent_df) == 0:
        st.info("No emails sent yet. Go to **Send Emails** first.")
        st.stop()

    followup_days = settings.get("followup_days", [3, 7, 14])
    due = []

    for to_email in sent_df["to_email"].unique():
        # Skip if lead marked as replied/won/lost/do_not_contact
        lead_status = ""
        if len(leads_df) > 0:
            lead_row = leads_df[leads_df["email"] == to_email]
            if len(lead_row) > 0:
                lead_status = str(lead_row.iloc[0].get("status", ""))
        if lead_status in ["replied", "won", "lost", "do_not_contact", "call_booked"]:
            continue

        emails_to = sent_df[sent_df["to_email"] == to_email].sort_values("sent_at")
        num_sent = len(emails_to)
        if num_sent >= 4:
            continue

        last = emails_to.iloc[-1]
        if last.get("status") == "failed":
            continue

        try:
            last_date = datetime.strptime(str(last["sent_at"])[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue

        delay_idx = min(num_sent - 1, len(followup_days) - 1)
        due_date = last_date + timedelta(days=followup_days[delay_idx])

        if datetime.now() >= due_date:
            due.append({
                "to_email": to_email,
                "business_name": str(last.get("business_name", "")),
                "followup_num": num_sent,
                "template": str(last.get("template", list(TEMPLATES.keys())[0])),
                "last_sent": str(last["sent_at"])[:10],
                "days_ago": (datetime.now() - last_date).days,
            })

    if not due:
        st.success("No follow-ups due right now. Check back later!")
        # Show next due date
        next_dates = []
        for to_email in sent_df["to_email"].unique():
            emails_to = sent_df[sent_df["to_email"] == to_email].sort_values("sent_at")
            if len(emails_to) >= 4:
                continue
            last = emails_to.iloc[-1]
            try:
                last_date = datetime.strptime(str(last["sent_at"])[:19], "%Y-%m-%d %H:%M:%S")
                delay_idx = min(len(emails_to) - 1, len(followup_days) - 1)
                nd = last_date + timedelta(days=followup_days[delay_idx])
                if nd > datetime.now():
                    next_dates.append(nd)
            except Exception:
                pass
        if next_dates:
            next_due = min(next_dates)
            st.info(f"Next follow-up due: **{next_due.strftime('%B %d, %Y')}** ({(next_due - datetime.now()).days} days)")
    else:
        st.warning(f"**{len(due)} follow-ups are due!**")
        due_df = pd.DataFrame(due)
        st.dataframe(
            due_df[["business_name", "to_email", "followup_num", "last_sent", "days_ago"]],
            use_container_width=True, hide_index=True,
        )

        if st.button("SEND ALL FOLLOW-UPS", type="primary", use_container_width=True):
            account = settings["email_accounts"][0]
            progress = st.progress(0)
            status_area = st.empty()
            sent_count = 0

            for i, item in enumerate(due):
                progress.progress((i + 1) / len(due))
                status_area.text(f"Following up {i+1}/{len(due)}: {item['to_email']}...")

                lead_row = leads_df[leads_df["email"] == item["to_email"]]
                lead = lead_row.iloc[0] if len(lead_row) > 0 else {}

                variables = {
                    "business_name": str(item.get("business_name", "")),
                    "website": str(lead.get("website", "")) if isinstance(lead, pd.Series) else "",
                    "niche": str(lead.get("niche", "business")) if isinstance(lead, pd.Series) else "business",
                    "location": str(lead.get("location", "")) if isinstance(lead, pd.Series) else "",
                    "seo_issues": str(lead.get("seo_issues", "")) if isinstance(lead, pd.Series) else "",
                    "your_name": settings.get("your_name", ""),
                    "your_company": settings.get("your_company", ""),
                    "your_phone": settings.get("your_phone", ""),
                    "your_calendly": settings.get("your_calendly", ""),
                }

                template_name = item["template"] if item["template"] in TEMPLATES else list(TEMPLATES.keys())[0]
                subj, body = format_template(template_name, variables, followup_num=item["followup_num"])
                success, error = send_one_email(account, item["to_email"], subj, body)

                sent_record = {
                    "to_email": item["to_email"],
                    "business_name": item["business_name"],
                    "subject": subj,
                    "template": template_name,
                    "followup_num": item["followup_num"],
                    "from_email": account["email"],
                    "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "sent" if success else "failed",
                }
                sent_df_updated = load_sent()
                sent_df_updated = pd.concat([sent_df_updated, pd.DataFrame([sent_record])], ignore_index=True)
                save_sent(sent_df_updated)

                if success:
                    sent_count += 1
                    leads_df.loc[leads_df["email"] == item["to_email"], "status"] = "followed_up"
                    save_leads(leads_df)

                if i < len(due) - 1:
                    delay = random.uniform(settings.get("delay_min", 45), settings.get("delay_max", 120))
                    status_area.text(f"Waiting {delay:.0f}s...")
                    time.sleep(delay)

            progress.progress(1.0)
            status_area.text("")
            st.success(f"Sent {sent_count}/{len(due)} follow-ups!")
            st.rerun()
