#!/usr/bin/env python3
"""
SEO Cold Email Outreach System — Complete Dashboard App
Double-click 'LAUNCH APP.command' to start. Opens in your browser.
"""

import csv
import email.mime.multipart
import email.mime.text
import json
import os
import random
import re
import smtplib
import time
import urllib.parse
from datetime import datetime, timedelta
from io import StringIO

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

# ============================================================
# APP CONFIG
# ============================================================
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
LOGS_DIR = os.path.join(APP_DIR, "logs")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
LEADS_FILE = os.path.join(DATA_DIR, "leads.csv")
SENT_FILE = os.path.join(DATA_DIR, "sent_emails.csv")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

LEAD_COLUMNS = [
    "business_name", "website", "email", "email_source", "phone",
    "niche", "location", "seo_score", "seo_issues",
    "status", "notes", "added_date",
]

SENT_COLUMNS = [
    "to_email", "business_name", "subject", "template",
    "followup_num", "from_email", "sent_at", "status",
]

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


# ============================================================
# SETTINGS
# ============================================================
def load_settings():
    defaults = {
        "your_name": "",
        "your_company": "",
        "your_phone": "",
        "your_website": "",
        "your_calendly": "",
        "email_accounts": [],
        "target_niches": ["dentist", "plastic surgeon", "real estate agent", "med spa"],
        "target_locations": ["Hyderabad", "Mumbai", "Bangalore", "Delhi"],
        "daily_limit": 5,
        "delay_min": 45,
        "delay_max": 120,
        "followup_days": [3, 7, 14],
    }
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            saved = json.load(f)
            defaults.update(saved)
    return defaults


def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


# ============================================================
# LEADS DATABASE
# ============================================================
def load_leads():
    if os.path.exists(LEADS_FILE) and os.path.getsize(LEADS_FILE) > 0:
        try:
            df = pd.read_csv(LEADS_FILE)
            for col in LEAD_COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            return df
        except Exception:
            return pd.DataFrame(columns=LEAD_COLUMNS)
    return pd.DataFrame(columns=LEAD_COLUMNS)


def save_leads(df):
    df.to_csv(LEADS_FILE, index=False)


def load_sent():
    if os.path.exists(SENT_FILE) and os.path.getsize(SENT_FILE) > 0:
        try:
            return pd.read_csv(SENT_FILE)
        except Exception:
            return pd.DataFrame(columns=SENT_COLUMNS)
    return pd.DataFrame(columns=SENT_COLUMNS)


def save_sent(df):
    df.to_csv(SENT_FILE, index=False)


# ============================================================
# SCRAPER
# ============================================================
def search_duckduckgo(niche, location):
    query = f"{niche} in {location} website contact"
    url = "https://html.duckduckgo.com/html/"
    results = []

    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html",
        })
        time.sleep(random.uniform(2, 4))
        resp = session.post(url, data={"q": query}, timeout=15)
        if resp.status_code != 200:
            return results

        soup = BeautifulSoup(resp.text, "html.parser")
        skip = [
            "google.", "youtube.", "facebook.", "yelp.", "linkedin.",
            "instagram.", "twitter.", "wikipedia.", "amazon.", "justdial.",
            "sulekha.", "practo.", "indiamart.", "quora.", "reddit.",
            "duckduckgo.", "tripadvisor.", "naukri.", "glassdoor.",
        ]

        for result in soup.find_all("a", class_="result__a"):
            href = result.get("href", "")
            if "uddg=" in href:
                actual = urllib.parse.unquote(href.split("uddg=")[1].split("&")[0])
            elif href.startswith("http"):
                actual = href
            else:
                continue

            if any(d in actual.lower() for d in skip):
                continue
            if actual.startswith("http"):
                title = result.get_text(strip=True)
                results.append({"website": actual, "title": title[:80]})

    except Exception:
        pass

    # Deduplicate
    seen = set()
    unique = []
    for r in results:
        domain = urllib.parse.urlparse(r["website"]).netloc
        if domain and domain not in seen:
            seen.add(domain)
            unique.append(r)
    return unique[:20]


def analyze_website(website_url):
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

        # Emails
        email_pat = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        skip_emails = ["example.com", "sentry", "wixpress", "wordpress", "w3.org", ".png", ".jpg"]
        found = [e for e in re.findall(email_pat, resp.text) if not any(s in e.lower() for s in skip_emails)]
        if found:
            info["email"] = found[0]

        # Phone (Indian + international)
        for pat in [r'\+91[\s-]?\d{5}[\s-]?\d{5}', r'\+91[\s-]?\d{10}', r'0\d{2,4}[\s-]?\d{6,8}',
                    r'[\(]?\d{3}[\)]?[-.\s]?\d{3}[-.\s]?\d{4}', r'\d{10}']:
            phones = re.findall(pat, resp.text)
            if phones:
                info["phone"] = phones[0]
                break

        # SEO checks
        html_lower = resp.text.lower()
        if not resp.url.startswith("https"):
            info["seo_issues"].append("No SSL/HTTPS"); info["seo_score"] -= 15
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if not meta_desc or not meta_desc.get("content", "").strip():
            info["seo_issues"].append("Missing meta description"); info["seo_score"] -= 12
        h1 = soup.find_all("h1")
        if not h1:
            info["seo_issues"].append("No H1 heading"); info["seo_score"] -= 12
        if not title or len(title.text.strip()) < 10:
            info["seo_issues"].append("Poor page title"); info["seo_score"] -= 10
        if "viewport" not in html_lower:
            info["seo_issues"].append("Not mobile-optimized"); info["seo_score"] -= 15
        imgs = soup.find_all("img")
        no_alt = [i for i in imgs if not i.get("alt")]
        if imgs and len(no_alt) > len(imgs) * 0.5:
            info["seo_issues"].append(f"{len(no_alt)}/{len(imgs)} images missing alt text"); info["seo_score"] -= 8
        if "application/ld+json" not in html_lower and "itemtype" not in html_lower:
            info["seo_issues"].append("No structured data/schema"); info["seo_score"] -= 5
        canonical = soup.find("link", attrs={"rel": "canonical"})
        if not canonical:
            info["seo_issues"].append("Missing canonical tag"); info["seo_score"] -= 5

        info["seo_score"] = max(0, info["seo_score"])

        # Try contact page if no email
        if not info["email"]:
            for path in ["/contact", "/contact-us", "/about"]:
                try:
                    base = f"https://{urllib.parse.urlparse(resp.url).netloc}"
                    cr = session.get(base + path, timeout=8)
                    ce = [e for e in re.findall(email_pat, cr.text) if not any(s in e.lower() for s in skip_emails)]
                    if ce:
                        info["email"] = ce[0]
                        break
                except Exception:
                    continue

    except Exception:
        pass
    return info


