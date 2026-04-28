"""
Google job search via Google's natural search results.

Google search is the most reliable free method — it aggregates jobs from
LinkedIn, Indeed, company career sites, and other job boards without
requiring authentication or facing Cloudflare on the individual sites.

Strategy:
  1. Search Google with site-restricted queries
  2. Parse organic search results for job listings
  3. Enrich with JSON-LD job postings when available

Reference:
  https://www.google.com/search?q=Cloud+Engineer+Toronto+job
"""

from typing import List, Dict, Optional
import re
import json
import logging
from datetime import datetime
from urllib.parse import quote_plus, urljoin

from curl_cffi import requests

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

# Sites to include in Google search query
_JOB_SITES = [
    "linkedin.com/jobs",
    "indeed.com",
    "glassdoor.com",
    "ziprecruiter.com",
    "monster.com",
    "simplyhired.com",
    "careerbuilder.com",
    "dice.com",
    "craigslist.org",
]

# Company career sites
_COMPANY_SITES = [
    "google.com/about/careers",
    "amazon.jobs",
    "nvidia.com/careers",
    "microsoft.com/careers",
    "apple.com/careers/us",
    "meta.com/careers",
    "ibm.com/careers",
]


def search(keywords: List[str], location: str = "", max_results: int = 10) -> List[Dict]:
    """
    Search jobs via Google.

    Searches Google with job-related terms and parses organic results.

    Args:
        keywords: Search terms
        location: Location string
        max_results: Max jobs to return

    Returns:
        List of job dicts
    """
    jobs = _search_organic(keywords, location, max_results)
    return jobs


def _search_organic(keywords: List[str], location: str, max_results: int) -> List[Dict]:
    """Search Google organic results for jobs."""
    query = " ".join(keywords)
    if location:
        query += f" {location}"
    query += " job"

    url = f"https://www.google.com/search?q={quote_plus(query)}&hl=en"

    session = requests.Session()
    session.headers.update(_HEADERS)

    for version in ["chrome124", "chrome120", "chrome110"]:
        try:
            resp = session.get(url, impersonate=version, timeout=15)
            if resp.status_code == 200:
                html = resp.text
                # Check if we got actual search results (not a JS-required page)
                if 'div id="search"' in html or 'g-scrolling-carousel' in html or '<a href="/url?' in html:
                    logger.info(f"Google search succeeded with {version}")
                    return _parse_organic_results(html, max_results)
                # Also check for the noscript redirect (JS required page)
                if 'enablejs' in html and '/httpservice/retry/enablejs' in html:
                    logger.debug(f"Google requires JS ({version}), trying next profile")
                    continue
        except Exception as e:
            logger.debug(f"Google search with {version} failed: {e}")
            continue

    return []


def _parse_organic_results(html: str, max_results: int) -> List[Dict]:
    """Parse Google search results page for job links."""
    jobs = []
    seen_urls = set()

    # Extract search result links
    # Google uses /url?q=... redirects
    for m in re.finditer(r'href="/url\?q=([^&"\']+)', html):
        url = m.group(1)
        import urllib.parse
        url = urllib.parse.unquote(url)
        _add_job_from_url(url, html, jobs, seen_urls, max_results)

    # Also look for direct links
    for m in re.finditer(r'href="(https?://[^"\']+)"', html):
        url = m.group(1)
        _add_job_from_url(url, html, jobs, seen_urls, max_results)

    return jobs[:max_results]


def _add_job_from_url(url: str, html: str, jobs: List, seen_urls: set, max_results: int) -> None:
    """Try to extract job info from a URL found in search results."""
    if len(jobs) >= max_results:
        return

    # Dedup
    url_clean = url.rstrip('/').split('?')[0]
    if url_clean in seen_urls:
        return

    # Filter to job-related URLs only
    if not _looks_like_job_url(url):
        return

    seen_urls.add(url_clean)

    job = {
        'title': '',
        'company': '',
        'location': '',
        'description': '',
        'url': url,
        'source': 'Google',
        'date': '',
        'job_type': '',
    }

    # Try to extract a snippet/context from the search result
    # Google puts snippets near the link
    # We'll be conservative and return the URL with basic info
    # The caller can use the registry to extract full details

    if 'linkedin.com/jobs' in url:
        job['source'] = 'LinkedIn'
        job['company'] = _extract_company_from_url(url)
    elif 'indeed.com' in url:
        job['source'] = 'Indeed'
        job['company'] = _extract_company_from_url(url)
    elif 'glassdoor.com' in url:
        job['source'] = 'Glassdoor'
    elif 'amazon.jobs' in url:
        job['source'] = 'Amazon'
        job['company'] = 'Amazon'
    elif 'google.com/about/careers' in url:
        job['source'] = 'Google Careers'
        job['company'] = 'Google'

    jobs.append(job)


def _looks_like_job_url(url: str) -> bool:
    """Check if a URL looks like a job posting."""
    # Remove tracking/irrelevant URLs
    skip_patterns = [
        'google.com/search', 'google.com/shopping', 'google.com/maps',
        'youtube.com', 'facebook.com', 'twitter.com', 'instagram.com',
        'googleadservices.com', 'accounts.google.com',
        'policies.google.com', 'support.google.com',
        '/search?', 'webcache.googleusercontent.com',
    ]
    for p in skip_patterns:
        if p in url:
            return False

    # Must contain job-related keywords
    job_keywords = [
        '/jobs/', '/careers/', '/career/', '/opportunity',
        '-job-', '-career-', 'job=', 'career=',
        '/position/', '/opening/', '/apply/',
        'job/view/', 'job-posting',
    ]
    url_lower = url.lower()
    for kw in job_keywords:
        if kw in url_lower:
            return True

    # Check known job domains
    for site in _JOB_SITES + _COMPANY_SITES:
        if site in url_lower:
            return True

    return False


def _extract_company_from_url(url: str) -> str:
    """Try to infer company name from URL."""
    m = re.search(r'linkedin\.com/jobs/view/[^/]+-at-([^/?&]+)', url)
    if m:
        return m.group(1).replace('-', ' ').title()
    m = re.search(r'indeed\.com/.*?q=([^&]+)', url)
    if m:
        return m.group(1).replace('+', ' ').title()
    return ''
