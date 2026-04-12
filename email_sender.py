"""
Cold Email Sender - Sends personalized cold emails with follow-up sequences.
Uses SMTP (Gmail/Outlook) — completely free.
"""

import csv
import email.mime.multipart
import email.mime.text
import os
import random
import smtplib
import time
from datetime import datetime, timedelta

from config import (
    EMAIL_ACCOUNTS,
    EMAIL_LOG,
    FOLLOWUP_DELAYS,
    LEADS_CSV,
    MAX_DELAY_BETWEEN_EMAILS,
    MIN_DELAY_BETWEEN_EMAILS,
    SENT_LOG,
    YOUR_CALENDLY,
    YOUR_COMPANY,
    YOUR_NAME,
    YOUR_PHONE,
    YOUR_WEBSITE,
)
from seo_auditor import format_audit_for_email, quick_seo_audit
from templates.emails import ALL_TEMPLATES, format_email, get_template


def load_sent_log():
    """Load record of previously sent emails."""
    sent = {}
    if os.path.exists(SENT_LOG):
        with open(SENT_LOG, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row.get("to_email", "")
                if key not in sent:
                    sent[key] = []
                sent[key].append(row)
    return sent


def log_sent_email(to_email, subject, template_id, followup_num, from_email, status="sent"):
    """Log a sent email."""
    os.makedirs(os.path.dirname(SENT_LOG) if os.path.dirname(SENT_LOG) else ".", exist_ok=True)

    file_exists = os.path.exists(SENT_LOG) and os.path.getsize(SENT_LOG) > 0
    fieldnames = ["to_email", "subject", "template_id", "followup_num", "from_email",
                  "sent_at", "status"]

    with open(SENT_LOG, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "to_email": to_email,
            "subject": subject,
            "template_id": template_id,
            "followup_num": followup_num,
            "from_email": from_email,
            "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": status,
        })


def log_message(message):
    """Write to log file."""
    os.makedirs(os.path.dirname(EMAIL_LOG) if os.path.dirname(EMAIL_LOG) else ".", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(EMAIL_LOG, "a") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"  {message}")


def send_email(smtp_config, to_email, subject, body, reply_to=None):
    """
    Send a single email via SMTP.
    Returns True if sent successfully.
    """
    try:
        msg = email.mime.multipart.MIMEMultipart("alternative")
        msg["From"] = f"{smtp_config['name']} <{smtp_config['email']}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        if reply_to:
            msg["Reply-To"] = reply_to

        # Plain text version
        msg.attach(email.mime.text.MIMEText(body, "plain"))

        # Connect and send
        server = smtplib.SMTP(smtp_config["smtp_server"], smtp_config["smtp_port"])
        server.starttls()
        server.login(smtp_config["email"], smtp_config["password"])
        server.send_message(msg)
        server.quit()

        return True

    except smtplib.SMTPAuthenticationError:
        log_message(f"AUTH ERROR: Check email/password for {smtp_config['email']}")
        log_message("For Gmail: Enable 2FA, then create App Password at myaccount.google.com")
        return False
    except smtplib.SMTPRecipientsRefused:
        log_message(f"REJECTED: {to_email} — email address rejected by server")
        return False
    except Exception as e:
        log_message(f"ERROR sending to {to_email}: {str(e)[:100]}")
        return False


def get_next_account(accounts, sent_today):
    """
    Pick the email account that hasn't hit its daily limit yet.
    Distributes sends across accounts.
    """
    for account in accounts:
        email_addr = account["email"]
        count = sent_today.get(email_addr, 0)
        if count < account["daily_limit"]:
            return account
    return None


