"""
Lead Scraper - Find businesses that need SEO services
Uses DuckDuckGo search + website analysis + manual Google Maps import.
No paid APIs needed.
"""

import csv
import json
import os
import random
import re
import sys
import time
import urllib.parse
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from config import (
    LEADS_CSV,
    MAX_RESULTS_PER_SEARCH,
    TARGET_LOCATIONS,
    TARGET_NICHES,
)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


def get_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    })
    return session


# ============================================================
# METHOD 1: DuckDuckGo Search (works without blocking)
# ============================================================

def search_duckduckgo(niche, location, session):
    """Search DuckDuckGo for businesses — doesn't block like Google."""
    query = f"{niche} in {location} website contact"
    url = "https://html.duckduckgo.com/html/"

    print(f"  Searching DuckDuckGo: {niche} in {location}")
    businesses = []

    try:
        time.sleep(random.uniform(2, 5))
        resp = session.post(url, data={"q": query}, timeout=15)
        if resp.status_code != 200:
            print(f"  [!] Got status {resp.status_code}")
            return businesses

        soup = BeautifulSoup(resp.text, "html.parser")

        # DuckDuckGo results are in <a class="result__a"> tags
        for result in soup.find_all("a", class_="result__a"):
            href = result.get("href", "")
            # DuckDuckGo wraps URLs in a redirect
            if "uddg=" in href:
                actual_url = urllib.parse.unquote(href.split("uddg=")[1].split("&")[0])
            elif href.startswith("http"):
                actual_url = href
            else:
                continue

            # Filter out directories and social media
            skip_domains = [
                "google.", "youtube.", "facebook.", "yelp.", "yellowpages.",
                "bbb.", "linkedin.", "instagram.", "twitter.", "tiktok.",
                "wikipedia.", "amazon.", "justdial.", "sulekha.",
                "practo.", "indiamart.", "tradeindia.", "quora.",
                "reddit.", "tripadvisor.", "glassdoor.", "naukri.",
                "duckduckgo.",
            ]
            if any(d in actual_url.lower() for d in skip_domains):
                continue

            if actual_url.startswith("http"):
                title = result.get_text(strip=True)
                businesses.append({
                    "website": actual_url,
                    "niche": niche,
                    "location": location,
                    "title_hint": title[:80],
                })

    except Exception as e:
        print(f"  [!] Error: {e}")

    # Deduplicate by domain
    seen = set()
    unique = []
    for biz in businesses:
        domain = urllib.parse.urlparse(biz["website"]).netloc
        if domain and domain not in seen:
            seen.add(domain)
            unique.append(biz)

    print(f"  Found {len(unique)} unique websites")
    return unique[:MAX_RESULTS_PER_SEARCH]


# ============================================================
# METHOD 2: JustDial Scraper (great for Indian businesses)
# ============================================================

def search_justdial(niche, location, session):
    """Search JustDial for Indian businesses."""
    city = location.split(",")[0].strip().lower().replace(" ", "-")
    niche_slug = niche.lower().replace(" ", "-")

    url = f"https://www.justdial.com/{city}/{niche_slug}"
    print(f"  Searching JustDial: {niche} in {city}")
    businesses = []

    try:
        time.sleep(random.uniform(2, 4))
        session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://www.justdial.com/",
        })
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            print(f"  [!] JustDial returned status {resp.status_code}")
            return businesses

        soup = BeautifulSoup(resp.text, "html.parser")

        # JustDial stores business data in various formats
        # Look for business names and website links
        for item in soup.find_all("li", class_=re.compile(r"cntanr")):
            name_tag = item.find("span", class_="lng_cont_name")
            name = name_tag.get_text(strip=True) if name_tag else ""

            # Find website links
            website_tag = item.find("a", href=re.compile(r"http"), class_=re.compile(r"website"))
            website = ""
            if website_tag:
                website = website_tag.get("href", "")

            # Find phone (JustDial encodes these)
            phone = ""

            if name:
                businesses.append({
                    "website": website,
                    "business_name": name,
                    "niche": niche,
                    "location": location,
                    "phone": phone,
                })

        # Also try a simpler pattern - look for any external links
        if not businesses:
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                text = link.get_text(strip=True)
                if (href.startswith("http") and
                    "justdial" not in href and
                    len(text) > 3 and
                    not any(s in href for s in ["google", "facebook", "twitter", "instagram"])):
                    businesses.append({
                        "website": href,
                        "business_name": text[:60],
                        "niche": niche,
                        "location": location,
                    })

    except Exception as e:
        print(f"  [!] JustDial error: {e}")

    # Deduplicate
    seen = set()
    unique = []
    for biz in businesses:
        key = biz.get("website") or biz.get("business_name")
        if key and key not in seen:
            seen.add(key)
            unique.append(biz)

    print(f"  Found {len(unique)} businesses on JustDial")
    return unique[:MAX_RESULTS_PER_SEARCH]


