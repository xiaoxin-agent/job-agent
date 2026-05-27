"""
Bank of Canada — SuccessFactors career portal adapter.

URL pattern: careers.bankofcanada.ca

This is an SAP SuccessFactors-hosted career site. The page renders
job details server-side with fairly standard HTML structure:
  - <title> tag contains "Job Title Job Details | Bank of Canada"
  - Job details table (<dl> or similar) with: Requisition Number,
    Position Type, Location, Closing Date
  - Main content body with description sections

We parse the HTML directly since curl/requests work fine (no JS gate).
"""

from typing import Dict
import re


def extract(html: str, url: str) -> Dict[str, str]:
    """Extract job info from a Bank of Canada careers page."""
    result = {
        "title": "",
        "company": "Bank of Canada",
        "location": "",
        "description": "",
        "job_type": "",
    }

    # 1. Title from <title> tag: "Application Development Lead Job Details | Bank of Canada"
    m = re.search(r'<title[^>]*>\s*(.*?)\s*<', html, re.DOTALL)
    if m:
        raw = m.group(1).strip()
        # Strip trailing " Job Details | Bank of Canada" or " | Bank of Canada"
        title = re.sub(r'\s*(Job Details\s*)?\|?\s*Bank of Canada\s*$', '', raw, flags=re.IGNORECASE).strip()
        if title:
            result['title'] = title

    # Fallback: og:title
    if not result['title']:
        m = re.search(r'property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html)
        if m:
            result['title'] = m.group(1).strip()

    # 2. Location — find <span class="jobGeoLocation">Ottawa or Calgary, ON, CA</span>
    m = re.search(r'<span[^>]*class="[^"]*jobGeoLocation[^"]*"[^>]*>\s*([^<]+?)\s*</span>', html)
    if m:
        loc = m.group(1).strip()
        loc = re.sub(r'\s+', ' ', loc).strip()
        if loc:
            result['location'] = loc

    # Fallback: try meta keywords which contains location info
    if not result['location']:
        m = re.search(r'<meta\s+name="keywords"\s+content="([^"]*?Application[^"]*)"', html)
        if m:
            kw = m.group(1).strip()
            # Format: "Ottawa or Calgary Application Development Lead - ON"
            parts = kw.split('Application')
            if parts:
                loc = parts[0].strip()
                if loc:
                    result['location'] = loc
    
    # Another fallback: itemprop addressLocality in JSON-LD
    if not result['location']:
        m = re.search(r'itemprop="addressLocality"[^>]*content="([^"]+)"', html)
        if m:
            loc = m.group(1).strip()
            if loc:
                result['location'] = loc

    # 3. Position type -> job_type
    # "Position Type: Permanent" or "Position Length: Indeterminate"
    pos_type_pat = r'Position\s+Type[^:]*:\s*</[^>]+>\s*<[^>]+>\s*([^<]+)'
    m = re.search(pos_type_pat, html, re.IGNORECASE)
    if m:
        pt = m.group(1).strip()
        if 'permanent' in pt.lower():
            result['job_type'] = 'Full-Time'
        elif 'contract' in pt.lower():
            result['job_type'] = 'Contract'
        elif 'temporary' in pt.lower():
            result['job_type'] = 'Contract'
        elif 'part' in pt.lower():
            result['job_type'] = 'Part-Time'

    # 4. Description — extract the main content body
    result['description'] = _extract_description(html)

    return result


def _extract_description(html: str) -> str:
    """Extract job description from the Bank of Canada career page.

    The page is an SAP SuccessFactors template with this structure:
    - Navigation header
    - Job details table (Requisition Number, Location, etc.)
    - Main content area starting with a section heading like
      "Take a central role" or "What you will do"
    - Footer with "Find similar jobs" / navigation links
    """
    # Remove scripts and styles first
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, 0, re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, 0, re.DOTALL | re.IGNORECASE)

    # Step 1: Find the starting point of job description content
    start_markers = [
        'Take a central role',
        'The team',
        'What you will do',
        'Application Development Lead',
    ]
    start_idx = None
    for marker in start_markers:
        idx = html.find(marker)
        if idx >= 0:
            start_idx = idx
            break

    if start_idx is None:
        return ''

    # Step 2: Find end point — stop before "Find similar jobs" / footer
    end_markers = ['Find similar jobs:', 'Privacy', '<footer']
    end_idx = len(html)
    for marker in end_markers:
        idx = html.find(marker, start_idx)
        if idx >= 0 and idx < end_idx:
            end_idx = idx

    content = html[start_idx:end_idx]

    # Step 3: Strip HTML tags, keeping structure
    # Convert block tags to newlines
    for tag in ['</div>', '</p>', '</li>', '</h1>', '</h2>', '</h3>', '</h4>',
                '</h5>', '</h6>', '<br', '<br/>']:
        content = content.replace(tag, '\n')
    # Convert list items to bullet points
    content = re.sub(r'<li[^>]*>', '  \u2022 ', content)
    # Remove remaining HTML tags
    content = re.sub(r'<[^>]+>', '', content)
    # Decode HTML entities
    content = content.replace('&nbsp;', ' ')
    content = content.replace('&amp;', '&')
    content = content.replace('&lt;', '<')
    content = content.replace('&gt;', '>')
    content = content.replace('&quot;', '"')
    content = content.replace('&#39;', "'")

    # Step 4: Normalize whitespace and clean up
    content = content.replace('\\xa0', ' ')
    content = re.sub(r'[\t\r]+', '', content)
    content = re.sub(r'\n[ \t]+', '\n', content)
    content = re.sub(r'[ \t]+', ' ', content)
    content = re.sub(r'\n{4,}', '\n\n', content)
    # Remove stray '> ' that sometimes appears at line start from HTML blockquote
    content = re.sub(r'^>\s*', '', content, flags=re.MULTILINE)

    # Step 5: Split into lines, deduplicate, filter noise
    lines = content.split('\n')
    cleaned = []
    seen = set()

    noise_prefixes = [
        'javascript:', 'function(', 'var ', 'let ', 'const ', 'cookie',
        'display:', 'position:', '{', '}', '/*', '*/', '//',
        'Skip to main content', '#job-location', '# careers', 'Create Alert',
        'My Profile', 'Apply now', 'job-location-inline',
    ]

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip noise lines
        if any(line.startswith(p) for p in noise_prefixes):
            continue
        # Skip lines that are just the company URL
        if 'bankofcanada.ca' in line and len(line) < 60:
            continue
        # Deduplicate
        key = line.lower().strip()
        if key not in seen:
            cleaned.append(line)
            if len(line) > 3:
                seen.add(key)

    return '\n\n'.join(cleaned).strip()
