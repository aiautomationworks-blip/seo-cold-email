"""Niche Setup page — pre-built high-ticket niche profiles."""

import streamlit as st

from core.constants import NICHE_PROFILES
from core.settings import save_settings


def render(settings):
    st.markdown("## Niche Setup")
    st.markdown("Choose a high-ticket niche profile to pre-configure your system.")

    # ─── Niche Cards ───
    st.markdown("### Available Niche Profiles")

    # Group by tier
    premium = {k: v for k, v in NICHE_PROFILES.items() if v["tier"] == "premium"}
    high = {k: v for k, v in NICHE_PROFILES.items() if v["tier"] == "high"}
    medium = {k: v for k, v in NICHE_PROFILES.items() if v["tier"] == "medium"}
    standard = {k: v for k, v in NICHE_PROFILES.items() if v["tier"] == "standard"}

    if premium:
        st.markdown("#### Premium Tier ($3,000-5,000+ per client)")
        _show_niche_cards(premium, settings)

    if high:
        st.markdown("#### High Tier ($1,500-3,000 per client)")
        _show_niche_cards(high, settings)

    if medium:
        st.markdown("#### Medium Tier ($1,000-1,500 per client)")
        _show_niche_cards(medium, settings)

    if standard:
        st.markdown("#### Standard Tier ($500-1,000 per client)")
        _show_niche_cards(standard, settings)

    # ─── Current Configuration ───
    st.markdown("---")
    st.markdown("### Your Current Configuration")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Target Niches:** {', '.join(settings.get('target_niches', []))}")
    with col2:
        st.markdown(f"**Target Locations:** {', '.join(settings.get('target_locations', []))}")


def _show_niche_cards(niches, settings):
    """Display niche profile cards in a grid."""
    cols = st.columns(3)
    for i, (key, profile) in enumerate(niches.items()):
        with cols[i % 3]:
            st.markdown(f"**{profile['display_name']}**")
            st.markdown(f"Avg deal: ${profile['avg_deal_value']:,}")
            st.markdown(f"Pain points:")
            for pp in profile["pain_points"][:2]:
                st.markdown(f"- {pp}")

            if st.button(f"Use {profile['display_name']}", key=f"niche_{key}",
                         use_container_width=True):
                # Apply niche configuration
                settings["target_niches"] = profile["search_queries"][:4]
                save_settings(settings)
                st.session_state.settings = settings
                st.success(f"Applied {profile['display_name']} profile! Target niches updated.")
                st.rerun()
