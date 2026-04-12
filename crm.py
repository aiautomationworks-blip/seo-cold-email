"""
Simple CRM / Lead Tracker - Track leads, responses, and deal status.
CSV-based, no database needed.
"""

import csv
import os
from datetime import datetime

from config import CRM_FILE, LEADS_CSV, SENT_LOG


# Lead statuses
STATUSES = [
    "new",           # Just scraped, not contacted
    "contacted",     # Initial email sent
    "followed_up",   # Follow-up(s) sent
    "replied",       # They responded
    "call_booked",   # Discovery call scheduled
    "proposal_sent", # Sent a proposal
    "won",           # Closed the deal!
    "lost",          # Not interested / ghosted
    "do_not_contact", # Opted out / asked to stop
]

CRM_FIELDS = [
    "email", "business_name", "website", "niche", "location", "phone",
    "status", "emails_sent", "last_contacted", "replied_date",
    "call_date", "notes", "deal_value", "created_date", "updated_date",
]


def init_crm():
    """Initialize CRM file if it doesn't exist."""
    os.makedirs(os.path.dirname(CRM_FILE) if os.path.dirname(CRM_FILE) else ".", exist_ok=True)
    if not os.path.exists(CRM_FILE) or os.path.getsize(CRM_FILE) == 0:
        with open(CRM_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CRM_FIELDS)
            writer.writeheader()
        print(f"Created CRM file: {CRM_FILE}")


