"""Job extraction adapter for amazon.jobs.

Amazon renders job descriptions server-side in this structure:

<div id="job-detail-body">
  <div class="section"><h2>Description</h2><p>...</p></div>
  <div class="section"><h2>Basic Qualifications</h2><p>...</p></div>
  <div class="section"><h2>Preferred Qualifications</h2><p>...</p></div>
</div>

Key: each <div class="section"> has an <h2> heading followed by a <p> containing
all content (with <br/> line breaks instead of <ul>/<li>).
"""

from typing import Dict
import re


def extract(html: str, url: str) -> Dict[str, str]:
    """Extract job info from amazon.jobs pages."""
    result = {
        "title": "",
        "company": "Amazon",
        "location": "",
        "description": "",
        "job_type": "",
    }

    # Title from job-detail header
    title_m = re.search(
        r'<h[1-6][^>]*class="[^"]*"[^>]*>([^<]+)</h[1-6]>\s*'
        r'<[^>]+>\s*Job ID:',
        html, re.DOTALL
    )
    if not title_m:
        # Fallback: any h1/h2 near info-wrapper
        title_m = re.search(
            r'class="[^"]*info-wrapper[^"]*"[^>]*>'
            r'\s*<h[1-6][^>]*>([^<]+)</h[1-6]>',
            html, re.DOTALL
        )
    if not title_m:
        # Fallback: og:title
        title_m = re.search(
            r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
            html
        )
    if title_m:
        result["title"] = title_m.group(1).strip()

    # Location from the info area (contains "|" separator with location)
    loc_m = re.search(
        r'class="[^"]*info-wrapper[^"]*"[^>]*>.*?\|\s*([A-Za-z].*?)(?:</|$)',
        html, re.DOTALL
    )
    if loc_m:
        loc = loc_m.group(1).strip()
        # Remove trailing HTML-like fragments
        loc = re.sub(r'<[^<].*', '', loc).strip()
        if loc:
            result["location"] = loc

    # Description from job-detail-body
    body_m = re.search(
        r'<div[^>]*id="job-detail-body"[^>]*>(.*?)</div>\s*</div>\s*</div>',
        html, re.DOTALL
    )
    if not body_m:
        body_m = re.search(
            r'<div[^>]*id="job-detail-body"[^>]*>(.*?)</div>',
            html, re.DOTALL
        )

    if body_m:
        body_html = body_m.group(1)

        # Remove scripts and styles
        body_html = re.sub(r'<script[^>]*>.*?</script>', '', body_html, 0, re.DOTALL)
        body_html = re.sub(r'<style[^>]*>.*?</style>', '', body_html, 0, re.DOTALL)

        # Extract each section: <div class="section"> with <h2> heading + <p> content
        parts = []
        sections = re.findall(
            r'<div[^>]*class="[^"]*section[^"]*"[^>]*>'
            r'\s*<h[1-6][^>]*>(.*?)</h[1-6]>'
            r'\s*(.*?)'
            r'\s*</div>',
            body_html, re.DOTALL
        )

        for heading_html, content_html in sections:
            heading = re.sub(r'<[^>]+>', '', heading_html).strip()
            if not heading:
                continue

            # Amazon puts list items inside <p> separated by <br/>
            # First get the text
            text_content = re.sub(r'<[^>]+>', '\n', content_html)
            text_content = re.sub(r'\n\s*\n', '\n', text_content).strip()

            # Split by <br/> markers into bullet points
            # Since <br/> was replaced with '\n', we look for lines starting with '-'
            lines = text_content.split('\n')
            items = []
            for line in lines:
                line = line.strip()
                # Filter: skip empty, skip very short fragments
                if not line or len(line) < 5:
                    continue
                # Strip leading dash/bullet if present
                clean = line.lstrip('-*• ').strip()
                items.append(clean)

            if items:
                parts.append(heading)
                for item in items:
                    parts.append(f"    - {item}")

        if parts:
            result["description"] = '\n'.join(parts)
        else:
            # Fallback: just extract body text
            text = re.sub(r'<[^>]+>', ' ', body_html)
            text = re.sub(r'\s+', ' ', text).strip()
            if text:
                result["description"] = text

    else:
        # Try broader fallback: find the content wrapper
        outer = re.search(
            r'class="[^"]*content[^"]*"[^>]*>'
            r'(.*?)'
            r'</div>\s*</div>\s*</div>\s*</div>\s*</div>\s*</div>'
            r'(?:</main|<footer)',
            html, re.DOTALL
        )
        if outer:
            text = re.sub(r'<[^>]+>', ' ', outer.group(1))
            text = re.sub(r'\s+', ' ', text).strip()
            if text and len(text) > 200:
                result["description"] = text

    return result
