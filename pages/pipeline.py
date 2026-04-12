"""Pipeline View — column-based visual pipeline for lead management."""

import streamlit as st
import pandas as pd

from core.database import load_leads, save_leads
from core.constants import PIPELINE_STAGES, LEAD_STATUSES


def render(settings):
    st.markdown("## Lead Pipeline")

    leads_df = load_leads()

    if len(leads_df) == 0:
        st.info("No leads yet. Go to **Find Leads** to get started.")
        return

    # Pipeline metrics
    _render_pipeline_metrics(leads_df)

    st.markdown("---")

    # Pipeline columns
    _render_pipeline_columns(leads_df)


def _render_pipeline_metrics(leads_df):
    """Show conversion metrics across pipeline stages."""
    stage_counts = {}
    for stage in PIPELINE_STAGES:
        count = len(leads_df[leads_df["status"].fillna("new") == stage])
        stage_counts[stage] = count

    total = len(leads_df)
    cols = st.columns(len(PIPELINE_STAGES))

    for i, stage in enumerate(PIPELINE_STAGES):
        count = stage_counts[stage]
        pct = round(count / total * 100, 1) if total > 0 else 0
        cols[i].metric(
            stage.replace("_", " ").title(),
            count,
            f"{pct}%",
        )

    # Conversion rates
    contacted = stage_counts.get("contacted", 0)
    replied = stage_counts.get("replied", 0)
    won = stage_counts.get("won", 0)

    col1, col2, col3 = st.columns(3)
    if contacted > 0:
        col1.metric("Contact → Reply", f"{round(replied / contacted * 100, 1)}%" if contacted else "0%")
    if replied > 0:
        col2.metric("Reply → Won", f"{round(won / replied * 100, 1)}%" if replied else "0%")
    if total > 0:
        col3.metric("Overall Win Rate", f"{round(won / total * 100, 1)}%")

    # Pipeline value
    if "deal_value" in leads_df.columns:
        total_value = pd.to_numeric(leads_df["deal_value"], errors="coerce").sum()
        if total_value > 0:
            won_value = pd.to_numeric(
                leads_df[leads_df["status"] == "won"]["deal_value"], errors="coerce"
            ).sum()
            st.metric("Pipeline Value", f"${total_value:,.0f}", f"Won: ${won_value:,.0f}")


def _render_pipeline_columns(leads_df):
    """Render visual pipeline columns with lead cards."""

    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        niche_filter = st.selectbox(
            "Filter by Niche",
            ["All"] + sorted(leads_df["niche"].dropna().unique().tolist()),
            key="pipeline_niche",
        )
    with col2:
        location_filter = st.selectbox(
            "Filter by Location",
            ["All"] + sorted(leads_df["location"].dropna().unique().tolist()),
            key="pipeline_location",
        )

    filtered = leads_df.copy()
    if niche_filter != "All":
        filtered = filtered[filtered["niche"] == niche_filter]
    if location_filter != "All":
        filtered = filtered[filtered["location"] == location_filter]

    # Render columns
    display_stages = PIPELINE_STAGES
    cols = st.columns(len(display_stages))

    for i, stage in enumerate(display_stages):
        with cols[i]:
            stage_label = stage.replace("_", " ").title()
            stage_leads = filtered[filtered["status"].fillna("new") == stage]
            st.markdown(f"**{stage_label}** ({len(stage_leads)})")
            st.markdown("---")

            if len(stage_leads) == 0:
                st.caption("No leads")
                continue

            # Sort by lead score
            if "lead_score" in stage_leads.columns:
                stage_leads = stage_leads.copy()
                stage_leads["lead_score"] = pd.to_numeric(stage_leads["lead_score"], errors="coerce")
                stage_leads = stage_leads.sort_values("lead_score", ascending=False)

            for _, lead in stage_leads.head(10).iterrows():
                _render_lead_card(lead, stage, leads_df)

            if len(stage_leads) > 10:
                st.caption(f"+ {len(stage_leads) - 10} more")


def _render_lead_card(lead, current_stage, leads_df):
    """Render a single lead card in the pipeline."""
    name = str(lead.get("business_name", "Unknown"))[:25]
    grade = str(lead.get("lead_grade", ""))
    niche = str(lead.get("niche", ""))
    score = lead.get("lead_score", "")

    grade_colors = {"A": "green", "B": "blue", "C": "orange", "D": "red", "F": "red"}
    grade_badge = f" [{grade}]" if grade else ""

    card_label = f"{name}{grade_badge}"
    if niche:
        card_label += f" | {niche}"

    email = str(lead.get("email", ""))
    card_key = f"card_{email}_{current_stage}"

    with st.expander(card_label, expanded=False):
        st.caption(f"Score: {score} | {niche}")
        if email:
            st.caption(email)

        # Move actions
        stage_idx = PIPELINE_STAGES.index(current_stage) if current_stage in PIPELINE_STAGES else 0
        move_cols = st.columns(2)

        if stage_idx < len(PIPELINE_STAGES) - 2:  # Not at won/lost
            next_stage = PIPELINE_STAGES[stage_idx + 1]
            with move_cols[0]:
                if st.button(
                    f"→ {next_stage.replace('_', ' ').title()}",
                    key=f"move_{card_key}",
                    use_container_width=True,
                ):
                    leads_df.loc[leads_df["email"] == email, "status"] = next_stage
                    save_leads(leads_df)
                    st.rerun()

        with move_cols[1]:
            if current_stage != "lost":
                if st.button("Lost", key=f"lost_{card_key}", use_container_width=True):
                    leads_df.loc[leads_df["email"] == email, "status"] = "lost"
                    save_leads(leads_df)
                    st.rerun()
