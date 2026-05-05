"""Job extraction adapter for LinkedIn Jobs.

Uses Playwright (headless Chromium) to render the page — LinkedIn serves
job details dynamically and blocks curl/requests-based fetchers.

Usage (called from job_agent_core):
    from sites.linkedin import extract
    result = extract(html, url)

Note: html should come from Playwright page.content(), not curl_cffi.
"""

from typing import Dict
import re
import json
import logging

logger = logging.getLogger(__name__)


def extract(html: str, url: str) -> Dict[str, str]:
    """Extract job info from LinkedIn Jobs pages (Playwright-rendered HTML)."""
    result = {
        "title": "",
        "company": "",
        "location": "",
        "description": "",
        "job_type": "",
    }

    _try_json_ld(html, result)
    _try_embedded_data(html, result)
    _try_meta_tags(html, result)
    _try_description_content(html, result)
    _try_company_from_title(result)

    return result


def _try_json_ld(html: str, result: Dict) -> None:
    """Extract from JSON-LD (only present if page has it)."""
    jsonlds = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    for jd_raw in jsonlds:
        try:
            data = json.loads(jd_raw)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                        data = item
                        break
            if not isinstance(data, dict):
                continue
            if data.get('@type') == 'JobPosting':
                if data.get('title'):
                    result['title'] = data['title']
                org = data.get('hiringOrganization', {})
                if isinstance(org, dict) and org.get('name'):
                    result['company'] = org['name']
                loc = data.get('jobLocation', {})
                if isinstance(loc, dict):
                    addr = loc.get('address', {})
                    if isinstance(addr, dict):
                        city = addr.get('addressLocality', '')
                        region = addr.get('addressRegion', '')
                        parts = [p for p in [city, region] if p]
                        result['location'] = ', '.join(parts) or loc.get('name', '')
                    else:
                        result['location'] = loc.get('name', '')
                desc = data.get('description', '')
                if desc:
                    # Keep raw HTML description — _clean_html(keep_format=True) in caller
                    # will handle structure preservation (headings, lists, bold, etc.)
                    result['description'] = desc
                return
        except (json.JSONDecodeError, AttributeError):
            continue


def _try_embedded_data(html: str, result: Dict) -> None:
    """Extract from LinkedIn's embedded data-encoded tags."""
    # LinkedIn Playwright-rendered pages use nested structure:
    # <div class="description__text description__text--rich">
    #   <section class="show-more-less-html">
    #     <div class="show-more-less-html__markup">
    #       <p>...</p>
    #     </div>
    #   </section>
    # </div>

    best_text = ""

    for pattern in [
        # Most specific: description__text--rich container (Playwright render)
        r'class="description__text description__text--rich"[^>]*>(.*?)</div>\s*</section>\s*</div>',
        # show-more-less-html section (Playwright render, inside description__text)
        r'class="show-more-less-html[^"]*"[^>]*>(.*?)</section>',
        # Old format: span with description class
        r'<span[^>]*class=["\'][^"\']*description[^"\']*["\'][^>]*>'
        r'\s*<[^>]+>\s*(.*?)\s*</span>',
    ]:
        for m in re.finditer(pattern, html, re.DOTALL):
            # Keep HTML structure tags — _clean_html(keep_format=True) in the
            # caller will handle converting <strong>/<p>/<ul>/<li>/<br> etc.
            # into Markdown-compatible formatting (headings, lists, bold, etc.)
            text = m.group(1).strip()
            if text and len(text) > len(best_text):
                best_text = text

    if best_text:
        result['description'] = best_text


def _try_meta_tags(html: str, result: Dict) -> None:
    """Extract title, company from OG / meta tags."""
    meta = {}
    for m in re.finditer(r'<meta[^>]+>', html):
        name = (
            re.search(r'property="([^"]+)"', m.group())
            or re.search(r'name="([^"]+)"', m.group())
        )
        content = re.search(r'content="([^"]+)"', m.group())
        if name and content:
            meta[name.group(1)] = content.group(1)

    if not result['title'] and 'og:title' in meta:
        result['title'] = meta['og:title']
        # Clean up " | LinkedIn" suffix
        result['title'] = re.sub(r'\s*\|\s*LinkedIn\s*$', '', result['title'])

    if not result['description'] and 'og:description' in meta:
        result['description'] = meta['og:description']

    if not result['description'] and 'description' in meta:
        result['description'] = meta['description']

    # Try to extract company from og:title like "Ctrl hiring Senior Software Engineer..."
    # Also try article:author or profile:username
    if not result['company'] and 'article:author' in meta:
        result['company'] = meta['article:author']

    # Extract location from og:title "Company hiring Title in Location | LinkedIn"
    if not result['location'] and 'og:title' in meta:
        m = re.search(r'\bin\s+([A-Za-z\s,]+(?:Ontario|Canada|ON|USA|United States|CA)?)\s*\|\s*LinkedIn$', meta['og:title'])
        if m:
            result['location'] = m.group(1).strip()


def _try_description_content(html: str, result: Dict) -> None:
    """Extract job description from visible page content."""
    # Try the show-more-less div which contains full description
    for m in re.finditer(
        r'class=["\'][^"\']*show-more-less[^"\']*["\'][^>]*>(.*?)</div>',
        html, re.DOTALL
    ):
        # Keep HTML structure — caller will apply _clean_html(keep_format=True)
        text = m.group(1)
        if text and len(text) > len(result['description']):
            result['description'] = text

    # Try article content
    article = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)
    if article and not result['description']:
        text = article.group(1)
        if text:
            result['description'] = text


def _try_company_from_title(result: Dict) -> None:
    """Extract company from og:title format 'Company hiring Title...'"""
    if result['company'] or not result['title']:
        return
    m = re.search(r'^(.+?)\s+(?:hiring|is hiring for|is looking for)', result['title'])
    if m:
        result['company'] = m.group(1).strip()

    # LinkedIn sometimes uses "at CompanyName" in the job title
    # But og:title format is usually "Company hiring Title" so above covers it
