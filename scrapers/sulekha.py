"""Sulekha scraper — Indian business directory."""

import re

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, RawLead
from scrapers.registry import register


@register
class SulekhaScraper(BaseScraper):
    name = "Sulekha"
    description = "Search Sulekha for Indian businesses"
    supports_regions = ["in"]

    def search(self, niche, location):
        city = location.split(",")[0].strip().lower().replace(" ", "-")
        niche_slug = niche.lower().replace(" ", "-")
        url = f"https://www.sulekha.com/{niche_slug}/{city}"
        results = []

        try:
            self._sleep(2, 5)
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, "html.parser")

            # Sulekha business listings
            for item in soup.find_all("div", class_=re.compile(r"merchant|listing|bcard")):
                name_tag = item.find(["h2", "h3", "a"], class_=re.compile(r"name|title"))
                biz_name = name_tag.get_text(strip=True) if name_tag else ""

                website_tag = item.find("a", href=re.compile(r"http"), string=re.compile(r"website|visit", re.I))
                website = ""
                if website_tag:
                    website = website_tag.get("href", "")

                phone_tag = item.find(string=re.compile(r"\d{10}|\+91"))
                phone = phone_tag.strip() if phone_tag else ""

                if biz_name and website and not self._is_skip_domain(website):
                    results.append(RawLead(
                        website=website,
                        business_name=biz_name[:60],
                        phone=phone,
                        niche=niche,
                        location=location,
                        source="Sulekha",
                    ))

            # Fallback: DuckDuckGo site search
            if not results:
                query = f"site:sulekha.com {niche} {location}"
                ddg_url = "https://html.duckduckgo.com/html/"
                self._sleep(2, 4)
                resp = self.session.post(ddg_url, data={"q": query}, timeout=15)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for result in soup.find_all("a", class_="result__a"):
                        text = result.get_text(strip=True)
                        if text and len(text) > 5:
                            results.append(RawLead(
                                business_name=text[:60],
                                niche=niche,
                                location=location,
                                source="Sulekha",
                            ))
        except Exception:
            pass

        return self._deduplicate(results, max_results=15)
