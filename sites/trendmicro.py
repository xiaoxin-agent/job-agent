"""
Trend Micro — Workday-powered job board.

Thin wrapper around the universal Workday adapter.
"""

from typing import Dict, List, Optional
from sites.workday import search_trendmicro as workday_search

SITE = "TrendMicro"


def search(keywords: List[str] = None, location: str = "",
           max_results: int = 10, **kwargs) -> List[Dict]:
    if not keywords:
        keywords = ["Software", "Developer"]
    return workday_search(keywords, location, max_results)
