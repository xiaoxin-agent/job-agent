"""
LinkedIn job search via LinkedIn's public job search page.

Uses curl_cffi with impersonation. LinkedIn uses Cloudflare, so success
depends on the impersonation profile working. Falls back gracefully.

Strategy:
  1. Try direct LinkedIn job search page with curl_cffi
  2. Extract embedded job data from the page HTML

Reference search URL:
  https://www.linkedin.com/jobs/search/?keywords=Cloud+Engineer&location=Toronto
"""

from typing import List, Dict, Optional
import re
import json
import logging
from datetime import datetime

from curl_cffi import requests

logger = logging.getLogger(__name__)

# Headers mimicking a normal browser
_BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
    "Connection": "keep-alive",
}

# Try multiple impersonate versions in order
_IMPERSONATE_VERSIONS = ["chrome124", "chrome123", "chrome120", "chrome110", "safari17_0"]


def search(keywords: List[str], location: str = "", max_results: int = 10) -> List[Dict]:
    """
    Search LinkedIn jobs.

    Args:
        keywords: List of search keywords
        location: Job location string (e.g. "Toronto", "Remote")
        max_results: Maximum number of results to return

    Returns:
        List of job dicts with keys: title, company, location, description, url, source, date
    """
    query = "+".join(keywords) if keywords else "software"
    url = _build_search_url(query, location)

    html = _fetch(url)
    if not html:
        return []

    jobs = _parse_jobs(html, query, location)
    return jobs[:max_results]


def extract(html: str, url: str) -> Dict[str, str]:
    """
    Extract job details from a LinkedIn job page HTML.
    Adapter interface for registry.
    """
    import sites.linkedin as linkedin_extract
    return linkedin_extract.extract(html, url)


def _build_search_url(query: str, location: str) -> str:
    """Build LinkedIn job search URL."""
    url = "https://www.linkedin.com/jobs/search/"
    params = {"keywords": query}
    if location:
        params["location"] = location
    params["trk"] = "public_jobs_jobs-search-bar_search-submit"
    # We'll send it as a regular URL with query params
    qs = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    return f"{url}?{qs}"


def _fetch(url: str) -> Optional[str]:
    """
    Fetch LinkedIn jobs page. Tries multiple impersonation profiles.

    Returns:
        HTML text on success, None on failure.
    """
    session = requests.Session()
    session.headers.update(_BASE_HEADERS)

    # First hit homepage to establish cookies
    try:
        resp = session.get("https://www.linkedin.com/", impersonate="chrome124", timeout=15)
        logger.debug(f"LinkedIn home: status={resp.status_code}, cookies={len(session.cookies)}")
    except Exception as e:
        logger.warning(f"LinkedIn home failed: {e}")

    # Now try the jobs search page with different impersonation profiles
    for version in _IMPERSONATE_VERSIONS:
        try:
            resp = session.get(url, impersonate=version, timeout=20)
            if resp.status_code == 200:
                text = resp.text

                # Check for Cloudflare / challenge
                txt_lower = text.lower()
                if "challenge" in txt_lower[:3000] or "captcha" in txt_lower[:3000]:
                    logger.debug(f"LinkedIn blocked with {version} (challenge)")
                    continue

                # Check if we got actual content (not just login page)
                # LinkedIn without auth still serves job listings on the search page
                if len(text) > 50000 and _has_job_data(text):
                    logger.info(f"LinkedIn search succeeded with {version}")
                    return text

                logger.debug(f"LinkedIn search with {version}: no job data in response")
        except Exception as e:
            logger.debug(f"LinkedIn search with {version} failed: {e}")
            continue

    return None


def _has_job_data(html: str) -> bool:
    """Check if the HTML contains job listing data."""
    # Look for LinkedIn's job card structure or JSON data
    if 'data-tracking-control-name="public_jobs_job-result-card"' in html:
        return True
    if '"baseSearchUrl"' in html:
        return True
    if 'jobCardViewModel' in html or 'job-search-result-card' in html:
        return True
    # Fallback: check for title/company patterns
    return bool(re.search(r'class="[^"]*job-card[^"]*"', html))


