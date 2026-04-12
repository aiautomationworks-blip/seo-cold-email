"""Bing search scraper."""

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, RawLead
from scrapers.registry import register


@register
class BingScraper(BaseScraper):
    name = "Bing"
    description = "Search Bing for business websites"
    supports_regions = ["global"]

    def search(self, niche, location):
        query = f"{niche} in {location} website"
        url = f"https://www.bing.com/search?q={query.replace(' ', '+')}&count=30"
        results = []

        try:
            self._sleep(2, 4)
            self.session.headers.update({"Accept": "text/html"})
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, "html.parser")

            for li in soup.find_all("li", class_="b_algo"):
                link = li.find("a")
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
                    source="Bing",
                ))
        except Exception:
            pass

        return self._deduplicate(results)
