"""
Deloitte Careers — careers.deloitte.ca (Workday-based but custom domain).

Not a standard .wd{N}.myworkdayjobs.com subdomain, so we cannot use
the generic Workday adapter.  Job detail pages use a custom layout with
<div class="joblayouttoken displayDTM"> blocks and plain text content.

Companies that share the same CMS/Deloitte platform:
  - careers.deloitte.ca
  - careers.deloitte.com
"""

from typing import Dict, List, Optional
import re


SITE = "Deloitte"


def search(keywords: List[str] = None, location: str = "",
           max_results: int = 10, **kwargs) -> List[Dict]:
    """Deloitte does not expose a public search API — mark as unsupported."""
    return []


def extract(html: str, url: str = "") -> Dict[str, str]:
    """Extract job details from a careers.deloitte.ca page."""
    result: Dict[str, str] = {
        "title": "",
        "company": "Deloitte",
        "location": "",
        "description": "",
        "job_type": "",
    }

    # --- Title from <title> ---
    title_m = re.search(r'<title>\s*(.*?)\s*</title>', html, re.DOTALL | re.IGNORECASE)
    if title_m:
        raw = title_m.group(1).strip()
        # Strip trailing " Job Details | Deloitte" or similar
        raw = re.sub(r'\s*(Job Details)?\s*[|–-]\s*.*$', '', raw).strip()
        result["title"] = raw

    # --- Location ---
    loc_m = re.search(
        r'Primary\s*Location:[^<]*?</strong>([^<]+)',
        html, re.IGNORECASE
    )
    if loc_m:
        result["location"] = loc_m.group(1).strip()

    # --- Job type / Work model ---
    jt_m = re.search(r'Work\s*Model:\s*([^<]+)', html, re.IGNORECASE)
    if jt_m:
        result["job_type"] = jt_m.group(1).strip()

    # --- Description ---
    desc = _extract_description(html)
    if desc:
        result["description"] = desc

    return result


def _extract_description(html: str) -> str:
    """Extract job description from the HTML body.

    Strategy:
      1. Find the 'Job Description' label in raw HTML.
      2. Within that window, locate the actual description content
         (starts with a <div><H2> or <p>• or similar after the label).
      3. End at 'Our promise to our people' or land acknowledgement.
    """
    jd_idx = html.find("Job Description")
    if jd_idx == -1:
        return ""

    # Take a generous window after 'Job Description'
    section = html[jd_idx:jd_idx + 30000]

    # Strip script/style blocks
    section = re.sub(r'<script[^>]*>.*?</script>', '', section, flags=re.DOTALL | re.IGNORECASE)
    section = re.sub(r'<style[^>]*>.*?</style>', '', section, flags=re.DOTALL | re.IGNORECASE)

    # Find the actual content start.  After the 'Job Description' label,
    # there are some layout divs, then a div with <H2><b>What will your typical day
    # look like?</b></H2> or the first <p>• bullet.  Skip past the label + layout.
    # Look for the first <H2> with actual heading text, or the first <p> with bullet.
    content_start = 0

    # Try: <H2><b>What will your typical day
    h2_m = re.search(r'<H2>\s*<b>\s*(What will your typical)', section, re.IGNORECASE)
    if h2_m:
        content_start = h2_m.start()
    else:
        # Fallback: first <p>•  after 500 chars (skipping the label + layout)
        p_m = re.search(r'<p>\s*•', section[500:])
        if p_m:
            content_start = 500 + p_m.start()

    if content_start == 0:
        # Ultimate fallback: just start 1000 chars in to skip label + layout
        content_start = 1000

    content = section[content_start:]

    # End at the first known marker AFTER the content starts
    end_markers = [
        r'Our promise to our people',
        r'Deloitte is where potential comes to life',
        r'Deloitte Canada has \d+ offices',
        r'Acknowledgement',
    ]
    best_end = len(content)
    for pat in end_markers:
        m = re.search(pat, content, re.IGNORECASE)
        if m and m.start() > 100 and m.start() < best_end:
            best_end = m.start()

    content = content[:best_end]

    # Strip remaining HTML → plain text
    text = re.sub(r'<[^>]+>', '\n', content)
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    # Clean up whitespace
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    # Remove trailing empty lines or single bullet remnants
    text = re.sub(r'\n\s*•?\s*$', '', text)

    return text
