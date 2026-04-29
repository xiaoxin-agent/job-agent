"""
Alphawave Semi Careers — Workday-powered (thin wrapper around sites.workday).

Search: Workday API (alphawave.wd10.myworkdayjobs.com/Alphawave_External)
Details: JSON-LD from job detail pages.
"""

from typing import Dict, List
from .workday import search_alphawave, extract as wd_extract, get_company

SITE = "Alphawave"
SECTIONS = get_company("Alphawave").get("sections", [])


def search(keywords: List[str] = None, location: str = "",
           max_results: int = 10, **kwargs) -> List[Dict]:
    """Search Alphawave jobs via Workday API."""
    return search_alphawave(keywords, location, max_results)


def extract(html: str, url: str = "") -> Dict[str, str]:
    """Extract job details from an Alphawave Workday job page."""
    return wd_extract(html, url)
