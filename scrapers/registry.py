"""Scraper registry — auto-discovers and registers all scrapers."""

from scrapers.base import BaseScraper

_REGISTRY = {}


def register(cls):
    """Decorator to register a scraper class."""
    _REGISTRY[cls.name] = cls
    return cls


def get_all_scrapers():
    """Return dict of {name: scraper_class}."""
    _ensure_loaded()
    return dict(_REGISTRY)


def get_scraper(name):
    """Get a scraper class by name."""
    _ensure_loaded()
    return _REGISTRY.get(name)


def scraper_names():
    """Return list of all registered scraper names."""
    _ensure_loaded()
    return list(_REGISTRY.keys())


def _ensure_loaded():
    """Import all scraper modules to trigger registration."""
    if _REGISTRY:
        return
    # Import each module so @register decorators fire
    from scrapers import (  # noqa: F401
        duckduckgo, bing, brave, yahoo, google_search,
        yellow_pages, yelp, justdial, sulekha, indiamart,
        manta, hotfrog, realtor, houzz, healthgrades,
    )
