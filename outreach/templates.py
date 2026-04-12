"""8 Cold Email Templates — 4 original + 4 new high-ticket focused."""

import re

TEMPLATES = {
    # ─── TEMPLATE 1: SEO Audit Findings (Original) ───
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

    # ─── TEMPLATE 2: Competitor Comparison (Original) ───
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

    # ─── TEMPLATE 3: Value First / Free Tip (Original) ───
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

    # ─── TEMPLATE 4: Case Study (Original) ───
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

    # ─── TEMPLATE 5: Google Maps Focus (NEW) ───
    "Google Maps Focus": {
        "subjects": [
            "{business_name} — your Google Maps listing needs this",
            "People can't find {business_name} on Google Maps",
        ],
        "body": """Hi{name_greeting},

I searched for "{niche} in {location}" on Google Maps and noticed {business_name} isn't showing up in the top results.

This matters because 76% of people who search for a local business on their phone visit within 24 hours.

The good news: getting into the Google Maps 3-pack (the top 3 results) for a {niche} in {location} is very doable with a few specific optimizations.

I help local businesses like yours get found on Google Maps. Would a quick 10-minute chat about your listing be useful?

{signature}""",
        "followups": [
            """Hi{name_greeting},

Just following up on the Google Maps visibility for {business_name}.

I checked and there are 3-4 quick things you could do this week to start showing up higher on Maps:

1. Optimize your Google Business Profile categories
2. Add more photos (businesses with 100+ photos get 520% more calls)
3. Get responses to your reviews

Want me to walk you through the details?

{signature}""",
            """Hi{name_greeting},

Last follow-up on this — getting {business_name} into the Google Maps 3-pack could mean 10-20+ extra calls per month.

If you'd like a free Google Maps audit, just reply "yes" and I'll send it over.

{signature}""",
            """Hi{name_greeting},

Last note from me. If Google Maps visibility becomes a priority for {business_name}, feel free to reach out anytime.

Best,
{your_name}""",
        ],
    },

    # ─── TEMPLATE 6: Revenue Loss Calculator (NEW) ───
    "Revenue Loss Calculator": {
        "subjects": [
            "{business_name} is leaving money on the table",
            "How much is {business_name} losing to Google?",
        ],
        "body": """Hi{name_greeting},

I ran some quick numbers on {business_name}'s online presence:

- "{niche} in {location}" gets ~500+ searches/month on Google
- The #1 result gets ~30% of those clicks (150+ potential customers)
- For a {niche}, each new client is worth $500-2,000+

That's potentially $75,000-300,000/year in revenue that's going to your competitors instead.

I looked at {website} and found a few things holding you back:

{seo_issues}

These are fixable. Would a quick call make sense to discuss what's possible?

{signature}""",
        "followups": [
            """Hi{name_greeting},

Following up on my email about the revenue {business_name} could be getting from Google.

Even capturing 10% more of the local search traffic for "{niche} in {location}" could mean significant growth.

Would it help if I put together specific numbers for your market?

{signature}""",
            """Hi{name_greeting},

I'll keep this short — the {niche}s ranking above {business_name} on Google are getting the calls that should be going to you.

If you want to see exactly how many, I can send you a free market analysis.

{signature}""",
            """Hi{name_greeting},

This will be my last email. If revenue from Google becomes a focus for {business_name}, I'm here to help.

Best,
{your_name}""",
        ],
    },

    # ─── TEMPLATE 7: Quick Question (NEW — ultra short) ───
    "Quick Question": {
        "subjects": [
            "Quick question for {business_name}",
            "{business_name} — 30 second question",
        ],
        "body": """Hi{name_greeting},

Quick question: is getting more leads from Google something {business_name} is focused on this year?

I noticed {website} has some easy opportunities to rank higher for "{niche} in {location}" searches.

If yes — I have some ideas I'd love to share. If not — no worries at all.

{signature}""",
        "followups": [
            """Hi{name_greeting},

Just bumping this to the top of your inbox.

Is Google visibility on the radar for {business_name}?

{signature}""",
            """Hi{name_greeting},

Last try — if getting more Google leads for {business_name} is ever a priority, just reply to this email. I'll still have my notes on {website}.

Cheers,
{your_name}""",
        ],
    },

    # ─── TEMPLATE 8: Industry Report (NEW) ───
    "Industry Report": {
        "subjects": [
            "2025 SEO report for {niche}s in {location}",
            "What's working for {niche}s on Google right now",
        ],
        "body": """Hi{name_greeting},

I just finished analyzing the top-ranking {niche}s in {location} on Google, and I wanted to share a few findings:

1. Most {niche}s in {location} score below 60/100 on basic SEO
2. Only ~30% have their Google Business Profile fully optimized
3. The top 3 are getting 80%+ of all local search traffic

I checked {website} and {business_name} has room to move up significantly.

I put together a short report on what the top {niche}s in {location} are doing right. Want me to send it over? It's free.

{signature}""",
        "followups": [
            """Hi{name_greeting},

Following up on the {niche} industry report for {location}.

The insights are time-sensitive — Google's algorithm changes mean the window to move up is best right now before competitors catch on.

Want the report? Just reply "send it."

{signature}""",
            """Hi{name_greeting},

Last follow-up. The {niche} market report for {location} is ready whenever you'd like it.

If now isn't the right time, no worries. Feel free to reach out when it is.

Best,
{your_name}""",
        ],
    },
}


def format_template(template_name, variables, followup_num=0):
    """Format a template with variables. Returns (subject, body)."""
    tmpl = TEMPLATES.get(template_name)
    if not tmpl:
        tmpl = list(TEMPLATES.values())[0]

    # Name greeting
    name = variables.get("business_name", "").split()[0] if variables.get("business_name") else ""
    variables["name_greeting"] = f" {name}" if name else ""

    # Build signature
    sig_parts = [variables.get("your_name", "")]
    if variables.get("your_company"):
        sig_parts.append(variables["your_company"])
    if variables.get("your_phone"):
        sig_parts.append(variables["your_phone"])
    if variables.get("your_calendly"):
        sig_parts.append(f"\nP.S. Book a time here: {variables['your_calendly']}")
    variables["signature"] = "\n".join(sig_parts)

    # Select body and subject
    if followup_num == 0:
        body = tmpl["body"]
        subject = tmpl["subjects"][0]
    else:
        followups = tmpl.get("followups", [])
        idx = min(followup_num - 1, len(followups) - 1)
        body = followups[idx] if followups else tmpl["body"]
        subject = "Re: " + tmpl["subjects"][0]

    # Replace variables
    for key, val in variables.items():
        body = body.replace(f"{{{key}}}", str(val))
        subject = subject.replace(f"{{{key}}}", str(val))

    # Clean up unreplaced variables
    body = re.sub(r'\{[a-z_]+\}', '', body)
    subject = re.sub(r'\{[a-z_]+\}', '', subject)

    # Add unsubscribe text if not already present
    try:
        from core.compliance import add_unsubscribe_link
        body = add_unsubscribe_link(body)
    except ImportError:
        pass

    return subject.strip(), body.strip()


def template_names():
    """Return list of all template names."""
    return list(TEMPLATES.keys())
