"""
BlackBerry QNX Careers — Workday-powered (thin wrapper around sites.workday).

Search: Workday API (bb.wd3.myworkdayjobs.com/BlackBerry)
Details: JSON-LD from job detail pages.
"""

from typing import Dict, List
from .workday import search_blackberry, extract as wd_extract, get_company

SITE = "BlackBerry"
SECTIONS = get_company("BlackBerry").get("sections", [])


def search(keywords: List[str] = None, location: str = "",
           max_results: int = 10, **kwargs) -> List[Dict]:
    """Search BlackBerry jobs via Workday API."""
    return search_blackberry(keywords, location, max_results)


def extract(html: str, url: str = "") -> Dict[str, str]:
    """Extract job details from a BlackBerry Workday job page."""
    return wd_extract(html, url)
