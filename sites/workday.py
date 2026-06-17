"""
Workday — Generic Workday job board adapter.

Workday (WD) is a common ATS used by many companies including:
  Red Hat, SUSE, NVIDIA, Cisco, Adobe, Salesforce, Zoom, etc.

Each company has its own Workday tenant at:
  https://{company}.wd{N}.myworkdayjobs.com

The search API is at:
  POST /wday/cxs/{company}/{siteId}/jobs
  body: {"limit": N, "offset": 0}

Job detail pages embed JSON-LD with basic info.
"""

from typing import Dict, List, Optional
import re
import json
import time

from curl_cffi import requests

# ---------------------------------------------------------------------------
# Configuration for each Workday company
# ---------------------------------------------------------------------------
# Fields:
#   domain:      Workday subdomain (e.g. "redhat.wd5.myworkdayjobs.com")
#   site_id:     Site identifier in the API URL (e.g. "jobs" or "Jobsatsuse")
#   company:     Display name
#   locale:      Language tag for detail page URLs
#   sections:    Section headers in JSON-LD description (for formatting)
#   relevant_kws: Keywords used for matching relevance (optional)
#
WORKDAY_COMPANIES: Dict[str, Dict] = {
    "RedHat": {
        "domain": "redhat.wd5.myworkdayjobs.com",
        "site_id": "jobs",
        "company": "Red Hat",
        "locale": "en-US",
        "sections": [
            "About the Job",
            "What You Will Do",
            "What You Will Bring",
            "The following are considered as a plus",
            "About Red Hat",
            "Inclusion at Red Hat",
            "Equal Opportunity Policy",
        ],
    },
    "SUSE": {
        "domain": "suse.wd3.myworkdayjobs.com",
        "site_id": "Jobsatsuse",
        "company": "SUSE",
        "locale": "en-US",
        "sections": [
            "About Us",
            "About the Role",
            "The Role",
            "Responsibilities",
            "What You Will Do",
            "What You Will Bring",
            "Qualifications",
            "Requirements",
            "Required Skills and Experience",
            "Preferred Skills",
            "Nice to Have",
            "Skills",
            "About SUSE",
            "What SUSE Offers",
            "Benefits",
            "Inclusion at SUSE",
            "Equal Opportunity",
            "Diversity and Inclusion",
        ],
    },
    "NVIDIA": {
        "domain": "nvidia.wd5.myworkdayjobs.com",
        "site_id": "NVIDIAExternalCareerSite",
        "company": "NVIDIA",
        "locale": "en-US",
        "sections": [
            "NVIDIA",
            "What we need to see",
            "What you'll be doing:",
            "Ways to stand out from the crowd:",
            "Minimum Requirements",
            "Preferred Qualifications",
            "Qualifications",
            "Responsibilities",
        ],
    },
    "Ciena": {
        "domain": "ciena.wd5.myworkdayjobs.com",
        "site_id": "Careers",
        "company": "Ciena",
        "locale": "en-US",
        "sections": [
            "About the Job",
            "What You Will Do",
            "What You Will Bring",
            "Qualifications",
            "Requirements",
            "About Ciena",
            "Inclusion at Ciena",
            "Equal Opportunity",
        ],
    },
    "BlackBerry": {
        "domain": "bb.wd3.myworkdayjobs.com",
        "site_id": "BlackBerry",
        "company": "BlackBerry QNX",
        "locale": "en-US",
        "sections": [
            "About the Job",
            "Qualifications",
            "Requirements",
            "About BlackBerry",
            "Equal Opportunity",
        ],
    },
    "Alphawave": {
        "domain": "alphawave.wd10.myworkdayjobs.com",
        "site_id": "Alphawave_External",
        "company": "Alphawave Semi",
        "locale": "en-US",
        "sections": [
            "About the Role",
            "Qualifications",
            "Requirements",
            "Responsibilities",
            "What You Will Do",
            "What You Will Bring",
            "About Alphawave",
            "Equal Opportunity",
        ],
    },
    "Mitel": {
        "domain": "mitel.wd3.myworkdayjobs.com",
        "site_id": "mitelcareers",
        "company": "Mitel",
        "locale": "en-US",
        "sections": [
            "About the Role",
            "Qualifications",
            "Requirements",
            "Responsibilities",
            "What You Will Do",
            "What You Will Bring",
            "About Mitel",
            "Equal Opportunity",
        ],
    },
    "Intel": {
        "domain": "intel.wd1.myworkdayjobs.com",
        "site_id": "External",
        "company": "Intel",
        "locale": "en-US",
        "sections": [
            "Job Description",
            "Qualifications",
            "Minimum Qualifications",
            "Preferred Qualifications",
            "Responsibilities",
            "Inside this Business Group",
            "Posting Statement",
            "Benefits",
            "Job Type",
            "Shift",
            "Primary Location",
            "Additional Locations",
            "Work Model",
        ],
    },
    "TrendMicro": {
        "domain": "trendmicro.wd3.myworkdayjobs.com",
        "site_id": "External",
        "company": "Trend Micro",
        "locale": "en-US",
        "sections": [
            "About the Role",
            "Qualifications",
            "Requirements",
            "Key Responsibilities",
            "Responsibilities",
            "Position Summary",
            "Preferred",
            "Education",
            "What We Offer",
            "About Trend Micro",
            "About TrendAI",
            "Equal Opportunity",
        ],
    },
}


