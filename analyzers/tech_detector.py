"""Tech Detector — detect CMS, platforms, analytics, and other tech signals."""

import random
import re

import requests
from bs4 import BeautifulSoup

from core.constants import USER_AGENTS


def detect_tech(website_url):
    """
    Detect technologies used by a website.
    Returns dict of tech signals useful for lead scoring and personalization.
    """
    tech = {
        "cms": "",
        "has_analytics": False,
        "has_google_ads": False,
        "has_facebook_pixel": False,
        "has_ssl": False,
        "has_custom_email": False,
        "has_blog": False,
        "has_contact_form": False,
        "has_chat_widget": False,
        "platform_details": [],
    }

    try:
        session = requests.Session()
        session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
        resp = session.get(website_url, timeout=12, allow_redirects=True)
        if resp.status_code != 200:
            return tech

        html = resp.text.lower()
        soup = BeautifulSoup(resp.text, "html.parser")

        # SSL
        tech["has_ssl"] = resp.url.startswith("https")

        # CMS Detection
        cms_signals = {
            "WordPress": ["wp-content", "wp-includes", "wordpress"],
            "Wix": ["wix.com", "wixsite", "x-wix"],
            "Squarespace": ["squarespace.com", "sqsp."],
            "Shopify": ["shopify.com", "cdn.shopify"],
            "Weebly": ["weebly.com"],
            "Joomla": ["joomla", "/components/com_"],
            "Drupal": ["drupal", "sites/default/files"],
            "GoDaddy": ["godaddy.com", "secureserver.net"],
            "Webflow": ["webflow.com", "webflow.io"],
        }

        for cms, signals in cms_signals.items():
            if any(sig in html for sig in signals):
                tech["cms"] = cms
                tech["platform_details"].append(f"CMS: {cms}")
                break

        # Google Analytics
        if any(sig in html for sig in ["google-analytics.com", "gtag(", "googletagmanager.com", "ga('create"]):
            tech["has_analytics"] = True
            tech["platform_details"].append("Google Analytics")

        # Google Ads
        if any(sig in html for sig in ["googleadservices", "google_conversion", "adwords", "gads"]):
            tech["has_google_ads"] = True
            tech["platform_details"].append("Google Ads")

        # Facebook Pixel
        if any(sig in html for sig in ["facebook.com/tr", "fbevents", "fbq("]):
            tech["has_facebook_pixel"] = True
            tech["platform_details"].append("Facebook Pixel")

        # Blog detection
        if any(sig in html for sig in ["/blog", "/news", "/articles", "/posts"]):
            tech["has_blog"] = True
            tech["platform_details"].append("Has Blog")

        # Contact form detection
        forms = soup.find_all("form")
        for form in forms:
            action = str(form.get("action", "")).lower()
            form_html = str(form).lower()
            if any(kw in form_html or kw in action for kw in ["contact", "message", "inquiry", "email"]):
                tech["has_contact_form"] = True
                tech["platform_details"].append("Contact Form")
                break

        # Chat widget detection
        chat_signals = ["tawk.to", "livechat", "intercom", "drift", "crisp", "zendesk", "hubspot"]
        if any(sig in html for sig in chat_signals):
            tech["has_chat_widget"] = True
            tech["platform_details"].append("Live Chat")

        # Custom email domain check
        email_pat = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        skip = ["example.com", "sentry", "wixpress", "wordpress", "w3.org"]
        found_emails = [e for e in re.findall(email_pat, resp.text)
                       if not any(s in e.lower() for s in skip)]
        if found_emails:
            import urllib.parse
            site_domain = urllib.parse.urlparse(resp.url).netloc.replace("www.", "")
            for e in found_emails:
                if site_domain in e:
                    tech["has_custom_email"] = True
                    break

    except Exception:
        pass

    return tech
