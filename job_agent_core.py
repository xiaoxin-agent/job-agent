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
    
    def search_github_jobs(self, keywords: List[str], location: str, max_results: int = 5) -> List[Dict]:
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
                    desc = (job.get("description", "") + " " + job.get("title", "")).lower()
                    if any(kw.lower() in desc for kw in keywords):
                        jobs.append(self._format_job({
                            "title": job.get("title", ""),
                            "company": job.get("company", ""),
                            "location": job.get("location", ""),
                            "description": self._clean_html(job.get("description", ""))[:300],
                            "url": job.get("url", ""),
                            "date": job.get("created_at", ""),
                            "source": "GitHub Jobs"
                        }))
                        if len(jobs) >= max_results:
                            break
        except Exception as e:
            print(f"GitHub Jobs 搜索失败: {e}")
        
        return jobs
    
    def search_indeed(self, location: str, max_results: int = 5) -> List[Dict]:
        """从Indeed搜索职位（curl_cffi模拟浏览器Chrome指纹）"""
        jobs = []
        keywords = self.profile.get_skill_keywords()[:3]
        
        try:
            from curl_cffi import requests
            from urllib.parse import quote
            
            kw = quote(" ".join(keywords[:2]))
            loc = quote(location)
            
            urls = [
                f"https://ca.indeed.com/jobs?q={kw}&l={loc}",
                f"https://www.indeed.com/jobs?q={kw}&l={loc}",
            ]
            
            for url in urls:
                if len(jobs) >= max_results:
                    break
                print(f"搜索Indeed: {url}")
                
                resp = requests.get(url, impersonate='chrome120', timeout=20)
                if resp.status_code != 200:
                    print(f"Indeed返回状态码: {resp.status_code}")
                    continue
                
                html = resp.text
                
                # 步骤1: 提取所有公司名（data-testid="company-name"）
                companies = []
                for m in re.finditer(r'data-testid="company-name"[^>]*>(.*?)<', html, re.DOTALL):
                    txt = self._clean_html(m.group(1)).strip()
                    if txt:
                        companies.append(txt)
                
                if not companies:
                    print("Indeed: 未找到公司名")
                    continue
                
                # 步骤2: 从aria-label提取标题（格式: "full details of JOB TITLE"）
                titles = re.findall(r'aria-label="full details of ([^"]+)"', html)
                
                # 步骤3: 提取地点
                locs = []
                for m in re.finditer(r'data-testid="text-location"[^>]*>(.*?)<', html, re.DOTALL):
                    txt = self._clean_html(m.group(1)).strip()
                    if txt:
                        locs.append(txt)
                
                # 步骤4: 提取data-jk构造链接
                jks = re.findall(r'data-jk="([^"]+)"', html)
                
                # 步骤5: 组装卡片（按公司数对齐）
                n = min(len(companies), len(titles), len(jks), max_results)
                if n == 0:
                    print(f"Indeed: 解析失败 companies={len(companies)} titles={len(titles)} jks={len(jks)}")
                    continue
                
                for i in range(n):
                    job_url = f"https://ca.indeed.com/viewjob?jk={jks[i]}"
                    desc = f"From Indeed - {' '.join(keywords[:2])} in {location}"
                    # 尝试抓详情页（逐个抓，超时30秒总体）
                    try:
                        detail = self.fetch_indeed_job_details(job_url)
                        if detail:
                            desc = detail
                    except:
                        pass
                    jobs.append(self._format_job({
                        "title": titles[i] if i < len(titles) else companies[i],
                        "company": companies[i],
                        "location": locs[i] if i < len(locs) else location,
                        "description": desc,
                        "url": job_url,
                        "date": "",
                        "source": "Indeed"
                    }))
                
                if jobs:
                    break
        except ImportError:
            print("Indeed搜索需要curl_cffi库: pip install curl_cffi")
        except Exception as e:
            print(f"Indeed 搜索失败: {e}")
        
        return jobs
    
    def search_remoteok(self, max_results: int = 5) -> List[Dict]:
        """搜索RemoteOK"""
        jobs = []
        
        try:
            import requests
            
            url = "https://remoteok.io/api"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 1:
                    skills = self.profile.get_skill_keywords()
                    for item in data[1:20]:
                        title = item.get("position", "")
                        desc = item.get("description", "")
                        content = (title + " " + desc).lower()
                        
                        if any(s.lower() in content for s in skills):
                            jobs.append(self._format_job({
                                "title": title,
                                "company": item.get("company", ""),
                                "location": "Remote",
                                "description": self._clean_html(desc)[:300],
                                "url": f"https://remoteok.io/remote-jobs/{item.get('slug', '')}",
                                "date": item.get("date", ""),
                                "source": "RemoteOK"
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
    
    def search_all(self, max_per_source: int = 3, sources: List[str] = None, keywords: List[str] = None, location: str = None) -> Dict:
        """多源搜索，可指定来源和关键词/地点"""
        if keywords is None:
            keywords = self.profile.get_skill_keywords()[:3]
        if location is None:
            location = self.profile.profile.get("preferred_locations", ["Canada"])[0]
        
        source_map = {
            "GitHub Jobs": lambda: self.search_github_jobs(keywords, location, max_per_source),
            "RemoteOK": lambda: self.search_remoteok(max_per_source),
            "Indeed": lambda: self.search_indeed(location, max_per_source),
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
    
    def fetch_indeed_job_details(self, url: str) -> str:
        """抓取Indeed职位详情页面获取美化的描述"""
        try:
            from curl_cffi import requests
            resp = requests.get(url, impersonate='chrome120', timeout=15)
            if resp.status_code != 200:
                return ""
            html = resp.text
            
            # 找jobDescriptionText区块
            import re
            for pat in [
                r'id="jobDescriptionText"[^>]*>(.*?)</div>\s*</div>',
                r'id="jobDescriptionText"[^>]*>(.*?)(?:<div[^>]+id=)',
                r'class="[^"]*jobsearch-JobComponent-description[^"]*"[^>]*>(.*?)(?:<div[^>]*class="[^"]*jobsearch)',
            ]:
                m = re.search(pat, html, re.DOTALL)
                if m and len(m.group(1)) > 100:
                    result = self._beautify_description(m.group(1))
                    if len(result) > 100:
                        return result
            # 备选：全文
            result = self._beautify_description(html)
            return result[:3000]
        except:
            return ""
    
    def _format_job(self, raw: Dict) -> Dict:
        """格式化职位数据"""
        return {
            "title": raw.get("title", "Unknown"),
            "company": raw.get("company", "Unknown"),
            "location": raw.get("location", "Unknown"),
            "description": raw.get("description", ""),
            "url": raw.get("url", ""),
            "date": raw.get("date", ""),
            "source": raw.get("source", ""),
            "analyzed": False,
            "match_score": 0,
            "match_details": {},
            "status": "new",
            "saved_at": datetime.datetime.now().isoformat()
        }
    
    def _clean_html(self, text: str) -> str:
        """清理HTML标签"""
        if not text:
            return ""
        text = re.sub(r'<[^>]+>', ' ', text)
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
        text = re.sub(r'\s+', ' ', text).strip()
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
    
    def _get_category_weight(self, category: str) -> float:
        """获取技能类别权重"""
        weights = {
            "Cloud": 25,
            "AI/ML": 25,
            "Linux": 20,
            "Python": 15,
            "C/C++": 10,
            "DevOps": 5
        }
        return weights.get(category, 10)
    
    def _skill_match_score(self, level: str) -> float:
        """获取技能匹配得分"""
        scores = {
            "expert": 1.0,
            "intermediate": 0.7,
            "beginner": 0.4
        }
        return scores.get(level, 0.5)
    
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
        """加载跟踪数据"""
        if os.path.exists(self.jobs_file):
            try:
                with open(self.jobs_file, "r", encoding="utf-8") as f:
                    return json.load(f)
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
        tracked = {
            "id": hashlib.md5(f"{job.get('title')}_{job.get('company')}_{time.time()}".encode()).hexdigest()[:8],
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "url": job.get("url", ""),
            "match_score": job.get("match_score", 0),
            "source": job.get("source", ""),
            "status": "saved",  # saved / applied / interviewing / rejected / offer
            "notes": "",
            "cover_letter": "",
            "applied_date": None,
            "interview_dates": [],
            "follow_up_dates": [],
            "saved_at": datetime.datetime.now().isoformat(),
            "last_updated": datetime.datetime.now().isoformat()
        }
        
        # 去重
        for existing in self.tracked_jobs:
            if existing["title"] == tracked["title"] and existing["company"] == tracked["company"]:
                return False
        
        self.tracked_jobs.insert(0, tracked)
        self.save()
        return True
    
    def update_status(self, job_id: str, status: str, notes: str = ""):
        """更新申请状态"""
        for job in self.tracked_jobs:
            if job["id"] == job_id:
                job["status"] = status
                job["last_updated"] = datetime.datetime.now().isoformat()
                
                if status == "applied" and not job["applied_date"]:
                    job["applied_date"] = datetime.datetime.now().isoformat()
                
                if notes:
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
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """获取单个职位"""
        for job in self.tracked_jobs:
            if job["id"] == job_id:
                return job
        return None

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