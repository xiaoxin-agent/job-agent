"""
Amazon Canada job search.

Amazon uses its own jobs portal at amazon.jobs with a JSON search API.
The API returns paginated results with rich location data.

API endpoint:
  GET /en-gb/search.json?offset=0&result_limit=20&sort=recent&country=CAN

Keywords are passed via ?text=... parameter.
"""

from typing import List, Dict, Optional
import re
import json
import logging
import time

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://www.amazon.jobs/en-gb/search.json"
COUNTRY_CODE = "CAN"  # Canada


def _fetch_page(offset: int = 0, limit: int = 20, keywords: List[str] = None,
                location: str = "") -> Dict:
    """
    Fetch one page of Amazon jobs.

    Amazon's search API:
      country=CAN filters to Canada
      text=... searches across all fields
    """
    params = {
        "offset": offset,
        "result_limit": limit,
        "sort": "recent",
        "country": COUNTRY_CODE,
    }

    if keywords:
        params["text"] = " ".join(keywords)

    try:
        resp = requests.get(
            API_BASE,
            params=params,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Accept": "application/json",
            },
            timeout=20,
        )
        if resp.status_code != 200:
            logger.warning(f"Amazon API returned {resp.status_code}")
            return {"hits": 0, "jobs": []}
        return resp.json()
    except Exception as e:
        logger.warning(f"Amazon API error: {e}")
        return {"hits": 0, "jobs": []}


def _parse_location(location_data) -> str:
    """Parse Amazon's complex location object into a readable string.

    Amazon returns locations as lists of JSON strings like:
      [
        '{"normalizedLocation":"Toronto, Ontario, CAN","city":"Toronto",...}',
        ...
      ]
    """
    if isinstance(location_data, str):
        # Try to parse as JSON string
        try:
            parsed = json.loads(location_data)
            return _parse_location(parsed)
        except (json.JSONDecodeError, TypeError):
            return location_data

    if isinstance(location_data, list):
        parts = []
        for item in location_data:
            loc_str = _parse_location(item)
            if loc_str:
                parts.append(loc_str)
        return "; ".join(parts)

    if isinstance(location_data, dict):
        # Try normalizedLocation first (cleanest format)
        loc = location_data.get("normalizedLocation", "")
        if loc and isinstance(loc, str) and len(loc) > 3:
            return loc
        # Fall back to location field
        loc = location_data.get("location", "")
        if loc and isinstance(loc, str) and len(loc) > 3:
            return loc
        # Build from components
        city = location_data.get("city", "") or location_data.get("normalizedCityName", "")
        state = location_data.get("normalizedStateName", "")
        country = location_data.get("normalizedCountryName", "")
        parts = [p for p in [city, state, country] if p and len(p) > 1]
        if parts:
            return ", ".join(parts)
        return ""

    return str(location_data) if location_data else ""


def search(keywords: List[str], location: str = "", max_results: int = 10) -> List[Dict]:
    """
    Search Amazon Canada jobs.

    Fetches jobs from Amazon's JSON API, paginating to find keyword-matching
    results within the Canada filter.

    Args:
        keywords: Search terms (e.g. ["Cloud", "AI", "SDE"])
        location: Location filter (e.g. "Toronto", "Vancouver")
        max_results: Max jobs to return

    Returns:
        List of job dicts (same format as other sites)
    """
    if not keywords:
        keywords = ["Software", "Developer"]

    kw_lower = [k.lower() for k in keywords]

    all_jobs = []
    offset = 0
    page_size = min(max_results * 3, 100)
    max_pages = 5  # Cap total fetches
    hits = 0

    for page in range(max_pages):
        data = _fetch_page(offset=offset, limit=page_size, keywords=keywords,
                           location=location)
        jobs = data.get("jobs", [])
        hits = data.get("hits", 0)

        if not jobs:
            break

        for job in jobs:
            if not isinstance(job, dict):
                continue

            title = job.get("title", "") or job.get("job_title", "") or ""

            # Keyword filter
            title_lower = title.lower()
            if not any(kw in title_lower for kw in kw_lower):
                continue

            # Parse location
            raw_location = job.get("locations") or job.get("location") or ""
            loc_str = _parse_location(raw_location)

            # Check if Canadian location
            loc_lower = loc_str.lower()
            if not any(c in loc_lower for c in ["canada", "ca, ", "can", "toronto",
                                                 "vancouver", "montreal", "ottawa",
                                                 "calgary", "waterloo"]):
                if "canada" not in loc_lower:
                    continue

            # Location filter
            if location and location.lower() not in ("remote", "global"):
                loc_lower = location.lower()
                loc_ok = False
                for part in loc_lower.split(","):
                    part = part.strip()
                    if part and part in loc_str.lower():
                        loc_ok = True
                        break
                if not loc_ok:
                    user_w = {w for w in re.split(r"[\s,]+", loc_lower) if len(w) > 2}
                    txt_w = {w for w in re.split(r"[\s,\/]+", loc_str.lower()) if len(w) > 2}
                    if user_w & txt_w:
                        loc_ok = True
                if not loc_ok:
                    if "remote" not in loc_str.lower() and "virtual" not in loc_str.lower():
                        continue

            # Build job URL
            job_id = job.get("id", "") or job.get("job_id", "") or ""
            if job_id:
                job_url = f"https://www.amazon.jobs/en-gb/jobs/{job_id}"
            else:
                job_url = "https://www.amazon.jobs/en-gb"

            # Description (truncated)
            desc = job.get("description", "") or job.get("descriptionTeaser", "") or ""
            if isinstance(desc, str) and desc:
                desc_clean = re.sub(r'<[^>]+>', ' ', desc)
                desc_clean = re.sub(r'\s+', ' ', desc_clean).strip()
            else:
                desc_clean = ""

            # Job category / department
            basic_quals = job.get("basic_qualifications", "")
            pref_quals = job.get("preferred_qualifications", "")
            if basic_quals or pref_quals:
                desc_parts = []
                if basic_quals:
                    desc_parts.append(f"<h2>Basic Qualifications</h2><p>{basic_quals}</p>")
                if pref_quals:
                    desc_parts.append(f"<h2>Preferred Qualifications</h2><p>{pref_quals}</p>")
                if desc_clean:
                    desc_parts.insert(0, f"<h2>Description</h2><p>{desc_clean}</p>")
                desc_html = "\n".join(desc_parts)
            else:
                desc_html = f"<p>{desc_clean}</p>" if desc_clean else title

            # Job type
            job_type = job.get("job_type", "") or "Full-Time"
            if not job_type or job_type.lower() == "regular":
                job_type = "Full-Time"

            # Date
            date = job.get("posted_date", "") or job.get("date", "") or ""

            all_jobs.append({
                "title": title,
                "company": "Amazon",
                "location": loc_str,
                "description": desc_html,
                "url": job_url,
                "source": "Amazon",
                "date": str(date),
                "job_type": job_type,
                "remote": "Remote" if ("remote" in loc_str.lower() or
                                        "virtual" in loc_str.lower()) else "",
            })

            if len(all_jobs) >= max_results:
                break

        if len(all_jobs) >= max_results:
            break

        offset += page_size
        if offset >= hits:
            break
        time.sleep(0.3)  # Rate limiting

    return all_jobs[:max_results]


def extract(html: str, url: str) -> Dict[str, str]:
    """
    Extract job details from an Amazon job page.
    Reuses the existing amazon.py adapter for detail page extraction.
    """
    # Import the existing detail extractor
    from sites.amazon import extract as amazon_extract
    return amazon_extract(html, url)
