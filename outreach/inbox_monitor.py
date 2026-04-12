"""Inbox Monitor — IMAP reply & bounce detection for Gmail."""

import email
import imaplib
import re
from datetime import datetime, timedelta
from email.header import decode_header

from core.database_v2 import (
    save_reply, update_lead_status, load_sent,
    log_activity, load_unsubscribes, add_unsubscribe,
)


class InboxMonitor:
    """Monitor Gmail inbox for replies and bounces via IMAP."""

    BOUNCE_SENDERS = {"mailer-daemon", "postmaster", "mail-daemon"}
    UNSUBSCRIBE_KEYWORDS = {"unsubscribe", "stop", "remove me", "opt out", "opt-out", "no more"}

    def __init__(self, account):
        """
        Args:
            account: dict with email, password, imap_server, imap_port
        """
        self.account = account
        self.email_addr = account["email"]
        self.password = account["password"]
        self.imap_server = account.get("imap_server", "imap.gmail.com")
        self.imap_port = account.get("imap_port", 993)
        self.connection = None

    def connect(self):
        """Connect to IMAP server."""
        try:
            self.connection = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self.connection.login(self.email_addr, self.password)
            return True, ""
        except imaplib.IMAP4.error as e:
            return False, f"IMAP login failed: {str(e)[:100]}"
        except Exception as e:
            return False, f"Connection error: {str(e)[:100]}"

    def disconnect(self):
        """Close IMAP connection."""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except Exception:
                pass

    def check_replies(self, since_days=7):
        """
        Check inbox for replies to our sent emails.
        Returns list of reply dicts.
        """
        if not self.connection:
            ok, err = self.connect()
            if not ok:
                return [], err

        replies = []
        try:
            self.connection.select("INBOX")

            # Search for recent emails
            since_date = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
            _, message_ids = self.connection.search(None, f'(SINCE "{since_date}")')

            if not message_ids[0]:
                return [], ""

            # Load our sent emails for matching
            sent_df = load_sent()
            sent_emails = set()
            sent_subjects = {}
            sent_message_ids = {}

            if len(sent_df) > 0:
                sent_emails = set(sent_df["to_email"].tolist())
                for _, row in sent_df.iterrows():
                    to = str(row.get("to_email", ""))
                    subj = str(row.get("subject", ""))
                    msg_id = str(row.get("message_id", ""))
                    if to:
                        sent_subjects[to] = subj
                    if msg_id:
                        sent_message_ids[msg_id] = {
                            "to_email": to,
                            "campaign_id": str(row.get("campaign_id", "")),
                        }

            # Process each message
            for msg_id in message_ids[0].split():
                try:
                    _, msg_data = self.connection.fetch(msg_id, "(RFC822)")
                    raw = msg_data[0][1]
                    msg = email.message_from_bytes(raw)

                    from_addr = self._extract_email(msg.get("From", ""))
                    subject = self._decode_subject(msg.get("Subject", ""))
                    in_reply_to = msg.get("In-Reply-To", "")
                    date_str = msg.get("Date", "")

                    # Skip our own sent emails
                    if from_addr == self.email_addr:
                        continue

                    # Match by In-Reply-To header
                    matched = False
                    campaign_id = ""
                    if in_reply_to and in_reply_to in sent_message_ids:
                        matched = True
                        campaign_id = sent_message_ids[in_reply_to].get("campaign_id", "")

                    # Match by sender email (they're replying to us)
                    if not matched and from_addr in sent_emails:
                        # Check subject similarity
                        original_subject = sent_subjects.get(from_addr, "")
                        if self._subjects_match(subject, original_subject):
                            matched = True

                    if not matched:
                        continue

                    # Extract body
                    body = self._extract_body(msg)

                    # Determine type
                    is_bounce = self._is_bounce(from_addr, subject, body)
                    is_auto = self._is_auto_reply(subject, body)

                    # Parse date
                    try:
                        received_at = email.utils.parsedate_to_datetime(date_str).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        received_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    reply_data = {
                        "from_email": from_addr,
                        "to_email": self.email_addr,
                        "subject": subject,
                        "body": body[:2000],
                        "received_at": received_at,
                        "campaign_id": campaign_id,
                        "is_bounce": 1 if is_bounce else 0,
                        "is_auto_reply": 1 if is_auto else 0,
                        "sentiment": self._detect_sentiment(body),
                        "processed": 0,
                    }

                    replies.append(reply_data)

                except Exception:
                    continue

        except Exception as e:
            return replies, f"Error checking inbox: {str(e)[:100]}"

        return replies, ""

    def check_bounces(self, since_days=7):
        """Check for bounce/MAILER-DAEMON messages."""
        if not self.connection:
            ok, err = self.connect()
            if not ok:
                return [], err

        bounces = []
        try:
            self.connection.select("INBOX")
            since_date = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")

            for sender in self.BOUNCE_SENDERS:
                _, ids = self.connection.search(None, f'(FROM "{sender}" SINCE "{since_date}")')
                if not ids[0]:
                    continue

                for msg_id in ids[0].split():
                    try:
                        _, msg_data = self.connection.fetch(msg_id, "(RFC822)")
                        raw = msg_data[0][1]
                        msg = email.message_from_bytes(raw)

                        body = self._extract_body(msg)
                        bounced_email = self._extract_bounced_email(body)

                        if bounced_email:
                            bounces.append({
                                "from_email": bounced_email,
                                "to_email": self.email_addr,
                                "subject": self._decode_subject(msg.get("Subject", "")),
                                "body": body[:1000],
                                "received_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "is_bounce": 1,
                                "is_auto_reply": 0,
                                "sentiment": "",
                                "processed": 0,
                            })
                    except Exception:
                        continue

        except Exception as e:
            return bounces, str(e)[:100]

        return bounces, ""

    def process_replies(self, replies):
        """Save replies and update lead statuses."""
        new_count = 0
        bounce_count = 0

        for reply in replies:
            # Save reply
            save_reply(reply)

            from_email = reply["from_email"]

            if reply.get("is_bounce"):
                update_lead_status(from_email, "bounced")
                bounce_count += 1
                log_activity("bounce_detected", f"Bounce from {from_email}")
            else:
                # Check for unsubscribe intent
                body_lower = reply.get("body", "").lower()
                if any(kw in body_lower for kw in self.UNSUBSCRIBE_KEYWORDS):
                    add_unsubscribe(from_email, "reply_keyword")
                    update_lead_status(from_email, "do_not_contact")
                    log_activity("unsubscribe_detected", f"{from_email} unsubscribed via reply")
                else:
                    update_lead_status(from_email, "replied")
                    new_count += 1
                    log_activity("reply_received", f"Reply from {from_email}")

        return new_count, bounce_count

    # ─── Helper Methods ─────────────────────────────────────

    def _extract_email(self, from_header):
        """Extract email address from From header."""
        match = re.search(r'<([^>]+)>', from_header)
        if match:
            return match.group(1).lower()
        match = re.search(r'[\w.+-]+@[\w.-]+\.\w+', from_header)
        if match:
            return match.group(0).lower()
        return from_header.lower().strip()

    def _decode_subject(self, subject):
        """Decode email subject."""
        try:
            decoded = decode_header(subject)
            parts = []
            for text, charset in decoded:
                if isinstance(text, bytes):
                    parts.append(text.decode(charset or "utf-8", errors="ignore"))
                else:
                    parts.append(text)
            return " ".join(parts)
        except Exception:
            return str(subject)

    def _subjects_match(self, reply_subject, original_subject):
        """Check if reply subject matches original (Re: prefix handling)."""
        clean_reply = re.sub(r'^(Re:\s*|Fwd:\s*)+', '', reply_subject, flags=re.IGNORECASE).strip().lower()
        clean_original = re.sub(r'^(Re:\s*|Fwd:\s*)+', '', original_subject, flags=re.IGNORECASE).strip().lower()
        return clean_reply == clean_original or clean_original in clean_reply

    def _extract_body(self, msg):
        """Extract plain text body from email message."""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
                    except Exception:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
            except Exception:
                body = str(msg.get_payload())
        return body.strip()

    def _is_bounce(self, from_addr, subject, body):
        """Detect if message is a bounce notification."""
        from_lower = from_addr.lower()
        if any(s in from_lower for s in self.BOUNCE_SENDERS):
            return True
        bounce_indicators = [
            "delivery failed", "undeliverable", "mail delivery failed",
            "delivery status notification", "returned mail",
            "message not delivered", "550 ", "553 ", "mailbox not found",
        ]
        combined = f"{subject} {body}".lower()
        return any(ind in combined for ind in bounce_indicators)

    def _is_auto_reply(self, subject, body):
        """Detect auto-replies / out-of-office."""
        indicators = [
            "out of office", "automatic reply", "auto-reply",
            "autoreply", "on vacation", "currently away",
            "will be out", "limited access to email",
        ]
        combined = f"{subject} {body}".lower()
        return any(ind in combined for ind in indicators)

    def _extract_bounced_email(self, body):
        """Extract the bounced recipient email from bounce message body."""
        patterns = [
            r'(?:failed|rejected|undeliverable).*?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'<([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})>',
        ]
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                email_addr = match.group(1).lower()
                if email_addr != self.email_addr:
                    return email_addr
        return ""

    def _detect_sentiment(self, body):
        """Simple keyword-based sentiment detection."""
        body_lower = body.lower()
        positive = ["interested", "yes", "sounds good", "let's talk", "schedule",
                     "book", "sure", "great", "tell me more", "send me"]
        negative = ["not interested", "no thanks", "no thank you", "remove",
                     "unsubscribe", "stop", "spam", "don't contact"]

        neg_count = sum(1 for w in negative if w in body_lower)
        pos_count = sum(1 for w in positive if w in body_lower)

        if neg_count > pos_count:
            return "negative"
        if pos_count > 0:
            return "positive"
        return "neutral"


def check_campaign_bounce_rate(campaign_id, threshold=5.0):
    """
    Check if a campaign's bounce rate exceeds threshold.
    Returns (should_pause, bounce_rate).
    """
    from core.database_v2 import get_campaign_stats
    stats = get_campaign_stats(campaign_id)
    if stats["sent"] == 0:
        return False, 0.0
    rate = stats["bounced"] / stats["sent"] * 100
    return rate > threshold, rate
