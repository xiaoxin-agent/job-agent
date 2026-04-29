"""
Ciena Careers — Workday-powered (thin wrapper around sites.workday).

Search: Workday API (ciena.wd5.myworkdayjobs.com/Careers)
Details: JSON-LD from job detail pages.
"""

from typing import Dict, List
from .workday import search_ciena, extract as wd_extract, get_company

SITE = "Ciena"
SECTIONS = get_company("Ciena").get("sections", [])


def search(keywords: List[str] = None, location: str = "",
           max_results: int = 10, **kwargs) -> List[Dict]:
    """Search Ciena jobs via Workday API."""
    return search_ciena(keywords, location, max_results)


def extract(html: str, url: str = "") -> Dict[str, str]:
    """Extract job details from a Ciena Workday job page."""
    return wd_extract(html, url)