def get_company(company_key: str) -> Optional[Dict]:
    """Look up a company config by its key."""
    return WORKDAY_COMPANIES.get(company_key)


def list_companies() -> List[str]:
    """Return all configured company keys."""
    return list(WORKDAY_COMPANIES.keys())


def add_company(key: str, domain: str, site_id: str, company: str,
                locale: str = "en-US", sections: List[str] = None) -> None:
    """Programmatically register a new Workday company."""
    from copy import deepcopy
    base = deepcopy(WORKDAY_COMPANIES.get("SUSE", {}))
    base["domain"] = domain
    base["site_id"] = site_id
    base["company"] = company
    base["locale"] = locale
    if sections:
        base["sections"] = sections
    WORKDAY_COMPANIES[key] = base


def _format_description(text: str, sections: List[str]) -> str:
    """Convert Workday plain-text description with minimal formatting.

    Workday JSON-LD descriptions are continuous text with section headers.
    We preserve the original text and only bold known section headers.
    No <p> wrapping — let the frontend display it as-is.
    """
    if not text:
        return ""

    header_pattern = "(" + "|".join(
        rf"\b{re.escape(h)}(?:\s*[:?])?" for h in sections
    ) + ")"
    parts = re.split(header_pattern, text, flags=re.IGNORECASE)

    if len(parts) < 2:
        # No recognizable headers — return raw text unchanged
        return text

    result_parts = []
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if not part:
            i += 1
            continue
        clean = part.rstrip(":? ").strip()
        is_header = any(clean.lower() == h.lower() for h in sections)
        if is_header:
            result_parts.append(f"\n<strong>{clean}</strong>\n")
            if i + 1 < len(parts):
                body = parts[i + 1].strip()
                body = re.sub(r'^[:?]\s*', '', body)
                result_parts.append(body)
                i += 2
            else:
                i += 1
        else:
            result_parts.append(part)
            i += 1

    return "\n".join(result_parts).strip()


def _auto_format_description(text: str) -> str:
    """Auto-format a Workday description that has no recognized section headers.

    Handles two common formats:
    1. Single-line continuous text (no actual newlines) — split on patterns like
       "Key Responsibilities:", "Qualifications:", capitalized sentence-starting
       section headers, common JD section names.
    2. Text with embedded \\n escapes that need rendering.

    Returns text with proper \n line breaks.
    """
    if not text:
        return ""

    # Handle \\n escape sequences (literal backslash-n)
    if r"\n" in text and "\n" not in text:
        text = text.replace(r"\n", "\n")

    # If there are already real newlines, just normalize whitespace
    if "\n" in text or "\r" in text:
        lines = re.split(r"\r?\n", text)
        # Collapse multiple blank lines
        cleaned = []
        blank = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if not blank:
                    cleaned.append("")
                    blank = True
            else:
                cleaned.append(stripped)
                blank = False
        return "\n".join(cleaned).strip()

    # Single-line text: try to split on section-like headers
    # Common JD section headers that start sentences/paragraphs
    section_patterns = [
        r"Job Description:\s*",
        r"Job Details:\s*",
        r"Key Responsibilities:",
        r"Responsibilities:",
        r"Qualifications:",
        r"Minimum Qualifications:",
        r"Preferred Qualifications:",
        r"Required Qualifications:",
        r"Requirements:",
        r"About the Role:",
        r"About the Team:",
        r"What You Will Do:",
        r"What You Will Bring:",
        r"Professional traits:",
        r"Inside this Business Group:",
        r"Posting Statement:",
        r"Benefits:",
        r"Salary Range:",
        r"Work Model:",
    ]

    combined_pattern = "(" + "|".join(section_patterns) + ")"
    parts = re.split(combined_pattern, text, flags=re.IGNORECASE | re.DOTALL)

    if len(parts) < 3:
        # No recognizable headers — wrap long text at sentence boundaries
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
        if len(sentences) > 1:
            return "\n\n".join(s.strip() for s in sentences if s.strip())
        return text

    # Found section headers: format with bold headers
    result_parts = []
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if not part:
            i += 1
            continue
        # Check if this part is a section header match
        clean = part.rstrip(":? ").strip()
        is_header = any(
            clean.lower() == h.replace("\\s*", "").rstrip(":? ").lower().replace("\\s*", "")
            for h in section_patterns
        ) or re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*:\s*$", clean + ":", re.DOTALL)
        if is_header:
            result_parts.append(f"\n<strong>{clean}</strong>\n")
            if i + 1 < len(parts):
                body = parts[i + 1].strip()
                body = re.sub(r'^[:?]\s*', '', body)
                result_parts.append(body)
                i += 2
            else:
                i += 1
        else:
            result_parts.append(part)
            i += 1

    return "\n".join(result_parts).strip()


