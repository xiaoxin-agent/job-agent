"""
Generic Lever job board adapter.

Lever is a common ATS used by many companies.
API: GET https://api.lever.co/v0/postings/{company}?limit=100
Returns full job listings with plain-text descriptions.
"""

from typing import Dict, List, Optional
import re
import json
import requests


LEVER_COMPANIES: Dict[str, Dict] = {}


def get_company(company_key: str) -> Optional[Dict]:
    return LEVER_COMPANIES.get(company_key)


def add_company(key: str, slug: str, company: str) -> None:
    """Register a Lever company."""
    LEVER_COMPANIES[key] = {
        "slug": slug,
        "company": company,
    }


# Register known Lever companies
add_company("Fullscript", "fullscript", "Fullscript")
add_company("MagnetForensics", "magnetforensics", "Magnet Forensics")


def search(company_key: str, keywords: List[str] = None,
           location: str = "", max_results: int = 10) -> List[Dict]:
    """Search jobs for a Lever-hosted company."""
    config = LEVER_COMPANIES.get(company_key)
    if not config:
        return []

    if not keywords:
        keywords = ["Software", "Developer"]
    kw_lower = [k.lower() for k in keywords]

    try:
        resp = requests.get(
            f"https://api.lever.co/v0/postings/{config['slug']}?limit=100",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    jobs = []
    company_name = config["company"]
    for job in data:
        title = job.get("text", "")
        title_lower = title.lower()

        # Keyword filter
        if not any(kw in title_lower for kw in kw_lower):
            continue

        categories = job.get("categories", {}) or {}
        location_str = categories.get("location", "") or ""
        commitment = categories.get("commitment", "") or ""
        team = categories.get("team", "") or ""

        # Location filter
        if location and location.lower() not in ("remote", "global"):
            loc_lower = location.lower()
            loc_ok = False
            for part in loc_lower.split(","):
                part = part.strip()
                if part and part in location_str.lower():
                    loc_ok = True
                    break
            if not loc_ok:
                user_w = {w for w in re.split(r"[\s,]+", loc_lower) if len(w) > 2}
                txt_w = {w for w in re.split(r"[\s,\/]+", location_str.lower()) if len(w) > 2}
                if user_w & txt_w:
                    loc_ok = True
            if not loc_ok:
                continue

        detail_url = job.get("hostedUrl", "")
        desc_plain = job.get("descriptionPlain", "") or ""
        if desc_plain:
            desc = f"<p>{desc_plain.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace(chr(10), '<br>')}</p>"
        else:
            desc = title

        jobs.append({
            "title": title,
            "company": company_name,
            "location": location_str,
            "description": desc,
            "url": detail_url,
            "source": company_key,
            "date": str(job.get("createdAt", "") or ""),
            "job_type": commitment or "Full-Time",
            "remote": "",
            "departments": [team] if team else [],
            "salary_min": 0,
            "salary_max": 0,
            "currency": "USD",
        })

    return jobs[:max_results]


def search_fullscript(keywords: List[str] = None, location: str = "",
                      max_results: int = 10) -> List[Dict]:
    return search("Fullscript", keywords, location, max_results)


def search_magnetforensics(keywords: List[str] = None, location: str = "",
                            max_results: int = 10) -> List[Dict]:
    return search("MagnetForensics", keywords, location, max_results)
