"""Email Sequences — execute campaign steps, manage variables, handle conditions."""

import random
from datetime import datetime

from core.campaigns import CampaignManager, SequenceStep
from core.database_v2 import (
    load_sent, save_reply, update_lead_status,
    log_activity, increment_account_sends, load_replies,
)
from outreach.email_sender import send_one_email
from outreach.templates import format_template


def build_variables(lead, settings):
    """
    Unified variable builder for templates.
    Replaces duplicate implementations across send_emails, followups, daily_run.
    """
    lead_dict = lead if isinstance(lead, dict) else lead.to_dict() if hasattr(lead, "to_dict") else dict(lead)

    seo_issues = str(lead_dict.get("seo_issues", ""))
    if seo_issues and seo_issues != "nan":
        issues_list = [i.strip() for i in seo_issues.split(";") if i.strip()]
        formatted_issues = "\n".join(f"- {issue}" for issue in issues_list[:5])
    else:
        formatted_issues = "- A few technical improvements that could boost your rankings"

    return {
        "business_name": str(lead_dict.get("business_name", "")),
        "website": str(lead_dict.get("website", "")),
        "niche": str(lead_dict.get("niche", "business")),
        "location": str(lead_dict.get("location", "")),
        "seo_issues": formatted_issues,
        "seo_score": str(lead_dict.get("seo_score", "")),
        "your_name": settings.get("your_name", ""),
        "your_company": settings.get("your_company", ""),
        "your_phone": settings.get("your_phone", ""),
        "your_calendly": settings.get("your_calendly", ""),
    }


class SequenceExecutor:
    """Execute campaign sequence steps with conditions and tracking."""

    def __init__(self, settings):
        self.settings = settings

    def execute_due_sends(self, campaign_id, max_sends=None):
        """Execute all due sends for a campaign. Returns (sent_count, errors)."""
        campaign = CampaignManager.get_campaign(campaign_id)
        if not campaign or campaign.status != "active":
            return 0, ["Campaign not active"]

        due = CampaignManager.get_due_sends(campaign_id)
        if not due:
            return 0, []

        # Get account
        account = self._get_account(campaign.account_email)
        if not account:
            return 0, ["No email account configured"]

        limit = max_sends or campaign.daily_limit
        sent_count = 0
        errors = []

        for item in due[:limit]:
            lead = item["lead"]
            step = item["step"]
            step_num = item["step_num"]

            # Check conditions before sending
            if self._should_skip(lead, campaign_id):
                continue

            # Build email content
            variables = build_variables(lead, self.settings)

            # A/B variant selection
            variant = "A"
            subject = step.subject
            body = step.body

            if step.variant_b_subject and step.variant_b_body:
                if random.random() < 0.5:
                    variant = "B"
                    subject = step.variant_b_subject
                    body = step.variant_b_body

            # Format with variables
            for key, val in variables.items():
                subject = subject.replace(f"{{{key}}}", str(val))
                body = body.replace(f"{{{key}}}", str(val))

            # Also format using template system for signature etc
            if step.template:
                subject, body = format_template(
                    step.template, variables,
                    followup_num=step_num,
                )

            # Send
            success, error = send_one_email(
                account,
                lead["email"],
                subject,
                body,
            )

            if success:
                sent_count += 1
                # Record in sent_emails
                self._record_send(lead, subject, step, campaign_id, step_num, account, variant)
                # Update lead status
                new_status = "contacted" if step_num == 0 else "followed_up"
                update_lead_status(lead["email"], new_status)
                increment_account_sends(account["email"])
                log_activity(
                    "email_sent",
                    f"Step {step_num + 1} sent to {lead['email']} (variant {variant})",
                    campaign_id=campaign_id,
                )
            else:
                errors.append(f"{lead['email']}: {error}")

        return sent_count, errors

    def _should_skip(self, lead, campaign_id):
        """Check if we should skip sending to this lead."""
        # Check reply history
        replies = load_replies()
        for r in replies:
            if r.get("from_email") == lead["email"] and r.get("campaign_id") == campaign_id:
                return True  # Already replied

        # Check bounce history
        for r in replies:
            if r.get("from_email") == lead["email"] and r.get("is_bounce"):
                return True  # Bounced

        # Check unsubscribe
        from core.database_v2 import load_unsubscribes
        if lead["email"] in load_unsubscribes():
            return True

        return False

    def _get_account(self, account_email):
        """Get email account config."""
        accounts = self.settings.get("email_accounts", [])
        if account_email:
            for acc in accounts:
                if acc.get("email") == account_email:
                    return acc
        return accounts[0] if accounts else None

    def _record_send(self, lead, subject, step, campaign_id, step_num, account, variant):
        """Record a sent email in the database."""
        import pandas as pd
        from core.database_v2 import get_connection, _ensure_db
        import uuid

        message_id = f"<{uuid.uuid4().hex}@{account['email'].split('@')[1]}>"

        _ensure_db()
        conn = get_connection()
        try:
            conn.execute("""
                INSERT INTO sent_emails (to_email, business_name, subject, template,
                    followup_num, from_email, sent_at, status, message_id,
                    campaign_id, sequence_step, variant)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                lead["email"],
                lead.get("business_name", ""),
                subject,
                step.template,
                step_num,
                account["email"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "sent",
                message_id,
                campaign_id,
                step_num,
                variant,
            ))
            conn.commit()
        finally:
            conn.close()

    def get_next_step(self, campaign_id, lead_email):
        """Get the next sequence step for a specific lead."""
        campaign = CampaignManager.get_campaign(campaign_id)
        if not campaign:
            return None

        import pandas as pd
        sent_df = load_sent()
        if len(sent_df) > 0:
            lead_sent = sent_df[
                (sent_df["to_email"] == lead_email) &
                (sent_df["campaign_id"] == campaign_id)
            ]
            current_step = len(lead_sent)
        else:
            current_step = 0

        if current_step < len(campaign.sequence):
            return campaign.sequence[current_step]
        return None


def is_in_send_window(timezone_offset=0):
    """
    Check if current time is within sending window.
    Optimal: 9-11 AM and 2-4 PM recipient time.
    Acceptable: 9 AM - 6 PM.
    """
    from datetime import timedelta
    now = datetime.now() + timedelta(hours=timezone_offset)
    hour = now.hour
    weekday = now.weekday()

    # Skip weekends
    if weekday >= 5:
        return False, "weekend"

    # Optimal windows
    if 9 <= hour <= 11 or 14 <= hour <= 16:
        return True, "optimal"

    # Acceptable window
    if 9 <= hour <= 18:
        return True, "acceptable"

    return False, "outside_hours"