# ============================================================
# Website Analysis (extract emails, phones, SEO issues)
# ============================================================

def extract_business_info(website_url, session):
    """Visit a business website and extract contact info + SEO issues."""
    info = {
        "website": website_url,
        "business_name": "",
        "email": "",
        "phone": "",
        "has_ssl": website_url.startswith("https"),
        "has_meta_description": False,
        "has_h1": False,
        "page_title": "",
        "seo_issues": [],
    }

    try:
        resp = session.get(website_url, timeout=10, allow_redirects=True)
        if resp.status_code != 200:
            return info

        soup = BeautifulSoup(resp.text, "html.parser")

        # Page title
        title_tag = soup.find("title")
        if title_tag:
            info["page_title"] = title_tag.text.strip()[:100]
            info["business_name"] = title_tag.text.strip().split("|")[0].split("-")[0].strip()[:60]

        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        info["has_meta_description"] = bool(meta_desc and meta_desc.get("content", "").strip())

        # H1
        h1 = soup.find("h1")
        info["has_h1"] = bool(h1)

        # Find emails
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails_found = re.findall(email_pattern, resp.text)
        skip_emails = ["example.com", "sentry.io", "wixpress", "wordpress", "w3.org", ".png", ".jpg"]
        valid_emails = [e for e in emails_found if not any(s in e.lower() for s in skip_emails)]
        if valid_emails:
            info["email"] = valid_emails[0]

        # Find phone numbers (Indian + international formats)
        phone_patterns = [
            r'\+91[\s-]?\d{5}[\s-]?\d{5}',           # +91 XXXXX XXXXX
            r'\+91[\s-]?\d{10}',                       # +91 XXXXXXXXXX
            r'0\d{2,4}[\s-]?\d{6,8}',                 # 0XX-XXXXXXXX
            r'[\(]?\d{3}[\)]?[-.\s]?\d{3}[-.\s]?\d{4}', # (XXX) XXX-XXXX
            r'\d{10}',                                  # XXXXXXXXXX
        ]
        for pattern in phone_patterns:
            phones = re.findall(pattern, resp.text)
            if phones:
                info["phone"] = phones[0]
                break

        # SEO issues for personalization
        if not info["has_ssl"]:
            info["seo_issues"].append("No SSL certificate")
        if not info["has_meta_description"]:
            info["seo_issues"].append("Missing meta description")
        if not info["has_h1"]:
            info["seo_issues"].append("Missing H1 tag")
        if not title_tag or len(title_tag.text.strip()) < 10:
            info["seo_issues"].append("Poor page title")

        page_text = resp.text.lower()
        if "viewport" not in page_text:
            info["seo_issues"].append("Not mobile-optimized")
        if soup.find_all("img", alt="") or soup.find_all("img", alt=None):
            info["seo_issues"].append("Images missing alt text")

        # Try contact page for emails
        if not info["email"]:
            contact_links = soup.find_all("a", href=True, string=re.compile(r"contact", re.I))
            if contact_links:
                try:
                    contact_url = contact_links[0]["href"]
                    if not contact_url.startswith("http"):
                        contact_url = urllib.parse.urljoin(website_url, contact_url)
                    time.sleep(random.uniform(1, 2))
                    contact_resp = session.get(contact_url, timeout=10)
                    contact_emails = re.findall(email_pattern, contact_resp.text)
                    valid = [e for e in contact_emails if not any(s in e.lower() for s in skip_emails)]
                    if valid:
                        info["email"] = valid[0]
                except Exception:
                    pass

    except Exception as e:
        print(f"    [!] Error analyzing {website_url}: {e}")

    return info


def guess_email(domain, business_name=""):
    """Guess common email patterns."""
    domain = domain.replace("www.", "")
    return [
        f"info@{domain}",
        f"contact@{domain}",
        f"hello@{domain}",
        f"admin@{domain}",
        f"office@{domain}",
    ]


# ============================================================
# Main Scraping Functions
# ============================================================

