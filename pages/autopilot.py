"""Autopilot page — configure and trigger 24/7 automated outreach via GitHub Actions."""

import streamlit as st

from core.settings import save_settings
from outreach.templates import template_names


def render(settings):
    st.markdown("## Autopilot Mode")
    st.markdown("Set up 24/7 automated lead finding and emailing via GitHub Actions (free).")

    # ─── Status ───
    enabled = settings.get("autopilot_enabled", False)
    if enabled:
        st.success("Autopilot is ENABLED. GitHub Actions will run daily at 9 AM UTC.")
    else:
        st.info("Autopilot is currently disabled.")

    # ─── Configuration ───
    st.markdown("### Configure Autopilot")

    with st.form("autopilot_form"):
        col1, col2 = st.columns(2)

        with col1:
            ap_niches = st.multiselect(
                "Niches to target on autopilot",
                ["dentist", "plastic surgeon", "real estate agent", "med spa",
                 "chiropractor", "plumber", "roofing contractor", "lawyer",
                 "hvac contractor", "electrician"],
                default=settings.get("autopilot_niches", settings.get("target_niches", ["dentist"])),
            )
            ap_template = st.selectbox(
                "Email template",
                template_names(),
                index=0,
            )

        with col2:
            ap_locations_text = st.text_area(
                "Target cities (one per line)",
                value="\n".join(settings.get("autopilot_locations", settings.get("target_locations", ["Hyderabad"]))),
                height=150,
            )
            ap_max_leads = st.number_input("Max new leads per run", 5, 50, settings.get("autopilot_max_leads", 10))
            ap_max_emails = st.number_input("Max emails per run", 1, 20, settings.get("autopilot_max_emails", 5))

        ap_enabled = st.checkbox("Enable Autopilot", value=enabled)

        if st.form_submit_button("Save Autopilot Settings", type="primary", use_container_width=True):
            settings["autopilot_enabled"] = ap_enabled
            settings["autopilot_niches"] = ap_niches
            settings["autopilot_locations"] = [l.strip() for l in ap_locations_text.split("\n") if l.strip()]
            settings["autopilot_template"] = ap_template
            settings["autopilot_max_leads"] = ap_max_leads
            settings["autopilot_max_emails"] = ap_max_emails
            save_settings(settings)
            st.session_state.settings = settings
            st.success("Autopilot settings saved!")

    # ─── Manual Trigger ───
    st.markdown("---")
    st.markdown("### Manual Run")
    st.markdown("Click below to run the autopilot cycle manually (find leads + send emails).")

    if st.button("Run Autopilot Now", type="primary", use_container_width=True):
        _run_autopilot_cycle(settings)

    # ─── Setup Instructions ───
    st.markdown("---")
    st.markdown("### GitHub Actions Setup (Free 24/7 Automation)")
    st.markdown("""
**One-time setup to run automatically every day:**

1. **Push your code to GitHub** (if not already done)
2. **Add your secrets** in GitHub repo settings:
   - Go to your repo > Settings > Secrets and variables > Actions
   - Add these secrets:
     - `GMAIL_ADDRESS` — your Gmail address
     - `GMAIL_PASSWORD` — your Gmail App Password
3. **The workflow file** is already at `.github/workflows/daily_outreach.yml`
4. **It runs automatically** every day at 9 AM UTC (2:30 PM IST)

**Free tier:** GitHub gives 2,000 minutes/month for free. Each run takes ~5-10 minutes,
so you can run it 200+ times/month at no cost.
    """)


