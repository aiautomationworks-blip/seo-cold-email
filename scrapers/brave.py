"""Brave Search scraper."""

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, RawLead
from scrapers.registry import register


@register
class BraveScraper(BaseScraper):
    name = "Brave"
    description = "Search Brave for business websites"
    supports_regions = ["global"]

    def search(self, niche, location):
        query = f"{niche} in {location} website contact"
        url = f"https://search.brave.com/search?q={query.replace(' ', '+')}"
        results = []

        try:
            self._sleep(2, 5)
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, "html.parser")

            for item in soup.find_all("div", class_="snippet"):
                link = item.find("a", class_="result-header")
                if not link:
                    link = item.find("a")
                if not link:
                    continue
                href = link.get("href", "")
                if not href.startswith("http") or self._is_skip_domain(href):
                    continue
                title = link.get_text(strip=True)
                results.append(RawLead(
                    website=href,
                    title=title[:80],
                    niche=niche,
                    location=location,
                    source="Brave",
                ))
        except Exception:
            pass

        return self._deduplicate(results)