def _parse_jobs(html: str, query: str, location: str) -> List[Dict]:
    """
    Parse LinkedIn job listing HTML.

    LinkedIn embeds job data in several ways:
    1. window.__INITIAL_STATE__ JSON (sometimes present)
    2. JSON-LD script tags
    3. Job card HTML elements
    """
    jobs = []

    # Strategy 1: Try __INITIAL_STATE__ if present
    jobs = _parse_from_initial_state(html)
    if jobs:
        return jobs

    # Strategy 2: Try JSON-LD (sometimes on search pages)
    jobs = _parse_from_jsonld(html)
    if jobs:
        return jobs

    # Strategy 3: Parse from inline script data
    jobs = _parse_from_inline_data(html)
    if jobs:
        return jobs

    # Strategy 4: Parse from HTML job cards (fallback)
    jobs = _parse_from_html(html)
    return jobs


def _parse_from_initial_state(html: str) -> List[Dict]:
    """Extract jobs from window.__INITIAL_STATE__ JSON blob."""
    jobs = []
    m = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\});', html, re.DOTALL)
    if not m:
        return jobs

    try:
        data = json.loads(m.group(1))
        # Navigate to job search results
        # Structure varies; look for common paths
        for key in ('jobSearch', 'jobs', 'searchResults', 'results'):
            section = data.get(key, {})
            if isinstance(section, dict):
                elements = section.get('elements', section.get('items', section.get('results', [])))
                if isinstance(elements, list):
                    for item in elements:
                        if isinstance(item, dict):
                            job = _extract_job_from_item(item)
                            if job:
                                job['source'] = 'LinkedIn'
                                jobs.append(job)
    except (json.JSONDecodeError, AttributeError):
        pass
    return jobs


def _parse_from_jsonld(html: str) -> List[Dict]:
    """Extract jobs from JSON-LD script tags."""
    jobs = []
    jsonlds = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    for raw in jsonlds:
        try:
            data = json.loads(raw)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                    job = {
                        'title': item.get('title', ''),
                        'company': '',
                        'location': '',
                        'description': item.get('description', ''),
                        'url': item.get('url', ''),
                        'source': 'LinkedIn',
                        'date': item.get('datePosted', ''),
                    }
                    org = item.get('hiringOrganization', {})
                    if isinstance(org, dict):
                        job['company'] = org.get('name', '')
                    loc = item.get('jobLocation', {})
                    if isinstance(loc, dict):
                        addr = loc.get('address', {})
                        if isinstance(addr, dict):
                            parts = [p for p in [addr.get('addressLocality', ''),
                                                  addr.get('addressRegion', ''),
                                                  addr.get('addressCountry', '')] if p]
                            job['location'] = ', '.join(parts)
                    if job['title'] or job['company']:
                        job['description'] = re.sub(r'<[^>]+>', ' ', job['description']).strip()[:2000]
                        jobs.append(job)
        except (json.JSONDecodeError, AttributeError):
            continue
    return jobs


def _parse_from_inline_data(html: str) -> List[Dict]:
    """Extract jobs from inline script data attributes."""
    jobs = []

    # Look for data-delayed-job-cards or similar data attributes
    cards = re.findall(
        r'<li[^>]*class=["\'][^"\']*job-result-card[^"\']*["\'][^>]*>(.*?)</li>',
        html, re.DOTALL
    )
    if not cards:
        cards = re.findall(
            r'<div[^>]*data-job-id[=][\"\']([^\"\']+)[\"\']',
            html
        )
        if cards:
            # We have job IDs but not the full data
            logger.debug(f"Found {len(cards)} job IDs (need full page render)")
            return jobs

    for card_html in cards[:20]:
        title = _extract_attr(card_html, 'data-job-title')
        if not title:
            title = _extract_text(card_html, 'h3') or _extract_text(card_html, 'a[class*=title]')
        company = _extract_attr(card_html, 'data-company-name')
        if not company:
            company = _extract_text(card_html, 'h4') or _extract_text(card_html, '[class*=company]')
        location = _extract_text(card_html, '[class*=location]')
        url_m = re.search(r'href=["\']([^"\']+/jobs/view/\d+[^"\']*)', card_html)
        url = url_m.group(1) if url_m else ''
        if url and not url.startswith('http'):
            url = 'https://www.linkedin.com' + url

        if title:
            jobs.append({
                'title': title.strip(),
                'company': company.strip() if company else '',
                'location': location.strip() if location else '',
                'description': '',
                'url': url,
                'source': 'LinkedIn',
                'date': '',
            })

    return jobs


