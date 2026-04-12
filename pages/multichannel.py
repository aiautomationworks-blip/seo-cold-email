"""Multi-Channel Outreach page — LinkedIn and WhatsApp message generators."""

import pandas as pd
import streamlit as st

from core.database import load_leads
from outreach.multichannel import (
    generate_linkedin_message,
    generate_whatsapp_message,
    generate_follow_up_schedule,
)


def render(settings):
    st.markdown("## Multi-Channel Outreach")
    st.markdown("Generate copy-paste messages for LinkedIn and WhatsApp.")

    leads_df = load_leads()

    if len(leads_df) == 0:
        st.info("No leads yet. Go to **Find Leads** first.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["LinkedIn", "WhatsApp", "Follow-up Schedule"])

    # ─── LinkedIn ───
    with tab1:
        st.markdown("### LinkedIn Connection Messages")
        st.markdown("*Copy-paste these when sending LinkedIn connection requests (300 char limit)*")

        # Lead selector
        lead_options = []
        for _, row in leads_df.iterrows():
            name = str(row.get("business_name", "Unknown"))
            email = str(row.get("email", ""))
            lead_options.append(f"{name} ({email})")

        selected_idx = st.selectbox("Select a lead", range(len(lead_options)),
                                    format_func=lambda x: lead_options[x],
                                    key="linkedin_lead")

        lead = leads_df.iloc[selected_idx]
        messages = generate_linkedin_message(lead.to_dict(), settings)

        for name, msg in messages.items():
            st.markdown(f"**{name}** ({len(msg)} chars)")
            st.code(msg, language=None)

    # ─── WhatsApp ───
    with tab2:
        st.markdown("### WhatsApp Messages")
        st.markdown("*Click the link to open WhatsApp with pre-filled message*")

        selected_idx_wa = st.selectbox("Select a lead", range(len(lead_options)),
                                       format_func=lambda x: lead_options[x],
                                       key="whatsapp_lead")

        lead = leads_df.iloc[selected_idx_wa]
        result = generate_whatsapp_message(lead.to_dict(), settings)

        for name, msg in result["messages"].items():
            st.markdown(f"**{name}**")
            st.code(msg, language=None)
            if name in result["links"]:
                st.markdown(f"[Open in WhatsApp]({result['links'][name]})")
            st.markdown("---")

        if not lead.get("phone"):
            st.warning("No phone number for this lead. WhatsApp links won't work without a phone number.")

    # ─── Follow-up Schedule ───
    with tab3:
        st.markdown("### Multi-Channel Follow-up Schedule")
        st.markdown("*Recommended sequence for maximum response rates*")

        selected_idx_fu = st.selectbox("Select a lead", range(len(lead_options)),
                                       format_func=lambda x: lead_options[x],
                                       key="schedule_lead")

        lead = leads_df.iloc[selected_idx_fu]
        schedule = generate_follow_up_schedule(lead.to_dict())

        schedule_df = pd.DataFrame(schedule)
        st.dataframe(schedule_df, use_container_width=True, hide_index=True)

        st.markdown("""
**Tips for multi-channel outreach:**
- Start with email (least intrusive)
- Connect on LinkedIn on day 3 (builds credibility)
- WhatsApp on day 6 only if they have a phone number
- Never be pushy — if they say no, respect it
        """)
