"""Job extraction adapter for Google Careers (SPA with backslash-u-escaped HTML in <script> tags).

Google Careers stores job description HTML inside <script> tags with unicode
escape sequences (backslash-u003c for <, backslash-u003e for >, etc.). We decode these tags and
extract the structured description from heading + <ul> pairs.
"""

from typing import Dict
import re


def extract(html: str, url: str) -> Dict[str, str]:
    """Extract job info from Google Careers pages."""
    result = {
        "title": "",
        "company": "Google",
        "location": "",
        "description": "",
        "job_type": "",
    }

    # Try JSON-LD first (Google often includes it)
    jsonlds = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL
    )

    import json
    for jd_raw in jsonlds:
        try:
            jd = json.loads(jd_raw)
            if isinstance(jd, list):
                jd = jd[0] if jd else {}
            if jd.get('@type') in ('JobPosting',):
                result['title'] = jd.get('title', '') or result['title']
                # Company from hiringOrganization
                org = jd.get('hiringOrganization', {})
                if isinstance(org, dict) and org.get('name'):
                    result['company'] = org['name']
                # Location
                loc = jd.get('jobLocation', {})
                if isinstance(loc, dict):
                    if '@type' in loc:
                        addr = loc.get('address', {})
                        city = addr.get('addressLocality', '')
                        region = addr.get('addressRegion', '')
                        parts = [p for p in [city, region] if p]
                        result['location'] = ', '.join(parts)
                # Description
                desc = jd.get('description', '')
                if desc and len(desc) > len(result['description']):
                    result['description'] = re.sub(r'<[^>]+>', ' ', desc).strip()
        except (json.JSONDecodeError, AttributeError):
            pass

    if result['description'] and len(result['description']) >= 1000:
        return result

    # Fallback: get title from OG meta or <title> if JSON-LD didn't have it
    if not result['title']:
        og_title = re.search(
            r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
            html
        )
        if og_title:
            result['title'] = og_title.group(1)
        else:
            title_m = re.search(r'<title>([^<]+)</title>', html, re.DOTALL)
            if title_m:
                # Google Careers format: "Job Title — Google Careers"
                t = title_m.group(1).strip()
                t = re.sub(r'\s*[—–-]\s*Google\s*Careers.*$', '', t)
                result['title'] = t.strip()

    # Fallback: extract from SPA script tags with \u-escaped HTML
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

        # Build structured description by scanning decoded HTML sequentially
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

        # Deduplicate
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
        return result

    candidates.sort(key=len, reverse=True)
    best = candidates[0]
    if len(best) < 200:
        return result

    for marker in ['Responsibilities', 'Minimum qualifications', 'Preferred qualifications', 'About the job']:
        idx = best.find(marker)
        if idx >= 0:
            best = best[idx:]
            break

    result["description"] = best
    return result
