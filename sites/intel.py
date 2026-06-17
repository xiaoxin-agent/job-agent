"""
Intel Careers — Workday-powered (thin wrapper around sites.workday).

Intel uses Workday ATS at:
  https://intel.wd1.myworkdayjobs.com/en-US/External/

Search: Workday API (intel.wd1.myworkdayjobs.com)
Details: JSON-LD from job detail pages, enhanced with REST API fallback.
"""

from typing import Dict, List
from .workday import search_intel, extract as wd_extract, get_company

SITE = "Intel"
SECTIONS = get_company("Intel").get("sections", [])


def search(keywords: List[str] = None, location: str = "",
           max_results: int = 10, **kwargs) -> List[Dict]:
    """Search Intel jobs via Workday API."""
    return search_intel(keywords, location, max_results)


def extract(html: str, url: str = "") -> Dict[str, str]:
    """Extract job details from an Intel Workday job page."""
    return wd_extract(html, url)
