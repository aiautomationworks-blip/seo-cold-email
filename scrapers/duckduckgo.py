"""DuckDuckGo scraper — the most reliable free search scraper."""

import urllib.parse

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, RawLead
from scrapers.registry import register


@register
class DuckDuckGoScraper(BaseScraper):
    name = "DuckDuckGo"
    description = "Search DuckDuckGo HTML (reliable, no blocking)"
    supports_regions = ["global"]

    def search(self, niche, location):
        query = f"{niche} in {location} website contact"
        url = "https://html.duckduckgo.com/html/"
        results = []

        try:
            self._sleep(2, 4)
            resp = self.session.post(url, data={"q": query}, timeout=15)
            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, "html.parser")

            for result in soup.find_all("a", class_="result__a"):
                href = result.get("href", "")
                if "uddg=" in href:
                    actual = urllib.parse.unquote(href.split("uddg=")[1].split("&")[0])
                elif href.startswith("http"):
                    actual = href
                else:
                    continue

                if self._is_skip_domain(actual):
                    continue

                if actual.startswith("http"):
                    title = result.get_text(strip=True)
                    results.append(RawLead(
                        website=actual,
                        title=title[:80],
                        niche=niche,
                        location=location,
                        source="DuckDuckGo",
                    ))
        except Exception:
            pass

        return self._deduplicate(results)
