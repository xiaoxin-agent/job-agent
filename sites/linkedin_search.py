"""
LinkedIn job search via DuckDuckGo (site:linkedin.com/jobs).

LinkedIn blocks non-browser traffic directly, but DuckDuckGo indexes
LinkedIn job listings and can crawl them freely. This is the most
reliable free method to find LinkedIn jobs without authentication.

Strategy:
  1. Search DuckDuckGo with "site:linkedin.com/jobs" + keywords + location
  2. Parse organic results (title, URL, snippet with company/location)
  3. Optionally enrich via linkedin.py extract() when job detail page is visited

Reference:
  https://html.duckduckgo.com/html/?q=site:linkedin.com/jobs+Software+Engineer+Toronto
"""

from typing import List, Dict, Optional
import re
import logging
from datetime import datetime
from urllib.parse import quote_plus, unquote

logger = logging.getLogger(__name__)

# Headers mimicking a normal browser
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# DuckDuckGo HTML endpoint
_DDG_URL = "https://html.duckduckgo.com/html/"


def search(keywords: List[str], location: str = "", max_results: int = 10) -> List[Dict]:
    """
    Search LinkedIn jobs via DuckDuckGo.

    Args:
        keywords: Search terms (e.g. ["Software Engineer"])
        location: Location string (e.g. "Toronto")
        max_results: Max jobs to return

    Returns:
        List of job dicts matching the standard format:
        {title, company, location, description, url, source, date, job_type}
    """
    if not keywords:
        return []

    query = "site:linkedin.com/jobs " + " ".join(keywords)
    if location:
        query += " " + location

    results = _search_ddg(query, max_results)
    return results


def _search_ddg(query: str, max_results: int) -> List[Dict]:
    """Search DuckDuckGo and parse organic results."""
    import urllib.request

    url = _DDG_URL + "?q=" + quote_plus(query)

    req = urllib.request.Request(url, headers=_HEADERS)
    jobs = []

    try:
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")
        return jobs

    # Parse result blocks
    # Each result: <div class="result results_links ..."> ... <div class="links_main links_deep result__body"> ... </div></div></div>
    blocks = re.findall(
        r'<div class="result results_links[^>]*>.*?<div class="links_main links_deep result__body">(.*?)</div>\s*</div>\s*</div>',
        html,
        re.DOTALL,
    )

    for block in blocks:
        if len(jobs) >= max_results:
            break

        # Extract title + URL
        a_match = re.search(
            r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.DOTALL
        )
        if not a_match:
            continue

        raw_url = a_match.group(1)
        title = re.sub(r"<[^>]+>", "", a_match.group(2)).strip()

        # Unobfuscate DuckDuckGo redirect URL
        job_url = _resolve_ddg_url(raw_url)

        # Skip non-job pages (LinkedIn search pages, not individual postings)
        if not _looks_like_job_page(job_url, title):
            continue

        # Extract snippet (often contains company name, location)
        snippet_match = re.search(
            r'class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL
        )
        snippet = ""
        if snippet_match:
            snippet = re.sub(r"<[^>]+>", "", snippet_match.group(1)).strip()
            snippet = _clean_html_entities(snippet)

        # Parse company and location from title and URL
        company = _extract_company(job_url, title, snippet)
        location = _extract_location(title, snippet)

        job = {
            "title": title,
            "company": company,
            "location": location,
            "description": snippet,
            "url": job_url,
            "source": "LinkedIn",
            "date": "",
            "job_type": "",
        }
        jobs.append(job)

    return jobs


def _resolve_ddg_url(raw_url: str) -> str:
    """Extract the actual URL from DuckDuckGo's redirect link."""
    # DDG format: //duckduckgo.com/l/?uddg=https%3A%2F%2F...&rut=...
    m = re.search(r"uddg=([^&]+)", raw_url)
    if m:
        return unquote(m.group(1))
    # Direct link fallback
    return raw_url


def _looks_like_job_page(url: str, title: str) -> bool:
    """Check if a LinkedIn URL looks like an individual job posting."""
    url_lower = url.lower()

    # Must be LinkedIn
    if "linkedin" not in url_lower:
        return False

    # Skip LinkedIn search pages / company pages
    skip_patterns = [
        "linkedin.com/jobs/",
        "linkedin.com/company/",
        "linkedin.com/in/",
        "linkedin.com/search",
        "linkedin.com/signup",
        "linkedin.com/login",
        "linkedin.com/feed",
    ]

    # Check if it's a search results page (ends with /jobs/ or has /jobs/ without /view/)
    if "linkedin.com/jobs/view/" in url_lower or "linkedin.com/jobs/collections/" in url_lower:
        return True

    # Also accept URLs with /jobs/ followed by a specific job ID
    if re.search(r"linkedin\.com/jobs/\d", url_lower):
        return True

    # If it has /jobs/ in it and the title looks like a job title, accept it
    if "linkedin.com/jobs" in url_lower:
        # Filter out generic "X jobs in Y" titles
        generic_patterns = [
            r"jobs in ",
            r"jobs near ",
            r"hiring\s*$",
            r"\d+.*jobs",
            r"job search",
            r"top companies",
            r"find a job",
        ]
        for pat in generic_patterns:
            if re.search(pat, title.lower()):
                return False
        return True

    return False


def _extract_company(url: str, title: str, snippet: str) -> str:
    """Extract company name from LinkedIn URL or snippet."""
    # Try LinkedIn URL pattern: linkedin.com/jobs/view/1234-at-CompanyName
    m = re.search(r"linkedin\.com/jobs/view/\d+-at-([^/?&]+)", url.lower())
    if m:
        return m.group(1).replace("-", " ").title().strip()

    # Try from URL: linkedin.com/jobs/company-name/jobs/
    m = re.search(r"linkedin\.com/jobs/([^/]+)/jobs/?", url.lower())
    if m:
        return m.group(1).replace("-", " ").title().strip()

    # Try snippet for patterns like "at CompanyName" or "CompanyName is hiring"
    m = re.search(r"\b(?:at|@)\s+([A-Z][A-Za-z0-9\s.&]+?)(?:\s+is\s+hiring|\s+-\s+|\s+\|)", snippet)
    if m:
        return m.group(1).strip()

    return "LinkedIn"


def _extract_location(title: str, snippet: str) -> str:
    """Extract location from title or snippet."""
    # Many LinkedIn job titles end with "- Location"
    m = re.search(r"\s+[-–]\s+([A-Za-z\s,]+(?:Ontario|Canada|ON|USA|United States))$", title)
    if m:
        return m.group(1).strip()

    # Try snippet for location
    m = re.search(r"([A-Z][a-z]+(?:\s*,\s*[A-Z]{2})?)\s*[-–]\s*\d", snippet[:200])
    if m:
        return m.group(1).strip()

    # Try common location patterns in snippet
    m = re.search(r"\b(Toronto|Vancouver|Montreal|Ottawa|Calgary|Waterloo|Kitchener|Remote|San Francisco|New York|Seattle|Austin|Boston|Chicago|Los Angeles|Palo Alto|Sunnyvale|Mountain View)[^.,]*", snippet)
    if m:
        return m.group(0).strip()

    return ""


def _clean_html_entities(text: str) -> str:
    """Clean HTML entities from text."""
    text = text.replace("&#x27;", "'")
    text = text.replace("&#39;", "'")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#xA0;", " ")
    text = text.replace("&#160;", " ")
    return text
