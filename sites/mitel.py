"""
Mitel Careers — Workday-powered (thin wrapper around sites.workday).

Search: Mitel Workday API (mitel.wd3.myworkdayjobs.com/mitelcareers)
"""

from typing import Dict, List
from .workday import search_mitel, extract as wd_extract, get_company

SITE = "Mitel"
SECTIONS = get_company("Mitel").get("sections", [])


def search(keywords: List[str] = None, location: str = "",
           max_results: int = 10, **kwargs) -> List[Dict]:
    """Search Mitel jobs via Workday API."""
    return search_mitel(keywords, location, max_results)


def extract(html: str, url: str = "") -> Dict[str, str]:
    """Extract job details from a Mitel Workday job page."""
    return wd_extract(html, url)
