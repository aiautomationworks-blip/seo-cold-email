"""
Email Finder - Find and verify email addresses for leads.
Uses free methods: website scraping, pattern guessing, SMTP verification.
"""

import csv
import dns.resolver
import re
import smtplib
import socket
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

from config import LEADS_CSV


# Common email patterns sorted by likelihood
EMAIL_PATTERNS = [
    "{first}@{domain}",
    "{first}.{last}@{domain}",
    "{first}{last}@{domain}",
    "info@{domain}",
    "contact@{domain}",
    "hello@{domain}",
    "admin@{domain}",
    "office@{domain}",
    "sales@{domain}",
    "support@{domain}",
]

# Common first names for business owners (used as fallback)
GENERIC_PREFIXES = ["info", "contact", "hello", "admin", "office", "sales", "team"]


def extract_domain(website_url):
    """Extract clean domain from URL."""
    parsed = urllib.parse.urlparse(website_url)
    domain = parsed.netloc or parsed.path
    domain = domain.replace("www.", "")
    return domain


def check_mx_record(domain):
    """Check if domain has MX records (can receive email)."""
    try:
        mx_records = dns.resolver.resolve(domain, "MX")
        return len(mx_records) > 0
    except Exception:
        return False


def verify_email_smtp(email, timeout=10):
    """
    Verify if an email exists using SMTP RCPT TO.
    Note: Many servers block this, so treat as a soft signal.
    Returns: True (exists), False (rejected), None (can't determine)
    """
    domain = email.split("@")[1]

    try:
        # Get MX record
        mx_records = dns.resolver.resolve(domain, "MX")
        mx_host = str(mx_records[0].exchange).rstrip(".")
    except Exception:
        return None

    try:
        server = smtplib.SMTP(timeout=timeout)
        server.connect(mx_host)
        server.helo("verify.check")
        server.mail("verify@check.com")
        code, _ = server.rcpt(email)
        server.quit()

        if code == 250:
            return True
        elif code == 550:
            return False
        return None
    except Exception:
        return None


def scrape_emails_from_url(url, session=None):
    """Scrape all email addresses from a URL."""
    if session is None:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })

    emails = set()
    try:
        resp = session.get(url, timeout=10)
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        found = re.findall(email_pattern, resp.text)

        # Filter junk
        skip = ["example.com", "sentry", "wixpress", "wordpress", "w3.org", ".png", ".jpg", ".gif"]
        for email in found:
            if not any(s in email.lower() for s in skip):
                emails.add(email.lower())
    except Exception:
        pass

    return list(emails)


def find_emails_for_website(website_url, session=None):
    """
    Comprehensive email finding for a single website.
    Tries multiple pages and methods.
    """
    if session is None:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })

    domain = extract_domain(website_url)
    all_emails = set()

    # 1. Scrape main page
    found = scrape_emails_from_url(website_url, session)
    all_emails.update(found)

    # 2. Try common contact page URLs
    contact_paths = [
        "/contact", "/contact-us", "/about", "/about-us",
        "/team", "/our-team", "/get-in-touch",
    ]

    base_url = f"https://{domain}" if not website_url.startswith("http") else website_url.rstrip("/")

    for path in contact_paths:
        try:
            url = f"{base_url}{path}"
            found = scrape_emails_from_url(url, session)
            all_emails.update(found)
            if all_emails:
                break  # Found emails, stop looking
            time.sleep(0.5)
        except Exception:
            continue

    # 3. If still no emails, try to find contact page links
    if not all_emails:
        try:
            resp = session.get(website_url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            for link in soup.find_all("a", href=True):
                href = link.get("href", "").lower()
                text = link.get_text("").lower()
                if any(kw in href or kw in text for kw in ["contact", "about", "team"]):
                    full_url = urllib.parse.urljoin(website_url, link["href"])
                    found = scrape_emails_from_url(full_url, session)
                    all_emails.update(found)
                    if all_emails:
                        break
        except Exception:
            pass

    # 4. Filter to same-domain emails (prefer these)
    same_domain = [e for e in all_emails if domain in e]
    other_domain = [e for e in all_emails if domain not in e]

    if same_domain:
        return same_domain
    elif other_domain:
        return other_domain

    # 5. If nothing found, generate guesses
    guesses = [f"{prefix}@{domain}" for prefix in GENERIC_PREFIXES[:3]]
    return guesses


def enrich_leads_with_emails(leads_csv=None):
    """
    Read leads CSV, find emails for those missing them, update CSV.
    """
    leads_csv = leads_csv or LEADS_CSV

    if not csv_exists(leads_csv):
        print(f"No leads file found at {leads_csv}")
        return

    # Read all leads
    leads = []
    with open(leads_csv, "r") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            leads.append(row)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })

    updated = 0
    for i, lead in enumerate(leads):
        email = lead.get("email", "").strip()
        website = lead.get("website", "").strip()
        is_guessed = lead.get("email_guessed", "").lower() == "true"

        # Skip if we have a real (non-guessed) email
        if email and not is_guessed:
            continue

        if not website:
            continue

        print(f"[{i+1}/{len(leads)}] Finding email for: {website}")
        found_emails = find_emails_for_website(website, session)

        if found_emails:
            lead["email"] = found_emails[0]
            lead["email_guessed"] = "False" if "@" in found_emails[0] else "True"
            updated += 1
            print(f"  Found: {found_emails[0]}")
        else:
            print(f"  No email found")

        time.sleep(1)

    # Write back
    if "email_guessed" not in fieldnames:
        fieldnames.append("email_guessed")

    with open(leads_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(leads)

    print(f"\nUpdated {updated} leads with new emails")


def csv_exists(path):
    """Check if CSV file exists and has content."""
    import os
    return os.path.exists(path) and os.path.getsize(path) > 0


def verify_lead_emails(leads_csv=None, max_workers=5):
    """
    Verify emails in the leads CSV using MX record checks.
    Marks emails as verified/unverified.
    """
    leads_csv = leads_csv or LEADS_CSV

    if not csv_exists(leads_csv):
        print(f"No leads file found at {leads_csv}")
        return

    leads = []
    with open(leads_csv, "r") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        for row in reader:
            leads.append(row)

    if "email_verified" not in fieldnames:
        fieldnames.append("email_verified")

    verified_count = 0
    for lead in leads:
        email = lead.get("email", "")
        if not email or "@" not in email:
            lead["email_verified"] = "No"
            continue

        domain = email.split("@")[1]
        has_mx = check_mx_record(domain)
        lead["email_verified"] = "Yes" if has_mx else "No"
        if has_mx:
            verified_count += 1
        print(f"  {'OK' if has_mx else 'FAIL'} - {email}")

    with open(leads_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(leads)

    print(f"\n{verified_count}/{len(leads)} emails have valid MX records")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        verify_lead_emails()
    else:
        enrich_leads_with_emails()
