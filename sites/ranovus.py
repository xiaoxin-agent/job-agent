"""
Ranovus — BambooHR-powered job board.

Searches the BambooHR /careers/list API (same pattern as Solace).
"""

from typing import Dict, List, Optional
import json
import re
import requests

SITE = "Ranovus"

# BambooHR locationType: 1=Remote, 2=Onsite, 3=Hybrid
LOCATION_TYPE_MAP = {"1": "Remote", "2": "On-site", "3": "Hybrid"}


def search(keywords: List[str] = None, location: str = "",
           max_results: int = 10, **kwargs) -> List[Dict]:
    """Search Ranovus jobs via BambooHR list API."""
    if not keywords:
        keywords = ["Software", "Engineer"]
    kw_lower = [k.lower() for k in keywords]

    try:
        resp = requests.get(
            "https://ranovus.bamboohr.com/careers/list",
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

        if not any(kw in title_lower for kw in kw_lower):
            continue

        loc = job.get("location", {})
        city = (loc.get("city") or "").strip()
        state = (loc.get("state") or "").strip()
        location_str = ", ".join(p for p in [city, state] if p)

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

        detail_url = f"https://ranovus.bamboohr.com/careers/{job['id']}"
        job_type = LOCATION_TYPE_MAP.get(loc_type, "Full-Time")
        if is_remote:
            job_type = "Remote"

        jobs.append({
            "title": title,
            "company": "Ranovus",
            "location": location_str,
            "description": title,
            "url": detail_url,
            "source": "Ranovus",
            "date": "",
            "job_type": job_type,
            "remote": "Remote" if is_remote else "",
        })

    return jobs[:max_results]
