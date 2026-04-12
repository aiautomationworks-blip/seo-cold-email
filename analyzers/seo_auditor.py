"""SEO Auditor — 12-check comprehensive audit with severity scoring."""

import random
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup

from core.constants import USER_AGENTS


def run_seo_audit(website_url):
    """
    Run a comprehensive SEO audit on a website.
    Returns dict with score (0-100), issues list, and summary.
    """
    audit = {
        "website": website_url,
        "score": 100,
        "issues": [],
        "summary": "",
        "specific_fix": "",
        "load_time": 0,
        "page_size_kb": 0,
    }

    try:
        session = requests.Session()
        session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
        resp = session.get(website_url, timeout=15, allow_redirects=True)
        load_time = resp.elapsed.total_seconds()
        audit["load_time"] = round(load_time, 2)
        audit["page_size_kb"] = round(len(resp.content) / 1024, 1)

        soup = BeautifulSoup(resp.text, "html.parser")
        html = resp.text.lower()

        # 1. SSL/HTTPS
        if not resp.url.startswith("https"):
            audit["issues"].append({
                "issue": "No SSL/HTTPS",
                "impact": "Google penalizes non-secure sites. Visitors see 'Not Secure' warning.",
                "severity": "high", "deduction": 15,
            })
            audit["score"] -= 15

        # 2. Page Title
        title = soup.find("title")
        if not title or not title.text.strip():
            audit["issues"].append({
                "issue": "Missing page title",
                "impact": "Google doesn't know what your page is about.",
                "severity": "high", "deduction": 15,
            })
            audit["score"] -= 15
        elif len(title.text.strip()) < 20:
            audit["issues"].append({
                "issue": f"Page title too short ({len(title.text.strip())} chars)",
                "impact": "You're leaving ranking opportunities on the table.",
                "severity": "medium", "deduction": 8,
            })
            audit["score"] -= 8
        elif len(title.text.strip()) > 60:
            audit["issues"].append({
                "issue": "Page title too long (gets cut off in search results)",
                "impact": "Searchers can't read your full title.",
                "severity": "low", "deduction": 5,
            })
            audit["score"] -= 5

        # 3. Meta Description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if not meta_desc or not meta_desc.get("content", "").strip():
            audit["issues"].append({
                "issue": "Missing meta description",
                "impact": "Google auto-generates a snippet — usually hurts CTR.",
                "severity": "high", "deduction": 12,
            })
            audit["score"] -= 12

        # 4. H1 Tag
        h1_tags = soup.find_all("h1")
        if not h1_tags:
            audit["issues"].append({
                "issue": "No H1 heading tag",
                "impact": "Google uses H1 as a major ranking signal.",
                "severity": "high", "deduction": 12,
            })
            audit["score"] -= 12
        elif len(h1_tags) > 1:
            audit["issues"].append({
                "issue": f"Multiple H1 tags ({len(h1_tags)} found)",
                "impact": "Confuses Google about your page's main topic.",
                "severity": "medium", "deduction": 5,
            })
            audit["score"] -= 5

        # 5. Mobile Viewport
        viewport = soup.find("meta", attrs={"name": "viewport"})
        if not viewport:
            audit["issues"].append({
                "issue": "Not mobile-optimized (missing viewport)",
                "impact": "60%+ of searches are mobile. Google uses mobile-first indexing.",
                "severity": "high", "deduction": 15,
            })
            audit["score"] -= 15

        # 6. Image Alt Text
        images = soup.find_all("img")
        no_alt = [img for img in images if not img.get("alt")]
        if images and len(no_alt) > len(images) * 0.5:
            audit["issues"].append({
                "issue": f"{len(no_alt)}/{len(images)} images missing alt text",
                "impact": "Missing traffic from Google Image Search.",
                "severity": "medium", "deduction": 8,
            })
            audit["score"] -= 8

        # 7. Page Speed
        if load_time > 3:
            audit["issues"].append({
                "issue": f"Slow page load ({load_time:.1f}s)",
                "impact": "Page speed is a ranking factor. Slow sites lose visitors.",
                "severity": "high", "deduction": 10,
            })
            audit["score"] -= 10

        # 8. Page Size
        page_size_kb = len(resp.content) / 1024
        if page_size_kb > 3000:
            audit["issues"].append({
                "issue": f"Large page size ({page_size_kb:.0f}KB)",
                "impact": "Heavy pages load slowly on mobile.",
                "severity": "medium", "deduction": 5,
            })
            audit["score"] -= 5

        # 9. Schema/Structured Data
        if "application/ld+json" not in html and "itemtype" not in html:
            audit["issues"].append({
                "issue": "No structured data (Schema markup)",
                "impact": "Missing rich snippets in search results (stars, hours).",
                "severity": "medium", "deduction": 5,
            })
            audit["score"] -= 5

        # 10. Canonical Tag
        canonical = soup.find("link", attrs={"rel": "canonical"})
        if not canonical:
            audit["issues"].append({
                "issue": "Missing canonical tag",
                "impact": "Risk of duplicate content diluting rankings.",
                "severity": "medium", "deduction": 5,
            })
            audit["score"] -= 5

        # 11. Internal Links
        domain = urllib.parse.urlparse(resp.url).netloc
        internal_links = [a for a in soup.find_all("a", href=True)
                         if domain in urllib.parse.urljoin(resp.url, a["href"])]
        if len(internal_links) < 3:
            audit["issues"].append({
                "issue": "Very few internal links",
                "impact": "Poor internal linking means Google can't discover your pages.",
                "severity": "medium", "deduction": 5,
            })
            audit["score"] -= 5

        # 12. Open Graph / Social Meta
        og_title = soup.find("meta", property="og:title")
        if not og_title:
            audit["issues"].append({
                "issue": "Missing Open Graph meta tags",
                "impact": "Social media shares won't look professional.",
                "severity": "low", "deduction": 3,
            })
            audit["score"] -= 3

        # Generate summary
        audit["score"] = max(0, audit["score"])
        high_issues = [i for i in audit["issues"] if i["severity"] == "high"]
        medium_issues = [i for i in audit["issues"] if i["severity"] == "medium"]

        if high_issues:
            audit["summary"] = f"Found {len(high_issues)} critical and {len(medium_issues)} moderate SEO issues"
            audit["specific_fix"] = high_issues[0]["issue"]
        elif medium_issues:
            audit["summary"] = f"Found {len(medium_issues)} SEO improvements"
            audit["specific_fix"] = medium_issues[0]["issue"]
        else:
            audit["summary"] = "Site has good basic SEO foundations"

    except Exception as e:
        audit["issues"].append({
            "issue": f"Could not analyze site: {str(e)[:50]}",
            "impact": "Site may be down or blocking automated checks.",
            "severity": "high", "deduction": 0,
        })
        audit["score"] = 0
        audit["summary"] = "Could not analyze"

    return audit


def format_issues_for_email(audit):
    """Format top issues as a bullet list for email personalization."""
    if not audit["issues"]:
        return "a few SEO improvements I'd recommend"

    top = sorted(audit["issues"],
                 key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["severity"]])[:3]
    return "\n".join(f"- {i['issue']}: {i['impact']}" for i in top)


def format_issues_short(issues_str):
    """Format semicolon-separated issues string into bullet points."""
    if not issues_str or issues_str == "nan":
        return "a few SEO improvements"
    parts = [i.strip() for i in str(issues_str).split(";") if i.strip()]
    return "\n".join(f"- {p}" for p in parts[:4])
