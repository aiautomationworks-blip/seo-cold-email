"""Yahoo Search scraper."""

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, RawLead
from scrapers.registry import register


@register
class YahooScraper(BaseScraper):
    name = "Yahoo"
    description = "Search Yahoo for business websites"
    supports_regions = ["global"]

    def search(self, niche, location):
        query = f"{niche} in {location} website"
        url = f"https://search.yahoo.com/search?p={query.replace(' ', '+')}&n=20"
        results = []

        try:
            self._sleep(2, 5)
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, "html.parser")

            for div in soup.find_all("div", class_="algo-sr"):
                link = div.find("a")
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
                    source="Yahoo",
                ))
        except Exception:
            pass

        return self._deduplicate(results)
