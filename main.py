#!/usr/bin/env python3
"""
Cold Email Outreach System - Main Runner
Get SEO clients through automated cold email outreach.

Usage:
    python main.py                  - Interactive menu
    python main.py scrape           - Scrape new leads
    python main.py find-emails      - Find emails for leads
    python main.py audit <url>      - Audit a single website
    python main.py send             - Send cold emails (interactive)
    python main.py send --dry-run   - Preview emails without sending
    python main.py followups        - Send due follow-ups
    python main.py crm              - Open CRM dashboard
"""

import os
import sys

# Change to script directory so imports work
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════╗
║          COLD EMAIL OUTREACH SYSTEM FOR SEO             ║
║          ─────────────────────────────────               ║
║          Get SEO Clients on Autopilot                    ║
║          $0 Budget Required                              ║
╚══════════════════════════════════════════════════════════╝
    """)


def print_menu():
    print("""
    WHAT DO YOU WANT TO DO?
    ─────────────────────────

    [1] Scrape Leads        - Auto-find businesses from the internet
    [2] Add Leads Manually  - Type in leads one by one
    [3] Import Leads CSV    - Import from a spreadsheet file
    [4] Find Emails         - Find email addresses for your leads
    [5] SEO Audit           - Check a website's SEO problems
    [6] Send Cold Emails    - Send personalized outreach
    [7] Preview Emails      - See what emails look like (safe, no sending)
    [8] Send Follow-ups     - Follow up with people who didn't reply
    [9] CRM Dashboard       - See your pipeline and stats
    [10] Quick Start Guide  - Step-by-step instructions
    [11] Google Maps Guide  - How to get leads from Google Maps
    [0] Exit

    """)


def quick_start_guide():
    print("""
    ══════════════════════════════════════════════════════
    QUICK START GUIDE — Get Your First Client in 7 Days
    ══════════════════════════════════════════════════════

    STEP 1: SET UP YOUR EMAIL (Day 1)
    ──────────────────────────────────
    a) Create a NEW Gmail account (don't use your personal one)
       → e.g., yourname.seo@gmail.com
    b) Enable 2-Factor Authentication
    c) Create an App Password:
       → Google Account → Security → 2-Step Verification → App Passwords
       → Select "Mail" → Generate → Copy the 16-character password
    d) Edit config.py with your email and app password

    STEP 2: WARM UP YOUR EMAIL (Days 1-3)
    ──────────────────────────────────────
    → Send 5-10 normal emails per day to friends/other accounts
    → Reply to them, mark as important
    → This tells Google you're a real person, not a spammer
    → Start cold outreach at 5/day, increase by 5 every 3 days
    → Max out at 25-30/day per Gmail account

    STEP 3: CONFIGURE YOUR TARGETS (Day 1)
    ───────────────────────────────────────
    → Edit config.py — set your target niches and locations
    → Best niches for SEO: dentists, lawyers, plumbers, roofers,
      HVAC, chiropractors, med spas, real estate agents
    → Start with YOUR city or nearby cities

    STEP 4: SCRAPE LEADS (Day 2)
    ────────────────────────────
    → Option [1] from this menu
    → This finds businesses in your target niches/locations
    → Extracts their website, email, phone, and SEO issues

    STEP 5: ENRICH + VERIFY EMAILS (Day 2)
    ──────────────────────────────────────
    → Option [2] then [3] from this menu
    → Finds real email addresses from their websites
    → Verifies the emails are deliverable

    STEP 6: SEND COLD EMAILS (Day 3+)
    ─────────────────────────────────
    → Option [7] first to PREVIEW (always preview first!)
    → Option [5] to send for real
    → Start with 5-10 emails per day
    → The system will auto-personalize with their SEO issues

    STEP 7: FOLLOW UP (Days 6, 10, 17)
    ──────────────────────────────────
    → Option [6] — sends follow-ups to people who haven't replied
    → Follow-ups are where most deals close
    → Run this every day

    STEP 8: MANAGE RESPONSES (Ongoing)
    ─────────────────────────────────
    → Option [8] for your pipeline dashboard
    → When someone replies:
      python crm.py replied their@email.com
    → When you book a call:
      python crm.py call their@email.com 2024-01-15
    → When you close:
      python crm.py won their@email.com 1500

    ══════════════════════════════════════════════════════
    TIPS FOR SUCCESS:
    ──────────────────
    • Personalization is EVERYTHING — the SEO audit makes you
      stand out from every other cold email they get
    • Follow up AT LEAST 3 times — most deals close on follow-up #2-3
    • Keep subject lines short and curiosity-driven
    • NEVER send more than 30 emails/day per Gmail account
    • Reply to everyone — even "not interested" deserves a polite reply
    • Offer a FREE mini-audit call — low barrier to entry
    • Track everything in the CRM
    ══════════════════════════════════════════════════════
    """)


def run_interactive():
    print_banner()

    while True:
        print_menu()
        choice = input("    Enter choice: ").strip()

        if choice == "0":
            print("\n    Goodbye! Go close some deals.\n")
            break

        elif choice == "1":
            print("\n    Starting lead scraper...\n")
            from lead_scraper import scrape_leads
            scrape_leads()

        elif choice == "2":
            print("\n    Add leads one by one...\n")
            from lead_scraper import add_lead_interactive
            add_lead_interactive()

        elif choice == "3":
            csv_path = input("    Path to your CSV file: ").strip()
            if csv_path:
                from lead_scraper import import_csv
                import_csv(csv_path)
            else:
                print("    No file path given.")

        elif choice == "4":
            print("\n    Finding emails for leads...\n")
            from email_finder import enrich_leads_with_emails
            enrich_leads_with_emails()

        elif choice == "5":
            url = input("    Enter website URL: ").strip()
            if url:
                if not url.startswith("http"):
                    url = f"https://{url}"
                from seo_auditor import quick_seo_audit, format_audit_for_email
                audit = quick_seo_audit(url)
                print(f"\n    SEO Score: {audit['score']}/100")
                print(f"    Summary: {audit['summary']}")
                print(f"\n    Issues:")
                for issue in audit["issues"]:
                    print(f"      [{issue['severity'].upper():6s}] {issue['issue']}")
                    print(f"               {issue['impact']}")
                print(f"\n    Email-ready snippet:")
                print(format_audit_for_email(audit))

        elif choice == "6":
            print("\n    Available templates:")
            from templates.emails import ALL_TEMPLATES
            for i, t in enumerate(ALL_TEMPLATES):
                print(f"      [{i+1}] {t['name']}")

            t_choice = input("\n    Choose template (1-4) [1]: ").strip() or "1"
            template_id = ALL_TEMPLATES[int(t_choice) - 1]["id"]

            max_emails = input("    Max emails to send (or 'all') [10]: ").strip() or "10"
            max_emails = None if max_emails == "all" else int(max_emails)

            confirm = input(f"\n    Send up to {max_emails or 'all'} emails with '{template_id}' template? (y/n): ").strip()
            if confirm.lower() == "y":
                from email_sender import run_cold_outreach
                run_cold_outreach(template_id=template_id, max_emails=max_emails)

        elif choice == "7":
            print("\n    Previewing emails (DRY RUN — nothing will be sent)...\n")
            from templates.emails import ALL_TEMPLATES
            print("    Available templates:")
            for i, t in enumerate(ALL_TEMPLATES):
                print(f"      [{i+1}] {t['name']}")

            t_choice = input("\n    Choose template (1-4) [1]: ").strip() or "1"
            template_id = ALL_TEMPLATES[int(t_choice) - 1]["id"]

            from email_sender import run_cold_outreach
            run_cold_outreach(template_id=template_id, max_emails=3, dry_run=True)

        elif choice == "8":
            print("\n    Checking for due follow-ups...\n")
            from email_sender import run_followups
            run_followups()

        elif choice == "9":
            from crm import sync_from_leads, sync_from_sent_log, get_dashboard
            sync_from_leads()
            sync_from_sent_log()
            get_dashboard()

        elif choice == "10":
            quick_start_guide()

        elif choice == "11":
            from lead_scraper import google_maps_manual_help
            google_maps_manual_help()

        else:
            print("    Invalid choice. Try again.")

        input("\n    Press Enter to continue...")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "scrape":
            from lead_scraper import scrape_leads
            scrape_leads()

        elif cmd == "find-emails":
            from email_finder import enrich_leads_with_emails
            enrich_leads_with_emails()

        elif cmd == "verify-emails":
            from email_finder import verify_lead_emails
            verify_lead_emails()

        elif cmd == "audit":
            if len(sys.argv) < 3:
                print("Usage: python main.py audit <url>")
            else:
                url = sys.argv[2]
                if not url.startswith("http"):
                    url = f"https://{url}"
                from seo_auditor import quick_seo_audit
                audit = quick_seo_audit(url)
                print(f"Score: {audit['score']}/100 | {audit['summary']}")
                for i in audit["issues"]:
                    print(f"  [{i['severity']}] {i['issue']}: {i['impact']}")

        elif cmd == "send":
            dry_run = "--dry-run" in sys.argv
            template = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("-") else "seo_audit"
            from email_sender import run_cold_outreach
            run_cold_outreach(template_id=template, dry_run=dry_run)

        elif cmd == "followups":
            from email_sender import run_followups
            run_followups()

        elif cmd == "crm":
            from crm import sync_from_leads, sync_from_sent_log, get_dashboard
            sync_from_leads()
            sync_from_sent_log()
            get_dashboard()

        else:
            print(f"Unknown command: {cmd}")
            print("Run 'python main.py' for interactive menu")
    else:
        run_interactive()
