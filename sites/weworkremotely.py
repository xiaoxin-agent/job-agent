"""
We Work Remotely job search.

We Work Remotely is a popular remote job board with a curl-friendly website.
No authentication or API key needed.

Reference: https://weworkremotely.com/categories/remote-programming-jobs
"""

from typing import List, Dict, Optional
import re
import logging
from datetime import datetime
from urllib.parse import urljoin

from curl_cffi import requests

logger = logging.getLogger(__name__)

CATEGORIES = {
    "programming": "remote-programming-jobs",
    "devops": "remote-devops-sysadmin-jobs",
    "design": "remote-design-jobs",
    "writing": "remote-writing-jobs",
    "marketing": "remote-marketing-jobs",
    "customer": "remote-customer-support-jobs",
    "data": "remote-data-jobs",
    "product": "remote-product-jobs",
    "sales": "remote-sales-jobs",
    "finance": "remote-finance-legal-jobs",
}

BASE_URL = "https://weworkremotely.com"


def search(keywords: List[str], location: str = "", max_results: int = 10) -> List[Dict]:
    """
    Search We Work Remotely.

    Since WWR is category-based (not keyword search), we fetch the programming
    and devops categories and filter by keywords.

    Args:
        keywords: Search terms to filter by
        location: Ignored (all jobs are remote)
        max_results: Max results

    Returns:
        List of job dicts
    """
    jobs = []

    # Categories most relevant to Cloud/AI/Linux profiles
    # Note: Main category pages only show sub-categories, not jobs.
    # We need to fetch sub-category pages to get actual listings.
    relevant_cats = [
        "remote-back-end-programming-jobs",
        "remote-full-stack-programming-jobs",
        "remote-front-end-programming-jobs",
        "remote-devops-sysadmin-jobs",
        "remote-data-jobs",
        "remote-programming-jobs",
        "remote-software-dev-jobs",
    ]

    for cat_slug in relevant_cats:
        results = _fetch_category(cat_slug)
        jobs.extend(results)
        if len(jobs) >= max_results * 2:  # fetch a bit more then filter
            break

    # Filter by keywords
    filtered = _filter_by_keywords(jobs, keywords)

    return filtered[:max_results]


def extract(html: str, url: str) -> Dict[str, str]:
    """Extract job details from a WWR job page."""
    result = {
        "title": "",
        "company": "",
        "location": "Remote",
        "description": "",
        "job_type": "Full-Time",
    }

    # Title from header
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    if m:
        result['title'] = re.sub(r'<[^>]+>', '', m.group(1)).strip()

    # Company
    m = re.search(r'class=["\']company["\'][^>]*>([^<]+)', html)
    if m:
        result['company'] = m.group(1).strip()

    # Description
    m = re.search(r'<div[^>]*class=["\']listing-container["\'][^>]*>(.*?)</div>\s*</div>\s*</footer>', html, re.DOTALL)
    if m:
        desc = re.sub(r'<[^>]+>', ' ', m.group(1))
        result['description'] = re.sub(r'\s+', ' ', desc).strip()[:3000]

    # Job type
    if 'contract' in html.lower():
        result['job_type'] = 'Contract'
    elif 'part.time' in html.lower():
        result['job_type'] = 'Part-Time'

    return result


def _fetch_category(category_slug: str) -> List[Dict]:
    """Fetch and parse a WWR category page."""
    url = f"{BASE_URL}/categories/{category_slug}"
    jobs = []

    try:
        resp = requests.get(url, impersonate="chrome120", timeout=15)
        if resp.status_code != 200:
            return jobs
        html = resp.text

        # Parse job listings from the sub-category page
        # Each job is in <li class="... listing-container ...">
        # with <a href="/remote-jobs/..."> inside
        listing_blocks = re.findall(
            r'<a[^>]*href="/remote-jobs/([^"]+)"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )

        seen = set()
        for job_slug, content in listing_blocks:
            job_url = f"{BASE_URL}/remote-jobs/{job_slug}"
            if job_url in seen:
                continue
            seen.add(job_url)

            # Extract title and company from the link content
            title = ""
            company = ""

            # Title is in <span class="new-listing__header__title__text">
            t = re.search(r'class=["\']new-listing__header__title__text["\'][^>]*>(.*?)</span>', content, re.DOTALL)
            if t:
                title = re.sub(r'<[^>]+>', '', t.group(1)).strip()

            # Company is in <p class="new-listing__company-name"> or <span>
            c = re.search(r'class=["\']new-listing__company-name["\'][^>]*>(.*?)</p>', content, re.DOTALL)
            if not c:
                c = re.search(r'class=["\']new-listing__company-name["\'][^>]*>(.*?)</span>', content, re.DOTALL)
            if c:
                company = re.sub(r'<[^>]+>', '', c.group(1)).strip()

            location = "Remote"

            # Date from <p class="new-listing__header__icons__date">
            date = ""
            d = re.search(r'class=["\']new-listing__header__icons__date["\'][^>]*>(.*?)</p>', content, re.DOTALL)
            if d:
                date = d.group(1).strip()

            if title:
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "description": "",
                    "url": job_url,
                    "source": "WeWorkRemotely",
                    "date": date,
                    "job_type": "Full-Time",
                })

        logger.debug(f"WWR {category_slug}: found {len(jobs)} jobs")
    except Exception as e:
        logger.warning(f"WWR {category_slug} fetch failed: {e}")

    return jobs


def _filter_by_keywords(jobs: List[Dict], keywords: List[str]) -> List[Dict]:
    """Filter jobs by keyword matching in title/company."""
    if not keywords:
        return jobs

    kw_lower = {k.strip().lower() for k in keywords if k.strip()}

    filtered = []
    for job in jobs:
        text = f"{job['title']} {job['company']}".lower()
        if any(kw in text for kw in kw_lower):
            filtered.append(job)

    # If filtering removed everything, return top results anyway
    if not filtered:
        return jobs[:5]

    return filtered