def _run_autopilot_cycle(settings):
    """Run one autopilot cycle: find leads, then send emails."""
    import random
    import time
    import urllib.parse
    from datetime import datetime

    import pandas as pd

    from core.database import load_leads, save_leads, load_sent, save_sent
    from scrapers.registry import get_all_scrapers
    from analyzers.email_finder import analyze_website
    from analyzers.lead_scorer import score_lead
    from outreach.templates import TEMPLATES, format_template
    from outreach.email_sender import send_one_email

    progress = st.progress(0)
    status = st.empty()
    log = st.empty()
    messages = []

    # Step 1: Find leads
    status.text("Step 1: Finding new leads...")
    niches = settings.get("autopilot_niches", settings.get("target_niches", ["dentist"]))
    locations = settings.get("autopilot_locations", settings.get("target_locations", ["Hyderabad"]))
    max_leads = settings.get("autopilot_max_leads", 10)

    leads_df = load_leads()
    existing_domains = set()
    if len(leads_df) > 0 and "website" in leads_df.columns:
        for w in leads_df["website"].dropna():
            existing_domains.add(urllib.parse.urlparse(str(w)).netloc)

    scrapers_dict = get_all_scrapers()
    selected = settings.get("selected_scrapers", ["DuckDuckGo"])
    active_scrapers = [scrapers_dict[s]() for s in selected if s in scrapers_dict]
    if not active_scrapers:
        active_scrapers = [list(scrapers_dict.values())[0]()]

    new_leads = []
    for niche in niches:
        for location in locations:
            if len(new_leads) >= max_leads:
                break
            for scraper in active_scrapers:
                if len(new_leads) >= max_leads:
                    break
                try:
                    raw = scraper.search(niche, location)
                    for r in raw[:5]:
                        if not r.website or len(new_leads) >= max_leads:
                            continue
                        domain = urllib.parse.urlparse(r.website).netloc
                        if domain in existing_domains:
                            continue
                        existing_domains.add(domain)

                        info = analyze_website(r.website)
                        lead = {
                            "business_name": info["business_name"] or r.business_name or r.title[:60],
                            "website": r.website,
                            "email": info["email"] or f"info@{domain.replace('www.', '')}",
                            "email_source": "found" if info["email"] else "guessed",
                            "phone": info["phone"] or r.phone,
                            "niche": niche, "location": location,
                            "seo_score": info["seo_score"],
                            "seo_issues": "; ".join(info["seo_issues"]),
                            "lead_score": "", "lead_grade": "",
                            "status": "new", "notes": "",
                            "added_date": datetime.now().strftime("%Y-%m-%d"),
                            "source": scraper.name,
                        }
                        scoring = score_lead(lead)
                        lead["lead_score"] = scoring["total_score"]
                        lead["lead_grade"] = scoring["grade"]
                        new_leads.append(lead)
                        messages.append(f"Found: {lead['business_name']} (Score: {scoring['total_score']})")
                except Exception:
                    pass

    if new_leads:
        new_df = pd.DataFrame(new_leads)
        leads_df = pd.concat([leads_df, new_df], ignore_index=True)
        save_leads(leads_df)
        messages.append(f"--- Saved {len(new_leads)} new leads ---")

    progress.progress(0.5)

    # Step 2: Send emails
    status.text("Step 2: Sending emails...")
    if not settings.get("email_accounts"):
        messages.append("No email account configured. Skipping sends.")
    else:
        sent_df = load_sent()
        sent_emails = set(sent_df["to_email"].tolist()) if len(sent_df) > 0 else set()

        leads_df = load_leads()
        unsent = leads_df[
            (leads_df["email"].notna()) &
            (leads_df["email"] != "") &
            (~leads_df["email"].isin(sent_emails)) &
            (leads_df["status"].fillna("new") == "new")
        ]

        if "lead_score" in unsent.columns:
            unsent["lead_score"] = pd.to_numeric(unsent["lead_score"], errors="coerce")
            unsent = unsent.sort_values("lead_score", ascending=False)

        account = settings["email_accounts"][0]
        template_name = settings.get("autopilot_template", list(TEMPLATES.keys())[0])
        max_emails = settings.get("autopilot_max_emails", 5)
        emails_sent = 0

        for idx, lead in unsent.head(max_emails).iterrows():
            to_email = str(lead["email"])
            variables = {
                "business_name": str(lead.get("business_name", "")),
                "website": str(lead.get("website", "")),
                "niche": str(lead.get("niche", "business")),
                "location": str(lead.get("location", "")),
                "seo_issues": str(lead.get("seo_issues", "some SEO improvements")),
                "your_name": settings.get("your_name", ""),
                "your_company": settings.get("your_company", ""),
                "your_phone": settings.get("your_phone", ""),
                "your_calendly": settings.get("your_calendly", ""),
            }
            subj, body = format_template(template_name, variables)
            success, error = send_one_email(account, to_email, subj, body)

            record = {
                "to_email": to_email,
                "business_name": str(lead.get("business_name", "")),
                "subject": subj, "template": template_name,
                "followup_num": 0, "from_email": account["email"],
                "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "sent" if success else "failed",
            }
            sent_df = load_sent()
            sent_df = pd.concat([sent_df, pd.DataFrame([record])], ignore_index=True)
            save_sent(sent_df)

            if success:
                leads_df.loc[leads_df["email"] == to_email, "status"] = "contacted"
                save_leads(leads_df)
                emails_sent += 1
                messages.append(f"Sent to: {to_email}")
            else:
                messages.append(f"Failed: {to_email} ({error})")

            time.sleep(random.uniform(30, 60))

        messages.append(f"--- Sent {emails_sent} emails ---")

    progress.progress(1.0)
    status.text("Autopilot cycle complete!")
    log.text("\n".join(messages))
