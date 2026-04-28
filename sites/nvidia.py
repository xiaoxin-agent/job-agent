"""
NVIDIA Careers — Workday-powered (thin wrapper around sites.workday).

Search: Workday API (nvidia.wd5.myworkdayjobs.com)
Details: JSON-LD from job detail pages.
"""

from typing import Dict, List
from .workday import search_nvidia, extract as wd_extract

SITE = "NVIDIA"


def search(keywords: List[str] = None, location: str = "",
           max_results: int = 10, **kwargs) -> List[Dict]:
    """Search NVIDIA jobs via Workday API."""
    return search_nvidia(keywords, location, max_results)


def extract(html: str, url: str = "") -> Dict[str, str]:
    """Extract job details from a NVIDIA Workday job page."""
    return wd_extract(html, url)
