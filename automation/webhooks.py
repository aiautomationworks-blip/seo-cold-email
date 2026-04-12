"""Webhook Notifications — Discord/Slack alerts for replies, bounces, summaries."""

import json
from datetime import datetime

import requests


def send_discord(webhook_url, message, embed=None):
    """Send a message to Discord webhook."""
    if not webhook_url:
        return False
    try:
        payload = {"content": message}
        if embed:
            payload["embeds"] = [embed]
        resp = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        return resp.status_code in (200, 204)
    except Exception:
        return False


def send_slack(webhook_url, message, blocks=None):
    """Send a message to Slack webhook."""
    if not webhook_url:
        return False
    try:
        payload = {"text": message}
        if blocks:
            payload["blocks"] = blocks
        resp = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


def notify_reply(settings, from_email, subject, sentiment=""):
    """Send notification about a new reply."""
    discord_url = settings.get("discord_webhook", "")
    slack_url = settings.get("slack_webhook", "")

    sentiment_text = f" ({sentiment})" if sentiment else ""
    message = f"New reply from **{from_email}**{sentiment_text}\nSubject: {subject}"

    if discord_url:
        embed = {
            "title": "New Reply Received",
            "description": message,
            "color": 5025616,  # Green
            "timestamp": datetime.utcnow().isoformat(),
        }
        send_discord(discord_url, "", embed)

    if slack_url:
        send_slack(slack_url, f":email: {message}")


def notify_bounce(settings, email):
    """Send notification about a bounce."""
    discord_url = settings.get("discord_webhook", "")
    slack_url = settings.get("slack_webhook", "")

    message = f"Bounce detected: {email}"

    if discord_url:
        embed = {
            "title": "Bounce Alert",
            "description": message,
            "color": 15158332,  # Red
            "timestamp": datetime.utcnow().isoformat(),
        }
        send_discord(discord_url, "", embed)

    if slack_url:
        send_slack(slack_url, f":warning: {message}")


def send_daily_summary(settings):
    """Send daily summary of outreach activity."""
    discord_url = settings.get("discord_webhook", "")
    slack_url = settings.get("slack_webhook", "")

    if not discord_url and not slack_url:
        return

    try:
        from core.database_v2 import load_activity_log, load_replies
        from core.database import load_leads, load_sent

        leads_df = load_leads()
        sent_df = load_sent()
        replies = load_replies()

        # Today's activity
        today = datetime.now().strftime("%Y-%m-%d")
        log = load_activity_log(limit=50)
        today_actions = [a for a in log if a.get("created_at", "").startswith(today)]

        today_sent = len([a for a in today_actions if a.get("action") == "email_sent"])
        today_replies = len([a for a in today_actions if a.get("action") == "reply_received"])
        today_bounces = len([a for a in today_actions if a.get("action") == "bounce_detected"])
        today_leads = len([a for a in today_actions if a.get("action") in ("lead_found", "campaign_created")])

        summary = (
            f"**Daily Outreach Summary — {today}**\n"
            f"- Emails sent: {today_sent}\n"
            f"- Replies: {today_replies}\n"
            f"- Bounces: {today_bounces}\n"
            f"- New leads: {today_leads}\n"
            f"- Total leads: {len(leads_df)}\n"
            f"- Total sent: {len(sent_df)}\n"
            f"- Total replies: {len(replies)}"
        )

        if discord_url:
            embed = {
                "title": f"Daily Summary — {today}",
                "description": summary.replace("**", ""),
                "color": 3447003,  # Blue
                "timestamp": datetime.utcnow().isoformat(),
            }
            send_discord(discord_url, "", embed)

        if slack_url:
            send_slack(slack_url, summary.replace("**", "*"))

        print(f"  Daily summary sent")

    except Exception as e:
        print(f"  Summary notification error: {e}")
