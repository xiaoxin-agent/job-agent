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


def _fetch_detail(job_id: int) -> Dict[str, str]:
    """Fetch job details from BambooHR /careers/{id}/detail API."""
    result = {
        "description": "",
        "location": "",
        "job_type": "Full-Time",
        "title": "",
    }
    try:
        resp = requests.get(
            f"https://solace.bamboohr.com/careers/{job_id}/detail",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json",
                     "Referer": f"https://solace.bamboohr.com/careers/{job_id}"},
            timeout=15,
        )
        if resp.status_code != 200:
            return result
        data = resp.json()
        job = data.get("result", {}).get("jobOpening", {}) or {}
        result["title"] = job.get("jobOpeningName", "")
        desc = job.get("description", "") or ""
        if desc:
            result["description"] = desc
        loc = job.get("location", {}) or {}
        parts = [p for p in [loc.get("city", ""), loc.get("state", ""), loc.get("addressCountry", "")] if p]
        result["location"] = ", ".join(parts)
        result["job_type"] = job.get("employmentStatusLabel", "Full-Time")
    except Exception:
        pass
    return result


def _extract_job_id(url: str) -> int:
    """Extract job ID from BambooHR URL."""
    m = re.search(r'/careers/(\d+)', url)
    return int(m.group(1)) if m else 0


def extract(html: str, url: str = "") -> Dict[str, str]:
    """Extract job details using BambooHR /careers/{id}/detail API."""
    result = {
        "title": "",
        "company": "Solace",
        "location": "",
        "description": "",
        "job_type": "Full-Time",
    }

    job_id = _extract_job_id(url)
    if not job_id:
        return result

    detail = _fetch_detail(job_id)
    result.update({k: v for k, v in detail.items() if v})
    return result
