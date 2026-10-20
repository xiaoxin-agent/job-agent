"""
Telesat — careers site (www.telesat.com/careers/jobs/<uuid>).

The marketing site is behind an nginx WAF that returns 403 for Chrome-like
impersonation profiles and for plain requests. Safari impersonation gets
through, so the core fetcher retries with that before falling back here.

Job pages are WordPress/Elementor pages rendered by a shortcode plugin:
  title       -> <h1>...</h1> inside elementor-widget-4d684266
  body        -> elementor-widget-2de2cc0c (paragraphs, <h2>, <ul><li>)
  commitment  -> "Commitment: ..." line
  department  -> "Department: ..."
  location    -> "Location: ..."
  team        -> "Team: ..."
  apply URL   -> jobs.lever.co/telesat/<uuid>/apply

Also provides a search helper over the /careers/jobs/ listing table.
"""

import html as html_mod
import json
import re
from typing import Dict, List

SITE = "Telesat"
COMPANY = "Telesat"
LIST_URL = "https://www.telesat.com/careers/jobs/"
SAFARI_IMPERSONATE = "safari17_0"

_DETAIL_PATH_RE = re.compile(
    r"/careers/jobs/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)


def _impersonations() -> List[str]:
    """UA profiles to try. Safari works; Chrome is blocked by the WAF."""
    try:
        from curl_cffi.requests import Session  # noqa: F401
    except Exception:
        return []
    return [SAFARI_IMPERSONATE, "safari17_2_ios", "safari15_5"]


def http_get(url: str, timeout: int = 20) -> str:
    """GET a Telesat page, trying Safari impersonation first. Returns '' on failure."""
    for imp in _impersonations():
        try:
            from curl_cffi import requests as cffi_req
            resp = cffi_req.get(url, impersonate=imp, timeout=timeout)
            if resp.status_code == 200 and len(resp.text) > 2000:
                return resp.text
        except Exception:
            continue
    # Last resort: plain requests (works for the listing page).
    try:
        import requests as std_req
        resp = std_req.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return ""


def normalize_url(url: str) -> str:
    """Telesat detail pages 301 to the trailing-slash form."""
    m = _DETAIL_PATH_RE.search(url)
    if m:
        return f"https://www.telesat.com/careers/jobs/{m.group(1)}/"
    if "?" in url:
        url = url.split("?", 1)[0]
    return url


def _strip_tags(fragment: str) -> str:
    """Turn an HTML fragment into readable plain text, preserving structure."""
    text = fragment
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|h[1-6]|ul|ol|tr|section)>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>", "  • ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_mod.unescape(text).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _widget_inner(html: str, widget_id: str) -> str:
    """Extract the inner HTML of an Elementor widget container by data-id."""
    start = html.find(f'data-id="{widget_id}"')
    if start == -1:
        return ""
    open_div = html.find(">", start)
    if open_div == -1:
        return ""
    return html[open_div + 1:]


def _first_balanced_div(html: str) -> str:
    """Return the content of the outermost <div>...matching </div> in html."""
    depth = 1
    for m in re.finditer(r"<div\b[^>]*>|</div>", html, flags=re.IGNORECASE):
        if m.group(0).lower().startswith("</"):
            depth -= 1
            if depth == 0:
                return html[: m.start()]
        else:
            depth += 1
    return html


def _meta(html: str, key: str, kind: str = "name") -> str:
    m = re.search(
        rf'<meta[^>]+{kind}=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']*)',
        html, flags=re.IGNORECASE,
    )
    return html_mod.unescape(m.group(1)).strip() if m else ""


