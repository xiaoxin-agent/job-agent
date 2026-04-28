"""
Canonical (Ubuntu) careers job search.

Canonical uses Greenhouse for recruiting. Their careers page at
https://canonical.com/careers/all embeds the full job listing JSON directly
in the HTML, so no API key or special access is needed.

The embedded JSON contains: id, title, location, departments, description,
employment type, skills, and Greenhouse apply URL.

Reference:
  https://canonical.com/careers/all
  https://canonical.com/careers/engineering
"""

from typing import List, Dict, Optional
import re
import json
import logging
from datetime import datetime

from curl_cffi import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://canonical.com"
CAREERS_URL = f"{BASE_URL}/careers/all"

# Canonical departments that align with Cloud/AI/Linux roles
_DEPT_PRIORITY = [
    "Engineering",
    "Support Engineering",
    "Product",
    "Commercial Operations",
]


def search(keywords: List[str], location: str = "", max_results: int = 10) -> List[Dict]:
    """
    Search Canonical jobs.

    Fetches all open roles from canonical.com/careers/all and filters
    by keywords and location.

    Args:
        keywords: Search terms (e.g. ["Cloud", "AI", "Linux"])
        location: Location filter (e.g. "Canada", "Americas", "EMEA")
        max_results: Max jobs to return

    Returns:
        List of job dicts
    """
    all_jobs = _fetch_all_jobs()
    if not all_jobs:
        return []

    # Filter by keywords
    if keywords:
        kw_lower = {k.strip().lower() for k in keywords if k.strip()}
        filtered = []
        for j in all_jobs:
            text = f"{j['title']} {j['departments']} {j.get('description', '')}".lower()
            if any(kw in text for kw in kw_lower):
                filtered.append(j)
        all_jobs = filtered

    # Filter by location
    if location:
        loc_lower = location.lower()
        location_filtered = []
        for j in all_jobs:
            j_loc = j.get('location', '').lower()
            # Canonical locations are like "Home based - EMEA", "Home based - Americas"
            # Match region/country in the location string
            if loc_lower in j_loc or j_loc.startswith('home based') and loc_lower in j_loc:
                location_filtered.append(j)
        if location_filtered:  # Only apply if we got results (don't empty on strict match)
            all_jobs = location_filtered

    # Sort: prioritize high-match departments, then featured jobs
    def sort_key(j):
        dept_priority = 0
        for i, d in enumerate(_DEPT_PRIORITY):
            if d in j.get('departments', []):
                dept_priority = len(_DEPT_PRIORITY) - i
                break
        featured = j.get('featured') or False
        return (dept_priority, featured, j.get('title', ''))

    all_jobs.sort(key=sort_key, reverse=True)

    return all_jobs[:max_results]


def extract(html: str, url: str) -> Dict[str, str]:
    """
    Extract job details from a Canonical job page (Greenhouse page).
    Adapter interface for registry.
    """
    result = {
        "title": "",
        "company": "Canonical",
        "location": "",
        "description": "",
        "job_type": "Full-Time",
    }

    # Greenhouse job pages embed data in JSON-LD
    jsonlds = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    for raw in jsonlds:
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                result['title'] = data.get('title', '') or result['title']
                org = data.get('hiringOrganization', {})
                if isinstance(org, dict) and org.get('name'):
                    result['company'] = org['name']
                loc = data.get('jobLocation', {})
                if isinstance(loc, dict):
                    addr = loc.get('address', {})
                    if isinstance(addr, dict):
                        parts = [p for p in [
                            addr.get('addressLocality', ''),
                            addr.get('addressRegion', ''),
                            addr.get('addressCountry', ''),
                        ] if p]
                        result['location'] = ', '.join(parts)
                    elif loc.get('name'):
                        result['location'] = loc['name']
                desc = data.get('description', '')
                if desc:
                    result['description'] = re.sub(r'<[^>]+>', ' ', desc).strip()[:3000]
                result['job_type'] = data.get('employmentType', 'FULL_TIME').replace('_', '-').title()
                break
        except (json.JSONDecodeError, AttributeError):
            continue

    # Fallback: title from <h1>
    if not result['title']:
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
        if m:
            result['title'] = re.sub(r'<[^>]+>', '', m.group(1)).strip()

    return result


def _fetch_all_jobs() -> List[Dict]:
    """
    Fetch all Canonical job listings from the careers page.

    The page embeds a JavaScript array containing all 280+ jobs as JSON.
    """
    try:
        resp = requests.get(CAREERS_URL, impersonate="chrome120", timeout=20)
        if resp.status_code != 200:
            logger.warning(f"Canonical careers page returned {resp.status_code}")
            return []
        html = resp.text
    except Exception as e:
        logger.warning(f"Failed to fetch Canonical careers: {e}")
        return []

    return _parse_jobs(html)


def _parse_jobs(html: str) -> List[Dict]:
    """Parse the embedded JSON array from the careers page."""
    # Find the jobs array in the script tag
    # Pattern: [{"date": "...", "departments": [...], "title": "...", ...}]
    # It appears in a <script> block after DOMContentLoaded listener
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)

    for script in scripts:
        if '"date"' not in script or 'departments' not in script:
            continue

        # Locate the JSON array start
        match = re.search(r'\[\s*\{\s*"date"', script)
        if not match:
            continue

        start = match.start()

        # Count brackets to find the end
        depth = 0
        end = start
        for pos in range(start, len(script)):
            ch = script[pos]
            if ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
                if depth == 0:
                    end = pos + 1
                    break

        raw = script[start:end]
        try:
            jobs_data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Canonical: failed to parse jobs JSON")
            continue

        jobs = []
        for item in jobs_data:
            if not isinstance(item, dict) or not item.get('title'):
                continue

            # Canonical individual job pages are at /careers/{job_id}
            # (slug-based URLs all 404, but ID-based URLs work)
            job_id = item.get('id', '')
            if job_id:
                job_url = f"{BASE_URL}/careers/{job_id}"
            else:
                job_url = CAREERS_URL

            # Normalize location
            location = item.get('location', '') or ''

            # Departments
            departments = item.get('departments', [])
            dept_str = ', '.join(departments) if isinstance(departments, list) else str(departments)

            # Employment type
            emp = item.get('employment', 'Full-time')
            job_type = "Full-Time"
            if emp:
                emp_lower = emp.lower()
                if 'contract' in emp_lower:
                    job_type = "Contract"
                elif 'part' in emp_lower:
                    job_type = "Part-Time"
                elif 'intern' in emp_lower:
                    job_type = "Internship"

            # Description (truncated)
            description = item.get('description', '')
            if not isinstance(description, str):
                description = str(description) if description else ''

            job = {
                "title": item['title'],
                "company": "Canonical",
                "location": location,
                "description": description[:2000],
                "url": job_url,
                "source": "Canonical",
                "date": item.get('date', ''),
                "job_type": job_type,
                "departments": departments,
                "featured": item.get('featured', False),
                "skills": item.get('skills', []),
                "management": item.get('management', False),
            }
            jobs.append(job)

        logger.debug(f"Canonical: parsed {len(jobs)} jobs")
        return jobs

    logger.warning("Canonical: no job data found in page")
    return []
