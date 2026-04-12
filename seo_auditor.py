"""
Quick SEO Auditor - Generates personalized SEO findings for each lead.
This makes your cold emails specific and valuable, not generic spam.
"""

import re
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup


def quick_seo_audit(website_url):
    """
    Run a quick SEO audit on a website.
    Returns dict of findings to use in email personalization.
    """
    audit = {
        "website": website_url,
        "issues": [],
        "score": 100,  # Start perfect, deduct for issues
        "summary": "",
        "specific_fix": "",
    }

    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })

        # Follow redirects, check final URL
        resp = session.get(website_url, timeout=15, allow_redirects=True)
        load_time = resp.elapsed.total_seconds()
        soup = BeautifulSoup(resp.text, "html.parser")
        html = resp.text.lower()

        # 1. SSL Check
        if not resp.url.startswith("https"):
            audit["issues"].append({
                "issue": "No SSL/HTTPS",
                "impact": "Google penalizes non-secure sites. Visitors see 'Not Secure' warning.",
                "severity": "high",
            })
            audit["score"] -= 15

        # 2. Page Title
        title = soup.find("title")
        if not title or not title.text.strip():
            audit["issues"].append({
                "issue": "Missing page title",
                "impact": "Google doesn't know what your page is about. This hurts all your rankings.",
                "severity": "high",
            })
            audit["score"] -= 15
        elif len(title.text.strip()) < 20:
            audit["issues"].append({
                "issue": f"Page title too short ({len(title.text.strip())} chars)",
                "impact": "You're leaving ranking opportunities on the table with a short title.",
                "severity": "medium",
            })
            audit["score"] -= 8
        elif len(title.text.strip()) > 60:
            audit["issues"].append({
                "issue": "Page title too long (gets cut off in search results)",
                "impact": "Searchers can't read your full title, reducing click-through rates.",
                "severity": "low",
            })
            audit["score"] -= 5

        # 3. Meta Description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if not meta_desc or not meta_desc.get("content", "").strip():
            audit["issues"].append({
                "issue": "Missing meta description",
                "impact": "Google will auto-generate a snippet — it's usually terrible and hurts CTR.",
                "severity": "high",
            })
            audit["score"] -= 12

        # 4. H1 Tag
        h1_tags = soup.find_all("h1")
        if not h1_tags:
            audit["issues"].append({
                "issue": "No H1 heading tag",
                "impact": "Google uses H1 as a major ranking signal. Your page is missing its main heading.",
                "severity": "high",
            })
            audit["score"] -= 12
        elif len(h1_tags) > 1:
            audit["issues"].append({
                "issue": f"Multiple H1 tags ({len(h1_tags)} found)",
                "impact": "Confuses Google about your page's main topic. Should have exactly one H1.",
                "severity": "medium",
            })
            audit["score"] -= 5

        # 5. Mobile Viewport
        viewport = soup.find("meta", attrs={"name": "viewport"})
        if not viewport:
            audit["issues"].append({
                "issue": "Not mobile-optimized (missing viewport tag)",
                "impact": "60%+ of searches are mobile. Google uses mobile-first indexing.",
                "severity": "high",
            })
            audit["score"] -= 15

        # 6. Image Alt Text
        images = soup.find_all("img")
        images_without_alt = [img for img in images if not img.get("alt")]
        if images and len(images_without_alt) > len(images) * 0.5:
            audit["issues"].append({
                "issue": f"{len(images_without_alt)} of {len(images)} images missing alt text",
                "impact": "Missing free traffic from Google Image Search. Also hurts accessibility.",
                "severity": "medium",
            })
            audit["score"] -= 8

        # 7. Page Speed (basic check based on response time and page size)
        page_size_kb = len(resp.content) / 1024
        if load_time > 3:
            audit["issues"].append({
                "issue": f"Slow page load ({load_time:.1f} seconds)",
                "impact": "Google confirms page speed is a ranking factor. Slow sites lose visitors.",
                "severity": "high",
            })
            audit["score"] -= 10
        if page_size_kb > 3000:
            audit["issues"].append({
                "issue": f"Large page size ({page_size_kb:.0f}KB)",
                "impact": "Heavy pages load slowly on mobile, hurting rankings and user experience.",
                "severity": "medium",
            })
            audit["score"] -= 5

        # 8. Schema/Structured Data
        if "application/ld+json" not in html and "itemtype" not in html:
            audit["issues"].append({
                "issue": "No structured data (Schema markup)",
                "impact": "Missing rich snippets in search results (stars, hours, reviews).",
                "severity": "medium",
            })
            audit["score"] -= 5

        # 9. Canonical Tag
        canonical = soup.find("link", attrs={"rel": "canonical"})
        if not canonical:
            audit["issues"].append({
                "issue": "Missing canonical tag",
                "impact": "Risk of duplicate content issues diluting your rankings.",
                "severity": "medium",
            })
            audit["score"] -= 5

        # 10. Internal Links
        domain = urllib.parse.urlparse(resp.url).netloc
        internal_links = [a for a in soup.find_all("a", href=True)
                         if domain in urllib.parse.urljoin(resp.url, a["href"])]
        if len(internal_links) < 3:
            audit["issues"].append({
                "issue": "Very few internal links",
                "impact": "Poor internal linking means Google can't discover and rank your other pages.",
                "severity": "medium",
            })
            audit["score"] -= 5

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
            audit["specific_fix"] = ""

    except Exception as e:
        audit["issues"].append({
            "issue": f"Could not analyze site: {str(e)[:50]}",
            "impact": "Site may be down or blocking automated checks.",
            "severity": "high",
        })
        audit["score"] = 0
        audit["summary"] = "Could not analyze"

    return audit


def format_audit_for_email(audit):
    """
    Format audit results into a short, punchy email-ready snippet.
    """
    if not audit["issues"]:
        return ""

    # Pick top 2-3 issues to mention
    top_issues = sorted(audit["issues"],
                       key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["severity"]])[:3]

    lines = []
    for issue in top_issues:
        lines.append(f"- {issue['issue']}: {issue['impact']}")

    return "\n".join(lines)


def batch_audit(leads, max_per_batch=50):
    """
    Run SEO audits on a batch of leads.
    Returns dict mapping website -> audit results.
    """
    results = {}
    for i, lead in enumerate(leads[:max_per_batch]):
        website = lead.get("website", "")
        if not website:
            continue

        print(f"  [{i+1}/{min(len(leads), max_per_batch)}] Auditing: {website}")
        audit = quick_seo_audit(website)
        results[website] = audit

        if audit["issues"]:
            print(f"    Score: {audit['score']}/100 | Issues: {len(audit['issues'])}")
        else:
            print(f"    Score: {audit['score']}/100 | No issues found")

        time.sleep(1)  # Be respectful

    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        url = sys.argv[1]
        if not url.startswith("http"):
            url = f"https://{url}"
        audit = quick_seo_audit(url)
        print(f"\nSEO Audit for: {url}")
        print(f"Score: {audit['score']}/100")
        print(f"Summary: {audit['summary']}")
        print(f"\nIssues found:")
        for issue in audit["issues"]:
            print(f"  [{issue['severity'].upper()}] {issue['issue']}")
            print(f"         {issue['impact']}")
        print(f"\nEmail snippet:")
        print(format_audit_for_email(audit))
    else:
        print("Usage: python seo_auditor.py <website_url>")
        print("Example: python seo_auditor.py example.com")
