"""Settings page — configure profile, email accounts, compliance, and targets."""

import streamlit as st

from core.settings import save_settings
from core.database_v2 import save_email_account, load_email_accounts
from outreach.email_sender import send_one_email
from scrapers.registry import scraper_names


def render(settings):
    st.markdown("## Settings")

    tab1, tab2, tab3 = st.tabs(["General", "Email Accounts", "Compliance"])

    with tab1:
        _render_general(settings)

    with tab2:
        _render_email_accounts(settings)

    with tab3:
        _render_compliance(settings)


def _render_general(settings):
    """General settings form."""
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
                "email_accounts": settings.get("email_accounts", []),
                "daily_limit": daily_limit,
                "delay_min": delay_min,
                "delay_max": delay_max,
                "target_niches": [n.strip() for n in niches_text.split("\n") if n.strip()],
                "target_locations": [l.strip() for l in locations_text.split("\n") if l.strip()],
                "followup_days": [f1, f2, f3],
                "selected_scrapers": selected_scrapers,
                "autopilot_enabled": settings.get("autopilot_enabled", False),
                "autopilot_niches": settings.get("autopilot_niches", []),
                "autopilot_locations": settings.get("autopilot_locations", []),
                "autopilot_template": settings.get("autopilot_template", "SEO Audit Findings"),
                "autopilot_max_leads": settings.get("autopilot_max_leads", 10),
                "autopilot_max_emails": settings.get("autopilot_max_emails", 5),
                # AI settings
                "groq_api_key": settings.get("groq_api_key", ""),
                "gemini_api_key": settings.get("gemini_api_key", ""),
                # Compliance
                "add_unsubscribe": settings.get("add_unsubscribe", True),
                "skip_weekends": settings.get("skip_weekends", True),
                # Webhooks
                "discord_webhook": settings.get("discord_webhook", ""),
                "slack_webhook": settings.get("slack_webhook", ""),
            }
            save_settings(new_settings)
            st.session_state.settings = new_settings
            st.success("Settings saved!")


def _render_email_accounts(settings):
    """Multi-account email management."""
    st.markdown("### Email Accounts")
    st.markdown("""
**How to get your Gmail App Password:**
1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Click **Security** > Turn on **2-Step Verification**
3. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. Create an App Password for **Mail** and paste below
    """)

    # Show existing accounts
    existing = settings.get("email_accounts", [])
    db_accounts = load_email_accounts()

    if existing or db_accounts:
        st.markdown("**Current Accounts:**")
        all_displayed = set()
        for acc in existing:
            email = acc.get("email", "")
            if email and email not in all_displayed:
                st.markdown(f"- {email} (Settings)")
                all_displayed.add(email)
        for acc in db_accounts:
            email = acc.get("email", "")
            if email and email not in all_displayed:
                warmup = " [Warmup]" if acc.get("warmup_mode") else ""
                st.markdown(f"- {email} (DB){warmup}")
                all_displayed.add(email)

    # Add new account
    st.markdown("---")
    st.markdown("**Add / Update Account:**")

    with st.form("add_account"):
        col1, col2 = st.columns(2)
        with col1:
            gmail_addr = st.text_input("Gmail Address")
        with col2:
            gmail_pass = st.text_input("App Password", type="password")

        col1, col2 = st.columns(2)
        with col1:
            acc_name = st.text_input("Display Name", value=settings.get("your_name", ""))
        with col2:
            acc_daily_limit = st.number_input("Daily limit for this account", 1, 50, 20)

        warmup = st.checkbox("Enable warmup mode (starts at 2/day, ramps up)")

        if st.form_submit_button("Add/Update Account", type="primary", use_container_width=True):
            if gmail_addr and gmail_pass:
                # Save to settings
                accs = settings.get("email_accounts", [])
                # Update existing or add new
                found = False
                for i, a in enumerate(accs):
                    if a.get("email") == gmail_addr:
                        accs[i] = {
                            "email": gmail_addr, "password": gmail_pass,
                            "smtp_server": "smtp.gmail.com", "smtp_port": 587,
                            "name": acc_name,
                        }
                        found = True
                        break
                if not found:
                    accs.append({
                        "email": gmail_addr, "password": gmail_pass,
                        "smtp_server": "smtp.gmail.com", "smtp_port": 587,
                        "name": acc_name,
                    })
                settings["email_accounts"] = accs
                save_settings(settings)
                st.session_state.settings = settings

                # Also save to database for rotation/warmup
                save_email_account({
                    "email": gmail_addr,
                    "password": gmail_pass,
                    "name": acc_name,
                    "daily_limit": acc_daily_limit,
                    "warmup_mode": 1 if warmup else 0,
                })

                st.success(f"Account {gmail_addr} saved!")
                st.rerun()
            else:
                st.error("Both email and password are required")

    # Test email
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


def _render_compliance(settings):
    """Compliance and deliverability settings."""
    st.markdown("### Compliance Settings")

    with st.form("compliance_form"):
        add_unsub = st.checkbox(
            "Auto-add unsubscribe link to all emails",
            value=settings.get("add_unsubscribe", True),
        )
        skip_weekends = st.checkbox(
            "Skip sending on weekends",
            value=settings.get("skip_weekends", True),
        )

        st.markdown("---")
        st.markdown("### AI Email Writer (Free APIs)")
        st.caption("Both are free with generous limits. You only need one.")

        groq_key = st.text_input(
            "Groq API Key (14,400 req/day free)",
            value=settings.get("groq_api_key", ""),
            type="password",
            help="Get free key at console.groq.com",
        )
        gemini_key = st.text_input(
            "Google Gemini API Key (15 RPM free)",
            value=settings.get("gemini_api_key", ""),
            type="password",
            help="Get free key at aistudio.google.com",
        )

        st.markdown("---")
        st.markdown("### Webhook Notifications")
        discord_webhook = st.text_input(
            "Discord Webhook URL",
            value=settings.get("discord_webhook", ""),
            help="Get webhook URL from Discord channel settings > Integrations",
        )
        slack_webhook = st.text_input(
            "Slack Webhook URL",
            value=settings.get("slack_webhook", ""),
            help="Create webhook at api.slack.com/apps",
        )

        if st.form_submit_button("Save Compliance Settings", type="primary", use_container_width=True):
            settings["add_unsubscribe"] = add_unsub
            settings["skip_weekends"] = skip_weekends
            settings["groq_api_key"] = groq_key
            settings["gemini_api_key"] = gemini_key
            settings["discord_webhook"] = discord_webhook
            settings["slack_webhook"] = slack_webhook
            save_settings(settings)
            st.session_state.settings = settings
            st.success("Compliance settings saved!")
