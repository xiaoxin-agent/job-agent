"""
Nokia — Oracle Cloud HCM job board scraper.

Nokia uses Oracle Cloud HCM (Candidate Experience) at:
  https://jobs.nokia.com/en/sites/CX_1

The SPA uses a REST API with a custom finder URL format similar to Fortinet.


!! IMPORTANT — Known API Limitation !!

Nokia's Oracle HCM instance (siteNumber=CX_1) has a SERVER-SIDE RESTRICTION:
the findReqs finder API ALWAYS returns the exact same 25 jobs regardless of
keyword, locationId, offset, or any other filter parameter.

Confirmed facts (investigated 2026-04-29 & 2026-05-05):
- 867 total jobs exist in the database (returned as TotalJobsCount)
- 107 Canada jobs exist (from locationsFacet)
- But the API only ever returns the same 25 "default" jobs
- keyword (e.g. "Engineer") → completely ignored by the API
- locationId (e.g. Canada=300000000471544) → ignored
- selectedLocationsFacet → ignored
- offset (pagination) → returns IDENTICAL 25 jobs, not page 2
- All query parameters fed through findParams mapSearchParamsToRest are ignored

Why this happens:
- The SPA uses the same URL format as Fortinet's WORKING instance
  (/recruitingCEJobRequisitions?onlyData=true&expand=...&finder=findReqs;:findParams:{json})
- The JavaScript code (main-minimal.js v2601.16.260640537) DOES pass keyword,
  locationId, offset correctly through P(e,g) param mapping
- The "24" resource version in mapSearchParamsToRest(e, siteNumber, 24, t) is
  identical between working (Fortinet CX_2001) and broken (Nokia CX_1) instances
- The difference is server-side config: Nokia's Oracle Cloud tenant has restricted
  the API to 25 unfilterable results; Fortinet's tenant allows full access

What the website shows:
- The SPA page at jobs.nokia.com is 100% JS-rendered — NO server-side data
- It calls the SAME restricted API and gets the SAME 25 jobs
- Client-side JS filters by keyword/location (React state)
- So the website ALSO only displays from these 25 jobs
- The "89 Open Jobs" shown on the site is the TotalJobsCount for Canada from
  locationsFacet metadata, NOT the actual number of accessible job detail pages

What we've tried (all failed):
1. Direct oraclecloud /hcmRestApi/ endpoint
2. jobs.nokia.com/rest/ proxy
3. jobs.nokia.com/rest/ without /hcmRestApi/resources/{version}/ prefix
4. findParams as separate URL query param (not inline finder)
5. selectedLocationsFacet (SAME) parameter
6. POST to /action/getRequisitionDetailsForMap (empty result)
7. All offsets from 0 to 800 (same 25 jobs repeated)
8. Oracle HCM resource version "24" vs "11.13.18.05" (version 24 not supported)
9. Browser automation not viable (1.3GB disk, and wouldn't bypass server restriction)

Known also affected:
- Nokia job detail pages (e.g. /requisition/job/35679, /requisition/job/34461)
  return 200 but SPA redirects to /404 client-side because Oracle API returns 404
  for individual requisition detail endpoints — jobs can be listed but not viewed.

Module behavior:
- Returns the 25 jobs the API does provide
- Applies client-side keyword/location filter to the available 25
- This is the BEST we can do with the restricted API — full search is impossible
  without Nokia changing their Oracle HCM tenant configuration.

Contrast with Fortinet (sites/fortinet.py):
- Same Oracle HCM platform
- siteNumber=CX_2001 (different tenant/instance)
- keyword, locationId, offset ALL work correctly
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

# Known geography IDs from locationsFacet
LOCATION_IDS = {
    "india": "300000000471745",
    "united states": "300000000480126",
    "canada": "300000000471544",
    "poland": "300000000471967",
    "portugal": "300000000471982",
    "germany": "300000000471987",
    "united kingdom": "300000000471975",
    "china": "300000000471829",
    "finland": "300000000471718",
    "france": "300000000471823",
}


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
        # Try to map location to geography ID (though API ignores it anyway)
        loc_lower = location.lower()
        for loc_name, geo_id in LOCATION_IDS.items():
            if loc_lower == loc_name or loc_name.startswith(loc_lower) or loc_lower.startswith(loc_name):
                finder_params["locationId"] = geo_id
                break
        else:
            finder_params["location"] = location

    finder_encoded = requests.utils.quote(json.dumps(finder_params))
    url = (
        f"{API_BASE}/recruitingCEJobRequisitions"
        f"?onlyData=true"
        f"&expand=requisitionList.secondaryLocations"
        f"&finder=findReqs;:findParams:{finder_encoded}"
    )
    return url


def _call_api(url: str, extract_facets: bool = False) -> tuple:
    """Call the Nokia Oracle HCM REST API.
    
    Returns (job_list, facet_data) tuple.
    facet_data is a dict with locationsFacet, categoriesFacet etc. if available.
    """
    try:
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        }, timeout=20)
        if resp.status_code != 200:
            return [], {}
        raw = resp.text
        # Response is a JSON-encoded string — double-parse
        if raw.startswith('"'):
            data = json.loads(json.loads(raw))
        else:
            data = json.loads(raw)
        items = data.get("items", [])
        if not items:
            return [], {}
        
        item = items[0]
        reqs = item.get("requisitionList", [])
        
        # Extract facet data if available
        facets = {}
        for facet_key in ("locationsFacet", "categoriesFacet", "titlesFacet",
                          "postingDatesFacet", "workplaceTypesFacet"):
            val = item.get(facet_key)
            if val:
                facets[facet_key] = val
        
        # TotalJobsCount
        total = item.get("TotalJobsCount")
        if total:
            facets["TotalJobsCount"] = total
            
        return reqs, facets
    except Exception:
        return [], {}


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
    """Search Nokia jobs.
    
    NOTE: Due to Nokia's Oracle HCM server-side restriction, this function can
    only return from a fixed pool of ~25 jobs. All keyword/location filters are
    applied client-side to those 25. The actual Nokia site has 867 jobs (107 in
    Canada as of 2026-05-05) but the API refuses to return them.
    """
    if not keywords:
        keywords = ["Software", "Engineer"]
    kw_lower = set(k.lower() for k in keywords)

    keyword = keywords[0] if keywords else ""
    url = _build_finder_url(keyword=keyword, location=location,
                            limit=min(max_results * 5, 100), offset=0)
    raw_jobs, _ = _call_api(url)

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

        # Keyword match
        if not any(kw in title for kw in kw_lower):
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
            if not loc_ok and country not in ("CA", "US"):
                continue
            if not loc_ok:
                continue

        parsed = _parse_job(rj)
        jobs.append(parsed)

        if len(jobs) >= max_results:
            break

    return jobs[:max_results]


def fetch_job_details(job_id: str) -> Optional[Dict]:
    """Fetch a single job by ID for detailed description.
    
    NOTE: Due to Nokia's Oracle HCM server-side restriction, individual job
    detail endpoints return 404 even though the job ID exists in search results.
    This function searches the 25 available jobs for a matching ID.
    """
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
