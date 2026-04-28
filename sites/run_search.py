#!/usr/bin/env python3
"""
命令行职位搜索工具

用法:
  python sites/run_search.py --site indeed,remoteok --keywords "Cloud AI Linux" --location Toronto --max 5
  python sites/run_search.py --site all --keywords "ML Engineer" --location "Remote Canada"
  python sites/run_search.py --site remoteok --keywords Python --max 10
  python sites/run_search.py --list-sites

选项:
  --site, -s        搜索源，多个用逗号分隔 (all / indeed / remoteok / github / 站点名...)
  --keywords, -k    搜索关键词 (默认从 user_profile 读取)
  --location, -l    职位地点 (默认从 user_profile 读取)
  --max, -m         每个源最多返回结果数 (默认 8)
  --list-sites      列出可用搜索源
  --json            输出 JSON 格式
"""

import argparse
import json
import sys
import os

# 确保能找到 job_agent_core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def list_available_sites(engine=None):
    """列出所有可用搜索源"""
    sites = {
        "indeed": "sites.indeed.search",
        "remoteok": "job_agent_core.JobSearchEngine.search_remoteok (via HTTP)",
        "github": "job_agent_core.JobSearchEngine.search_github_jobs",
        "linkedin": "sites.linkedin_search.search",
        "googlejobs": "sites.google_jobs.search",
        "google": "sites.google_jobs.search",
        "weworkremotely": "sites.weworkremotely.search",
        "wwr": "sites.weworkremotely.search",
        "canonical": "sites.canonical.search",
        "redhat": "sites.redhat.search",
    }
    if engine:
        # 从 search_all 的 source_map 获取实际注册的源
        try:
            src_map = {
                "GitHub Jobs": engine.search_github_jobs,
                "RemoteOK": engine.search_remoteok,
                "Indeed": engine.search_indeed,
            }
            print("\n注册的搜索源:")
            for name, fn in src_map.items():
                status = "✓" if fn else "✗"
                mod = getattr(fn, "__module__", "?") if fn else "?"
                print(f"  {status} {name}  ({mod})")
        except Exception as e:
            print(f"  (无法加载: {e})")

    print("\n可用的 --site 值:")
    for name, desc in sites.items():
        print(f"  {name:15s} {desc}")
    print("  all                 所有源")
    print()
    print("示例:")
    print("  python sites/run_search.py --site remoteok --keywords Python")
    print("  python sites/run_search.py --site all --keywords \"Cloud AI\" --location Toronto")
    return sites


def run_search(sites, keywords, location, max_results, output_json=False):
    """执行搜索并打印结果"""
    from job_agent_core import JobAgent

    agent = JobAgent()
    engine = agent.engine
    profile = agent.profile

    # 处理站点参数
    if not sites or "all" in sites:
        sources = None  # search_all 默认走所有源
    else:
        # 做名称映射
        name_map = {
            "indeed": "Indeed",
            "remoteok": "RemoteOK",
            "github": "GitHub Jobs",
            "linkedin": "LinkedIn",
            "googlejobs": "GoogleJobs",
            "google": "GoogleJobs",
            "weworkremotely": "WeWorkRemotely",
            "wwr": "WeWorkRemotely",
            "canonical": "Canonical",
            "redhat": "RedHat",
            "suse": "SUSE",
            "nvidia": "NVIDIA",
        }
        sources = []
        for s in sites:
            mapped = name_map.get(s.strip().lower(), s.strip())
            sources.append(mapped)
        # 检查是否有非法源
        valid = {"Indeed", "RemoteOK", "GitHub Jobs", "LinkedIn", "GoogleJobs", "WeWorkRemotely", "Canonical", "RedHat", "SUSE", "NVIDIA"}
        unknown = [s for s in sources if s not in valid]
        if unknown:
            print(f"⚠ 未知搜索源: {unknown}")
            print(f"  可用: {', '.join(sorted(valid))}")
            return

    if not keywords:
        keywords = profile.get_skill_keywords()[:3]
    if not location:
        location = profile.profile.get("preferred_locations", ["Canada"])[0]

    print(f"🔍 搜索: {', '.join(keywords)}")
    print(f"📍 地点: {location}")
    print(f"📡 源:   {', '.join(sources) if sources else '全部'}")
    print(f"📊 每源: {max_results} 条")
    print()

    results = engine.search_all(
        max_per_source=max_results,
        sources=sources,
        keywords=keywords,
        location=location,
    )

    all_jobs = results.get("jobs", [])
    links = results.get("links", [])

    if links:
        print(f"🔗 搜索链接 ({len(links)}):")
        for link in links:
            print(f"   {link}")
        print()

    if not all_jobs:
        print("⚠ 未找到任何职位")
        return

    if output_json:
        print(json.dumps(all_jobs, ensure_ascii=False, indent=2))
        return

    print(f"✅ 找到 {len(all_jobs)} 个职位:\n")
    for i, job in enumerate(all_jobs, 1):
        title = job.get("title", "N/A")
        company = job.get("company", "N/A")
        location_j = job.get("location", "N/A")
        source = job.get("source", "?")
        job_type = job.get("job_type", "")
        score = job.get("match_score", "")
        score_str = f" [匹配度: {score}%]" if score else ""
        url = job.get("url", "")

        print(f"  {i:2d}. [{source:10s}] {title}")
        print(f"      {company:25s} {location_j}")
        if job_type:
            print(f"      {job_type}")
        if score:
            print(f"      匹配度: {score}%")
        if url:
            print(f"      {url}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="🔍 职位搜索工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--site", "-s", default="all",
                        help="搜索源，多个用逗号分隔 (indeed,remoteok,github / all)")
    parser.add_argument("--keywords", "-k", default="",
                        help="搜索关键词 (默认从 user_profile 读取)")
    parser.add_argument("--location", "-l", default="",
                        help="职位地点 (默认从 user_profile 读取)")
    parser.add_argument("--max", "-m", type=int, default=8,
                        help="每个源最多返回结果数 (默认 8)")
    parser.add_argument("--json", action="store_true",
                        help="JSON 格式输出")
    parser.add_argument("--list-sites", action="store_true",
                        help="列出可用搜索源")
    parser.add_argument("--raw", action="store_true",
                        help="直接使用 sites.xxx.search 而非通过 engine")
    args = parser.parse_args()

    if args.list_sites:
        list_available_sites()
        return

    sites = [s.strip() for s in args.site.split(",")] if args.site else ["all"]
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()] if args.keywords else []
    location = args.location or ""

    run_search(sites, keywords, location, args.max, output_json=args.json)


if __name__ == "__main__":
    main()
