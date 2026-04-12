"""Account Manager — inbox rotation, warmup, and health tracking."""

from datetime import datetime, timedelta

from core.database_v2 import (
    load_email_accounts, save_email_account,
    get_connection, _ensure_db, log_activity,
)


class AccountManager:
    """Manage multiple email accounts with rotation, warmup, and limits."""

    def __init__(self, settings):
        self.settings = settings

    def get_next_account(self):
        """
        Round-robin account selection.
        Returns the account with the lowest sends_today that hasn't hit its limit.
        """
        accounts = self._get_all_accounts()
        if not accounts:
            return None

        today = datetime.now().strftime("%Y-%m-%d")

        eligible = []
        for acc in accounts:
            if acc.get("status") != "active":
                continue

            sends = acc.get("sends_today", 0)
            last_date = acc.get("last_send_date", "")

            # Reset counter if new day
            if last_date != today:
                sends = 0

            # Calculate effective limit (warmup mode)
            limit = self._get_effective_limit(acc)

            if sends < limit:
                eligible.append({**acc, "_sends": sends, "_limit": limit})

        if not eligible:
            return None

        # Pick account with fewest sends today (round-robin effect)
        eligible.sort(key=lambda a: a["_sends"])
        chosen = eligible[0]

        # Clean internal keys
        chosen.pop("_sends", None)
        chosen.pop("_limit", None)
        return chosen

    def _get_effective_limit(self, account):
        """Calculate effective daily limit considering warmup mode."""
        base_limit = account.get("daily_limit", 20)

        if not account.get("warmup_mode"):
            return base_limit

        warmup_start = account.get("warmup_start_date", "")
        if not warmup_start:
            return 2  # Start with 2

        try:
            start = datetime.strptime(warmup_start, "%Y-%m-%d")
            days_elapsed = (datetime.now() - start).days
            # Ramp: 2/day, +2 every 3 days
            warmup_limit = 2 + (days_elapsed // 3) * 2
            return min(warmup_limit, base_limit)
        except (ValueError, TypeError):
            return 2

    def _get_all_accounts(self):
        """Get all accounts from both settings and database."""
        db_accounts = load_email_accounts()
        settings_accounts = self.settings.get("email_accounts", [])

        # Merge: DB accounts take priority, add any settings-only accounts
        by_email = {a["email"]: a for a in db_accounts}
        for sa in settings_accounts:
            email = sa.get("email", "")
            if email and email not in by_email:
                by_email[email] = {
                    "email": email,
                    "password": sa.get("password", ""),
                    "smtp_server": sa.get("smtp_server", "smtp.gmail.com"),
                    "smtp_port": sa.get("smtp_port", 587),
                    "name": sa.get("name", ""),
                    "daily_limit": 20,
                    "sends_today": 0,
                    "last_send_date": "",
                    "warmup_mode": 0,
                    "status": "active",
                }

        return list(by_email.values())

    def get_account_health(self, email):
        """
        Get health score for an account (0-100).
        Based on bounce rate, reply rate, sending capacity.
        """
        _ensure_db()
        conn = get_connection()
        try:
            # Sent count
            sent = conn.execute(
                "SELECT COUNT(*) FROM sent_emails WHERE from_email=?", (email,)
            ).fetchone()[0]

            # Bounce count
            bounces = conn.execute(
                "SELECT COUNT(*) FROM replies WHERE to_email=? AND is_bounce=1", (email,)
            ).fetchone()[0]

            # Reply count
            replies = conn.execute(
                "SELECT COUNT(*) FROM replies WHERE to_email=? AND is_bounce=0", (email,)
            ).fetchone()[0]
        finally:
            conn.close()

        if sent == 0:
            return {"score": 100, "bounce_rate": 0, "reply_rate": 0, "sent": 0}

        bounce_rate = bounces / sent * 100
        reply_rate = replies / sent * 100

        score = 100
        if bounce_rate > 10:
            score -= 40
        elif bounce_rate > 5:
            score -= 20
        elif bounce_rate > 2:
            score -= 10

        if reply_rate > 5:
            score += 0  # Good, no penalty
        elif reply_rate < 1 and sent > 50:
            score -= 10  # Low engagement

        return {
            "score": max(0, min(100, score)),
            "bounce_rate": round(bounce_rate, 1),
            "reply_rate": round(reply_rate, 1),
            "sent": sent,
            "bounces": bounces,
            "replies": replies,
        }

    def get_all_health(self):
        """Get health data for all accounts."""
        accounts = self._get_all_accounts()
        result = []
        for acc in accounts:
            health = self.get_account_health(acc["email"])
            result.append({
                "email": acc["email"],
                "name": acc.get("name", ""),
                "daily_limit": acc.get("daily_limit", 20),
                "sends_today": acc.get("sends_today", 0),
                "warmup_mode": acc.get("warmup_mode", 0),
                "warmup_start_date": acc.get("warmup_start_date", ""),
                "status": acc.get("status", "active"),
                **health,
            })
        return result

    def start_warmup(self, email):
        """Start warmup for an account."""
        accounts = load_email_accounts()
        for acc in accounts:
            if acc["email"] == email:
                acc["warmup_mode"] = 1
                acc["warmup_start_date"] = datetime.now().strftime("%Y-%m-%d")
                save_email_account(acc)
                log_activity("warmup_started", f"Warmup started for {email}")
                return True
        return False

    def stop_warmup(self, email):
        """Stop warmup for an account."""
        accounts = load_email_accounts()
        for acc in accounts:
            if acc["email"] == email:
                acc["warmup_mode"] = 0
                save_email_account(acc)
                log_activity("warmup_stopped", f"Warmup stopped for {email}")
                return True
        return False
