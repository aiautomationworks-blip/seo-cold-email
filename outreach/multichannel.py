"""Multi-channel outreach — LinkedIn and WhatsApp message generators."""

import urllib.parse


def generate_linkedin_message(lead_data, settings):
    """Generate a LinkedIn connection request message (300 char limit)."""
    biz_name = str(lead_data.get("business_name", "your business"))
    niche = str(lead_data.get("niche", "business"))
    location = str(lead_data.get("location", "your area"))
    your_name = settings.get("your_name", "")

    messages = {
        "Connection Request": f"Hi! I came across {biz_name} and was impressed. I help {niche}s in {location} get more leads from Google. Would love to connect and share some insights I found about your online presence. - {your_name}",

        "Short & Casual": f"Hi! Quick one — I noticed a few things on {biz_name}'s Google presence that could bring in more leads. Happy to share if you're interested. No pitch! - {your_name}",

        "Value-First": f"Hi! I just analyzed the top {niche}s on Google in {location}. {biz_name} has solid potential but is missing a few things the top-ranked ones have. Want me to share what I found? - {your_name}",
    }

    # Truncate to LinkedIn's 300 char limit
    return {name: msg[:300] for name, msg in messages.items()}


def generate_whatsapp_message(lead_data, settings):
    """Generate WhatsApp messages and click-to-chat links."""
    biz_name = str(lead_data.get("business_name", "your business"))
    niche = str(lead_data.get("niche", "business"))
    location = str(lead_data.get("location", "your area"))
    website = str(lead_data.get("website", ""))
    phone = str(lead_data.get("phone", ""))
    your_name = settings.get("your_name", "")

    messages = {
        "Introduction": f"""Hi! I'm {your_name}. I help {niche}s in {location} get more leads from Google.

I took a look at {website} and noticed a few things that could help {biz_name} show up higher in search results.

Would you be open to a quick chat about it? No charge, just sharing what I see.""",

        "Quick Value": f"""Hi! Quick question — is getting more leads from Google something {biz_name} is focused on?

I noticed {website} has some easy opportunities to rank higher. Happy to share if interested!

- {your_name}""",

        "Follow-up": f"""Hi! I sent an email about some SEO findings for {biz_name} but wanted to reach out here too.

The short version: there are 3-4 quick fixes that could help {website} get more Google traffic.

Would a quick 10-min call work? I can share what I found. - {your_name}""",
    }

    # Generate WhatsApp click-to-chat links
    links = {}
    if phone:
        clean_phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if not clean_phone.startswith("+"):
            clean_phone = "+91" + clean_phone  # Default to India
        for name, msg in messages.items():
            encoded = urllib.parse.quote(msg)
            links[name] = f"https://wa.me/{clean_phone}?text={encoded}"

    return {"messages": messages, "links": links}


def generate_follow_up_schedule(lead_data):
    """Generate a multi-channel follow-up schedule."""
    biz_name = str(lead_data.get("business_name", "Business"))
    return [
        {"day": 1, "channel": "Email", "action": f"Send initial cold email to {biz_name}"},
        {"day": 3, "channel": "LinkedIn", "action": f"Send LinkedIn connection request to {biz_name}"},
        {"day": 4, "channel": "Email", "action": f"Follow-up email #1 to {biz_name}"},
        {"day": 6, "channel": "WhatsApp", "action": f"Send WhatsApp message to {biz_name} (if phone available)"},
        {"day": 8, "channel": "Email", "action": f"Follow-up email #2 to {biz_name}"},
        {"day": 14, "channel": "Email", "action": f"Final follow-up email to {biz_name}"},
        {"day": 15, "channel": "LinkedIn", "action": f"LinkedIn follow-up message to {biz_name}"},
    ]
