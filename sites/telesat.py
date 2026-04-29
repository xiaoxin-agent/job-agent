"""
Telesat — Lever-powered job board.

Thin wrapper around the universal Lever adapter.
"""

from typing import Dict, List, Optional
from sites.lever import search_telesat as lever_search

SITE = "Telesat"


def search(keywords: List[str] = None, location: str = "",
           max_results: int = 10, **kwargs) -> List[Dict]:
    if not keywords:
        keywords = ["Software", "Engineer"]
    return lever_search(keywords, location, max_results)
