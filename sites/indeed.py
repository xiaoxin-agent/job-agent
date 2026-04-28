"""
Indeed 职位搜索与详情解析

提供两个主要入口：
  - search(keywords, location, max_results)  → 搜索结果列表
  - extract(html, url)                       → 详情页内容抽取（适配 registry 接口）

注意: Indeed 目前使用 Cloudflare 挑战防护（返回 403），所有浏览器指纹模仿均无效。
      实际使用时需要代理或第三方搜索 API。
"""

import re
from typing import Dict, List, Optional

# ============================================================
# 工具函数（独立轻量版，不依赖外部）
# ============================================================

def _fix_mojibake(text: str) -> str:
    """修复双重编码的 UTF-8 文本（emoji/特殊字符）"""
    if not text:
        return text
    try:
        encoded = text.encode('latin-1')
        fixed = encoded.decode('utf-8')
        has_bad = any(0x80 <= ord(c) <= 0x9F for c in text)
        has_accent = any(0xC0 <= ord(c) <= 0xFF for c in text)
        if has_bad or has_accent:
            if not any(0x80 <= ord(c) <= 0x9F for c in fixed):
                return fixed
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return text


def _clean_html(text: str) -> str:
    """清理HTML标签，保留段落结构，去除反垃圾追踪文本"""
    if not text:
        return ""
    text = _fix_mojibake(text)
    text = re.sub(
        r'Please\s+mention\s+the\s+word\s+\S+\s+and\s+tag\s+\S+.*?(?:\(#\S+\))?\.\s*',
        '', text, flags=re.IGNORECASE | re.DOTALL
    )
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&#39;', "'", text)
    text = re.sub(r'\s{3,}', '\n\n', text)
    return text.strip()


def _beautify_description(raw_html: str) -> str:
    """把HTML详情文本转成美化后的结构化描述"""
    if not raw_html:
        return ""
    text = raw_html
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<li[^>]*>', '• ', text)
    text = text.replace('</li>', '\n')
    text = text.replace('<ul>', '\n')
    text = text.replace('</ul>', '\n')
    text = re.sub(r'<p[^>]*>', '', text)
    text = text.replace('</p>', '\n\n')
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if line:
            lines.append(line)
        else:
            lines.append('')
    text = '\n'.join(lines)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text[:3000]


def _format_job(raw: Dict) -> Dict:
    """格式化单个职位数据为统一格式"""
    job_type = raw.get("job_type", "")
    if not job_type:
        desc = (raw.get("title", "") + " " + raw.get("description", "")).lower()
        if any(kw in desc for kw in ["contract", "contractor"]):
            job_type = "Contract"
        elif any(kw in desc for kw in ["part.time", "parttime"]):
            job_type = "Part-Time"
        elif any(kw in desc for kw in ["full.time", "fulltime", "permanent"]):
            job_type = "Full-Time"
        elif any(kw in desc.split() for kw in ["intern", "internship"]):
            job_type = "Internship"
        elif any(kw in desc for kw in ["freelance", "freelancer"]):
            job_type = "Freelance"
    return {
        "title": raw.get("title", "Unknown"),
        "company": raw.get("company", "Unknown"),
        "location": raw.get("location", "Unknown"),
        "description": raw.get("description", ""),
        "url": raw.get("url", ""),
        "date": raw.get("date", ""),
        "source": "Indeed",
        "job_type": job_type,
    }


# ============================================================
# 搜索（列表页）
# ============================================================

def search(keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
    """
    从 Indeed 搜索职位列表。

    注意：当前 Indeed 使用 Cloudflare 挑战防护，返回 403。
    需要代理或第三方服务才能通过验证。
    """
    from urllib.parse import quote

    if not keywords:
        return []
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split() if k.strip()]

    jobs = []
    kw = quote(" ".join(keywords[:2]))
    loc = quote(location)

    urls = [
        f"https://ca.indeed.com/jobs?q={kw}&l={loc}",
        f"https://www.indeed.com/jobs?q={kw}&l={loc}",
    ]

    try:
        from curl_cffi import requests

        for url in urls:
            if len(jobs) >= max_results:
                break

            resp = requests.get(url, impersonate="chrome120", timeout=20)
            if resp.status_code != 200:
                continue

            html = resp.text
            parsed = _parse_search_results(html, keywords, location, max_results)
            jobs.extend(parsed)

            if jobs:
                break
    except ImportError:
        pass
    except Exception:
        pass

    return jobs