def run_cold_outreach(
    template_id="seo_audit",
    max_emails=None,
    dry_run=False,
    run_audit=True,
):
    """
    Main outreach function. Sends personalized cold emails.

    Args:
        template_id: Which email template to use
        max_emails: Maximum emails to send in this run (None = send all)
        dry_run: If True, print emails but don't actually send
        run_audit: If True, run SEO audit for personalization
    """
    # Load leads
    if not os.path.exists(LEADS_CSV):
        print(f"No leads found at {LEADS_CSV}")
        print("Run lead_scraper.py first to get leads.")
        return

    leads = []
    with open(LEADS_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("email", "").strip():
                leads.append(row)

    if not leads:
        print("No leads with email addresses found.")
        return

    # Load sent log
    sent_log = load_sent_log()

    # Track sends per account today
    sent_today = {}
    today = datetime.now().strftime("%Y-%m-%d")
    for email_addr, entries in sent_log.items():
        for entry in entries:
            if entry.get("sent_at", "").startswith(today):
                from_addr = entry.get("from_email", "")
                sent_today[from_addr] = sent_today.get(from_addr, 0) + 1

    # Get template
    template = get_template(template_id)

    print("=" * 60)
    print(f"COLD EMAIL OUTREACH — Template: {template['name']}")
    print(f"Leads loaded: {len(leads)}")
    print(f"{'DRY RUN MODE' if dry_run else 'LIVE MODE'}")
    print("=" * 60)

    emails_sent = 0
    emails_skipped = 0

    for lead in leads:
        if max_emails and emails_sent >= max_emails:
            print(f"\nReached limit of {max_emails} emails. Stopping.")
            break

        to_email = lead.get("email", "").strip()
        website = lead.get("website", "").strip()
        business_name = lead.get("business_name", "").strip()
        niche = lead.get("niche", "business").strip()
        location = lead.get("location", "your area").strip()

        # Skip if already emailed
        if to_email in sent_log:
            existing = sent_log[to_email]
            if len(existing) >= 4:  # All follow-ups sent
                emails_skipped += 1
                continue

        # Get email account
        account = get_next_account(EMAIL_ACCOUNTS, sent_today)
        if not account:
            print("\nAll email accounts hit daily limits. Try again tomorrow.")
            break

        # Run SEO audit for personalization
        seo_issues_text = ""
        specific_fix = ""
        seo_score = ""
        if run_audit and website:
            print(f"\n[{emails_sent + 1}] Auditing: {website}")
            audit = quick_seo_audit(website)
            seo_issues_text = format_audit_for_email(audit)
            specific_fix = audit.get("specific_fix", "")
            seo_score = str(audit.get("score", ""))

        # Build variables
        variables = {
            "name": business_name.split()[0] if business_name else "",  # First word as name guess
            "business_name": business_name or "your business",
            "website": website,
            "niche": niche,
            "location": location,
            "seo_issues": seo_issues_text or "a few SEO issues that could be improved",
            "specific_fix": specific_fix or "some quick SEO improvements",
            "seo_score": seo_score,
            "your_name": YOUR_NAME,
            "your_company": YOUR_COMPANY,
            "your_phone": YOUR_PHONE,
            "your_calendly": YOUR_CALENDLY,
            "your_website": YOUR_WEBSITE,
        }

        # Determine which email to send (initial or follow-up)
        followup_num = 0
        if to_email in sent_log:
            followup_num = len(sent_log[to_email])

        # Format email
        subject, body = format_email(template, variables, followup_num=followup_num)

        if dry_run:
            print(f"\n{'='*40} DRY RUN {'='*40}")
            print(f"TO: {to_email}")
            print(f"FROM: {account['email']}")
            print(f"SUBJECT: {subject}")
            print(f"FOLLOW-UP: #{followup_num}")
            print(f"-" * 40)
            print(body)
            print(f"{'='*40}")
            emails_sent += 1
            continue

        # Send it
        print(f"\n[{emails_sent + 1}] Sending to: {to_email} (follow-up #{followup_num})")
        success = send_email(account, to_email, subject, body)

        if success:
            log_sent_email(to_email, subject, template_id, followup_num, account["email"])
            log_message(f"SENT to {to_email} | Template: {template_id} | Follow-up: {followup_num}")
            sent_today[account["email"]] = sent_today.get(account["email"], 0) + 1
            emails_sent += 1
        else:
            log_sent_email(to_email, subject, template_id, followup_num, account["email"], status="failed")
            log_message(f"FAILED to send to {to_email}")

        # Random delay between emails
        delay = random.uniform(MIN_DELAY_BETWEEN_EMAILS, MAX_DELAY_BETWEEN_EMAILS)
        print(f"  Waiting {delay:.0f}s before next email...")
        time.sleep(delay)

    print(f"\n{'='*60}")
    print(f"DONE! Sent: {emails_sent} | Skipped: {emails_skipped}")
    print(f"{'='*60}")


def run_followups():
    """
    Check sent log and send follow-ups where due.
    """
    if not os.path.exists(SENT_LOG):
        print("No sent emails found. Run initial outreach first.")
        return

    sent_log = load_sent_log()
    followups_due = []

    for to_email, entries in sent_log.items():
        # Sort by sent date
        entries.sort(key=lambda x: x.get("sent_at", ""))

        # Get latest send
        latest = entries[-1]
        followup_num = len(entries)

        if followup_num >= 4:  # All follow-ups done
            continue

        if latest.get("status") == "failed":
            continue

        # Check if enough time has passed
        sent_at = datetime.strptime(latest["sent_at"], "%Y-%m-%d %H:%M:%S")
        delay_days = FOLLOWUP_DELAYS[min(followup_num - 1, len(FOLLOWUP_DELAYS) - 1)]
        due_date = sent_at + timedelta(days=delay_days)

        if datetime.now() >= due_date:
            followups_due.append({
                "to_email": to_email,
                "followup_num": followup_num,
                "template_id": latest.get("template_id", "seo_audit"),
                "last_subject": latest.get("subject", ""),
            })

    if not followups_due:
        print("No follow-ups due right now.")
        return

    print(f"Found {len(followups_due)} follow-ups to send")

    # Load leads for context
    leads_by_email = {}
    if os.path.exists(LEADS_CSV):
        with open(LEADS_CSV, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("email"):
                    leads_by_email[row["email"]] = row

    sent_today = {}
    for followup in followups_due:
        account = get_next_account(EMAIL_ACCOUNTS, sent_today)
        if not account:
            print("All accounts hit daily limits.")
            break

        to_email = followup["to_email"]
        template = get_template(followup["template_id"])
        lead = leads_by_email.get(to_email, {})

        variables = {
            "name": lead.get("business_name", "").split()[0] if lead.get("business_name") else "",
            "business_name": lead.get("business_name", "your business"),
            "website": lead.get("website", "your website"),
            "niche": lead.get("niche", "business"),
            "location": lead.get("location", "your area"),
            "seo_issues": lead.get("seo_issues", ""),
            "specific_fix": "",
            "seo_score": "",
            "your_name": YOUR_NAME,
            "your_company": YOUR_COMPANY,
            "your_phone": YOUR_PHONE,
            "your_calendly": YOUR_CALENDLY,
            "your_website": YOUR_WEBSITE,
        }

        subject, body = format_email(template, variables, followup_num=followup["followup_num"])

        print(f"\nSending follow-up #{followup['followup_num']} to {to_email}")
        success = send_email(account, to_email, subject, body)

        if success:
            log_sent_email(to_email, subject, followup["template_id"],
                          followup["followup_num"], account["email"])
            sent_today[account["email"]] = sent_today.get(account["email"], 0) + 1
        else:
            log_sent_email(to_email, subject, followup["template_id"],
                          followup["followup_num"], account["email"], status="failed")

        delay = random.uniform(MIN_DELAY_BETWEEN_EMAILS, MAX_DELAY_BETWEEN_EMAILS)
        time.sleep(delay)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--followups":
        run_followups()
    elif len(sys.argv) > 1 and sys.argv[1] == "--dry-run":
        template_id = sys.argv[2] if len(sys.argv) > 2 else "seo_audit"
        max_emails = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        run_cold_outreach(template_id=template_id, max_emails=max_emails, dry_run=True)
    else:
        template_id = sys.argv[1] if len(sys.argv) > 1 else "seo_audit"
        max_emails = int(sys.argv[2]) if len(sys.argv) > 2 else None
        run_cold_outreach(template_id=template_id, max_emails=max_emails)
