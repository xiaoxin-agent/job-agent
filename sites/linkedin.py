"""Job extraction adapter for LinkedIn Jobs.

LinkedIn renders job descriptions server-side with structured content
in <span class="job-description"> or data-encoded attributes.
"""

from typing import Dict
import re
import json


def extract(html: str, url: str) -> Dict[str, str]:
    """Extract job info from LinkedIn Jobs pages."""
    result = {
        "title": "",
        "company": "",
        "location": "",
        "description": "",
        "job_type": "",
    }

    # LinkedIn embeds job data in application/ld+json or window.__INITIAL_STATE__
    _try_json_ld(html, result)
    _try_embedded_data(html, result)

    # Fallback to OG tags
    if not result['title']:
        m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html)
        if m:
            result['title'] = m.group(1)

    if not result['company']:
        m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html)
        if m:
            t = m.group(1)
            if ' - ' in t:
                result['company'] = t.split(' - ')[-1].strip()

    return result


def _try_json_ld(html: str, result: Dict) -> None:
    """Extract from JSON-LD."""
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
                result['title'] = data.get('title', '') or result['title']
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
                    result['description'] = re.sub(r'<[^>]+>', ' ', desc).strip()
                    if len(result['description']) > len(result.get('description', '')):
                        pass
                return
        except (json.JSONDecodeError, AttributeError):
            continue


def _try_embedded_data(html: str, result: Dict) -> None:
    """Extract from window.__INITIAL_STATE__ or data-encoded tags."""
    # LinkedIn sometimes stores description in data-tag
    desc_m = re.search(
        r'<span[^>]*class=["\'][^"\']*description[^"\']*["\'][^>]*>'
        r'\s*<[^>]+>\s*(.*?)\s*</span>',
        html, re.DOTALL
    )
    if desc_m:
        text = re.sub(r'<[^>]+>', '', desc_m.group(1)).strip()
        if text and len(text) > len(result['description']):
            result['description'] = text
