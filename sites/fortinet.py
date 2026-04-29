"""
Fortinet — Oracle Cloud HCM job board scraper using the SPA's REST API.

Fortinet uses Oracle Cloud HCM (Candidate Experience) at:
  https://edel.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2001

The SPA uses a REST API with a custom finder URL format:
  /recruitingCEJobRequisitions?onlyData=true&finder=findReqs;:findParams:{JSON}

This module directly calls that API with the finder parameters encoded
in the URL, bypassing the need for a browser session.
"""

from typing import Dict, List, Optional
import json
import re
import requests

API_VERSION = "11.13.18.05"

FORTINET_CONFIG = {
    "domain": "edel.fa.us2.oraclecloud.com",
    "site": "CX_2001",
    "company": "Fortinet",
    "careers_url": "https://edel.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2001",
}

_CANADA_LOCATION_ID = "300000000361286"


def _build_finder_url(keyword: str = "", location: str = "",
                      location_id: str = "", limit: int = 25,
                      offset: int = 0) -> str:
    """Build the Oracle HCM REST URL with finder parameters.

    The URL format is:
      /hcmRestApi/resources/{version}/recruitingCEJobRequisitions
        ?onlyData=true
        &expand=requisitionList.secondaryLocations,requisitionList.workLocation,...
        &finder=findReqs;:findParams:{URL_ENCODED_JSON}

    The findParams JSON contains all search criteria.
    """
    find_params = {
        "siteNumber": FORTINET_CONFIG["site"],
        "limit": limit,
        "offset": offset,
    }
    if keyword:
        find_params["keyword"] = keyword
    if location:
        find_params["location"] = location
    if location_id:
        find_params["locationId"] = location_id
        find_params["locationLevel"] = "country"

    params_json = json.dumps(find_params, ensure_ascii=False)

    # The URL needs the params JSON URL-encoded in the finder suffix
    from urllib.parse import quote
    return (
        f"https://{FORTINET_CONFIG['domain']}/hcmRestApi/resources/{API_VERSION}"
        f"/recruitingCEJobRequisitions"
        f"?onlyData=true"
        f"&expand=requisitionList.secondaryLocations,requisitionList.workLocation,"
        f"requisitionList.otherWorkLocations"
        f"&finder=findReqs;:findParams:{quote(params_json)}"
    )


def _call_api(session: requests.Session, url: str) -> Dict:
    """Call the Oracle HCM REST API and return parsed JSON."""
    resp = session.get(
        url,
        headers={
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def _parse_jobs(data: Dict) -> List[Dict]:
    """Parse Oracle REST API response into standard format."""
    results = []
    items = data.get("items", [])
    if not items:
        return results

    req_list = items[0].get("requisitionList", [])

    for req in req_list:
        title = req.get("Title", "") or ""
        # PrimaryLocation is a string like "Burnaby, BC, Canada"
        location = req.get("PrimaryLocation", "") or ""
        posted = req.get("PostedDate", "") or ""
        req_id = req.get("Id", "") or ""
        desc = req.get("ShortDescriptionStr", "") or ""

        # Clean up HTML-like artifacts in description
        desc_plain = re.sub(r"<[^>]+>", " ", desc)
        desc_plain = re.sub(r"\s+", " ", desc_plain).strip()

        detail_url = (
            f"https://edel.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/"
            f"en/sites/{FORTINET_CONFIG['site']}/requisitions/preview/{req_id}"
        )

        # Job type / workplace type
        workplace_type = req.get("WorkplaceType", "") or ""
        remote = ""
        if workplace_type:
            wt = workplace_type.lower()
            if "remote" in wt:
                remote = "Remote"
            elif "hybrid" in wt:
                remote = "Hybrid"

        job_type = req.get("WorkerType", "") or req.get("JobType", "") or "Full-Time"

        results.append({
            "title": title,
            "company": "Fortinet",
            "location": location,
            "description": f"<p>{desc_plain}</p>",
            "url": detail_url,
            "source": "Fortinet",
            "date": posted,
            "job_type": job_type,
            "remote": remote,
        })

    return results


def search(keywords: Optional[List[str]] = None,
           location: str = "", max_results: int = 10) -> List[Dict]:
    """Search Fortinet jobs via Oracle Cloud HCM API.

    Uses the SPA's internal finder API with keyword and optional location filtering.
    """
    if not keywords:
        keywords = []

    keyword = " ".join(keywords) if keywords else ""

    # Determine location filter: if "Canada" or Canadian city, use Canada locationId
    location_id = ""
    location_api = ""
    loc_lower = location.lower()
    if any(city in loc_lower for city in ["canada", "ottawa", "kanata", "toronto",
                                            "montreal", "vancouver", "burnaby",
                                            "calgary", "edmonton", "waterloo",
                                            "mississauga", "markham"]):
        location_id = _CANADA_LOCATION_ID
        location_api = location if location else "Canada"
    elif loc_lower in ("remote", "global", ""):
        pass  # no location filter
    else:
        # For other locations, pass through
        location_id = _CANADA_LOCATION_ID
        location_api = location

    # Try with location filter first
    url = _build_finder_url(keyword=keyword, location=location_api,
                            location_id=location_id, limit=max_results)

    session = requests.Session()
    session.headers.update({
        "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"),
        "Accept-Language": "en-US,en;q=0.9",
    })

    try:
        # Initialize session by visiting the career page
        session.get(FORTINET_CONFIG["careers_url"],
                    headers={"Accept": "text/html"},
                    timeout=15)

        data = _call_api(session, url)
        all_jobs = _parse_jobs(data)

        # If location was specified as "Canada" but the API may have returned
        # global results (the locationId/Location filters are soft),
        # do a client-side Canada filter
        if location and "canada" in loc_lower:
            all_jobs = [j for j in all_jobs if "Canada" in j.get("location", "")]

        return all_jobs[:max_results]

    except Exception as e:
        # Log and return empty — better than crashing
        return []


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
                    parts = [p for p in [
                        addr.get("addressLocality", ""),
                        addr.get("addressRegion", ""),
                        addr.get("addressCountry", "")
                    ] if p]
                    result["location"] = ", ".join(parts)
                break
    except Exception:
        pass
    return result
