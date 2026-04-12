"""IndiaMart scraper — Indian B2B directory."""

import re

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, RawLead
from scrapers.registry import register


@register
class IndiaMartScraper(BaseScraper):
    name = "IndiaMart"
    description = "Search IndiaMart for Indian businesses"
    supports_regions = ["in"]

    def search(self, niche, location):
        search_term = niche.replace(" ", "+")
        city = location.split(",")[0].strip().lower()
        url = f"https://dir.indiamart.com/search.mp?ss={search_term}&city={city}"
        results = []

        try:
            self._sleep(2, 5)
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, "html.parser")

            for item in soup.find_all("div", class_=re.compile(r"lstng|card|supplier")):
                name_tag = item.find(["h2", "h3", "a"], class_=re.compile(r"compny|name|title"))
                biz_name = name_tag.get_text(strip=True) if name_tag else ""

                website_tag = item.find("a", href=re.compile(r"http"), class_=re.compile(r"website|url"))
                website = ""
                if website_tag:
                    href = website_tag.get("href", "")
                    if not self._is_skip_domain(href):
                        website = href

                if biz_name:
                    results.append(RawLead(
                        website=website,
                        business_name=biz_name[:60],
                        niche=niche,
                        location=location,
                        source="IndiaMart",
                    ))
        except Exception:
            pass

        return self._deduplicate(results, max_results=15)
