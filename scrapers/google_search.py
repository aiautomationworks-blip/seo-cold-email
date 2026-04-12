"""Google Search scraper — may get blocked, use as backup."""

import urllib.parse

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, RawLead
from scrapers.registry import register


@register
class GoogleScraper(BaseScraper):
    name = "Google"
    description = "Search Google (may get rate-limited)"
    supports_regions = ["global"]

    def search(self, niche, location):
        query = f"{niche} in {location} website"
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num=20"
        results = []

        try:
            self._sleep(3, 6)
            self.session.headers.update({
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            })
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, "html.parser")

            for div in soup.find_all("div", class_="g"):
                link = div.find("a")
                if not link:
                    continue
                href = link.get("href", "")
                if not href.startswith("http") or self._is_skip_domain(href):
                    continue
                title_el = div.find("h3")
                title = title_el.get_text(strip=True) if title_el else ""
                results.append(RawLead(
                    website=href,
                    title=title[:80],
                    niche=niche,
                    location=location,
                    source="Google",
                ))
        except Exception:
            pass

        return self._deduplicate(results)
