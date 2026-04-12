"""CSV database helpers — now a thin wrapper around SQLite (database_v2).

All functions delegate to database_v2 for actual storage.
CSV compatibility maintained for backward-compat imports.
"""

import os

from core.constants import LEAD_COLUMNS, SENT_COLUMNS

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(APP_DIR, "data")
LEADS_FILE = os.path.join(DATA_DIR, "leads.csv")
SENT_FILE = os.path.join(DATA_DIR, "sent_emails.csv")

os.makedirs(DATA_DIR, exist_ok=True)

# Import from SQLite backend
from core.database_v2 import (
    load_leads,
    save_leads,
    load_sent,
    save_sent,
)
