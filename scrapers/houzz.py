"""Houzz scraper — finds home service professionals."""

import re

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, RawLead
from scrapers.registry import register


@register
class HouzzScraper(BaseScraper):
    name = "Houzz"
    description = "Find home service pros on Houzz"
    supports_regions = ["us", "global"]

    def search(self, niche, location):
        # Only useful for home/construction niches
        home_keywords = [
            "contractor", "plumber", "electrician", "roofing", "hvac",
            "landscap", "interior design", "architect", "remodel",
            "painting", "flooring", "kitchen", "bathroom",
        ]
        if not any(kw in niche.lower() for kw in home_keywords):
            return []

        search_term = niche.replace(" ", "-").lower()
        loc = location.replace(" ", "-").lower()
        url = f"https://www.houzz.com/professionals/{search_term}/{loc}"
        results = []

        try:
            self._sleep(2, 5)
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, "html.parser")

            for item in soup.find_all("div", class_=re.compile(r"professional|result|card")):
                name_tag = item.find(["a", "h2", "h3"], class_=re.compile(r"name|title"))
                biz_name = name_tag.get_text(strip=True) if name_tag else ""

                link = item.find("a", href=re.compile(r"houzz.com/professionals/"))
                if link:
                    # Try to get actual website from profile
                    profile_url = link.get("href", "")
                    if not profile_url.startswith("http"):
                        profile_url = f"https://www.houzz.com{profile_url}"
                    try:
                        self._sleep(1, 2)
                        prof_resp = self.session.get(profile_url, timeout=10)
                        prof_soup = BeautifulSoup(prof_resp.text, "html.parser")
                        website_link = prof_soup.find("a", href=re.compile(r"http"), class_=re.compile(r"website"))
                        if website_link:
                            website = website_link.get("href", "")
                            if not self._is_skip_domain(website):
                                results.append(RawLead(
                                    website=website,
                                    business_name=biz_name[:60],
                                    niche=niche,
                                    location=location,
                                    source="Houzz",
                                ))
                    except Exception:
                        continue

                if len(results) >= 10:
                    break
        except Exception:
            pass

        return self._deduplicate(results)
