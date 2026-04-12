"""Deliverability Toolkit — SPF/DKIM/DMARC checks, spam detection, scoring."""

import re

try:
    import dns.resolver
    HAS_DNS = True
except ImportError:
    HAS_DNS = False


# Common spam trigger words
SPAM_WORDS = [
    "act now", "apply now", "buy now", "buy direct", "click here",
    "click below", "congratulations", "dear friend", "don't delete",
    "don't miss", "double your", "earn extra", "exclusive deal",
    "free", "free access", "free gift", "free trial", "guarantee",
    "incredible deal", "limited time", "make money", "million dollars",
    "no cost", "no obligation", "offer expires", "once in a lifetime",
    "order now", "please read", "prize", "promise", "risk-free",
    "satisfaction guaranteed", "special promotion", "this isn't spam",
    "urgent", "winner", "you have been selected", "100% free",
    "100% satisfied", "cash bonus", "extra income",
]


def check_spf(domain):
    """
    Check SPF record for a domain.
    Returns dict with status, record, and recommendation.
    """
    if not HAS_DNS:
        return {"status": "unknown", "record": "", "recommendation": "Install dnspython for DNS checks"}

    try:
        answers = dns.resolver.resolve(domain, "TXT")
        for rdata in answers:
            txt = rdata.to_text().strip('"')
            if txt.startswith("v=spf1"):
                has_all = "-all" in txt or "~all" in txt
                return {
                    "status": "pass" if has_all else "weak",
                    "record": txt,
                    "recommendation": "" if has_all else "Add '-all' to SPF record for strict enforcement",
                }
        return {
            "status": "missing",
            "record": "",
            "recommendation": "Add SPF record: v=spf1 include:_spf.google.com ~all",
        }
    except dns.resolver.NXDOMAIN:
        return {"status": "error", "record": "", "recommendation": "Domain not found"}
    except Exception as e:
        return {"status": "error", "record": "", "recommendation": str(e)[:100]}


def check_dkim(domain, selector="google"):
    """
    Check DKIM record for a domain.
    Returns dict with status and recommendation.
    """
    if not HAS_DNS:
        return {"status": "unknown", "record": "", "recommendation": "Install dnspython for DNS checks"}

    dkim_domain = f"{selector}._domainkey.{domain}"
    try:
        answers = dns.resolver.resolve(dkim_domain, "TXT")
        for rdata in answers:
            txt = rdata.to_text().strip('"')
            if "v=DKIM1" in txt or "p=" in txt:
                return {
                    "status": "pass",
                    "record": txt[:100] + "..." if len(txt) > 100 else txt,
                    "recommendation": "",
                }
        return {
            "status": "missing",
            "record": "",
            "recommendation": f"No DKIM record found for selector '{selector}'",
        }
    except dns.resolver.NXDOMAIN:
        return {
            "status": "missing",
            "record": "",
            "recommendation": "DKIM not configured. Enable in Google Workspace admin.",
        }
    except Exception as e:
        return {"status": "error", "record": "", "recommendation": str(e)[:100]}


def check_dmarc(domain):
    """
    Check DMARC record for a domain.
    Returns dict with status, policy, and recommendation.
    """
    if not HAS_DNS:
        return {"status": "unknown", "record": "", "policy": "", "recommendation": "Install dnspython"}

    dmarc_domain = f"_dmarc.{domain}"
    try:
        answers = dns.resolver.resolve(dmarc_domain, "TXT")
        for rdata in answers:
            txt = rdata.to_text().strip('"')
            if txt.startswith("v=DMARC1"):
                policy = ""
                p_match = re.search(r'p=(\w+)', txt)
                if p_match:
                    policy = p_match.group(1)

                status = "pass"
                rec = ""
                if policy == "none":
                    status = "weak"
                    rec = "Consider upgrading DMARC policy from 'none' to 'quarantine' or 'reject'"

                return {
                    "status": status,
                    "record": txt,
                    "policy": policy,
                    "recommendation": rec,
                }
        return {
            "status": "missing",
            "record": "",
            "policy": "",
            "recommendation": "Add DMARC record: v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com",
        }
    except dns.resolver.NXDOMAIN:
        return {
            "status": "missing", "record": "", "policy": "",
            "recommendation": "Add DMARC record for email authentication",
        }
    except Exception as e:
        return {"status": "error", "record": "", "policy": "", "recommendation": str(e)[:100]}


