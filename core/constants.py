"""Constants — columns, statuses, niche profiles, scoring weights."""

LEAD_COLUMNS = [
    "business_name", "website", "email", "email_source", "phone",
    "niche", "location", "seo_score", "seo_issues", "lead_score",
    "lead_grade", "status", "notes", "added_date", "source",
]

SENT_COLUMNS = [
    "to_email", "business_name", "subject", "template",
    "followup_num", "from_email", "sent_at", "status",
]

LEAD_STATUSES = [
    "new", "contacted", "followed_up", "replied",
    "call_booked", "proposal_sent", "won", "lost", "do_not_contact",
]

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]

SKIP_DOMAINS = [
    "google.", "youtube.", "facebook.", "yelp.", "linkedin.",
    "instagram.", "twitter.", "wikipedia.", "amazon.", "justdial.",
    "sulekha.", "practo.", "indiamart.", "quora.", "reddit.",
    "duckduckgo.", "tripadvisor.", "naukri.", "glassdoor.",
    "yellowpages.", "bbb.", "tiktok.", "pinterest.",
    "bing.", "yahoo.", "tradeindia.",
]

# Scoring weights for lead scoring (total = 100)
SCORING_WEIGHTS = {
    "industry_value": 25,       # Based on niche avg deal value
    "seo_opportunity": 25,      # Inverse of SEO quality
    "budget_signals": 20,       # Google Ads, Analytics, custom domain
    "business_maturity": 15,    # Blog, team page, multi-location
    "engagement_readiness": 15, # Real email, contact form, named person
}

# Niche profiles with avg deal values and pain points
NICHE_PROFILES = {
    "dentist": {
        "display_name": "Dentist / Dental Clinic",
        "avg_deal_value": 2000,
        "tier": "high",
        "pain_points": [
            "New patient acquisition from Google",
            "Competing with corporate dental chains",
            "Google Maps visibility",
        ],
        "search_queries": [
            "dentist", "dental clinic", "dental office", "family dentist",
            "cosmetic dentist", "dental implants",
        ],
    },
    "plastic_surgeon": {
        "display_name": "Plastic Surgeon / Med Spa",
        "avg_deal_value": 5000,
        "tier": "premium",
        "pain_points": [
            "High-value procedure bookings",
            "Trust and credibility online",
            "Competing for 'near me' searches",
        ],
        "search_queries": [
            "plastic surgeon", "cosmetic surgery", "med spa", "medspa",
            "botox", "liposuction", "facelift",
        ],
    },
    "lawyer": {
        "display_name": "Law Firm / Attorney",
        "avg_deal_value": 5000,
        "tier": "premium",
        "pain_points": [
            "Expensive PPC costs ($50-200/click)",
            "Local search visibility",
            "Client trust and reviews",
        ],
        "search_queries": [
            "lawyer", "attorney", "law firm", "legal services",
            "personal injury lawyer", "family lawyer", "criminal defense attorney",
        ],
    },
    "real_estate": {
        "display_name": "Real Estate Agent / Broker",
        "avg_deal_value": 3000,
        "tier": "high",
        "pain_points": [
            "Lead generation beyond Zillow/Realtor.com",
            "Personal brand visibility",
            "Neighborhood authority",
        ],
        "search_queries": [
            "real estate agent", "realtor", "real estate broker",
            "property dealer", "homes for sale",
        ],
    },
    "chiropractor": {
        "display_name": "Chiropractor",
        "avg_deal_value": 1500,
        "tier": "medium",
        "pain_points": [
            "New patient acquisition",
            "Competing with other wellness providers",
            "Google Maps ranking",
        ],
        "search_queries": [
            "chiropractor", "chiropractic", "back pain treatment",
            "spine adjustment",
        ],
    },
    "plumber": {
        "display_name": "Plumber / Plumbing Company",
        "avg_deal_value": 1500,
        "tier": "medium",
        "pain_points": [
            "Emergency search visibility",
            "Competing with HomeAdvisor/Angi leads",
            "Service area coverage",
        ],
        "search_queries": [
            "plumber", "plumbing service", "emergency plumber",
            "drain cleaning", "water heater repair",
        ],
    },
    "roofing": {
        "display_name": "Roofing Contractor",
        "avg_deal_value": 3000,
        "tier": "high",
        "pain_points": [
            "High-ticket project leads",
            "Storm damage searches",
            "Trust and reviews for big purchases",
        ],
        "search_queries": [
            "roofing contractor", "roof repair", "roof replacement",
            "roofing company", "roofer",
        ],
    },
    "hvac": {
        "display_name": "HVAC Contractor",
        "avg_deal_value": 2000,
        "tier": "high",
        "pain_points": [
            "Seasonal search demand",
            "Emergency service visibility",
            "Competing with big franchises",
        ],
        "search_queries": [
            "hvac contractor", "air conditioning repair", "heating repair",
            "ac installation", "furnace repair",
        ],
    },
    "electrician": {
        "display_name": "Electrician",
        "avg_deal_value": 1500,
        "tier": "medium",
        "pain_points": [
            "Emergency electrical service searches",
            "Commercial vs residential leads",
            "Service area visibility",
        ],
        "search_queries": [
            "electrician", "electrical contractor", "electrical repair",
            "wiring service",
        ],
    },
    "medical_practice": {
        "display_name": "Doctor / Medical Practice",
        "avg_deal_value": 3000,
        "tier": "high",
        "pain_points": [
            "Patient acquisition cost",
            "Competing with hospital networks",
            "Specialty-specific searches",
        ],
        "search_queries": [
            "doctor", "medical clinic", "physician", "family doctor",
            "specialist", "healthcare",
        ],
    },
    "gym_fitness": {
        "display_name": "Gym / Fitness Studio",
        "avg_deal_value": 1000,
        "tier": "medium",
        "pain_points": [
            "Local membership acquisition",
            "Competing with big chains",
            "Class and program visibility",
        ],
        "search_queries": [
            "gym", "fitness studio", "personal trainer", "yoga studio",
            "crossfit", "pilates",
        ],
    },
    "restaurant": {
        "display_name": "Restaurant / Cafe",
        "avg_deal_value": 800,
        "tier": "standard",
        "pain_points": [
            "Google Maps and 'near me' searches",
            "Online ordering visibility",
            "Review management",
        ],
        "search_queries": [
            "restaurant", "cafe", "catering", "food delivery",
        ],
    },
}
