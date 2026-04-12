"""Email Sender — SMTP email sending with tracking headers."""

import email.mime.multipart
import email.mime.text
import smtplib
import uuid


def send_one_email(account, to_email, subject, body, message_id=None, in_reply_to=None):
    """
    Send a single email via SMTP.
    Returns (success: bool, error: str).

    Optional:
        message_id: Custom Message-ID for reply tracking
        in_reply_to: Message-ID of original (for threading)
    """
    try:
        msg = email.mime.multipart.MIMEMultipart("alternative")
        msg["From"] = f"{account.get('name', '')} <{account['email']}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        # Custom Message-ID for reply tracking
        if not message_id:
            domain = account["email"].split("@")[1] if "@" in account["email"] else "local"
            message_id = f"<{uuid.uuid4().hex}@{domain}>"
        msg["Message-ID"] = message_id

        # Threading support
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
            msg["References"] = in_reply_to

        # List-Unsubscribe header (RFC 2369)
        msg["List-Unsubscribe"] = f"<mailto:{account['email']}?subject=unsubscribe>"

        msg.attach(email.mime.text.MIMEText(body, "plain"))

        server = smtplib.SMTP(
            account.get("smtp_server", "smtp.gmail.com"),
            account.get("smtp_port", 587),
        )
        server.starttls()
        server.login(account["email"], account["password"])
        server.send_message(msg)
        server.quit()
        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, "Wrong email/password. For Gmail: enable 2FA, create App Password at myaccount.google.com/apppasswords"
    except smtplib.SMTPRecipientsRefused:
        return False, f"Email address {to_email} was rejected"
    except Exception as e:
        return False, str(e)[:200]
