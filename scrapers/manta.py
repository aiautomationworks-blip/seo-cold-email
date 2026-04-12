"""Manta scraper — US small business directory."""

import re

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, RawLead
from scrapers.registry import register


@register
class MantaScraper(BaseScraper):
    name = "Manta"
    description = "Search Manta for US small businesses"
    supports_regions = ["us"]

    def search(self, niche, location):
        search_term = niche.replace(" ", "+")
        loc = location.replace(" ", "+")
        url = f"https://www.manta.com/search?search_source=nav&search={search_term}&search_location={loc}"
        results = []

        try:
            self._sleep(2, 5)
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, "html.parser")

            for item in soup.find_all("div", class_=re.compile(r"result|listing|card")):
                link = item.find("a", href=True)
                if not link:
                    continue
                biz_name = link.get_text(strip=True)
                if len(biz_name) < 3:
                    continue

                # Manta links to business profile pages
                href = link.get("href", "")
                if "/c/" in href:
                    # Try to get website from business profile
                    profile_url = href if href.startswith("http") else f"https://www.manta.com{href}"
                    try:
                        self._sleep(1, 2)
                        prof_resp = self.session.get(profile_url, timeout=10)
                        prof_soup = BeautifulSoup(prof_resp.text, "html.parser")
                        website_link = prof_soup.find("a", class_=re.compile(r"website"))
                        if website_link:
                            website = website_link.get("href", "")
                            if website.startswith("http") and not self._is_skip_domain(website):
                                results.append(RawLead(
                                    website=website,
                                    business_name=biz_name[:60],
                                    niche=niche,
                                    location=location,
                                    source="Manta",
                                ))
                    except Exception:
                        continue

                if len(results) >= 10:
                    break
        except Exception:
            pass

        return self._deduplicate(results)
