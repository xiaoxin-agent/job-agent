"""
Fullscript Careers — Lever-powered (thin wrapper around sites.lever).

Search: Lever API (api.lever.co/v0/postings/fullscript)
Details: Lever API includes full description.
"""

from typing import Dict, List
from .lever import search_fullscript

SITE = "Fullscript"


def search(keywords: List[str] = None, location: str = "",
           max_results: int = 10, **kwargs) -> List[Dict]:
    """Search Fullscript jobs via Lever API."""
    return search_fullscript(keywords, location, max_results)


def extract(html: str, url: str = "") -> Dict[str, str]:
    """Extract job details from a Fullscript Lever job page."""
    result = {
        "title": "",
        "company": "Fullscript",
        "location": "",
        "description": "",
        "job_type": "Full-Time",
    }
    try:
        import json, re
        jsonlds = re.findall(
            r'<script[^>]+type=[\"\']application/ld\+json[\"\'][^>]*>'
            r'(.*?)</script>', html, re.DOTALL
        )
        for raw in jsonlds:
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                result["title"] = data.get("title") or result["title"]
                desc = data.get("description") or ""
                if desc:
                    result["description"] = f"<p>{desc.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}</p>"
                loc = data.get("jobLocation", {})
                if isinstance(loc, dict):
                    addr = loc.get("address", {})
                    parts = [p for p in [addr.get("addressLocality", ""), addr.get("addressRegion", ""), addr.get("addressCountry", "")] if p]
                    result["location"] = ", ".join(parts)
                break
    except Exception:
        pass
    return result
