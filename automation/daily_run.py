#!/usr/bin/env python3
"""
Daily Automation Script — for GitHub Actions or manual cron.
Finds new leads, sends emails, sends follow-ups.

Usage:
    python automation/daily_run.py              - Full daily routine
    python automation/daily_run.py --safe       - Follow-ups only
    python automation/daily_run.py --leads-only - Find leads only
"""

import os
import random
import sys
import time
import urllib.parse
from datetime import datetime, timedelta

# Ensure imports work from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from core.settings import load_settings
from core.database import load_leads, save_leads, load_sent, save_sent
from scrapers.registry import get_all_scrapers
from analyzers.email_finder import analyze_website
from analyzers.lead_scorer import score_lead
from outreach.templates import TEMPLATES, format_template
from outreach.email_sender import send_one_email


def daily_routine(safe_mode=False, leads_only=False):
    """Run the daily autopilot routine."""
    settings = load_settings()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'='*60}")
    print(f"DAILY OUTREACH RUN — {timestamp}")
    print(f"Mode: {'SAFE (follow-ups only)' if safe_mode else 'LEADS ONLY' if leads_only else 'FULL'}")
    print(f"{'='*60}")

    if not settings.get("autopilot_enabled", False) and not any(a in sys.argv for a in ["--force", "--safe", "--leads-only"]):
        print("Autopilot is disabled. Enable it in the app or use --force flag.")
        return

    # Override email credentials from env if available (GitHub Actions)
    if os.environ.get("GMAIL_ADDRESS") and os.environ.get("GMAIL_PASSWORD"):
        settings["email_accounts"] = [{
            "email": os.environ["GMAIL_ADDRESS"],
            "password": os.environ["GMAIL_PASSWORD"],
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "name": settings.get("your_name", ""),
        }]

    # ─── Step 1: Find new leads ───
    if not safe_mode:
        print(f"\n--- Step 1: Finding new leads ---")
        _find_new_leads(settings)

    if leads_only:
        print("\nLeads-only mode. Skipping email sends.")
        return

    # ─── Step 2: Send follow-ups ───
    print(f"\n--- Step 2: Sending follow-ups ---")
    _send_followups(settings)

    if not safe_mode:
        # ─── Step 3: Send new outreach ───
        print(f"\n--- Step 3: Sending new outreach ---")
        _send_new_outreach(settings)

    print(f"\n{'='*60}")
    print(f"DAILY RUN COMPLETE — {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")


def _find_new_leads(settings):
    """Find and save new leads."""
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
    active = [scrapers_dict[s]() for s in selected if s in scrapers_dict]
    if not active:
        active = [list(scrapers_dict.values())[0]()]

    new_leads = []
    for niche in niches:
        for location in locations:
            if len(new_leads) >= max_leads:
                break
            for scraper in active:
                if len(new_leads) >= max_leads:
                    break
                print(f"  [{scraper.name}] {niche} in {location}...")
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
                        print(f"    Found: {lead['business_name']} (Score: {scoring['total_score']})")
                except Exception as e:
                    print(f"    Error: {e}")

    if new_leads:
        new_df = pd.DataFrame(new_leads)
        leads_df = pd.concat([leads_df, new_df], ignore_index=True)
        save_leads(leads_df)
        print(f"  Saved {len(new_leads)} new leads")
    else:
        print("  No new leads found")


def _send_followups(settings):
    """Send due follow-up emails."""
    if not settings.get("email_accounts"):
        print("  No email account configured")
        return

    sent_df = load_sent()
    leads_df = load_leads()
    if len(sent_df) == 0:
        print("  No emails sent yet")
        return

    followup_days = settings.get("followup_days", [3, 7, 14])
    account = settings["email_accounts"][0]
    sent_count = 0

    for to_email in sent_df["to_email"].unique():
        if len(leads_df) > 0:
            lead_row = leads_df[leads_df["email"] == to_email]
            if len(lead_row) > 0:
                status = str(lead_row.iloc[0].get("status", ""))
                if status in ["replied", "won", "lost", "do_not_contact", "call_booked"]:
                    continue

        emails_to = sent_df[sent_df["to_email"] == to_email].sort_values("sent_at")
        if len(emails_to) >= 4:
            continue
        last = emails_to.iloc[-1]
        if last.get("status") == "failed":
            continue

        try:
            last_date = datetime.strptime(str(last["sent_at"])[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue

        delay_idx = min(len(emails_to) - 1, len(followup_days) - 1)
        due_date = last_date + timedelta(days=followup_days[delay_idx])
        if datetime.now() < due_date:
            continue

        lead_row = leads_df[leads_df["email"] == to_email]
        lead = lead_row.iloc[0] if len(lead_row) > 0 else {}
        variables = {
            "business_name": str(last.get("business_name", "")),
            "website": str(lead.get("website", "")) if isinstance(lead, pd.Series) else "",
            "niche": str(lead.get("niche", "business")) if isinstance(lead, pd.Series) else "business",
            "location": str(lead.get("location", "")) if isinstance(lead, pd.Series) else "",
            "seo_issues": str(lead.get("seo_issues", "")) if isinstance(lead, pd.Series) else "",
            "your_name": settings.get("your_name", ""),
            "your_company": settings.get("your_company", ""),
            "your_phone": settings.get("your_phone", ""),
            "your_calendly": settings.get("your_calendly", ""),
        }

        template_name = str(last.get("template", list(TEMPLATES.keys())[0]))
        if template_name not in TEMPLATES:
            template_name = list(TEMPLATES.keys())[0]
        subj, body = format_template(template_name, variables, followup_num=len(emails_to))
        success, error = send_one_email(account, to_email, subj, body)

        record = {
            "to_email": to_email, "business_name": str(last.get("business_name", "")),
            "subject": subj, "template": template_name,
            "followup_num": len(emails_to), "from_email": account["email"],
            "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "sent" if success else "failed",
        }
        sent_df = load_sent()
        sent_df = pd.concat([sent_df, pd.DataFrame([record])], ignore_index=True)
        save_sent(sent_df)

        if success:
            sent_count += 1
            leads_df.loc[leads_df["email"] == to_email, "status"] = "followed_up"
            save_leads(leads_df)
            print(f"  Follow-up sent to: {to_email}")

        time.sleep(random.uniform(30, 60))

    print(f"  Sent {sent_count} follow-ups")


def _send_new_outreach(settings):
    """Send initial outreach emails."""
    if not settings.get("email_accounts"):
        print("  No email account configured")
        return

    sent_df = load_sent()
    leads_df = load_leads()
    sent_emails = set(sent_df["to_email"].tolist()) if len(sent_df) > 0 else set()

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
    sent_count = 0

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
            "to_email": to_email, "business_name": str(lead.get("business_name", "")),
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
            sent_count += 1
            print(f"  Sent to: {to_email}")

        time.sleep(random.uniform(30, 60))

    print(f"  Sent {sent_count} new emails")


if __name__ == "__main__":
    safe = "--safe" in sys.argv
    leads_only = "--leads-only" in sys.argv
    daily_routine(safe_mode=safe, leads_only=leads_only)
