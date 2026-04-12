"""Base scraper class and RawLead dataclass."""

import random
import time
import urllib.parse
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

import requests

from core.constants import SKIP_DOMAINS, USER_AGENTS


@dataclass
class RawLead:
    """A raw lead from a scraper before enrichment."""
    website: str = ""
    title: str = ""
    business_name: str = ""
    phone: str = ""
    niche: str = ""
    location: str = ""
    source: str = ""


class BaseScraper(ABC):
    """Abstract base class for all lead scrapers."""

    name: str = "Base"
    description: str = ""
    supports_regions: list = []  # e.g. ["us", "in", "global"]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def _sleep(self, min_sec=2, max_sec=5):
        """Random delay to avoid rate limits."""
        time.sleep(random.uniform(min_sec, max_sec))

    def _is_skip_domain(self, url):
        """Check if URL is a directory/social site we should skip."""
        url_lower = url.lower()
        return any(d in url_lower for d in SKIP_DOMAINS)

    def _deduplicate(self, leads: List[RawLead], max_results=20) -> List[RawLead]:
        """Remove duplicate domains from results."""
        seen = set()
        unique = []
        for lead in leads:
            domain = urllib.parse.urlparse(lead.website).netloc
            if domain and domain not in seen:
                seen.add(domain)
                unique.append(lead)
        return unique[:max_results]

    @abstractmethod
    def search(self, niche: str, location: str) -> List[RawLead]:
        """Search for leads. Must be implemented by subclasses."""
        pass
