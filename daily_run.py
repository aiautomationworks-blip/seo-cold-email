#!/usr/bin/env python3
"""
Daily Automation Script - Run this once a day (manually or via cron).
It handles: follow-ups → new outreach → CRM sync.

Usage:
    python daily_run.py              - Run full daily routine
    python daily_run.py --safe       - Follow-ups only (no new outreach)

Cron example (run daily at 9am):
    0 9 * * 1-5 cd /path/to/cold_email_system && python3 daily_run.py >> logs/daily.log 2>&1
"""

import os
import sys
from datetime import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))


def daily_routine(safe_mode=False):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"DAILY OUTREACH RUN — {timestamp}")
    print(f"{'='*60}")

    # Step 1: Send due follow-ups (most important!)
    print(f"\n--- Step 1: Sending follow-ups ---")
    from email_sender import run_followups
    run_followups()

    if not safe_mode:
        # Step 2: Send new outreach (up to daily limit)
        print(f"\n--- Step 2: Sending new outreach ---")
        from email_sender import run_cold_outreach
        run_cold_outreach(template_id="seo_audit", max_emails=10)

    # Step 3: Sync CRM
    print(f"\n--- Step 3: Syncing CRM ---")
    from crm import sync_from_leads, sync_from_sent_log, get_dashboard
    sync_from_leads()
    sync_from_sent_log()
    get_dashboard()

    print(f"\n{'='*60}")
    print(f"DAILY RUN COMPLETE — {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    safe = "--safe" in sys.argv
    daily_routine(safe_mode=safe)