def check_all_records(domain):
    """Run all DNS authentication checks for a domain."""
    return {
        "spf": check_spf(domain),
        "dkim": check_dkim(domain),
        "dmarc": check_dmarc(domain),
    }


def scan_spam_words(text):
    """
    Scan text for spam trigger words.
    Returns list of found spam words and a spam score.
    """
    text_lower = text.lower()
    found = [word for word in SPAM_WORDS if word in text_lower]
    # Spam score: 0 (clean) to 100 (very spammy)
    score = min(100, len(found) * 10)
    return found, score


def check_template_spam(subject, body):
    """
    Check an email template for spam issues.
    Returns dict with score, found words, and recommendations.
    """
    combined = f"{subject} {body}"
    found, spam_score = scan_spam_words(combined)

    recs = []
    if found:
        recs.append(f"Remove or replace spam trigger words: {', '.join(found[:5])}")

    # Check subject
    if subject.count("!") > 1:
        recs.append("Reduce exclamation marks in subject")
        spam_score = min(100, spam_score + 10)

    caps_words = re.findall(r'\b[A-Z]{4,}\b', subject)
    if caps_words:
        recs.append(f"Avoid ALL CAPS: {', '.join(caps_words[:3])}")
        spam_score = min(100, spam_score + 15)

    if len(subject) > 80:
        recs.append("Shorten subject line (>80 chars may be truncated)")
        spam_score = min(100, spam_score + 5)

    # Check body
    link_count = len(re.findall(r'https?://', body))
    if link_count > 3:
        recs.append(f"Too many links ({link_count}) — keep under 3")
        spam_score = min(100, spam_score + 10)

    if body.count("$") > 2:
        recs.append("Excessive dollar signs may trigger spam filters")
        spam_score = min(100, spam_score + 10)

    return {
        "spam_score": spam_score,
        "found_words": found,
        "recommendations": recs,
        "clean": spam_score < 20,
    }


def calculate_deliverability_score(domain=None, template_subject="", template_body=""):
    """
    Calculate overall deliverability score (0-100).
    Combines DNS authentication and content analysis.
    """
    score = 100
    details = []

    # DNS checks (60% weight)
    if domain:
        records = check_all_records(domain)

        if records["spf"]["status"] == "pass":
            details.append("SPF: Configured correctly")
        elif records["spf"]["status"] == "weak":
            score -= 10
            details.append("SPF: Weak configuration")
        else:
            score -= 20
            details.append("SPF: Missing or error")

        if records["dkim"]["status"] == "pass":
            details.append("DKIM: Configured correctly")
        else:
            score -= 15
            details.append("DKIM: Not found (check selector)")

        if records["dmarc"]["status"] == "pass":
            details.append("DMARC: Configured correctly")
        elif records["dmarc"]["status"] == "weak":
            score -= 5
            details.append("DMARC: Weak policy")
        else:
            score -= 15
            details.append("DMARC: Missing")

    # Content checks (40% weight)
    if template_subject or template_body:
        spam_result = check_template_spam(template_subject, template_body)
        content_penalty = spam_result["spam_score"] * 0.4  # 40% weight
        score -= content_penalty
        if spam_result["found_words"]:
            details.append(f"Spam words found: {len(spam_result['found_words'])}")
        else:
            details.append("Content: Clean")

    return {
        "score": max(0, round(score)),
        "details": details,
        "grade": _score_to_grade(max(0, round(score))),
    }


def _score_to_grade(score):
    """Convert score to letter grade."""
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"
