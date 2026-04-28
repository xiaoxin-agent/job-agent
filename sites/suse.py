"""
SUSE Careers — Workday-based search module.

Uses SUSE's Workday API (suse.wd3.myworkdayjobs.com) to search jobs.
Search results have basic info; details are scraped from individual job pages.
"""

from typing import Dict, List, Optional
import re
import json
import time

from curl_cffi import requests

SITE = "SUSE"
WORKDAY_API = "https://suse.wd3.myworkdayjobs.com/wday/cxs/suse/Jobsatsuse/jobs"
JOB_PAGE = "https://suse.wd3.myworkdayjobs.com/en-US/Jobsatsuse"
JOB_DOMAIN = "suse.wd3.myworkdayjobs.com"

SECTIONS = [
    "About Us",
    "About the Role",
    "The Role",
    "Responsibilities",
    "What You Will Do",
    "What You Will Bring",
    "Qualifications",
    "Requirements",
    "Required Skills and Experience",
    "Preferred Skills",
    "Nice to Have",
    "Skills",
    "About SUSE",
    "What SUSE Offers",
    "Benefits",
    "Inclusion at SUSE",
    "Equal Opportunity",
    "Diversity and Inclusion",
]


def _format_suse_description(text: str) -> str:
    """Convert SUSE plain-text Workday description to structured HTML."""
    if not text:
        return ""

    # Build regex that matches any section header (case-insensitive)
    header_pattern = "(" + "|".join(
        rf"\b{re.escape(h)}(?:\s*[:?])?" for h in SECTIONS
    ) + ")"
    parts = re.split(header_pattern, text, flags=re.IGNORECASE)

    if len(parts) < 2:
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f"<p>{escaped}</p>"

    html_parts = []
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if not part:
            i += 1
            continue

        # Detect if this part is a known section header
        clean = part.rstrip(":? ").strip()
        is_header = any(clean.lower() == h.lower() for h in SECTIONS)

        if is_header:
            if i + 1 < len(parts):
                body = parts[i + 1].strip()
                body = re.sub(r'^[:?]\s*', '', body)
                html_parts.append(f"<p><strong>{clean}</strong></p>")
                html_parts.append(f"<p>{body}</p>")
                i += 2
            else:
                html_parts.append(f"<p><strong>{clean}</strong></p>")
                i += 1
        else:
            html_parts.append(f"<p>{part}</p>")
            i += 1

    return "\n".join(html_parts)


def extract(html: str, url: str = "") -> Dict[str, str]:
    """Extract job details from a SUSE Workday job page JSON-LD."""
    result = {
        "title": "",
        "company": "SUSE",
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
                desc = data.get("description") or ""
                if desc:
                    result["description"] = _format_suse_description(desc.strip())
                loc = data.get("jobLocation", {})
                if isinstance(loc, dict):
                    addr = loc.get("address", {})
                    locality = addr.get("addressLocality", "")
                    region = addr.get("addressRegion", "")
                    country = addr.get("addressCountry", "")
                    parts = [p for p in [locality, region, country] if p]
                    result["location"] = ", ".join(parts)
                employment = data.get("employmentType", "")
                if employment:
                    result["job_type"] = employment
                break
    except Exception:
        pass
    return result


def search(keywords: List[str] = None,
           location: str = "",
           max_results: int = 10) -> List[Dict]:
    """Search SUSE jobs via Workday API."""
    return _search_api(keywords, "en-US", max_results, location)


def _extract_job_id(external_path: str) -> str:
    """Extract numeric job ID from external path."""
    m = re.search(r'_(\d+)$', external_path)
    return m.group(1) if m else ""


def _search_api(keywords: List[str], locale: str = "en-US",
                limit: int = 20, location: str = "") -> List[Dict]:
    """Query Workday search API and filter results."""
    def _do_request():
        try:
            resp = requests.post(
                WORKDAY_API,
                json={"limit": min(limit * 3, 20), "offset": 0},
                impersonate="chrome120",
                headers={"Content-Type": "application/json",
                         "Accept": "application/json"},
                timeout=20,
            )
            if resp.status_code != 200:
                return None
            return resp.json()
        except Exception:
            return None

    for attempt in range(3):
        data = _do_request()
        if data is not None and data.get("jobPostings"):
            break
        time.sleep(2 * (attempt + 1))

    if data is None:
        return []
    job_postings = data.get("jobPostings", [])
    if not job_postings:
        return []

    results = []
    for job in job_postings:
        title = job.get("title", "")
        locations_text = job.get("locationsText", "")
        external_path = job.get("externalPath", "")
        detail_url = f"{JOB_PAGE}{external_path}" if external_path else ""

        # Keyword filter
        if keywords:
            title_lower = title.lower()
            if not any(kw.lower() in title_lower for kw in keywords):
                continue

        posted_on = job.get("postedOn", "")

        results.append({
            "title": title,
            "company": "SUSE",
            "location": locations_text or "Global / Remote",
            "description": title,
            "url": detail_url,
            "source": SITE,
            "date": posted_on,
            "job_type": "Full-Time",
            "remote": "Remote",
            "departments": [],
            "salary_min": 0,
            "salary_max": 0,
            "currency": "USD",
        })

    return results[:limit]