def load_crm():
    """Load all CRM records."""
    init_crm()
    records = {}
    with open(CRM_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records[row["email"]] = row
    return records


def save_crm(records):
    """Save all CRM records."""
    with open(CRM_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CRM_FIELDS)
        writer.writeheader()
        for record in records.values():
            writer.writerow(record)


def sync_from_leads():
    """
    Import leads from leads.csv into CRM.
    Won't overwrite existing CRM entries.
    """
    crm = load_crm()
    imported = 0

    if not os.path.exists(LEADS_CSV):
        print(f"No leads file at {LEADS_CSV}")
        return

    with open(LEADS_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get("email", "").strip()
            if not email or email in crm:
                continue

            crm[email] = {
                "email": email,
                "business_name": row.get("business_name", ""),
                "website": row.get("website", ""),
                "niche": row.get("niche", ""),
                "location": row.get("location", ""),
                "phone": row.get("phone", ""),
                "status": "new",
                "emails_sent": 0,
                "last_contacted": "",
                "replied_date": "",
                "call_date": "",
                "notes": "",
                "deal_value": "",
                "created_date": datetime.now().strftime("%Y-%m-%d"),
                "updated_date": datetime.now().strftime("%Y-%m-%d"),
            }
            imported += 1

    save_crm(crm)
    print(f"Imported {imported} new leads into CRM (total: {len(crm)})")


def sync_from_sent_log():
    """Update CRM with email send data from sent log."""
    crm = load_crm()

    if not os.path.exists(SENT_LOG):
        return

    with open(SENT_LOG, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get("to_email", "")
            if email in crm and row.get("status") == "sent":
                crm[email]["emails_sent"] = int(crm[email].get("emails_sent", 0)) + 1
                crm[email]["last_contacted"] = row.get("sent_at", "")[:10]
                if crm[email]["status"] == "new":
                    crm[email]["status"] = "contacted"
                elif crm[email]["status"] == "contacted":
                    crm[email]["status"] = "followed_up"
                crm[email]["updated_date"] = datetime.now().strftime("%Y-%m-%d")

    save_crm(crm)


def update_lead(email, **kwargs):
    """Update a specific lead in the CRM."""
    crm = load_crm()
    if email not in crm:
        print(f"Lead not found: {email}")
        return

    for key, value in kwargs.items():
        if key in CRM_FIELDS:
            crm[email][key] = value

    crm[email]["updated_date"] = datetime.now().strftime("%Y-%m-%d")
    save_crm(crm)
    print(f"Updated: {email}")


def mark_replied(email, notes=""):
    """Mark a lead as replied."""
    update_lead(email, status="replied", replied_date=datetime.now().strftime("%Y-%m-%d"), notes=notes)


def mark_call_booked(email, call_date, notes=""):
    """Mark a lead as having a call booked."""
    update_lead(email, status="call_booked", call_date=call_date, notes=notes)


def mark_won(email, deal_value="", notes=""):
    """Mark a lead as a closed deal."""
    update_lead(email, status="won", deal_value=deal_value, notes=notes)


def mark_lost(email, notes=""):
    """Mark a lead as lost."""
    update_lead(email, status="lost", notes=notes)


def mark_do_not_contact(email, notes="Requested removal"):
    """Mark a lead as do-not-contact (respect their wish)."""
    update_lead(email, status="do_not_contact", notes=notes)


def get_dashboard():
    """Print a dashboard of your pipeline."""
    crm = load_crm()

    if not crm:
        print("CRM is empty. Run sync_from_leads() first.")
        return

    # Count by status
    status_counts = {}
    total_deal_value = 0
    for record in crm.values():
        status = record.get("status", "new")
        status_counts[status] = status_counts.get(status, 0) + 1
        if record.get("deal_value"):
            try:
                total_deal_value += float(record["deal_value"])
            except ValueError:
                pass

    print("\n" + "=" * 50)
    print("  COLD EMAIL OUTREACH DASHBOARD")
    print("=" * 50)
    print(f"\n  Total Leads: {len(crm)}")
    print(f"  Total Pipeline Value: ${total_deal_value:,.0f}")
    print(f"\n  --- Pipeline ---")

    for status in STATUSES:
        count = status_counts.get(status, 0)
        bar = "#" * count
        if count > 0:
            print(f"  {status:20s} | {count:4d} | {bar}")

    # Conversion rates
    total = len(crm)
    contacted = sum(1 for r in crm.values() if r.get("status") not in ("new",))
    replied = sum(1 for r in crm.values() if r.get("status") in ("replied", "call_booked", "proposal_sent", "won"))
    calls = sum(1 for r in crm.values() if r.get("status") in ("call_booked", "proposal_sent", "won"))
    won = status_counts.get("won", 0)

    print(f"\n  --- Conversion Rates ---")
    if total > 0:
        print(f"  Contacted:    {contacted}/{total} ({contacted/total*100:.1f}%)")
    if contacted > 0:
        print(f"  Reply Rate:   {replied}/{contacted} ({replied/contacted*100:.1f}%)")
    if replied > 0:
        print(f"  Call Rate:    {calls}/{replied} ({calls/replied*100:.1f}%)")
    if calls > 0:
        print(f"  Close Rate:   {won}/{calls} ({won/calls*100:.1f}%)")

    print("\n" + "=" * 50)


def list_leads(status=None, limit=20):
    """List leads, optionally filtered by status."""
    crm = load_crm()

    if status:
        filtered = {k: v for k, v in crm.items() if v.get("status") == status}
    else:
        filtered = crm

    print(f"\n{'Email':40s} | {'Business':25s} | {'Status':15s} | {'Sent':4s}")
    print("-" * 90)

    for i, (email, record) in enumerate(filtered.items()):
        if i >= limit:
            print(f"\n... and {len(filtered) - limit} more")
            break
        print(f"{email:40s} | {record.get('business_name', '')[:25]:25s} | "
              f"{record.get('status', 'new'):15s} | {record.get('emails_sent', 0):4s}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("CRM Commands:")
        print("  python crm.py sync       - Import leads & sync sent emails")
        print("  python crm.py dashboard   - Show pipeline dashboard")
        print("  python crm.py list [status] - List leads (optionally by status)")
        print("  python crm.py replied <email> - Mark lead as replied")
        print("  python crm.py call <email> <date> - Book a call")
        print("  python crm.py won <email> [value] - Mark as won")
        print("  python crm.py lost <email> - Mark as lost")
        print("  python crm.py remove <email> - Do not contact")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "sync":
        sync_from_leads()
        sync_from_sent_log()
        print("CRM synced!")
    elif cmd == "dashboard":
        get_dashboard()
    elif cmd == "list":
        status = sys.argv[2] if len(sys.argv) > 2 else None
        list_leads(status=status)
    elif cmd == "replied":
        if len(sys.argv) < 3:
            print("Usage: python crm.py replied <email>")
        else:
            notes = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
            mark_replied(sys.argv[2], notes=notes)
    elif cmd == "call":
        if len(sys.argv) < 4:
            print("Usage: python crm.py call <email> <date>")
        else:
            mark_call_booked(sys.argv[2], sys.argv[3])
    elif cmd == "won":
        if len(sys.argv) < 3:
            print("Usage: python crm.py won <email> [deal_value]")
        else:
            value = sys.argv[3] if len(sys.argv) > 3 else ""
            mark_won(sys.argv[2], deal_value=value)
    elif cmd == "lost":
        if len(sys.argv) < 3:
            print("Usage: python crm.py lost <email>")
        else:
            mark_lost(sys.argv[2])
    elif cmd == "remove":
        if len(sys.argv) < 3:
            print("Usage: python crm.py remove <email>")
        else:
            mark_do_not_contact(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
