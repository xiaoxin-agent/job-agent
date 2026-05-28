"""
Trend Micro — Workday-powered job board.

Thin wrapper around the universal Workday adapter.
"""

from typing import Dict, List, Optional
from sites.workday import search_trendmicro as workday_search
from sites.workday import extract as wd_extract, get_company

SITE = "TrendMicro"
SECTIONS = get_company("TrendMicro").get("sections", []) if get_company("TrendMicro") else []


def search(keywords: List[str] = None, location: str = "",
           max_results: int = 10, **kwargs) -> List[Dict]:
    if not keywords:
        keywords = ["Software", "Developer"]
    return workday_search(keywords, location, max_results)


def extract(html: str, url: str = "") -> Dict[str, str]:
    """Extract job details from a Trend Micro Workday job page."""
    return wd_extract(html, url)
