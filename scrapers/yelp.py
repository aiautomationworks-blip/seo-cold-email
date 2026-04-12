"""Yelp scraper — extracts business websites from Yelp listings."""

import re

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, RawLead
from scrapers.registry import register


@register
class YelpScraper(BaseScraper):
    name = "Yelp"
    description = "Search Yelp for business listings"
    supports_regions = ["us", "global"]

    def search(self, niche, location):
        search_term = niche.replace(" ", "+")
        loc = location.replace(" ", "+")
        url = f"https://www.yelp.com/search?find_desc={search_term}&find_loc={loc}"
        results = []

        try:
            self._sleep(2, 5)
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, "html.parser")

            # Yelp renders business cards with links
            for link in soup.find_all("a", href=re.compile(r"/biz/")):
                href = link.get("href", "")
                text = link.get_text(strip=True)
                if len(text) < 3 or not href.startswith("/biz/"):
                    continue

                biz_slug = href.split("/biz/")[1].split("?")[0]
                biz_url = f"https://www.yelp.com/biz/{biz_slug}"

                # Try to get the actual business website from the biz page
                try:
                    self._sleep(1, 3)
                    biz_resp = self.session.get(biz_url, timeout=10)
                    biz_soup = BeautifulSoup(biz_resp.text, "html.parser")

                    website_link = biz_soup.find("a", href=re.compile(r"biz_redir"))
                    if website_link:
                        actual_url = website_link.get("href", "")
                        if "url=" in actual_url:
                            import urllib.parse
                            actual_url = urllib.parse.unquote(
                                actual_url.split("url=")[1].split("&")[0]
                            )
                        if actual_url.startswith("http") and not self._is_skip_domain(actual_url):
                            phone_tag = biz_soup.find("p", string=re.compile(r"\d{3}"))
                            phone = phone_tag.get_text(strip=True) if phone_tag else ""
                            results.append(RawLead(
                                website=actual_url,
                                business_name=text[:60],
                                phone=phone,
                                niche=niche,
                                location=location,
                                source="Yelp",
                            ))
                except Exception:
                    continue

                if len(results) >= 15:
                    break
        except Exception:
            pass

        return self._deduplicate(results)
