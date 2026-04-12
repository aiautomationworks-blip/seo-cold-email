"""
Cold Email Templates for SEO Services
Each template has: subject, body, and follow-ups.
Variables: {name}, {business_name}, {website}, {niche}, {location},
           {seo_issues}, {specific_fix}, {seo_score}, {your_name},
           {your_company}, {your_phone}, {your_calendly}, {your_website}
"""

# ============================================================
# TEMPLATE 1: The "I Found Something" Approach
# Best for: Leads where you found specific SEO issues
# ============================================================
TEMPLATE_SEO_AUDIT = {
    "id": "seo_audit",
    "name": "SEO Audit Findings",
    "subject_lines": [
        "Quick question about {website}",
        "{business_name} — found something on your site",
        "Noticed something about {business_name}'s Google presence",
    ],
    "body": """Hi{name_greeting},

I was looking at {website} and noticed a few things that are likely costing you leads from Google:

{seo_issues}

These are quick fixes that could help you show up higher when people search for "{niche} in {location}."

I help {niche}s in {location} get more calls and bookings from Google — without paid ads.

Would it make sense to jump on a quick 10-min call this week so I can walk you through what I found? No pitch, just sharing what I see.

{signature}""",

    "followup_1": """Hi{name_greeting},

Just following up on my email from a few days ago about {website}.

The issues I found ({specific_fix}) are the kind of thing that gets worse over time as competitors fix theirs.

Happy to share my findings in a quick call — completely free, no strings attached.

{signature}""",

    "followup_2": """Hi{name_greeting},

I'll keep this short — I sent over some SEO findings about {website} last week.

If you're curious, I put together a quick list of the top 3 things I'd fix first to get {business_name} ranking higher on Google.

Want me to send it over?

{signature}""",

    "followup_3": """Hi{name_greeting},

Last note from me — I don't want to be a pest.

If improving {business_name}'s Google rankings is on your radar at any point, feel free to reach out. I'll still have my notes on your site.

Wishing you all the best,
{your_name}""",
}


# ============================================================
# TEMPLATE 2: The "Competitor" Approach
# Best for: Competitive niches where you can reference competitors
# ============================================================
TEMPLATE_COMPETITOR = {
    "id": "competitor",
    "name": "Competitor Comparison",
    "subject_lines": [
        "How {business_name} compares to other {niche}s on Google",
        "{business_name} vs. competitors on Google — quick insight",
        "Your competitors in {location} are doing this",
    ],
    "body": """Hi{name_greeting},

I was researching {niche}s in {location} and noticed something interesting.

Some of your competitors are showing up above {business_name} on Google for searches like "{niche} near me" and "{niche} in {location}" — and it's not because they're better. They just have their website set up to rank.

A few quick changes to {website} could help you compete with (and pass) them.

Would you be open to a 10-minute call where I can show you exactly what they're doing differently? No cost, no obligation.

{signature}""",

    "followup_1": """Hi{name_greeting},

Following up on my email about {business_name}'s Google visibility.

I looked a bit deeper and there are 2-3 specific things your top-ranking competitors have on their sites that {website} is missing.

Would a quick email breakdown be helpful, or would you prefer to chat?

{signature}""",

    "followup_2": """Hi{name_greeting},

Quick one — I know you're busy running a business.

If you ever want to see exactly how {business_name} stacks up against other {niche}s on Google in {location}, I'm happy to put together a free comparison.

Just reply "interested" and I'll send it over.

{signature}""",

    "followup_3": """Hi{name_greeting},

Last email from me on this — I know timing is everything.

If getting more leads from Google becomes a priority for {business_name}, I'm here. Feel free to reach out anytime.

Best,
{your_name}""",
}


# ============================================================
# TEMPLATE 3: The "Value First" Approach
# Best for: Higher-ticket niches (lawyers, doctors, etc.)
# ============================================================
TEMPLATE_VALUE_FIRST = {
    "id": "value_first",
    "name": "Value First (Free Tip)",
    "subject_lines": [
        "Free tip to get {business_name} more Google calls",
        "One thing I'd change on {website} today",
        "Quick SEO win for {business_name}",
    ],
    "body": """Hi{name_greeting},

I'll get straight to it — here's one free thing you can do today to get more calls from Google:

{specific_fix}

This alone won't put you at #1, but it's a quick win most {niche}s in {location} overlook.

I specialize in helping {niche}s rank higher on Google and get more bookings. If you'd like, I can do a full (free) review of {website} and share 3-5 more improvements.

Worth a quick chat?

{signature}""",

    "followup_1": """Hi{name_greeting},

Just wanted to check — did you get a chance to look at the SEO tip I sent for {website}?

If it was helpful, I have a few more specific to {niche}s in {location} that could make a real difference.

Happy to share them on a quick call or over email — whatever works.

{signature}""",

    "followup_2": """Hi{name_greeting},

Last follow-up on this — I put together a short SEO checklist specifically for {niche}s that want more calls from Google.

Want me to send it your way? It's free and takes about 15 minutes to go through.

{signature}""",

    "followup_3": """Hi{name_greeting},

I'll leave it here. If you ever want a fresh set of eyes on {business_name}'s Google presence, just reply and I'll be happy to help.

Cheers,
{your_name}""",
}