def extract(html: str, url: str = "") -> Dict[str, str]:
    """Extract job details from a generic Workday job page.

    Adapter interface for registry. Detects company from the URL.
    """
    result = {
        "title": "",
        "company": "",
        "location": "",
        "description": "",
        "job_type": "Full-Time",
    }

    # Detect company from URL
    company_config = _detect_company_from_url(url)
    if company_config:
        result["company"] = company_config["company"]
    sections = company_config.get("sections", []) if company_config else []

    try:
        jsonlds = re.findall(
            r'<script[^>]+type=[\"\']application/ld\+json[\"\'][^>]*>'
            r'(.*?)</script>', html, re.DOTALL
        )
        for raw in jsonlds:
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                result["title"] = data.get("title") or result["title"]
                desc = data.get("description") or ""
                if desc:
                    if sections:
                        result["description"] = _format_description(desc.strip(), sections)
                    else:
                        # 没有 sections 配置时，尝试自动格式化
                        fmt = _auto_format_description(desc.strip())
                        result["description"] = fmt
                loc = data.get("jobLocation", {})
                if isinstance(loc, dict):
                    addr = loc.get("address", {})
                    locality = addr.get("addressLocality", "")
                    region = addr.get("addressRegion", "")
                    country = addr.get("addressCountry", "")
                    parts = [p for p in [locality, region, country] if p]
                    result["location"] = ", ".join(parts)
                employment = data.get("employmentType", "")
                if employment:
                    result["job_type"] = employment.replace("_", "-").title()
                break
    except Exception:
        pass
    return result


def _detect_company_from_url(url: str) -> Optional[Dict]:
    """Find the company config whose domain matches the given URL."""
    for cfg in WORKDAY_COMPANIES.values():
        domain = cfg["domain"]
        if domain in url:
            return cfg
    return None


def _build_api_url(company_config: Dict) -> str:
    """Build the Workday search API URL for a company."""
    domain = company_config["domain"]
    company_name = company_config["company"].lower().replace(" ", "")
    site_id = company_config["site_id"]
    # The domain is already company-specific, but we need to extract the short name
    # e.g. redhat.wd5 -> company=redhat, suse.wd3 -> company=suse
    short_name = domain.split(".")[0]
    return f"https://{domain}/wday/cxs/{short_name}/{site_id}/jobs"


def _build_job_page_url(company_config: Dict, external_path: str) -> str:
    """Build the full job detail URL."""
    domain = company_config["domain"]
    locale = company_config.get("locale", "en-US")
    site_id = company_config["site_id"]
    return f"https://{domain}/{locale}/{site_id}{external_path}"


def search(company_key: str, keywords: List[str] = None,
           location: str = "", max_results: int = 10) -> List[Dict]:
    """Search jobs for a specific Workday company.

    Args:
        company_key: Key in WORKDAY_COMPANIES (e.g. "RedHat", "SUSE")
        keywords: List of search keywords (OR matching on title)
        location: Location filter (not strict — Workday locations vary)
        max_results: Maximum jobs to return

    Returns:
        List of job dicts
    """
    config = WORKDAY_COMPANIES.get(company_key)
    if not config:
        return []

    return _search_api(company_key, config, keywords, config.get("locale", "en-US"),
                       max_results, location)


