"""Email Health Dashboard — account health, deliverability, spam checker."""

import streamlit as st

from outreach.account_manager import AccountManager
from analyzers.deliverability import (
    check_all_records, check_template_spam, calculate_deliverability_score,
)
from outreach.templates import TEMPLATES, template_names, format_template


def render(settings):
    st.markdown("## Email Health Dashboard")

    tab1, tab2, tab3 = st.tabs(["Account Health", "Deliverability", "Spam Checker"])

    with tab1:
        _render_account_health(settings)

    with tab2:
        _render_deliverability(settings)

    with tab3:
        _render_spam_checker(settings)


def _render_account_health(settings):
    """Per-account health cards."""
    mgr = AccountManager(settings)
    health_data = mgr.get_all_health()

    if not health_data:
        st.info("No email accounts configured. Add accounts in Settings.")
        return

    for acc in health_data:
        with st.expander(f"{acc['email']} — Score: {acc['score']}/100", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Health Score", f"{acc['score']}/100")
            col2.metric("Sent", acc.get("sent", 0))
            col3.metric("Bounce Rate", f"{acc.get('bounce_rate', 0)}%")
            col4.metric("Reply Rate", f"{acc.get('reply_rate', 0)}%")

            # Daily usage
            limit = acc.get("daily_limit", 20)
            sends = acc.get("sends_today", 0)
            st.progress(min(sends / limit, 1.0) if limit > 0 else 0, text=f"Today: {sends}/{limit}")

            # Warmup status
            if acc.get("warmup_mode"):
                warmup_start = acc.get("warmup_start_date", "N/A")
                from datetime import datetime
                try:
                    start = datetime.strptime(warmup_start, "%Y-%m-%d")
                    days = (datetime.now() - start).days
                    effective = 2 + (days // 3) * 2
                    st.info(
                        f"Warmup Mode: Day {days} | "
                        f"Effective limit: {min(effective, limit)}/day | "
                        f"Started: {warmup_start}"
                    )
                except (ValueError, TypeError):
                    st.info("Warmup mode active")

            # Status
            status = acc.get("status", "active")
            if status != "active":
                st.warning(f"Account status: {status}")


def _render_deliverability(settings):
    """SPF/DKIM/DMARC status and deliverability score."""
    st.markdown("### Check Your Domain Authentication")
    st.caption("Enter your sending domain to check SPF, DKIM, and DMARC records.")

    # Auto-detect domain from account
    accounts = settings.get("email_accounts", [])
    default_domain = ""
    if accounts:
        email = accounts[0].get("email", "")
        if "@" in email:
            default_domain = email.split("@")[1]

    domain = st.text_input("Domain", value=default_domain, placeholder="yourdomain.com")

    if st.button("Check Deliverability", type="primary") and domain:
        with st.spinner("Checking DNS records..."):
            records = check_all_records(domain)

            # SPF
            spf = records["spf"]
            _show_record("SPF", spf)

            # DKIM
            dkim = records["dkim"]
            _show_record("DKIM", dkim)

            # DMARC
            dmarc = records["dmarc"]
            _show_record("DMARC", dmarc)

            # Overall score
            st.markdown("---")
            score = calculate_deliverability_score(domain)
            st.markdown(f"### Deliverability Score: {score['score']}/100 (Grade: {score['grade']})")

            for detail in score["details"]:
                st.markdown(f"- {detail}")


def _show_record(name, result):
    """Display a DNS record check result."""
    status = result.get("status", "unknown")
    icons = {"pass": "OK", "weak": "!", "missing": "X", "error": "?", "unknown": "?"}
    icon = icons.get(status, "?")

    st.markdown(f"**{name}:** [{icon}] {status.upper()}")
    if result.get("record"):
        st.code(result["record"], language=None)
    if result.get("recommendation"):
        st.caption(result["recommendation"])


def _render_spam_checker(settings):
    """Template spam word scanner."""
    st.markdown("### Template Spam Checker")
    st.caption("Check your email templates for spam trigger words.")

    # Template selector
    tmpl_name = st.selectbox("Check Template", template_names())

    variables = {
        "business_name": "Example Business",
        "website": "https://example.com",
        "niche": "dentist",
        "location": "New York",
        "seo_issues": "- Missing meta description\n- No SSL certificate",
        "your_name": settings.get("your_name", "Your Name"),
        "your_company": settings.get("your_company", ""),
        "your_phone": settings.get("your_phone", ""),
        "your_calendly": settings.get("your_calendly", ""),
    }

    subject, body = format_template(tmpl_name, variables)

    if st.button("Scan for Spam Words"):
        result = check_template_spam(subject, body)

        if result["clean"]:
            st.success(f"Template looks clean! Spam score: {result['spam_score']}/100")
        else:
            st.warning(f"Spam score: {result['spam_score']}/100")

        if result["found_words"]:
            st.markdown("**Spam trigger words found:**")
            for word in result["found_words"]:
                st.markdown(f"- \"{word}\"")

        if result["recommendations"]:
            st.markdown("**Recommendations:**")
            for rec in result["recommendations"]:
                st.markdown(f"- {rec}")

    # Custom text check
    st.markdown("---")
    st.markdown("### Check Custom Text")
    custom_subject = st.text_input("Subject line")
    custom_body = st.text_area("Email body")

    if st.button("Check Custom Text") and (custom_subject or custom_body):
        result = check_template_spam(custom_subject, custom_body)
        if result["clean"]:
            st.success(f"Looks clean! Score: {result['spam_score']}/100")
        else:
            st.warning(f"Spam score: {result['spam_score']}/100")
            for rec in result["recommendations"]:
                st.markdown(f"- {rec}")