# ============================================================
# EMAIL TEMPLATES
# ============================================================
TEMPLATES = {
    "SEO Audit Findings": {
        "subjects": [
            "Quick question about {website}",
            "{business_name} — found something on your site",
        ],
        "body": """Hi{name_greeting},

I was looking at {website} and noticed a few things that are likely costing you leads from Google:

{seo_issues}

These are quick fixes that could help you show up higher when people search for "{niche} in {location}."

I help {niche}s in {location} get more calls and bookings from Google — without paid ads.

Would it make sense to jump on a quick 10-min call this week so I can walk you through what I found? No pitch, just sharing what I see.

{signature}""",
        "followups": [
            """Hi{name_greeting},

Just following up on my email about {website}.

The issues I found are the kind that get worse over time as competitors fix theirs.

Happy to share my findings in a quick call — completely free, no strings attached.

{signature}""",
            """Hi{name_greeting},

I'll keep this short — I sent over some SEO findings about {website} last week.

If you're curious, I put together a quick list of the top 3 things I'd fix first to get {business_name} ranking higher on Google.

Want me to send it over?

{signature}""",
            """Hi{name_greeting},

Last note from me — I don't want to be a pest.

If improving {business_name}'s Google rankings is on your radar at any point, feel free to reach out.

Wishing you all the best,
{your_name}""",
        ],
    },
    "Competitor Comparison": {
        "subjects": [
            "How {business_name} compares on Google",
            "Your competitors in {location} are doing this",
        ],
        "body": """Hi{name_greeting},

I was researching {niche}s in {location} and noticed something interesting.

Some of your competitors are showing up above {business_name} on Google for searches like "{niche} near me" — and it's not because they're better. They just have their website set up to rank.

A few quick changes to {website} could help you compete with (and pass) them.

Would you be open to a 10-minute call where I can show you exactly what they're doing differently? No cost, no obligation.

{signature}""",
        "followups": [
            """Hi{name_greeting},

Following up on my email about {business_name}'s Google visibility.

I looked deeper and there are 2-3 specific things your top-ranking competitors have that {website} is missing.

Would a quick breakdown be helpful?

{signature}""",
            """Hi{name_greeting},

If you ever want to see how {business_name} stacks up against other {niche}s on Google in {location}, I'm happy to put together a free comparison.

Just reply "interested" and I'll send it over.

{signature}""",
            """Hi{name_greeting},

Last email from me on this. If getting more leads from Google becomes a priority for {business_name}, I'm here.

Best,
{your_name}""",
        ],
    },
    "Value First (Free Tip)": {
        "subjects": [
            "Free tip to get {business_name} more Google calls",
            "Quick SEO win for {business_name}",
        ],
        "body": """Hi{name_greeting},

Here's one free thing you can do today to get more calls from Google:

{seo_issues}

This alone won't put you at #1, but it's a quick win most {niche}s in {location} overlook.

I specialize in helping {niche}s rank higher on Google. If you'd like, I can do a full (free) review of {website} and share 3-5 more improvements.

Worth a quick chat?

{signature}""",
        "followups": [
            """Hi{name_greeting},

Did you get a chance to look at the SEO tip I sent for {website}?

I have a few more specific to {niche}s in {location} that could make a real difference.

Happy to share on a quick call or over email.

{signature}""",
            """Hi{name_greeting},

I put together a short SEO checklist specifically for {niche}s that want more calls from Google.

Want me to send it your way? Free and takes 15 minutes.

{signature}""",
            """Hi{name_greeting},

I'll leave it here. If you ever want a fresh set of eyes on {business_name}'s Google presence, just reply.

Cheers,
{your_name}""",
        ],
    },
    "Case Study": {
        "subjects": [
            "How a {niche} got 3x more Google calls",
            "This {niche} went from page 5 to page 1",
        ],
        "body": """Hi{name_greeting},

I recently helped a {niche} go from barely showing up on Google to ranking on the first page.

Within 90 days they saw:
- 3x increase in calls from Google
- First page rankings for main keywords
- 40% more website visitors from organic search

I took a look at {website} and I see similar potential for {business_name}.

Would you be open to a quick chat about what that could look like for you?

{signature}""",
        "followups": [
            """Hi{name_greeting},

Just circling back on my email about getting {business_name} more visibility on Google.

The strategies I used work especially well right now because most local businesses haven't caught up yet.

Would a 10-minute call this week work?

{signature}""",
            """Hi{name_greeting},

The {niche} I mentioned saw most results in the first 60-90 days because we focused on quick wins first.

If you're interested, I can share which quick wins would apply to {business_name}.

{signature}""",
            """Hi{name_greeting},

I don't want to keep filling your inbox, so this will be my last note.

If you ever want to explore getting more leads from Google, feel free to reach out.

All the best,
{your_name}""",
        ],
    },
}


