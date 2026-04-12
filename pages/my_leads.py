"""My Leads page — view, filter, edit, and export leads with scoring."""

import pandas as pd
import streamlit as st

from core.database import load_leads, save_leads
from core.constants import LEAD_STATUSES
from analyzers.lead_scorer import score_lead


def render(settings):
    st.markdown("## My Leads")

    leads_df = load_leads()

    if len(leads_df) == 0:
        st.info("No leads yet. Go to **Find Leads** to get started.")
        st.stop()

    # ─── Filters ───
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status_filter = st.selectbox("Status", ["All"] + list(leads_df["status"].fillna("new").unique()))
    with col2:
        niche_filter = st.selectbox("Niche", ["All"] + sorted(leads_df["niche"].dropna().unique().tolist()))
    with col3:
        location_filter = st.selectbox("Location", ["All"] + sorted(leads_df["location"].dropna().unique().tolist()))
    with col4:
        grade_options = ["All"]
        if "lead_grade" in leads_df.columns:
            grades = leads_df["lead_grade"].dropna().unique().tolist()
            grade_options += sorted([g for g in grades if g])
        grade_filter = st.selectbox("Lead Grade", grade_options)

    filtered = leads_df.copy()
    if status_filter != "All":
        filtered = filtered[filtered["status"].fillna("new") == status_filter]
    if niche_filter != "All":
        filtered = filtered[filtered["niche"] == niche_filter]
    if location_filter != "All":
        filtered = filtered[filtered["location"] == location_filter]
    if grade_filter != "All" and "lead_grade" in filtered.columns:
        filtered = filtered[filtered["lead_grade"] == grade_filter]

    # Sort by lead score if available
    if "lead_score" in filtered.columns:
        filtered["lead_score"] = pd.to_numeric(filtered["lead_score"], errors="coerce")
        filtered = filtered.sort_values("lead_score", ascending=False)

    st.markdown(f"**Showing {len(filtered)} leads**")

    # ─── Batch actions ───
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Re-score All Leads", use_container_width=True):
            with st.spinner("Scoring leads..."):
                for idx, row in leads_df.iterrows():
                    scoring = score_lead(row.to_dict())
                    leads_df.at[idx, "lead_score"] = scoring["total_score"]
                    leads_df.at[idx, "lead_grade"] = scoring["grade"]
                save_leads(leads_df)
            st.success("All leads re-scored!")
            st.rerun()

    # ─── Editable table ───
    display_cols = ["business_name", "website", "email", "phone", "niche", "location",
                    "seo_score", "lead_score", "lead_grade", "status", "source", "notes"]
    available_cols = [c for c in display_cols if c in filtered.columns]

    edited = st.data_editor(
        filtered[available_cols],
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "status": st.column_config.SelectboxColumn("Status", options=LEAD_STATUSES),
            "website": st.column_config.LinkColumn("Website"),
            "lead_score": st.column_config.NumberColumn("Score", min_value=0, max_value=100),
            "lead_grade": st.column_config.SelectboxColumn("Grade", options=["A", "B", "C", "D", "F"]),
        },
        hide_index=True,
    )

    if st.button("Save Changes", type="primary"):
        for col in available_cols:
            leads_df.loc[filtered.index, col] = edited[col].values
        save_leads(leads_df)
        st.success("Changes saved!")
        st.rerun()

    # ─── Export ───
    st.markdown("---")
    csv_data = filtered.to_csv(index=False)
    st.download_button("Download as CSV", csv_data, "leads_export.csv", "text/csv")
