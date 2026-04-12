"""SQLite database layer — replaces CSV for performance + relational data."""

import os
import sqlite3
import csv
from datetime import datetime

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(APP_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "cold_email.db")
LEADS_CSV = os.path.join(DATA_DIR, "leads.csv")
SENT_CSV = os.path.join(DATA_DIR, "sent_emails.csv")

os.makedirs(DATA_DIR, exist_ok=True)


def get_connection():
    """Get SQLite connection with WAL mode for concurrent reads."""
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    """Create all tables if they don't exist."""
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT DEFAULT '',
            website TEXT DEFAULT '',
            email TEXT DEFAULT '',
            email_source TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            niche TEXT DEFAULT '',
            location TEXT DEFAULT '',
            seo_score REAL DEFAULT 0,
            seo_issues TEXT DEFAULT '',
            lead_score REAL DEFAULT 0,
            lead_grade TEXT DEFAULT '',
            status TEXT DEFAULT 'new',
            notes TEXT DEFAULT '',
            added_date TEXT DEFAULT '',
            source TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            deal_value REAL DEFAULT 0,
            campaign_id TEXT DEFAULT '',
            email_verified TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS sent_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            to_email TEXT NOT NULL,
            business_name TEXT DEFAULT '',
            subject TEXT DEFAULT '',
            template TEXT DEFAULT '',
            followup_num INTEGER DEFAULT 0,
            from_email TEXT DEFAULT '',
            sent_at TEXT DEFAULT '',
            status TEXT DEFAULT 'sent',
            message_id TEXT DEFAULT '',
            campaign_id TEXT DEFAULT '',
            sequence_step INTEGER DEFAULT 0,
            variant TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'draft',
            template TEXT DEFAULT '',
            sequence_json TEXT DEFAULT '[]',
            account_email TEXT DEFAULT '',
            daily_limit INTEGER DEFAULT 5,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            started_at TEXT DEFAULT '',
            paused_at TEXT DEFAULT '',
            completed_at TEXT DEFAULT ''
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_email TEXT NOT NULL,
            to_email TEXT DEFAULT '',
            subject TEXT DEFAULT '',
            body TEXT DEFAULT '',
            received_at TEXT DEFAULT '',
            campaign_id TEXT DEFAULT '',
            lead_id INTEGER DEFAULT 0,
            is_bounce INTEGER DEFAULT 0,
            is_auto_reply INTEGER DEFAULT 0,
            sentiment TEXT DEFAULT '',
            processed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS unsubscribes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            reason TEXT DEFAULT '',
            unsubscribed_at TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS email_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT DEFAULT '',
            smtp_server TEXT DEFAULT 'smtp.gmail.com',
            smtp_port INTEGER DEFAULT 587,
            imap_server TEXT DEFAULT 'imap.gmail.com',
            imap_port INTEGER DEFAULT 993,
            name TEXT DEFAULT '',
            daily_limit INTEGER DEFAULT 20,
            sends_today INTEGER DEFAULT 0,
            last_send_date TEXT DEFAULT '',
            warmup_mode INTEGER DEFAULT 0,
            warmup_start_date TEXT DEFAULT '',
            warmup_daily INTEGER DEFAULT 2,
            bounce_rate REAL DEFAULT 0,
            reply_rate REAL DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            details TEXT DEFAULT '',
            lead_id INTEGER DEFAULT 0,
            campaign_id TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Indexes for common queries
    c.execute("CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_leads_campaign ON leads(campaign_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sent_to ON sent_emails(to_email)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sent_campaign ON sent_emails(campaign_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sent_message_id ON sent_emails(message_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_replies_from ON replies(from_email)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_unsubscribes_email ON unsubscribes(email)")

    conn.commit()
    conn.close()


# ─── CSV Migration ───────────────────────────────────────────

