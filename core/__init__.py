"""Core module — settings, database helpers, constants, campaigns, compliance."""
from core.settings import load_settings, save_settings, get_setting
from core.database import load_leads, save_leads, load_sent, save_sent, LEADS_FILE, SENT_FILE
from core.constants import (
    LEAD_COLUMNS, SENT_COLUMNS, LEAD_STATUSES, NICHE_PROFILES,
    SCORING_WEIGHTS, USER_AGENTS, SKIP_DOMAINS,
    SENT_COLUMNS_V2, CAMPAIGN_STATUSES, PIPELINE_STAGES,
)
