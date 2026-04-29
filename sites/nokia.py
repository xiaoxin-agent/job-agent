"""
Nokia — Oracle Cloud HCM job board scraper.

Nokia uses Oracle Cloud HCM (Candidate Experience) at:
  https://jobs.nokia.com/en/sites/CX_1

The SPA uses a REST API with a custom finder URL format similar to Fortinet.
"""

from typing import Dict, List, Optional
import json
import re
import requests

SITE = "Nokia"

SITE_NUMBER = "CX_1"
API_BASE = "https://jobs.nokia.com/rest"
CAREERS_URL = "https://jobs.nokia.com/en/sites/CX_1"

WORKPLACE_MAP = {
    "ORA_ON_SITE": "On-site",
    "ORA_HYBRID": "Hybrid",
    "ORA_REMOTE": "Remote",
}

_COUNTRY_WHITELIST = {"CA", "US"}


def _build_finder_url(keyword: str = "", location: str = "",
                      limit: int = 25, offset: int = 0) -> str:
    """Build the Oracle HCM finder URL for Nokia."""
    finder_params = {
        "siteNumber": SITE_NUMBER,
        "limit": limit,
        "offset": offset,
    }
    if keyword:
        finder_params["keyword"] = keyword
    if location and location.lower() not in ("remote", "global"):
        finder_params["location"] = location

    finder_encoded = requests.utils.quote(json.dumps(finder_params))
    url = (
        f"{API_BASE}/recruitingCEJobRequisitions"
        f"?onlyData=true"
        f"&expand=requisitionList.secondaryLocations"
        f"&finder=findReqs;:findParams:{finder_encoded}"
    )
    return url


def _call_api(url: str) -> List[Dict]:
    """Call the Nokia Oracle HCM REST API and return the job list."""
    try:
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        }, timeout=20)
        if resp.status_code != 200:
            return []
        raw = resp.text
        # Response is a JSON-encoded string — double-parse
        if raw.startswith('"'):
            data = json.loads(json.loads(raw))
        else:
            data = json.loads(raw)
        items = data.get("items", [])
        if not items:
            return []
        return items[0].get("requisitionList", [])
    except Exception:
        return []


def _parse_job(raw_job: Dict) -> Dict:
    """Parse a raw Oracle HCM job dict into our standard format."""
    title = raw_job.get("Title", "")
    location = raw_job.get("PrimaryLocation", "")
    country = raw_job.get("PrimaryLocationCountry", "")

    # Build description from available fields
    desc_parts = []
    if raw_job.get("ExternalResponsibilitiesStr"):
        desc_parts.append(raw_job["ExternalResponsibilitiesStr"])
    if raw_job.get("ExternalQualificationsStr"):
        desc_parts.append(raw_job["ExternalQualificationsStr"])
    if not desc_parts and raw_job.get("ShortDescriptionStr"):
        desc_parts.append(raw_job["ShortDescriptionStr"])
    description = "\n\n".join(desc_parts)

    job_id = raw_job.get("Id", "")
    apply_url = f"{CAREERS_URL}/requisition/job/{job_id}" if job_id else CAREERS_URL

    posted_date = raw_job.get("PostedDate", "")

    wp_code = raw_job.get("WorkplaceTypeCode", "")
    job_type = WORKPLACE_MAP.get(wp_code, raw_job.get("WorkplaceType", ""))

    is_remote = "Remote" if job_type == "Remote" else ""

    # Detect Canada via country code or location text
    is_canada = country == "CA" or "Canada" in location or "ON" in location

    return {
        "title": title,
        "company": "Nokia",
        "location": location,
        "description": description,
        "url": apply_url,
        "source": "Nokia",
        "date": posted_date,
        "job_type": job_type,
        "remote": is_remote,
    }


def search(keywords: List[str] = None, location: str = "",
           max_results: int = 10, **kwargs) -> List[Dict]:
    """Search Nokia jobs."""
    if not keywords:
        keywords = ["Software", "Engineer"]
    kw_lower = set(k.lower() for k in keywords)

    # Try with keyword search
    keyword = keywords[0] if keywords else ""
    url = _build_finder_url(keyword=keyword, location=location,
                            limit=min(max_results * 5, 100), offset=0)
    raw_jobs = _call_api(url)

    # The Nokia API pagination is limited (always returns same 25 jobs).
    # We'll filter what we get.
    jobs = []
    seen_ids = set()
    for rj in raw_jobs:
        jid = rj.get("Id", "")
        if jid in seen_ids:
            continue
        seen_ids.add(jid)

        title = rj.get("Title", "").lower()
        title_words = set(re.split(r"[\s\-/]+", title))

        # Keyword match
        if not any(kw in title for kw in kw_lower):
            # Also check ShortDescriptionStr
            desc = (rj.get("ShortDescriptionStr") or "").lower()
            if not any(kw in desc for kw in kw_lower):
                continue

        country = rj.get("PrimaryLocationCountry", "")
        loc_text = rj.get("PrimaryLocation", "")

        # Location filter
        if location and location.lower() not in ("remote", "global"):
            loc_lower = location.lower()
            loc_ok = False
            if country == "CA" and any(p.strip() in loc_lower
                                       for p in ["canada", "on", "ottawa",
                                                  "toronto", "montreal",
                                                  "vancouver", "calgary"]):
                loc_ok = True
            if not loc_ok and loc_lower in loc_text.lower():
                loc_ok = True
            if not loc_ok:
                user_w = {w for w in re.split(r"[\s,]+", loc_lower) if len(w) > 2}
                txt_w = {w for w in re.split(r"[\s,\/]+", loc_text.lower()) if len(w) > 2}
                if user_w & txt_w:
                    loc_ok = True
            if not loc_ok and country != "CA":
                continue
            if not loc_ok:
                continue

        parsed = _parse_job(rj)
        jobs.append(parsed)

        if len(jobs) >= max_results:
            break

    return jobs[:max_results]


def fetch_job_details(job_id: str) -> Optional[Dict]:
    """Fetch a single job by ID for detailed description."""
    url = _build_finder_url(limit=1, offset=0)
    try:
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        }, timeout=20)
        if resp.status_code != 200:
            return None
        raw = resp.text
        if raw.startswith('"'):
            data = json.loads(json.loads(raw))
        else:
            data = json.loads(raw)
        items = data.get("items", [])
        if not items:
            return None
        for rj in items[0].get("requisitionList", []):
            if rj.get("Id", "") == job_id:
                return _parse_job(rj)
    except Exception:
        pass
    return None
