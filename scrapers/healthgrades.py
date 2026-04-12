"""Healthgrades scraper — finds healthcare providers via DuckDuckGo."""

import urllib.parse

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, RawLead
from scrapers.registry import register


@register
class HealthgradesScraper(BaseScraper):
    name = "Healthgrades"
    description = "Find healthcare providers and their websites"
    supports_regions = ["us"]

    def search(self, niche, location):
        # Only useful for medical/health niches
        health_keywords = [
            "dentist", "doctor", "surgeon", "physician", "chiropractor",
            "therapist", "dermatolog", "optometrist", "orthodontist",
            "pediatric", "veterinar", "med spa", "clinic", "medical",
        ]
        if not any(kw in niche.lower() for kw in health_keywords):
            return []

        query = f"{niche} {location} official website"
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
                # Skip healthgrades itself
                if "healthgrades." in actual.lower():
                    continue

                title = result.get_text(strip=True)
                results.append(RawLead(
                    website=actual,
                    title=title[:80],
                    niche=niche,
                    location=location,
                    source="Healthgrades",
                ))
        except Exception:
            pass

        return self._deduplicate(results)