def _search_api(company_key: str, company_config: Dict, keywords: List[str], locale: str,
                limit: int = 20, location: str = "") -> List[Dict]:
    """Query Workday search API and filter results."""
    api_url = _build_api_url(company_config)
    page_size = min(limit * 3, 20)

    search_query = " ".join(keywords).strip() if keywords else ""

    def _fetch(offset: int) -> Optional[Dict]:
        try:
            payload = {"limit": page_size, "offset": offset}
            if search_query:
                payload["searchText"] = search_query
            resp = requests.post(
                api_url, json=payload,
                impersonate="chrome120",
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=20,
            )
            return resp.json() if resp.status_code == 200 else None
        except Exception:
            return None

    # Fetch initial page
    data = None
    for attempt in range(3):
        data = _fetch(0)
        if data is not None:
            break
        time.sleep(2 * (attempt + 1))
    if data is None:
        return []

    job_postings = list(data.get("jobPostings", []))

    # Paginate keyword search results — Workday limit is 20/page, but
    # ASIC-related jobs can span 3+ pages. 3 pages (60 jobs) covers most
    # location-filtered searches. No keyword = single page of latest jobs.
    max_pages = 3 if search_query else 0
    for page in range(1, max_pages + 1):
        # Collect enough: we want limit * 5 for location filtering headroom
        if len(job_postings) >= limit * 5:
            break
        offset = page * page_size
        page_data = None
        for attempt in range(3):
            page_data = _fetch(offset)
            if page_data is not None:
                break
            time.sleep(2 * (attempt + 1))
        if page_data is None or not page_data.get("jobPostings"):
            break
        job_postings.extend(page_data["jobPostings"])

    # Filter and build results
    company_name = company_config["company"]
    results = []
    for job in job_postings:
        title = job.get("title", "")
        locations_text = (job.get("locationsText") or "")
        external_path = job.get("externalPath", "")
        detail_url = _build_job_page_url(company_config, external_path) if external_path else ""

        # Location filter
        if location and location.lower() not in ("remote", "global"):
            loc_lower = location.lower()
            loc_ok = False
            for part in loc_lower.split(","):
                part = part.strip()
                if part and part in locations_text.lower():
                    loc_ok = True
                    break
            if not loc_ok:
                user_w = {w for w in re.split(r"[\s,]+", loc_lower) if len(w) > 2}
                txt_w = {w for w in re.split(r"[\s,\/]+", locations_text.lower()) if len(w) > 2}
                if user_w & txt_w:
                    loc_ok = True
            if not loc_ok and "remote" in locations_text.lower():
                loc_ok = True
            if not loc_ok:
                continue

        results.append({
            "title": title,
            "company": company_name,
            "location": locations_text or "Global / Remote",
            "description": title,
            "url": detail_url,
            "source": company_key,
            "date": job.get("postedOn", ""),
            "job_type": "Full-Time",
            "remote": "Remote",
            "departments": [],
            "salary_min": 0,
            "salary_max": 0,
            "currency": "USD",
        })
        if len(results) >= limit:
            break

    return results[:limit]


# ---------------------------------------------------------------------------
# Company-specific search functions (for registry / backward compatibility)
# ---------------------------------------------------------------------------
def search_redhat(keywords: List[str] = None, location: str = "",
                  max_results: int = 10) -> List[Dict]:
    return search("RedHat", keywords, location, max_results)


def search_suse(keywords: List[str] = None, location: str = "",
                max_results: int = 10) -> List[Dict]:
    return search("SUSE", keywords, location, max_results)


def search_nvidia(keywords: List[str] = None, location: str = "",
                  max_results: int = 10) -> List[Dict]:
    return search("NVIDIA", keywords, location, max_results)


def search_ciena(keywords: List[str] = None, location: str = "",
                 max_results: int = 10) -> List[Dict]:
    return search("Ciena", keywords, location, max_results)


def search_blackberry(keywords: List[str] = None, location: str = "",
                      max_results: int = 10) -> List[Dict]:
    return search("BlackBerry", keywords, location, max_results)


def search_alphawave(keywords: List[str] = None, location: str = "",
                     max_results: int = 10) -> List[Dict]:
    return search("Alphawave", keywords, location, max_results)


def search_mitel(keywords: List[str] = None, location: str = "",
                  max_results: int = 10) -> List[Dict]:
    return search("Mitel", keywords, location, max_results)


def search_intel(keywords: List[str] = None, location: str = "",
                 max_results: int = 10) -> List[Dict]:
    return search("Intel", keywords, location, max_results)


def search_trendmicro(keywords: List[str] = None, location: str = "",
                       max_results: int = 10) -> List[Dict]:
    return search("TrendMicro", keywords, location, max_results)

