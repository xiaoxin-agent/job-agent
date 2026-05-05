#!/usr/bin/env python3
"""
求职Agent - Web版
核心系统：搜索、分析、匹配、跟踪
"""

import datetime
import json
import os
import re
import random
import hashlib
import time
from typing import List, Dict, Optional
from job_agent_apply import ApplyManager

# ============================================================
# 配置文件
# ============================================================

class Config:
    # 工作目录
    WORKSPACE = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(WORKSPACE, "agent_data")
    
    # 端口
    PORT = 9999
    
    # 默认搜索设置
    DEFAULT_KEYWORDS = ["Cloud", "AI", "Linux", "ML", "Kernel", "DevOps", "Kubernetes"]
    DEFAULT_LOCATIONS = ["Toronto", "Vancouver", "Remote Canada", "Canada"]
    
    # 用户画像文件
    PROFILE_FILE = os.path.join(DATA_DIR, "user_profile.json")
    JOBS_FILE = os.path.join(DATA_DIR, "tracked_jobs.json")
    SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

# ============================================================
# 用户画像分析器
# ============================================================

class UserProfile:
    """
    管理用户技能画像，用于职位匹配度分析
    """
    
    DEFAULT_PROFILE = {
        "name": "",
        "title": "Cloud/AI/Linux Engineer",
        "skills": {
            # 核心技能 (权重高)
            "Cloud": {
                "keywords": ["AWS", "Azure", "GCP", "Kubernetes", "Docker", "Terraform", "CloudFormation"],
                "level": "expert",  # beginner / intermediate / expert
                "years": 5
            },
            "Linux": {
                "keywords": ["Linux", "Unix", "Ubuntu", "CentOS", "Kernel", "Bash", "Shell"],
                "level": "expert",
                "years": 5
            },
            "AI/ML": {
                "keywords": ["Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "Neural Network", "LLM", "AI"],
                "level": "intermediate",
                "years": 3
            },
            "Python": {
                "keywords": ["Python", "Django", "Flask", "FastAPI"],
                "level": "expert",
                "years": 5
            },
            # 扩展技能
            "C/C++": {
                "keywords": ["C", "C++", "CUDA", "GPU Programming"],
                "level": "intermediate",
                "years": 3
            },
            "DevOps": {
                "keywords": ["CI/CD", "Jenkins", "GitLab", "Ansible", "Prometheus", "Grafana"],
                "level": "intermediate",
                "years": 3
            }
        },
        "experience_years": 5,
        "education": "Computer Science / Engineering",
        "preferred_roles": [
            "ML Kernel Engineer",
            "AI Infrastructure Engineer",
            "Cloud AI Developer",
            "Performance Engineer",
            "Systems Engineer"
        ],
        "preferred_companies": ["Amazon", "Google", "Microsoft", "NVIDIA", "IBM", "AMD", "Intel"],
        "preferred_locations": ["Toronto", "Vancouver", "Remote Canada", "Remote US"],
        "salary_expectation": {
            "min": 130000,
            "max": 250000,
            "currency": "CAD"
        }
    }
    
    def __init__(self, profile_file: str):
        self.profile_file = profile_file
        self.profile = self._load()
    
    def _load(self) -> Dict:
        """加载用户画像"""
        if os.path.exists(self.profile_file):
            try:
                with open(self.profile_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return dict(self.DEFAULT_PROFILE)
        return dict(self.DEFAULT_PROFILE)
    
    def save(self):
        """保存用户画像"""
        os.makedirs(os.path.dirname(self.profile_file), exist_ok=True)
        with open(self.profile_file, "w", encoding="utf-8") as f:
            json.dump(self.profile, f, ensure_ascii=False, indent=2)
    
    def get_skill_keywords(self) -> List[str]:
        """获取所有技能关键词"""
        keywords = []
        for category, info in self.profile.get("skills", {}).items():
            keywords.extend(info.get("keywords", []))
        return list(set(keywords))
    
    def update_profile(self, updates: Dict):
        """更新用户画像"""
        for key, value in updates.items():
            if key in self.profile:
                if isinstance(self.profile[key], dict) and isinstance(value, dict):
                    self.profile[key].update(value)
                else:
                    self.profile[key] = value
        self.save()

# ============================================================
# 职位搜索引擎
# ============================================================

class JobSearchEngine:
    """
    多源职位搜索引擎
    从不同渠道获取职位信息
    """
    
    def __init__(self, profile: UserProfile):
        self.profile = profile
    

    def _infer_job_type(self, tags: list, title: str, desc: str) -> str:
        """从 tags / title / desc 推断职位类型"""
        text = (title + " " + desc).lower()
        tag_text = " ".join(t.lower() for t in (tags or []) if isinstance(t, str))
        full_text = text + " " + tag_text
        # Use word boundary matching to avoid false positives like 'internal' → 'intern'
        words = set(full_text.split())
        if any(w in words for w in ["contract", "contractor"]):
            return "Contract"
        if any(w in words for w in ["part-time", "parttime", "part time"]):
            return "Part-Time"
        if any(w in words for w in ["full-time", "fulltime", "full time", "permanent"]):
            return "Full-Time"
        if any(w in words for w in ["intern", "internship"]):
            return "Internship"
        if any(w in words for w in ["freelance", "freelancer"]):
            return "Freelance"
        if "co-op" in words or "coop" in words:
            return "Co-op"
        return ""
    
    def search_github_jobs(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]
        """搜索GitHub Jobs"""
        jobs = []
        
        try:
            import requests
            
            query = "+".join(keywords[:2])
            url = f"https://jobs.github.com/positions.json?description={query}"
            
            print(f"搜索GitHub: {query}")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                for job in data[:max_results]:
                    title = job.get("title", "")
                    desc_text = job.get("description", "")
                    full_text = (desc_text + " " + title).lower()
                    if any(kw.lower() in full_text for kw in keywords):
                        jobs.append(self._format_job({
                            "title": job.get("title", ""),
                            "company": job.get("company", ""),
                            "location": job.get("location", ""),
                            "description": self._clean_html(job.get("description", "")),
                            "url": job.get("url", ""),
                            "date": job.get("created_at", ""),
                            "source": "GitHub Jobs"
                        }))
                        if len(jobs) >= max_results:
                            break
        except Exception as e:
            print(f"GitHub Jobs 搜索失败: {e}")
        
        return jobs
    
    def search_indeed(self, location: str, max_results: int = 5, keywords: List[str] = None) -> List[Dict]:
        """委托 sites.indeed.search 进行 Indeed 搜索"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]

        from sites.indeed import search as indeed_search
        return indeed_search(keywords, location, max_results)
    
    def search_canonical(self, location: str, max_results: int = 5, keywords: List[str] = None) -> List[Dict]:
        """委托 sites.canonical.search 进行 Canonical 职位搜索"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]

        from sites.canonical import search as canonical_search
        return canonical_search(keywords, location, max_results)

    def search_redhat(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
        """委托 sites.redhat.search 进行 Red Hat 职位搜索"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]

        from sites.redhat import search as redhat_search
        return redhat_search(keywords, location, max_results)

    def search_nvidia(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
        """委托 sites.nvidia.search 进行 NVIDIA 职位搜索"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]

        from sites.nvidia import search as nvidia_search
        return nvidia_search(keywords, location, max_results)

    def search_suse(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
        """委托 sites.suse.search 进行 SUSE 职位搜索"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]

        from sites.suse import search as suse_search
        return suse_search(keywords, location, max_results)


    def search_ciena(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
        """委托 sites.ciena.search 进行 Ciena 职位搜索"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]
        from sites.ciena import search as ciena_search
        return ciena_search(keywords, location, max_results)

    def search_blackberry(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
        """委托 sites.blackberry.search 进行 BlackBerry 职位搜索"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]
        from sites.blackberry import search as blackberry_search
        return blackberry_search(keywords, location, max_results)

    def search_alphawave(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
        """委托 sites.alphawave.search 进行 Alphawave 职位搜索"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]
        from sites.alphawave import search as alphawave_search
        return alphawave_search(keywords, location, max_results)

    def search_solace(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
        """委托 sites.solace.search 进行 Solace 职位搜索"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]
        from sites.solace import search as solace_search
        return solace_search(keywords, location, max_results)

    def search_fullscript(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
        """委托 sites.fullscript.search 进行 Fullscript 职位搜索"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]
        from sites.fullscript import search as fullscript_search
        return fullscript_search(keywords, location, max_results)

    def search_weworkremotely(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
        """委托 sites.weworkremotely.search 进行 WeWorkRemotely 搜索"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]

        from sites.weworkremotely import search as wwr_search
        return wwr_search(keywords, location, max_results)

    def search_google_jobs(self, location: str, max_results: int = 5, keywords: List[str] = None) -> List[Dict]:
        """委托 sites.google_jobs.search 进行 Google 搜索聚合"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]

        from sites.google_jobs import search as google_search
        return google_search(keywords, location, max_results)

    def search_linkedin(self, location: str, max_results: int = 5, keywords: List[str] = None) -> List[Dict]:
        """委托 sites.linkedin_search.search 进行 LinkedIn 搜索"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]

        from sites.linkedin_search import search as linkedin_search
        return linkedin_search(keywords, location, max_results)

    def search_amazon(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
        """委托 sites.amazon_search.search 进行 Amazon Canada 职位搜索"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]

        from sites.amazon_search import search as amazon_search
        return amazon_search(keywords, location, max_results)

    def search_google_careers(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
        """委托 sites.google_careers_search.search 进行 Google Careers 职位搜索"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]

        from sites.google_careers_search import search as google_careers_search
        return google_careers_search(keywords, location, max_results)

    def search_mitel(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
        """委托 sites.workday.search 进行 Mitel 职位搜索 (Workday)"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]

        from sites.workday import search_mitel as mitel_search
        return mitel_search(keywords, location, max_results)

    def search_magnetforensics(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
        """委托 sites.lever.search 进行 Magnet Forensics 职位搜索 (Lever)"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]

        from sites.lever import search_magnetforensics as magnet_search
        return magnet_search(keywords, location, max_results)

    def search_telesat(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
        """委托 sites.lever.search 进行 Telesat 职位搜索 (Lever)"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]

        from sites.lever import search_telesat as telesat_search
        return telesat_search(keywords, location, max_results)

    def search_trendmicro(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
        """委托 sites.workday.search 进行 Trend Micro 职位搜索 (Workday)"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]

        from sites.workday import search_trendmicro as trendmicro_search
        return trendmicro_search(keywords, location, max_results)

    def search_ranovus(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
        """委托 sites.ranovus.search 进行 Ranovus 职位搜索 (BambooHR)"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]

        from sites.ranovus import search as ranovus_search
        return ranovus_search(keywords, location, max_results)

    def search_nokia(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
        """委托 sites.nokia.search 进行 Nokia 职位搜索 (Oracle HCM)
        
        ⚠️ 已知限制：Nokia 的 Oracle HCM 租户（CX_1）在服务器端做
        了限制，API 永远只返回固定的 25 个职位，所有关键字/地点筛选
        和分页参数均被忽略。实际数据库有 867 个职位（加拿大 107 个），
        但 API 拒绝返回。详情见 sites/nokia.py 的模块文档。
        """
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]

        from sites.nokia import search as nokia_search
        return nokia_search(keywords, location, max_results)

    def search_fortinet(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
        """委托 sites.fortinet.search 进行 Fortinet 职位搜索"""
        if not keywords:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]

        from sites.fortinet import search as fortinet_search
        return fortinet_search(keywords, location, max_results)

    def search_remoteok(self, max_results: int = 5, keywords: List[str] = None) -> List[Dict]:
        """搜索RemoteOK"""
        jobs = []
        
        try:
            import requests
            
            url = "https://remoteok.io/api"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 1:
                    # Use user keywords if provided, else fall back to profile skills
                    import re
                    skills = keywords if keywords else self.profile.get_skill_keywords()
                    for item in data[1:]:
                        title = item.get("position", "")
                        desc = item.get("description", "")
                        title_lower = title.lower()
                        desc_lower = desc.lower()
                        
                        # Match full keyword phrase (word boundary) — allows partial keyword overlap in title
                        _EXCLUDE_DESC_WORDS = {'driver': ['driver of', 'driver for', 'key driver']}
                        
                        matched = False
                        for s in skills:
                            sw = s.strip().lower()
                            if not sw:
                                continue
                            # Title match (word boundary)
                            if re.search(r'\b' + re.escape(sw) + r'\b', title_lower):
                                matched = True
                                break
                        
                        if not matched:
                            # Description match with exclusion for common false positives
                            for s in skills:
                                sw = s.strip().lower()
                                if not sw or not re.search(r'\b' + re.escape(sw) + r'\b', desc_lower):
                                    continue
                                excluded = False
                                if sw in _EXCLUDE_DESC_WORDS:
                                    for pat in _EXCLUDE_DESC_WORDS[sw]:
                                        if pat in desc_lower:
                                            excluded = True
                                            break
                                if not excluded:
                                    matched = True
                                    break
                        
                        if matched:
                            tags = item.get("tags", [])
                            job_type = self._infer_job_type(tags, title, desc)
                            jobs.append(self._format_job({
                                "title": title,
                                "company": item.get("company", ""),
                                "location": "Remote",
                                "description": self._clean_html(desc),
                                "url": f"https://remoteok.io/remote-jobs/{item.get('slug', '')}",
                                "date": item.get("date", ""),
                                "source": "RemoteOK",
                                "job_type": job_type
                            }))
                            if len(jobs) >= max_results:
                                break
        except:
            pass
        
        return jobs
    
    def generate_search_links(self, user_keywords: List[str] = None) -> List[Dict]:
        """生成动态搜索链接（用户可在浏览器打开）"""
        keywords = user_keywords or self.profile.get_skill_keywords()[:3]
        locations = self.profile.profile.get("preferred_locations", ["Canada"])
        
        links = []
        timestamp = int(time.time())
        
        company_searches = [
            {
                "name": "Amazon",
                "url_template": "https://www.amazon.jobs/en/search?base_query={keyword}+engineer&loc_query={location}&ts={ts}",
                "keywords": ["ML", "Kernel", "AWS", "Cloud", "AI"]
            },
            {
                "name": "Google",
                "url_template": "https://careers.google.com/jobs/results/?q={keyword}+{location}&ts={ts}",
                "keywords": ["AI", "Infrastructure", "Cloud", "ML"]
            },
            {
                "name": "Microsoft",
                "url_template": "https://careers.microsoft.com/us/en/search-results?keywords={keyword}%20{location}&ts={ts}",
                "keywords": ["Linux", "Kernel", "Azure", "AI"]
            },
            {
                "name": "NVIDIA",
                "url_template": "https://www.nvidia.com/en-us/about-nvidia/careers/search/?q={keyword}+{location}&ts={ts}",
                "keywords": ["GPU", "CUDA", "Performance", "AI"]
            },
            {
                "name": "IBM",
                "url_template": "https://www.ibm.com/careers/us-en/search/?q={keyword}+{location}&ts={ts}",
                "keywords": ["ML", "Systems", "Cloud", "AI"]
            }
        ]
        
        for company in company_searches:
            keyword = random.choice(company["keywords"])
            location = random.choice(locations)
            
            url = company["url_template"].format(
                keyword=keyword,
                location=location,
                ts=timestamp
            )
            
            links.append({
                "title": f"{company['name']} - {keyword} Engineer in {location}",
                "company": company["name"],
                "url": url,
                "keywords": [keyword],
                "timestamp": timestamp,
                "source": "search_link"
            })
        
        # 通用搜索链接
        for kw in keywords[:2]:
            for loc in locations[:1]:
                search_query = f"{kw} engineer {loc}"
                url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}&ts={timestamp}"
                
                links.append({
                    "title": f"Google - {kw} Engineer {loc}",
                    "company": "Google (通用搜索)",
                    "url": url,
                    "keywords": [kw],
                    "timestamp": timestamp,
                    "source": "search_link"
                })
        
        return links
    
    def search_all(self, max_per_source: int = 8, sources: List[str] = None, keywords: List[str] = None, location: str = None) -> Dict:
        """多源搜索，可指定来源和关键词/地点"""
        if keywords is None:
            keywords = self.profile.get_skill_keywords()[:3]
        elif isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split() if k.strip()]
        if location is None:
            location = self.profile.profile.get("preferred_locations", ["Canada"])[0]
        
        source_map = {
            "GitHub Jobs": lambda: self.search_github_jobs(keywords, location, max_per_source),
            "RemoteOK": lambda: self.search_remoteok(max_per_source, keywords),
            "Indeed": lambda: self.search_indeed(location, max_per_source, keywords),
            "LinkedIn": lambda: self.search_linkedin(location, max_per_source, keywords),
            "GoogleJobs": lambda: self.search_google_jobs(location, max_per_source, keywords),
            "WeWorkRemotely": lambda: self.search_weworkremotely(keywords, location, max_per_source),
            "Canonical": lambda: self.search_canonical(location, max_per_source, keywords),
            "RedHat": lambda: self.search_redhat(keywords, location, max_per_source),
            "SUSE": lambda: self.search_suse(keywords, location, max_per_source),
            "NVIDIA": lambda: self.search_nvidia(keywords, location, max_per_source),
            "Ciena": lambda: self.search_ciena(keywords, location, max_per_source),
            "BlackBerry": lambda: self.search_blackberry(keywords, location, max_per_source),
            "Alphawave": lambda: self.search_alphawave(keywords, location, max_per_source),
            "Solace": lambda: self.search_solace(keywords, location, max_per_source),
            "Fullscript": lambda: self.search_fullscript(keywords, location, max_per_source),
            "Amazon": lambda: self.search_amazon(keywords, location, max_per_source),
            "Google": lambda: self.search_google_careers(keywords, location, max_per_source),
            "Mitel": lambda: self.search_mitel(keywords, location, max_per_source),
            "MagnetForensics": lambda: self.search_magnetforensics(keywords, location, max_per_source),
            "Fortinet": lambda: self.search_fortinet(keywords, location, max_per_source),
            "Telesat": lambda: self.search_telesat(keywords, location, max_per_source),
            "TrendMicro": lambda: self.search_trendmicro(keywords, location, max_per_source),
            "Ranovus": lambda: self.search_ranovus(keywords, location, max_per_source),
            "Nokia": lambda: self.search_nokia(keywords, location, max_per_source),
        }
        
        all_jobs = []
        search_links = []
        
        # 默认搜索所有来源
        if not sources:
            sources = list(source_map.keys())
        
        for src in sources:
            fn = source_map.get(src)
            if fn:
                print(f"搜索来源: {src}")
                try:
                    jobs = fn()
                    all_jobs.extend(jobs)
                except Exception as e:
                    print(f"{src} 搜索出错: {e}")
        
        # 搜索链接只对综合搜索生成
        if len(sources) > 1:
            search_links = self.generate_search_links()
        
        # 去重
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            key = f"{job.get('title', '')}_{job.get('company', '')}"
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)
        
        return {
            "jobs": unique_jobs,
            "search_links": search_links,
            "stats": {
                "total_jobs": len(unique_jobs),
                "total_links": len(search_links),
                "search_time": datetime.datetime.now().isoformat(),
                "search_id": hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
            }
        }
    
    def _beautify_description(self, raw_html: str) -> str:
        """把HTML详情文本转成美化后的结构化描述"""
        if not raw_html:
            return ""
        import re
        
        html = raw_html
        text = html
        
        # 加
        # 提取可见内容
        # 保留<ul> <li> <br> <p>的结构
        # 先把<br>、<br/>、<br />换成
        text = re.sub(r'<br\s*/?>', '\n', text)
        # 保留列表结构
        text = re.sub(r'<li[^>]*>', '• ', text)
        text = text.replace('</li>', '\n')
        text = text.replace('<ul>', '\n')
        text = text.replace('</ul>', '\n')
        # p段落换行
        text = re.sub(r'<p[^>]*>', '', text)
        text = text.replace('</p>', '\n\n')
        # 清理其他标签
        text = re.sub(r'<[^>]+>', '', text)
        # 解码HTML实体
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        # 清理多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        # 清理行首尾空格
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
    

    
    def _format_job(self, raw: Dict) -> Dict:
        """格式化职位数据"""
        job_type = raw.get("job_type", "")
        if not job_type:
            # fallback: infer from description
            desc = (raw.get("title", "") + " " + raw.get("description", "")).lower()
            if any(kw in desc for kw in ["contract", "contractor"]):
                job_type = "Contract"
            elif any(kw in desc for kw in ["part.time", "parttime"]):
                job_type = "Part-Time"
            elif any(kw in desc for kw in ["full.time", "fulltime", "permanent"]):
                job_type = "Full-Time"
            # Match whole word to avoid 'internal' matching 'intern'
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
            "source": raw.get("source", ""),
            "job_type": job_type,
            "analyzed": False,
            "match_score": 0,
            "match_details": {},
            "status": "new",
            "saved_at": datetime.datetime.now().isoformat()
        }
    
    @staticmethod
    def _fix_mojibake(text: str) -> str:
        """修复双重编码的 UTF-8 文本（emoji/特殊字符）
        
        RemoteOK 等源有时返回被 Latin-1 双重编码的 UTF-8 字符串，
        如 📈 \u2192 \xf0\x9f\x93\x88 \u2192 Ã°\x9f\x93\x88
        """
        if not text:
            return text
        try:
            encoded = text.encode('latin-1')
            fixed = encoded.decode('utf-8')
            # 修复后的文本不应包含 C1 控制字符或一个字节拆成多个字符的产物
            # 检查：修复后的文本是否包含更多有效的高位字符（U+0080+），
            # 且原始文本有明显的 UTF-8 双编码特征
            has_bad = any(0x80 <= ord(c) <= 0x9F for c in text)
            has_accent = any(0xC0 <= ord(c) <= 0xFF for c in text)
            if has_bad or has_accent:
                # 额外检查：修复后不再有 C1 控制字符
                if not any(0x80 <= ord(c) <= 0x9F for c in fixed):
                    return fixed
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
        return text

    def _clean_html(self, text: str) -> str:
        """清理HTML标签，保留段落结构，去除反垃圾追踪文本"""
        if not text:
            return ""
        text = self._fix_mojibake(text)
        # Remove anti-spam tracking tags common in RemoteOK job postings
        # e.g. "Please mention the word **EMINENT** and tag RMTczLjcyLjYuMjQ1 ..."
        text = re.sub(
            r'Please\s+mention\s+the\s+word\s+\S+\s+and\s+tag\s+\S+.*?(?:\(#\S+\))?\.\s*',
            '', text, flags=re.IGNORECASE | re.DOTALL
        )
        text = re.sub(
            r'This is a beta feature to avoid spam applicants\..*?(?:\.|$)\s*',
            '', text, flags=re.IGNORECASE | re.DOTALL
        )
        # 把<br>、</p>、</li>、</div>等换成换行
        text = re.sub(r'<br\s*/?>', '\n', text)
        text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</li>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</h[1-6]>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<li[^>]*>', '  • ', text)
        # 清理剩余HTML标签
        text = re.sub(r'<[^>]+>', ' ', text)
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        # 合并多余空白
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        # 清理每行首尾空格
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            lines.append(line)
        text = '\n'.join(lines)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        return text

# ============================================================
# 职位分析器
# ============================================================

class JobAnalyzer:
    """
    分析职位与用户的匹配度
    """
    
    def __init__(self, profile: UserProfile):
        self.profile = profile
    
    def analyze_job(self, job: Dict) -> Dict:
        """分析单个职位"""
        if job.get("source") == "search_link":
            return job  # 搜索链接不需要分析
        
        title = (job.get("title", "") + " " + job.get("description", "")).lower()
        
        # 分析技能匹配
        matched_skills = []
        missing_skills = []
        total_weight = 0
        matched_weight = 0
        
        for category, info in self.profile.profile.get("skills", {}).items():
            weight = self._get_category_weight(category)
            total_weight += weight
            
            category_matched = False
            for keyword in info.get("keywords", []):
                if keyword.lower() in title:
                    matched_skills.append({
                        "category": category,
                        "keyword": keyword,
                        "level": info.get("level", "intermediate"),
                        "score": self._skill_match_score(info.get("level", "intermediate"))
                    })
                    matched_weight += weight
                    category_matched = True
                    break
            
            if not category_matched:
                # 检查是否有部分匹配
                for keyword in info.get("keywords", []):
                    parts = keyword.lower().split()
                    if len(parts) > 1 and any(p in title for p in parts):
                        matched_skills.append({
                            "category": category,
                            "keyword": keyword,
                            "level": info.get("level", "intermediate"),
                            "score": self._skill_match_score(info.get("level", "intermediate")) * 0.5,
                            "partial": True
                        })
                        matched_weight += weight * 0.5
                        break
        
        # 计算总体匹配度
        match_score = round((matched_weight / total_weight) * 100) if total_weight > 0 else 0
        
        # 提取薪资信息
        salary_info = self._extract_salary(job.get("description", ""))
        
        # 地点匹配
        location = job.get("location", "").lower()
        preferred = [l.lower() for l in self.profile.profile.get("preferred_locations", [])]
        location_match = any(p in location for p in preferred)
        
        # 公司匹配
        company = job.get("company", "").lower()
        preferred_companies = [c.lower() for c in self.profile.profile.get("preferred_companies", [])]
        company_match = any(pc in company for pc in preferred_companies)
        
        # 角色匹配
        role = job.get("title", "").lower()
        preferred_roles = [r.lower() for r in self.profile.profile.get("preferred_roles", [])]
        role_match = any(pr in role for pr in preferred_roles)
        
        result = {
            **job,
            "analyzed": True,
            "match_score": match_score,
            "match_details": {
                "skill_match": matched_skills,
                "matched_skills_count": len(matched_skills),
                "salary": salary_info,
                "location_match": location_match,
                "company_match": company_match,
                "role_match": role_match
            },
            "analysis_time": datetime.datetime.now().isoformat()
        }
        
        return result
    
    def analyze_all(self, search_result: Dict) -> Dict:
        """分析所有职位"""
        analyzed_jobs = []
        
        for job in search_result.get("jobs", []):
            analyzed = self.analyze_job(job)
            analyzed_jobs.append(analyzed)
        
        # 按匹配度排序
        analyzed_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        
        return {
            "jobs": analyzed_jobs,
            "search_links": search_result.get("search_links", []),
            "stats": {
                **search_result.get("stats", {}),
                "analyzed_jobs": len(analyzed_jobs),
                "high_match": len([j for j in analyzed_jobs if j.get("match_score", 0) >= 70]),
                "medium_match": len([j for j in analyzed_jobs if 40 <= j.get("match_score", 0) < 70]),
                "low_match": len([j for j in analyzed_jobs if j.get("match_score", 0) < 40]),
                "avg_match_score": round(sum(j.get("match_score", 0) for j in analyzed_jobs) / len(analyzed_jobs)) if analyzed_jobs else 0
            }
        }
    
    @staticmethod
    def _get_category_weight_static(category: str) -> float:
        """获取技能类别权重（静态版本）"""
        weights = {
            "Cloud": 25,
            "AI/ML": 25,
            "Linux": 20,
            "Python": 15,
            "C/C++": 10,
            "DevOps": 5
        }
        return weights.get(category, 10)
    
    @staticmethod
    def _skill_match_score_static(level: str) -> float:
        """获取技能匹配得分（静态版本）"""
        scores = {
            "expert": 1.0,
            "intermediate": 0.7,
            "beginner": 0.4
        }
        return scores.get(level, 0.5)
    
    def _get_category_weight(self, category: str) -> float:
        """获取技能类别权重"""
        return self._get_category_weight_static(category)
    
    def _skill_match_score(self, level: str) -> float:
        """获取技能匹配得分"""
        return self._skill_match_score_static(level)
    
    def _extract_salary(self, text: str) -> Optional[Dict]:
        """从文本中提取薪资信息"""
        patterns = [
            r'\$([0-9,]+)\s*[-–to]+\s*\$?([0-9,]+)\s*(K|k|CAD|USD)?',
            r'([0-9]+)\s*[-–to]+\s*([0-9]+)\s*(K|k)?\s*(CAD|USD)?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    groups = match.groups()
                    min_sal = float(groups[0].replace(",", ""))
                    max_sal = float(groups[1].replace(",", ""))
                    
                    if groups[2] and groups[2].upper() == 'K':
                        min_sal *= 1000
                        max_sal *= 1000
                    
                    currency = groups[3] if len(groups) > 3 and groups[3] else "CAD"
                    
                    return {
                        "min": min_sal,
                        "max": max_sal,
                        "currency": currency,
                        "text": match.group(0)
                    }
                except:
                    pass
        
        return None
    
    def generate_cover_letter(self, job: Dict) -> str:
        """生成定制求职信"""
        company = job.get("company", "Hiring Team")
        title = job.get("title", "position")
        
        # 提取匹配的技能
        match_details = job.get("match_details", {})
        matched_skills = match_details.get("skill_match", [])
        
        # 提取技能分类
        skill_categories = {}
        for skill in matched_skills:
            cat = skill.get("category", "Other")
            if cat not in skill_categories:
                skill_categories[cat] = []
            skill_categories[cat].append(skill.get("keyword"))
        
        skills_text = ""
        if skill_categories:
            skills_text = "I bring strong expertise in:\n"
            for cat, keywords in skill_categories.items():
                skills_text += f"  • {cat}: {', '.join(keywords[:3])}\n"
        
        letter = f"""Dear {company} Hiring Team,

I am writing to express my strong interest in the {title} position. With {self.profile.profile.get('experience_years', 5)}+ years of experience spanning cloud infrastructure, Linux systems, and AI/ML technologies, I believe my background aligns closely with your requirements.

{skills_text}
My experience includes designing and optimizing high-performance systems at the intersection of cloud computing and AI infrastructure. I have deep expertise in Linux system programming and cloud-native technologies, combined with practical experience in machine learning frameworks and deployment pipelines.

I am particularly excited about this opportunity because it leverages my strongest skills while pushing into areas where I am eager to grow further. The chance to work on cutting-edge {self.profile.profile.get('preferred_roles', ['systems'])[0]} challenges is exactly what I am looking for in my next role.

I would welcome the opportunity to discuss how my experience can contribute to your team's success. Thank you for your consideration.

Best regards,
{self.profile.profile.get('name', 'Your Name')}"""

        return letter

# ============================================================
# 申请跟踪器
# ============================================================

class JobTracker:
    """
    跟踪职位申请状态
    """
    
    def __init__(self, jobs_file: str):
        self.jobs_file = jobs_file
        self.tracked_jobs = self._load()
    
    def _load(self) -> List[Dict]:
        """加载跟踪数据，自动修复数据不一致"""
        if os.path.exists(self.jobs_file):
            try:
                with open(self.jobs_file, "r", encoding="utf-8") as f:
                    jobs = json.load(f)
                # 修复 interviewing 但 interviews 为空的不一致
                for job in jobs:
                    if job.get("status") == "interviewing":
                        interviews = job.get("interviews")
                        if not interviews or len(interviews) == 0:
                            job["status"] = "applied"
                return jobs
            except:
                return []
        return []
    
    def save(self):
        """保存跟踪数据"""
        os.makedirs(os.path.dirname(self.jobs_file), exist_ok=True)
        with open(self.jobs_file, "w", encoding="utf-8") as f:
            json.dump(self.tracked_jobs, f, ensure_ascii=False, indent=2)
    
    def add_job(self, job: Dict):
        """添加职位到跟踪列表"""
        now = datetime.datetime.now().isoformat()
        tracked = {
            "id": hashlib.md5(f"{job.get('title')}_{job.get('company')}_{time.time()}".encode()).hexdigest()[:8],
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "url": job.get("url", ""),
            "description": job.get("description", ""),
            "job_type": job.get("job_type", ""),
            "match_score": job.get("match_score", 0),
            "source": job.get("source", ""),
            "status": "saved",  # saved / applied / interviewing / rejected / offer
            "notes": "",
            "cover_letter": "",
            "applied_date": None,
            "interview_dates": [],
            "follow_up_dates": [],
            "saved_at": now,
            "last_updated": now,
            "status_history": [{"status": "saved", "timestamp": now, "from": ""}]
        }
        
        # 去重
        for existing in self.tracked_jobs:
            if existing["title"] == tracked["title"] and existing["company"] == tracked["company"]:
                return False
        
        self.tracked_jobs.insert(0, tracked)
        self.save()
        return True
    
    def update_cover_letter(self, title: str, company: str, letter: str) -> bool:
        """保存/更新职位的求职信（通过 title+company 匹配）"""
        for job in self.tracked_jobs:
            if job["title"] == title and job["company"] == company:
                job["cover_letter"] = letter
                job["last_updated"] = datetime.datetime.now().isoformat()
                self.save()
                return True
        return False

    def update_cover_letter_by_id(self, job_id: str, letter: str) -> bool:
        """通过 job_id 保存/更新求职信"""
        for job in self.tracked_jobs:
            if job["id"] == job_id:
                job["cover_letter"] = letter
                job["last_updated"] = datetime.datetime.now().isoformat()
                self.save()
                return True
        return False

    def update_status(self, job_id: str, status: str, notes: str = ""):
        """更新申请状态，自动记录每次状态变更时间。"""
        for job in self.tracked_jobs:
            if job["id"] == job_id:
                now = datetime.datetime.now().isoformat()
                old_status = job.get("status")
                job["status"] = status
                job["last_updated"] = now

                # 首次标记 applied 时记录
                if status == "applied" and not job.get("applied_date"):
                    job["applied_date"] = now

                # 面试轮次记录
                if status == "interviewing":
                    if "interviews" not in job:
                        job["interviews"] = []
                    next_round = len(job["interviews"]) + 1
                    job["interviews"].append({
                        "round": next_round,
                        "date": now,
                        "notes": notes or ""
                    })
                    # 在状态历史中标记轮次
                    status_label = f"interviewing_{next_round}"
                else:
                    status_label = status

                # 状态变更历史（只记录实际变化，忽略重复点击）
                if status != old_status:
                    if "status_history" not in job:
                        job["status_history"] = []
                    job["status_history"].append({
                        "status": status_label,
                        "timestamp": now,
                        "from": old_status or ""
                    })

                if notes and status != "interviewing":
                    job["notes"] = notes

                self.save()
                return True
        return False
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        stats = {
            "total": len(self.tracked_jobs),
            "saved": len([j for j in self.tracked_jobs if j["status"] == "saved"]),
            "applied": len([j for j in self.tracked_jobs if j["status"] == "applied"]),
            "interviewing": len([j for j in self.tracked_jobs if j["status"] == "interviewing"]),
            "rejected": len([j for j in self.tracked_jobs if j["status"] == "rejected"]),
            "offer": len([j for j in self.tracked_jobs if j["status"] == "offer"]),
            "avg_match_score": 0
        }
        
        if self.tracked_jobs:
            scores = [j.get("match_score", 0) for j in self.tracked_jobs]
            stats["avg_match_score"] = round(sum(scores) / len(scores))
        
        return stats
    
    def undo_last_status(self, job_id: str) -> bool:
        """删除最后一条 status_history 记录，并把 status 回退到上一条。"""
        job = self.get_job(job_id)
        if not job:
            return False
        history = job.get("status_history") or []
        if len(history) < 2:
            return False
        history.pop()  # 删除最后一条
        # 回退到倒数第二条的状态
        prev = history[-1]
        prev_status = prev["status"]
        job["status"] = prev_status.split("_")[0] if "interviewing" in prev_status else prev_status
        job["last_updated"] = prev["timestamp"]
        self.save()
        return True

    def delete_interview(self, job_id: str, round_num: int) -> bool:
        """删除指定轮次的面试记录。"""
        job = self.get_job(job_id)
        if not job:
            return False
        interviews = job.get("interviews") or []
        before = len(interviews)
        job["interviews"] = [iv for iv in interviews if iv.get("round") != round_num]
        if len(job["interviews"]) == before:
            return False
        # 如果所有面试记录都删除了，且当前状态是 interviewing，回退到 applied
        if not job["interviews"] and job["status"] == "interviewing":
            job["status"] = "applied"
            job["last_updated"] = datetime.datetime.now().isoformat()
        self.save()
        return True

    def get_job(self, job_id: str) -> Optional[Dict]:
        """获取单个职位"""
        for job in self.tracked_jobs:
            if job["id"] == job_id:
                return job
        return None
    
    def _resume_path(self, job_id: str) -> str:
        """简历文件路径"""
        base = os.path.dirname(self.jobs_file)
        resume_dir = os.path.join(base, "resumes")
        os.makedirs(resume_dir, exist_ok=True)
        return os.path.join(resume_dir, f"{job_id}.pdf")

    # ---- 简历库管理 ----

    def _resume_dir(self) -> str:
        base = os.path.dirname(self.jobs_file)
        d = os.path.join(base, "resumes")
        os.makedirs(d, exist_ok=True)
        return d

    def _resume_idx_path(self) -> str:
        return os.path.join(self._resume_dir(), "resume_index.json")

    def _load_resume_index(self) -> list:
        path = self._resume_idx_path()
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return []

    def _save_resume_index(self, idx: list):
        with open(self._resume_idx_path(), "w") as f:
            json.dump(idx, f, ensure_ascii=False, indent=2)

    def list_resumes(self) -> list:
        """列出简历库所有简历"""
        return self._load_resume_index()

    def add_resume(self, name: str, data: bytes) -> dict:
        """上传简历到简历库，返回简历信息"""
        import uuid
        idx = self._load_resume_index()
        rid = uuid.uuid4().hex[:12]
        now = datetime.datetime.now().isoformat()
        entry = {"id": rid, "name": name, "filename": f"{rid}.pdf", "created_at": now}
        path = os.path.join(self._resume_dir(), entry["filename"])
        with open(path, "wb") as f:
            f.write(data)
        idx.append(entry)
        self._save_resume_index(idx)
        return entry

    def get_resume(self, resume_id: str) -> Optional[bytes]:
        """读取简历库中的简历文件"""
        idx = self._load_resume_index()
        for r in idx:
            if r["id"] == resume_id:
                path = os.path.join(self._resume_dir(), r["filename"])
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        return f.read()
        return None

    def get_resume_info(self, resume_id: str) -> Optional[dict]:
        """获取简历信息"""
        idx = self._load_resume_index()
        for r in idx:
            if r["id"] == resume_id:
                return r
        return None

    def delete_resume(self, resume_id: str) -> bool:
        """从简历库删除简历"""
        idx = self._load_resume_index()
        for i, r in enumerate(idx):
            if r["id"] == resume_id:
                path = os.path.join(self._resume_dir(), r["filename"])
                if os.path.exists(path):
                    os.remove(path)
                del idx[i]
                self._save_resume_index(idx)
                # 清理职位中对这个简历的引用
                for job in self.tracked_jobs:
                    if job.get("resume_id") == resume_id:
                        job.pop("resume_id", None)
                        job.pop("resume_name", None)
                        job.pop("job_resume_file", None)
                        job.pop("has_edited_resume", None)
                        # 删除职位副本目录
                        job_dir = os.path.join(self._resume_dir(), f"job_{job['id']}")
                        if os.path.exists(job_dir):
                            import shutil
                            shutil.rmtree(job_dir, ignore_errors=True)
                self.save()
                return True
        return False

    def delete_job_resume(self, job_id: str) -> bool:
        """删除职位关联的简历副本，保留简历库原始文件"""
        for job in self.tracked_jobs:
            if job["id"] == job_id:
                # 删除职位副本目录
                job_dir = os.path.join(self._resume_dir(), f"job_{job['id']}")
                if os.path.exists(job_dir):
                    import shutil
                    shutil.rmtree(job_dir, ignore_errors=True)
                # 清空引用
                job.pop("resume_id", None)
                job.pop("resume_name", None)
                job.pop("job_resume_file", None)
                job.pop("has_edited_resume", None)
                self.save()
                return True
        return False

    def delete_job(self, job_id: str) -> bool:
        """删除跟踪的职位（不删简历库，只清引用）"""
        for i, job in enumerate(self.tracked_jobs):
            if job["id"] == job_id:
                del self.tracked_jobs[i]
                self.save()
                return True
        return False

    def assign_resume(self, job_id: str, resume_id: str) -> bool:
        """给职位关联简历（从简历库复制副本到职位专属目录）"""
        info = self.get_resume_info(resume_id)
        if not info:
            return False
        for job in self.tracked_jobs:
            if job["id"] == job_id:
                job["resume_id"] = resume_id
                job["resume_name"] = info["name"]
                # 从简历库复制 PDF 到职位专属副本
                src = self.get_resume(resume_id)
                if src:
                    job_dir = os.path.join(self._resume_dir(), f"job_{job_id}")
                    os.makedirs(job_dir, exist_ok=True)
                    dest_filename = f"{resume_id}.pdf"
                    dest_path = os.path.join(job_dir, dest_filename)
                    with open(dest_path, "wb") as f:
                        f.write(src)
                    job["job_resume_file"] = job_dir
                self.save()
                return True
        return False

    def get_job_resume(self, job_id: str) -> Optional[bytes]:
        """读取职位专属简历副本"""
        for job in self.tracked_jobs:
            if job["id"] == job_id and job.get("resume_id"):
                job_dir = os.path.join(self._resume_dir(), f"job_{job_id}")
                filename = f"{job['resume_id']}.pdf"
                path = os.path.join(job_dir, filename)
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        return f.read()
                # 回退到简历库
                return self.get_resume(job["resume_id"])
        return None

    def save_job_resume_text(self, job_id: str, html: str) -> bool:
        """保存职位的简历 HTML 版本（不修改原始 PDF）"""
        for job in self.tracked_jobs:
            if job["id"] == job_id and job.get("resume_id"):
                job_dir = os.path.join(self._resume_dir(), f"job_{job_id}")
                os.makedirs(job_dir, exist_ok=True)
                path = os.path.join(job_dir, "resume.html")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(html)
                job["has_edited_resume"] = True
                self.save()
                return True
        return False

    def get_job_resume_html(self, job_id: str) -> Optional[str]:
        """读取职位的简历 HTML（编辑后的版本）"""
        for job in self.tracked_jobs:
            if job["id"] == job_id and job.get("resume_id"):
                job_dir = os.path.join(self._resume_dir(), f"job_{job_id}")
                path = os.path.join(job_dir, "resume.html")
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        return f.read()
        return None

    def _pdf_to_markdown(self, data: bytes) -> str:
        """将 PDF 二进制数据转换为 Markdown 格式"""
        if not data:
            return ""
        try:
            from io import BytesIO
            from pdfminer.high_level import extract_text
            text = extract_text(BytesIO(data))
        except Exception as e:
            return f"[PDF 解析失败: {e}]"

        import re
        lines = text.split("\n")
        md_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                # 空行 — 段落分隔
                if md_lines and md_lines[-1] != "":
                    md_lines.append("")
                i += 1
                continue

            # 检测标题：短行且不以句号标点结尾
            is_heading = (
                len(line) < 60
                and not line.endswith(('.', '。', '!', '！', '?', '？', ':', '：', ',', '，'))
                and not re.match(r'^[\d\s\-•*]+$', line)  # 纯列表标记
                and len(line) > 1
            )

            # URL 行
            if re.match(r'^https?://', line):
                md_lines.append(f"<{line}>")
                i += 1
                continue

            # 检查是否是列表项（以 • 或 - 或数字开头）
            list_match = re.match(r'^(•|\*|-|\d+\.)\s*(.*)', line)
            if list_match:
                prefix = list_match.group(1)
                content = list_match.group(2)
                # 简单转换为 markdown 列表
                if prefix.isdigit():  # 有序列表
                    md_lines.append(f"1. {content}")
                else:
                    md_lines.append(f"- {content}")
                i += 1
                continue

            if is_heading:
                md_lines.append(f"## {line}")
            else:
                md_lines.append(line)
            i += 1

        # 合并多行为段落
        result = []
        para = []
        for line in md_lines:
            if line == "":
                if para:
                    result.append(" ".join(para))
                    para = []
                result.append("")
            elif line.startswith("## ") or line.startswith("- ") or line.startswith("1. "):
                if para:
                    result.append(" ".join(para))
                    para = []
                result.append(line)
            else:
                para.append(line)
        if para:
            result.append(" ".join(para))

        markdown = "\n".join(result)
        return markdown

    def get_job_resume_markdown(self, job_id: str) -> Optional[str]:
        """读取职位的简历 Markdown（编辑后的版本）"""
        for job in self.tracked_jobs:
            if job["id"] == job_id and job.get("resume_id"):
                job_dir = os.path.join(self._resume_dir(), f"job_{job_id}")
                path = os.path.join(job_dir, "resume.md")
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        return f.read()
                # 没有编辑版，从 PDF 转换
                data = self.get_job_resume(job_id)
                if data:
                    return self._pdf_to_markdown(data)
        return None

    def save_job_resume_markdown(self, job_id: str, markdown: str) -> bool:
        """保存职位的简历 Markdown 版本（不修改原始 PDF）"""
        for job in self.tracked_jobs:
            if job["id"] == job_id and job.get("resume_id"):
                job_dir = os.path.join(self._resume_dir(), f"job_{job_id}")
                os.makedirs(job_dir, exist_ok=True)
                path = os.path.join(job_dir, "resume.md")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(markdown)
                job["has_edited_resume"] = True
                self.save()
                return True
        return False

    def markdown_to_html(self, markdown: str) -> str:
        """将 Markdown 渲染为 HTML"""
        if not markdown:
            return "<p style='color:#888'>暂无内容</p>"
        try:
            import markdown as md
            import re
            # 预处理：URL 自动转链接
            markdown = re.sub(
                r'(?<!\()(https?://[^\s<)>"]+)',
                r'<\1>',
                markdown
            )
            html = md.markdown(
                markdown,
                extensions=['extra', 'smarty']
            )
            return html
        except Exception as e:
            return f"<p style='color:#d32f2f'>渲染失败: {e}</p><pre>{markdown}</pre>"

    def resume_to_pdf_bytes(self, markdown: str, title: str = "简历") -> Optional[bytes]:
        """将 Markdown 转换为 PDF 字节"""
        try:
            html_content = self.markdown_to_html(markdown)
            full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.7; font-size: 12pt; color: #222; }}
h1 {{ font-size: 20pt; margin-top: 24px; }}
h2 {{ font-size: 16pt; margin-top: 20px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }}
h3 {{ font-size: 14pt; margin-top: 16px; }}
p {{ margin: 8px 0; }}
ul, ol {{ margin: 8px 0; padding-left: 24px; }}
li {{ margin: 4px 0; }}
a {{ color: #1a73e8; }}
strong {{ font-weight: 600; }}
code {{ background: #f5f5f5; padding: 1px 4px; border-radius: 3px; font-size: 11pt; }}
pre {{ background: #f5f5f5; padding: 12px; border-radius: 6px; overflow-x: auto; }}
</style>
</head>
<body>
{html_content}
</body>
</html>"""
            from weasyprint import HTML as WeasyHTML
            pdf_bytes = WeasyHTML(string=full_html).write_pdf()
            return pdf_bytes
        except Exception as e:
            print(f"PDF 生成失败: {e}")
            return None

    def _pdf_bytes_to_html(self, data: bytes) -> str:
        """将 PDF 二进制数据转换为 HTML"""
        if not data:
            return "<p style='color:#888'>简历文件未找到</p>"
        try:
            from io import BytesIO
            from pdfminer.high_level import extract_text
            text = extract_text(BytesIO(data))
        except Exception as e:
            return f"<p style='color:#d32f2f'>PDF 解析失败: {e}</p>"
        # 简单格式化：空行分段，URL 加链接
        import re
        paragraphs = []
        for block in text.split("\n\n"):
            block = block.strip()
            if not block:
                continue
            lines = []
            for line in block.split("\n"):
                line = line.strip()
                if not line:
                    continue
                # URL -> 链接
                line = re.sub(
                    r'(https?://[^\s]+)',
                    r'<a href="\1" target="_blank">\1</a>',
                    line
                )
                if len(line) < 50 and not line.endswith(('.', '。', '!', '！', '?', '？')):
                    lines.append(f"<strong>{line}</strong>")
                else:
                    lines.append(line)
            paragraphs.append("<p>" + "<br>".join(lines) + "</p>")
        html = "\n".join(paragraphs)
        if not html:
            html = f"<pre>{re.escape(text)}</pre>"
        return html

    def convert_resume_to_html_given_data(self, data: bytes, label: str = "") -> str:
        """将 PDF 二进制数据转换为 HTML（不查简历库）"""
        return self._pdf_bytes_to_html(data)

    def convert_resume_to_html(self, resume_id: str) -> str:
        """将简历 PDF 转换为 HTML 格式，返回 HTML 字符串"""
        data = self.get_resume(resume_id)
        return self._pdf_bytes_to_html(data)

# ============================================================
# Agent 主类
# ============================================================

class JobAgent:
    """
    求职Agent主类
    整合搜索、分析、跟踪功能
    """
    
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or Config.DATA_DIR
        
        # 初始化各模块
        self.profile = UserProfile(os.path.join(self.data_dir, "user_profile.json"))
        self.engine = JobSearchEngine(self.profile)
        self.analyzer = JobAnalyzer(self.profile)
        self.tracker = JobTracker(os.path.join(self.data_dir, "tracked_jobs.json"))
        self.apply_manager = ApplyManager(self.data_dir)
        
        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)
    
    def run_search(self, sources: List[str] = None, keywords: List[str] = None, location: str = None) -> Dict:
        """执行完整搜索和分析，可指定来源/关键词/地点"""
        print(f"Agent: 开始搜索 (来源: {sources or '全部'})...")
        results = self.engine.search_all(sources=sources, keywords=keywords, location=location)
        
        print(f"Agent: 找到 {results['stats']['total_jobs']} 个职位")
        analyzed = self.analyzer.analyze_all(results)
        print(f"Agent: 分析完成 - 高匹配: {analyzed['stats']['high_match']}")
        
        # 保存历史
        self._save_search_history(analyzed)
        
        return analyzed
    
    def save_job(self, job: Dict) -> bool:
        """保存职位到跟踪列表"""
        return self.tracker.add_job(job)
    
    def fetch_job_from_url(self, url: str, keep_html: bool = False) -> Dict:
        """通过URL抓取并解析职位信息，返回 {title, company, location, description, job_type}
        
        Uses a plugin-style site adapter system. Each site has its own extractor
        in sites/<name>.py. Falls back to generic extraction for unrecognized URLs.
        
        For LinkedIn, uses Playwright (headless Chromium) because LinkedIn blocks
        curl/requests-based fetchers with CAPTCHA.
        
        keep_html=True: 保留描述中的HTML格式标签（用于保存等场景）
        """
        result = {"title": "", "company": "", "location": "", "description": "", "job_type": "", "url": url}

        # LinkedIn requires Playwright (headless browser) — curl gets CAPTCHA'd
        if 'linkedin.com/jobs' in url.lower():
            # Strip tracking params — LinkedIn redirects to login with them
            clean_url = re.sub(r'\?.*', '', url).rstrip('/') + '/'
            html = self._fetch_linkedin_with_playwright(clean_url)
            if not html:
                return result
        else:
            try:
                from curl_cffi import requests
                resp = requests.get(url, impersonate='chrome120', timeout=20)
            except:
                try:
                    resp = requests.get(url, timeout=20)
                except Exception as e:
                    return result

            if resp.status_code != 200:
                return result
            html = resp.text


        # Route to site-specific adapter if available
        from sites.registry import get_adapter
        adapter = get_adapter(url)
        if adapter is not None:
            extracted = adapter(html, url)
            result.update(extracted)
            # Only clean HTML for display/search; keep raw for save
            if result['description'] and not keep_html:
                try:
                    result['description'] = self.engine._clean_html(
                        '<div>' + result['description'] + '</div>'
                    )
                except:
                    pass
            return result

        # No specific adapter — use generic fallback
        from sites.generic import extract
        extracted = extract(html, url)
        result.update(extracted)
        if result['description']:
            try:
                result['description'] = self.engine._clean_html(
                    '<div>' + result['description'] + '</div>'
                )
            except:
                pass
        return result

    @staticmethod
    def _fetch_linkedin_with_playwright(url: str) -> str:
        """使用 Playwright 渲染 LinkedIn 职位页面，返回 HTML。"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("playwright not installed, cannot fetch LinkedIn jobs")
            return ""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-blink-features=AutomationControlled'],
                )
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                )
                context.add_init_script(
                    """Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"""
                )
                page = context.new_page()
                page.goto(url, wait_until='domcontentloaded', timeout=20000)
                page.wait_for_timeout(3000)  # Let LinkedIn render
                html = page.content()
                browser.close()
                return html
        except Exception as e:
            logger.warning(f"Playwright fetch failed for {url}: {e}")
            return ""

    def _extract_jsonld_company(self, jd: dict) -> str:
        """从JSON-LD提取公司名"""
        for key in ('hiringOrganization', 'employer', 'organization'):
            org = jd.get(key, {})
            if isinstance(org, dict):
                name = org.get('name', '')
                if name:
                    return name
        return ''

    def _extract_jsonld_location(self, jd: dict) -> str:
        """从JSON-LD提取地点"""
        loc = jd.get('jobLocation', {})
        if not isinstance(loc, dict):
            loc = jd.get('location', loc)
        if isinstance(loc, dict):
            if '@type' in loc:
                city = loc.get('address', {}).get('addressLocality', '')
                region = loc.get('address', {}).get('addressRegion', '')
                country = loc.get('address', {}).get('addressCountry', '')
                if isinstance(country, dict):
                    country = country.get('name', '')
                parts = [p for p in [city, region, country] if p]
                return ', '.join(parts)
        return loc.get('name', '') if isinstance(loc, dict) else str(loc)

    def _extract_body_description(self, html: str) -> str:
        """从页面body中提取较长的文本块作为职位描述"""
        import re
        # Remove all script/style
        cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html, 0, re.DOTALL)
        cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, 0, re.DOTALL)
        # Find large text blocks
        blocks = re.findall(r'>([^<]{300,})<', cleaned)
        if not blocks:
            return ''
        # Pick the longest
        blocks.sort(key=len, reverse=True)
        best = blocks[0]
        # Skip if looks like nav/footer boilerplate
        best = best.strip()
        if len(best) < 200:
            return ''
        return self.engine._clean_html(f'<div>{best}</div>')

    def _extract_from_script_tags(self, html: str) -> str:
        """Extract job description from script tags with u-escaped HTML
        (SPA sites like Google Careers store content in compiled JS bundles)."""
        import re
        bs = chr(92)  # backslash
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        candidates = []

        for s in scripts:
            if len(s) < 200:
                continue
            # Look for escaped unicode HTML patterns in the raw script content
            has_escaped = (bs + 'u003c') in s or (bs + 'u003e') in s
            has_keywords = 'qualification' in s.lower() or 'responsibilit' in s.lower()
            if not has_escaped and not has_keywords:
                continue

            # Decode unicode escape sequences
            if has_escaped:
                decoded = s.replace(bs + 'u003c', '<').replace(bs + 'u003e', '>')
                decoded = decoded.replace(bs + 'u003d', '=').replace(bs + 'u0026', '&')
                decoded = decoded.replace(bs + 'u0027', "'").replace(bs + 'u0022', '"')
                decoded = decoded.replace(bs + 'u002f', '/')
            else:
                decoded = s

            # Build a structured description by pairing headings with <ul> sections
            parts = []
            # Build structured description by scanning decoded HTML sequentially
            # This handles both heading+<ul> pairs and headingless <ul> sections
            parts = []
            # Find all heading+ul pairs AND lone uls in document order
            seen_headings = set()
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

            # Deduplicate: remove consecutive duplicate sections
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
                candidates.append(chr(10).join(parts))
                continue

            # Fallback: plain text
            text = re.sub(r'<[^>]+>', ' ', decoded)
            text = text.replace(bs + 'n', chr(10))
            text = re.sub(r'\s+', ' ', text).strip()
            if len(text) > 300:
                candidates.append(text)

        if not candidates:
            return ''

        candidates.sort(key=len, reverse=True)
        best = candidates[0]
        if len(best) < 200:
            return ''

        for marker in ['Responsibilities', 'Minimum qualifications', 'Preferred qualifications', 'About the job']:
            idx = best.find(marker)
            if idx >= 0:
                best = best[idx:]
                break

        return best

    def generate_cover_letter(self, job: Dict) -> str:
        """generate cover letter"""
        return self.analyzer.generate_cover_letter(job)
    def generate_cover_letter(self, job: Dict) -> str:
        """生成求职信"""
        return self.analyzer.generate_cover_letter(job)
    
    def get_dashboard_data(self) -> Dict:
        """获取仪表盘数据"""
        search_history = self._get_search_history()
        
        return {
            "profile": self.profile.profile,
            "tracker_stats": self.tracker.get_stats(),
            "recent_searches": search_history[-5:] if search_history else [],
            "current_time": datetime.datetime.now().isoformat()
        }
    
    def update_profile(self, updates: Dict):
        """更新用户画像"""
        self.profile.update_profile(updates)
    
    def update_job_status(self, job_id: str, status: str, notes: str = ""):
        """更新职位状态"""
        return self.tracker.update_status(job_id, status, notes)
    
    def delete_job(self, job_id: str) -> bool:
        """删除跟踪的职位"""
        return self.tracker.delete_job(job_id)
    
    def rerun_analysis(self, job_id: str) -> Optional[Dict]:
        """根据关联的简历 Markdown 重新计算匹配度"
        
        Args:
            job_id: 职位 ID
            
        Returns:
            更新后的 job dict，若无关联简历或无职位返回 None
        """
        import re
        
        # 找到职位
        job = None
        for j in self.tracker.tracked_jobs:
            if j["id"] == job_id:
                job = j
                break
        if not job:
            return None
        
        # 获取简历 Markdown
        resume_md = self.tracker.get_job_resume_markdown(job_id)
        if not resume_md:
            return None
        
        # 计算简历与职位的匹配度：
        # 遍历 profile 技能类别，检查简历中哪些技能在职位要求中存在（交集）
        resume_lower = resume_md.lower()
        job_title_desc = (job.get("title", "") + " " + job.get("description", "")).lower()
        skills = self.profile.profile.get("skills", {})
        
        total_weight = 0
        matched_weight = 0
        matched_skills = []
        
        for category, info in skills.items():
            weight = JobAnalyzer._get_category_weight_static(category)
            total_weight += weight
            
            # 先看职位描述了哪些技能
            job_has_skill = False
            job_skill_keyword = ""
            for keyword in info.get("keywords", []):
                kw_lower = keyword.lower()
                if kw_lower in job_title_desc:
                    job_has_skill = True
                    job_skill_keyword = keyword
                    break
                parts = kw_lower.split()
                if len(parts) > 1 and any(p in job_title_desc for p in parts):
                    job_has_skill = True
                    job_skill_keyword = keyword
                    break
            
            # 职位要求了该技能，再检查简历是否有
            if job_has_skill:
                # 检查简历是否包含该技能
                resume_has = False
                partial_match = False
                for keyword in info.get("keywords", []):
                    kw_lower = keyword.lower()
                    if kw_lower in resume_lower:
                        resume_has = True
                        break
                    parts = kw_lower.split()
                    if len(parts) > 1 and any(p in resume_lower for p in parts):
                        partial_match = True
                        break
                
                if resume_has:
                    matched_skills.append({
                        "category": category,
                        "keyword": job_skill_keyword,
                        "from": "resume",
                        "level": info.get("level", "intermediate"),
                        "score": JobAnalyzer._skill_match_score_static(info.get("level", "intermediate"))
                    })
                    matched_weight += weight
                elif partial_match:
                    matched_skills.append({
                        "category": category,
                        "keyword": job_skill_keyword,
                        "from": "resume",
                        "partial": True,
                        "level": info.get("level", "intermediate"),
                        "score": JobAnalyzer._skill_match_score_static(info.get("level", "intermediate")) * 0.5
                    })
                    matched_weight += weight * 0.5
        
        match_score = round((matched_weight / total_weight) * 100) if total_weight > 0 else 0
        
        # 更新职位的 match_score
        job["match_score"] = match_score
        job["match_details"] = {
            "skill_match": matched_skills,
            "matched_skills_count": len(matched_skills),
            "source": "resume_rerun"
        }
        # 标记已根据简历重新匹配
        job["resume_rerun"] = True
        self.tracker.save()
        
        return job

    def _save_search_history(self, result: Dict):
        """保存搜索历史""" 
        history_file = os.path.join(self.data_dir, "search_history.json")
        history = []
        
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except:
                pass
        
        # 只保存摘要
        summary = {
            "time": result["stats"]["search_time"],
            "search_id": result["stats"]["search_id"],
            "total_jobs": result["stats"]["total_jobs"],
            "high_match": result["stats"]["high_match"],
            "medium_match": result["stats"]["medium_match"],
            "avg_score": result["stats"]["avg_match_score"]
        }
        
        history.append(summary)
        
        # 最多保存20条
        if len(history) > 20:
            history = history[-20:]
        
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def _get_search_history(self) -> List[Dict]:
        """获取搜索历史"""
        history_file = os.path.join(self.data_dir, "search_history.json")
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return []


# ============================================================
# 主程序入口
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 求职Agent 核心模块")
    print("=" * 60)
    print()
    
    agent = JobAgent()
    
    print("Agent 已初始化")
    print(f"技能: {', '.join(agent.profile.get_skill_keywords()[:5])}")
    print(f"已跟踪职位: {agent.tracker.get_stats()['total']}")
    print()
    
    # 执行一次搜索测试
    print("执行搜索测试...")
    results = agent.run_search()
    
    print(f"\n搜索完成!")
    print(f"  职位: {results['stats']['total_jobs']}")
    print(f"  搜索链接: {len(results['search_links'])}")
    print(f"  高匹配: {results['stats']['high_match']}")
    print(f"  平均匹配度: {results['stats']['avg_match_score']}%")