def format_template(template_name, variables, followup_num=0):
    tmpl = TEMPLATES[template_name]
    name = variables.get("business_name", "").split()[0] if variables.get("business_name") else ""
    variables["name_greeting"] = f" {name}" if name else ""

    sig_parts = [variables.get("your_name", "")]
    if variables.get("your_company"):
        sig_parts.append(variables["your_company"])
    if variables.get("your_phone"):
        sig_parts.append(variables["your_phone"])
    if variables.get("your_calendly"):
        sig_parts.append(f"\nP.S. Book a time here: {variables['your_calendly']}")
    variables["signature"] = "\n".join(sig_parts)

    if followup_num == 0:
        body = tmpl["body"]
        subject = tmpl["subjects"][0]
    else:
        idx = min(followup_num - 1, len(tmpl["followups"]) - 1)
        body = tmpl["followups"][idx]
        subject = "Re: " + tmpl["subjects"][0]

    for key, val in variables.items():
        body = body.replace(f"{{{key}}}", str(val))
        subject = subject.replace(f"{{{key}}}", str(val))

    body = re.sub(r'\{[a-z_]+\}', '', body)
    subject = re.sub(r'\{[a-z_]+\}', '', subject)
    return subject.strip(), body.strip()


# ============================================================
# EMAIL SENDER
# ============================================================
def send_one_email(account, to_email, subject, body):
    try:
        msg = email.mime.multipart.MIMEMultipart("alternative")
        msg["From"] = f"{account['name']} <{account['email']}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(email.mime.text.MIMEText(body, "plain"))

        server = smtplib.SMTP(account.get("smtp_server", "smtp.gmail.com"), account.get("smtp_port", 587))
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


# ============================================================
# STREAMLIT APP
# ============================================================
st.set_page_config(
    page_title="SEO Cold Email System",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Load settings into session
if "settings" not in st.session_state:
    st.session_state.settings = load_settings()

settings = st.session_state.settings

# ============================================================
# SIDEBAR NAVIGATION
# ============================================================
st.sidebar.title("SEO Cold Email System")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Find Leads", "My Leads", "SEO Audit",
     "Send Emails", "Follow-ups", "Backup & Restore", "Settings"],
    index=0,
)

st.sidebar.markdown("---")
leads_df = load_leads()
sent_df = load_sent()
st.sidebar.metric("Total Leads", len(leads_df))
st.sidebar.metric("Emails Sent", len(sent_df))


# ============================================================
# PAGE: DASHBOARD
# ============================================================
def _find_col(options, candidates):
    for c in candidates:
        for i, o in enumerate(options):
            if c.lower() == o.lower():
                return i
    return 0


if page == "Dashboard":
    st.markdown("## Dashboard")

    if not settings.get("your_name"):
        st.warning("Go to **Settings** first to set up your name, email account, and targets.")
        st.stop()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Leads", len(leads_df))
    with col2:
        st.metric("Emails Sent", len(sent_df))
    with col3:
        replied = len(leads_df[leads_df["status"] == "replied"]) if "status" in leads_df.columns else 0
        st.metric("Replies", replied)
    with col4:
        won = len(leads_df[leads_df["status"] == "won"]) if "status" in leads_df.columns else 0
        st.metric("Clients Won", won)

    st.markdown("---")

    # Pipeline
    if len(leads_df) > 0 and "status" in leads_df.columns:
        st.markdown("### Pipeline")
        status_counts = leads_df["status"].fillna("new").value_counts()
        st.bar_chart(status_counts)

    # Recent activity
    if len(sent_df) > 0:
        st.markdown("### Recent Emails Sent")
        recent = sent_df.tail(10).sort_values("sent_at", ascending=False) if "sent_at" in sent_df.columns else sent_df.tail(10)
        st.dataframe(recent[["to_email", "business_name", "template", "followup_num", "sent_at", "status"]],
                     use_container_width=True, hide_index=True)

    # Quick actions
    st.markdown("### Quick Actions")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Find New Leads", use_container_width=True):
            st.switch_page_workaround = "Find Leads"
    with col2:
        if st.button("Send Emails", use_container_width=True):
            st.switch_page_workaround = "Send Emails"
    with col3:
        if st.button("Send Follow-ups", use_container_width=True):
            st.switch_page_workaround = "Follow-ups"