def migrate_csv_to_sqlite():
    """Auto-migrate existing CSV data into SQLite on first run."""
    conn = get_connection()
    c = conn.cursor()

    # Migrate leads.csv
    if os.path.exists(LEADS_CSV) and os.path.getsize(LEADS_CSV) > 0:
        count = c.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        if count == 0:
            try:
                with open(LEADS_CSV, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        c.execute("""
                            INSERT INTO leads (business_name, website, email, email_source,
                                phone, niche, location, seo_score, seo_issues, lead_score,
                                lead_grade, status, notes, added_date, source)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """, (
                            row.get("business_name", ""),
                            row.get("website", ""),
                            row.get("email", ""),
                            row.get("email_source", ""),
                            row.get("phone", ""),
                            row.get("niche", ""),
                            row.get("location", ""),
                            float(row.get("seo_score", 0) or 0),
                            row.get("seo_issues", ""),
                            float(row.get("lead_score", 0) or 0),
                            row.get("lead_grade", ""),
                            row.get("status", "new"),
                            row.get("notes", ""),
                            row.get("added_date", ""),
                            row.get("source", ""),
                        ))
                conn.commit()
                print(f"Migrated {c.execute('SELECT COUNT(*) FROM leads').fetchone()[0]} leads from CSV")
            except Exception as e:
                print(f"CSV migration error (leads): {e}")
                conn.rollback()

    # Migrate sent_emails.csv
    if os.path.exists(SENT_CSV) and os.path.getsize(SENT_CSV) > 0:
        count = c.execute("SELECT COUNT(*) FROM sent_emails").fetchone()[0]
        if count == 0:
            try:
                with open(SENT_CSV, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        c.execute("""
                            INSERT INTO sent_emails (to_email, business_name, subject,
                                template, followup_num, from_email, sent_at, status)
                            VALUES (?,?,?,?,?,?,?,?)
                        """, (
                            row.get("to_email", ""),
                            row.get("business_name", ""),
                            row.get("subject", ""),
                            row.get("template", ""),
                            int(row.get("followup_num", 0) or 0),
                            row.get("from_email", ""),
                            row.get("sent_at", ""),
                            row.get("status", "sent"),
                        ))
                conn.commit()
                print(f"Migrated {c.execute('SELECT COUNT(*) FROM sent_emails').fetchone()[0]} sent emails from CSV")
            except Exception as e:
                print(f"CSV migration error (sent_emails): {e}")
                conn.rollback()

    conn.close()


# ─── Pandas-compatible wrappers (drop-in replacements) ─────

def load_leads():
    """Load leads as a pandas DataFrame (drop-in CSV replacement)."""
    import pandas as pd
    _ensure_db()
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM leads ORDER BY id", conn)
        # Drop internal columns for backward compat
        for col in ["created_at", "updated_at"]:
            if col in df.columns:
                df = df.drop(columns=[col])
        return df
    except Exception:
        from core.constants import LEAD_COLUMNS
        return pd.DataFrame(columns=LEAD_COLUMNS)
    finally:
        conn.close()


def save_leads(df):
    """Save leads DataFrame to SQLite (drop-in CSV replacement)."""
    import pandas as pd
    _ensure_db()
    conn = get_connection()
    try:
        # Clear and rewrite for simplicity (same as CSV overwrite)
        conn.execute("DELETE FROM leads")
        for _, row in df.iterrows():
            conn.execute("""
                INSERT INTO leads (business_name, website, email, email_source,
                    phone, niche, location, seo_score, seo_issues, lead_score,
                    lead_grade, status, notes, added_date, source, tags,
                    deal_value, campaign_id, email_verified)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                str(row.get("business_name", "")),
                str(row.get("website", "")),
                str(row.get("email", "")),
                str(row.get("email_source", "")),
                str(row.get("phone", "")),
                str(row.get("niche", "")),
                str(row.get("location", "")),
                float(row.get("seo_score", 0) or 0),
                str(row.get("seo_issues", "")),
                float(row.get("lead_score", 0) or 0),
                str(row.get("lead_grade", "")),
                str(row.get("status", "new")),
                str(row.get("notes", "")),
                str(row.get("added_date", "")),
                str(row.get("source", "")),
                str(row.get("tags", "")),
                float(row.get("deal_value", 0) or 0),
                str(row.get("campaign_id", "")),
                str(row.get("email_verified", "")),
            ))
        conn.commit()
    finally:
        conn.close()


def load_sent():
    """Load sent emails as a pandas DataFrame (drop-in CSV replacement)."""
    import pandas as pd
    _ensure_db()
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM sent_emails ORDER BY id", conn)
        for col in ["created_at"]:
            if col in df.columns:
                df = df.drop(columns=[col])
        return df
    except Exception:
        from core.constants import SENT_COLUMNS
        return pd.DataFrame(columns=SENT_COLUMNS)
    finally:
        conn.close()


def save_sent(df):
    """Save sent emails DataFrame to SQLite (drop-in CSV replacement)."""
    import pandas as pd
    _ensure_db()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM sent_emails")
        for _, row in df.iterrows():
            conn.execute("""
                INSERT INTO sent_emails (to_email, business_name, subject,
                    template, followup_num, from_email, sent_at, status,
                    message_id, campaign_id, sequence_step, variant)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                str(row.get("to_email", "")),
                str(row.get("business_name", "")),
                str(row.get("subject", "")),
                str(row.get("template", "")),
                int(row.get("followup_num", 0) or 0),
                str(row.get("from_email", "")),
                str(row.get("sent_at", "")),
                str(row.get("status", "sent")),
                str(row.get("message_id", "")),
                str(row.get("campaign_id", "")),
                int(row.get("sequence_step", 0) or 0),
                str(row.get("variant", "")),
            ))
        conn.commit()
    finally:
        conn.close()


# ─── Campaign functions ───────────────────────────────────────

def load_campaigns():
    """Load all campaigns as list of dicts."""
    _ensure_db()
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM campaigns ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_campaign(campaign):
    """Insert or update a campaign."""
    _ensure_db()
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO campaigns
                (id, name, status, template, sequence_json, account_email,
                 daily_limit, created_at, updated_at, started_at, paused_at, completed_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            campaign["id"],
            campaign.get("name", ""),
            campaign.get("status", "draft"),
            campaign.get("template", ""),
            campaign.get("sequence_json", "[]"),
            campaign.get("account_email", ""),
            campaign.get("daily_limit", 5),
            campaign.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            campaign.get("started_at", ""),
            campaign.get("paused_at", ""),
            campaign.get("completed_at", ""),
        ))
        conn.commit()
    finally:
        conn.close()


