"""
Red Hat Careers — Workday-based search module.

Uses Red Hat's Workday API (wd5.myworkdayjobs.com) to search jobs.
Search results have basic info; details are scraped from individual job pages.
"""

import re
import json
from typing import Dict, List, Optional

from curl_cffi import requests

SITE = "RedHat"

BASE_URL = "https://www.redhat.com"
WORKDAY_API = "https://redhat.wd5.myworkdayjobs.com/wday/cxs/redhat/jobs/jobs"
JOB_PAGE = "https://redhat.wd5.myworkdayjobs.com/jobs"
CAREERS_URL = f"{BASE_URL}/en/jobs"

# Departments/categories we care about (matched against job titles and descriptions)
RELEVANT_KEYWORDS = [
    "engineer", "developer", "sre", "devops", "cloud", "linux",
    "kubernetes", "openshift", "python", "ansible", "automation",
    "infrastructure", "platform", "ai", "ml", "machine learning",
    "data", "security", "architect", "kernel", "storage", "networking",
    "open source", "software", "backend", "full stack", "frontend",
]

LANGUAGES = {
    "en": "en-US",
    "zh": "zh-CN",
    "fr": "fr-FR",
    "de": "de-DE",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "pt": "pt-BR",
    "es": "es-ES",
    "it": "it-IT",
}


# ---------------------------------------------------------------------------
# Registry interface
# ---------------------------------------------------------------------------

def search(keywords: List[str], location: str = "",
           max_results: int = 10, lang: str = "en") -> List[Dict]:
    """Search Red Hat jobs matching *any* keyword (OR logic)."""
    locale = LANGUAGES.get(lang, "en-US")
    results = _search_api(keywords, locale, limit=max_results, location=location)
    return results[:max_results]


def _format_redhat_description(text: str) -> str:
    """Convert Red Hat's plain-text JSON-LD description to simple HTML.

    Red Hat's JSON-LD is just continuous text with section headers like:
      About the Job : ...  What You Will Do? ...  What You Will Bring ? ...
      The following are considered as a plus: ...  About Red Hat ...

    We split on known header markers, wrap each section in <p>, and
    give headers <strong> treatment.
    """
    section_headers = [
        "About the Job",
        "What You Will Do",
        "What You Will Bring",
        "The following are considered as a plus",
        "About Red Hat",
        "Inclusion at Red Hat",
        "Equal Opportunity Policy",
    ]
    # Build a regex that splits on any section header (case-insensitive, word-boundary)
    # Eats trailing punctuation (:, ?, etc) into the header capture so it doesn't
    # show up as orphaned text in the next part.
    def _header_re(h: str) -> str:
        # Match the header followed by optional :, ?, or :space, then trim from the result
        return rf"\b{re.escape(h)}(?:\s*[:?])?"
    header_pattern = "(" + "|".join(_header_re(h) for h in section_headers) + ")"
    parts = re.split(header_pattern, text, flags=re.IGNORECASE)

    if len(parts) < 2:
        # No recognizable sections -> wrap whole thing in <p>
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f"<p>{escaped}</p>"

    html_parts = []
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if not part:
            i += 1
            continue
        # Check if this part IS a recognized section header
        is_header = False
        for h in section_headers:
            # Strip trailing punctuation for comparison
            clean = part.rstrip(":? ").strip()
            if clean.lower() == h.lower():
                is_header = True
                part = clean  # Use clean version for display
                break
        if is_header:
            if i + 1 < len(parts):
                body = parts[i + 1].strip()
                # body sometimes starts with ': ' or '? ' — strip it
                body = re.sub(r'^[:?]\s*', '', body)
                html_parts.append(f"<p><strong>{part}</strong></p>")
                html_parts.append(f"<p>{body}</p>")
                i += 2
            else:
                html_parts.append(f"<p><strong>{part}</strong></p>")
                i += 1
        else:
            html_parts.append(f"<p>{part}</p>")
            i += 1

    return "\n".join(html_parts)


def extract(html: str, url: str = "") -> Dict:
    """Extract job details from a Red Hat job page JSON-LD."""
    result = {"title": "", "company": "Red Hat", "location": "",
              "description": "", "job_type": ""}
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
                # Keep HTML for rich display (clean_html is done at fetch_job_from_url level)
                result["description"] = _format_redhat_description(desc.strip())
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
    if not result["description"]:
        # Fallback: try to find description in meta tags
        desc_m = re.search(
            r'<meta[^>]+name=[\"\']description[\"\'][^>]+content=[\"\']'
            r'([^\"]+)[\"\']', html, re.IGNORECASE
        )
        if desc_m:
            result["description"] = desc_m.group(1)
    return result


# ---------------------------------------------------------------------------
# Internal API
# ---------------------------------------------------------------------------

def _search_api(keywords: List[str], locale: str = "en-US",
                limit: int = 20, location: str = "") -> List[Dict]:
    """Query Workday search API and filter results."""
    def _do_request():
        try:
            resp = requests.post(
                WORKDAY_API,
                json={"limit": min(limit * 3, 20), "offset": 0},  # Workday API max is 20
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

    # Retry up to 3 times if empty response (Workday API rate-limits)
    import time
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

        # Create URL to job detail page
        detail_url = f"{JOB_PAGE}{external_path}" if external_path else ""

        # Match against keywords (OR logic)
        if keywords:
            title_lower = title.lower()
            if not any(kw.lower() in title_lower for kw in keywords):
                continue

        # Location search disabled for Red Hat - jobs are global/remote across many cities.
        # Most Red Hat positions won't match specific city names like Toronto.
        pass

        posted_on = job.get("postedOn", "")
        remote_type = job.get("remoteType", "On-site")

        # Map remote type to a standard format
        if remote_type == "Remote":
            remote_str = "Remote"
        elif remote_type == "Hybrid":
            remote_str = "Hybrid"
        else:
            remote_str = "On-site"

        # Get short description from bulletFields (usually contains req ID)
        short_desc = title  # fallback

        results.append({
            "title": title,
            "company": "Red Hat",
            "location": locations_text or "United States",
            "description": short_desc,
            "url": detail_url,
            "source": SITE,
            "date": posted_on,
            "job_type": "Full-Time",
            "remote": remote_str,
            "departments": [],
            "featured": False,
        })

    return results


def _fetch_details(url: str) -> Optional[Dict]:
    """Fetch job details from a Red Hat job page and return extracted info."""
    try:
        resp = requests.get(url, impersonate="chrome120", timeout=20)
        if resp.status_code != 200:
            return None
        return extract(resp.text, url)
    except Exception:
        return None