# ============================================================
# PAGE: FIND LEADS
# ============================================================
elif page == "Find Leads":
    st.markdown("## Find Leads")

    tab1, tab2, tab3 = st.tabs(["Auto-Search", "Add Manually", "Import CSV"])

    # --- TAB 1: AUTO SEARCH ---
    with tab1:
        st.markdown("Search the internet for businesses that need SEO.")

        col1, col2 = st.columns(2)
        with col1:
            niches = st.multiselect(
                "Business types to find",
                ["dentist", "plastic surgeon", "real estate agent", "med spa",
                 "chiropractor", "plumber", "roofing contractor", "lawyer",
                 "hvac contractor", "electrician"],
                default=settings.get("target_niches", ["dentist"]),
            )
        with col2:
            locations_text = st.text_area(
                "Cities (one per line)",
                value="\n".join(settings.get("target_locations", ["Hyderabad"])),
                height=150,
            )
            locations = [l.strip() for l in locations_text.strip().split("\n") if l.strip()]

        max_per = st.slider("Max results per search", 5, 20, 10)

        if st.button("Start Searching", type="primary", use_container_width=True):
            leads_df = load_leads()
            existing_domains = set()
            if len(leads_df) > 0 and "website" in leads_df.columns:
                for w in leads_df["website"].dropna():
                    existing_domains.add(urllib.parse.urlparse(str(w)).netloc)

            total_found = 0
            progress = st.progress(0)
            status_text = st.empty()
            results_container = st.empty()

            total_searches = len(niches) * len(locations)
            search_num = 0

            new_leads = []

            for niche in niches:
                for location in locations:
                    search_num += 1
                    progress.progress(search_num / total_searches)
                    status_text.text(f"Searching: {niche} in {location}...")

                    results = search_duckduckgo(niche, location)

                    for r in results[:max_per]:
                        domain = urllib.parse.urlparse(r["website"]).netloc
                        if domain in existing_domains:
                            continue
                        existing_domains.add(domain)

                        status_text.text(f"Analyzing: {domain}...")
                        info = analyze_website(r["website"])

                        lead = {
                            "business_name": info["business_name"] or r.get("title", "")[:60],
                            "website": r["website"],
                            "email": info["email"],
                            "email_source": "found" if info["email"] else "guessed",
                            "phone": info["phone"],
                            "niche": niche,
                            "location": location,
                            "seo_score": info["seo_score"],
                            "seo_issues": "; ".join(info["seo_issues"]),
                            "status": "new",
                            "notes": "",
                            "added_date": datetime.now().strftime("%Y-%m-%d"),
                        }

                        if not lead["email"]:
                            lead["email"] = f"info@{domain.replace('www.', '')}"
                            lead["email_source"] = "guessed"

                        new_leads.append(lead)
                        total_found += 1

                        # Show live results
                        results_container.dataframe(
                            pd.DataFrame(new_leads)[["business_name", "website", "email", "seo_score", "niche", "location"]],
                            use_container_width=True, hide_index=True,
                        )

                    time.sleep(random.uniform(2, 4))

            progress.progress(1.0)

            if new_leads:
                new_df = pd.DataFrame(new_leads)
                leads_df = pd.concat([leads_df, new_df], ignore_index=True)
                save_leads(leads_df)
                status_text.text("")
                st.success(f"Found and saved {total_found} new leads!")
            else:
                status_text.text("")
                st.info("No new leads found. Try different niches or cities.")

    # --- TAB 2: ADD MANUALLY ---
    with tab2:
        st.markdown("Add leads one at a time.")

        with st.form("add_lead_form"):
            col1, col2 = st.columns(2)
            with col1:
                biz_name = st.text_input("Business Name *")
                website_url = st.text_input("Website URL")
                email_addr = st.text_input("Email")
            with col2:
                phone = st.text_input("Phone")
                niche = st.text_input("Niche (e.g. dentist)")
                location = st.text_input("City")

            submitted = st.form_submit_button("Add Lead", type="primary", use_container_width=True)

            if submitted and biz_name:
                if website_url and not website_url.startswith("http"):
                    website_url = "https://" + website_url

                # Auto-analyze if website given
                seo_score = ""
                seo_issues = ""
                if website_url:
                    with st.spinner("Analyzing website..."):
                        info = analyze_website(website_url)
                        if not email_addr and info["email"]:
                            email_addr = info["email"]
                        if not phone and info["phone"]:
                            phone = info["phone"]
                        seo_score = info["seo_score"]
                        seo_issues = "; ".join(info["seo_issues"])

                if not email_addr and website_url:
                    domain = urllib.parse.urlparse(website_url).netloc.replace("www.", "")
                    email_addr = f"info@{domain}"

                new_lead = pd.DataFrame([{
                    "business_name": biz_name, "website": website_url,
                    "email": email_addr, "email_source": "manual",
                    "phone": phone, "niche": niche, "location": location,
                    "seo_score": seo_score, "seo_issues": seo_issues,
                    "status": "new", "notes": "",
                    "added_date": datetime.now().strftime("%Y-%m-%d"),
                }])
                leads_df = load_leads()
                leads_df = pd.concat([leads_df, new_lead], ignore_index=True)
                save_leads(leads_df)
                st.success(f"Added: {biz_name}" + (f" (email: {email_addr})" if email_addr else ""))

    # --- TAB 3: IMPORT CSV ---
    with tab3:
        st.markdown("Upload a CSV or Excel file with your leads.")
        st.markdown("Your file should have columns like: `business_name`, `website`, `email`, `phone`, `niche`, `location`")

        uploaded = st.file_uploader("Choose a file", type=["csv", "xlsx", "xls"])

        if uploaded:
            try:
                if uploaded.name.endswith(".csv"):
                    import_df = pd.read_csv(uploaded)
                else:
                    import_df = pd.read_excel(uploaded)

                st.markdown(f"**Found {len(import_df)} rows with columns:** {', '.join(import_df.columns.tolist())}")
                st.dataframe(import_df.head(5), use_container_width=True, hide_index=True)

                # Column mapping
                st.markdown("### Map your columns")
                col_options = ["(skip)"] + import_df.columns.tolist()

                col1, col2, col3 = st.columns(3)
                with col1:
                    name_col = st.selectbox("Business Name column", col_options, index=_find_col(col_options, ["business_name", "company", "name"]))
                    website_col = st.selectbox("Website column", col_options, index=_find_col(col_options, ["website", "url", "domain"]))
                with col2:
                    email_col = st.selectbox("Email column", col_options, index=_find_col(col_options, ["email", "email_address"]))
                    phone_col = st.selectbox("Phone column", col_options, index=_find_col(col_options, ["phone", "mobile", "telephone"]))
                with col3:
                    niche_col = st.selectbox("Niche column", col_options, index=_find_col(col_options, ["niche", "category", "industry"]))
                    location_col = st.selectbox("Location column", col_options, index=_find_col(col_options, ["location", "city", "area"]))

                if st.button("Import Leads", type="primary", use_container_width=True):
                    new_leads = []
                    for _, row in import_df.iterrows():
                        lead = {
                            "business_name": str(row.get(name_col, "")) if name_col != "(skip)" else "",
                            "website": str(row.get(website_col, "")) if website_col != "(skip)" else "",
                            "email": str(row.get(email_col, "")) if email_col != "(skip)" else "",
                            "email_source": "imported",
                            "phone": str(row.get(phone_col, "")) if phone_col != "(skip)" else "",
                            "niche": str(row.get(niche_col, "")) if niche_col != "(skip)" else "",
                            "location": str(row.get(location_col, "")) if location_col != "(skip)" else "",
                            "seo_score": "", "seo_issues": "",
                            "status": "new", "notes": "",
                            "added_date": datetime.now().strftime("%Y-%m-%d"),
                        }
                        if lead["business_name"] or lead["website"] or lead["email"]:
                            new_leads.append(lead)

                    if new_leads:
                        new_df = pd.DataFrame(new_leads)
                        leads_df = load_leads()
                        leads_df = pd.concat([leads_df, new_df], ignore_index=True)
                        save_leads(leads_df)
                        st.success(f"Imported {len(new_leads)} leads!")
                    else:
                        st.warning("No valid leads found in the file.")

            except Exception as e:
                st.error(f"Error reading file: {e}")


