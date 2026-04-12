"""JustDial scraper — great for Indian businesses."""

import re

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, RawLead
from scrapers.registry import register


@register
class JustDialScraper(BaseScraper):
    name = "JustDial"
    description = "Search JustDial for Indian businesses"
    supports_regions = ["in"]

    def search(self, niche, location):
        city = location.split(",")[0].strip().lower().replace(" ", "-")
        niche_slug = niche.lower().replace(" ", "-")
        url = f"https://www.justdial.com/{city}/{niche_slug}"
        results = []

        try:
            self._sleep(2, 4)
            self.session.headers.update({"Referer": "https://www.justdial.com/"})
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, "html.parser")

            for item in soup.find_all("li", class_=re.compile(r"cntanr")):
                name_tag = item.find("span", class_="lng_cont_name")
                biz_name = name_tag.get_text(strip=True) if name_tag else ""

                website_tag = item.find("a", href=re.compile(r"http"), class_=re.compile(r"website"))
                website = website_tag.get("href", "") if website_tag else ""

                if biz_name and website and not self._is_skip_domain(website):
                    results.append(RawLead(
                        website=website,
                        business_name=biz_name[:60],
                        niche=niche,
                        location=location,
                        source="JustDial",
                    ))

            # Fallback: extract external links
            if not results:
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    text = link.get_text(strip=True)
                    if (href.startswith("http") and
                        "justdial" not in href and
                        len(text) > 3 and
                        not self._is_skip_domain(href)):
                        results.append(RawLead(
                            website=href,
                            business_name=text[:60],
                            niche=niche,
                            location=location,
                            source="JustDial",
                        ))
        except Exception:
            pass

        return self._deduplicate(results)