# ============================================================
# TEMPLATE 4: The "Case Study" Approach
# Best when: You have results to share (even from your own site)
# ============================================================
TEMPLATE_CASE_STUDY = {
    "id": "case_study",
    "name": "Case Study / Social Proof",
    "subject_lines": [
        "How a {niche} in {location} got 3x more Google calls",
        "This {niche} went from page 5 to page 1 — here's how",
        "{niche} in {location}? Here's what's working right now",
    ],
    "body": """Hi{name_greeting},

I recently helped a {niche} go from barely showing up on Google to ranking on the first page for their main keywords.

Within 90 days they saw:
- 3x increase in calls from Google
- First page rankings for "[niche] + [city]" searches
- 40% more website visitors from organic search

I took a look at {website} and I see similar potential for {business_name}.

Would you be open to a quick chat about what that could look like for you?

{signature}""",

    "followup_1": """Hi{name_greeting},

Just circling back on my email about getting {business_name} more visibility on Google.

The strategies I used for other {niche}s in the area work especially well right now because most local businesses haven't caught up yet.

Would a 10-minute call this week work?

{signature}""",

    "followup_2": """Hi{name_greeting},

I wanted to share one more thing — the {niche} I mentioned saw most of their results in the first 60-90 days because we focused on quick wins first.

If you're interested, I can share exactly which quick wins would apply to {business_name}.

{signature}""",

    "followup_3": """Hi{name_greeting},

I don't want to keep filling your inbox, so this will be my last note.

If you ever want to explore getting more leads from Google for {business_name}, feel free to reach out. I'll still have my analysis of {website} on file.

All the best,
{your_name}""",
}


# ============================================================
# Signature templates
# ============================================================
SIGNATURE_CASUAL = """{your_name}
{your_company}
{your_phone}"""

SIGNATURE_WITH_CALENDLY = """{your_name}
{your_company}

P.S. If you want to skip the back-and-forth, feel free to grab a time here: {your_calendly}"""

SIGNATURE_MINIMAL = """Best,
{your_name}
{your_phone}"""


# ============================================================
# All templates in a list for easy access
# ============================================================
ALL_TEMPLATES = [
    TEMPLATE_SEO_AUDIT,
    TEMPLATE_COMPETITOR,
    TEMPLATE_VALUE_FIRST,
    TEMPLATE_CASE_STUDY,
]


def get_template(template_id):
    """Get a template by ID."""
    for t in ALL_TEMPLATES:
        if t["id"] == template_id:
            return t
    return ALL_TEMPLATES[0]


def format_email(template, variables, followup_num=0, signature_style="calendly"):
    """
    Format an email template with variables.
    followup_num: 0 = initial email, 1-3 = follow-ups
    """
    # Select signature
    if signature_style == "calendly":
        sig = SIGNATURE_WITH_CALENDLY
    elif signature_style == "casual":
        sig = SIGNATURE_CASUAL
    else:
        sig = SIGNATURE_MINIMAL

    # Format name greeting
    name = variables.get("name", "").strip()
    variables["name_greeting"] = f" {name}" if name else ""

    variables["signature"] = sig

    # Select body
    if followup_num == 0:
        body = template["body"]
        subject = template["subject_lines"][0]
    elif followup_num == 1:
        body = template.get("followup_1", template["body"])
        subject = "Re: " + template["subject_lines"][0]
    elif followup_num == 2:
        body = template.get("followup_2", template["body"])
        subject = "Re: " + template["subject_lines"][0]
    else:
        body = template.get("followup_3", template["body"])
        subject = "Re: " + template["subject_lines"][0]

    # Replace all variables
    for key, value in variables.items():
        body = body.replace(f"{{{key}}}", str(value))
        subject = subject.replace(f"{{{key}}}", str(value))

    # Clean up any unreplaced variables
    import re
    body = re.sub(r'\{[a-z_]+\}', '', body)
    subject = re.sub(r'\{[a-z_]+\}', '', subject)

    return subject.strip(), body.strip()