# ============================================================
# PAGE: MY LEADS
# ============================================================
elif page == "My Leads":
    st.markdown("## My Leads")

    leads_df = load_leads()

    if len(leads_df) == 0:
        st.info("No leads yet. Go to **Find Leads** to get started.")
        st.stop()

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox("Status", ["All"] + list(leads_df["status"].fillna("new").unique()))
    with col2:
        niche_filter = st.selectbox("Niche", ["All"] + list(leads_df["niche"].dropna().unique()))
    with col3:
        location_filter = st.selectbox("Location", ["All"] + list(leads_df["location"].dropna().unique()))

    filtered = leads_df.copy()
    if status_filter != "All":
        filtered = filtered[filtered["status"].fillna("new") == status_filter]
    if niche_filter != "All":
        filtered = filtered[filtered["niche"] == niche_filter]
    if location_filter != "All":
        filtered = filtered[filtered["location"] == location_filter]

    st.markdown(f"**Showing {len(filtered)} leads**")

    # Editable table
    display_cols = ["business_name", "website", "email", "phone", "niche", "location", "seo_score", "status", "notes"]
    available_cols = [c for c in display_cols if c in filtered.columns]

    edited = st.data_editor(
        filtered[available_cols],
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "status": st.column_config.SelectboxColumn(
                "Status",
                options=["new", "contacted", "followed_up", "replied", "call_booked", "proposal_sent", "won", "lost", "do_not_contact"],
            ),
            "website": st.column_config.LinkColumn("Website"),
        },
        hide_index=True,
    )

    if st.button("Save Changes", type="primary"):
        # Update the original dataframe with edits
        for col in available_cols:
            leads_df.loc[filtered.index, col] = edited[col].values
        save_leads(leads_df)
        st.success("Changes saved!")
        st.rerun()

    # Export
    st.markdown("---")
    csv_data = filtered.to_csv(index=False)
    st.download_button("Download as CSV", csv_data, "leads_export.csv", "text/csv")


# ============================================================
# PAGE: SEO AUDIT
# ============================================================
elif page == "SEO Audit":
    st.markdown("## SEO Audit")
    st.markdown("Check any website's SEO and get findings you can use in your emails.")

    url = st.text_input("Enter website URL", placeholder="example.com")

    if st.button("Run Audit", type="primary") and url:
        if not url.startswith("http"):
            url = "https://" + url

        with st.spinner("Analyzing website..."):
            info = analyze_website(url)

        # Score display
        score = info["seo_score"]
        if score >= 80:
            score_color = "green"
        elif score >= 50:
            score_color = "orange"
        else:
            score_color = "red"

        st.markdown(f"### SEO Score: :{score_color}[{score}/100]")

        if info["seo_issues"]:
            st.markdown("### Issues Found")
            for issue in info["seo_issues"]:
                st.markdown(f"- {issue}")

            st.markdown("### Copy-Paste for Your Email")
            issues_text = "\n".join(f"- {i}" for i in info["seo_issues"])
            st.code(issues_text, language=None)
        else:
            st.success("No major SEO issues found!")

        if info["email"]:
            st.markdown(f"**Email found:** {info['email']}")
        if info["phone"]:
            st.markdown(f"**Phone found:** {info['phone']}")


