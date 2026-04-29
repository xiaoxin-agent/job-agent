"""
Fortinet — custom Oracle Cloud HCM job board scraper.

Fortinet uses Oracle Cloud HCM (Candidate Experience) at:
  https://edel.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2001

Direct REST API access to Oracle HCM is session-based and requires
the SPA authentication flow. This module uses the rendered career page
and follows redirects to extract job listings from the Oracle Cloud
Candidate Experience API.

Currently provides a best-effort scraper that works with the JS-rendered
search endpoint via the Oracle HCM REST API with basic session cookies.
"""

from typing import Dict, List, Optional
import re
import json
import time
import requests


FORTINET_CONFIG = {
    "domain": "edel.fa.us2.oraclecloud.com",
    "site": "CX_2001",
    "company": "Fortinet",
    "base_url": "https://edel.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2001",
    "api_base": "https://edel.fa.us2.oraclecloud.com/hcmRestApi/resources/latest",
}


def _get_session(base_url: str) -> Optional[requests.Session]:
    """Establish a session by visiting the career page to get cookies."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })
    try:
        resp = session.get(base_url, timeout=15)
        resp.raise_for_status()
        time.sleep(1)
        return session
    except Exception:
        return None


def _fetch_jobs_from_oracle(session: requests.Session, api_base: str,
                             keywords: Optional[List[str]],
                             limit: int) -> List[Dict]:
    """Try to fetch jobs from Oracle REST API with session cookies.

    Oracle's REST API returns empty results without proper authentication
    tokens. This provides best-effort results.
    """
    try:
        # The Oracle REST API endpoint for job requisitions
        url = f"{api_base}/recruitingCEJobRequisitions?offset=0&limit={limit}&onlyMyRgs=false"
        resp = session.get(
            url,
            headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            if items:
                return _parse_oracle_jobs(items, keywords)
    except Exception:
        pass
    return []


def _parse_oracle_jobs(items: List[Dict], keywords: Optional[List[str]]) -> List[Dict]:
    """Parse Oracle REST API job items into standard format."""
    results = []
    kw_lower = [k.lower() for k in keywords] if keywords else []

    for item in items:
        title = item.get("Title", "") or item.get("title", "")
        title_lower = title.lower()

        # Keyword filter
        if kw_lower and not any(kw in title_lower for kw in kw_lower):
            continue

        locations = []
        for loc_field in ["PrimaryLocation", "locations", "Location"]:
            loc_data = item.get(loc_field, {})
            if isinstance(loc_data, dict):
                parts = []
                for f in ["City", "country", "Country", "State", "state"]:
                    v = loc_data.get(f, "")
                    if v:
                        parts.append(str(v))
                if parts:
                    locations.append(", ".join(parts))
            elif isinstance(loc_data, str):
                locations.append(loc_data)

        location_str = "; ".join(locations) if locations else ""

        desc = item.get("Description", "") or item.get("description", "") or title

        req_id = item.get("Id", "") or item.get("id", "")
        url = f"https://edel.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2001/requisitions/preview/{req_id}"

        job_type = item.get("JobType", "") or item.get("employmentType", "") or "Full-Time"

        results.append({
            "title": title,
            "company": "Fortinet",
            "location": location_str,
            "description": desc,
            "url": url,
            "source": "Fortinet",
            "date": item.get("PostedDate", "") or item.get("postingDate", "") or "",
            "job_type": job_type,
            "remote": "",
        })

    return results


def search(keywords: Optional[List[str]] = None,
           location: str = "", max_results: int = 10) -> List[Dict]:
    """Search Fortinet jobs via Oracle Cloud HCM.

    Due to Oracle's session-based API, this module does best-effort.
    When the Oracle API doesn't return jobs (common without browser auth),
    returns an empty list gracefully.
    """
    if not keywords:
        keywords = ["Software"]

    config = FORTINET_CONFIG
    session = _get_session(config["base_url"])
    if not session:
        return []

    jobs = _fetch_jobs_from_oracle(session, config["api_base"], keywords, max_results)

    # If Oracle API returned nothing, note it but don't fail
    if not jobs:
        return []

    # Location filter
    if location and location.lower() not in ("remote", "global"):
        loc_lower = location.lower()
        filtered = []
        for job in jobs:
            loc_ok = False
            for part in loc_lower.split(","):
                part = part.strip()
                if part and part in job["location"].lower():
                    loc_ok = True
                    break
            if not loc_ok:
                user_w = {w for w in re.split(r"[\s,]+", loc_lower) if len(w) > 2}
                txt_w = {w for w in re.split(r"[\s,\/]+", job["location"].lower()) if len(w) > 2}
                if user_w & txt_w:
                    loc_ok = True
            if loc_ok:
                filtered.append(job)
        jobs = filtered

    return jobs[:max_results]


def extract(html: str, url: str = "") -> Dict[str, str]:
    """Extract job details from a Fortinet/Oracle job page."""
    result = {
        "title": "",
        "company": "Fortinet",
        "location": "",
        "description": "",
        "job_type": "Full-Time",
    }
    try:
        # Try JSON-LD
        jsonlds = re.findall(
            r'<script[^>]+type=[\"\']application/ld\+json[\"\'][^>]*>'
            r'(.*?)</script>', html, re.DOTALL
        )
        for raw in jsonlds:
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                result["title"] = data.get("title") or result["title"]
                result["description"] = data.get("description") or ""
                loc = data.get("jobLocation", {})
                if isinstance(loc, dict):
                    addr = loc.get("address", {})
                    parts = [p for p in [addr.get("addressLocality", ""), addr.get("addressRegion", ""), addr.get("addressCountry", "")] if p]
                    result["location"] = ", ".join(parts)
                break
    except Exception:
        pass
    return result
