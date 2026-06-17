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
    """Extract job details from a Fortinet/Oracle job page.

    Oracle HCM / Redwood SPA pages do NOT embed JSON-LD.
    Extraction strategy (priority order):
      1. Parse OG meta tags (present in SPA server-rendered shell)
      2. Extract job ID from URL and try the REST API (finder with keyword)
      3. Fall back to <title> tag
    """
    result = {
        "title": "",
        "company": "Fortinet",
        "location": "",
        "description": "",
        "job_type": "Full-Time",
    }

    # --- Priority 1: OG meta tags (present in server-rendered SPA shell) ---
    title_m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html)
    if title_m:
        result["title"] = title_m.group(1).strip()

    desc_m = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)', html)
    if desc_m:
        result["description"] = desc_m.group(1).strip()

    # --- Priority 2: Try OG meta locale / site_name for location hints ---
    # (no explicit location in OG for Oracle HCM, leave empty unless found)

    # --- Attempt REST API for richer data (title, location, full description) ---
    try:
        job_id = _extract_job_id_from_url(url)
        if job_id:
            api_result = _fetch_job_by_id(job_id)
            if api_result:
                # API data is more complete — override OG values
                if api_result.get("title"):
                    result["title"] = api_result["title"]
                if api_result.get("location"):
                    result["location"] = api_result["location"]
                if api_result.get("description"):
                    result["description"] = api_result["description"]
                if api_result.get("job_type"):
                    result["job_type"] = api_result["job_type"]
    except Exception:
        pass

    # --- Priority 3: <title> tag fallback ---
    if not result["title"]:
        title_tag = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
        if title_tag:
            result["title"] = title_tag.group(1).strip()

    return result


def _extract_job_id_from_url(url: str) -> Optional[str]:
    """Extract the numeric job/requisition ID from an Oracle HCM job URL.

    Matches patterns like:
      .../job/22476
      .../requisitions/preview/22476
      .../CX_2001/job/22476/...
    """
    m = re.search(r'/(?:job|requisitions/preview)/(\d+)', url)
    if m:
        return m.group(1)
    return None


def _fetch_job_by_id(job_id: str) -> Optional[Dict]:
    """Fetch a single job's full details via its numeric ID using the Oracle HCM
    `recruitingCEJobRequisitionDetails` REST API endpoint.

    Unlike the finder API (which only returns 25 results sorted by relevancy),
    this endpoint supports direct ID lookup and returns the complete job
    description, qualifications, responsibilities, and location details.
    """
    url = (
        f"https://{FORTINET_CONFIG['domain']}/hcmRestApi/resources/{API_VERSION}"
        f"/recruitingCEJobRequisitionDetails/{job_id}"
        f"?onlyData=true"
    )

    session = requests.Session()
    session.headers.update({
        "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"),
        "Accept-Language": "en-US,en;q=0.9",
    })

    try:
        # Warm the session with a visit to the career page
        session.get(FORTINET_CONFIG["careers_url"],
                    headers={"Accept": "text/html"},
                    timeout=15)
        resp = session.get(
            url,
            headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
            timeout=15,
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        if not data or not data.get("Id"):
            return None

        title = data.get("Title", "") or ""

        # Description: use ExternalDescriptionStr (full HTML), or short description as fallback
        desc_html = data.get("ExternalDescriptionStr", "") or \
                    data.get("ShortDescriptionStr", "") or ""

        # Extract location from GeographyId, or fall back to extracting from description
        location = _resolve_geography_location(
            session, data.get("GeographyId"), data.get("GeographyNodeId")
        )
        if not location:
            location = _extract_location_from_desc(desc_html)

        # Also append Qualifications/Responsibilities if available as separate fields
        quals = data.get("ExternalQualificationsStr", "") or ""
        respos = data.get("ExternalResponsibilitiesStr", "") or ""
        if quals and "</ul>" not in desc_html[-50:]:
            desc_html += f"\n<h3>Qualifications</h3>\n{quals}"
        if respos and "</ul>" not in desc_html[-50:]:
            desc_html += f"\n<h3>Responsibilities</h3>\n{respos}"

        job_schedule = data.get("JobSchedule", "") or "Full time"
        study_level = data.get("StudyLevel", "") or ""

        return {
            "title": title,
            "location": location,
            "description": desc_html,
            "job_type": job_schedule,
            "education": study_level,
        }
    except Exception:
        pass

    return None


def _resolve_geography_location(session: requests.Session,
                                 geography_id, geography_node_id) -> str:
    """Resolve GeographyId / GeographyNodeId to a human-readable location string
    using the Oracle HCM Geography REST API (if available).
    The Geography API is often restricted; falls back to empty string."""
    gid = geography_id or geography_node_id
    if not gid:
        return ""
    try:
        url = (
            f"https://{FORTINET_CONFIG['domain']}/hcmRestApi/resources/{API_VERSION}"
            f"/recruitingCEGeography/{gid}?onlyData=true"
        )
        resp = session.get(
            url,
            headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
            timeout=10,
        )
        if resp.status_code == 200:
            geo = resp.json()
            parts = []
            for key in ["City", "Province", "Country", "Name"]:
                val = geo.get(key, "")
                if val:
                    parts.append(val)
            if parts:
                return ", ".join(parts)
    except Exception:
        pass
    return ""


def _extract_location_from_desc(desc_html: str) -> str:
    """Fallback: extract location info from job description HTML/plain text.
    Looks for common patterns like 'in Ottawa', 'Ottawa, ON', etc."""
    # Strip HTML tags for plain text search
    text = re.sub(r'<[^>]+>', ' ', desc_html)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'\s+', ' ', text)

    # Pattern: "in {City}" or "to our {City}" or "{City}, {Province}"
    # Known Canadian cities + provinces
    _cities = [
        "Ottawa", "Toronto", "Vancouver", "Montreal", "Calgary",
        "Edmonton", "Winnipeg", "Burnaby", "Mississauga", "Brampton",
        "Hamilton", "Quebec City", "Kitchener", "Waterloo", "London",
        "Halifax", "Victoria", "Saskatoon", "Regina", "Markham",
        "Richmond Hill", "Kanata", "Oakville", "Burlington", "Gatineau",
    ]
    for city in _cities:
        m = re.search(rf'\b(?:in|to|at|near|for)\s+{re.escape(city)}\b', text, re.IGNORECASE)
        if m:
            return city
    # Broader: any capitalized city name (2+ words allowed) followed by province or country
    m = re.search(r'\b([A-Z][a-z]+(?:[- ][A-Z][a-z]+)*),\s*(?:ON|QC|BC|AB|SK|MB|NS|NB|NL|PE|YT|NT|NU|Canada)\b', text)
    if m:
        return m.group(1)
    return ""