def _page_title(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    if not m:
        return ""
    title = html_mod.unescape(m.group(1)).strip()
    # "Telesat | Senior Network Management Software Developer"
    parts = [p.strip() for p in title.split("|")]
    if len(parts) > 1 and parts[0].lower().startswith("telesat"):
        title = "|".join(parts[1:]).strip()
    return title


def _details_block(html: str) -> Dict[str, str]:
    """Parse the Commitment/Department/Location/Team sidebar."""
    out: Dict[str, str] = {}
    for label in ("Commitment", "Department", "Location", "Team"):
        m = re.search(
            rf"<strong>\s*{label}\s*:?\s*</strong>\s*([^<]*)",
            html, flags=re.IGNORECASE,
        )
        if m:
            out[label.lower()] = html_mod.unescape(m.group(1)).strip()
    return out


def extract(html: str, url: str) -> Dict[str, str]:
    """Extract job info from a Telesat job detail page."""
    result: Dict[str, str] = {
        "title": "",
        "company": COMPANY,
        "location": "",
        "description": "",
        "job_type": "",
    }
    if not html:
        return result

    # Title: h1 on the page, else <title>/og:title, else the listing row.
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL | re.IGNORECASE)
    if m:
        result["title"] = _strip_tags(m.group(1))
    if not result["title"]:
        result["title"] = _page_title(html) or _meta(html, "og:title", "property")

    # Body: collection of shortcode widgets between the title and the Apply button.
    body_parts: List[str] = []
    h1_pos = html.find("<h1")
    apply_pos = html.find("Apply Now", max(h1_pos, 0))
    scope = html[h1_pos:apply_pos] if h1_pos != -1 and apply_pos != -1 else html
    # Each job paragraph block lives in its own elementor-widget-shortcode.
    for block in re.findall(
        r'<div class="elementor-shortcode">([\s\S]*?)</div>\s*</div>\s*</div>',
        scope,
    ):
        text = _strip_tags(block)
        if len(text) > 30:
            body_parts.append(text)
    description = "\n\n".join(body_parts).strip()
    if len(description) < 200:
        # Fallback: whole column, minus chrome.
        cleaned = _strip_tags(scope)
        if len(cleaned) > len(description):
            description = cleaned
    result["description"] = description

    # Sidebar details.
    details = _details_block(html)
    result["location"] = details.get("location", "")
    result["job_type"] = details.get("commitment", "")
    for key, field in (("department", "department"), ("team", "team")):
        if details.get(key):
            result[field] = details[key]  # type: ignore[literal-required]

    # Apply URL (Lever-hosted).
    m = re.search(r'https://jobs\.lever\.co/telesat/[0-9a-z-]+/?apply', html, re.IGNORECASE)
    if m:
        result["apply_url"] = m.group(0)  # type: ignore[typeddict-unknown-key]

    return result


def parse_listing(html: str) -> List[Dict[str, str]]:
    """Parse /careers/jobs/ rows into {title, department, team, location, url}."""
    jobs: List[Dict[str, str]] = []
    row_re = re.compile(
        r"<div class='wp-lever-jobs-table--row'([^>]*)>(.*?)</div>", re.DOTALL
    )
    for attrs, body in row_re.findall(html):
        def attr(name: str) -> str:
            m = re.search(rf"data-{name}='([^']*)'", attrs)
            return html_mod.unescape(m.group(1)).strip() if m else ""

        m = re.search(r'href="([^"]+)"', body)
        if not m:
            continue
        spans = re.findall(r"<span class='(?:large|medium|small)'>(.*?)</span>", body, re.DOTALL)
        title = _strip_tags(spans[0]) if spans else ""
        jobs.append({
            "title": title,
            "department": attr("department"),
            "team": attr("team"),
            "location": attr("location"),
            "url": "https://www.telesat.com" + m.group(1),
        })
    return jobs


def find_in_listing(html: str, url: str) -> Dict[str, str]:
    """Find the listing row matching this job URL (fallback when detail page is blocked)."""
    m = _DETAIL_PATH_RE.search(url)
    if not m:
        return {}
    job_id = m.group(1).lower()
    for job in parse_listing(html):
        if job_id in job["url"].lower():
            return job
    return {}


def search(keywords: List[str] = None, location: str = "", max_results: int = 20,
           **kwargs) -> List[Dict]:
    """Search the Telesat careers listing (client-side keyword filter)."""
    keywords = [k.lower() for k in (keywords or ["Software", "Engineer"])]
    html = http_get(LIST_URL)
    if not html:
        return []
    out = []
    for job in parse_listing(html):
        haystack = " ".join([job["title"], job["department"], job["team"]]).lower()
        if keywords and not any(k in haystack for k in keywords):
            continue
        if location and location.lower() not in job["location"].lower():
            continue
        out.append({
            "title": job["title"],
            "company": COMPANY,
            "location": job["location"],
            "url": job["url"],
            "department": job["department"],
            "team": job["team"],
            "source": "Telesat",
        })
        if len(out) >= max_results:
            break
    return out


if __name__ == "__main__":  # manual smoke test
    import sys
    u = sys.argv[1] if len(sys.argv) > 1 else ""
    page = http_get(normalize_url(u)) if u else http_get(LIST_URL)
    info = extract(page, u) if u else {}
    print(json.dumps(info, ensure_ascii=False, indent=2)[:2500])
