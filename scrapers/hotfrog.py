"""HotFrog scraper — international business directory."""

import re

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, RawLead
from scrapers.registry import register


@register
class HotFrogScraper(BaseScraper):
    name = "HotFrog"
    description = "Search HotFrog business directory"
    supports_regions = ["global"]

    def search(self, niche, location):
        search_term = niche.replace(" ", "-").lower()
        loc = location.replace(" ", "-").lower()
        url = f"https://www.hotfrog.com/search/{loc}/{search_term}"
        results = []

        try:
            self._sleep(2, 5)
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, "html.parser")

            for item in soup.find_all(["div", "li"], class_=re.compile(r"result|listing|card")):
                name_tag = item.find(["h2", "h3", "a"], class_=re.compile(r"name|title"))
                biz_name = name_tag.get_text(strip=True) if name_tag else ""

                website_tag = item.find("a", href=re.compile(r"http"), string=re.compile(r"website|visit", re.I))
                if not website_tag:
                    website_tag = item.find("a", class_=re.compile(r"website"))
                website = website_tag.get("href", "") if website_tag else ""

                phone_tag = item.find(string=re.compile(r"\d{3}.*\d{4}"))
                phone = phone_tag.strip() if phone_tag else ""

                if biz_name and website and not self._is_skip_domain(website):
                    results.append(RawLead(
                        website=website,
                        business_name=biz_name[:60],
                        phone=phone,
                        niche=niche,
                        location=location,
                        source="HotFrog",
                    ))
        except Exception:
            pass

        return self._deduplicate(results)
