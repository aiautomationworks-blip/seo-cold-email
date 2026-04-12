"""Yellow Pages scraper."""

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, RawLead
from scrapers.registry import register


@register
class YellowPagesScraper(BaseScraper):
    name = "YellowPages"
    description = "Search YellowPages.com for US businesses"
    supports_regions = ["us"]

    def search(self, niche, location):
        search_term = niche.replace(" ", "+")
        geo = location.replace(" ", "+")
        url = f"https://www.yellowpages.com/search?search_terms={search_term}&geo_location_terms={geo}"
        results = []

        try:
            self._sleep(2, 5)
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, "html.parser")

            for item in soup.find_all("div", class_="result"):
                name_tag = item.find("a", class_="business-name")
                if not name_tag:
                    continue
                biz_name = name_tag.get_text(strip=True)

                # Look for website link
                website_tag = item.find("a", class_="track-visit-website")
                website = website_tag.get("href", "") if website_tag else ""

                phone_tag = item.find("div", class_="phones")
                phone = phone_tag.get_text(strip=True) if phone_tag else ""

                if website and not self._is_skip_domain(website):
                    results.append(RawLead(
                        website=website,
                        business_name=biz_name[:60],
                        phone=phone,
                        niche=niche,
                        location=location,
                        source="YellowPages",
                    ))
        except Exception:
            pass

        return self._deduplicate(results)
