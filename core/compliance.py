"""Compliance Manager — CAN-SPAM compliance, unsubscribe management."""

import re
from datetime import datetime

from core.database_v2 import (
    load_unsubscribes, add_unsubscribe, load_replies,
    log_activity,
)


UNSUBSCRIBE_TEXT = """

---
If you'd rather not receive these emails, simply reply with "unsubscribe" and we'll remove you immediately.
{company_info}"""

SPAM_WORDS = [
    "act now", "buy now", "click here", "congratulations", "dear friend",
    "free", "guarantee", "limited time", "no obligation", "offer expires",
    "order now", "risk-free", "satisfaction guaranteed", "special promotion",
    "urgent", "winner", "you have been selected", "100% free",
    "cash bonus", "double your", "earn extra", "extra income",
    "million dollars", "no cost", "prize", "unlimited",
]


def check_can_send(email_address):
    """
    Check if we're allowed to send to this email.
    Returns (can_send: bool, reason: str).
    """
    if not email_address or not email_address.strip():
        return False, "No email address"

    # Check unsubscribe list
    unsubs = load_unsubscribes()
    if email_address.lower() in [u.lower() for u in unsubs]:
        return False, "Unsubscribed"

    # Check bounce history
    replies = load_replies()
    bounce_count = sum(
        1 for r in replies
        if r.get("from_email", "").lower() == email_address.lower() and r.get("is_bounce")
    )
    if bounce_count >= 2:
        return False, "Multiple bounces"

    # Check do-not-contact (via database)
    from core.database_v2 import get_connection, _ensure_db
    _ensure_db()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT status FROM leads WHERE email=? AND status='do_not_contact'",
            (email_address,),
        ).fetchone()
        if row:
            return False, "Do-not-contact status"
    finally:
        conn.close()

    return True, "OK"


def add_unsubscribe_link(body, settings=None):
    """Append unsubscribe text to email body."""
    if "reply with \"unsubscribe\"" in body.lower():
        return body  # Already has it

    company_info = ""
    if settings:
        parts = []
        if settings.get("your_company"):
            parts.append(settings["your_company"])
        if settings.get("your_website"):
            parts.append(settings["your_website"])
        company_info = " | ".join(parts)

    unsub = UNSUBSCRIBE_TEXT.replace("{company_info}", company_info)
    return body + unsub


def process_unsubscribe_replies(replies=None):
    """
    Auto-detect unsubscribe keywords in replies and add to unsubscribe list.
    Returns count of new unsubscribes.
    """
    if replies is None:
        replies = load_replies()

    keywords = {"unsubscribe", "stop", "remove me", "opt out", "opt-out",
                "no more", "take me off", "don't email", "stop emailing"}

    count = 0
    for reply in replies:
        if reply.get("processed"):
            continue

        body = reply.get("body", "").lower()
        subject = reply.get("subject", "").lower()
        combined = f"{subject} {body}"

        if any(kw in combined for kw in keywords):
            from_email = reply.get("from_email", "")
            if from_email:
                add_unsubscribe(from_email, "auto_detected_keyword")
                from core.database_v2 import update_lead_status
                update_lead_status(from_email, "do_not_contact")
                log_activity("auto_unsubscribe", f"{from_email} auto-unsubscribed")
                count += 1

    return count


def check_sending_compliance(subject, body):
    """
    Check email content for compliance issues.
    Returns list of warnings.
    """
    warnings = []

    # Check for spam words
    combined = f"{subject} {body}".lower()
    found_spam = [w for w in SPAM_WORDS if w in combined]
    if found_spam:
        warnings.append(f"Spam trigger words found: {', '.join(found_spam[:5])}")

    # Check for unsubscribe mechanism
    if "unsubscribe" not in body.lower():
        warnings.append("Missing unsubscribe option (CAN-SPAM requirement)")

    # Check for sender identification
    if not any(tag in body for tag in ["{your_name}", "{signature}"]):
        has_name = any(c.isalpha() for c in body[-200:]) if len(body) > 200 else True
        if not has_name:
            warnings.append("Missing sender identification")

    # Check subject line length
    if len(subject) > 80:
        warnings.append("Subject line too long (>80 chars) — may get truncated")

    # Check for ALL CAPS
    caps_words = re.findall(r'\b[A-Z]{4,}\b', subject)
    if caps_words:
        warnings.append(f"ALL CAPS in subject: {', '.join(caps_words[:3])}")

    # Check for excessive punctuation
    if subject.count("!") > 1 or subject.count("?") > 2:
        warnings.append("Excessive punctuation in subject line")

    return warnings


def get_compliance_score(subject, body):
    """
    Calculate compliance score 0-100.
    Higher = more compliant.
    """
    warnings = check_sending_compliance(subject, body)
    deductions = {
        "Spam trigger": 15,
        "Missing unsubscribe": 25,
        "Missing sender": 10,
        "Subject line too long": 5,
        "ALL CAPS": 10,
        "Excessive punctuation": 5,
    }

    score = 100
    for warning in warnings:
        for key, deduction in deductions.items():
            if key.lower() in warning.lower():
                score -= deduction
                break
        else:
            score -= 5  # Generic deduction

    return max(0, score)


def check_daily_sending_limits(account_email, settings):
    """Check if daily sending limit has been reached."""
    from core.database_v2 import get_connection, _ensure_db
    _ensure_db()

    daily_limit = settings.get("daily_limit", 5)
    today = datetime.now().strftime("%Y-%m-%d")

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT sends_today, last_send_date FROM email_accounts WHERE email=?",
            (account_email,),
        ).fetchone()

        if not row:
            return True, daily_limit  # No account record, allow

        if row["last_send_date"] != today:
            return True, daily_limit  # New day, allow

        remaining = daily_limit - row["sends_today"]
        return remaining > 0, remaining
    finally:
        conn.close()