def scrape_leads(niches=None, locations=None):
    """Main scraping function. Uses DuckDuckGo + JustDial."""
    niches = niches or TARGET_NICHES
    locations = locations or TARGET_LOCATIONS

    os.makedirs(os.path.dirname(LEADS_CSV) if os.path.dirname(LEADS_CSV) else ".", exist_ok=True)

    # Load existing leads to avoid duplicates
    existing_domains = set()
    if os.path.exists(LEADS_CSV):
        with open(LEADS_CSV, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "website" in row and row["website"]:
                    domain = urllib.parse.urlparse(row["website"]).netloc
                    existing_domains.add(domain)

    session = get_session()
    all_leads = []
    total_new = 0

    print("=" * 60)
    print("LEAD SCRAPER - Finding businesses that need SEO")
    print("=" * 60)

    for niche in niches:
        for location in locations:
            print(f"\n[*] Scraping: {niche} in {location}")

            # Try DuckDuckGo first
            businesses = search_duckduckgo(niche, location, session)

            # Also try JustDial for Indian cities
            jd_results = search_justdial(niche, location, session)
            businesses.extend(jd_results)

            for biz in businesses:
                website = biz.get("website", "")
                if not website:
                    continue

                domain = urllib.parse.urlparse(website).netloc
                if domain in existing_domains:
                    continue

                print(f"    Analyzing: {domain}")
                info = extract_business_info(website, session)

                # Use hints from search results
                if not info["business_name"] and biz.get("business_name"):
                    info["business_name"] = biz["business_name"]
                if not info["business_name"] and biz.get("title_hint"):
                    info["business_name"] = biz["title_hint"].split("|")[0].split("-")[0].strip()[:60]

                info["niche"] = niche
                info["location"] = location
                info["scraped_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")

                # Generate guessed emails if none found
                if not info["email"]:
                    guessed = guess_email(domain, info["business_name"])
                    info["email"] = guessed[0]
                    info["email_guessed"] = True
                else:
                    info["email_guessed"] = False

                info["seo_issues"] = "; ".join(info["seo_issues"]) if info["seo_issues"] else ""

                all_leads.append(info)
                existing_domains.add(domain)
                total_new += 1

                time.sleep(random.uniform(2, 4))

            time.sleep(random.uniform(3, 6))

    # Save to CSV
    if all_leads:
        fieldnames = [
            "business_name", "website", "email", "email_guessed", "phone",
            "niche", "location", "has_ssl", "has_meta_description", "has_h1",
            "page_title", "seo_issues", "scraped_date",
        ]

        file_exists = os.path.exists(LEADS_CSV) and os.path.getsize(LEADS_CSV) > 0
        with open(LEADS_CSV, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            if not file_exists:
                writer.writeheader()
            writer.writerows(all_leads)

        print(f"\n{'=' * 60}")
        print(f"DONE! Scraped {total_new} new leads")
        print(f"Total leads saved to: {LEADS_CSV}")
        print(f"{'=' * 60}")
    else:
        print("\nNo new leads found from search engines.")
        print("\nTRY THIS INSTEAD — Manual Google Maps method (takes 5 minutes):")
        print("  Run: python3 lead_scraper.py --google-maps-help")

    return all_leads


# ============================================================
# METHOD 3: Manual Google Maps Export (easiest, most reliable)
# ============================================================

def google_maps_manual_help():
    """Print step-by-step instructions for manually getting leads from Google Maps."""
    print("""
╔══════════════════════════════════════════════════════════╗
║     GOOGLE MAPS MANUAL METHOD (Most Reliable!)          ║
╚══════════════════════════════════════════════════════════╝

This takes about 5-10 minutes and gets you 50-100 leads:

STEP 1: Open Google Maps
────────────────────────
  → Go to: https://www.google.com/maps
  → Search: "dentist in Hyderabad" (or your niche + city)

STEP 2: Copy Business Details
─────────────────────────────
  → Click each business on the map
  → Copy their: Name, Website, Phone
  → Paste into a spreadsheet (Google Sheets or Excel)

STEP 3: Save as CSV
───────────────────
  → Your spreadsheet should have columns:
      business_name, website, phone, niche, location
  → Save/download as CSV file
  → Put it in: cold_email_system/data/ folder

STEP 4: Import Into System
─────────────────────────
  → Run: python3 lead_scraper.py --import data/your_file.csv

  ──────────────────────────────────────────────────────
  EVEN FASTER METHOD — Use the "Add Lead" command below
  to type leads one by one directly into the system.
  ──────────────────────────────────────────────────────

  → Run: python3 lead_scraper.py --add

    """)


def add_lead_interactive():
    """Add leads one by one interactively."""
    os.makedirs("data", exist_ok=True)

    fieldnames = [
        "business_name", "website", "email", "email_guessed", "phone",
        "niche", "location", "has_ssl", "has_meta_description", "has_h1",
        "page_title", "seo_issues", "scraped_date",
    ]

    file_exists = os.path.exists(LEADS_CSV) and os.path.getsize(LEADS_CSV) > 0

    print("""
╔══════════════════════════════════════════════════════════╗
║              ADD LEADS MANUALLY                          ║
║  Type business details. Type DONE to finish.             ║
╚══════════════════════════════════════════════════════════╝
    """)

    session = get_session()
    leads_added = 0

    while True:
        print(f"\n--- Lead #{leads_added + 1} ---")
        name = input("  Business Name (or DONE to finish): ").strip()
        if name.upper() == "DONE":
            break

        website = input("  Website URL: ").strip()
        if website and not website.startswith("http"):
            website = "https://" + website

        email = input("  Email (leave blank to auto-find): ").strip()
        phone = input("  Phone (optional): ").strip()
        niche = input("  Niche (e.g. dentist): ").strip()
        location = input("  City: ").strip()

        # Auto-analyze website if provided
        seo_issues = ""
        email_guessed = False
        if website:
            print(f"  Analyzing {website}...")
            info = extract_business_info(website, session)
            if not email and info["email"]:
                email = info["email"]
                print(f"  Found email: {email}")
            if not email:
                domain = urllib.parse.urlparse(website).netloc
                email = guess_email(domain)[0]
                email_guessed = True
                print(f"  Guessed email: {email}")
            if not phone and info["phone"]:
                phone = info["phone"]
            seo_issues = "; ".join(info["seo_issues"]) if info["seo_issues"] else ""
            if seo_issues:
                print(f"  SEO issues found: {seo_issues}")

        lead = {
            "business_name": name,
            "website": website,
            "email": email,
            "email_guessed": email_guessed,
            "phone": phone,
            "niche": niche,
            "location": location,
            "has_ssl": website.startswith("https") if website else False,
            "has_meta_description": "",
            "has_h1": "",
            "page_title": "",
            "seo_issues": seo_issues,
            "scraped_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        with open(LEADS_CSV, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
                file_exists = True
            writer.writerow(lead)

        leads_added += 1
        print(f"  Lead saved!")

    print(f"\n{'=' * 40}")
    print(f"Added {leads_added} leads to {LEADS_CSV}")
    print(f"{'=' * 40}")


def import_csv(csv_path):
    """Import leads from any CSV file."""
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return

    os.makedirs("data", exist_ok=True)
    fieldnames = [
        "business_name", "website", "email", "email_guessed", "phone",
        "niche", "location", "has_ssl", "has_meta_description", "has_h1",
        "page_title", "seo_issues", "scraped_date",
    ]

    imported = 0
    file_exists = os.path.exists(LEADS_CSV) and os.path.getsize(LEADS_CSV) > 0

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        source_fields = reader.fieldnames
        print(f"  Found columns: {source_fields}")

        for row in reader:
            # Try to map common column names
            name = (row.get("business_name") or row.get("Business Name") or
                    row.get("company") or row.get("Company") or
                    row.get("name") or row.get("Name") or "")
            website = (row.get("website") or row.get("Website") or
                       row.get("url") or row.get("URL") or
                       row.get("domain") or row.get("Domain") or "")
            email_addr = (row.get("email") or row.get("Email") or
                     row.get("email_address") or "")
            phone = (row.get("phone") or row.get("Phone") or
                     row.get("mobile") or row.get("Mobile") or "")
            niche = (row.get("niche") or row.get("Niche") or
                     row.get("category") or row.get("Category") or "")
            location_val = (row.get("location") or row.get("Location") or
                       row.get("city") or row.get("City") or "")

            if not name and not website and not email_addr:
                continue

            if website and not website.startswith("http"):
                website = "https://" + website

            lead = {
                "business_name": name,
                "website": website,
                "email": email_addr,
                "email_guessed": False,
                "phone": phone,
                "niche": niche,
                "location": location_val,
                "has_ssl": "",
                "has_meta_description": "",
                "has_h1": "",
                "page_title": "",
                "seo_issues": "",
                "scraped_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }

            with open(LEADS_CSV, "a", newline="") as outf:
                writer = csv.DictWriter(outf, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                    file_exists = True
                writer.writerow(lead)

            imported += 1

    print(f"\nImported {imported} leads from {csv_path}")
    print(f"Saved to: {LEADS_CSV}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--import" and len(sys.argv) > 2:
            import_csv(sys.argv[2])
        elif sys.argv[1] == "--add":
            add_lead_interactive()
        elif sys.argv[1] == "--google-maps-help":
            google_maps_manual_help()
        else:
            print("Usage:")
            print("  python3 lead_scraper.py              - Auto-scrape leads")
            print("  python3 lead_scraper.py --add         - Add leads manually")
            print("  python3 lead_scraper.py --import file.csv - Import from CSV")
            print("  python3 lead_scraper.py --google-maps-help - Google Maps guide")
    else:
        scrape_leads()
