"""
SUSE Careers — Workday-powered (thin wrapper around sites.workday).

Search: Workday API (suse.wd3.myworkdayjobs.com)
Details: JSON-LD from job detail pages.
"""

from typing import Dict, List
from .workday import search_suse, extract as wd_extract

SITE = "SUSE"


def search(keywords: List[str] = None, location: str = "",
           max_results: int = 10, **kwargs) -> List[Dict]:
    """Search SUSE jobs via Workday API."""
    return search_suse(keywords, location, max_results)


def extract(html: str, url: str = "") -> Dict[str, str]:
    """Extract job details from a SUSE Workday job page."""
    return wd_extract(html, url)
