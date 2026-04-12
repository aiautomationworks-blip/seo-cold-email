"""Find Leads page — multi-source lead discovery with scoring."""

import random
import time
import urllib.parse
from datetime import datetime

import pandas as pd
import streamlit as st

from core.database import load_leads, save_leads
from analyzers.email_finder import analyze_website
from analyzers.lead_scorer import score_lead
from scrapers.registry import get_all_scrapers, scraper_names


def render(settings):
    st.markdown("## Find Leads")

    tab1, tab2, tab3 = st.tabs(["Auto-Search", "Add Manually", "Import CSV"])

    # ─── TAB 1: AUTO SEARCH ───
    with tab1:
        st.markdown("Search the internet for businesses using multiple sources.")

        # Scraper selection
        all_scrapers = scraper_names()
        selected = st.multiselect(
            "Lead Sources",
            all_scrapers,
            default=settings.get("selected_scrapers", ["DuckDuckGo"]),
            help="Select which search engines and directories to use",
        )

        col1, col2 = st.columns(2)
        with col1:
            niches = st.multiselect(
                "Business types to find",
                ["dentist", "plastic surgeon", "real estate agent", "med spa",
                 "chiropractor", "plumber", "roofing contractor", "lawyer",
                 "hvac contractor", "electrician", "doctor", "gym",
                 "restaurant", "veterinarian", "accountant"],
                default=settings.get("target_niches", ["dentist"]),
            )
        with col2:
            locations_text = st.text_area(
                "Cities (one per line)",
                value="\n".join(settings.get("target_locations", ["Hyderabad"])),
                height=150,
            )
            locations = [loc.strip() for loc in locations_text.strip().split("\n") if loc.strip()]

        col1, col2 = st.columns(2)
        with col1:
            max_per = st.slider("Max results per search", 5, 20, 10)
        with col2:
            score_leads = st.checkbox("Score leads (takes longer but finds best prospects)", value=True)

        if st.button("Start Searching", type="primary", use_container_width=True):
            leads_df = load_leads()
            existing_domains = set()
            if len(leads_df) > 0 and "website" in leads_df.columns:
                for w in leads_df["website"].dropna():
                    existing_domains.add(urllib.parse.urlparse(str(w)).netloc)

            total_found = 0
            progress = st.progress(0)
            status_text = st.empty()
            results_container = st.empty()

            scrapers_dict = get_all_scrapers()
            active_scrapers = [scrapers_dict[s]() for s in selected if s in scrapers_dict]

            total_searches = len(niches) * len(locations) * len(active_scrapers)
            search_num = 0
            new_leads = []

            for niche in niches:
                for location in locations:
                    for scraper in active_scrapers:
                        search_num += 1
                        progress.progress(min(search_num / max(total_searches, 1), 1.0))
                        status_text.text(f"[{scraper.name}] Searching: {niche} in {location}...")

                        try:
                            raw_results = scraper.search(niche, location)
                        except Exception:
                            raw_results = []

                        for r in raw_results[:max_per]:
                            if not r.website:
                                continue
                            domain = urllib.parse.urlparse(r.website).netloc
                            if domain in existing_domains:
                                continue
                            existing_domains.add(domain)

                            status_text.text(f"Analyzing: {domain}...")
                            info = analyze_website(r.website)

                            lead = {
                                "business_name": info["business_name"] or r.business_name or r.title[:60],
                                "website": r.website,
                                "email": info["email"],
                                "email_source": "found" if info["email"] else "guessed",
                                "phone": info["phone"] or r.phone,
                                "niche": niche,
                                "location": location,
                                "seo_score": info["seo_score"],
                                "seo_issues": "; ".join(info["seo_issues"]),
                                "lead_score": "",
                                "lead_grade": "",
                                "status": "new",
                                "notes": "",
                                "added_date": datetime.now().strftime("%Y-%m-%d"),
                                "source": r.source or scraper.name,
                            }

                            if not lead["email"]:
                                lead["email"] = f"info@{domain.replace('www.', '')}"
                                lead["email_source"] = "guessed"

                            # Score the lead
                            if score_leads:
                                scoring = score_lead(lead)
                                lead["lead_score"] = scoring["total_score"]
                                lead["lead_grade"] = scoring["grade"]

                            new_leads.append(lead)
                            total_found += 1

                            results_container.dataframe(
                                pd.DataFrame(new_leads)[["business_name", "website", "email", "seo_score", "lead_score", "source"]],
                                use_container_width=True, hide_index=True,
                            )

                        time.sleep(random.uniform(1, 3))

            progress.progress(1.0)

            if new_leads:
                new_df = pd.DataFrame(new_leads)
                leads_df = pd.concat([leads_df, new_df], ignore_index=True)
                save_leads(leads_df)
                status_text.text("")
                st.success(f"Found and saved {total_found} new leads!")

                # Show score summary
                if score_leads and new_leads:
                    scored = [l for l in new_leads if l.get("lead_score")]
                    if scored:
                        a_count = sum(1 for l in scored if l.get("lead_grade") == "A")
                        b_count = sum(1 for l in scored if l.get("lead_grade") == "B")
                        st.info(f"Score summary: {a_count} A-grade, {b_count} B-grade leads found")
            else:
                status_text.text("")
                st.info("No new leads found. Try different niches, cities, or search sources.")

    # ─── TAB 2: ADD MANUALLY ───
    with tab2:
        st.markdown("Add leads one at a time.")

        with st.form("add_lead_form"):
            col1, col2 = st.columns(2)
            with col1:
                biz_name = st.text_input("Business Name *")
                website_url = st.text_input("Website URL")
                email_addr = st.text_input("Email")
            with col2:
                phone = st.text_input("Phone")
                niche = st.text_input("Niche (e.g. dentist)")
                location = st.text_input("City")

            submitted = st.form_submit_button("Add Lead", type="primary", use_container_width=True)

            if submitted and biz_name:
                if website_url and not website_url.startswith("http"):
                    website_url = "https://" + website_url

                seo_score = ""
                seo_issues = ""
                if website_url:
                    with st.spinner("Analyzing website..."):
                        info = analyze_website(website_url)
                        if not email_addr and info["email"]:
                            email_addr = info["email"]
                        if not phone and info["phone"]:
                            phone = info["phone"]
                        seo_score = info["seo_score"]
                        seo_issues = "; ".join(info["seo_issues"])

                if not email_addr and website_url:
                    domain = urllib.parse.urlparse(website_url).netloc.replace("www.", "")
                    email_addr = f"info@{domain}"

                new_lead = {
                    "business_name": biz_name, "website": website_url,
                    "email": email_addr, "email_source": "manual",
                    "phone": phone, "niche": niche, "location": location,
                    "seo_score": seo_score, "seo_issues": seo_issues,
                    "lead_score": "", "lead_grade": "",
                    "status": "new", "notes": "",
                    "added_date": datetime.now().strftime("%Y-%m-%d"),
                    "source": "manual",
                }

                # Score it
                scoring = score_lead(new_lead)
                new_lead["lead_score"] = scoring["total_score"]
                new_lead["lead_grade"] = scoring["grade"]

                leads_df = load_leads()
                leads_df = pd.concat([leads_df, pd.DataFrame([new_lead])], ignore_index=True)
                save_leads(leads_df)
                st.success(f"Added: {biz_name} (Score: {scoring['total_score']}, Grade: {scoring['grade']})")

    # ─── TAB 3: IMPORT CSV ───
    with tab3:
        st.markdown("Upload a CSV or Excel file with your leads.")
        st.markdown("Columns: `business_name`, `website`, `email`, `phone`, `niche`, `location`")

        uploaded = st.file_uploader("Choose a file", type=["csv", "xlsx", "xls"])

        if uploaded:
            try:
                if uploaded.name.endswith(".csv"):
                    import_df = pd.read_csv(uploaded)
                else:
                    import_df = pd.read_excel(uploaded)

                st.markdown(f"**Found {len(import_df)} rows with columns:** {', '.join(import_df.columns.tolist())}")
                st.dataframe(import_df.head(5), use_container_width=True, hide_index=True)

                col_options = ["(skip)"] + import_df.columns.tolist()

                st.markdown("### Map your columns")
                col1, col2, col3 = st.columns(3)
                with col1:
                    name_col = st.selectbox("Business Name", col_options, index=_find_col(col_options, ["business_name", "company", "name"]))
                    website_col = st.selectbox("Website", col_options, index=_find_col(col_options, ["website", "url", "domain"]))
                with col2:
                    email_col = st.selectbox("Email", col_options, index=_find_col(col_options, ["email", "email_address"]))
                    phone_col = st.selectbox("Phone", col_options, index=_find_col(col_options, ["phone", "mobile"]))
                with col3:
                    niche_col = st.selectbox("Niche", col_options, index=_find_col(col_options, ["niche", "category", "industry"]))
                    location_col = st.selectbox("Location", col_options, index=_find_col(col_options, ["location", "city", "area"]))

                if st.button("Import Leads", type="primary", use_container_width=True):
                    new_leads = []
                    for _, row in import_df.iterrows():
                        lead = {
                            "business_name": str(row.get(name_col, "")) if name_col != "(skip)" else "",
                            "website": str(row.get(website_col, "")) if website_col != "(skip)" else "",
                            "email": str(row.get(email_col, "")) if email_col != "(skip)" else "",
                            "email_source": "imported",
                            "phone": str(row.get(phone_col, "")) if phone_col != "(skip)" else "",
                            "niche": str(row.get(niche_col, "")) if niche_col != "(skip)" else "",
                            "location": str(row.get(location_col, "")) if location_col != "(skip)" else "",
                            "seo_score": "", "seo_issues": "",
                            "lead_score": "", "lead_grade": "",
                            "status": "new", "notes": "",
                            "added_date": datetime.now().strftime("%Y-%m-%d"),
                            "source": "imported",
                        }
                        if lead["business_name"] or lead["website"] or lead["email"]:
                            new_leads.append(lead)

                    if new_leads:
                        new_df = pd.DataFrame(new_leads)
                        leads_df = load_leads()
                        leads_df = pd.concat([leads_df, new_df], ignore_index=True)
                        save_leads(leads_df)
                        st.success(f"Imported {len(new_leads)} leads!")
                    else:
                        st.warning("No valid leads found in the file.")
            except Exception as e:
                st.error(f"Error reading file: {e}")


def _find_col(options, candidates):
    """Find best matching column index."""
    for c in candidates:
        for i, o in enumerate(options):
            if c.lower() == o.lower():
                return i
    return 0
