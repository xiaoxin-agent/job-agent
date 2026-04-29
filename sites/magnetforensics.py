"""
Magnet Forensics Careers — Lever-powered (thin wrapper around sites.lever).

Search: Lever API (api.lever.co/v0/postings/magnetforensics)
"""

from typing import Dict, List
from .lever import search_magnetforensics, get_company

SITE = "MagnetForensics"


def search(keywords: List[str] = None, location: str = "",
           max_results: int = 10, **kwargs) -> List[Dict]:
    """Search Magnet Forensics jobs via Lever API."""
    return search_magnetforensics(keywords, location, max_results)


def extract(html: str, url: str = "") -> Dict[str, str]:
    """Magnet Forensics jobs use the Lever hosted posting page."""
    return {
        "title": "",
        "company": "Magnet Forensics",
        "location": "",
        "description": "",
        "job_type": "Full-Time",
    }
