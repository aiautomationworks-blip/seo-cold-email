"""Settings page — configure your profile, email accounts, and targets."""

import streamlit as st

from core.settings import save_settings
from outreach.email_sender import send_one_email
from scrapers.registry import scraper_names


def render(settings):
    st.markdown("## Settings")

    with st.form("settings_form"):
        st.markdown("### About You")
        col1, col2 = st.columns(2)
        with col1:
            your_name = st.text_input("Your Name *", value=settings.get("your_name", ""))
            your_company = st.text_input("Company Name", value=settings.get("your_company", ""))
            your_phone = st.text_input("Phone", value=settings.get("your_phone", ""))
        with col2:
            your_website = st.text_input("Website", value=settings.get("your_website", ""))
            your_calendly = st.text_input("Calendly Link", value=settings.get("your_calendly", ""))

        st.markdown("---")
        st.markdown("### Gmail Account for Sending")
        st.markdown("""
**How to get your App Password (one-time setup):**
1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Click **Security** > Turn on **2-Step Verification**
3. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. Create an App Password for **Mail** and paste below
        """)

        existing_accounts = settings.get("email_accounts", [{}])
        if not existing_accounts:
            existing_accounts = [{}]
        acc = existing_accounts[0]

        col1, col2 = st.columns(2)
        with col1:
            gmail_addr = st.text_input("Gmail Address", value=acc.get("email", ""))
        with col2:
            gmail_pass = st.text_input("App Password", value=acc.get("password", ""), type="password")

        st.markdown("---")
        st.markdown("### Sending Settings")
        col1, col2, col3 = st.columns(3)
        with col1:
            daily_limit = st.number_input("Max emails/day", 1, 50, settings.get("daily_limit", 5))
        with col2:
            delay_min = st.number_input("Min delay (sec)", 10, 300, settings.get("delay_min", 45))
        with col3:
            delay_max = st.number_input("Max delay (sec)", 30, 600, settings.get("delay_max", 120))

        st.markdown("---")
        st.markdown("### Target Settings")
        niches_text = st.text_area(
            "Target niches (one per line)",
            value="\n".join(settings.get("target_niches", ["dentist"])),
        )
        locations_text = st.text_area(
            "Target cities (one per line)",
            value="\n".join(settings.get("target_locations", ["Hyderabad"])),
        )

        st.markdown("---")
        st.markdown("### Lead Sources")
        all_scraper_names = scraper_names()
        selected_scrapers = st.multiselect(
            "Active scrapers",
            all_scraper_names,
            default=settings.get("selected_scrapers", ["DuckDuckGo"]),
        )

        st.markdown("---")
        st.markdown("### Follow-up Schedule")
        col1, col2, col3 = st.columns(3)
        fdays = settings.get("followup_days", [3, 7, 14])
        with col1:
            f1 = st.number_input("Follow-up 1 (days after)", 1, 30, fdays[0] if len(fdays) > 0 else 3)
        with col2:
            f2 = st.number_input("Follow-up 2 (days after)", 1, 30, fdays[1] if len(fdays) > 1 else 7)
        with col3:
            f3 = st.number_input("Follow-up 3 (days after)", 1, 30, fdays[2] if len(fdays) > 2 else 14)

        saved = st.form_submit_button("Save Settings", type="primary", use_container_width=True)

        if saved:
            new_settings = {
                "your_name": your_name,
                "your_company": your_company,
                "your_phone": your_phone,
                "your_website": your_website,
                "your_calendly": your_calendly,
                "email_accounts": [{
                    "email": gmail_addr,
                    "password": gmail_pass,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "name": your_name,
                }] if gmail_addr else [],
                "daily_limit": daily_limit,
                "delay_min": delay_min,
                "delay_max": delay_max,
                "target_niches": [n.strip() for n in niches_text.split("\n") if n.strip()],
                "target_locations": [l.strip() for l in locations_text.split("\n") if l.strip()],
                "followup_days": [f1, f2, f3],
                "selected_scrapers": selected_scrapers,
                # Preserve autopilot settings
                "autopilot_enabled": settings.get("autopilot_enabled", False),
                "autopilot_niches": settings.get("autopilot_niches", []),
                "autopilot_locations": settings.get("autopilot_locations", []),
                "autopilot_template": settings.get("autopilot_template", "SEO Audit Findings"),
                "autopilot_max_leads": settings.get("autopilot_max_leads", 10),
                "autopilot_max_emails": settings.get("autopilot_max_emails", 5),
            }
            save_settings(new_settings)
            st.session_state.settings = new_settings
            st.success("Settings saved!")

    # ─── Test Email ───
    st.markdown("---")
    st.markdown("### Test Your Email Setup")
    test_to = st.text_input("Send test email to", placeholder="your-other-email@gmail.com")
    if st.button("Send Test Email") and test_to:
        if not settings.get("email_accounts"):
            st.error("Save your Gmail settings first!")
        else:
            with st.spinner("Sending test email..."):
                acc = settings["email_accounts"][0]
                success, error = send_one_email(
                    acc, test_to,
                    "Test from SEO Cold Email System",
                    f"Hi! This is a test email from your cold email system.\n\nIf you're reading this, your setup is working!\n\n- {settings.get('your_name', 'Your Name')}",
                )
            if success:
                st.success(f"Test email sent to {test_to}!")
            else:
                st.error(f"Failed: {error}")
