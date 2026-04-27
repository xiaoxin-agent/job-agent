"""Generic job extraction adapter for unknown sites.

Falls back to standard heuristics:
1. JSON-LD structured data
2. OG meta tags
3. <body> text extraction (>300 char blocks)
4. SPA script tag extraction (backslash-u-escaped HTML)
"""

from typing import Dict
import re
import json


def extract(html: str, url: str) -> Dict[str, str]:
    """Extract job info using standard heuristics."""
    result = {
        "title": "",
        "company": "",
        "location": "",
        "description": "",
        "job_type": "",
    }

    # 1. JSON-LD
    _try_json_ld(html, result)

    # 2. OG meta tags
    _try_og_meta(html, result)

    # 3. URL-based company name
    _try_url_company(url, result)

    # 4. Body text extraction
    if not result['description'] or len(result['description']) < 200:
        _try_body_text(html, result)

    # 5. SPA script tags
    if len(result['description']) < 1000:
        _try_script_tags(html, result)

    return result


def _try_json_ld(html: str, result: Dict) -> None:
    """Extract from JSON-LD script tags."""
    jsonlds = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    for jd_raw in jsonlds:
        try:
            data = json.loads(jd_raw)
            if not isinstance(data, dict):
                data = data[0] if isinstance(data, list) and len(data) > 0 else {}
            if data.get('@type') in ('JobPosting', 'job'):
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
                        country = addr.get('addressCountry', '')
                        if isinstance(country, dict):
                            country = country.get('name', '')
                        parts = [p for p in [city, region, country] if p]
                        if parts:
                            result['location'] = ', '.join(parts)
                    else:
                        result['location'] = loc.get('name', '')
                desc = data.get('description', data.get('baseSalary', {}).get('description', ''))
                if desc and len(desc) > len(result['description']):
                    result['description'] = re.sub(r'<[^>]+>', ' ', desc).strip()
                if result['title'] and result['description']:
                    return
        except (json.JSONDecodeError, AttributeError, TypeError):
            continue


def _try_og_meta(html: str, result: Dict) -> None:
    """Extract from OG meta tags."""
    if not result['title']:
        m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html)
        if m:
            result['title'] = m.group(1)
        else:
            m = re.search(r'<title>([^<]+)</title>', html, re.DOTALL)
            if m:
                result['title'] = m.group(1).strip()

    if not result['company']:
        m = re.search(r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)', html)
        if m:
            result['company'] = m.group(1)

    if not result['description']:
        m = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)', html)
        if m:
            result['description'] = re.sub(r'<[^>]+>', ' ', m.group(1)).strip()


def _try_url_company(url: str, result: Dict) -> None:
    """Extract company name from URL domain."""
    if result['company']:
        return
    from sites.registry import known_companies
    url_lower = url.lower()
    for domain, name in known_companies().items():
        if domain in url_lower:
            result['company'] = name
            break


def _try_body_text(html: str, result: Dict) -> None:
    """Extract large text blocks from <body>."""
    cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html, 0, re.DOTALL)
    cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, 0, re.DOTALL)
    blocks = re.findall(r'>([^<]{300,})<', cleaned)
    if not blocks:
        return
    blocks.sort(key=len, reverse=True)
    best = blocks[0].strip()
    if len(best) >= 200:
        result['description'] = re.sub(r'\s+', ' ', best)


def _try_script_tags(html: str, result: Dict) -> None:
    """Extract from SPA script tags with backslash-u-escaped HTML."""
    bs = chr(92)
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    candidates = []

    for s in scripts:
        if len(s) < 200:
            continue
        has_escaped = (bs + 'u003c') in s or (bs + 'u003e') in s
        has_keywords = 'qualification' in s.lower() or 'responsibilit' in s.lower()
        if not has_escaped and not has_keywords:
            continue

        if has_escaped:
            decoded = s.replace(bs + 'u003c', '<').replace(bs + 'u003e', '>')
            decoded = decoded.replace(bs + 'u003d', '=').replace(bs + 'u0026', '&')
            decoded = decoded.replace(bs + "u0027", "'").replace(bs + 'u0022', '"')
            decoded = decoded.replace(bs + 'u002f', '/')
        else:
            decoded = s

        parts = []
        for m in re.finditer(
            r'(<h[1-6][^>]*>.*?</h[1-6]>)\s*(<ul>.*?</ul>)'
            r'|<ul>(.*?)</ul>',
            decoded, re.DOTALL
        ):
            heading_html = m.group(1)
            paired_ul = m.group(2)
            lone_ul = m.group(3)
            if heading_html and paired_ul:
                heading = re.sub(r'<[^>]+>', '', heading_html).strip()
                ul = paired_ul
            elif lone_ul:
                ul = lone_ul
                if not any('Responsibilit' in p for p in parts):
                    heading = 'Responsibilities'
                else:
                    heading = None
            else:
                continue

            items = []
            for li in re.findall(r'<li[^>]*>(.*?)</li>', ul, re.DOTALL):
                clean = re.sub(r'<[^>]+>', '', li).strip()
                clean = clean.replace(bs + 'n', chr(10))
                clean = re.sub(r'\s+', ' ', clean).strip()
                for e, r in [('&amp;','&'),('&lt;','<'),('&gt;','>')]:
                    clean = clean.replace(e, r)
                clean = re.sub(r'&#[0-9]+;', '', clean)
                if clean and len(clean) > 10:
                    items.append('    - ' + clean)

            if items:
                if heading:
                    parts.append(heading)
                parts.extend(items)

        deduped = []
        seen_lines = set()
        for line in parts:
            key = line.lower().strip()
            if key not in seen_lines:
                deduped.append(line)
                if len(line) > 10:
                    seen_lines.add(key)
        parts = deduped

        if parts:
            candidates.append('\n'.join(parts))
            continue

        text = re.sub(r'<[^>]+>', ' ', decoded)
        text = text.replace(bs + 'n', chr(10))
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 300:
            candidates.append(text)

    if not candidates:
        return

    candidates.sort(key=len, reverse=True)
    best = candidates[0]
    if len(best) < 200:
        return

    for marker in ['Responsibilities', 'Minimum qualifications', 'Preferred qualifications', 'About the job']:
        idx = best.find(marker)
        if idx >= 0:
            best = best[idx:]
            break

    if best and len(best) > len(result.get('description', '')):
        result['description'] = best
