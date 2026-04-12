"""Campaign System — create, manage, and execute multi-step email campaigns."""

import json
import uuid
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Optional

from core.database_v2 import (
    load_campaigns, save_campaign, get_campaign_stats,
    get_leads_for_campaign, load_sent, log_activity,
)


@dataclass
class SequenceStep:
    """A single step in an email campaign sequence."""
    step_num: int = 1
    template: str = ""
    subject: str = ""
    body: str = ""
    delay_days: int = 0       # days to wait after previous step
    variant_b_subject: str = ""  # A/B test variant
    variant_b_body: str = ""

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Campaign:
    """A campaign with a sequence of email steps."""
    id: str = ""
    name: str = ""
    status: str = "draft"       # draft, active, paused, completed
    template: str = ""
    sequence: List[SequenceStep] = field(default_factory=list)
    account_email: str = ""
    daily_limit: int = 5
    created_at: str = ""
    updated_at: str = ""
    started_at: str = ""
    paused_at: str = ""
    completed_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_db_dict(self):
        """Convert to dict for database storage."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "template": self.template,
            "sequence_json": json.dumps([s.to_dict() for s in self.sequence]),
            "account_email": self.account_email,
            "daily_limit": self.daily_limit,
            "created_at": self.created_at,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "started_at": self.started_at,
            "paused_at": self.paused_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_db_dict(cls, d):
        """Create Campaign from database row dict."""
        seq_json = d.get("sequence_json", "[]")
        try:
            steps_data = json.loads(seq_json) if seq_json else []
        except (json.JSONDecodeError, TypeError):
            steps_data = []

        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            status=d.get("status", "draft"),
            template=d.get("template", ""),
            sequence=[SequenceStep.from_dict(s) for s in steps_data],
            account_email=d.get("account_email", ""),
            daily_limit=d.get("daily_limit", 5),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            started_at=d.get("started_at", ""),
            paused_at=d.get("paused_at", ""),
            completed_at=d.get("completed_at", ""),
        )


class CampaignManager:
    """Manage campaigns: create, pause, resume, assign leads, get stats."""

    @staticmethod
    def create_campaign(name, template="", sequence=None, account_email="", daily_limit=5):
        """Create a new campaign."""
        campaign = Campaign(
            name=name,
            template=template,
            sequence=sequence or [],
            account_email=account_email,
            daily_limit=daily_limit,
        )
        save_campaign(campaign.to_db_dict())
        log_activity("campaign_created", f"Campaign '{name}' created", campaign_id=campaign.id)
        return campaign

    @staticmethod
    def get_campaign(campaign_id):
        """Get a single campaign by ID."""
        campaigns = load_campaigns()
        for c in campaigns:
            if c["id"] == campaign_id:
                return Campaign.from_db_dict(c)
        return None

    @staticmethod
    def list_campaigns():
        """List all campaigns."""
        campaigns = load_campaigns()
        return [Campaign.from_db_dict(c) for c in campaigns]

    @staticmethod
    def activate_campaign(campaign_id):
        """Set campaign to active."""
        campaign = CampaignManager.get_campaign(campaign_id)
        if campaign:
            campaign.status = "active"
            campaign.started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_campaign(campaign.to_db_dict())
            log_activity("campaign_activated", f"Campaign '{campaign.name}' activated", campaign_id=campaign_id)

    @staticmethod
    def pause_campaign(campaign_id):
        """Pause a campaign."""
        campaign = CampaignManager.get_campaign(campaign_id)
        if campaign:
            campaign.status = "paused"
            campaign.paused_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_campaign(campaign.to_db_dict())
            log_activity("campaign_paused", f"Campaign '{campaign.name}' paused", campaign_id=campaign_id)

    @staticmethod
    def resume_campaign(campaign_id):
        """Resume a paused campaign."""
        campaign = CampaignManager.get_campaign(campaign_id)
        if campaign:
            campaign.status = "active"
            campaign.paused_at = ""
            save_campaign(campaign.to_db_dict())
            log_activity("campaign_resumed", f"Campaign '{campaign.name}' resumed", campaign_id=campaign_id)

    @staticmethod
    def complete_campaign(campaign_id):
        """Mark campaign as completed."""
        campaign = CampaignManager.get_campaign(campaign_id)
        if campaign:
            campaign.status = "completed"
            campaign.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_campaign(campaign.to_db_dict())
            log_activity("campaign_completed", f"Campaign '{campaign.name}' completed", campaign_id=campaign_id)

    @staticmethod
    def assign_leads(campaign_id, lead_emails):
        """Assign leads to a campaign by updating their campaign_id."""
        from core.database_v2 import get_connection, _ensure_db
        _ensure_db()
        conn = get_connection()
        try:
            for email in lead_emails:
                conn.execute(
                    "UPDATE leads SET campaign_id=?, updated_at=datetime('now') WHERE email=?",
                    (campaign_id, email),
                )
            conn.commit()
            log_activity(
                "leads_assigned",
                f"{len(lead_emails)} leads assigned to campaign",
                campaign_id=campaign_id,
            )
        finally:
            conn.close()

    @staticmethod
    def get_due_sends(campaign_id):
        """Get leads that are due for the next sequence step."""
        import pandas as pd
        from datetime import timedelta

        campaign = CampaignManager.get_campaign(campaign_id)
        if not campaign or campaign.status != "active":
            return []

        leads_df = get_leads_for_campaign(campaign_id)
        if len(leads_df) == 0:
            return []

        sent_df = load_sent()
        campaign_sent = sent_df[sent_df["campaign_id"] == campaign_id] if len(sent_df) > 0 else pd.DataFrame()

        due = []
        for _, lead in leads_df.iterrows():
            email = lead["email"]
            if lead.get("status") in ["replied", "won", "lost", "do_not_contact", "bounced"]:
                continue

            # Find what step this lead is on
            lead_sent = campaign_sent[campaign_sent["to_email"] == email] if len(campaign_sent) > 0 else pd.DataFrame()
            current_step = len(lead_sent)

            if current_step >= len(campaign.sequence):
                continue  # All steps sent

            next_step = campaign.sequence[current_step]

            # Check delay
            if current_step > 0 and len(lead_sent) > 0:
                last_sent = lead_sent.sort_values("sent_at").iloc[-1]
                try:
                    last_date = datetime.strptime(str(last_sent["sent_at"])[:19], "%Y-%m-%d %H:%M:%S")
                    due_date = last_date + timedelta(days=next_step.delay_days)
                    if datetime.now() < due_date:
                        continue
                except (ValueError, TypeError):
                    pass

            due.append({
                "lead": lead.to_dict(),
                "step": next_step,
                "step_num": current_step,
            })

        return due

    @staticmethod
    def get_stats(campaign_id):
        """Get campaign statistics."""
        stats = get_campaign_stats(campaign_id)
        campaign = CampaignManager.get_campaign(campaign_id)
        leads_df = get_leads_for_campaign(campaign_id)
        stats["total_leads"] = len(leads_df)
        stats["total_steps"] = len(campaign.sequence) if campaign else 0
        stats["reply_rate"] = (
            round(stats["replied"] / stats["sent"] * 100, 1) if stats["sent"] > 0 else 0
        )
        stats["bounce_rate"] = (
            round(stats["bounced"] / stats["sent"] * 100, 1) if stats["sent"] > 0 else 0
        )
        return stats


def build_default_sequence(template_name="SEO Audit Findings"):
    """Convert an existing template into a campaign sequence with follow-ups."""
    from outreach.templates import TEMPLATES

    tmpl = TEMPLATES.get(template_name)
    if not tmpl:
        tmpl = list(TEMPLATES.values())[0]
        template_name = list(TEMPLATES.keys())[0]

    steps = [
        SequenceStep(
            step_num=1,
            template=template_name,
            subject=tmpl["subjects"][0],
            body=tmpl["body"],
            delay_days=0,
        )
    ]

    followup_delays = [3, 7, 14]
    for i, followup_body in enumerate(tmpl.get("followups", [])):
        delay = followup_delays[i] if i < len(followup_delays) else 7
        steps.append(
            SequenceStep(
                step_num=i + 2,
                template=template_name,
                subject=f"Re: {tmpl['subjects'][0]}",
                body=followup_body,
                delay_days=delay,
            )
        )

    return steps
