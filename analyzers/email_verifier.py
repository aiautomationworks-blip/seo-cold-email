"""Email Verifier — MX lookup + SMTP handshake verification."""

import re
import socket
import smtplib

try:
    import dns.resolver
    HAS_DNS = True
except ImportError:
    HAS_DNS = False


def verify_email(email_address):
    """
    Verify a single email address.

    Returns dict:
        {
            "email": str,
            "is_valid": bool,
            "risk": "valid" | "risky" | "invalid",
            "reason": str,
            "mx_found": bool,
            "smtp_check": bool,
            "is_catchall": bool,
        }
    """
    result = {
        "email": email_address,
        "is_valid": False,
        "risk": "invalid",
        "reason": "",
        "mx_found": False,
        "smtp_check": False,
        "is_catchall": False,
    }

    # Step 1: Format validation
    if not email_address or not re.match(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email_address
    ):
        result["reason"] = "Invalid email format"
        return result

    domain = email_address.split("@")[1]

    # Step 2: Check for disposable/free domains
    disposable_domains = {
        "mailinator.com", "guerrillamail.com", "tempmail.com",
        "throwaway.email", "yopmail.com", "trashmail.com",
    }
    if domain.lower() in disposable_domains:
        result["reason"] = "Disposable email domain"
        result["risk"] = "invalid"
        return result

    # Step 3: MX Record lookup
    if not HAS_DNS:
        result["reason"] = "dnspython not installed — MX lookup skipped"
        result["risk"] = "risky"
        result["is_valid"] = True
        return result

    mx_hosts = _get_mx_records(domain)
    if not mx_hosts:
        result["reason"] = f"No MX records found for {domain}"
        return result

    result["mx_found"] = True

    # Step 4: SMTP handshake verification
    smtp_result = _smtp_check(email_address, mx_hosts[0])
    result["smtp_check"] = smtp_result["valid"]
    result["is_catchall"] = smtp_result.get("catchall", False)

    if smtp_result["valid"]:
        if smtp_result.get("catchall"):
            result["is_valid"] = True
            result["risk"] = "risky"
            result["reason"] = "Catch-all domain (accepts all addresses)"
        else:
            result["is_valid"] = True
            result["risk"] = "valid"
            result["reason"] = "Email address verified"
    else:
        result["reason"] = smtp_result.get("error", "SMTP verification failed")
        result["risk"] = "invalid"

    return result


def _get_mx_records(domain):
    """Lookup MX records for a domain."""
    try:
        answers = dns.resolver.resolve(domain, "MX")
        mx_hosts = sorted(
            [(r.preference, str(r.exchange).rstrip(".")) for r in answers]
        )
        return [h for _, h in mx_hosts]
    except Exception:
        return []


def _smtp_check(email_address, mx_host):
    """Perform SMTP RCPT TO check against MX server."""
    result = {"valid": False, "catchall": False, "error": ""}
    try:
        sock = socket.create_connection((mx_host, 25), timeout=10)
        server = smtplib.SMTP()
        server.sock = sock
        server.ehlo_or_helo_if_needed()

        # MAIL FROM with empty sender
        code, _ = server.mail("")
        if code != 250:
            result["error"] = "MAIL FROM rejected"
            server.quit()
            return result

        # RCPT TO with the actual email
        code, msg = server.rcpt(email_address)
        if code == 250:
            result["valid"] = True
        elif code == 550:
            result["error"] = "Mailbox does not exist"
            server.quit()
            return result
        else:
            result["error"] = f"RCPT returned {code}"
            result["valid"] = True  # Some servers return unusual codes but still deliver
            result["catchall"] = True

        # Catch-all detection: test a random address
        import uuid
        random_email = f"{uuid.uuid4().hex[:12]}@{email_address.split('@')[1]}"
        code2, _ = server.rcpt(random_email)
        if code2 == 250:
            result["catchall"] = True

        server.quit()
    except socket.timeout:
        result["error"] = "Connection timeout"
        result["valid"] = True  # Can't verify but MX exists
        result["catchall"] = True
    except Exception as e:
        result["error"] = str(e)[:100]
        # If MX exists, assume risky but possible
        result["valid"] = True
        result["catchall"] = True

    return result


def verify_lead_emails(leads, max_count=50):
    """
    Batch verify emails from a list of lead dicts.

    Args:
        leads: list of dicts with 'email' key
        max_count: max emails to verify in one batch

    Returns:
        list of verification results
    """
    results = []
    seen = set()
    for lead in leads[:max_count]:
        email = lead.get("email", "")
        if not email or email in seen:
            continue
        seen.add(email)
        result = verify_email(email)
        result["business_name"] = lead.get("business_name", "")
        results.append(result)
    return results


def get_risk_color(risk):
    """Return color for risk level display."""
    return {"valid": "green", "risky": "orange", "invalid": "red"}.get(risk, "gray")


def get_risk_emoji(risk):
    """Return emoji for risk level."""
    return {"valid": "OK", "risky": "?", "invalid": "X"}.get(risk, "-")