def _parse_search_results(html: str, keywords: List[str], location: str, max_results: int) -> List[Dict]:
    """解析 Indeed 搜索结果 HTML 返回职位列表"""
    jobs = []

    # 步骤1: 提取所有公司名
    companies = []
    for m in re.finditer(r'data-testid="company-name"[^>]*>(.*?)<', html, re.DOTALL):
        txt = _clean_html(m.group(1)).strip()
        if txt:
            companies.append(txt)

    if not companies:
        return jobs

    # 步骤2: 从 aria-label 提取标题
    titles = re.findall(r'aria-label="full details of ([^"]+)"', html)

    # 步骤3: 提取地点
    locs = []
    for m in re.finditer(r'data-testid="text-location"[^>]*>(.*?)<', html, re.DOTALL):
        txt = _clean_html(m.group(1)).strip()
        if txt:
            locs.append(txt)

    # 步骤4: 提取 data-jk 构造链接
    jks = re.findall(r'data-jk="([^"]+)"', html)

    # 步骤5: 组装卡片
    n = min(len(companies), len(titles), len(jks), max_results)
    if n == 0:
        return jobs

    for i in range(n):
        job_url = f"https://ca.indeed.com/viewjob?jk={jks[i]}"
        desc = f"From Indeed - {' '.join(keywords[:2])} in {location}"
        job_type_val = ""

        # 尝试抓详情页
        try:
            detail_info = _fetch_details(job_url)
            if detail_info and detail_info.get("desc"):
                desc = detail_info["desc"]
                job_type_val = detail_info.get("job_type", "")
        except Exception:
            pass

        jobs.append(_format_job({
            "title": titles[i] if i < len(titles) else companies[i],
            "company": companies[i],
            "location": locs[i] if i < len(locs) else location,
            "description": desc,
            "url": job_url,
            "date": "",
            "source": "Indeed",
            "job_type": job_type_val,
        }))

    return jobs


# ============================================================
# 详情页抽取（registry 接口 + 内部使用）
# ============================================================

def extract(html: str, url: str) -> Dict[str, str]:
    """
    Registry 适配器接口。从详情页 HTML 抽取职位信息。

    Args:
        html: 详情页 HTML
        url:  详情页 URL

    Returns:
        {title, company, location, description, job_type}
    """
    result = {
        "title": "",
        "company": "",
        "location": "",
        "description": "",
        "job_type": "",
    }

    # Title
    title_m = re.search(r'<title>([^<]+)</title>', html)
    if title_m:
        result["title"] = title_m.group(1).strip()

    # OG title fallback
    og_m = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
    og_title = og_m.group(1) if og_m else ""
    if og_title:
        parts = og_title.split(" - ")
        if len(parts) >= 2:
            result["title"] = parts[0].strip()
            result["company"] = parts[1].strip()

    # Company name from JSON-LD
    jsonlds = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    import json as _json
    for raw in jsonlds:
        try:
            data = _json.loads(raw)
            if isinstance(data, list):
                data = data[0] if data else {}
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                if not result["title"]:
                    result["title"] = data.get("title", "")
                org = data.get("hiringOrganization", {})
                if isinstance(org, dict) and org.get("name"):
                    result["company"] = org["name"]
                loc = data.get("jobLocation", {})
                if isinstance(loc, dict):
                    addr = loc.get("address", {})
                    if isinstance(addr, dict):
                        city = addr.get("addressLocality", "")
                        region = addr.get("addressRegion", "")
                        parts = [p for p in [city, region] if p]
                        result["location"] = ", ".join(parts)
                desc = data.get("description", "")
                if desc:
                    result["description"] = re.sub(r"<[^>]+>", " ", desc).strip()
                    break
        except (_json.JSONDecodeError, AttributeError):
            continue

    # Company from og:site_name
    if not result["company"]:
        site_m = re.search(r'<meta[^>]+property="og:site_name"[^>]+content="([^"]+)"', html)
        if site_m:
            result["company"] = site_m.group(1)

    # Description fallback: jobDescriptionText
    if not result["description"]:
        for pat in [
            r'id="jobDescriptionText"[^>]*>(.*?)</div>\s*</div>',
            r'id="jobDescriptionText"[^>]*>(.*?)(?:<div[^>]+id=)',
            r'class="[^"]*jobsearch-JobComponent-description[^"]*"[^>]*>(.*?)(?:<div[^>]*class="[^"]*jobsearch)',
        ]:
            m = re.search(pat, html, re.DOTALL)
            if m and len(m.group(1)) > 100:
                result["description"] = _beautify_description(m.group(1))
                if len(result["description"]) > 100:
                    break

    if not result["description"]:
        result["description"] = _beautify_description(html)

    # Job type
    jt_match = re.search(r'data-testid="([A-Za-z-]+tile)"', html)
    if jt_match:
        raw = jt_match.group(1).replace("-tile", "").lower()
        if "full" in raw:
            result["job_type"] = "Full-Time"
        elif "part" in raw:
            result["job_type"] = "Part-Time"
        elif "contract" in raw:
            result["job_type"] = "Contract"
        elif "temp" in raw:
            result["job_type"] = "Temporary"
        elif "intern" in raw:
            result["job_type"] = "Internship"

    return result


# ============================================================
# 详情页抓取（内部使用，被 search() 调用）
# ============================================================

def _fetch_details(url: str) -> Dict:
    """抓取 Indeed 详情页返回 {desc, job_type}"""
    result = {"desc": "", "job_type": ""}
    try:
        from curl_cffi import requests
        resp = requests.get(url, impersonate="chrome120", timeout=15)
        if resp.status_code != 200:
            return result
        extracted = extract(resp.text, url)
        if extracted:
            result["desc"] = extracted.get("description", "")
            result["job_type"] = extracted.get("job_type", "")
    except Exception:
        pass
    return result