def _parse_from_html(html: str) -> List[Dict]:
    """Fallback: parse job info from HTML text patterns."""
    jobs = []

    # Try to find job data in script tags with JSON content
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    for script in scripts:
        if len(script) < 100:
            continue
        # Look for JSON with job-related keys
        for key in ('title', 'company', 'jobTitle'):
            if key in script[:500]:
                try:
                    # Try to extract JSON objects
                    objs = re.findall(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', script)
                    for obj_str in objs:
                        if 'title' in obj_str and 'company' in obj_str:
                            data = json.loads(obj_str)
                            if isinstance(data, dict) and 'title' in data and 'company' in data:
                                job = {
                                    'title': data.get('title', ''),
                                    'company': data.get('company', '') or '',
                                    'location': data.get('location', '') or '',
                                    'description': data.get('description', '') or '',
                                    'url': data.get('url', '') or '',
                                    'source': 'LinkedIn',
                                    'date': data.get('datePosted', '') or '',
                                }
                                if job['title'] and job['company']:
                                    jobs.append(job)
                except (json.JSONDecodeError, AttributeError):
                    continue
            break

    return jobs


def _extract_attr(html: str, attr: str) -> Optional[str]:
    """Extract a data-* attribute value from HTML snippet."""
    m = re.search(rf'{re.escape(attr)}=["\']([^"\']+)["\']', html)
    return m.group(1) if m else None


def _extract_text(html: str, selector: str) -> Optional[str]:
    """Simple text extraction from HTML using tag/class patterns."""
    # Handle common patterns: <tag>text</tag>, <tag class="...">text</tag>
    # selector can be: 'h3', 'h4', '[class*=company]', 'a[class*=title]'
    tag_match = re.match(r'(\w+)', selector)
    tag = tag_match.group(1) if tag_match else 'div'
    class_pattern = ''
    cls_m = re.search(r'class\*=\s*["\']([^"\']+)["\']', selector)
    if cls_m:
        class_pattern = rf'[^>]*class=["\'][^"\']*{re.escape(cls_m.group(1))}[^"\']*["\']'

    pattern = rf'<{tag}{class_pattern}[^>]*>([^<]+)</{tag}>'
    m = re.search(pattern, html)
    return m.group(1).strip() if m else None


def _extract_job_from_item(item: Dict) -> Optional[Dict]:
    """Extract job info from a parsed JSON item."""
    if 'title' not in item and 'jobTitle' not in item:
        return None

    title = item.get('title', item.get('jobTitle', ''))
    # Usually these items have nested company info
    company_data = item.get('company', item.get('hiringOrganization', {}))
    if isinstance(company_data, dict):
        company = company_data.get('name', '')
    elif isinstance(company_data, str):
        company = company_data
    else:
        company = ''

    location_data = item.get('location', item.get('formattedLocation', ''))
    if isinstance(location_data, dict):
        location = location_data.get('name', location_data.get('text', ''))
    else:
        location = str(location_data)

    url = item.get('url', item.get('jobUrl', item.get('applyUrl', item.get('externalUrl', ''))))
    if url and not url.startswith('http'):
        url = 'https://www.linkedin.com' + url

    return {
        'title': title,
        'company': company,
        'location': location,
        'description': item.get('description', item.get('snippet', '')),
        'url': url,
        'source': 'LinkedIn',
        'date': item.get('datePosted', item.get('postDate', '')),
    }
