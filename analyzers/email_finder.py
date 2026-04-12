"""Email Finder — find and extract email addresses from websites."""

import random
import re
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup

from core.constants import USER_AGENTS

SKIP_EMAILS = [
    "example.com", "sentry", "wixpress", "wordpress",
    "w3.org", ".png", ".jpg", ".gif", ".svg",
]

GENERIC_PREFIXES = ["info", "contact", "hello", "admin", "office"]


def analyze_website(website_url):
    """
    Visit a business website and extract contact info + basic SEO issues.
    Used during lead discovery for quick enrichment.
    Returns dict with email, phone, business_name, seo_score, seo_issues.
    """
    info = {
        "email": "", "phone": "", "business_name": "",
        "seo_score": 100, "seo_issues": [],
    }

    try:
        session = requests.Session()
        session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
        resp = session.get(website_url, timeout=10, allow_redirects=True)
        if resp.status_code != 200:
            return info

        soup = BeautifulSoup(resp.text, "html.parser")

        # Business name from title
        title = soup.find("title")
        if title:
            info["business_name"] = title.text.strip().split("|")[0].split("-")[0].strip()[:60]

        # Find emails
        email_pat = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        found = [e for e in re.findall(email_pat, resp.text)
                 if not any(s in e.lower() for s in SKIP_EMAILS)]
        if found:
            info["email"] = found[0]

        # Find phone (Indian + international)
        for pat in [r'\+91[\s-]?\d{5}[\s-]?\d{5}', r'\+91[\s-]?\d{10}',
                    r'0\d{2,4}[\s-]?\d{6,8}',
                    r'[\(]?\d{3}[\)]?[-.\s]?\d{3}[-.\s]?\d{4}', r'\d{10}']:
            phones = re.findall(pat, resp.text)
            if phones:
                info["phone"] = phones[0]
                break

        # Quick SEO checks
        html_lower = resp.text.lower()
        if not resp.url.startswith("https"):
            info["seo_issues"].append("No SSL/HTTPS")
            info["seo_score"] -= 15
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if not meta_desc or not meta_desc.get("content", "").strip():
            info["seo_issues"].append("Missing meta description")
            info["seo_score"] -= 12
        h1 = soup.find_all("h1")
        if not h1:
            info["seo_issues"].append("No H1 heading")
            info["seo_score"] -= 12
        if not title or len(title.text.strip()) < 10:
            info["seo_issues"].append("Poor page title")
            info["seo_score"] -= 10
        if "viewport" not in html_lower:
            info["seo_issues"].append("Not mobile-optimized")
            info["seo_score"] -= 15
        imgs = soup.find_all("img")
        no_alt = [i for i in imgs if not i.get("alt")]
        if imgs and len(no_alt) > len(imgs) * 0.5:
            info["seo_issues"].append(f"{len(no_alt)}/{len(imgs)} images missing alt text")
            info["seo_score"] -= 8
        if "application/ld+json" not in html_lower and "itemtype" not in html_lower:
            info["seo_issues"].append("No structured data/schema")
            info["seo_score"] -= 5
        canonical = soup.find("link", attrs={"rel": "canonical"})
        if not canonical:
            info["seo_issues"].append("Missing canonical tag")
            info["seo_score"] -= 5

        info["seo_score"] = max(0, info["seo_score"])

        # Try contact page if no email found
        if not info["email"]:
            for path in ["/contact", "/contact-us", "/about"]:
                try:
                    base = f"https://{urllib.parse.urlparse(resp.url).netloc}"
                    cr = session.get(base + path, timeout=8)
                    ce = [e for e in re.findall(email_pat, cr.text)
                          if not any(s in e.lower() for s in SKIP_EMAILS)]
                    if ce:
                        info["email"] = ce[0]
                        break
                except Exception:
                    continue

    except Exception:
        pass

    return info


def find_emails_for_website(website_url, session=None):
    """
    Comprehensive email finding for a website.
    Tries main page, contact pages, and about pages.
    Returns list of emails found (best first).
    """
    if session is None:
        session = requests.Session()
        session.headers.update({"User-Agent": random.choice(USER_AGENTS)})

    domain = _extract_domain(website_url)
    all_emails = set()
    email_pat = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

    # 1. Scrape main page
    try:
        resp = session.get(website_url, timeout=10)
        found = [e for e in re.findall(email_pat, resp.text)
                 if not any(s in e.lower() for s in SKIP_EMAILS)]
        all_emails.update(found)
    except Exception:
        pass

    # 2. Try common contact pages
    if not all_emails:
        base_url = f"https://{domain}"
        for path in ["/contact", "/contact-us", "/about", "/about-us", "/team"]:
            try:
                resp = session.get(f"{base_url}{path}", timeout=8)
                found = [e for e in re.findall(email_pat, resp.text)
                         if not any(s in e.lower() for s in SKIP_EMAILS)]
                all_emails.update(found)
                if all_emails:
                    break
                time.sleep(0.5)
            except Exception:
                continue

    # 3. Prioritize same-domain emails
    same_domain = [e for e in all_emails if domain.replace("www.", "") in e]
    other = [e for e in all_emails if domain.replace("www.", "") not in e]

    if same_domain:
        return same_domain
    if other:
        return other

    # 4. Generate guesses if nothing found
    clean_domain = domain.replace("www.", "")
    return [f"{prefix}@{clean_domain}" for prefix in GENERIC_PREFIXES[:3]]


def _extract_domain(url):
    """Extract clean domain from URL."""
    parsed = urllib.parse.urlparse(url)
    return (parsed.netloc or parsed.path).replace("www.", "")
