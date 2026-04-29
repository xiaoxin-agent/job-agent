"""
Google Careers job search.

Google uses a SPA-style career page that embeds job data in
AF_initDataCallback(…) script tags. We scrape the search results page
and extract the structured job listings from these embedded JSON blobs.

Search URL:
  https://www.google.com/about/careers/search?q=software+engineer&location=Canada
"""

from typing import List, Dict, Optional
import re
import json
import logging
import datetime

import requests

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.google.com/about/careers/search"


def _fetch_search_page(keywords: List[str], location: str) -> str:
    """Fetch the Google Careers search results page."""
    params = {"q": " ".join(keywords) if keywords else "software engineer"}
    if location:
        params["location"] = location

    try:
        resp = requests.get(
            SEARCH_URL,
            params=params,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=25,
        )
        if resp.status_code != 200:
            logger.warning(f"Google Careers returned {resp.status_code}")
            return ""
        return resp.text
    except Exception as e:
        logger.warning(f"Google Careers fetch error: {e}")
        return ""


def _parse_jobs_from_page(html: str) -> List[Dict]:
    """
    Parse Google Careers job listings from AF_initDataCallback script.
    Extracts the array nested under data: [...] from the ds:1 blob
    by bracket-counting (since the JS syntax is not valid JSON).

    Each job entry has ~21 fields:
      [0]:  job_id (string)
      [1]:  title (string)
      [2]:  signin_url (string)
      [3]:  [null, responsibilities_html]
      [4]:  [null, qualifications_html]
      [5]:  company_tenant_id (string)
      [6]:  None
      [7]:  company_name (string, e.g. "Google")
      [8]:  locale (string, e.g. "en-US")
      [9]:  [[location_name, [address], city, zip, state, country], ...]
      [10]: [null, description_preview_html]
      [11]: [category_id]
      [12]: [timestamp_ms, ?]
    """
    # Find the <script> tag containing AF_initDataCallback with ds:1
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)

    for script in scripts:
        if 'AF_initDataCallback' not in script or "'ds:1'" not in script:
            continue
        if 'data:[' not in script:
            continue

        # Extract the data: [...] array by bracket counting
        data_match = re.search(r'data:\s*(\[)', script)
        if not data_match:
            continue

        start = data_match.start(1)
        depth = 0
        end = start
        for i in range(start, len(script)):
            ch = script[i]
            if ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        data_str = script[start:end]
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            continue

        if not isinstance(data, list) or len(data) == 0:
            continue

        # data[0] is the job array: [job1, job2, ...]
        job_array = data[0]
        if not isinstance(job_array, list):
            continue

        jobs = []
        for entry in job_array:
            if not isinstance(entry, list) or len(entry) < 10:
                continue

            job_id = str(entry[0]) if entry[0] else ""
            title = str(entry[1]) if entry[1] else ""

            if not title or not job_id:
                continue

            # Build description from responsibilities (entry[3]) and qualifications (entry[4])
            desc_parts = []

            if len(entry) > 3 and isinstance(entry[3], list) and len(entry[3]) > 1:
                resp_html = entry[3][1]
                if resp_html and isinstance(resp_html, str) and len(resp_html) > 20:
                    desc_parts.append(f"<h2>Responsibilities</h2>{resp_html}")

            if len(entry) > 4 and isinstance(entry[4], list) and len(entry[4]) > 1:
                quals_html = entry[4][1]
                if quals_html and isinstance(quals_html, str) and len(quals_html) > 20:
                    desc_parts.append(f"<h2>Minimum qualifications</h2>{quals_html}")

            # Location from entry[9]
            loc_str = ""
            if len(entry) > 9 and isinstance(entry[9], list):
                loc_parts = []
                for loc_entry in entry[9]:
                    if isinstance(loc_entry, list) and len(loc_entry) >= 1:
                        loc_name = loc_entry[0]
                        if loc_name and isinstance(loc_name, str):
                            loc_parts.append(loc_name)
                loc_str = "; ".join(loc_parts)

            # Date from entry[12]
            date_str = ""
            if len(entry) > 12 and isinstance(entry[12], list) and len(entry[12]) > 0:
                ts = entry[12][0]
                if ts and isinstance(ts, (int, float)):
                    try:
                        # Check if this is ms or s timestamp
                        if ts > 100000000000:  # ms
                            dt = datetime.datetime.fromtimestamp(ts / 1000)
                        else:
                            dt = datetime.datetime.fromtimestamp(ts)
                        date_str = dt.strftime("%Y-%m-%d")
                    except Exception:
                        date_str = str(ts)

            desc_html = "\n".join(desc_parts) if desc_parts else title

            jobs.append({
                "title": title,
                "company": "Google",
                "location": loc_str,
                "description": desc_html,
                "url": f"https://www.google.com/about/careers/applications/jobs/results/{job_id}",
                "source": "Google",
                "date": str(date_str),
                "job_type": "Full-Time",
                "remote": "Remote" if "remote" in loc_str.lower() else "",
            })

        if jobs:
            return jobs

    logger.info("Google Careers: no job data found in page")
    return []


def search(keywords: List[str], location: str = "", max_results: int = 10) -> List[Dict]:
    """
    Search Google Careers jobs.

    Scrapes the Google Careers search page for embedded job data.

    Args:
        keywords: Search terms
        location: Location filter (e.g. "Toronto", "Canada")
        max_results: Max jobs to return

    Returns:
        List of job dicts
    """
    html = _fetch_search_page(keywords, location)
    if not html:
        return []

    all_jobs = _parse_jobs_from_page(html)

    if not all_jobs:
        logger.info("Google Careers: no jobs found via embedded data")
        return []

    # Location filter
    # Note: Google already filters by keywords server-side via the ?q= URL param.
    # We do NOT re-filter by keyword here — it would drop Canada-located jobs
    # that match the user's intent but don't have the keyword in descriptions.
    if location and location.lower() not in ("remote", "global"):
        loc_lower = location.lower()
        loc_tokens = {w for w in re.split(r"[\s,\/]+", loc_lower) if len(w) > 2}

        filtered = []
        for j in all_jobs:
            j_loc = j.get("location", "").lower()
            if any(token in j_loc for token in loc_tokens):
                filtered.append(j)
            elif "remote" in j_loc or "global" in j_loc:
                filtered.append(j)
            else:
                j_words = {w for w in re.split(r"[\s,\/]+", j_loc) if len(w) > 2}
                if loc_tokens & j_words:
                    filtered.append(j)

        if filtered:
            all_jobs = filtered
        else:
            # No jobs matched location — return nothing rather than all jobs
            all_jobs = []

    return all_jobs[:max_results]


def extract(html: str, url: str) -> Dict[str, str]:
    """
    Extract job details from a Google Careers job page.
    Reuses the existing google_careers.py adapter for detail page extraction.
    """
    from sites.google_careers import extract as google_extract
    return google_extract(html, url)
