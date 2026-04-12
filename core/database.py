"""CSV database helpers — load/save leads and sent emails."""

import os

import pandas as pd

from core.constants import LEAD_COLUMNS, SENT_COLUMNS

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(APP_DIR, "data")
LEADS_FILE = os.path.join(DATA_DIR, "leads.csv")
SENT_FILE = os.path.join(DATA_DIR, "sent_emails.csv")

os.makedirs(DATA_DIR, exist_ok=True)


def load_leads():
    """Load leads CSV into a DataFrame."""
    if os.path.exists(LEADS_FILE) and os.path.getsize(LEADS_FILE) > 0:
        try:
            df = pd.read_csv(LEADS_FILE)
            for col in LEAD_COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            return df
        except Exception:
            return pd.DataFrame(columns=LEAD_COLUMNS)
    return pd.DataFrame(columns=LEAD_COLUMNS)


def save_leads(df):
    """Save leads DataFrame to CSV."""
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(LEADS_FILE, index=False)


def load_sent():
    """Load sent emails CSV into a DataFrame."""
    if os.path.exists(SENT_FILE) and os.path.getsize(SENT_FILE) > 0:
        try:
            return pd.read_csv(SENT_FILE)
        except Exception:
            return pd.DataFrame(columns=SENT_COLUMNS)
    return pd.DataFrame(columns=SENT_COLUMNS)


def save_sent(df):
    """Save sent emails DataFrame to CSV."""
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(SENT_FILE, index=False)