# ============================================================
# PAGE: SEND EMAILS
# ============================================================
elif page == "Send Emails":
    st.markdown("## Send Cold Emails")

    if not settings.get("email_accounts"):
        st.warning("Set up your Gmail account in **Settings** first.")
        st.stop()

    leads_df = load_leads()
    sent_df = load_sent()

    # Filter leads that haven't been emailed yet
    sent_emails = set(sent_df["to_email"].tolist()) if len(sent_df) > 0 else set()
    unsent = leads_df[
        (leads_df["email"].notna()) &
        (leads_df["email"] != "") &
        (~leads_df["email"].isin(sent_emails)) &
        (leads_df["status"].fillna("new").isin(["new"]))
    ]

    st.info(f"**{len(unsent)} leads** ready to email (not yet contacted)")

    # Template selection
    template_name = st.selectbox("Choose email template", list(TEMPLATES.keys()))

    # Preview
    st.markdown("### Preview")
    if len(unsent) > 0:
        preview_lead = unsent.iloc[0]
        variables = {
            "business_name": str(preview_lead.get("business_name", "the business")),
            "website": str(preview_lead.get("website", "")),
            "niche": str(preview_lead.get("niche", "business")),
            "location": str(preview_lead.get("location", "your area")),
            "seo_issues": str(preview_lead.get("seo_issues", "a few SEO improvements")),
            "your_name": settings.get("your_name", ""),
            "your_company": settings.get("your_company", ""),
            "your_phone": settings.get("your_phone", ""),
            "your_calendly": settings.get("your_calendly", ""),
        }
        subj, body = format_template(template_name, variables)
        st.markdown(f"**To:** {preview_lead.get('email', '')}")
        st.markdown(f"**Subject:** {subj}")
        st.text_area("Email body", body, height=300, disabled=True)

    # Send controls
    st.markdown("### Send")
    col1, col2 = st.columns(2)
    with col1:
        max_to_send = st.number_input("How many to send now?", min_value=1, max_value=min(50, len(unsent)), value=min(5, len(unsent)))
    with col2:
        account = settings["email_accounts"][0]
        st.text_input("Sending from", value=account["email"], disabled=True)

    if st.button("SEND EMAILS", type="primary", use_container_width=True):
        if len(unsent) == 0:
            st.warning("No leads to email.")
        else:
            progress = st.progress(0)
            status_area = st.empty()
            results_log = []

            for i, (idx, lead) in enumerate(unsent.head(max_to_send).iterrows()):
                if i >= max_to_send:
                    break

                progress.progress((i + 1) / max_to_send)
                to_email = str(lead["email"])
                status_area.text(f"Sending {i+1}/{max_to_send}: {to_email}...")

                variables = {
                    "business_name": str(lead.get("business_name", "")),
                    "website": str(lead.get("website", "")),
                    "niche": str(lead.get("niche", "business")),
                    "location": str(lead.get("location", "")),
                    "seo_issues": str(lead.get("seo_issues", "some SEO improvements")),
                    "your_name": settings.get("your_name", ""),
                    "your_company": settings.get("your_company", ""),
                    "your_phone": settings.get("your_phone", ""),
                    "your_calendly": settings.get("your_calendly", ""),
                }

                subj, body = format_template(template_name, variables)
                success, error = send_one_email(account, to_email, subj, body)

                # Log it
                sent_record = {
                    "to_email": to_email,
                    "business_name": str(lead.get("business_name", "")),
                    "subject": subj,
                    "template": template_name,
                    "followup_num": 0,
                    "from_email": account["email"],
                    "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "sent" if success else "failed",
                }
                sent_df = load_sent()
                sent_df = pd.concat([sent_df, pd.DataFrame([sent_record])], ignore_index=True)
                save_sent(sent_df)

                # Update lead status
                leads_df = load_leads()
                leads_df.loc[leads_df["email"] == to_email, "status"] = "contacted"
                save_leads(leads_df)

                status_emoji = "sent" if success else "FAILED"
                results_log.append(f"{status_emoji} → {to_email}" + (f" ({error})" if error else ""))

                # Delay between emails
                if i < max_to_send - 1:
                    delay = random.uniform(
                        settings.get("delay_min", 45),
                        settings.get("delay_max", 120)
                    )
                    status_area.text(f"Waiting {delay:.0f}s before next email...")
                    time.sleep(delay)

            progress.progress(1.0)
            status_area.text("")

            sent_count = sum(1 for r in results_log if r.startswith("sent"))
            st.success(f"Done! Sent {sent_count}/{max_to_send} emails.")

            for r in results_log:
                if r.startswith("sent"):
                    st.markdown(f"- {r}")
                else:
                    st.markdown(f"- :red[{r}]")


