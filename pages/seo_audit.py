"""SEO Audit page — run comprehensive audits on any website."""

import streamlit as st

from analyzers.seo_auditor import run_seo_audit, format_issues_for_email
from analyzers.tech_detector import detect_tech


def render(settings):
    st.markdown("## SEO Audit")
    st.markdown("Check any website's SEO and get findings you can use in your emails.")

    url = st.text_input("Enter website URL", placeholder="example.com")

    col1, col2 = st.columns(2)
    with col1:
        run_tech = st.checkbox("Include tech detection", value=True)

    if st.button("Run Audit", type="primary") and url:
        if not url.startswith("http"):
            url = "https://" + url

        with st.spinner("Analyzing website..."):
            audit = run_seo_audit(url)
            tech = detect_tech(url) if run_tech else None

        # Score display
        score = audit["seo_score"]
        if score >= 80:
            color = "green"
        elif score >= 50:
            color = "orange"
        else:
            color = "red"

        st.markdown(f"### SEO Score: :{color}[{score}/100]")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Load Time", f"{audit.get('load_time', 0)}s")
        with col2:
            st.metric("Page Size", f"{audit.get('page_size_kb', 0):.0f} KB")
        with col3:
            st.metric("Issues Found", len(audit.get("issues", [])))

        # Issues
        if audit.get("issues"):
            st.markdown("### Issues Found")
            for issue in audit["issues"]:
                severity = issue.get("severity", "medium")
                icon = {"high": "!!!", "medium": "!!", "low": "!"}.get(severity, "!")
                st.markdown(f"**[{severity.upper()}]** {issue['issue']}")
                st.markdown(f"  *{issue['impact']}*")

            st.markdown("### Copy-Paste for Your Email")
            issues_text = format_issues_for_email(audit)
            st.code(issues_text, language=None)
        else:
            st.success("No major SEO issues found!")

        # Tech detection
        if tech:
            st.markdown("### Technology Detected")
            col1, col2 = st.columns(2)
            with col1:
                if tech.get("cms"):
                    st.markdown(f"**CMS:** {tech['cms']}")
                st.markdown(f"**SSL:** {'Yes' if tech.get('has_ssl') else 'No'}")
                st.markdown(f"**Google Analytics:** {'Yes' if tech.get('has_analytics') else 'No'}")
                st.markdown(f"**Google Ads:** {'Yes' if tech.get('has_google_ads') else 'No'}")
            with col2:
                st.markdown(f"**Blog:** {'Yes' if tech.get('has_blog') else 'No'}")
                st.markdown(f"**Contact Form:** {'Yes' if tech.get('has_contact_form') else 'No'}")
                st.markdown(f"**Live Chat:** {'Yes' if tech.get('has_chat_widget') else 'No'}")
                st.markdown(f"**Facebook Pixel:** {'Yes' if tech.get('has_facebook_pixel') else 'No'}")