def load_replies():
    """Load all replies as list of dicts."""
    _ensure_db()
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM replies ORDER BY received_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_reply(reply):
    """Insert a reply record."""
    _ensure_db()
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO replies (from_email, to_email, subject, body,
                received_at, campaign_id, lead_id, is_bounce, is_auto_reply,
                sentiment, processed)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            reply.get("from_email", ""),
            reply.get("to_email", ""),
            reply.get("subject", ""),
            reply.get("body", ""),
            reply.get("received_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            reply.get("campaign_id", ""),
            reply.get("lead_id", 0),
            reply.get("is_bounce", 0),
            reply.get("is_auto_reply", 0),
            reply.get("sentiment", ""),
            reply.get("processed", 0),
        ))
        conn.commit()
    finally:
        conn.close()


def load_unsubscribes():
    """Load all unsubscribed emails."""
    _ensure_db()
    conn = get_connection()
    try:
        rows = conn.execute("SELECT email FROM unsubscribes").fetchall()
        return [r["email"] for r in rows]
    finally:
        conn.close()


def add_unsubscribe(email, reason=""):
    """Add email to unsubscribe list."""
    _ensure_db()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO unsubscribes (email, reason) VALUES (?, ?)",
            (email, reason),
        )
        conn.commit()
    finally:
        conn.close()


def load_email_accounts():
    """Load all email accounts as list of dicts."""
    _ensure_db()
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM email_accounts ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_email_account(account):
    """Insert or update an email account."""
    _ensure_db()
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO email_accounts
                (email, password, smtp_server, smtp_port, imap_server, imap_port,
                 name, daily_limit, sends_today, last_send_date,
                 warmup_mode, warmup_start_date, warmup_daily,
                 bounce_rate, reply_rate, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            account["email"],
            account.get("password", ""),
            account.get("smtp_server", "smtp.gmail.com"),
            account.get("smtp_port", 587),
            account.get("imap_server", "imap.gmail.com"),
            account.get("imap_port", 993),
            account.get("name", ""),
            account.get("daily_limit", 20),
            account.get("sends_today", 0),
            account.get("last_send_date", ""),
            account.get("warmup_mode", 0),
            account.get("warmup_start_date", ""),
            account.get("warmup_daily", 2),
            account.get("bounce_rate", 0),
            account.get("reply_rate", 0),
            account.get("status", "active"),
        ))
        conn.commit()
    finally:
        conn.close()


def log_activity(action, details="", lead_id=0, campaign_id=""):
    """Log an activity event."""
    _ensure_db()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO activity_log (action, details, lead_id, campaign_id) VALUES (?,?,?,?)",
            (action, details, lead_id, campaign_id),
        )
        conn.commit()
    finally:
        conn.close()


def load_activity_log(limit=100):
    """Load recent activity log entries."""
    _ensure_db()
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_campaign_stats(campaign_id):
    """Get stats for a campaign: sent, replied, bounced counts."""
    _ensure_db()
    conn = get_connection()
    try:
        sent = conn.execute(
            "SELECT COUNT(*) FROM sent_emails WHERE campaign_id=? AND status='sent'",
            (campaign_id,),
        ).fetchone()[0]
        replied = conn.execute(
            "SELECT COUNT(*) FROM replies WHERE campaign_id=? AND is_bounce=0",
            (campaign_id,),
        ).fetchone()[0]
        bounced = conn.execute(
            "SELECT COUNT(*) FROM replies WHERE campaign_id=? AND is_bounce=1",
            (campaign_id,),
        ).fetchone()[0]
        return {"sent": sent, "replied": replied, "bounced": bounced}
    finally:
        conn.close()


def get_leads_for_campaign(campaign_id):
    """Get all leads assigned to a campaign."""
    import pandas as pd
    _ensure_db()
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM leads WHERE campaign_id=?", conn, params=(campaign_id,)
        )
        return df
    finally:
        conn.close()


def update_lead_status(email, status):
    """Update a lead's status by email."""
    _ensure_db()
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE leads SET status=?, updated_at=datetime('now') WHERE email=?",
            (status, email),
        )
        conn.commit()
    finally:
        conn.close()


def increment_account_sends(email):
    """Increment sends_today for an account."""
    _ensure_db()
    conn = get_connection()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        # Reset counter if new day
        conn.execute("""
            UPDATE email_accounts
            SET sends_today = CASE
                WHEN last_send_date != ? THEN 1
                ELSE sends_today + 1
            END,
            last_send_date = ?
            WHERE email = ?
        """, (today, today, email))
        conn.commit()
    finally:
        conn.close()


# ─── Initialization ─────────────────────────────────────────

_db_initialized = False

def _ensure_db():
    """Ensure database is initialized (called once)."""
    global _db_initialized
    if not _db_initialized:
        init_database()
        migrate_csv_to_sqlite()
        _db_initialized = True
