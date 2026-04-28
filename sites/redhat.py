"""
Red Hat Careers — Workday-powered (thin wrapper around sites.workday).

Search: workday Workday API (redhat.wd5.myworkdayjobs.com)
Details: JSON-LD from job detail pages.
"""

from typing import Dict, List
from .workday import search_redhat, extract as wd_extract, get_company

SITE = "RedHat"
SECTIONS = get_company("RedHat").get("sections", [])


def search(keywords: List[str] = None, location: str = "",
           max_results: int = 10, **kwargs) -> List[Dict]:
    """Search Red Hat jobs via Workday API."""
    return search_redhat(keywords, location, max_results)


def extract(html: str, url: str = "") -> Dict[str, str]:
    """Extract job details from a Red Hat Workday job page."""
    return wd_extract(html, url)
