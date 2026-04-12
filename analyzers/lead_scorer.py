"""Lead Scorer — 5-category scoring system (0-100) for identifying high-ticket prospects."""

import re

from core.constants import NICHE_PROFILES, SCORING_WEIGHTS


def score_lead(lead_data, audit_data=None, tech_data=None):
    """
    Score a lead from 0-100 across 5 categories.

    Args:
        lead_data: dict with business_name, website, email, niche, seo_score, seo_issues, etc.
        audit_data: optional SEO audit results
        tech_data: optional tech detection results

    Returns:
        dict with total_score, grade, breakdown, and recommendation
    """
    breakdown = {
        "industry_value": 0,
        "seo_opportunity": 0,
        "budget_signals": 0,
        "business_maturity": 0,
        "engagement_readiness": 0,
    }

    niche = str(lead_data.get("niche", "")).lower().replace(" ", "_")
    website = str(lead_data.get("website", ""))
    email = str(lead_data.get("email", ""))
    seo_score = _safe_int(lead_data.get("seo_score", 50))
    seo_issues = str(lead_data.get("seo_issues", ""))

    # ─── 1. Industry Value (0-25) ───
    profile = _find_niche_profile(niche)
    if profile:
        tier = profile.get("tier", "standard")
        if tier == "premium":
            breakdown["industry_value"] = 25
        elif tier == "high":
            breakdown["industry_value"] = 20
        elif tier == "medium":
            breakdown["industry_value"] = 15
        else:
            breakdown["industry_value"] = 10
    else:
        breakdown["industry_value"] = 12  # Unknown niche, give moderate score

    # ─── 2. SEO Opportunity (0-25) — inverse of SEO quality ───
    if seo_score == 0:
        breakdown["seo_opportunity"] = 10  # Site might be down
    elif seo_score <= 30:
        breakdown["seo_opportunity"] = 25  # Terrible SEO = huge opportunity
    elif seo_score <= 50:
        breakdown["seo_opportunity"] = 20
    elif seo_score <= 70:
        breakdown["seo_opportunity"] = 15
    elif seo_score <= 85:
        breakdown["seo_opportunity"] = 10
    else:
        breakdown["seo_opportunity"] = 5  # Good SEO = less opportunity

    # Bonus for specific high-impact issues
    issue_lower = seo_issues.lower()
    if "no ssl" in issue_lower or "no https" in issue_lower:
        breakdown["seo_opportunity"] = min(25, breakdown["seo_opportunity"] + 3)
    if "not mobile" in issue_lower:
        breakdown["seo_opportunity"] = min(25, breakdown["seo_opportunity"] + 3)

    # ─── 3. Budget Signals (0-20) ───
    if tech_data:
        # Google Ads pixel present = they spend on marketing
        if tech_data.get("has_google_ads"):
            breakdown["budget_signals"] += 8
        # Google Analytics = they track metrics
        if tech_data.get("has_analytics"):
            breakdown["budget_signals"] += 5
        # Custom domain email = professional
        if tech_data.get("has_custom_email"):
            breakdown["budget_signals"] += 4
        # CMS detected = someone maintains it
        if tech_data.get("cms"):
            breakdown["budget_signals"] += 3
    else:
        # Estimate from available data
        if website and "." in website:
            domain = website.split("//")[-1].split("/")[0].replace("www.", "")
            # Custom domain (not free hosting)
            if not any(free in domain for free in [
                "wordpress.com", "wix.com", "weebly.com", "blogspot.",
                "squarespace.com", "godaddy.com", "freesite",
            ]):
                breakdown["budget_signals"] += 8
            else:
                breakdown["budget_signals"] += 3

        # Has a real email (not guessed)
        email_source = str(lead_data.get("email_source", ""))
        if email_source == "found":
            breakdown["budget_signals"] += 5
        elif email and "@" in email:
            breakdown["budget_signals"] += 3

    breakdown["budget_signals"] = min(20, breakdown["budget_signals"])

    # ─── 4. Business Maturity (0-15) ───
    if audit_data:
        issues = audit_data.get("issues", [])
        # Having structured data = mature website
        has_schema = not any(i.get("issue", "").startswith("No structured") for i in issues)
        if has_schema:
            breakdown["business_maturity"] += 5
        # Good page title = professional
        has_good_title = not any("title" in i.get("issue", "").lower() for i in issues)
        if has_good_title:
            breakdown["business_maturity"] += 3
        # Meta description = knows SEO basics
        has_meta = not any("meta description" in i.get("issue", "").lower() for i in issues)
        if has_meta:
            breakdown["business_maturity"] += 3
        # OG tags = social media aware
        has_og = not any("Open Graph" in i.get("issue", "") for i in issues)
        if has_og:
            breakdown["business_maturity"] += 2
    else:
        # Estimate from seo_score
        if seo_score >= 70:
            breakdown["business_maturity"] = 10
        elif seo_score >= 50:
            breakdown["business_maturity"] = 7
        else:
            breakdown["business_maturity"] = 4

    # Has a business name = established
    if lead_data.get("business_name"):
        breakdown["business_maturity"] = min(15, breakdown["business_maturity"] + 2)

    breakdown["business_maturity"] = min(15, breakdown["business_maturity"])

    # ─── 5. Engagement Readiness (0-15) ───
    # Real email found on site
    if email and "@" in email:
        email_source = str(lead_data.get("email_source", ""))
        if email_source == "found":
            breakdown["engagement_readiness"] += 8
        elif email_source == "manual":
            breakdown["engagement_readiness"] += 7
        else:
            breakdown["engagement_readiness"] += 4

    # Has phone number
    if lead_data.get("phone"):
        breakdown["engagement_readiness"] += 4

    # Has a real name in business name (not just domain)
    biz_name = str(lead_data.get("business_name", ""))
    if biz_name and len(biz_name) > 5 and not biz_name.startswith("http"):
        breakdown["engagement_readiness"] += 3

    breakdown["engagement_readiness"] = min(15, breakdown["engagement_readiness"])

    # ─── Calculate totals ───
    total = sum(breakdown.values())
    total = min(100, max(0, total))

    grade = _get_grade(total)
    recommendation = _get_recommendation(total, breakdown)

    return {
        "total_score": total,
        "grade": grade,
        "breakdown": breakdown,
        "recommendation": recommendation,
    }


def _find_niche_profile(niche):
    """Find matching niche profile, with fuzzy matching."""
    niche_lower = niche.lower().replace("_", " ")
    for key, profile in NICHE_PROFILES.items():
        if key.replace("_", " ") in niche_lower or niche_lower in key.replace("_", " "):
            return profile
        # Check display name
        if niche_lower in profile["display_name"].lower():
            return profile
        # Check search queries
        for q in profile.get("search_queries", []):
            if q in niche_lower or niche_lower in q:
                return profile
    return None


def _safe_int(val):
    """Safely convert to int."""
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 50


def _get_grade(score):
    """Convert score to letter grade."""
    if score >= 85:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 55:
        return "C"
    elif score >= 40:
        return "D"
    else:
        return "F"


def _get_recommendation(score, breakdown):
    """Generate action recommendation based on score."""
    if score >= 80:
        return "HIGH PRIORITY — Contact immediately. Strong potential client."
    elif score >= 65:
        return "GOOD PROSPECT — Worth reaching out with personalized pitch."
    elif score >= 50:
        return "MODERATE — Include in regular outreach cycle."
    elif score >= 35:
        return "LOW PRIORITY — May respond but lower deal value."
    else:
        return "SKIP — Focus efforts on higher-scoring leads."