# ============================================================
# PAGE: FOLLOW-UPS
# ============================================================
elif page == "Follow-ups":
    st.markdown("## Follow-ups")

    if not settings.get("email_accounts"):
        st.warning("Set up your Gmail account in **Settings** first.")
        st.stop()

    sent_df = load_sent()
    leads_df = load_leads()

    if len(sent_df) == 0:
        st.info("No emails sent yet. Go to **Send Emails** first.")
        st.stop()

    # Find follow-ups that are due
    followup_days = settings.get("followup_days", [3, 7, 14])
    due = []

    for to_email in sent_df["to_email"].unique():
        # Skip if lead marked as replied/won/lost/do_not_contact
        lead_status = ""
        if len(leads_df) > 0:
            lead_row = leads_df[leads_df["email"] == to_email]
            if len(lead_row) > 0:
                lead_status = str(lead_row.iloc[0].get("status", ""))
        if lead_status in ["replied", "won", "lost", "do_not_contact", "call_booked"]:
            continue

        emails_to = sent_df[sent_df["to_email"] == to_email].sort_values("sent_at")
        num_sent = len(emails_to)
        if num_sent >= 4:  # Initial + 3 follow-ups
            continue

        last = emails_to.iloc[-1]
        if last.get("status") == "failed":
            continue

        try:
            last_date = datetime.strptime(str(last["sent_at"])[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue

        delay_idx = min(num_sent - 1, len(followup_days) - 1)
        due_date = last_date + timedelta(days=followup_days[delay_idx])

        if datetime.now() >= due_date:
            due.append({
                "to_email": to_email,
                "business_name": str(last.get("business_name", "")),
                "followup_num": num_sent,
                "template": str(last.get("template", list(TEMPLATES.keys())[0])),
                "last_sent": str(last["sent_at"])[:10],
                "days_ago": (datetime.now() - last_date).days,
            })

    if not due:
        st.success("No follow-ups due right now. Check back later!")
        next_dates = []
        for to_email in sent_df["to_email"].unique():
            emails_to = sent_df[sent_df["to_email"] == to_email].sort_values("sent_at")
            if len(emails_to) >= 4:
                continue
            last = emails_to.iloc[-1]
            try:
                last_date = datetime.strptime(str(last["sent_at"])[:19], "%Y-%m-%d %H:%M:%S")
                delay_idx = min(len(emails_to) - 1, len(followup_days) - 1)
                nd = last_date + timedelta(days=followup_days[delay_idx])
                if nd > datetime.now():
                    next_dates.append(nd)
            except Exception:
                pass
        if next_dates:
            next_due = min(next_dates)
            st.info(f"Next follow-up due: **{next_due.strftime('%B %d, %Y')}** ({(next_due - datetime.now()).days} days from now)")
    else:
        st.warning(f"**{len(due)} follow-ups are due!**")
        due_df = pd.DataFrame(due)
        st.dataframe(due_df[["business_name", "to_email", "followup_num", "last_sent", "days_ago"]],
                     use_container_width=True, hide_index=True)

        if st.button("SEND ALL FOLLOW-UPS", type="primary", use_container_width=True):
            account = settings["email_accounts"][0]
            progress = st.progress(0)
            status_area = st.empty()
            sent_count = 0

            for i, item in enumerate(due):
                progress.progress((i + 1) / len(due))
                status_area.text(f"Following up {i+1}/{len(due)}: {item['to_email']}...")

                lead_row = leads_df[leads_df["email"] == item["to_email"]]
                lead = lead_row.iloc[0] if len(lead_row) > 0 else {}

                variables = {
                    "business_name": str(item.get("business_name", "")),
                    "website": str(lead.get("website", "")) if isinstance(lead, pd.Series) else "",
                    "niche": str(lead.get("niche", "business")) if isinstance(lead, pd.Series) else "business",
                    "location": str(lead.get("location", "")) if isinstance(lead, pd.Series) else "",
                    "seo_issues": str(lead.get("seo_issues", "")) if isinstance(lead, pd.Series) else "",
                    "your_name": settings.get("your_name", ""),
                    "your_company": settings.get("your_company", ""),
                    "your_phone": settings.get("your_phone", ""),
                    "your_calendly": settings.get("your_calendly", ""),
                }

                template_name_fu = item["template"] if item["template"] in TEMPLATES else list(TEMPLATES.keys())[0]
                subj, body = format_template(template_name_fu, variables, followup_num=item["followup_num"])

                success, error = send_one_email(account, item["to_email"], subj, body)

                sent_record = {
                    "to_email": item["to_email"],
                    "business_name": item["business_name"],
                    "subject": subj,
                    "template": template_name_fu,
                    "followup_num": item["followup_num"],
                    "from_email": account["email"],
                    "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "sent" if success else "failed",
                }
                sent_df_updated = load_sent()
                sent_df_updated = pd.concat([sent_df_updated, pd.DataFrame([sent_record])], ignore_index=True)
                save_sent(sent_df_updated)

                if success:
                    sent_count += 1
                    leads_df.loc[leads_df["email"] == item["to_email"], "status"] = "followed_up"
                    save_leads(leads_df)

                if i < len(due) - 1:
                    delay = random.uniform(settings.get("delay_min", 45), settings.get("delay_max", 120))
                    status_area.text(f"Waiting {delay:.0f}s...")
                    time.sleep(delay)

            progress.progress(1.0)
            status_area.text("")
            st.success(f"Sent {sent_count}/{len(due)} follow-ups!")
            st.rerun()


# ============================================================
# PAGE: BACKUP & RESTORE
# ============================================================
elif page == "Backup & Restore":
    st.markdown("## Backup & Restore")
    st.markdown("Download your data regularly so you never lose it.")

    st.markdown("### Download Backup")
    col1, col2, col3 = st.columns(3)

    with col1:
        leads_df_bk = load_leads()
        if len(leads_df_bk) > 0:
            st.download_button(
                f"Download Leads ({len(leads_df_bk)})",
                leads_df_bk.to_csv(index=False),
                f"leads_backup_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                use_container_width=True,
            )
        else:
            st.info("No leads to backup")

    with col2:
        sent_df_bk = load_sent()
        if len(sent_df_bk) > 0:
            st.download_button(
                f"Download Sent Emails ({len(sent_df_bk)})",
                sent_df_bk.to_csv(index=False),
                f"sent_backup_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                use_container_width=True,
            )
        else:
            st.info("No sent emails to backup")

    with col3:
        settings_bk = load_settings()
        settings_copy = {k: v for k, v in settings_bk.items()}
        # Hide passwords in backup
        for acc in settings_copy.get("email_accounts", []):
            acc["password"] = "***HIDDEN***"
        st.download_button(
            "Download Settings",
            json.dumps(settings_copy, indent=2),
            "settings_backup.json",
            "application/json",
            use_container_width=True,
        )

    st.markdown("---")
    st.markdown("### Restore from Backup")

    restore_tab1, restore_tab2 = st.tabs(["Restore Leads", "Restore Sent Emails"])

    with restore_tab1:
        uploaded_leads = st.file_uploader("Upload leads CSV backup", type=["csv"], key="restore_leads")
        if uploaded_leads:
            try:
                restored = pd.read_csv(uploaded_leads)
                st.markdown(f"Found **{len(restored)} leads** in backup")
                st.dataframe(restored.head(5), use_container_width=True, hide_index=True)
                if st.button("Restore These Leads", type="primary"):
                    existing = load_leads()
                    combined = pd.concat([existing, restored], ignore_index=True)
                    combined = combined.drop_duplicates(subset=["email", "website"], keep="last")
                    save_leads(combined)
                    st.success(f"Restored! Total leads now: {len(combined)}")
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    with restore_tab2:
        uploaded_sent = st.file_uploader("Upload sent emails CSV backup", type=["csv"], key="restore_sent")
        if uploaded_sent:
            try:
                restored_sent = pd.read_csv(uploaded_sent)
                st.markdown(f"Found **{len(restored_sent)} sent records** in backup")
                if st.button("Restore Sent Records", type="primary"):
                    existing_sent = load_sent()
                    combined_sent = pd.concat([existing_sent, restored_sent], ignore_index=True)
                    combined_sent = combined_sent.drop_duplicates(subset=["to_email", "sent_at"], keep="last")
                    save_sent(combined_sent)
                    st.success(f"Restored! Total sent records: {len(combined_sent)}")
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")


# ============================================================
# PAGE: SETTINGS
# ============================================================
elif page == "Settings":
    st.markdown("## Settings")

    with st.form("settings_form"):
        st.markdown("### About You")
        col1, col2 = st.columns(2)
        with col1:
            your_name = st.text_input("Your Name *", value=settings.get("your_name", ""))
            your_company = st.text_input("Company Name", value=settings.get("your_company", ""))
            your_phone = st.text_input("Phone", value=settings.get("your_phone", ""))
        with col2:
            your_website = st.text_input("Website", value=settings.get("your_website", ""))
            your_calendly = st.text_input("Calendly Link (free at calendly.com)", value=settings.get("your_calendly", ""))

        st.markdown("---")
        st.markdown("### Gmail Account for Sending")
        st.markdown("""
        **How to get your App Password (one-time setup):**
        1. Go to [myaccount.google.com](https://myaccount.google.com)
        2. Click **Security** on the left
        3. Turn on **2-Step Verification** if not already on
        4. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
        5. Type **Mail** as the app name, click **Create**
        6. Copy the 16-character password and paste below
        """)

        existing_accounts = settings.get("email_accounts", [{}])
        if not existing_accounts:
            existing_accounts = [{}]
        acc = existing_accounts[0]

        col1, col2 = st.columns(2)
        with col1:
            gmail_addr = st.text_input("Gmail Address", value=acc.get("email", ""))
        with col2:
            gmail_pass = st.text_input("App Password", value=acc.get("password", ""), type="password")

        st.markdown("---")
        st.markdown("### Sending Settings")
        col1, col2, col3 = st.columns(3)
        with col1:
            daily_limit = st.number_input("Max emails per day", min_value=1, max_value=50, value=settings.get("daily_limit", 5))
        with col2:
            delay_min = st.number_input("Min delay between emails (sec)", min_value=10, max_value=300, value=settings.get("delay_min", 45))
        with col3:
            delay_max = st.number_input("Max delay between emails (sec)", min_value=30, max_value=600, value=settings.get("delay_max", 120))

        st.markdown("---")
        st.markdown("### Target Settings")
        niches_text = st.text_area(
            "Target niches (one per line)",
            value="\n".join(settings.get("target_niches", ["dentist"])),
        )
        locations_text = st.text_area(
            "Target cities (one per line)",
            value="\n".join(settings.get("target_locations", ["Hyderabad"])),
        )

        saved = st.form_submit_button("Save Settings", type="primary", use_container_width=True)

        if saved:
            new_settings = {
                "your_name": your_name,
                "your_company": your_company,
                "your_phone": your_phone,
                "your_website": your_website,
                "your_calendly": your_calendly,
                "email_accounts": [{
                    "email": gmail_addr,
                    "password": gmail_pass,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "name": your_name,
                }] if gmail_addr else [],
                "daily_limit": daily_limit,
                "delay_min": delay_min,
                "delay_max": delay_max,
                "target_niches": [n.strip() for n in niches_text.split("\n") if n.strip()],
                "target_locations": [l.strip() for l in locations_text.split("\n") if l.strip()],
                "followup_days": settings.get("followup_days", [3, 7, 14]),
            }
            save_settings(new_settings)
            st.session_state.settings = new_settings
            st.success("Settings saved!")

    # Test email button
    st.markdown("---")
    st.markdown("### Test Your Email Setup")
    test_to = st.text_input("Send test email to", placeholder="your-other-email@gmail.com")
    if st.button("Send Test Email") and test_to:
        if not settings.get("email_accounts"):
            st.error("Save your Gmail settings first!")
        else:
            with st.spinner("Sending test email..."):
                acc = settings["email_accounts"][0]
                success, error = send_one_email(
                    acc, test_to,
                    "Test from SEO Cold Email System",
                    f"Hi! This is a test email from your cold email system.\n\nIf you're reading this, your setup is working perfectly!\n\n- {settings.get('your_name', 'Your Name')}"
                )
            if success:
                st.success(f"Test email sent to {test_to}! Check your inbox.")
            else:
                st.error(f"Failed: {error}")
