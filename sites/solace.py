"""
Solace Careers — BambooHR-powered.

Search: BambooHR /careers/list API (solace.bamboohr.com)
Details: BambooHR job pages are JS-rendered, basic extract from HTML.
"""

from typing import Dict, List, Optional
import json
import re
import requests

SITE = "Solace"

# BambooHR locationType: 1=Remote, 2=Onsite, 3=Hybrid
LOCATION_TYPE_MAP = {"1": "Remote", "2": "On-site", "3": "Hybrid"}


def search(keywords: List[str] = None, location: str = "",
           max_results: int = 10, **kwargs) -> List[Dict]:
    """Search Solace jobs via BambooHR list API."""
    if not keywords:
        keywords = ["Software", "Developer"]
    kw_lower = [k.lower() for k in keywords]

    try:
        resp = requests.get(
            "https://solace.bamboohr.com/careers/list",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception:
        return []

    jobs = []
    for job in data.get("result", []):
        title = job.get("jobOpeningName", "")
        title_lower = title.lower()

        # Keyword filter
        if not any(kw in title_lower for kw in kw_lower):
            continue

        loc = job.get("location", {})
        city = (loc.get("city") or "").strip()
        state = (loc.get("state") or "").strip()
        location_str = ", ".join(p for p in [city, state] if p)

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

        is_remote = job.get("isRemote")
        loc_type = str(job.get("locationType", ""))

        detail_url = f"https://solace.bamboohr.com/careers/{job['id']}"
        job_type = LOCATION_TYPE_MAP.get(loc_type, "Full-Time")
        if is_remote:
            job_type = "Remote"

        jobs.append({
            "title": title,
            "company": "Solace",
            "location": location_str,
            "description": title,
            "url": detail_url,
            "source": "Solace",
            "date": "",
            "job_type": job_type,
            "remote": "Remote" if is_remote else "",
            "departments": [job.get("departmentLabel", "")],
            "salary_min": 0,
            "salary_max": 0,
            "currency": "CAD",
        })

    return jobs[:max_results]


def extract(html: str, url: str = "") -> Dict[str, str]:
    """Extract job details from a Solace BambooHR job page."""
    result = {
        "title": "",
        "company": "Solace",
        "location": "",
        "description": "",
        "job_type": "Full-Time",
    }

    # Try to extract from JSON-LD
    try:
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
