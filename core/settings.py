"""Settings management — load/save JSON settings, secrets via st.secrets."""

import json
import os

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(APP_DIR, "data")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

os.makedirs(DATA_DIR, exist_ok=True)

DEFAULTS = {
    "your_name": "",
    "your_company": "",
    "your_phone": "",
    "your_website": "",
    "your_calendly": "",
    "email_accounts": [],
    "target_niches": ["dentist", "plastic surgeon", "real estate agent", "med spa"],
    "target_locations": ["Hyderabad", "Mumbai", "Bangalore", "Delhi"],
    "daily_limit": 5,
    "delay_min": 45,
    "delay_max": 120,
    "followup_days": [3, 7, 14],
    "autopilot_enabled": False,
    "autopilot_niches": [],
    "autopilot_locations": [],
    "autopilot_template": "SEO Audit Findings",
    "autopilot_max_emails": 5,
    "autopilot_max_leads": 10,
    "selected_scrapers": ["DuckDuckGo"],
}


def load_settings():
    """Load settings from JSON file, filling in defaults."""
    settings = dict(DEFAULTS)
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                saved = json.load(f)
                settings.update(saved)
        except Exception:
            pass
    return settings


def save_settings(settings):
    """Save settings to JSON file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def get_setting(key, default=None):
    """Get a single setting value."""
    settings = load_settings()
    return settings.get(key, default)
