#!/usr/bin/env python3
"""
求职Agent - Web界面
美观的浏览器界面，供求职者使用
"""

import json
import socket
import base64
import os
import datetime
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Optional

from job_agent_core import JobAgent
from job_agent_apply import ApplyManager

# ============================================================
# Company logo SVGs (inline, no external requests)
# ============================================================

LOGOS_DIR = os.path.join(os.path.dirname(__file__), 'static', 'logos')


def get_company_logo(company_name: str) -> str:
    """Return an <img> tag or emoji for the company."""
    if not company_name:
        return get_company_emoji(company_name)
    name = company_name.lower().strip()
    # Try exact match first, then substring
    def _read_svg(path):
        with open(path, 'r') as f:
            svg = f.read()
        # Use data URI - replace " with ' and < with %3C, > with %3E
        import urllib.parse
        encoded = urllib.parse.quote(svg, safe='')
        return f'<img src="data:image/svg+xml,{encoded}" style="width:18px;height:18px;vertical-align:middle;margin-right:3px" alt="{company_name}">'
    svg_path = os.path.join(LOGOS_DIR, f'{name}.svg')
    if os.path.exists(svg_path):
        return _read_svg(svg_path)
    for fname in os.listdir(LOGOS_DIR):
        base = fname.replace('.svg', '').lower()
        if base in name:
            return _read_svg(os.path.join(LOGOS_DIR, fname))
    return get_company_emoji(company_name)

# Website-specific company emoji mapping
COMPANY_EMOJIS = {
    'google': '🔍',  # 🔍 (Google = search)
    'amazon': '📦',  # 📦 (package)
    'apple': '❤️',  # ❤️ (love brand)
    'microsoft': '💻',  # 💻 (Windows/pc)
    'meta': '🌍',  # 🌍 (Meta connects the world)
    'linkedin': '💼',  # 💼 (professional networking)
    'indeed': '🔍',  # 🔍 (job search)
    'nvidia': '🧩',  # 🧩 (GPU/tech)
    'ibm': '📊',  # 📊 (enterprise/data)
    'remoteok': '🌎',  # 🌎 (remote work globe)
    'greenhouse': '🌱',  # 🌱 (greenhouse = plant)
    'lever': '⚕',  # ⚕️ (cross/medical)
    'twitter': '🐦',  # 🐦 (Twitter bird)
    'x': '❔',  # ❔ (X = unknown)
    'tesla': '🚘',  # 🚘 (car)
    'netflix': '🎬',  # 🎬 (entertainment)
    'spotify': '🎵',  # 🎵 (music)
    'uber': '🚙',  # 🚙 (ride)
    'airbnb': '🏠',  # 🏠 (home/host)
    'stripe': '💳',  # 💳 (payments)
    'square': '💰',  # 💰 (money)
    'shopify': '🛍',  # 🛍️ (shopping)
    'notion': '📝',  # 📝 (notes)
    'figma': '🎨',  # 🎨 (design)
    'databricks': '📡',  # 📡 (data)
    'datadog': '🐶',  # 🐶 (dog)
    'cloudflare': '☁',  # ☁️ (cloud)
    'dropbox': '📥',  # 📥 (inbox)
    'slack': '💬',  # 💬 (chat)
    'github': '💻',  # 💻 (code)
    'gitlab': '🧱',  # 🧱 (build)
    'docker': '🐳',  # 🐳 (whale)
    'kubernetes': '🚢',  # 🚢 (ship)
    'sentry': '📨',  # 📨 (alert)
    'hashicorp': '🏰',  # 🏰 (castle)
    'mongodb': '🐱',  # 🐱 (cat)
    'redis': '🍌',  # 🍌 (banana)
    'elastic': '🔍',  # 🔍 (search)
    'splunk': '🔎',  # 🔎 (data search)
}


def get_company_emoji(company_name: str) -> str:
    """Return the best-matching emoji for a company name.
    Falls back to 🏢 (Office Building) when no match."""
    if not company_name:
        return '🏢'
    name = company_name.lower().strip()
    for key, emoji in COMPANY_EMOJIS.items():
        if key == name:
            return emoji
    for key, emoji in COMPANY_EMOJIS.items():
        if key in name:
            return emoji
    return '🏢'


def _build_logo_map() -> dict:
    """Build a dict: company_name_lower -> <img data-uri> or emoji fallback."""
    result = {}
    from urllib.parse import quote
    import os as _os
    for key in COMPANY_EMOJIS:
        name = key.lower().strip()
        svg_path = _os.path.join(LOGOS_DIR, f'{name}.svg')
        if _os.path.exists(svg_path):
            with open(svg_path, 'r') as f:
                svg = f.read()
            encoded = quote(svg, safe='')
            result[key] = f'<img src="data:image/svg+xml,{encoded}" style="width:18px;height:18px;vertical-align:middle;margin-right:3px" alt="{key}">'
        else:
            result[key] = get_company_emoji(key)
    return result


PORT = 9999


# ============================================================
# 国际化 (i18n) — 当前支持 en / zh-CN / fr
# ============================================================

LANGUAGES: Dict[str, Dict[str, str]] = {
    "en": {
        # 导航
        "nav_home": "🏠 Home",
        "nav_dashboard": "📊 Dashboard",
        "nav_search": "🔍 Search",
        "nav_tracked": "📋 Tracked",
        "nav_profile": "👤 Profile",
        "nav_resume": "📄 Resumes",
        "nav_letter": "✉️ Cover Letter",
        "nav_learn_calendar": "📅 Learn Plan",
        "resume_title": "Resume Library",
        "resume_upload": "Upload Resume",
        "resume_delete": "Delete",
        "resume_empty": "No resumes yet",
        "resume_upload_hint": "Upload a new resume (PDF recommended)",
        # 通用
        "page_title": "Job Search Agent",
        "hero_h1": "🤖 Job Search Agent",
        "hero_subtitle": "Smart Job Search · Skill Matching · Application Tracking",
        "start_search": "🚀 Start Search",
        "dashboard": "📊 Dashboard",
        "search_btn": "🔍 Search Jobs",
        "save_btn": "💾 Save",
        "saved_btn": "✅ Saved",
        "view_btn": "🔗 View",
        "letter_btn": "✉️ Cover Letter",
        "job_title": "Job Title",
        "company": "Company",
        "location": "Location",
        "source": "Source",
        "date": "Date",
        "match_score": "Match",
        "status": "Status",
        "all": "All",
        "saved": "Saved",
        "applied": "\u2705 Applied",
        "interviewing": "Interviewing",
        "rejected": "Rejected",
        "offer": "Offer",
        "no_results": "No results yet. Try a search!",
        "error": "Error",
        # 跟踪页操作按钮
        "btn_apply": "📤 Apply",
        "btn_interview": "🤝 Interview",
        "btn_reject": "❌ Reject",
        "btn_offer": "🎉 Offer",
        "btn_delete": "🗑️ Delete",
        # 搜索页
        "search_page_title": "🔍 Search Jobs",
        "search_desc": "Search multiple platforms and auto-analyze match scores.",
        "search_btn_lg": "🚀 Start Search",
        "search_again_btn": "🚀 Search Again",
        "keywords_label": "Keywords",
        "location_label": "Location",
        "sources_label": "Sources",
        "select_all": "Select All",
        "search_results": "📊 Search Results",
        "jobs_found": "Jobs",
        "high_match": "High Match",
        "avg_match": "Avg Match",
        "job_list": "💼 Job Listings",
        "cover_letter_title": "✉️ Cover Letter",
        # 仪表盘
        "dash_title": "📊 Dashboard",
        "total_tracked": "Tracked",
        "applications": "Applications",
        "interviews": "Interviews",
        "offers": "Offers",
        "application_status": "Application Progress",
        "skill_profile": "🛠️ Skill Profile",
        "edit_profile": "Edit Profile",
        # 跟踪页
        "tracked_title": "📋 Tracked Jobs",
        "learn_plan_title": "📅 Study Plan",
        "all_statuses": "All Statuses",
        "no_tracked": "No saved jobs yet.",
        # 画像页
        "profile_title": "👤 Profile",
        "profile_desc": "Update your skills and preferences for better job matching.",
        "name_label": "Name",
        "target_role": "Target Role",
        "salary_min": "Min Salary",
        "salary_max": "Max Salary",
        "currency": "Currency",
        "locations_label": "Target Locations",
        "target_companies": "Target Companies",
        "save_profile": "💾 Save Profile",
        # 求职信页
        "letter_title": "✉️ Cover Letter Generator",
        "letter_desc": "Select a saved job to generate a tailored cover letter.",
        "generate_letter": "Generate",
        # 首页特征
        "feature_multi": "Multi-Source",
        "feature_multi_desc": "Fetch real-time jobs from Indeed and other platforms",
        "feature_match": "Smart Matching",
        "feature_match_desc": "Auto-analyze match score based on your skill profile",
        "feature_track": "Application Tracking",
        "feature_track_desc": "Track from discovery to offer, all in one place",
        "feature_letter": "Cover Letters",
        "feature_letter_desc": "Generate tailored cover letters with one click",        # Search page button texts
        "searching_text": "Searching...",
        "status_searching": "Searching from ",
        "status_done": "✅ Done, found ",
        "status_done_end": " jobs",
        "status_failed": "❌ Failed",
        "btn_search": "🚀 Start Search",
        "btn_search_again": "🚀 Search Again",
        "btn_save": "💾 Save",
        "btn_letter": "✉️ Letter",
        "btn_view": "🔗 View Posting",
        "btn_add_job": "📤 Add Job",
        "saved_text": "✅ Saved",
        "btn_preview": "👁 Preview",
        "btn_download": "📥 Download",
        "btn_edit": "✏ Edit",
        "btn_optimize": "🎯 Optimize",
        "btn_link_resume": "📎 Link Resume",
        "match_percent": "% Match",
        "url_placeholder": "Paste job URL (Google Careers / LinkedIn / Indeed…)",
        "confirm_delete": "Delete this job?",
        "note_prompt": "Note (optional):",
        "url_empty": "Please paste a job link",
        "parse_failed": "Parse failed",
        "cover_letter_title_short": "Cover Letter",
        "loading": "Loading...",
        "btn_regenerate": "🔄 Regenerate",
        "btn_copy": "📋 Copy",
        "month_prefix": "Month ",
        "week_focus": "Week {}",
        "tasks_completed": "{} tasks completed",
        "gap_modal_title": "🎯 Skill Gap Analysis",
        "btn_generate_plan": "📚 Generate Study Plan",
        "btn_view_plan": "📚 View Study Plan",
        "learn_plan_empty": "No study plans yet. Generate one from the <a href='/tracked'>tracked page</a>.",
        "learn_plan_modal_title": "\U0001f4da Study Plan",
        "learn_plan_progress": "Progress",
        "learn_plan_export": "\U0001f4c5 Export Plan",
        "learn_plan_focus": "\U0001f3af Focus Skills",
        "learn_plan_priority_high": "High Priority",
        "learn_plan_priority_mid": "Mid Priority",
        "learn_plan_priority_low": "Low Priority",
        "learn_plan_resource_type": "Resource",
        "learn_plan_weekly": "\U0001f4c5 Weekly Plan",
        "learn_plan_check_hint": " / Check completed tasks",
        "learn_plan_week": "Week",
        "learn_plan_hours": "h",
        "learn_plan_projects": "\U0001f4bb Projects",
        "learn_plan_skills": "Skills",
        "learn_plan_advice": "\U0001f4a1 Advice:",
        "learn_plan_open": "\U0001f517 Open",
        "learn_plan_priority_label": " Priority",
        "saved_to_tracker": "✅ Saved to tracker, refresh to see",
        "link_resume_title": "\U0001f4ce Link Resume",
        "btn_assign": "\U0001f517 Assign",
        "upload_new_resume": "\U0001f4e4 Upload New Resume",
        "cancel": "Cancel",
        "gap_skills": "✅ Existing Skills",
        "gap_missing": "\u26a0 Missing Skills",
        "gap_weak": "\u2191 Needs Improvement",
        "gap_suggestions": "\U0001f4a1 Suggestions",
        "exists_text": "⚠️ Exists",
        "cal_month_names": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
        "cal_weekday_labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "cal_modal_resources": "\U0001f4da Recommended Resources",
        "cal_modal_projects": "\U0001f4a1 Related Projects",
        "cal_modal_advice": "\U0001f4ad Study Advice",
        "btn_generate_quiz": "🧪 Generate Quiz",
        "quiz_section_title": "🧪 Quiz",
        "quiz_generating": "Generating...",
        "quiz_submit": "Submit Answers",
        "quiz_reset": "Reset",
        "quiz_answer_placeholder": "Enter your answer...",
        "quiz_hint_submit_to_check": "Click \"Submit\" to check reference answers",
        "quiz_result_title": "Quiz Results",
        "quiz_correct": " correct",
        "quiz_question_prefix": "Q",
        "quiz_you_answered": "You chose: ",
        "quiz_correct_answer": "Correct: ",
        "quiz_essay_title": " (Essay)",
        "quiz_your_answer": "Your answer: ",
        "quiz_reference_answer": "Reference: ",
        "quiz_not_answered": "Not answered",

        "btn_fullscreen_edit": "\U0001F58A Fullscreen Edit",
        "resume_preview_title": "\U0001F4C4 Resume Preview",
        "no_content": "No content yet",
        "load_failed": "\u274c Load failed: ",
        "md_edit_placeholder": "Edit in Markdown...",

        # resume editor page
        "resume_edit_title": "Edit Resume - ",
        "resume_edit_subtitle": "Job-specific copy",
        "btn_back": "← Back",
        "btn_export_pdf": "\U0001f4c4 Export PDF",
        "btn_exporting": "Generating...",
        "btn_save": "\U0001f4be Save",
        "md_editor_label": "Markdown Editor",
        "md_editor_placeholder": "Edit in Markdown...",
        "preview_failed": "Preview failed",
        "toolbar_bold": "Bold",
        "toolbar_heading": "Heading",
        "toolbar_list": "List",
        "toolbar_link": "Link",
        "status_saved": "\u2705 Saved",
        "status_save_failed": "\u274c Save failed: ",
        "status_save_error": "\u274c Save error: ",
        "status_export_failed": "Export failed: ",
        "status_export_error": "Export error: ",
        # Timeline & interview
        "interview_note_prompt": "Record notes for this round (optional):",
        "tl_round": "Round {}",
        "tl_detail": "▶ Details",
        "tl_hide": "▼ Hide",
        "tl_interview_records": "—— Interviews ——",
        "just_now": "just now",
        "time_m_ago": "{}min ago",
        "time_h_ago": "{}hr ago",
        "analyzing": "Analyzing...",
        "apply_analysis": "\U0001F4E4 Apply Analysis",
        "method_email": "\U0001F4E7 Apply by Email",
        "method_manual": "\U0001F64B Apply Manually",
        "applied_btn": "\u2705 Applied",
        "next_steps": "\U0001F4CB Next Steps",
        "analysis_failed": "Analysis failed",
        "analysis_error": "Analysis error",
        # Apply analysis instruction templates (used by JS post-processing)
        "visit_company_site": "Visit the company website or job platform to apply",
        "auto_submit_prefix": "Auto-submit to",
        "visit_prefix": "Visit",
        "site_apply_suffix": "website to apply",
        "career_page_suffix": "careers page",
        "search_prefix": "Search",
        "linkedin_suggestion": "Or find the hiring contact via LinkedIn",
        "prep_cover_resume": "Prepare cover letter and resume",
        "auto_fill_submit": "System auto-fills form and submits",
        "result_logged": "Submission result recorded in history",
        "indeed_apply": "Open Indeed page, click \"Apply on Company Site\"",
        "or_visit_prefix": "Or directly visit",
        "search_job_suffix": "to search for jobs",
        "upload_resume_cover": "Upload tailored resume and cover letter",
        "record_status": "Return to system and record application status",
        "gen_cover": "Generate cover letter",
        "send_resume_email": "Send resume to provided email",
        "wait_reply": "Wait for response",
        "indeed_click_prefix": "Open Indeed page, click",
        "indeed_method_header": "Indeed Application Methods",
        "easy_apply": "Easy Apply \u2014 Submit directly on Indeed",
        "apply_on_site_prefix": "Apply on Company Site \u2014 Visit",
        "guessed_url": "Guessed career page",
        "desc_emails": "Emails in description",
        # Learn plan page
        "learn_tasks_done": "tasks done",
        "skill_header": "Skills",
        "kw_header": "Keywords",
        "level_header": "Level",
        "exp_header": "Experience",
        "saved_status": "Saved",
        "failed_status": "Failed",
        "hint_gen_cover": "Please generate a cover letter from the search page first.",
        "downloaded_text": "Downloaded!",
        "copied_text": "Copied!",
        "confirm_regen": "This will discard progress. Regenerate?",
    },
    "zh-CN": {
        "nav_home": "🏠 首页",
        "nav_dashboard": "📊 仪表盘",
        "nav_search": "🔍 搜索",
        "nav_tracked": "📋 职位跟踪",
        "nav_profile": "👤 画像",
        "nav_resume": "📄 简历库",
        "nav_letter": "✉️ 求职信",
        "nav_learn_calendar": "📅 学习计划",
        "resume_title": "简历库",
        "resume_upload": "上传简历",
        "resume_delete": "删除",
        "resume_empty": "暂无简历",
        "resume_upload_hint": "上传新简历（推荐 PDF 格式）",
        # 通用
        "page_title": "职业搜索助手",
        "hero_h1": "🤖 求职Agent",
        "hero_subtitle": "智能职位搜索 · 技能匹配 · 申请跟踪",
        "start_search": "🚀 开始搜索",
        "dashboard": "📊 仪表盘",
        "search_btn": "🔍 搜索职位",
        "save_btn": "💾 保存",
        "saved_btn": "✅ 已保存",
        "view_btn": "🔗 查看",
        "letter_btn": "✉️ 求职信",
        "job_title": "职位",
        "company": "公司",
        "location": "地点",
        "source": "来源",
        "date": "日期",
        "match_score": "匹配度",
        "status": "状态",
        "all": "全部",
        "saved": "已保存",
        "applied": "已申请",
        "interviewing": "面试中",
        "rejected": "已拒绝",
        "offer": "Offer",
        "no_results": "还没有搜索结果，试试搜索吧！",
        "loading": "搜索中…",
        "error": "错误",
        # 跟踪页操作按钮
        "btn_apply": "📤 申请",
        "btn_interview": "🤝 面试",
        "btn_reject": "❌ 拒绝",
        "btn_offer": "🎉 Offer",
        "btn_delete": "🗑️ 删除",
        # 搜索页
        "search_page_title": "🔍 搜索职位",
        "search_desc": "点击下方按钮，从多个平台获取实时职位并自动分析匹配度。",
        "search_btn_lg": "🚀 开始搜索",
        "search_again_btn": "🚀 重新搜索",
        "keywords_label": "关键词",
        "location_label": "地点",
        "sources_label": "来源",
        "select_all": "全选",
        "search_results": "📊 搜索结果",
        "jobs_found": "职位",
        "high_match": "高匹配",
        "avg_match": "平均匹配度",
        "job_list": "💼 职位列表",
        "cover_letter_title": "✉️ 求职信",
        # 仪表盘
        "dash_title": "📊 仪表盘",
        "total_tracked": "已跟踪",
        "applications": "已申请",
        "interviews": "面试",
        "offers": "Offer",
        "application_status": "申请状态",
        "skill_profile": "🛠️ 技能画像",
        "edit_profile": "编辑画像",
        # 跟踪页
        "tracked_title": "📋 跟踪职位",
        "learn_plan_title": "📅 学习计划",
        "all_statuses": "所有状态",
        "no_tracked": "还没有保存职位",
        # 画像页
        "profile_title": "👤 用户画像",
        "profile_desc": "更新你的技能和偏好以获得更好的匹配。",
        "name_label": "姓名",
        "target_role": "目标职位",
        "salary_min": "最低薪资",
        "salary_max": "最高薪资",
        "currency": "货币",
        "locations_label": "目标地点",
        "target_companies": "目标公司",
        "save_profile": "💾 保存画像",
        # 求职信页
        "letter_title": "✉️ 求职信生成器",
        "letter_desc": "选择一个已保存的职位生成定制求职信。",
        "generate_letter": "生成",
        # 首页特征
        "feature_multi": "多源搜索",
        "feature_multi_desc": "从Indeed等平台获取实时职位信息",
        "feature_match": "智能匹配",
        "feature_match_desc": "基于你的技能画像自动分析职位匹配度",
        "feature_track": "申请跟踪",
        "feature_track_desc": "管理你的申请状态，从发现到Offer全程跟踪",
        "feature_letter": "求职信生成",
        "feature_letter_desc": "一键生成定制求职信，突出你的优势",        # 搜索页按钮文本
        "searching_text": "搜索中…",
        "status_searching": "正在从 ",
        "status_done": "✅ 完成，找到 ",
        "status_done_end": " 个相关职位",
        "status_failed": "❌ 失败",
        "btn_search": "🚀 开始搜索",
        "btn_search_again": "🚀 重新搜索",
        "btn_save": "💾 保存",
        "btn_letter": "✉️ 求职信",
        "btn_view": "🔗 查看原文",
        "btn_add_job": "📤 添加职位",
        "saved_text": "✅ 已保存",
        "btn_preview": "👁 预览",
        "btn_download": "📥 下载",
        "btn_edit": "✏ 编辑",
        "btn_optimize": "🎯 优化",
        "btn_link_resume": "📎 关联简历",
        "match_percent": "% 匹配",
        "url_placeholder": "粘贴职位链接，如 Google Careers / LinkedIn / Indeed…",
        "confirm_delete": "确定删除？",
        "note_prompt": "备注（可选）:",
        "url_empty": "请粘贴职位链接",
        "parse_failed": "解析失败",
        "cover_letter_title_short": "求职信",
        "loading": "加载中...",
        "btn_regenerate": "🔄 重新生成",
        "btn_copy": "📋 复制",
        "month_prefix": "",
        "week_focus": "第{}周",
        "tasks_completed": "{}/{} 任务完成",
        "gap_modal_title": "🎯 技能差距分析",
        "btn_generate_plan": "📚 生成学习计划",
        "btn_view_plan": "📚 查看学习计划",
        "learn_plan_empty": "暂无学习计划，请先在 <a href='/tracked'>跟踪页面</a> 为职位生成学习计划。",
        "learn_plan_modal_title": "📚 强化学习计划",
        "learn_plan_progress": "进度",
        "learn_plan_export": "📅 导出计划",
        "learn_plan_focus": "🎯 重点技能",
        "learn_plan_priority_high": "高优先级",
        "learn_plan_priority_mid": "中优先级",
        "learn_plan_priority_low": "低优先级",
        "learn_plan_resource_type": "资源",
        "learn_plan_weekly": "📅 每周计划",
        "learn_plan_check_hint": "∕ 勾选已完成的任务",
        "learn_plan_week": "第",
        "learn_plan_hours": "h",
        "learn_plan_projects": "💻 练习项目",
        "learn_plan_skills": "技能",
        "learn_plan_advice": "💡 建议:",
        "learn_plan_open": "\U0001f517 \u6253\u5f00",
        "learn_plan_priority_label": "\u4f18\u5148\u7ea7",
        "saved_to_tracker": "✅ 已保存到跟踪列表，刷新页面查看",
        "cal_month_names": ["1\u6708", "2\u6708", "3\u6708", "4\u6708", "5\u6708", "6\u6708", "7\u6708", "8\u6708", "9\u6708", "10\u6708", "11\u6708", "12\u6708"],
        "cal_weekday_labels": ["\u4e00", "\u4e8c", "\u4e09", "\u56db", "\u4e94", "\u516d", "\u65e5"],
        "cal_modal_resources": "\U0001f4da \u63a8\u8350\u8d44\u6e90",
        "cal_modal_projects": "\U0001f4a1 \u76f8\u5173\u9879\u76ee",
        "cal_modal_advice": "\U0001f4ad \u5b66\u4e60\u5efa\u8bae",
        "btn_generate_quiz": "\U0001f9ea \u751f\u6210\u6d4b\u9a8c",
        "quiz_section_title": "🧪 测验",
        "quiz_generating": "生成中...",
        "quiz_submit": "提交答题",
        "quiz_reset": "重置",
        "quiz_answer_placeholder": "请输入你的回答...",
        "quiz_hint_submit_to_check": "答完后点\"提交\"可查看参考答案",
        "quiz_result_title": "答题结果",
        "quiz_correct": " 正确",
        "quiz_question_prefix": "第",
        "quiz_you_answered": " 你选: ",
        "quiz_correct_answer": " 正确: ",
        "quiz_essay_title": " (简答)",
        "quiz_your_answer": "你的回答: ",
        "quiz_reference_answer": "参考答案: ",
        "quiz_not_answered": "未填",

        "btn_fullscreen_edit": "🖊 全屏编辑",
        "resume_preview_title": "📄 简历预览",
        "no_content": "暂无内容",
        "load_failed": "❌ 加载失败: ",
        "md_edit_placeholder": "Markdown 编辑...",
        "link_resume_title": "\U0001f4ce 关联简历",
        "btn_assign": "\U0001f517 关联",
        "upload_new_resume": "\U0001f4e4 上传新简历并关联",
        "cancel": "取消",
        "gap_skills": "\u2705 已有技能",
        "gap_missing": "\u26a0 缺少技能",
        "gap_weak": "\u2191 需加强",
        "gap_suggestions": "\U0001f4a1 建议",
        "exists_text": "⚠️ 已存在",

        # resume editor page
        "resume_edit_title": "\u7f16\u8f91\u7b80\u5386 - ",
        "resume_edit_subtitle": "\u804c\u4f4d\u4e13\u5c5e\u526f\u672c",
        "btn_back": "\u2190 \u8fd4\u56de",
        "btn_export_pdf": "\U0001f4c4 \u5bfc\u51fa PDF",
        "btn_exporting": "\u751f\u6210\u4e2d...",
        "btn_save": "\U0001f4be \u4fdd\u5b58",
        "md_editor_label": "Markdown \u7f16\u8f91\u5668",
        "md_editor_placeholder": "Markdown \u683c\u5f0f\u7f16\u8f91...",
        "preview_failed": "\u9884\u89c8\u5931\u8d25",
        "toolbar_bold": "\u7c97\u4f53",
        "toolbar_heading": "\u6807\u9898",
        "toolbar_list": "\u5217\u8868",
        "toolbar_link": "\u94fe\u63a5",
        "status_saved": "\u2705 \u5df2\u4fdd\u5b58",
        "status_save_failed": "\u274c \u4fdd\u5b58\u5931\u8d25: ",
        "status_save_error": "\u274c \u4fdd\u5b58\u51fa\u9519: ",
        "status_export_failed": "\u5bfc\u51fa\u5931\u8d25: ",
        "status_export_error": "\u5bfc\u51fa\u51fa\u9519: ",
        # Timeline & interview
        "interview_note_prompt": "\u8bb0\u5f55\u8fd9\u8f6e\u9762\u8bd5\u5907\u6ce8\uff08\u53ef\u9009\uff09:",
        "tl_round": "\u7b2c{}轮",
        "tl_detail": "\u25b6 \u8be6\u60c5",
        "tl_hide": "\u25bc \u6536\u8d77",
        "tl_interview_records": "\u2014\u2014 \u9762\u8bd5\u8bb0\u5f55 \u2014\u2014",
        "just_now": "\u521a\u521a",
        "time_m_ago": "{} \u5206\u949f\u524d",
        "time_h_ago": "{} \u5c0f\u65f6\u524d",
        "analyzing": "\u5206\u6790\u4e2d...",
        "apply_analysis": "\U0001F4E4 \u7533\u8bf7\u5206\u6790",
        "method_email": "\U0001F4E7 \u90ae\u7bb1\u7533\u8bf7",
        "method_manual": "\U0001F64B \u624b\u52a8\u7533\u8bf7",
        "applied_btn": "\u2705 \u5df2\u7533\u8bf7",
        "next_steps": "\U0001F4CB \u4e0b\u4e00\u6b65",
        "analysis_failed": "\u5206\u6790\u5931\u8d25",
        "analysis_error": "\u5206\u6790\u51fa\u9519",
        # Apply analysis instruction templates
        "visit_company_site": "\u8bf7\u81ea\u884c\u524d\u5f80\u516c\u53f8\u5b98\u7f51\u6216\u6c42\u804c\u5e73\u53f0\u6295\u9012",
        "auto_submit_prefix": "\u4e00\u952e\u6295\u9012\u81f3",
        "visit_prefix": "\u524d\u5f80",
        "site_apply_suffix": "\u5b98\u7f51\u63d0\u4ea4\u7533\u8bf7",
        "career_page_suffix": "\u5b98\u7f51\u67e5\u627e Careers \u9875\u9762",
        "search_prefix": "\u641c\u7d22",
        "linkedin_suggestion": "\u6216\u901a\u8fc7 LinkedIn \u627e\u5230\u62db\u8058\u8d1f\u8d23\u4eba\u8054\u7cfb",
        "prep_cover_resume": "\u51c6\u5907\u6c42\u804c\u4fe1\u548c\u7b80\u5386",
        "auto_fill_submit": "\u7cfb\u7edf\u81ea\u52a8\u586b\u5199\u8868\u5355\u5e76\u63d0\u4ea4",
        "result_logged": "\u6295\u9012\u7ed3\u679c\u4f1a\u8bb0\u5f55\u5230\u7533\u8bf7\u5386\u53f2",
        "indeed_apply": "\u6253\u5f00 Indeed \u9875\u9762\uff0c\u70b9\u51fb \"Apply on Company Site\"",
        "or_visit_prefix": "\u6216\u76f4\u63a5\u524d\u5f80",
        "search_job_suffix": "\u641c\u7d22\u804c\u4f4d",
        "upload_resume_cover": "\u4e0a\u4f20\u5b9a\u5236\u7b80\u5386\u548c\u6c42\u804c\u4fe1",
        "record_status": "\u8fd4\u56de\u7cfb\u7edf\u8bb0\u5f55\u7533\u8bf7\u72b6\u6001",
        "gen_cover": "\u751f\u6210\u6c42\u804c\u4fe1",
        "send_resume_email": "\u53d1\u9001\u7b80\u5386\u5230\u6307\u5b9a\u90ae\u7bb1",
        "wait_reply": "\u7b49\u5f85\u5bf9\u65b9\u56de\u590d",
        "indeed_click_prefix": "\u6253\u5f00 Indeed \u9875\u9762\uff0c\u70b9\u51fb",
        "indeed_method_header": "Indeed \u7533\u8bf7\u65b9\u5f0f",
        "easy_apply": "Easy Apply \u2014 \u901a\u8fc7 Indeed \u76f4\u63a5\u6295\u9012",
        "apply_on_site_prefix": "Apply on Company Site \u2014 \u524d\u5f80",
        "guessed_url": "\u731c\u6d4b\u7684\u62db\u8058\u9875",
        "desc_emails": "\u63cf\u8ff0\u4e2d\u90ae\u7bb1",
        "learn_tasks_done": "\u4efb\u52a1\u5b8c\u6210",
        "skill_header": "\u6280\u80fd",
        "kw_header": "\u5173\u952e\u8bcd",
        "level_header": "\u6c34\u5e73",
        "exp_header": "\u7ecf\u9a8c",
        "saved_status": "\u5df2\u4fdd\u5b58",
        "failed_status": "\u5931\u8d25",
        "hint_gen_cover": "\u8bf7\u5148\u5728\u641c\u7d22\u9875\u9762\u751f\u6210\u6c42\u804c\u4fe1\u3002",
        "downloaded_text": "\u5df2\u4e0b\u8f7d!",
        "copied_text": "\u5df2\u590d\u5236!",
        "confirm_regen": "\u786e\u5b9a\u91cd\u65b0\u751f\u6210\u5b66\u4e60\u8ba1\u5212\uff1f\uff08\u5c06\u4e22\u5f03\u5f53\u524d\u8fdb\u5ea6\uff09",
    },
    "fr": {
        # Navigation
        "nav_home": "🏠 Accueil",
        "nav_dashboard": "📊 Tableau de bord",
        "nav_search": "🔍 Recherche",
        "nav_tracked": "📋 Suivi",
        "nav_profile": "👤 Profil",
        "nav_resume": "📄 CV",
        "nav_letter": "✉️ Lettre de motivation",
        "nav_learn_calendar": "📅 Plan d\u0027\u00e9tude",
        "resume_title": "Bibliothèque de CV",
        "resume_upload": "Télécharger un CV",
        "resume_delete": "Supprimer",
        "resume_empty": "Aucun CV pour le moment",
        "resume_upload_hint": "Télécharger un nouveau CV (PDF recommandé)",
        # Général
        "page_title": "Agent de Recherche d'Emploi",
        "hero_h1": "🤖 Agent de Recherche d'Emploi",
        "hero_subtitle": "Recherche intelligente · Correspondance de compétences · Suivi des candidatures",
        "start_search": "🚀 Lancer la recherche",
        "dashboard": "📊 Tableau de bord",
        "search_btn": "🔍 Rechercher",
        "save_btn": "💾 Enregistrer",
        "saved_btn": "✅ Enregistré",
        "view_btn": "🔗 Voir",
        "letter_btn": "✉️ Lettre",
        "job_title": "Titre du poste",
        "company": "Entreprise",
        "location": "Lieu",
        "source": "Source",
        "date": "Date",
        "match_score": "Correspondance",
        "status": "Statut",
        "all": "Tout",
        "saved": "Enregistrés",
        "applied": "Postulés",
        "interviewing": "Entretien",
        "rejected": "Refusés",
        "offer": "Offre",
        "no_results": "Aucun résultat pour le moment. Essayez une recherche !",
        "loading": "Recherche en cours...",
        "error": "Erreur",
        # Boutons d'action page suivi
        "btn_apply": "📤 Postuler",
        "btn_interview": "🤝 Entretien",
        "btn_reject": "❌ Refuser",
        "btn_offer": "🎉 Offre",
        "btn_delete": "🗑️ Supprimer",
        # Page de recherche
        "search_page_title": "🔍 Rechercher des offres",
        "search_desc": "Rechercher sur plusieurs plateformes et analyser automatiquement les scores de correspondance.",
        "search_btn_lg": "🚀 Lancer la recherche",
        "search_again_btn": "🚀 Relancer la recherche",
        "keywords_label": "Mots-clés",
        "location_label": "Lieu",
        "sources_label": "Sources",
        "select_all": "Tout sélectionner",
        "search_results": "📊 Résultats de recherche",
        "jobs_found": "Offres",
        "high_match": "Haute correspondance",
        "avg_match": "Corresp. moyenne",
        "job_list": "💼 Liste des offres",
        "cover_letter_title": "✉️ Lettre de motivation",
        # Tableau de bord
        "dash_title": "📊 Tableau de bord",
        "total_tracked": "Suivis",
        "applications": "Candidatures",
        "interviews": "Entretiens",
        "offers": "Offres",
        "application_status": "Progression des candidatures",
        "skill_profile": "🛠️ Profil de compétences",
        "edit_profile": "Modifier le profil",
        # Page de suivi
        "tracked_title": "📋 Offres suivies",
        "learn_plan_title": "📅 Plan d\u0027\u00e9tude",
        "all_statuses": "Tous les statuts",
        "no_tracked": "Aucune offre enregistrée.",
        # Page de profil
        "profile_title": "👤 Profil",
        "profile_desc": "Mettez à jour vos compétences et préférences.",
        "name_label": "Nom",
        "target_role": "Poste visé",
        "salary_min": "Salaire min",
        "salary_max": "Salaire max",
        "currency": "Devise",
        "locations_label": "Lieux cibles",
        "target_companies": "Entreprises cibles",
        "save_profile": "💾 Enregistrer le profil",
        # Générateur de lettre
        "letter_title": "✉️ Générateur de lettre",
        "letter_desc": "Sélectionnez une offre enregistrée pour générer une lettre personnalisée.",
        "generate_letter": "Générer",
        # Fonctionnalités d'accueil
        "feature_multi": "Multi-sources",
        "feature_multi_desc": "Offres en temps réel depuis Indeed et d'autres plateformes",
        "feature_match": "Correspondance intelligente",
        "feature_match_desc": "Analyse automatique basée sur votre profil de compétences",
        "feature_track": "Suivi des candidatures",
        "feature_track_desc": "De la découverte à l'offre, tout au même endroit",
        "feature_letter": "Lettres de motivation",
        "feature_letter_desc": "Générez des lettres personnalisées en un clic",
        # Boutons de recherche (utilisés dans la page de recherche)
        "searching_text": "Recherche en cours…",
        "status_searching": "Recherche en cours depuis ",
        "status_done": "✅ Terminé, ",
        "status_done_end": " offres trouvées",
        "status_failed": "❌ Échec",
        "btn_search": "🚀 Lancer la recherche",
        "btn_search_again": "🚀 Relancer la recherche",
        "btn_save": "💾 Enregistrer",
        "cal_month_names": ["Janvier", "F\u00e9vrier", "Mars", "Avril", "Mai", "Juin", "Juillet", "Ao\u00fbt", "Septembre", "Octobre", "Novembre", "D\u00e9cembre"],
        "cal_weekday_labels": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
        "cal_modal_resources": "\U0001f4da Ressources recommand\u00e9es",
        "cal_modal_projects": "\U0001f4a1 Projets connexes",
        "cal_modal_advice": "\U0001f4ad Conseils d'\u00e9tude",
        "btn_generate_quiz": "🧪 Générer le quiz",
        "quiz_section_title": "🧪 Quiz",
        "quiz_generating": "Génération...",
        "quiz_submit": "Soumettre",
        "quiz_reset": "Réinitialiser",
        "quiz_answer_placeholder": "Entrez votre réponse...",
        "quiz_hint_submit_to_check": "Cliquez sur \"Soumettre\" pour voir la réponse",
        "quiz_result_title": "Résultats",
        "quiz_correct": " correct",
        "quiz_question_prefix": "Q",
        "quiz_you_answered": "Vous avez choisi : ",
        "quiz_correct_answer": "Correct : ",
        "quiz_essay_title": " (Rédaction)",
        "quiz_your_answer": "Votre réponse : ",
        "quiz_reference_answer": "Référence : ",
        "quiz_not_answered": "Non répondu",

        "btn_fullscreen_edit": "🖊 Édition plein écran",
        "resume_preview_title": "📄 Aperçu du CV",
        "no_content": "Pas encore de contenu",
        "load_failed": "❌ Échec du chargement: ",
        "md_edit_placeholder": "Modifier en Markdown...",
        "btn_letter": "✉️ Lettre de motivation",
        "btn_view": "🔗 Voir l'offre",
        "btn_add_job": "📤 Ajouter un poste",
        "saved_text": "✅ Enregistré",
        "btn_preview": "👁 Aperçu",
        "btn_download": "📥 Télécharger",
        "btn_edit": "✏ Modifier",
        "btn_optimize": "🎯 Optimiser",
        "btn_link_resume": "📎 Lier CV",
        "match_percent": "% Correspondance",
        "url_placeholder": "Collez le lien (Google Careers / LinkedIn / Indeed…)",
        "confirm_delete": "Supprimer ce poste ?",
        "note_prompt": "Note (optionnelle) :",
        "url_empty": "Veuillez coller un lien",
        "parse_failed": "Échec d'analyse",
        "cover_letter_title_short": "Lettre de motivation",
        "loading": "Chargement...",
        "btn_regenerate": "🔄 Régénérer",
        "btn_copy": "📋 Copier",
        "month_prefix": "",
        "week_focus": "Semaine {}",
        "tasks_completed": "{} tâches terminées",
        "gap_modal_title": "🎯 Analyse des écarts de compétences",
        "btn_generate_plan": "📚 Générer un plan d'étude",
        "btn_view_plan": "📚 Voir le plan d'étude",
        "learn_plan_empty": "Aucun plan d'étude pour le moment. Générez-en un depuis la <a href='/tracked'>page de suivi</a>.",
        "learn_plan_modal_title": "\U0001f4da Plan d'\u00e9tude",
        "learn_plan_progress": "Progression",
        "learn_plan_export": "\U0001f4c5 Exporter le plan",
        "learn_plan_focus": "\U0001f3af Comp\u00e9tences cl\u00e9s",
        "learn_plan_priority_high": "Haute priorit\u00e9",
        "learn_plan_priority_mid": "Priorit\u00e9 moyenne",
        "learn_plan_priority_low": "Faible priorit\u00e9",
        "learn_plan_resource_type": "Ressource",
        "learn_plan_weekly": "\U0001f4c5 Plan hebdomadaire",
        "learn_plan_check_hint": " / T\u00e2ches termin\u00e9es",
        "learn_plan_week": "Semaine",
        "learn_plan_hours": "h",
        "learn_plan_projects": "\U0001f4bb Projets",
        "learn_plan_skills": "Comp\u00e9tences",
        "learn_plan_advice": "\U0001f4a1 Conseils:",
        "learn_plan_open": "\U0001f517 Ouvrir",
        "learn_plan_priority_label": " Priorit\u00e9",
        "saved_to_tracker": "✅ Enregistré, actualisez pour voir",
        "link_resume_title": "\U0001f4ce Lier CV",
        "btn_assign": "\U0001f517 Assigner",
        "upload_new_resume": "\U0001f4e4 T\u00e9l\u00e9charger un nouveau CV",
        "cancel": "Annuler",
        "gap_skills": "\u2705 Compétences existantes",
        "gap_missing": "\u26a0 Compétences manquantes",
        "gap_weak": "\u2191 À améliorer",
        "gap_suggestions": "\U0001f4a1 Suggestions",
        "exists_text": "⚠️ Déjà enregistré",
        "btn_letter_generate": "✉️ Générer la lettre",
        "my_profile": "Mon profil",
        "tracked_jobs": "Offres suivies",        # resume editor page
        "resume_edit_title": "Modifier CV - ",
        "resume_edit_subtitle": "Copie sp\u00e9cifique au poste",
        "btn_back": "\u2190 Retour",
        "btn_export_pdf": "\U0001f4c4 Exporter PDF",
        "btn_exporting": "G\u00e9n\u00e9ration...",
        "btn_save": "\U0001f4be Enregistrer",
        "md_editor_label": "\u00c9diteur Markdown",
        "md_editor_placeholder": "Modifier en Markdown...",
        "preview_failed": "\u00c9chec de l\u2019aper\u00e7u",
        "toolbar_bold": "Gras",
        "toolbar_heading": "Titre",
        "toolbar_list": "Liste",
        "toolbar_link": "Lien",
        "status_saved": "\u2705 Enregistr\u00e9",
        "status_save_failed": "\u274c \u00c9chec enreg.: ",
        "status_save_error": "\u274c Erreur enreg.: ",
        "status_export_failed": "\u00c9chec export: ",
        "status_export_error": "Erreur export: ",
        # Timeline & interview
        "interview_note_prompt": "Notes pour ce tour (optionnel) :",
        "tl_round": "Tour {}",
        "tl_detail": "\u25b6 D\u00e9tails",
        "tl_hide": "\u25bc Masquer",
        "tl_interview_records": "\u2014\u2014 Entretiens \u2014\u2014",
        "just_now": "\u00e0 l\u2019instant",
        "time_m_ago": "il y a {} min",
        "time_h_ago": "il y a {} h",
        "analyzing": "Analyse en cours...",
        "apply_analysis": "\U0001F4E4 Analyse de candidature",
        "method_email": "\U0001F4E7 Postuler par email",
        "method_manual": "\U0001F64B Postuler manuellement",
        "applied_btn": "\u2705 Postul\u00e9",
        "next_steps": "\U0001F4CB Prochaines \u00e9tapes",
        "analysis_failed": "\u00c9chec d\u2019analyse",
        "analysis_error": "Erreur d\u2019analyse",
        # Apply analysis instruction templates
        "visit_company_site": "Visitez le site web de l\u2019entreprise ou une plateforme d\u2019emploi pour postuler",
        "auto_submit_prefix": "Soumission auto pour",
        "visit_prefix": "Visiter",
        "site_apply_suffix": "le site web pour postuler",
        "career_page_suffix": "page Carri\u00e8res",
        "search_prefix": "Rechercher",
        "linkedin_suggestion": "Ou trouver le recruteur sur LinkedIn",
        "prep_cover_resume": "Pr\u00e9parer lettre de motivation et CV",
        "auto_fill_submit": "Le syst\u00e8me remplit le formulaire et soumet",
        "result_logged": "Le r\u00e9sultat sera enregistr\u00e9 dans l\u2019historique",
        "indeed_apply": "Ouvrir la page Indeed, cliquer sur \"Apply on Company Site\"",
        "or_visit_prefix": "Ou visiter directement",
        "search_job_suffix": "pour chercher des offres",
        "upload_resume_cover": "T\u00e9l\u00e9charger CV et lettre de motivation personnalis\u00e9s",
        "record_status": "Revenir au syst\u00e8me et enregistrer le statut",
        "gen_cover": "G\u00e9n\u00e9rer une lettre de motivation",
        "send_resume_email": "Envoyer le CV par email",
        "wait_reply": "Attendre une r\u00e9ponse",
        "indeed_click_prefix": "Ouvrir la page Indeed, cliquer",
        "indeed_method_header": "M\u00e9thodes de candidature Indeed",
        "easy_apply": "Easy Apply \u2014 Postuler directement sur Indeed",
        "apply_on_site_prefix": "Apply on Company Site \u2014 Visiter",
        "guessed_url": "Page Carri\u00e8res estim\u00e9e",
        "desc_emails": "Emails dans la description",
        "learn_tasks_done": "t\u00e2ches faites",
        "skill_header": "Comp\u00e9tences",
        "kw_header": "Mots-cl\u00e9s",
        "level_header": "Niveau",
        "exp_header": "Exp\u00e9rience",
        "saved_status": "Sauvegard\u00e9",
        "failed_status": "\u00c9chec",
        "hint_gen_cover": "G\u00e9n\u00e9rez d\u2019abord une lettre de motivation depuis la page de recherche.",
        "downloaded_text": "T\u00e9l\u00e9charg\u00e9 !",
        "copied_text": "Copi\u00e9 !",
        "confirm_regen": "Cela supprimera la progression. Reg\u00e9n\u00e9rer ?",

    },

}


def t(lang: str, key: str, default: str = "") -> str:
    """翻译函数"""
    if lang not in LANGUAGES:
        lang = "zh-CN"
    return LANGUAGES[lang].get(key, LANGUAGES.get("zh-CN", {}).get(key, default or key))


class JobAgentHandler(BaseHTTPRequestHandler):

    agent: JobAgent = None

    def _get_lang(self, params: Dict) -> str:
        """获取语言偏好：URL参数 > Accept-Language > profile存储 > 默认"""
        lang = params.get("lang", "")
        if lang in LANGUAGES:
            return lang
        # 从浏览器 Accept-Language 自动检测
        accept = self.headers.get("Accept-Language", "")
        for pref in accept.split(","):
            code = pref.split(";")[0].strip()
            if code.startswith("zh"): return "zh-CN"
            if code.startswith("fr"): return "fr"
            if code.startswith("en"): return "en"
        try:
            stored = self.agent.engine.profile.profile.get("language", "zh-CN")
            if stored in LANGUAGES:
                return stored
        except:
            pass
        return "zh-CN"

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = dict(urllib.parse.parse_qsl(parsed.query))

        routes = {
            "/": self.handle_home,
            "/dashboard": self.handle_dashboard,
            "/search": self.handle_search_page,
            "/tracked": self.handle_tracked_page,
            "/profile": self.handle_profile_page,
            "/letter": self.handle_letter_page,
            "/resumes": self.handle_resume_page,
            "/learn_plan": self.handle_learn_calendar_page,
            "/resume_view": self.handle_resume_view_page,
        }

        # GET 下载简历 / 获取简历列表
        if path == "/api/get_resume":
            self.api_get_resume_GET(params)
            return
        if path == "/api/list_resumes":
            self.api_list_resumes_GET(params)
            return
        if path == "/api/preview_resume":
            self.api_preview_resume_GET(params)
            return

        # Special GET handlers that need method awareness
        if path == "/api/learn_plan":
            self.api_learn_plan(params, method="GET")
            return
        if path == "/api/learn_plan_ical":
            self.api_learn_plan_ical(params)
            return
        if path == "/api/get_cover_letter":
            self.api_get_cover_letter(params)
            return
        if path == "/api/learn_plan_progress":
            self.api_learn_plan_progress_GET(params)
            return
        if path == "/api/generate_quiz":
            self.api_generate_quiz(params)
            return

        handler = routes.get(path)
        if handler:
            handler(params)
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        # 处理文件上传（multipart/form-data）
        if path == "/api/upload_resume":
            self.api_upload_resume(body, self.headers.get("Content-Type", ""))
            return
        if path == "/api/add_resume_multipart":
            self.api_add_resume_multipart(body, self.headers.get("Content-Type", ""))
            return

        try:
            data = json.loads(body)
        except:
            data = {}

        api_routes = {
            "/api/run_search": self.api_run_search,
            "/api/save_job": self.api_save_job,
            "/api/update_status": self.api_update_status,
            "/api/delete_job": self.api_delete_job,
            "/api/update_profile": self.api_update_profile,
            "/api/generate_letter": self.api_generate_letter,
            "/api/upload_resume": self.api_upload_resume,
            "/api/get_resume": self.api_get_resume,
            "/api/list_resumes": self.api_list_resumes,
            "/api/add_resume": self.api_add_resume,
            "/api/delete_resume": self.api_delete_resume,
            "/api/assign_resume": self.api_assign_resume,
            "/api/save_job_resume": self.api_save_job_resume,
            "/api/get_resume_markdown": self.api_get_resume_markdown,
            "/api/download_resume_pdf": self.api_download_resume_pdf,
            "/api/convert_markdown": self.api_convert_markdown,
            "/api/save_job_resume_md": self.api_save_job_resume_md,
            "/api/analyze_apply": self.api_analyze_apply,
            "/api/record_apply": self.api_record_apply,
            "/api/tailor_resume": self.api_tailor_resume,
            "/api/fetch_job_from_url": self.api_fetch_job_from_url,
            "/api/analyze_skill_gap": self.api_analyze_skill_gap,
            "/api/learn_plan": self.api_learn_plan,
            "/api/learn_plan_progress": self.api_learn_plan_progress,
            "/api/learn_plan_ical": self.api_learn_plan_ical,
            "/api/generate_quiz": self.api_generate_quiz,
            "/api/quiz_submit": self.api_quiz_submit,
            "/api/save_cover_letter": self.api_save_cover_letter,
        }

        handler = api_routes.get(path)
        if handler:
            handler(data)
        else:
            self.send_json({"error": "not found"}, 404)

    # ===================== 页面 =====================

    def handle_home(self, params):
        lang = self._get_lang(params)
        html = self._page(t(lang, "page_title"), f"""
        <div class="hero">
            <h1>{t(lang, 'hero_h1')}</h1>
            <p class="subtitle">{t(lang, 'hero_subtitle')}</p>
            <div class="hero-actions">
                <a href="/search?lang={lang}" class="btn btn-primary btn-lg">{t(lang, 'start_search')}</a>
                <a href="/dashboard?lang={lang}" class="btn btn-secondary btn-lg">{t(lang, 'dashboard')}</a>
            </div>
        </div>
        <div class="features">
            <div class="feature-card">
                <div class="feature-icon">🔍</div>
                <h3>{t(lang, 'feature_multi')}</h3>
                <p>{t(lang, 'feature_multi_desc')}</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🎯</div>
                <h3>{t(lang, 'feature_match')}</h3>
                <p>{t(lang, 'feature_match_desc')}</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">📋</div>
                <h3>{t(lang, 'feature_track')}</h3>
                <p>{t(lang, 'feature_track_desc')}</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">✉️</div>
                <h3>{t(lang, 'feature_letter')}</h3>
                <p>{t(lang, 'feature_letter_desc')}</p>
            </div>
        </div>
        """, lang=lang)
        self._send_html(html)

    def handle_dashboard(self, params):
        lang = self._get_lang(params)
        data = self.agent.get_dashboard_data()
        stats = data["tracker_stats"]
        profile = data["profile"]
        years_label = "yr" if lang == "en" else "年"

        cards = "".join([
            f"""<div class="stat-card"><div class="stat-number">{v}</div>
                 <div class="stat-label">{l}</div></div>"""
            for v, l in [(stats['total'], t(lang, 'total_tracked')), (stats['applied'] + stats['interviewing'], t(lang, 'applications')),
                         (stats['rejected'], t(lang, 'rejected')), (stats['offer'], t(lang, 'offers')),
                         (f"{stats.get('avg_match_score', 0)}%", t(lang, 'avg_match'))]
        ])

        segs = [
            ("saved", "#5f6368", stats['saved'], t(lang, 'saved')),
            ("applied", "#1a73e8", stats['applied'], t(lang, 'applied')),
            ("interviewing", "#fbbc04", stats['interviewing'], t(lang, 'interviewing')),
            ("rejected", "#ea4335", stats['rejected'], t(lang, 'rejected')),
            ("offer", "#34a853", stats['offer'], t(lang, 'offer')),
        ]
        status_bar = '<div class="status-bar">' + "".join(
            f'<div class="status-segment" style="flex:{max(c,1)};background:{color}">{c} {label}</div>'
            for _, color, c, label in segs
        ) + '</div>'

        skills = ""
        levels_map = {"beginner": 1, "intermediate": 2, "expert": 3}
        for cat, info in profile.get("skills", {}).items():
            n = levels_map.get(info.get("level", "intermediate"), 2)
            dots = "".join(
                '<span class="dot {}"></span>'.format("filled" if i < n else "")
                for i in range(3)
            )
            skills += f"""
            <div class="skill-item">
                <span class="skill-name">{cat}</span>
                <span class="skill-level">{dots}</span>
                <span class="skill-years">{info.get('years', 0)}{years_label}</span>
            </div>"""

        html = self._page(t(lang, 'dash_title'), f"""
        <h1>{t(lang, 'dash_title')}</h1>
        <div class="stats-grid">{cards}</div>
        <div class="section"><h2>{t(lang, 'application_status')}</h2>{status_bar}</div>
        <div class="section">
            <h2>{t(lang, 'skill_profile')}</h2>
            <div class="skills-list">{skills}</div>
            <a href="/profile?lang={lang}" class="btn">{t(lang, 'edit_profile')}</a>
        </div>
        """, lang=lang)
        self._send_html(html)

    def handle_search_page(self, params):
        lang = self._get_lang(params)
        
        # Pre-translate all visible text
        _t = lambda k: t(lang, k)
        
        
        searching_text = t(lang, "searching_text")
        status_searching = t(lang, "status_searching")
        status_done = t(lang, "status_done")
        status_done_end = t(lang, "status_done_end")
        status_failed = t(lang, "status_failed")
        btn_search = t(lang, "btn_search")
        btn_search_again = t(lang, "btn_search_again")
        btn_save = t(lang, "btn_save")
        btn_letter = t(lang, "btn_letter")
        btn_view = t(lang, "btn_view")
        saved_text = t(lang, "saved_text")
        exists_text = t(lang, "exists_text")
        
        h1_title = _t('search_page_title')
        kw_label = _t('keywords_label')
        loc_label = _t('location_label')
        src_label = _t('sources_label')
        select_all = _t('select_all')
        jobs_label = _t('jobs_found')
        high_match = _t('high_match')
        avg_match = _t('avg_match')
        search_results_h2 = _t('search_results')
        job_list_h2 = _t('job_list')

        # Official career page URLs for each source
        _source_urls = {
            "Canonical": "https://canonical.com/careers",
            "RedHat": "https://www.redhat.com/en/jobs",
            "SUSE": "https://www.suse.com/careers/",
            "NVIDIA": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
            "Ciena": "https://ciena.wd5.myworkdayjobs.com/Careers",
            "BlackBerry": "https://bb.wd3.myworkdayjobs.com/BlackBerry",
            "Alphawave": "https://alphawave.wd10.myworkdayjobs.com/Alphawave_External",
            "Solace": "https://solace.bamboohr.com/careers",
            "Fullscript": "https://jobs.lever.co/fullscript",
            "Amazon": "https://www.amazon.jobs/en-gb/job_categories/software-development",
            "Google": "https://careers.google.com/jobs/results/",
            "Mitel": "https://mitel.wd3.myworkdayjobs.com/mitelcareers",
            "MagnetForensics": "https://jobs.lever.co/magnetforensics",
            "Fortinet": "https://edel.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2001",
            "Telesat": "https://www.telesat.com/careers/",
            "TrendMicro": "https://trendmicro.wd3.myworkdayjobs.com/External",
            "Ranovus": "https://ranovus.bamboohr.com/careers",
            "Nokia": "https://jobs.nokia.com/en/sites/CX_1",
        }

        def _src_label(value, name):
            """Render a source checkbox with external link."""
            url = _source_urls.get(value, "")
            checked = ' checked' if value in ('Canonical', 'RedHat', 'Mitel') else ''
            link = f'<a href="{url}" target="_blank" class="src-link" title="Open {name} careers page">↗</a>' if url else ''
            return f'<label class="source-check"><input type="checkbox" class="src-cb" value="{value}"{checked}> {name} {link}</label>'

        html_body = f"""<h1>{h1_title}</h1>
        <div class="section">
            <div class="search-form">
                <div class="form-row">
                    <label>{kw_label}</label>
                    <input id="kw" value="ML Kernel Cloud AI" placeholder="ML, Kernel, Cloud...">
                </div>
                <div class="form-row">
                    <label>{loc_label}</label>
                    <input id="loc" value="" placeholder="Toronto, ON / Vancouver, BC / Montreal / Remote Canada...">
                </div>
                <div class="form-row sources-row">
                    <label>{src_label}</label>
                    <label class="source-check select-all-cb"><input type="checkbox" id="selectAllSrc" checked onchange="toggleAllSources(this.checked)"> {select_all}</label>
                    {_src_label('Canonical', 'Canonical')}
                    {_src_label('RedHat', 'Red Hat')}
                    {_src_label('SUSE', 'SUSE')}
                    {_src_label('NVIDIA', 'NVIDIA')}
                    {_src_label('Ciena', 'Ciena')}
                    {_src_label('BlackBerry', 'BlackBerry')}
                    {_src_label('Alphawave', 'Alphawave')}
                    {_src_label('Solace', 'Solace')}
                    {_src_label('Fullscript', 'Fullscript')}
                    {_src_label('Amazon', 'Amazon')}
                    {_src_label('Google', 'Google')}
                    {_src_label('Mitel', 'Mitel')}
                    {_src_label('MagnetForensics', 'MagnetForensics')}
                    {_src_label('Fortinet', 'Fortinet')}
                    {_src_label('Telesat', 'Telesat')}
                    {_src_label('TrendMicro', 'Trend Micro')}
                    {_src_label('Ranovus', 'Ranovus')}
                    {_src_label('Nokia', 'Nokia')}
                </div>
                <button onclick="runSearch()" class="btn btn-primary btn-lg" id="searchBtn">{btn_search}</button>
            </div>
            <div id="search-status" style="margin-top:12px"></div>
        </div>
        <div id="results"></div>
        
        <script>
        // i18n strings passed from Python
        var _searching = {json.dumps(searching_text, ensure_ascii=False)};
        var _src_prefix = {json.dumps(status_searching, ensure_ascii=False)};
        var _done_prefix = {json.dumps(status_done, ensure_ascii=False)};
        var _done_suffix = {json.dumps(status_done_end, ensure_ascii=False)};
        var _failed = {json.dumps(status_failed, ensure_ascii=False)};
        var _btn_search = {json.dumps(btn_search, ensure_ascii=False)};
        var _btn_search_again = {json.dumps(btn_search_again, ensure_ascii=False)};
        var _btn_save = {json.dumps(btn_save, ensure_ascii=False)};
        var _btn_letter = {json.dumps(btn_letter, ensure_ascii=False)};
        var _btn_view = {json.dumps(btn_view, ensure_ascii=False)};
        var _saved_text = {json.dumps(saved_text, ensure_ascii=False)};
        var _exists_text = {json.dumps(exists_text, ensure_ascii=False)};
        var _jobs_label = {json.dumps(jobs_label, ensure_ascii=False)};
        var _high_match = {json.dumps(high_match, ensure_ascii=False)};
        var _avg_match = {json.dumps(avg_match, ensure_ascii=False)};
        var _sr_h2 = {json.dumps(search_results_h2, ensure_ascii=False)};
        var _jl_h2 = {json.dumps(job_list_h2, ensure_ascii=False)};
        
        // Company logo/emoji mapping (from backend)
        var _companyLogos = {json.dumps(_build_logo_map(), ensure_ascii=False)};
        
        // Select all / deselect all sources
        function toggleAllSources(checked) {{
            var cbs = document.querySelectorAll('.src-cb');
            var val = checked ? true : false;
            for (var i = 0; i < cbs.length; i++) {{
                cbs[i].checked = val;
            }}
        }}
        function getCompanyLogo(name) {{
            if (!name) return '\U0001F3E2';
            var n = name.toLowerCase().trim();
            if (_companyLogos[n]) return _companyLogos[n];
            for (var k in _companyLogos) {{
                if (n.indexOf(k) >= 0) return _companyLogos[k];
            }}
            return '\U0001F3E2';
        }}

        var searchData = null;

        function renderResults(d) {{
            const results = document.getElementById('results');
            const status = document.getElementById('search-status');
            var h = '<div class="search-summary"><h2>' + _sr_h2 + '</h2>';
            h += '<div class="result-stats">';
            h += '<span>' + _jobs_label + ': ' + d.stats.total_jobs + '</span>';
            h += '<span>' + _high_match + ': ' + d.stats.high_match + '</span>';
            h += '<span>' + _avg_match + ': ' + d.stats.avg_match_score + '%</span>';
            h += '</div></div><h2>' + _jl_h2 + '</h2>';
            (d.jobs || []).forEach(function(job, i) {{
                var sc = job.match_score || 0;
                var cls = sc >= 70 ? 'score-high' : sc >= 40 ? 'score-medium' : 'score-low';
                var mark = sc >= 70 ? '🎯' : sc >= 40 ? '👍' : '📋';
                var desc = job.description || '';
                var shortDesc = desc.substring(0, 120);
                h += '<div class="job-card" id="card-' + i + '">';
                h += '<div class="job-header" onclick="toggleDesc(' + i + ')" style="cursor:pointer">';
                h += '<div class="job-title">' + mark + ' ' + (job.title || '') + ' ';
                    var types = (job.job_type || '').split(' ').filter(Boolean);
                    types.forEach(function(t) {{
                        h += '<span class="job-type-tag">' + t + '</span> ';
                    }});
                    h += '</div>';
                h += '<div class="job-score ' + cls + '">' + sc + '%</div></div>';
                h += '<div class="job-meta">';
                h += '<span>' + getCompanyLogo(job.company) + ' ' + (job.company || '') + '</span>';
                h += '<span>📍 ' + (job.location || '') + '</span>';
                h += '<span>📅 ' + String(job.date || '').substring(0, 10) + '</span>';
                h += '<span>📡 ' + (job.source || '') + '</span></div>';
                h += '<div class="job-desc" id="desc-' + i + '">' + shortDesc + '</div>';
                h += '<div class="job-desc-full" id="fulldesc-' + i + '" style="display:none">' + desc.replace(/\\n/g, '<br>') + '</div>';
                h += '<div class="job-actions">';
                if (job.url) h += '<a href="' + job.url + '" target="_blank" class="btn btn-small">' + _btn_view + '</a>';
                h += '<button onclick="saveJob(' + i + ')" class="btn btn-small btn-save" id="save-' + i + '">' + _btn_save + '</button>';
                h += '</div></div>';
            }});
            if (d.search_links && d.search_links.length) {{
                h += '<h2>' + _sr_h2 + '</h2>';
                d.search_links.forEach(function(lk) {{
                    h += '<div class="link-item"><div>' + lk.title + '</div>';
                    h += '<a href="' + lk.url + '" target="_blank" class="link-url">' + lk.url + '</a></div>';
                }});
            }}
            results.innerHTML = h;
            status.innerHTML = '<p>' + _done_prefix + d.stats.total_jobs + _done_suffix + '</p>';
        }}

        function loadCachedResults() {{
            var cached = sessionStorage.getItem('searchResults');
            if (cached) {{
                try {{
                    var d = JSON.parse(cached);
                    if (!d.jobs || d.jobs.length === 0) {{
                        sessionStorage.removeItem('searchResults');
                        return false;
                    }}
                    searchData = d;
                    renderResults(d);
                    document.getElementById('searchBtn').textContent = _btn_search_again;
                    return true;
                }} catch(e) {{}}
            }}
            return false;
        }}

        // When any individual source changes, update "select all" state
        document.querySelectorAll('.src-cb').forEach(function(cb) {{
            cb.addEventListener('change', function() {{
                var all = document.querySelectorAll('.src-cb');
                var allChecked = true;
                for (var i = 0; i < all.length; i++) {{
                    if (!all[i].checked) {{ allChecked = false; break; }}
                }}
                document.getElementById('selectAllSrc').checked = allChecked;
            }});
        }});

        async function runSearch() {{
            const btn = document.getElementById('searchBtn');
            const status = document.getElementById('search-status');
            const results = document.getElementById('results');
            const sources = [];
            document.querySelectorAll('.src-cb:checked').forEach(function(cb) {{ sources.push(cb.value); }});

            btn.disabled = true;
            btn.textContent = _searching;
            status.innerHTML = '<div class="loading"><div class="spinner"></div><p>' + _src_prefix + sources.join(', ') + '</p></div>';
            try {{
                const resp = await fetch('/api/run_search', {{
                    method:'POST',
                    headers:{{'Content-Type':'application/json'}},
                    body:JSON.stringify({{sources: sources, keywords: document.getElementById('kw').value, location: document.getElementById('loc').value}})
                }});
                const d = await resp.json();
                if (d.success) {{
                    searchData = d;
                    sessionStorage.setItem('searchResults', JSON.stringify(d));
                    renderResults(d);
                }} else {{
                    status.innerHTML = '<p class="error">' + _failed + (d.error || '') + '</p>';
                }}
            }} catch(e) {{
                status.innerHTML = '<p class="error">' + _failed + e + '</p>';
            }}
            btn.disabled = false;
            btn.textContent = _btn_search_again;
        }}
        
        // On page load, restore cached results if available
        loadCachedResults();
        function toggleDesc(i) {{
            var short = document.getElementById('desc-' + i);
            var full = document.getElementById('fulldesc-' + i);
            if (!full) return;
            if (full.style.display === 'none') {{
                full.style.display = 'block';
                short.style.display = 'none';
            }} else {{
                full.style.display = 'none';
                short.style.display = 'block';
            }}
        }}
        async function saveJob(i) {{
            if (!searchData || !searchData.jobs[i]) return;
            var resp = await fetch('/api/save_job', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job: searchData.jobs[i]}})}});
            var d = await resp.json();
            document.getElementById('save-' + i).textContent = d.success ? _saved_text : _exists_text;
            document.getElementById('save-' + i).disabled = true;
        }}
        // Debug: show JS errors on page
        window.onerror = function(msg, url, line, col, err) {{
            var status = document.getElementById('search-status');
            if (status) status.innerHTML = '<p class="error">JS Error: ' + msg + ' (line ' + line + ')</p>';
        }};
        </script>
        """
        html = self._page(h1_title, html_body, lang=lang)
        self._send_html(html)

    def handle_tracked_page(self, params):
        lang = self._get_lang(params)
        tracker = self.agent.tracker
        status_filter = params.get("status", "all")
        jobs = tracker.tracked_jobs
        if status_filter != "all":
            jobs = [j for j in jobs if j["status"] == status_filter]

        labels = {"saved": t(lang, 'saved'),"applied": t(lang, 'applied'),"interviewing": t(lang, 'interviewing'),"rejected": t(lang, 'rejected'),"offer": t(lang, 'offer')}
        btn_apply = t(lang, "btn_apply")
        btn_interview = t(lang, "btn_interview")
        btn_reject = t(lang, "btn_reject")
        btn_offer = t(lang, "btn_offer")
        btn_delete = t(lang, "btn_delete")

        tabs = ""
        for key, label in [("all",t(lang, 'all')),("saved",t(lang, 'saved')),("applied",t(lang, 'applied')),("interviewing",t(lang, 'interviewing')),("rejected",t(lang, 'rejected')),("offer",t(lang, 'offer'))]:
            cnt = len([j for j in tracker.tracked_jobs if key=="all" or j["status"]==key])
            active = "active" if status_filter == key else ""
            tabs += f'<a href="/tracked?status={key}&lang={lang}" class="tab {active}">{label} ({cnt})</a>'

        btn_view = t(lang, "btn_view")
        btn_letter = t(lang, "btn_letter")
        btn_add_job = t(lang, "btn_add_job")
        btn_preview = t(lang, "btn_preview")
        btn_edit = t(lang, "btn_edit")
        btn_fullscreen_edit = t(lang, "btn_fullscreen_edit")
        resume_preview_title = t(lang, "resume_preview_title")
        no_content = t(lang, "no_content")
        load_failed = t(lang, "load_failed")
        md_edit_placeholder = t(lang, "md_edit_placeholder")
        btn_optimize = t(lang, "btn_optimize")
        btn_link_resume = t(lang, "btn_link_resume")
        match_percent = t(lang, "match_percent")
        url_placeholder = t(lang, "url_placeholder")
        confirm_delete = t(lang, "confirm_delete")
        note_prompt = t(lang, "note_prompt")
        url_empty = t(lang, "url_empty")
        parse_failed = t(lang, "parse_failed")
        cover_letter_title_short = t(lang, "cover_letter_title_short")
        loading_text = t(lang, "loading")
        gap_modal_title = t(lang, "gap_modal_title")
        learn_plan_modal_title = t(lang, "learn_plan_modal_title")
        learn_plan_progress = t(lang, "learn_plan_progress")
        learn_plan_export = t(lang, "learn_plan_export")
        learn_plan_focus = t(lang, "learn_plan_focus")
        learn_plan_priority_high = t(lang, "learn_plan_priority_high")
        learn_plan_priority_mid = t(lang, "learn_plan_priority_mid")
        learn_plan_priority_low = t(lang, "learn_plan_priority_low")
        learn_plan_resource_type = t(lang, "learn_plan_resource_type")
        learn_plan_weekly = t(lang, "learn_plan_weekly")
        learn_plan_check_hint = t(lang, "learn_plan_check_hint")
        learn_plan_week = t(lang, "learn_plan_week")
        lang_sfx = {"en": "", "zh-CN": "\u5468", "fr": ""}
        learn_plan_suffix = lang_sfx.get(lang, "")
        learn_plan_hours = t(lang, "learn_plan_hours")
        learn_plan_projects = t(lang, "learn_plan_projects")
        learn_plan_skills = t(lang, "learn_plan_skills")
        learn_plan_advice = t(lang, "learn_plan_advice")
        btn_generate_plan = t(lang, "btn_generate_plan")
        btn_view_plan = t(lang, "btn_view_plan")
        learn_plan_empty = t(lang, "learn_plan_empty")
        btn_save = t(lang, "btn_save")
        btn_regenerate = t(lang, "btn_regenerate")
        btn_copy = t(lang, "btn_copy")
        def _fmt_time(iso_str):
            """格式化 ISO 时间戳为简短显示。"""
            if not iso_str:
                return ""
            try:
                d = datetime.datetime.fromisoformat(iso_str)
                now = datetime.datetime.now(d.tzinfo) if d.tzinfo else datetime.datetime.now()
                delta = now - d
                if delta < datetime.timedelta(hours=1):
                    mins = int(delta.total_seconds() / 60)
                    return t(lang, "just_now") if mins == 0 else t(lang, "time_m_ago").format(mins)
                elif delta < datetime.timedelta(days=1):
                    return t(lang, "time_h_ago").format(int(delta.total_seconds() / 3600))
                else:
                    return d.strftime("%m-%d %H:%M")
            except:
                return iso_str[:16] if iso_str else ""

        def _has_applied(j):
            """判断职位是否曾标记为 applied，依据 status_history 或 applied_date。"""
            if j.get("applied_date"):
                return True
            history = j.get("status_history") or []
            return any(h.get("status") == "applied" for h in history)

        def _render_timeline_detail(j):
            """渲染完整状态变更详情（展开后显示，含面试备注）。"""
            interviews = j.get("interviews") or []
            history = j.get("status_history") or []
            if not history and not interviews:
                return ""
            labels_map = {"saved": "📌", "applied": "📄", "interviewing": "💬", "rejected": "❌", "offer": "🎉"}
            rows = []
            for h in history:
                s = h.get("status", "")
                base_s = s.split("_")[0] if "interviewing" in s else s
                icon = labels_map.get(base_s, "●")
                label_text = labels.get(base_s, base_s)
                ft = _fmt_time(h["timestamp"])
                rows.append(f"<div class='tl-row'><span class='tl-icon'>{icon}</span><span class='tl-status'>{label_text}</span><span class='tl-time'>{ft}</span></div>")
            # 面试详情（含备注）
            if interviews:
                rows.append("<div class='tl-sep'>" + t(lang, "tl_interview_records") + "</div>")
                for iv in interviews:
                    ft = _fmt_time(iv["date"])
                    note = ("<span class='tl-note'>" + iv["notes"] + "</span>") if iv.get("notes") else ""
                    round_label = t(lang, "tl_round").format(iv['round'])
                    rows.append(f"<div class='tl-row'><span class='tl-icon'>💬</span><span class='tl-status'>{round_label}</span><span class='tl-time'>{ft}</span>{note}</div>")
            return "<div class='tl-container'>" + "".join(rows) + "</div>"

        def _render_status_timeline(j):
            """渲染状态变更时间线摘要。"""
            history = j.get("status_history") or []
            interviews = j.get("interviews") or []
            if len(history) < 2 and len(interviews) < 2:
                return ""
            labels_map = {"saved": "📌", "applied": "📄", "interviewing": "💬", "rejected": "❌", "offer": "🎉"}
            parts = []
            seen = set()
            for h in history:
                s = h.get("status", "")
                base_s = s.split("_")[0] if "interviewing" in s else s
                if base_s not in seen:
                    seen.add(base_s)
                    icon = labels_map.get(base_s, "●")
                    label_text = labels.get(base_s, base_s)
                    ft = _fmt_time(h["timestamp"])
                    parts.append(icon + " " + label_text + (" " + ft if ft else ""))
            if len(interviews) > 1:
                for iv in interviews[1:]:
                    icon = labels_map["interviewing"]
                    ft = _fmt_time(iv["date"])
                    note = (" \"" + iv["notes"] + "\"") if iv.get("notes") else ""
                    round_label = t(lang, "tl_round").format(iv['round'])
                    parts.append(f"{icon} {round_label}{note}{' '+ft if ft else ''}")
            if len(parts) > 4:
                parts = parts[-4:]
            return " → ".join(parts) if parts else ""

        saved_to_tracker = t(lang, "saved_to_tracker")
        applied_text = t(lang, "applied")
        tl_detail_text = t(lang, "tl_detail")
        tl_hide_text = t(lang, "tl_hide")
        jobs_html = ""
        if not jobs:
            jobs_html = f'<p class="empty">{t(lang, "no_tracked")}</p>'
        for j in jobs:
            label = labels.get(j["status"], j["status"])
            status_time = _fmt_time(j.get("last_updated"))
            has_applied = _has_applied(j)
            apply_btn_class = 'btn-save' if has_applied else 'btn-primary'
            apply_btn_text = applied_text if has_applied else btn_apply
            apply_time_str = _fmt_time(j.get("applied_date"))
            jobs_html += f"""
            <div class="job-card">
                <div class="job-header" onclick="toggleTrackedDesc('{j['id']}')" style="cursor:pointer">
                    <div class="job-title">{j['title']}{' <span class="job-type-tag">'+j['job_type']+'</span>' if j.get('job_type') else ''}</div>
                    <span class="status-tag status-{j['status']}">{label}{' <span class="status-time">'+status_time+'</span>' if status_time else ''}</span>
                </div>
                <div class="job-meta">
                    <span>{get_company_logo(j.get('company',''))} {j['company']}</span>
                    <span>📍 {j['location']}</span>
                    <span>📊 {j.get('match_score',0)}{match_percent}</span>
                    <span id="skill-gap-{j['id']}">{self._render_skill_gap_html(j, lang)}</span>
                </div>
                <div class="job-desc-toggle">
                    <div class="job-desc-snippet" id="tdesc-{j['id']}">{(j.get('description','') or '')[:150].replace(chr(10),' ')}</div>
                    <div class="job-desc-full" id="tfull-{j['id']}" style="display:none">{j.get('description','').replace(chr(10),'<br>').replace(chr(10)+'<br>','<br>')}</div>
                </div>
                {('<div class="job-timeline" id="ttl-sum-'+j['id']+'" onclick="event.stopPropagation();toggleTimelineDetail(\''+j['id']+'\')">' + _render_status_timeline(j) + ' <span class="tl-expand-hint">' + tl_detail_text + '</span></div>') if _render_status_timeline(j) else ''}
                {'<div class="job-timeline-detail" id="ttl-'+j['id']+'" style="display:none">' + _render_timeline_detail(j) + '</div>' if _render_timeline_detail(j) else ''}
                <div class="job-actions">
                    <a href="{j.get('url','#')}" target="_blank" class="btn btn-small">{btn_view}</a>
                    <button onclick="analyzeApply('{j['id']}')" class="btn btn-small {apply_btn_class}" id="apply-anal-btn-{j['id']}">{apply_btn_text}</button>
                    {'<span class="applied-time" title="' + j.get('applied_date','') + '">🕐 ' + apply_time_str + '</span>' if has_applied and apply_time_str else ''}
                    <button onclick="recordInterview('{j['id']}')" class="btn btn-small btn-interview">{btn_interview}</button>
                    <button onclick="upd('{j['id']}','rejected')" class="btn btn-small btn-reject">{btn_reject}</button>
                    <button onclick="upd('{j['id']}','offer')" class="btn btn-small btn-offer">{btn_offer}</button>
                    <button onclick="delJob('{j['id']}')" class="btn btn-small btn-delete">{btn_delete}</button>
                    <button class="btn btn-small cover-letter-btn" data-job-id="{j['id']}" style="font-size:12px">{btn_letter}</button>
                </div>
                {f'<div class="job-notes">📝 {j.get("notes","")}</div>' if j.get("notes") else ''}
                {('<div class="job-resume"><span class="resume-icon">📜</span> <span class="resume-name">'+j['resume_name']+'</span> <span class="resume-actions"><a href="#" class="link-url view-resume-btn" data-job-id="' + j['id'] + '">'+btn_preview+'</a> <a href="/resume_view?job_id='+j['id']+'" class="link-url" target="_blank">'+btn_edit+'</a> <button id="tailor-'+j['id']+'" onclick="tailorResume('+chr(39)+j['id']+chr(39)+')" class="btn btn-small" style="font-size:12px">'+btn_optimize+'</button></span></div>') if j.get('resume_id') else '<div class="job-resume"><button onclick="linkResume('+chr(39)+j['id']+chr(39)+')" class="btn btn-small" style="margin-top:6px">'+btn_link_resume+'</button></div>'}
            </div>"""

        html = self._page(t(lang, 'tracked_title'), f"""
        <h1>{t(lang, 'tracked_title')}</h1>
        <div class="section"><div class="tab-bar">{tabs}</div></div>
        <div class="section section-add-url" style="margin-top:8px;margin-bottom:8px;padding:8px 0;display:flex;gap:8px;align-items:center">
            <input id="manual-job-url" type="url" placeholder="{url_placeholder}" style="flex:1;padding:8px 10px;border:1px solid #ddd;border-radius:6px;font-size:14px">
            <button onclick="fetchAndAddJob()" class="btn btn-primary" id="manual-add-btn" style="padding:8px 16px">{btn_add_job}</button>
        </div>
        <div id="manual-add-status" style="margin-bottom:8px;font-size:14px"></div>
        <div id="tracked-list">{jobs_html}</div>
        <script>
        var _btn_add_job = {json.dumps(btn_add_job, ensure_ascii=False)};
        var _url_empty = {json.dumps(url_empty, ensure_ascii=False)};
        var _parse_failed = {json.dumps(parse_failed, ensure_ascii=False)};
        var _loading_text = {json.dumps(loading_text, ensure_ascii=False)};
        var _saved_to_tracker = {json.dumps(saved_to_tracker, ensure_ascii=False)};
        var _cover_letter_title_short = {json.dumps(cover_letter_title_short, ensure_ascii=False)};
        var _btn_save = {json.dumps(btn_save, ensure_ascii=False)};
        var _btn_regenerate = {json.dumps(btn_regenerate, ensure_ascii=False)};
        var _btn_copy = {json.dumps(btn_copy, ensure_ascii=False)};
        var _gap_modal_title = {json.dumps(gap_modal_title, ensure_ascii=False)};
        var _btn_generate_plan = {json.dumps(btn_generate_plan, ensure_ascii=False)};
        var _btn_view_plan = {json.dumps(btn_view_plan, ensure_ascii=False)};
        var _btn_edit = {json.dumps(btn_edit, ensure_ascii=False)};
        var _btn_fullscreen_edit = {json.dumps(btn_fullscreen_edit, ensure_ascii=False)};
        var _resume_preview_title = {json.dumps(resume_preview_title, ensure_ascii=False)};
        var _no_content = {json.dumps(no_content, ensure_ascii=False)};
        var _load_failed = {json.dumps(load_failed, ensure_ascii=False)};
        var _md_edit_placeholder = {json.dumps(md_edit_placeholder, ensure_ascii=False)};
        var _learn_plan_empty = {json.dumps(learn_plan_empty, ensure_ascii=False)};
        var _learn_plan_modal_title = {json.dumps(learn_plan_modal_title, ensure_ascii=False)};
        var _learn_plan_progress_label = {json.dumps(learn_plan_progress, ensure_ascii=False)};
        var _learn_plan_export = {json.dumps(learn_plan_export, ensure_ascii=False)};
        var _learn_plan_focus = {json.dumps(learn_plan_focus, ensure_ascii=False)};
        var _learn_plan_priority_high = {json.dumps(learn_plan_priority_high, ensure_ascii=False)};
        var _learn_plan_priority_mid = {json.dumps(learn_plan_priority_mid, ensure_ascii=False)};
        var _learn_plan_priority_low = {json.dumps(learn_plan_priority_low, ensure_ascii=False)};
        var _learn_plan_resource_type = {json.dumps(learn_plan_resource_type, ensure_ascii=False)};
        var _learn_plan_weekly = {json.dumps(learn_plan_weekly, ensure_ascii=False)};
        var _learn_plan_check_hint = {json.dumps(learn_plan_check_hint, ensure_ascii=False)};
        var _learn_plan_week = {json.dumps(learn_plan_week, ensure_ascii=False)};
        var _learn_plan_suffix = {json.dumps(learn_plan_suffix, ensure_ascii=False)};
        var _learn_plan_hours = {json.dumps(learn_plan_hours, ensure_ascii=False)};
        var _learn_plan_projects = {json.dumps(learn_plan_projects, ensure_ascii=False)};
        var _learn_plan_skills = {json.dumps(learn_plan_skills, ensure_ascii=False)};
        var _learn_plan_advice = {json.dumps(learn_plan_advice, ensure_ascii=False)};
        var _confirm_delete = {json.dumps(confirm_delete, ensure_ascii=False)};
        var _note_prompt = {json.dumps(note_prompt, ensure_ascii=False)};
        var _link_resume_title = {json.dumps(t(lang, 'link_resume_title'), ensure_ascii=False)};
        var _btn_assign = {json.dumps(t(lang, 'btn_assign'), ensure_ascii=False)};
        var _upload_new_resume = {json.dumps(t(lang, 'upload_new_resume'), ensure_ascii=False)};
        var _cancel = {json.dumps(t(lang, 'cancel'), ensure_ascii=False)};
        var _tl_detail = {json.dumps(tl_detail_text, ensure_ascii=False)};
        var _tl_hide = {json.dumps(tl_hide_text, ensure_ascii=False)};
        var _analyzing_text = {json.dumps(t(lang, "analyzing"), ensure_ascii=False)};
        var _apply_analysis = {json.dumps(t(lang, "apply_analysis"), ensure_ascii=False)};
        var _method_email = {json.dumps(t(lang, "method_email"), ensure_ascii=False)};
        var _method_manual = {json.dumps(t(lang, "method_manual"), ensure_ascii=False)};
        var _applied_btn = {json.dumps(t(lang, "applied_btn"), ensure_ascii=False)};
        var _next_steps = {json.dumps(t(lang, "next_steps"), ensure_ascii=False)};
        var _analysis_failed = {json.dumps(t(lang, "analysis_failed"), ensure_ascii=False)};
        var _analysis_error = {json.dumps(t(lang, "analysis_error"), ensure_ascii=False)};
        var _visit_company_site = {json.dumps(t(lang, "visit_company_site"), ensure_ascii=False)};
        var _auto_submit_prefix = {json.dumps(t(lang, "auto_submit_prefix"), ensure_ascii=False)};
        var _visit_prefix = {json.dumps(t(lang, "visit_prefix"), ensure_ascii=False)};
        var _site_apply_suffix = {json.dumps(t(lang, "site_apply_suffix"), ensure_ascii=False)};
        var _career_page_suffix = {json.dumps(t(lang, "career_page_suffix"), ensure_ascii=False)};
        var _search_prefix = {json.dumps(t(lang, "search_prefix"), ensure_ascii=False)};
        var _linkedin_suggestion = {json.dumps(t(lang, "linkedin_suggestion"), ensure_ascii=False)};
        var _prep_cover_resume = {json.dumps(t(lang, "prep_cover_resume"), ensure_ascii=False)};
        var _auto_fill_submit = {json.dumps(t(lang, "auto_fill_submit"), ensure_ascii=False)};
        var _result_logged = {json.dumps(t(lang, "result_logged"), ensure_ascii=False)};
        var _indeed_apply = {json.dumps(t(lang, "indeed_apply"), ensure_ascii=False)};
        var _or_visit_prefix = {json.dumps(t(lang, "or_visit_prefix"), ensure_ascii=False)};
        var _search_job_suffix = {json.dumps(t(lang, "search_job_suffix"), ensure_ascii=False)};
        var _upload_resume_cover = {json.dumps(t(lang, "upload_resume_cover"), ensure_ascii=False)};
        var _record_status = {json.dumps(t(lang, "record_status"), ensure_ascii=False)};
        var _gen_cover = {json.dumps(t(lang, "gen_cover"), ensure_ascii=False)};
        var _send_resume_email = {json.dumps(t(lang, "send_resume_email"), ensure_ascii=False)};
        var _wait_reply = {json.dumps(t(lang, "wait_reply"), ensure_ascii=False)};
        var _indeed_click_prefix = {json.dumps(t(lang, "indeed_click_prefix"), ensure_ascii=False)};
        var _indeed_method_header = {json.dumps(t(lang, "indeed_method_header"), ensure_ascii=False)};
        var _easy_apply = {json.dumps(t(lang, "easy_apply"), ensure_ascii=False)};
        var _apply_on_site_prefix = {json.dumps(t(lang, "apply_on_site_prefix"), ensure_ascii=False)};
        var _guessed_url = {json.dumps(t(lang, "guessed_url"), ensure_ascii=False)};
        var _desc_emails = {json.dumps(t(lang, "desc_emails"), ensure_ascii=False)};
        var _lang = {json.dumps(lang, ensure_ascii=False)};
        // Skill gap detail popup via event delegation
        document.addEventListener('click', function(e) {{
            var closeBtn = e.target.closest('.skill-gap-close-btn');
            if (closeBtn) {{
                var detailModal = closeBtn.closest('#skill-gap-detail-modal');
                if (detailModal) detailModal.remove();
                return;
            }}
            var lpCloseBtn = e.target.closest('.learn-plan-close-btn');
            if (lpCloseBtn) {{
                var lpModal = lpCloseBtn.closest('#learn-plan-modal');
                if (lpModal) lpModal.remove();
                return;
            }}
            // Learn plan regenerate button
            var regenBtn = e.target.closest('#btn-regen-plan');
            if (regenBtn) {{
                var regenModal = regenBtn.closest('#learn-plan-modal');
                if (!regenModal) return;
                var jobIdRegen = regenModal.getAttribute('data-learn-jobid');
                if (!jobIdRegen) return;
                var confirmMsg = _confirm_regen;
                if (!confirm(confirmMsg)) return;
                var regenBtnEl = document.querySelector('.learn-plan-btn[data-learn-jobid="' + jobIdRegen + '"]');
                if (regenBtnEl) {{ regenBtnEl.textContent = _loading_text; regenBtnEl.disabled = true; }}
                regenModal.remove();
                (function(jid, btnel) {{
                    fetch('/api/learn_plan', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id: jid, lang: _lang, regenerate: true}})}})
                    .then(function(r){{return r.json()}})
                    .then(function(d){{
                        if (!d.success) {{ alert(d.error || 'Regenerate failed'); return; }}
                        if (btnel) {{ btnel.textContent = _btn_view_plan; btnel.disabled = false; }}
                        renderLearnPlanModal(jid, d.plan, d.progress || {{}}, true);
                    }})
                    .catch(function(e){{
                        if (btnel) {{ btnel.textContent = _btn_view_plan; btnel.disabled = false; }}
                        alert('Regenerate failed: ' + e);
                    }});
                }})(jobIdRegen, regenBtnEl);
                return;
            }}
            var gapSpan = e.target.closest('.skill-gap-group');
            if (gapSpan) {{
                var jobIdGap = gapSpan.getAttribute('data-gap-jobid') || '';
                var detailsRaw = gapSpan.getAttribute('data-gap-details');
                if (!detailsRaw) return;
                try {{
                    var details = JSON.parse(detailsRaw);
                    // Remove existing detail modal
                    var old = document.getElementById('skill-gap-detail-modal');
                    if (old) old.remove();
                    var h = '<div id="skill-gap-detail-modal" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.35);z-index:1001;display:flex;align-items:center;justify-content:center" onclick="if(event.target===this)this.remove()">';
                    h += '<div style="background:#fff;border-radius:10px;padding:20px;max-width:450px;width:90%;box-shadow:0 4px 20px rgba(0,0,0,0.2);font-size:15px;line-height:1.6">';
                    h += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px"><h3 style="margin:0;font-size:15px">' + _gap_modal_title + '</h3><button class="skill-gap-close-btn" style="background:none;border:none;font-size:20px;cursor:pointer;color:#888">×</button></div>';
                    h += details;
                    h += '<div style="margin-top:12px;text-align:center" id="learn-btn-area-' + jobIdGap + '"><button class="btn btn-small btn-primary learn-plan-btn" data-learn-jobid="' + jobIdGap + '" style="font-size:12px">\U0001f4da ' + _loading_text + '</button></div>';
                    // Check if plan already exists
                    fetch('/api/learn_plan?job_id=' + encodeURIComponent(jobIdGap))
                    .then(function(r){{return r.json()}})
                    .then(function(d){{
                        var btnArea = document.getElementById('learn-btn-area-' + jobIdGap);
                        if (btnArea) {{
                            var btn = btnArea.querySelector('.learn-plan-btn');
                            if (btn) {{
                                btn.textContent = d.plan ? _btn_view_plan : _btn_generate_plan;
                            }}
                        }}
                    }});
                    h += '</div></div>';
                    document.body.insertAdjacentHTML('beforeend', h);
                }} catch(e) {{}}
            }}
            var learnBtn = e.target.closest('.learn-plan-btn');
            if (learnBtn) {{
                var jobIdLearn = learnBtn.getAttribute('data-learn-jobid');
                if (jobIdLearn) {{
                    showLearnPlan(jobIdLearn);
                }}
            }}
        }});
                    function showLearnPlan(jobId) {{
                var btnEl = document.querySelector('.learn-plan-btn[data-learn-jobid="' + jobId + '"]');
                if (btnEl) {{ btnEl.textContent = _loading_text; btnEl.disabled = true; }}
                // First try GET to load saved plan
                fetch('/api/learn_plan?job_id=' + encodeURIComponent(jobId) + '&lang=' + encodeURIComponent(_lang))
                .then(function(r){{return r.json()}})
                .then(function(initial){{
                    var plan = initial.plan;
                    var progress = initial.progress || {{}};
                    var isSaved = initial.saved;
                    if (!plan) {{
                        // No saved plan, generate one
                        return fetch('/api/learn_plan', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id: jobId, lang: _lang}})}})
                        .then(function(r){{return r.json()}})
                        .then(function(d){{
                            if (!d.success) {{ alert('\u751f\u6210\u5931\u8d25: ' + (d.error || '')); return null; }}
                            return {{plan: d.plan, progress: d.progress || {{}}, isSaved: true}};
                        }});
                    }}
                    return {{plan: plan, progress: progress, isSaved: isSaved}};
                }})
                .then(function(result){{
                    if (!result || !result.plan) return;
                    // Use different text: '查看' if plan was already saved, '生成' if freshly generated
                    if (btnEl) {{
                        btnEl.textContent = result.isSaved ? _btn_view_plan : _btn_generate_plan;
                        btnEl.disabled = false;
                    }}
                    renderLearnPlanModal(jobId, result.plan, result.progress, result.isSaved);
                }})
                .catch(function(e){{
                    if (btnEl) {{ btnEl.textContent = '\U0001f4da \u5b66\u4e60\u8ba1\u5212'; btnEl.disabled = false; }}
                    alert('\u8bf7\u6c42\u5931\u8d25: ' + e);
                }});
            }}

            function toggleLearnTask(jobId, taskId, cb) {{
                var done = cb.checked;
                fetch('/api/learn_plan_progress', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id: jobId, task_id: taskId, done: done}})}})
                .then(function(r){{return r.json()}})
                .then(function(d){{
                    if (!d.success) return;
                    // Update progress bar
                    var bar = document.getElementById('learn-progress-bar-' + jobId);
                    var txt = document.getElementById('learn-progress-txt-' + jobId);
                    if (bar && d.total > 0) {{ bar.style.width = Math.round(d.done / d.total * 100) + '%'; }}
                    if (txt) {{ txt.textContent = d.done + '/' + d.total; }}
                }});
            }}

                        function renderLearnPlanModal(jobId, plan, progress, isSaved) {{
                var oldModal = document.getElementById('learn-plan-modal');
                if (oldModal) oldModal.remove();
                // Count total tasks
                var totalTasks = 0;
                var doneTasks = 0;
                if (plan.weekly_plan) {{
                    plan.weekly_plan.forEach(function(w){{
                        if (w.tasks) {{ w.tasks.forEach(function(t,i){{
                            var tid;
                            if (typeof t === 'object' && t.day_of_week) {{
                                tid = 'w' + w.week + '_d' + t.day_of_week;
                            }} else {{
                                tid = 'w' + w.week + '_t' + i;
                            }}
                            totalTasks++;
                            if (progress[tid] && progress[tid].done) doneTasks++;
                        }});}}
                    }});
                }}
                var pct = totalTasks > 0 ? Math.round(doneTasks / totalTasks * 100) : 0;
                var h = '<div id="learn-plan-modal" data-learn-jobid="' + jobId + '" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.35);z-index:1002;display:flex;align-items:center;justify-content:center" onclick="if(event.target===this)this.remove()">';
                h += '<div style="background:#fff;border-radius:10px;padding:20px;max-width:630px;width:92%;max-height:88vh;overflow-y:auto;box-shadow:0 4px 20px rgba(0,0,0,0.2);font-size:15px;line-height:1.6">';
                h += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">';
                h += '<h3 style="margin:0;font-size:15px">' + _learn_plan_modal_title + '</h3>';
                h += '<button class="learn-plan-close-btn" style="background:none;border:none;font-size:20px;cursor:pointer;color:#888">\u00d7</button></div>';

                // Progress bar
                if (totalTasks > 0) {{
                    h += '<div style="margin-bottom:10px">';
                    h += '<div style="display:flex;justify-content:space-between;font-size:13px;color:#666;margin-bottom:2px">';
                    h += '<span>' + _learn_plan_progress_label + '</span><span id="learn-progress-txt-' + jobId + '">' + doneTasks + '/' + totalTasks + '</span></div>';
                    h += '<div style="background:#e0e0e0;border-radius:4px;height:8px;overflow:hidden">';
                    h += '<div id="learn-progress-bar-' + jobId + '" style="background:#4caf50;height:8px;width:' + pct + '%;border-radius:4px;transition:width 0.3s"></div></div></div>';
                }}

                // Action buttons: ical export + regenerate
                h += '<div style="margin-bottom:10px;display:flex;gap:6px">';
                h += '<a href="/api/learn_plan_ical?job_id=' + encodeURIComponent(jobId) + '" download class="btn btn-small" style="font-size:11px;text-decoration:none">' + _learn_plan_export + '</a>';
                if (isSaved) {{
                    h += '<button id="btn-regen-plan" class="btn btn-small" style="font-size:11px;background:#ff9800;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer">' + _btn_regenerate + '</button>';
                }}
                h += '</div>';

                // Focus skills
                if (plan.focus_skills) {{
                    h += '<div style="margin-bottom:10px"><b>' + _learn_plan_focus + '</b></div>';
                    plan.focus_skills.forEach(function(s) {{
                        var priColor = s.priority === _learn_plan_priority_high ? '#d32f2f' : s.priority === _learn_plan_priority_mid ? '#e65100' : '#1565c0';
                        h += '<div style="background:#f8f9fa;border-radius:6px;padding:8px;margin-bottom:6px">';
                        h += '<div style="display:flex;justify-content:space-between;align-items:center"><b>' + (s.skill || '') + '</b> <span style="font-size:12px;color:' + priColor + ';font-weight:500">' + s.priority + '</span></div>';
                        h += '<div style="color:#555;font-size:14px;margin:4px 0">' + (s.reason || '') + '</div>';
                        if (s.resources) {{
                            s.resources.forEach(function(rsc) {{
                                var rscLink = rsc.url || 'https://www.google.com/search?q=' + encodeURIComponent(rsc.title || s.skill);
                                var rscUrl = '<a href="' + rscLink + '" target="_blank" style="margin-left:4px;font-size:11px;color:#1a73e8">\U0001f517</a>';
                                h += '<div style="font-size:11px;margin:2px 0;padding-left:8px">\u2022 <b>[' + (rsc.type || _learn_plan_resource_type) + ']</b> ' + (rsc.title || '') + (rsc.estimated_hours ? ' (' + rsc.estimated_hours + 'h)' : '') + rscUrl + '</div>';
                            }});
                        }}
                        h += '</div>';
                    }});
                }}

                // Weekly plan with checkboxes
                if (plan.weekly_plan) {{
                    h += '<div style="margin-top:10px"><b>' + _learn_plan_weekly + '</b> <span style="font-size:12px;color:#888">' + _learn_plan_check_hint + '</span></div>';
                    plan.weekly_plan.forEach(function(w) {{
                        h += '<div style="background:#fff8e1;border-radius:6px;padding:8px;margin-bottom:6px">';
                        h += '<div style="font-weight:500">' + _learn_plan_week + ' ' + w.week + _learn_plan_suffix + ': ' + (w.focus || '') + ' <span style="color:#888;font-size:11px">(\uff5e' + (w.estimated_hours || '') + '' + _learn_plan_hours + ')</span></div>';
                        if (w.tasks) {{
                            w.tasks.forEach(function(t, tIdx) {{
                                var tid;
                                if (typeof t === 'object' && t.day_of_week) {{
                                    tid = 'w' + w.week + '_d' + t.day_of_week;
                                }} else {{
                                    tid = 'w' + w.week + '_t' + tIdx;
                                }}
                                var done = progress[tid] && progress[tid].done;
                                var taskName = (typeof t === 'string') ? t : (t.name || '');
                                var taskTip = (typeof t === 'object' && t.advice) ? t.advice : (progress[tid] && progress[tid].advice ? progress[tid].advice : plan.advice || '');
                                h += '<div style="font-size:14px;padding:2px 0 2px 4px">';
                                h += '<input type="checkbox" class="learn-task-cb" data-jobid="' + jobId + '" data-taskid="' + tid + '" ' + (done ? 'checked' : '') + ' style="vertical-align:middle;margin-right:4px"> ';
                                h += '<span style="' + (done ? 'text-decoration:line-through;color:#888' : '') + '" title="' + (taskTip ? taskTip.replace(/"/g,'&quot;') : '') + '">' + taskName + '</span>';
                                h += '</div>';
                            }});
                        }}
                        h += '</div>';
                    }});
                }}

                // Projects
                if (plan.projects) {{
                    h += '<div style="margin-top:10px"><b>' + _learn_plan_projects + '</b></div>';
                    plan.projects.forEach(function(p) {{
                        h += '<div style="background:#e3f2fd;border-radius:6px;padding:8px;margin-bottom:6px">';
                        h += '<div style="font-weight:500">' + (p.name || '') + '</div>';
                        h += '<div style="font-size:14px;color:#555">' + (p.description || '') + '</div>';
                        if (p.skills) {{
                            h += '<div style="font-size:12px;color:#1565c0;margin-top:4px">\u2022 ' + _learn_plan_skills + ': ' + p.skills.join(', ') + '</div>';
                        }}
                        h += '</div>';
                    }});
                }}

                // Advice
                if (plan.advice) {{
                    h += '<div style="margin-top:10px;background:#f3e8ff;border-radius:6px;padding:10px;color:#6a1b9a">';
                    h += '<b>' + _learn_plan_advice + '</b><br>' + plan.advice;
                    h += '</div>';
                }}
                h += '</div></div>';
                document.body.insertAdjacentHTML('beforeend', h);

                // Attach checkbox change handlers
                document.querySelectorAll('.learn-task-cb').forEach(function(cb) {{
                    cb.addEventListener('change', function() {{
                        toggleLearnTask(this.getAttribute('data-jobid'), this.getAttribute('data-taskid'), this);
                        // Toggle strikethrough
                        var span = this.nextElementSibling;
                        if (span) {{
                            if (this.checked) {{ span.style.textDecoration = 'line-through'; span.style.color = '#888'; }}
                            else {{ span.style.textDecoration = 'none'; span.style.color = ''; }}
                        }}
                    }});
                }});
            }}
        function closeApplyModal() {{
            var el = document.getElementById('apply-analysis-modal');
            if (el) el.remove();
        }}
        var ANALYZING_TEXT = _analyzing_text;
        var APPLY_TEXT = '\u7533\u8bf7';
        var RECORDED_TEXT = '\u2705 \u5df2\u8bb0\u5f55';

        // Auto-analyze skill gaps for jobs with linked resume but no analysis
        (function() {{
            var els = document.querySelectorAll('[id^="skill-gap-"]');
            for (var i = 0; i < els.length; i++) {{
                (function(el) {{
                    if (!el.textContent.trim()) {{
                        var jobId = el.id.replace('skill-gap-', '');
                        fetch('/api/analyze_skill_gap', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id: jobId, lang: _lang}})}})
                        .then(function(r){{return r.json()}})
                        .then(function(d){{ if (d.success && d.html) {{ el.innerHTML = d.html; }}}});
                    }}
                }})(els[i]);
            }}
        }})();

        async function delJob(id) {{
            if (!confirm(_confirm_delete)) return;
            await fetch('/api/delete_job', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id:id}})}});
            location.reload();
        }}
        function toggleTrackedDesc(id) {{
            var short = document.getElementById('tdesc-' + id);
            var full = document.getElementById('tfull-' + id);
            if (!full) return;
            if (full.style.display === 'none') {{
                full.style.display = 'block';
                short.style.display = 'none';
            }} else {{
                full.style.display = 'none';
                short.style.display = 'block';
            }}
        }}
        function toggleTimelineDetail(id) {{
            var el = document.getElementById('ttl-' + id);
            var sum = document.getElementById('ttl-sum-' + id);
            if (!el || !sum) return;
            if (el.style.display === 'none') {{
                el.style.display = 'block';
                sum.innerHTML = sum.innerHTML.replace(_tl_detail, _tl_hide);
            }} else {{
                el.style.display = 'none';
                sum.innerHTML = sum.innerHTML.replace(_tl_hide, _tl_detail);
            }}
        }}
        async function upd(id, st) {{
            var notes = prompt(_note_prompt,'')||'';
            await fetch('/api/update_status', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id:id, status:st, notes:notes}})}});
            location.reload();
        }}
        function quickApply(jobId) {{
            var notes = prompt('\u6dfb\u52a0\u5907\u6ce8\uff08\u53ef\u9009\uff09:','')||'';
            fetch('/api/update_status', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id:jobId, status:'applied', notes:notes}})}})
            .then(function() {{ location.reload(); }});
        }}
        async function recordInterview(jobId) {{
            var _interview_note_prompt = {json.dumps(t(lang, 'interview_note_prompt'), ensure_ascii=False)};
            var notes = prompt(_interview_note_prompt,'')||'';
            await fetch('/api/update_status', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id:jobId, status:'interviewing', notes:notes}})}});
            location.reload();
        }}

        // ===== Manual URL Job Addition =====
        async function fetchAndAddJob() {{
            var url = document.getElementById('manual-job-url').value.trim();
            if (!url) {{ alert(_url_empty); return; }}
            var btn = document.getElementById('manual-add-btn');
            var status = document.getElementById('manual-add-status');
            btn.disabled = true;
            btn.textContent = '⏳ ' + _loading_text;
            status.innerHTML = '<span style="color:#888">' + _loading_text + '</span>';
            try {{
                var r = await fetch('/api/fetch_job_from_url', {{
                    method:'POST', headers:{{'Content-Type':'application/json'}},
                    body:JSON.stringify({{url:url}})
                }});
                var d = await r.json();
                if (!d.success) {{
                    status.innerHTML = '<span style="color:#d32f2f">❌ ' + (d.error || _parse_failed) + '</span>';
                    btn.disabled = false;
                    btn.textContent = _btn_add_job;
                    return;
                }}
                var job = d.job;
                status.innerHTML = '<div style="background:#e8f5e9;border:1px solid #a5d6a7;border-radius:8px;padding:12px">' +
                    '<div style="display:flex;justify-content:space-between;align-items:start">' +
                    '<div><b>' + escHtml(job.title) + '</b>' +
                    (job.company ? ' <span style="color:#666">at ' + escHtml(job.company) + '</span>' : '') +
                    (job.location ? ' <span style="color:#888;font-size:13px">📍 ' + escHtml(job.location) + '</span>' : '') +
                    '<br><span style="font-size:13px;color:#888">📊 匹配度: ' + (job.match_score || 0) + '%</span></div>' +
                    '<button onclick="saveFetchedJob(' + JSON.stringify(job).replace(/"/g, '&quot;') + ')" class="btn btn-primary btn-small" style="padding:6px 14px;flex-shrink:0">💾 保存</button></div>' +
                    '</div>';
                btn.disabled = false;
                btn.textContent = _btn_add_job;
            }} catch(e) {{
                status.innerHTML = '<span style="color:#d32f2f">❌ 请求失败: ' + e + '</span>';
                btn.disabled = false;
                btn.textContent = _btn_add_job;
            }}
        }}

        function saveFetchedJob(job) {{
            fetch('/api/save_job', {{
                method:'POST', headers:{{'Content-Type':'application/json'}},
                body:JSON.stringify({{job: job}})
            }})
            .then(function(r){{return r.json()}})
            .then(function(d){{
                if (d.success) {{
                    document.getElementById('manual-add-status').innerHTML = '<span style="color:#2e7d32">' + _saved_to_tracker + '</span>';
                    setTimeout(function(){{ location.reload(); }}, 1500);
                }} else {{
                    alert(d.error || '保存失败');
                    if (d.error && d.error.indexOf('已保存') >= 0) {{
                        setTimeout(function(){{ location.reload(); }}, 1000);
                    }}
                }}
            }});
        }}

        function escHtml(s) {{
            if (!s) return '';
            return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
        }}

        // ===== Apply Analysis =====
        async function analyzeApply(jobId) {{
            var old = document.getElementById('apply-analysis-modal');
            if (old) old.remove();

            var btn = document.getElementById('apply-anal-btn-' + jobId);
            var origText = null;
            if (btn && !btn.disabled) {{
                origText = btn.textContent;
                btn.textContent = ANALYZING_TEXT;
                btn.disabled = true;
            }}

            try {{
                var r = await fetch('/api/analyze_apply', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id: jobId}})}});
                var d = await r.json();
                if (!d.success) {{ alert(_analysis_failed + ': ' + (d.error || '')); return; }}
                // i18n post-process: replace known Chinese instruction templates
                if (d.analysis) {{
                    d.analysis.instructions = d.analysis.instructions
                        .replace('请自行前往公司官网或求职平台投递', _visit_company_site)
                        .replace('一键投递至', _auto_submit_prefix + ' ')
                        .replace('（Lever 自动表单）', '')
                        .replace('前往 ', _visit_prefix + ' ')
                        .replace(' 官网提交申请', _site_apply_suffix)
                        .replace(' 官网查找 Careers 页面', _career_page_suffix);
                    if (d.analysis.next_steps) {{
                        d.analysis.next_steps = d.analysis.next_steps.map(function(s) {{
                            return s
                                .replace('请自行前往公司官网或求职平台投递', _visit_company_site)
                                .replace('搜索 ', _search_prefix + ' ')
                                .replace(' 官网查找 Careers 页面', _career_page_suffix)
                                .replace('或通过 LinkedIn 找到招聘负责人联系', _linkedin_suggestion)
                                .replace('准备求职信和简历', _prep_cover_resume)
                                .replace('一键投递至', _auto_submit_prefix)
                                .replace('系统自动填写表单并提交', _auto_fill_submit)
                                .replace('投递结果会记录到申请历史', _result_logged)
                                .replace('打开 Indeed 页面，点击 "Apply on Company Site"', _indeed_apply)
                                .replace('或直接前往 ', _or_visit_prefix)
                                .replace(' 搜索职位', _search_job_suffix)
                                .replace('上传定制简历和求职信', _upload_resume_cover)
                                .replace('返回系统记录申请状态', _record_status)
                                .replace('生成求职信', _gen_cover)
                                .replace('发送简历到指定邮箱', _send_resume_email)
                                .replace('等待对方回复', _wait_reply)
                                .replace('打开 Indeed 页面，点击', _indeed_click_prefix);
                        }});
                    }}
                    if (d.analysis.details) {{
                        d.analysis.details = d.analysis.details
                            .replace('Indeed 申请方式', _indeed_method_header)
                            .replace('Easy Apply — 通过 Indeed 直接投递', _easy_apply)
                            .replace('Apply on Company Site — 前往 ', _apply_on_site_prefix)
                            .replace(' 官网', '')
                            .replace('猜测的招聘页', _guessed_url)
                            .replace('描述中邮箱', _desc_emails);
                    }}
                }}
                showApplyAnalysis(jobId, d.analysis, d.job);
            }} catch(e) {{
                alert(_analysis_error + ': ' + e);
            }} finally {{
                if (btn && origText !== null) {{ btn.textContent = origText; btn.disabled = false; }}
            }}
        }}

        function showApplyAnalysis(jobId, analysis, jobInfo) {{
            var h = '<div id="apply-analysis-modal" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:1000;display:flex;align-items:center;justify-content:center">';
            h += '<div style="background:#fff;border-radius:12px;padding:0;max-width:560px;width:95%;box-shadow:0 8px 32px rgba(0,0,0,0.2);display:flex;flex-direction:column;max-height:80vh">';

            // Title
            h += '<div style="display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-bottom:1px solid #e0e0e0;flex-shrink:0">';
            h += '<h3 style="margin:0;font-size:16px">' + _apply_analysis + '</h3>';
            h += '<button style="background:none;border:none;font-size:20px;cursor:pointer;color:#888;padding:4px;line-height:1" onclick="closeApplyModal()">\u00d7</button>';
            h += '</div>';

            // Content
            h += '<div style="overflow-y:auto;padding:20px;flex:1">';

            // Job info
            h += '<div style="margin-bottom:14px">';
            h += '<div style="font-weight:600;font-size:15px">' + jobInfo.title + '</div>';
            h += '<div style="color:#666;font-size:13px">' + jobInfo.company + ' \u00b7 ' + jobInfo.source + '</div>';
            h += '</div>';

            // Method badge
            var method = analysis.method;
            var methodLabel = method === 'email' ? _method_email : _method_manual;
            h += '<div style="margin-bottom:12px;padding:8px 12px;border-radius:6px;background:' + (method === 'email' ? '#e8f0fe' : '#fef7e0') + ';font-size:13px">';
            h += '<strong>' + methodLabel + '</strong>: ' + analysis.instructions;
            h += '</div>';

            // Details
            if (analysis.details) {{
                h += '<div style="margin-bottom:12px;padding:8px 12px;background:#f5f5f5;border-radius:6px;font-size:13px;line-height:1.6;white-space:pre-wrap">';
                h += analysis.details;
                h += '</div>';
            }}

            // Next steps
            if (analysis.next_steps && analysis.next_steps.length > 0) {{
                h += '<div style="margin-bottom:12px">';
                h += '<div style="font-weight:600;font-size:14px;margin-bottom:6px">' + _next_steps + '</div>';
                h += '<ol style="margin:0;padding-left:20px;font-size:13px;line-height:1.8">';
                analysis.next_steps.forEach(function(s) {{
                    h += '<li>' + s + '</li>';
                }});
                h += '</ol></div>';
            }}

            h += '</div>';  // end scroll content

            // Footer buttons
            h += '<div style="display:flex;justify-content:flex-end;gap:8px;padding:12px 20px;border-top:1px solid #e0e0e0;flex-shrink:0">';
            h += '<button class="btn" onclick="closeApplyModal()">' + _cancel + '</button>';
            var recordBtnId = 'apply-rec-' + jobId;
            h += '<button class="btn btn-primary" id="' + recordBtnId + '">' + _applied_btn + '</button>';
            h += '</div>';

            h += '</div></div>';
            document.body.insertAdjacentHTML('beforeend', h);
            // Delegate click on the "\u5df2\u7533\u8bf7" button
            setTimeout(function() {{
                var b = document.getElementById(recordBtnId);
                if (b) b.onclick = function() {{ recordManualApply(jobId); }};
            }}, 0);
        }}

        async function recordManualApply(jobId) {{
            try {{
                var r = await fetch('/api/record_apply', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id: jobId}})}});
                var d = await r.json();
                if (d.success) {{
                    var modal = document.getElementById('apply-analysis-modal');
                    if (modal) modal.remove();
                    // Update button to show applied
                    var btn = document.getElementById('apply-anal-btn-' + jobId);
                    if (btn) {{
                        btn.textContent = RECORDED_TEXT;
                        btn.disabled = true;
                        btn.style.backgroundColor = '#e6f4ea';
                        btn.style.color = '#34a853';
                        btn.style.border = '1px solid #34a853';
                        btn.className = 'btn btn-small';
                    }}
                }} else {{
                    alert(_analysis_failed + ': ' + (d.error || ''));
                }}
            }} catch(e) {{
                alert(_analysis_error + ': ' + e);
            }}
        }}
        function tailorResume(jobId) {{
            var btn = document.getElementById('tailor-' + jobId);
            if (btn) {{ btn.textContent = '⏳ ' + _quiz_generating + ''; btn.disabled = true; }}
            fetch('/api/tailor_resume', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id: jobId}})}})
            .then(function(r){{return r.json()}})
            .then(function(d){{
                if (btn) {{ btn.textContent = _btn_optimize; btn.disabled = false; }}
                if (d.success) {{
                    window.open('/resume_view?job_id=' + jobId, '_blank');
                }} else {{
                    alert(_analysis_failed + ': ' + (d.error || ''));
                }}
            }})
            .catch(function(e){{
                if (btn) {{ btn.textContent = _btn_optimize; btn.disabled = false; }}
                alert(_analysis_error + ': ' + e);
            }});
        }}
        function analyzeSkillGap(jobId) {{
            fetch('/api/analyze_skill_gap', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id: jobId, lang: _lang}})}})
            .then(function(r){{return r.json()}})
            .then(function(d){{
                if (d.success) {{
                    var el = document.getElementById('skill-gap-' + jobId);
                    if (el) {{ el.outerHTML = d.html; }}
                }}
            }})
            .catch(function(e){{}});
        }}
        function closeResumeModal() {{
            var el = document.getElementById('resume-modal-overlay');
            if (el) el.remove();
        }}
        function linkResume(jobId) {{
            var old = document.getElementById('resume-modal-overlay');
            if (old) old.remove();
            fetch('/api/list_resumes').then(function(r){{return r.json()}}).then(function(data){{
                var list = data.success ? data.resumes : [];
                var h = '<div id=\"resume-modal-overlay\" style=\"position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:1000;display:flex;align-items:center;justify-content:center\">';
                h += '<div style=\"background:#fff;border-radius:12px;padding:24px;max-width:500px;width:90%;max-height:80vh;overflow-y:auto\">';
                h += '<h3 style=\"margin-bottom:12px\">' + _link_resume_title + '</h3>';
                if (list.length > 0) {{
                    list.forEach(function(r){{
                        h += '<div style=\"display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid #eee\">';
                        h += '<span>\U0001f4c4 ' + r.name + '</span>';
                        h += '<button onclick=\"assignResume(\\'' + jobId + '\\',\\'' + r.id + '\\')\" class=\"btn btn-small\">' + _btn_assign + '</button>';
                        h += '</div>';
                    }});
                    h += '<hr style=\"margin:12px 0\">';
                }}
                h += '<div><button onclick=\"uploadNewResumeAndLink(\\'' + jobId + '\\')\" class=\"btn\" style=\"width:100%\">' + _upload_new_resume + '</button></div>';
                h += '<div style=\"margin-top:12px;text-align:right\"><button onclick=\"closeResumeModal()\" class=\"btn btn-small\">' + _cancel + '</button></div>';
                h += '</div></div>';
                document.body.insertAdjacentHTML('beforeend', h);
            }});
        }}
        async function assignResume(jobId, resumeId) {{
            closeResumeModal();
            try {{
                var r = await fetch('/api/assign_resume', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id:jobId, resume_id:resumeId}})}});
                var d = await r.json();
                if (d.success) {{ 
                    location.reload();
                }} else {{ alert(_parse_failed + ': ' + (d.error || '')); }}
            }} catch(e) {{ alert(_parse_failed + ': ' + e); }}
        }}
        async function uploadNewResumeAndLink(jobId) {{
            var input = document.createElement('input');
            input.type = 'file';
            input.accept = '.pdf,.doc,.docx';
            input.style.display = 'none';
            document.body.appendChild(input);
            input.onchange = async function(e) {{
                closeResumeModal();
                var file = e.target.files[0];
                if (!file) {{ document.body.removeChild(input); return; }}
                var formData = new FormData();
                formData.append('name', file.name);
                formData.append('resume', file);
                try {{
                    var r1 = await fetch('/api/add_resume_multipart', {{method:'POST', body:formData}});
                    var d1 = await r1.json();
                    if (!d1.success) {{ alert(_parse_failed + ': ' + (d1.error || '')); document.body.removeChild(input); return; }}
                    var r2 = await fetch('/api/assign_resume', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id:jobId, resume_id:d1.resume.id}})}});
                    var d2 = await r2.json();
                    if (!d2.success) {{ alert('\u5173\u8054\u5931\u8d25'); document.body.removeChild(input); return; }}
                    document.body.removeChild(input);
                    location.reload();
                }} catch(e) {{
                    alert('\u4e0a\u4f20\u51fa\u9519: ' + e);
                    console.error('linkupload error', e);
                }}
            }};
            input.click();
        }}

        // Cover letter modal: click delegation
        document.addEventListener('click', function(e) {{
            var btn = e.target.closest('.cover-letter-btn');
            if (!btn) return;
            var jobId = btn.getAttribute('data-job-id');
            showCoverLetterModal(jobId);
        }});

        function showCoverLetterModal(jobId) {{
            var old = document.getElementById('cover-letter-modal');
            if (old) old.remove();

            var modal = document.createElement('div');
            modal.id = 'cover-letter-modal';
            modal.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.35);z-index:1002;display:flex;align-items:center;justify-content:center';
            modal.onclick = function(ev) {{ if (ev.target === this) this.remove(); }};

            var inner = document.createElement('div');
            inner.style.cssText = 'background:rgba(255,255,255,0.95);backdrop-filter:blur(8px);border-radius:12px;padding:20px;max-width:600px;width:90%;max-height:80vh;box-shadow:0 4px 20px rgba(0,0,0,0.2);font-size:14px;line-height:1.6;display:flex;flex-direction:column';

            inner.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px"><h3 style="margin:0;font-size:15px">' + _cover_letter_title_short + '</h3><button class="cl-close-btn" style="background:none;border:none;font-size:20px;cursor:pointer;color:#888">×</button></div><textarea class="cl-textarea" style="width:100%;min-height:300px;flex:1;border:1px solid #ddd;border-radius:6px;padding:10px;font-size:13px;line-height:1.6;resize:vertical;font-family:inherit" readonly>' + _loading_text + '</textarea><div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end"><button class="cl-save-btn btn btn-small btn-primary" style="font-size:12px">' + _btn_save + '</button><button class="cl-regenerate-btn btn btn-small" style="font-size:12px">' + _btn_regenerate + '</button><button class="cl-copy-btn btn btn-small" style="font-size:12px">' + _btn_copy + '</button></div>';

            modal.appendChild(inner);
            document.body.appendChild(modal);

            var textarea = inner.querySelector('.cl-textarea');
            var saveBtn = inner.querySelector('.cl-save-btn');
            var regenBtn = inner.querySelector('.cl-regenerate-btn');
            var copyBtn = inner.querySelector('.cl-copy-btn');
            var closeBtn = inner.querySelector('.cl-close-btn');

            closeBtn.onclick = function() {{ modal.remove(); }};

            function loadLetter(isRegen) {{
                var url = '/api/get_cover_letter?job_id=' + encodeURIComponent(jobId);
                if (isRegen) url += '&regen=1';
                fetch(url)
                .then(function(r){{ return r.json(); }})
                .then(function(d) {{
                    if (d.success && d.letter) {{
                        textarea.value = d.letter;
                        textarea.readOnly = false;
                    }} else {{
                        textarea.value = '(生成失败: ' + (d.error || '') + ')';
                    }}
                }})
                .catch(function(e) {{
                    textarea.value = '请求失败: ' + e;
                }});
            }}
            loadLetter(false);

            saveBtn.onclick = function() {{
                fetch('/api/save_cover_letter', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{job_id: jobId, letter: textarea.value}})
                }})
                .then(function(r){{ return r.json(); }})
                .then(function(d) {{
                    if (d.success) {{
                        saveBtn.textContent = '✅ ' + _btn_save;
                        setTimeout(function(){{ saveBtn.textContent = _btn_save; }}, 2000);
                    }} else {{
                        alert(_parse_failed + ': ' + (d.error || ''));
                    }}
                }});
            }};

            regenBtn.onclick = function() {{
                textarea.value = _loading_text;
                textarea.readOnly = true;
                loadLetter(true);
            }};

            copyBtn.onclick = function() {{
                navigator.clipboard.writeText(textarea.value).then(function() {{
                    copyBtn.textContent = '✅ ' + _btn_copy;
                    setTimeout(function(){{ copyBtn.textContent = _btn_copy; }}, 2000);
                }});
            }};
        }}
        </script>
        """, lang=lang)
        html += self._tracked_resume_modal_html(lang)
        self._send_html(html)

    def handle_learn_calendar_page(self, params):
        lang = self._get_lang(params)
        jobs = self.agent.tracker.tracked_jobs
        learn_plan_week = t(lang, "learn_plan_week")
        lang_sfx = {"en": "", "zh-CN": "周", "fr": ""}
        learn_plan_suffix = lang_sfx.get(lang, "")
        cal_month_names = t(lang, "cal_month_names")
        cal_weekday_labels = t(lang, "cal_weekday_labels")
        cal_modal_resources = t(lang, "cal_modal_resources")
        cal_modal_projects = t(lang, "cal_modal_projects")
        cal_modal_advice = t(lang, "cal_modal_advice")
        week_focus_tpl = t(lang, "week_focus")
        cal_title = t(lang, "learn_plan_modal_title")
        cal_empty = t(lang, "learn_plan_empty")
        tasks_completed = t(lang, "tasks_completed")
        quiz_section_title = t(lang, "quiz_section_title")
        quiz_generating = t(lang, "quiz_generating")
        quiz_submit = t(lang, "quiz_submit")
        quiz_reset = t(lang, "quiz_reset")
        quiz_answer_placeholder = t(lang, "quiz_answer_placeholder")
        quiz_hint_submit_to_check = t(lang, "quiz_hint_submit_to_check")
        quiz_result_title = t(lang, "quiz_result_title")
        quiz_correct = t(lang, "quiz_correct")
        quiz_question_prefix = t(lang, "quiz_question_prefix")
        quiz_you_answered = t(lang, "quiz_you_answered")
        quiz_correct_answer = t(lang, "quiz_correct_answer")
        quiz_essay_title = t(lang, "quiz_essay_title")
        quiz_your_answer = t(lang, "quiz_your_answer")
        quiz_reference_answer = t(lang, "quiz_reference_answer")
        quiz_not_answered = t(lang, "quiz_not_answered")
        btn_generate_quiz = t(lang, "btn_generate_quiz")
        open_label = t(lang, "learn_plan_open")
        priority_label = t(lang, "learn_plan_priority_label")
        
        # Collect all jobs that have a learn plan
        plan_jobs = []
        for j in jobs:
            plan = j.get("learn_plan")
            if plan:
                plan_jobs.append(j)

        cards = ""
        month_names = cal_month_names
        weekday_labels = cal_weekday_labels

        if not plan_jobs:
            cards = f'''
            <div class="empty-state">
                <p>{cal_empty}</p>
            </div>'''

        for j in plan_jobs:
            plan = j["learn_plan"]
            progress = j.get("learn_plan_progress", {})
            job_title = j.get("title", "未知职位")
            company = j.get("company", "")
            job_id = j["id"]

            # Calculate progress (support new day_of_week IDs and old index-based IDs)
            total_tasks = 0
            done_tasks = 0
            if plan.get("weekly_plan"):
                for w in plan["weekly_plan"]:
                    if w.get("tasks"):
                        for t_idx, raw_task in enumerate(w["tasks"]):
                            if isinstance(raw_task, dict) and raw_task.get("day_of_week"):
                                tid = f"w{w['week']}_d{raw_task['day_of_week']}"
                            else:
                                tid = f"w{w['week']}_t{t_idx}"
                            total_tasks += 1
                            p = progress.get(tid, {})
                            if p.get("done"):
                                done_tasks += 1
            pct = round(done_tasks / total_tasks * 100) if total_tasks > 0 else 0
            pct_color = "#4caf50" if pct == 100 else "#ff9800" if pct >= 50 else "#f44336"

            # Generate calendar grid for each week in plan
            import datetime as dt
            today = dt.date.today()
            week_calendars = ""
            if plan.get("weekly_plan"):
                for w in plan["weekly_plan"]:
                    week_num = w.get("week", 1)
                    focus = w.get("focus", f"{learn_plan_week}{week_num}{learn_plan_suffix}")
                    week_start = today + dt.timedelta(days=(week_num - 1) * 7 - today.weekday())
                    # Monday start
                    # Actually, calculate from today's week offset
                    monday = today - dt.timedelta(days=today.weekday()) + dt.timedelta(weeks=week_num - 1)

                    # Build week grid
                    week_days = ""
                    for d in range(7):
                        day_date = monday + dt.timedelta(days=d)
                        day_str = str(day_date.day)
                        is_today = "today-dot" if day_date == today else ""
                        # Check tasks for this week: Mon-Fri only
                        tasks_for_day = ""
                        _render_cnt = 0
                        if w.get("tasks"):
                            for t_idx, raw_task in enumerate(w["tasks"]):
                                # Determine this task's day_of_week
                                if isinstance(raw_task, dict):
                                    task_dow = raw_task.get("day_of_week")
                                else:
                                    task_dow = None
                                if task_dow is not None:
                                    # day_of_week is 1=Mon..5=Fri
                                    # d=0=Mon(monday), 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
                                    # So task_dow=1 should match d=0, task_dow=2→d=1, etc.
                                    if d >= 5:
                                        continue
                                    if (task_dow - 1) != d:
                                        continue
                                else:
                                    if d >= 5:
                                        continue
                                    day_idx = t_idx % 5
                                    if day_idx != d:
                                        continue
                                # Build task ID: new format uses day_of_week, old format uses index
                                if task_dow is not None:
                                    tid = f"w{week_num}_d{task_dow}"
                                else:
                                    tid = f"w{week_num}_t{t_idx}"
                                p = progress.get(tid, {})
                                is_done = p.get("done", False)
                                done_cls = "task-done" if is_done else ""
                                # Get task text + per-task advice (handle both string and dict task formats)
                                if isinstance(raw_task, dict):
                                    task_text = raw_task.get("name", "")
                                else:
                                    task_text = raw_task
                                task_tip = p.get("advice", "") or plan.get("advice", "") or ""
                                # Build task detail: collect related resources from focus_skills
                                related_res_html = ""
                                related_proj_html = ""
                                matched_any = False
                                matched_res = []  # Track matched skills + their resources
                                for fs in plan.get("focus_skills", []):
                                    sk = fs.get("skill", "").lower()
                                    task_lower = task_text.lower()
                                    import re as _re
                                    match_skill = False
                                    # Normalize: collapse whitespace/punctuation to spaces, strip
                                    task_norm = _re.sub(r'[/,、（）()\s\u2014\u2013\-:]', ' ', task_lower).strip()
                                    sk_norm = _re.sub(r'[/,、（）()\s\u2014\u2013\-:]', ' ', sk).strip()
                                    # 1. Check overlap: words from task in skill name OR skill keywords in task
                                    task_words = set(w for w in task_norm.split() if len(w) > 1)
                                    sk_words = set(w for w in sk_norm.split() if len(w) > 1)
                                    if task_words & sk_words:
                                        match_skill = True
                                    if not match_skill:
                                        # Substring: any significant task word appears in skill or vice versa
                                        for tw in task_words:
                                            if tw in sk_norm or sk_norm in tw:
                                                match_skill = True
                                                break
                                        if not match_skill:
                                            # Check against common skill keyword patterns (English + Chinese equivalents)
                                            kw_patterns = [
                                                (["agent", "ai", "llm"], ["agent", "ai", "llm", "langchain"]),
                                                (["knowledge graph", "rag", "图谱", "检索", "知识"], ["knowledge", "graph", "rag", "retrieval"]),
                                                (["devops", "incident", "事件", "故障"], ["devops", "incident", "response"]),
                                                (["distributed", "分布式", "拓扑", "topology", "依赖"], ["distributed", "topology"]),
                                                (["aws", "cloud", "云", "云原生"], ["aws", "cloud", "architecture"]),
                                                (["python", "ml", "framework"], ["python", "ml", "framework"]),
                                                (["leader", "领导", "collaboration"], ["leader", "collaboration"]),
                                            ]
                                            for task_kws, sk_kws in kw_patterns:
                                                has_task_kw = any(kw in task_lower for kw in task_kws)
                                                has_sk_kw = any(kw in sk_norm for kw in sk_kws)
                                                if has_task_kw and has_sk_kw:
                                                    match_skill = True
                                                    break
                                    if not match_skill:
                                        # 2. Check if any resource title keyword is in task text
                                        for r in fs.get("resources", []):
                                            rt = r.get("title","").lower()
                                            rt_words = [w.strip() for w in _re.split(r'[/,、（）()\s\-\u2014\u2013:]', rt) if len(w.strip()) > 3]
                                            for rw in rt_words:
                                                if rw in task_lower:
                                                    match_skill = True
                                                    break
                                            if match_skill:
                                                break
                                    if match_skill:
                                        matched_any = True
                                    matched_res.append((match_skill, fs))
                                # END of for fs matching loop — now render once
                                import re as _re_outer
                                items_shown = 0
                                for is_match, fs in matched_res:
                                    sk = fs.get("skill", "")
                                    if matched_any:
                                        if not is_match:
                                            continue
                                        resources = fs.get("resources", []) or []
                                        items = "".join(
                                            '<li>\U0001f4da <strong>' + r.get("title","") + '</strong>' + (
                                                ' (' + str(r.get("estimated_hours","")) + 'h)' if r.get("estimated_hours") else ''
                                            ) + (
                                                ' <a href="' + (r.get("url","") or 'https://www.google.com/search?q=' + urllib.parse.quote(r.get("title",""))) + '" target="_blank" style="color:#1a73e8;font-size:11px">' + open_label + '</a>'
                                            ) + '</li>'
                                            for r in resources[:3]
                                        )
                                    else:
                                        remaining = 3 - items_shown
                                        if remaining <= 0:
                                            continue
                                        resources = fs.get("resources", []) or []
                                        items = "".join(
                                            '<li>\U0001f4da <strong>' + r.get("title","") + '</strong>' + (
                                                ' (' + str(r.get("estimated_hours","")) + 'h)' if r.get("estimated_hours") else ''
                                            ) + (
                                                ' <a href="' + (r.get("url","") or 'https://www.google.com/search?q=' + urllib.parse.quote(r.get("title",""))) + '" target="_blank" style="color:#1a73e8;font-size:11px">' + open_label + '</a>'
                                            ) + '</li>'
                                            for r in resources[:1]
                                        )
                                        items_shown += len(resources[:1]) if resources else 0
                                    if items:
                                        related_res_html += '<div class="td-skill-section"><div class="td-skill-name">\U0001f3af ' + fs.get("skill","") + ' (' + fs.get("priority","") + ' ' + priority_label + ')</div>' + fs.get("reason","") + '<ul>' + items + '</ul></div>'
                                for proj in plan.get("projects", []):
                                    if any(s.lower() in task_text.lower() for s in proj.get("skills",[])):
                                        related_proj_html += '<div class="td-project-item">\U0001f4a1 <strong>' + proj.get("name","") + '</strong>：' + proj.get("description","") + '</div>'
                                # Store detail data as encoded JSON data attributes
                                detail_obj = {
                                    "task": task_text,
                                    "focus": focus,
                                    "week": week_num,
                                    "resources_html": related_res_html,
                                    "projects_html": related_proj_html,
                                    "advice_text": task_tip,
                                    "has_quiz": True
                                }
                                detail_json = json.dumps(detail_obj, ensure_ascii=False)
                                detail_b64 = base64.b64encode(detail_json.encode()).decode()
                                disp = task_text[:14] + "..." if len(task_text) > 14 else task_text
                                cb_checked = "checked" if is_done else ""
                                cb_id = f"cb-{job_id}-{tid}"
                                tasks_for_day += f'''
                                    <div class="cal-task-row">
                                        <input type="checkbox" class="cal-task-cb" id="{cb_id}" data-jobid="{job_id}" data-taskid="{tid}" {cb_checked}>
                                        <div class="cal-task {done_cls}" data-detail="{detail_b64}" title="{task_text}">{disp}</div>
                                    </div>'''

                        
                        week_days += f'''
                        <div class="cal-day">
                            <div class="cal-day-header {is_today}">{day_str}</div>
                            {tasks_for_day}
                        </div>'''

                    # Calculate week progress (respect new day_of_week or old index-based IDs)
                    w_tasks = len(w.get("tasks", []))
                    w_done = 0
                    if w.get("tasks"):
                        for t_idx, raw_task in enumerate(w["tasks"]):
                            if isinstance(raw_task, dict) and raw_task.get("day_of_week"):
                                tid = f"w{week_num}_d{raw_task['day_of_week']}"
                            else:
                                tid = f"w{week_num}_t{t_idx}"
                            if progress.get(tid, {}).get("done"):
                                w_done += 1

                    # Month header
                    month_name = month_names[monday.month - 1]
                    week_calendars += f'''
                    <div class="week-calendar">
                        <div class="week-header">
                            <div class="week-title">\U0001f4c5 {week_focus_tpl.format(week_num)} \u00b7 {month_name} \u00b7 {focus}</div>
                            <div class="week-stats">
                                <span>{tasks_completed.format(w_done, w_tasks)}</span>
                                <div class="week-progress-bar"><div class="week-progress-fill" style="width:{round(w_done/w_tasks*100) if w_tasks else 0}%;background:{pct_color}"></div></div>
                            </div>
                        </div>
                        <div class="cal-grid">
                            {"".join(f'<div class="cal-day-header-label">{l}</div>' for l in weekday_labels)}
                            {week_days}
                        </div>
                    </div>'''

            cards += f'''
            <div class="cal-job-card">
                <div class="cal-job-header">
                    <div>
                        <h2>{job_title}</h2>
                        <div class="cal-company">{company}</div>
                    </div>
                    <div class="cal-overall-progress">
                        <div class="cal-progress-circle" style="--pct:{pct};--color:{pct_color}">
                            <span>{pct}%</span>
                        </div>
                        <div style="font-size:13px;color:#888">{done_tasks}/{total_tasks}</div>
                    </div>
                </div>
                {week_calendars}
            </div>'''

        style = f'''
        <style>
        .cal-job-card {{ background:#fff; border-radius:10px; padding:20px; margin-bottom:20px; box-shadow:0 2px 8px rgba(0,0,0,0.06); }}
        .cal-job-header {{ display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px; }}
        .cal-job-header h2 {{ margin:0; font-size:16px; }}
        .cal-company {{ color:#888; font-size:14px; }}
        .cal-overall-progress {{ text-align:center; }}
        .cal-progress-circle {{ width:48px; height:48px; border-radius:50%; background:conic-gradient(var(--color) 0% var(--pct), #e0e0e0 var(--pct) 100%); display:flex; align-items:center; justify-content:center; }}
        .cal-progress-circle span {{ background:#fff; width:38px; height:38px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:600; color:var(--color); }}
        .week-calendar {{ margin-bottom:20px; border:1px solid #eee; border-radius:8px; overflow:hidden; }}
        .week-header {{ display:flex; justify-content:space-between; align-items:center; padding:10px 12px; background:#f8f9fa; border-bottom:1px solid #eee; }}
        .week-title {{ font-weight:500; font-size:15px; }}
        .week-stats {{ display:flex; align-items:center; gap:8px; font-size:13px; color:#888; }}
        .week-progress-bar {{ width:60px; height:6px; background:#e0e0e0; border-radius:3px; overflow:hidden; }}
        .week-progress-fill {{ height:6px; border-radius:3px; transition:width 0.3s; }}
        .cal-grid {{ display:grid; grid-template-columns:repeat(7, 1fr); gap:0; }}
        .cal-day-header-label {{ text-align:center; padding:4px 0; font-size:12px; color:#888; background:#fafafa; }}
        .cal-day {{ min-height:70px; border-right:1px solid #f0f0f0; border-bottom:1px solid #f0f0f0; padding:4px; }}
        .cal-day:nth-child(7n) {{ border-right:none; }}
        .cal-day-header {{ font-size:12px; color:#888; margin-bottom:4px; }}
        .cal-day-header.today-dot {{ background:#1a73e8; color:#fff; border-radius:50%; width:20px; height:20px; display:flex; align-items:center; justify-content:center; }}
        .cal-task-row {{ display:flex; align-items:center; gap:2px; }}
        .cal-task-cb {{ margin:0; width:10px; height:10px; cursor:pointer; flex-shrink:0; }}
        .cal-task {{ font-size:10px; padding:1px 3px; margin:1px 0; background:#e3f2fd; border-radius:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; cursor:pointer; flex:1; min-width:0; }}
        .cal-task.task-done {{ background:#e8f5e9; text-decoration:line-through; color:#888; }}
        .empty-state {{ text-align:center; padding:60px 20px; color:#888; }}
        .empty-state a {{ color:#1a73e8; }}
        .td-overlay {{ position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.45); z-index:9999; display:none; align-items:center; justify-content:center; }}
        .td-modal {{ background:#fff; border-radius:12px; max-width:520px; width:90%; max-height:80vh; overflow-y:auto; box-shadow:0 8px 32px rgba(0,0,0,0.2); padding:24px; position:relative; }}
        .td-close {{ position:absolute; top:12px; right:16px; font-size:22px; cursor:pointer; color:#999; background:none; border:none; }}
        .td-close:hover {{ color:#333; }}
        .td-title-wrap {{ display:flex; align-items:flex-start; gap:10px; margin-bottom:4px; }}
        .td-title {{ font-size:17px; font-weight:600; padding-right:30px; }}
        .td-week {{ font-size:14px; color:#888; margin-bottom:16px; }}
        .td-section {{ margin-bottom:16px; }}
        .td-section-title {{ font-size:15px; font-weight:500; color:#555; margin-bottom:8px; border-bottom:1px solid #eee; padding-bottom:4px; }}
        .td-skill-section {{ margin-bottom:8px; padding:8px; background:#f8f9fa; border-radius:6px; font-size:14px; }}
        .td-skill-name {{ font-weight:600; margin-bottom:4px; }}
        .td-skill-section ul {{ margin:4px 0 0; padding-left:16px; }}
        .td-skill-section li {{ margin-bottom:3px; line-height:1.4; }}
        .td-project-item {{ padding:8px; background:#fff7e6; border-radius:6px; margin-bottom:6px; font-size:14px; }}
        .td-advice {{ padding:12px; background:#e8f5e9; border-radius:6px; font-size:15px; line-height:1.6; color:#2e7d32; }}
        .cal-task {{ cursor:pointer; }}
        .cal-task:hover {{ opacity:0.85; box-shadow:0 1px 4px rgba(0,0,0,0.15); }}
        </style>'''

        # Task detail modal (built as string literals to avoid f-string hell)
        modal = '''
        <div class="td-overlay" id="td-overlay" onclick="closeTaskDetail()" style="display: none">
            <div class="td-modal" onclick="event.stopPropagation()">
                <button class="td-close" onclick="closeTaskDetail()">&times;</button>
                <div class="td-title-wrap" id="td-title-wrap">
                    <input type="checkbox" id="td-checkbox" style="width:18px;height:18px;cursor:pointer;flex-shrink:0">
                    <div class="td-title" id="td-title"></div>
                </div>
                <div class="td-week" id="td-week"></div>
                <div class="td-section" id="td-section-resources" style="display:none">
                    <div class="td-section-title">\U0001f4da \u63a8\u8350\u8d44\u6e90</div>
                    <div id="td-resources"></div>
                </div>
                <div class="td-section" id="td-section-projects" style="display:none">
                    <div class="td-section-title">\U0001f4a1 \u76f8\u5173\u9879\u76ee</div>
                    <div id="td-projects"></div>
                </div>
                <div class="td-section" id="td-section-advice" style="display:none">
                    <div class="td-section-title">\U0001f4ad \u5b66\u4e60\u5efa\u8bae</div>
                    <div class="td-advice" id="td-advice"></div>
                </div>
                <div class="td-section" id="td-section-quiz" style="display:none">
                    <div class="td-section-title" id="td-section-quiz-title"></div>
                    <div id="td-quiz-content"></div>
                    <div id="td-quiz-result" style="margin-top:10px"></div>
                </div>
                <input type="hidden" id="td-detail-data" value="">
            </div>
        </div>
        <script>
        var _learn_plan_week = __learn_plan_week;
        var _learn_plan_suffix = __learn_plan_suffix;
        var _cal_modal_resources = __cal_modal_resources;
        var _cal_modal_projects = __cal_modal_projects;
        var _cal_modal_advice = __cal_modal_advice;
        var _lang = __lang;
        var _quiz_section_title = __quiz_section_title;
        var _quiz_generating = __quiz_generating;
        var _quiz_submit = __quiz_submit;
        var _quiz_reset = __quiz_reset;
        var _quiz_answer_placeholder = __quiz_answer_placeholder;
        var _quiz_hint_submit_to_check = __quiz_hint_submit_to_check;
        var _quiz_result_title = __quiz_result_title;
        var _quiz_correct = __quiz_correct;
        var _quiz_question_prefix = __quiz_question_prefix;
        var _quiz_you_answered = __quiz_you_answered;
        var _quiz_correct_answer = __quiz_correct_answer;
        var _quiz_essay_title = __quiz_essay_title;
        var _quiz_your_answer = __quiz_your_answer;
        var _quiz_reference_answer = __quiz_reference_answer;
        var _quiz_not_answered = __quiz_not_answered;
        var _btn_generate_quiz = __btn_generate_quiz;
        var _btn_optimize = {json.dumps(t(lang, 'btn_optimize'), ensure_ascii=False)};
        var _confirm_regen = {json.dumps(t(lang, 'confirm_regen'), ensure_ascii=False)};
        var _learn_tasks_done = {json.dumps(t(lang, 'learn_tasks_done'), ensure_ascii=False)};
        var _skill_header = {json.dumps(t(lang, 'skill_header'), ensure_ascii=False)};
        var _kw_header = {json.dumps(t(lang, 'kw_header'), ensure_ascii=False)};
        var _level_header = {json.dumps(t(lang, 'level_header'), ensure_ascii=False)};
        var _exp_header = {json.dumps(t(lang, 'exp_header'), ensure_ascii=False)};
        var _saved_status = {json.dumps(t(lang, 'saved_status'), ensure_ascii=False)};
        var _failed_status = {json.dumps(t(lang, 'failed_status'), ensure_ascii=False)};
        var _hint_gen_cover = {json.dumps(t(lang, 'hint_gen_cover'), ensure_ascii=False)};
        var _downloaded_text = {json.dumps(t(lang, 'downloaded_text'), ensure_ascii=False)};
        var _copied_text = {json.dumps(t(lang, 'copied_text'), ensure_ascii=False)};
        var _tasks_completed = {json.dumps(t(lang, 'tasks_completed'), ensure_ascii=False)};

        // Store current task's job/task id for modal checkbox
        var _td_job_id = '';
        var _td_task_id = '';

        // Click on .cal-task div opens detail modal
        document.addEventListener('click', function(e) {
            var el = e.target.closest('.cal-task');
            if (!el || !el.dataset.detail) return;
            try {
                var d = JSON.parse(new TextDecoder().decode(new Uint8Array(Array.from(atob(el.dataset.detail), function(c){return c.charCodeAt(0)}))));
            } catch(e) { try { var d = JSON.parse(JSON.parse(decodeURIComponent(atob(el.dataset.detail)))); } catch(e2) { var d = {}; } }
            document.getElementById('td-title').textContent = d.task;
            document.getElementById('td-week').textContent = '\U0001f4c5 ' + (_learn_plan_week || '') + ' ' + (d.week || '') + (_learn_plan_suffix || '') + ' \u2014 ' + (d.focus || '');

            var rDiv = document.getElementById('td-resources');
            var rSec = document.getElementById('td-section-resources');
            if (d.resources_html) {
                rDiv.innerHTML = d.resources_html;
                rSec.style.display = '';
            } else {
                rSec.style.display = 'none';
            }
            document.getElementById('td-section-resources').children[0].textContent = _cal_modal_resources;

            var pDiv = document.getElementById('td-projects');
            var pSec = document.getElementById('td-section-projects');
            if (d.projects_html) {
                pDiv.innerHTML = d.projects_html;
                pSec.style.display = '';
            } else {
                pSec.style.display = 'none';
            }
            document.getElementById('td-section-projects').children[0].textContent = _cal_modal_projects;

            var aDiv = document.getElementById('td-advice');
            var aSec = document.getElementById('td-section-advice');
            if (d.advice_text) {
                aDiv.textContent = d.advice_text;
                aSec.style.display = '';
            } else {
                aSec.style.display = 'none';
            }
            document.getElementById('td-section-advice').children[0].textContent = _cal_modal_advice;

            // Get job/task id from the clicked el's parent row
            var row = el.closest('.cal-task-row');
            var cb = row ? row.querySelector('.cal-task-cb') : null;
            _td_job_id = cb ? cb.getAttribute('data-jobid') : '';
            _td_task_id = cb ? cb.getAttribute('data-taskid') : '';
            document.getElementById('td-checkbox').checked = cb ? cb.checked : false;
            document.getElementById('td-overlay').style.display = 'flex';
            // Render quiz section — show generate button
            var qSec = document.getElementById('td-section-quiz');
            var qContent = document.getElementById('td-quiz-content');
            var qResult = document.getElementById('td-quiz-result');
            qResult.innerHTML = '';
                        var _onclick = "generateQuiz('" + _td_job_id + "', '" + _td_task_id + "')";
            qContent.innerHTML = '<div style="margin:8px 0"><button class="btn btn-primary" onclick="' + _onclick + '">' + _btn_generate_quiz + '</button><span id="quiz-loading" style="display:none;margin-left:8px;font-size:13px;color:#666">' + _quiz_generating + '</span></div>';
            qSec.style.display = '';
            // Check existing quiz score
            fetch('/api/learn_plan_progress?job_id=' + encodeURIComponent(_td_job_id))
            .then(function(r){return r.json()})
            .then(function(data) {
                if (!data.success) return;
                var p = data.progress && data.progress[_td_task_id];
                if (p && p.quiz_score) {
                    var qs = p.quiz_score;
                    qContent.innerHTML += '<div style="padding:8px 12px;background:#e8f5e9;border-radius:4px;font-size:13px;margin-top:6px">\u4e0a\u6b21\u6210\u7ee9: ' + qs.score + '/' + qs.total + '</div>';
                }
            });


        });

        // Checkbox in modal: save progress and update all indicators in place
        document.addEventListener('change', function(e) {
            var cb = e.target.closest('.cal-task-cb');
            if (cb) {
                // Calendar grid checkbox: save silently, update text decoration
                var jobId = cb.getAttribute('data-jobid');
                var taskId = cb.getAttribute('data-taskid');
                var done = cb.checked;
                var row = cb.parentElement;
                var taskEl = row ? row.querySelector('.cal-task') : null;
                if (taskEl) {
                    if (done) { taskEl.classList.add('task-done'); }
                    else { taskEl.classList.remove('task-done'); }
                }
                fetch('/api/learn_plan_progress', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({job_id: jobId, task_id: taskId, done: done})})
                .then(function(r){return r.json()})
                .then(function(d){ if (d.success) { updateCalendarProgress(jobId); } });
                return;
            }
            var modalCb = e.target.closest('#td-checkbox');
            if (!modalCb) return;
            if (!_td_job_id || !_td_task_id) return;
            var done = modalCb.checked;
            // Sync calendar grid checkbox
            var gridCb = document.querySelector('.cal-task-cb[data-jobid="' + _td_job_id + '"][data-taskid="' + _td_task_id + '"]');
            if (gridCb) {
                gridCb.checked = done;
                var row2 = gridCb.parentElement;
                var taskEl2 = row2 ? row2.querySelector('.cal-task') : null;
                if (taskEl2) {
                    if (done) { taskEl2.classList.add('task-done'); }
                    else { taskEl2.classList.remove('task-done'); }
                }
            }
            fetch('/api/learn_plan_progress', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({job_id: _td_job_id, task_id: _td_task_id, done: done})})
            .then(function(r){return r.json()})
            .then(function(d){ if (d.success) { updateCalendarProgress(_td_job_id); } });
        });


        function escHtml(s) {
            if (!s) return '';
            return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
        }

        function generateQuiz(jobId, taskId) {
            var qSec = document.getElementById('td-section-quiz');
            var qContent = document.getElementById('td-quiz-content');
            var qResult = document.getElementById('td-quiz-result');
            if (!qSec || !qContent) return;
            qContent.innerHTML = '<div style="margin:8px 0;color:#888;font-size:13px">' + _quiz_generating + '</div>';
            qResult.innerHTML = '';
            // Fetch quiz from backend
            var url = '/api/generate_quiz?job_id=' + encodeURIComponent(jobId) + '&task_id=' + encodeURIComponent(taskId) + '&lang=' + encodeURIComponent(_lang);
            fetch(url)
            .then(function(r){ return r.json(); })
            .then(function(d){
                if (d.success && d.quiz) {
                    renderQuizInline(d.quiz, qContent, qResult, jobId, taskId);
                } else {
                    qContent.innerHTML = '<div style="color:#c62828;font-size:13px">' + (d.error || 'Generate failed') + '</div>';
                }
            })
            .catch(function(e){
                qContent.innerHTML = '<div style="color:#c62828;font-size:13px">Error: ' + e + '</div>';
            });
        }

        // Render quiz: randomly pick 5 from 10, display as interactive form
        function renderQuizInline(quiz, container, resultDiv, jobId, taskId) {
            var html = '<form id="quiz-form">';
            var _submitOnclick = "submitQuizInline(document.getElementById('quiz-form'), document.getElementById('td-quiz-result'), '" + jobId + "', '" + taskId + "')";
            var _resetOnclick = "resetQuizInline(document.getElementById('quiz-form'), document.getElementById('td-quiz-result'))";
            quiz.forEach(function(q, idx) {
                var qid = 'q_' + idx;
                html += '<div style="margin-bottom:14px;padding:10px;background:#f9f9f9;border-radius:6px;border:1px solid #e0e0e0">';
                html += '<div style="font-weight:600;font-size:14px;margin-bottom:6px">' + (idx+1) + '. ' + escHtml(q.q) + '</div>';
                if (q.type === 'choice') {
                    html += '<input type="hidden" name="' + qid + '_type" value="choice">';
                    html += '<input type="hidden" name="' + qid + '_answer" value="' + q.answer + '">';
                    q.options.forEach(function(opt, oi) {
                        var letter = String.fromCharCode(65 + oi);
                        html += '<label style="display:block;padding:5px 8px;margin:3px 0;border-radius:4px;cursor:pointer;background:#fff;border:1px solid #ddd">';
                        html += '<input type="radio" name="' + qid + '" value="' + oi + '" style="margin-right:6px">';
                        html += '<strong>' + letter + '</strong>. ' + escHtml(opt);
                        html += '</label>';
                    });
                } else {
                    html += '<input type="hidden" name="' + qid + '_type" value="essay">';
                    html += '<input type="hidden" name="' + qid + '_reference" value="' + escHtml(q.reference || '') + '">';
                    html += '<textarea name="' + qid + '" rows="3" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:4px;font-size:13px" placeholder="' + _quiz_answer_placeholder + '"></textarea>';
                    html += '<div style="font-size:12px;color:#888;margin-top:4px">' + _quiz_hint_submit_to_check + '</div>';
                }
                html += '</div>';
            });
            html += '<div style="display:flex;gap:8px"><button type="button" class="btn btn-primary" onclick="' + _submitOnclick + '">' + _quiz_submit + '</button>';
            html += '<button type="button" class="btn" onclick="' + _resetOnclick + '">' + _quiz_reset + '</button></div>';
            html += '</form>';
            container.innerHTML = html;
        }

        function submitQuizInline(form, resultDiv, jobId, taskId) {
            var score = 0;
            var total = 0;
            var results = [];
            var inputs = form.querySelectorAll('input[type="hidden"][name$="_type"]');
            inputs.forEach(function(h) {
                var prefix = h.name.replace('_type', '');
                var qtype = h.value;
                total++;
                var answerEl = form.querySelector('input[name="' + prefix + '_answer"]');
                var refEl = form.querySelector('input[name="' + prefix + '_reference"]');
                var userEl = form.querySelector('[name="' + prefix + '"]');
                var userVal = userEl ? (userEl.type === 'radio' ? (form.querySelector('[name="' + prefix + '"]:checked') || {}).value : userEl.value.trim()) : '';
                if (qtype === 'choice') {
                    var correct = answerEl ? parseInt(answerEl.value) : -1;
                    var isCorrect = (parseInt(userVal) === correct);
                    if (isCorrect) score++;
                    results.push({type:'choice', correct: isCorrect, userVal: userVal, correctVal: correct});
                } else {
                    results.push({type:'essay', userVal: userVal, reference: refEl ? refEl.value : ''});
                }
            });
            var html = '<div style="padding:12px;background:#e8f5e9;border-radius:6px;font-size:14px">';
            var choiceCount = results.filter(function(r){return r.type==='choice'}).length;
            html += '<div style="font-weight:600;margin-bottom:8px">' + _quiz_result_title + '</div>';
            html += '<div>Multiple Choice: ' + results.filter(function(r){return r.type==='choice' && r.correct}).length + '/' + choiceCount + '' + _quiz_correct + '</div>';
            results.forEach(function(r, idx) {
                if (r.type === 'choice') {
                    var letters = ['A','B','C','D'];
                    var correctLetter = letters[r.correctVal] || '?';
                    var userLetter = letters[r.userVal] || _quiz_not_answered;
                    html += '<div style="margin-top:6px;padding:6px 10px;background:' + (r.correct ? '#e8f5e9' : '#ffebee') + ';border-radius:4px;font-size:13px">';
                    html += '<span style="font-weight:600;color:' + (r.correct ? '#2e7d32' : '#c62828') + '">' + (r.correct ? '\u2713 ' : '\u2717 ') + _quiz_question_prefix + (idx+1) + '</span>';
                    html += _quiz_you_answered + userLetter + _quiz_correct_answer + correctLetter;
                    html += '</div>';
                } else {
                    html += '<div style="margin-top:6px;padding:6px 10px;background:#fff8e1;border-radius:4px;font-size:13px">';
                    html += '<div><strong>' + _quiz_question_prefix + (idx+1) + _quiz_essay_title + '</strong></div>';
                    html += '<div style="margin:4px 0"><em>' + _quiz_your_answer + '</em> ' + escHtml(r.userVal || _quiz_not_answered) + '</div>';
                    if (r.reference) {
                        html += '<div style="margin:4px 0;padding:6px;background:#fff;border:1px dashed #ccc;border-radius:4px"><em>' + _quiz_reference_answer + '</em> ' + escHtml(r.reference) + '</div>';
                    }
                    html += '</div>';
                }
            });
            html += '</div>';
            resultDiv.innerHTML = html;
            fetch('/api/quiz_submit', {method:'POST', headers:{'Content-Type':'application/json'},
                body:JSON.stringify({job_id: jobId, task_id: taskId, score: score, total: total})});
        }

        function resetQuizInline(form, resultDiv) {
            form.reset();
            resultDiv.innerHTML = '';
        }

        // Update all progress
// Update all progress indicators for a job without page reload
        function updateCalendarProgress(jobId) {
            fetch('/api/learn_plan_progress?job_id=' + encodeURIComponent(jobId))
            .then(function(r){return r.json()})
            .then(function(data){
                if (!data.success) return;
                var progress = data.progress || {};
                var cards = document.querySelectorAll('.cal-job-card');
                cards.forEach(function(card) {
                    var allTasks = card.querySelectorAll('.cal-task-cb');
                    var total = 0;
                    var done = 0;
                    allTasks.forEach(function(tcb) {
                        var jid = tcb.getAttribute('data-jobid');
                        if (jid !== jobId) return;
                        total++;
                        var tid = tcb.getAttribute('data-taskid');
                        if (progress[tid] && progress[tid].done) done++;
                    });
                    if (total === 0) return;
                    // Update overall circle
                    var pct = Math.round(done / total * 100);
                    var circle = card.querySelector('.cal-progress-circle');
                    if (circle) {
                        circle.style.setProperty('--pct', pct);
                        var color = pct === 100 ? '#4caf50' : pct >= 50 ? '#ff9800' : '#f44336';
                        circle.style.setProperty('--color', color);
                        var span = circle.querySelector('span');
                        if (span) span.textContent = pct + '%';
                    }
                    var statDiv = card.querySelector('.cal-overall-progress div:last-child');
                    if (statDiv) statDiv.textContent = done + '/' + total;
                    // Update each week's progress
                    card.querySelectorAll('.week-calendar').forEach(function(wc) {
                        var weekCbs = wc.querySelectorAll('.cal-task-cb');
                        var wTotal = 0;
                        var wDone = 0;
                        weekCbs.forEach(function(wcb) {
                            var jid = wcb.getAttribute('data-jobid');
                            if (jid !== jobId) return;
                            wTotal++;
                            var tid = wcb.getAttribute('data-taskid');
                            if (progress[tid] && progress[tid].done) wDone++;
                        });
                        if (wTotal === 0) return;
                        var bar = wc.querySelector('.week-progress-fill');
                        if (bar) bar.style.width = Math.round(wDone / wTotal * 100) + '%';
                        var stat = wc.querySelector('.week-stats span');
                        if (stat) stat.textContent = _tasks_completed.replace('{}', wDone).replace('{}', wTotal);
                    });
                });
            });
        }

        function closeTaskDetail() {
            document.getElementById('td-overlay').style.display = 'none';
        }
        </script>'''

        body = style + f'''
        <div class="container">
            <h1>\U0001f4c5 {cal_title}</h1>
            {cards}
                </div>
        <script>
        var __cal_modal_resources = {json.dumps(cal_modal_resources, ensure_ascii=False)};
        var __cal_modal_projects = {json.dumps(cal_modal_projects, ensure_ascii=False)};
        var __cal_modal_advice = {json.dumps(cal_modal_advice, ensure_ascii=False)};
        var __learn_plan_week = {json.dumps(learn_plan_week, ensure_ascii=False)};
        var __learn_plan_suffix = {json.dumps(learn_plan_suffix, ensure_ascii=False)};
        var __lang = {json.dumps(lang, ensure_ascii=False)};
        var __quiz_section_title = {json.dumps(quiz_section_title, ensure_ascii=False)};
        var __quiz_generating = {json.dumps(quiz_generating, ensure_ascii=False)};
        var __quiz_submit = {json.dumps(quiz_submit, ensure_ascii=False)};
        var __quiz_reset = {json.dumps(quiz_reset, ensure_ascii=False)};
        var __quiz_answer_placeholder = {json.dumps(quiz_answer_placeholder, ensure_ascii=False)};
        var __quiz_hint_submit_to_check = {json.dumps(quiz_hint_submit_to_check, ensure_ascii=False)};
        var __quiz_result_title = {json.dumps(quiz_result_title, ensure_ascii=False)};
        var __quiz_correct = {json.dumps(quiz_correct, ensure_ascii=False)};
        var __quiz_question_prefix = {json.dumps(quiz_question_prefix, ensure_ascii=False)};
        var __quiz_you_answered = {json.dumps(quiz_you_answered, ensure_ascii=False)};
        var __quiz_correct_answer = {json.dumps(quiz_correct_answer, ensure_ascii=False)};
        var __quiz_essay_title = {json.dumps(quiz_essay_title, ensure_ascii=False)};
        var __quiz_your_answer = {json.dumps(quiz_your_answer, ensure_ascii=False)};
        var __quiz_reference_answer = {json.dumps(quiz_reference_answer, ensure_ascii=False)};
        var __quiz_not_answered = {json.dumps(quiz_not_answered, ensure_ascii=False)};
        var __btn_generate_quiz = {json.dumps(btn_generate_quiz, ensure_ascii=False)};
        </script>
        ''' + modal

        self._send_html(self._page(t(lang, "learn_plan_title"), body, lang=lang))

    def handle_profile_page(self, params):
        lang = self._get_lang(params)
        p = self.agent.profile.profile
        sk = ""
        years_label = "yr" if lang == "en" else "年"
        for cat, info in p.get("skills", {}).items():
            kw = ", ".join(info.get("keywords", [])[:4])
            sk += f"<tr><td>{cat}</td><td>{kw}…</td><td>{info.get('level','')}</td><td>{info.get('years',0)}{years_label}</td></tr>"
        skill_header = t(lang, "skill_header")
        kw_header = t(lang, "kw_header")
        level_header = t(lang, "level_header")
        exp_header = t(lang, "exp_header")
        saved_text = " ✅ " + t(lang, "saved_status")
        failed_text = " ❌ " + t(lang, "failed_status")

        html = self._page(t(lang, 'profile_title'), f"""
        <h1>{t(lang, 'profile_title')}</h1>
        <p style="color:#666;margin-bottom:16px">{t(lang, 'profile_desc')}</p>
        <div class="section">
            <h2>{t(lang, 'name_label')}</h2>
            <div class="profile-form">
                <div class="form-row"><label>{t(lang, 'name_label')}</label><input id="name" value="{p.get('name','')}"></div>
                <div class="form-row"><label>{t(lang, 'target_role')}</label><input id="title" value="{p.get('title','')}"></div>
                <div class="form-row"><label>{t(lang, 'applications')}({years_label})</label><input id="exp" type="number" value="{p.get('experience_years',5)}"></div>
                <div class="form-row"><label>Education</label><input id="edu" value="{p.get('education','')}"></div>
                <div class="form-row"><label>{t(lang, 'target_companies')}</label><input id="cos" value="{', '.join(p.get('preferred_companies',[]))}"></div>
                <div class="form-row"><label>{t(lang, 'locations_label')}</label><input id="locs" value="{', '.join(p.get('preferred_locations',[]))}"></div>
                <div class="form-row"><label>{t(lang, 'target_role')}</label><input id="roles" value="{', '.join(p.get('preferred_roles',[]))}"></div>
                <div class="form-row"><label>{t(lang, 'salary_min')}/{t(lang, 'salary_max')}({t(lang, 'currency')})</label>
                    <div class="salary-range">
                        <input id="sal_min" type="number" value="{p.get('salary_expectation',{}).get('min',130000)}"> ~
                        <input id="sal_max" type="number" value="{p.get('salary_expectation',{}).get('max',250000)}">
                    </div>
                </div>
                <button onclick="saveProfile()" class="btn btn-primary">{t(lang, 'save_profile')}</button>
                <span id="ps"></span>
            </div>
        </div>
        <div class="section">
            <h2>{t(lang, 'skill_profile')}</h2>
            <table class="skills-table"><thead><tr><th>{skill_header}</th><th>{kw_header}</th><th>{level_header}</th><th>{exp_header}</th></tr></thead>
            <tbody>{sk}</tbody></table>
        </div>
        <script>
        async function saveProfile() {{
            var d = {{
                name: document.getElementById('name').value,
                title: document.getElementById('title').value,
                experience_years: parseInt(document.getElementById('exp').value),
                education: document.getElementById('edu').value,
                preferred_companies: document.getElementById('cos').value.split(',').map(s=>s.trim()).filter(Boolean),
                preferred_locations: document.getElementById('locs').value.split(',').map(s=>s.trim()).filter(Boolean),
                preferred_roles: document.getElementById('roles').value.split(',').map(s=>s.trim()).filter(Boolean),
                salary_expectation: {{min: parseInt(document.getElementById('sal_min').value), max: parseInt(document.getElementById('sal_max').value), currency: "CAD"}}
            }};
            var r = await fetch('/api/update_profile', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(d)}});
            var j = await r.json();
            document.getElementById('ps').textContent = j.success ? '{saved_text}' : '{failed_text}';
        }}
        </script>
        """, lang=lang)
        self._send_html(html)

    def handle_letter_page(self, params):
        lang = self._get_lang(params)
        hint_text = t(lang, "hint_gen_cover")
        downloaded_text = t(lang, "downloaded_text")
        copied_text = t(lang, "copied_text")
        html = self._page(t(lang, 'letter_title'), f"""
        <h1>{t(lang, 'letter_title')}</h1>
        <div id="letter-content"><p>{hint_text}</p></div>
        <div style="margin-top:12px">
            <button onclick="dl()" class="btn btn-primary">{t(lang, 'save_btn')}</button>
            <button onclick="cp()" class="btn btn-secondary">{t(lang, 'letter_btn')}</button>
        </div>
        <script>
        if (window.letterContent) document.getElementById('letter-content').innerHTML = '<pre>'+window.letterContent+'</pre>';
        function dl() {{ var t = document.getElementById('letter-content').textContent; var b = new Blob([t], {{type:'text/plain'}}); var a = document.createElement('a'); a.href=URL.createObjectURL(b); a.download='cover_letter.txt'; a.click(); alert('{downloaded_text}'); }}
        function cp() {{ navigator.clipboard.writeText(document.getElementById('letter-content').textContent).then(function(){{alert('{copied_text}');}}); }}
        </script>
        """, lang=lang)
        self._send_html(html)

    # ===================== API =====================

    def api_run_search(self, data):
        try:
            sources = data.get("sources", None)
            kw = data.get("keywords", None)
            kw_list = [k.strip() for k in kw.replace(",", " ").split()] if kw else None
            loc = data.get("location", None)
            result = self.agent.run_search(sources=sources, keywords=kw_list, location=loc)
            self.send_json({
                "success": True,
                "jobs": result.get("jobs", []),
                "search_links": result.get("search_links", []),
                "stats": result.get("stats", {})
            })
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_save_job(self, data):
        try:
            job_data = data.get("job", {})
            # 如果职位有URL但描述不完整，尝试抓取完整详情
            url = job_data.get("url", "")
            desc = job_data.get("description", "")
            if url and (len(desc) < 500 or not job_data.get("title")):
                try:
                    fetched = self.agent.fetch_job_from_url(url, keep_html=True)
                    if fetched.get("description"):
                        job_data["description"] = fetched["description"]
                    if fetched.get("title"):
                        job_data["title"] = fetched["title"]
                    if fetched.get("company"):
                        job_data["company"] = fetched["company"]
                    if fetched.get("location"):
                        job_data["location"] = fetched["location"]
                    if fetched.get("job_type"):
                        job_data["job_type"] = fetched["job_type"]
                except Exception:
                    pass

            ok = self.agent.save_job(job_data)
            if ok:
                try:
                    letter = self.agent.generate_cover_letter(job_data)
                    self.agent.tracker.update_cover_letter(job_data.get("title",""), job_data.get("company",""), letter)
                except Exception:
                    pass
                self.send_json({"success": True, "fetched": bool(desc) or None})
            else:
                self.send_json({"success": False, "error": "该职位已保存，请勿重复添加"})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_update_status(self, data):
        try:
            ok = self.agent.update_job_status(data.get("job_id",""), data.get("status",""), data.get("notes",""))
            self.send_json({"success": ok})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)
    
    def api_delete_job(self, data):
        try:
            ok = self.agent.delete_job(data.get("job_id",""))
            self.send_json({"success": ok})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_update_profile(self, data):
        try:
            # Persist language preference if sent from client
            if 'language' in data and data['language'] in ('en', 'zh-CN', 'fr'):
                self.agent.update_profile({'language': data['language']})
            self.agent.update_profile(data)
            self.send_json({"success": True})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_generate_letter(self, data):
        try:
            letter = self.agent.generate_cover_letter(data.get("job", {}))
            self.send_json({"success": True, "letter": letter})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_get_cover_letter(self, data):
        try:
            job_id = data.get("job_id", "")
            lang = data.get("lang", "")
            if lang not in ("en", "zh-CN", "fr"):
                lang = "zh-CN"
            regen = data.get("regen", "") == "1"
            letter = ""
            for j in self.agent.tracker.tracked_jobs:
                if j["id"] == job_id:
                    letter = j.get("cover_letter", "") if not regen else ""
                    break
            if not letter:
                # Generate on demand (or regenerate)
                for j in self.agent.tracker.tracked_jobs:
                    if j["id"] == job_id:
                        letter = self.agent.generate_cover_letter(j)
                        self.agent.tracker.update_cover_letter_by_id(job_id, letter)
                        break
            self.send_json({"success": True, "letter": letter})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_save_cover_letter(self, data):
        try:
            job_id = data.get("job_id", "")
            letter = data.get("letter", "")
            ok = self.agent.tracker.update_cover_letter_by_id(job_id, letter)
            self.send_json({"success": ok})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_upload_resume(self, body: bytes, content_type: str):
        """处理简历文件上传 (multipart/form-data)"""
        try:
            import uuid
            boundary = None
            for part in content_type.split(";"):
                part = part.strip()
                if part.startswith("boundary="):
                    boundary = part[9:]
            if not boundary:
                self.send_json({"success": False, "error": "缺少 boundary"}, 400)
                return

            job_id = ""
            file_data = None
            # 手动解析 multipart
            delimiter = b"--" + boundary.encode()
            parts = body.split(delimiter)
            for part in parts:
                if b"Content-Disposition" not in part:
                    continue
                # 分离 header 和 body
                header_end = part.find(b"\r\n\r\n")
                if header_end == -1:
                    continue
                headers_raw = part[:header_end].decode("utf-8", errors="replace")
                content = part[header_end+4:]  # 跳过 \r\n\r\n
                # 去掉尾部 \r\n--
                if content.endswith(b"\r\n"):
                    content = content[:-2]
                elif content.endswith(b"--\r\n"):
                    content = content[:-4]

                if 'name="job_id"' in headers_raw:
                    job_id = content.decode("utf-8", errors="replace").strip()
                elif 'name="resume"' in headers_raw:
                    file_data = content

            if not job_id or not file_data:
                self.send_json({"success": False, "error": "缺少 job_id 或 resume 文件"}, 400)
                return
            self.agent.tracker.save_resume(job_id, file_data)
            self.send_json({"success": True})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_get_resume_GET(self, params):
        """GET 方式返回简历文件供下载（支持 resume_id 或 job_id）"""
        try:
            job_id = params.get("job_id", "")
            resume_id = params.get("resume_id", "")
            if job_id:
                content = self.agent.tracker.get_job_resume(job_id)
                if content is None:
                    content = self.agent.tracker.get_resume(resume_id) if resume_id else None
            else:
                content = self.agent.tracker.get_resume(resume_id)
            if content is None:
                self.send_json({"success": False, "error": "未找到简历"}, 404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", f'attachment; filename="resume_{resume_id}.pdf"')
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_preview_resume_GET(self, params):
        """GET 方式返回简历的 HTML 预览（优先使用 Markdown 编辑版）"""
        try:
            resume_id = params.get("resume_id", "")
            job_id = params.get("job_id", "")
            if job_id:
                # 优先使用 markdown 编辑版
                md = self.agent.tracker.get_job_resume_markdown(job_id)
                if md:
                    html = self.agent.tracker.markdown_to_html(md)
                else:
                    data = self.agent.tracker.get_job_resume(job_id)
                    if data:
                        html = self.agent.tracker.convert_resume_to_html_given_data(data, resume_id or job_id)
                    else:
                        html = "<p style='color:#888'>未找到该职位的简历</p>"
            elif resume_id:
                html = self.agent.tracker.convert_resume_to_html(resume_id)
            else:
                self.send_json({"success": False, "error": "缺少 resume_id 或 job_id"}, 400)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_get_resume(self, data):
        """返回简历文件供下载 (POST)"""
        try:
            resume_id = data.get("resume_id", data.get("job_id", ""))
            content = self.agent.tracker.get_resume(resume_id)
            if content is None:
                self.send_json({"success": False, "error": "未找到简历"}, 404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", f'attachment; filename="resume_{resume_id}.pdf"')
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_list_resumes_GET(self, params):
        """GET 返回简历列表"""
        try:
            resumes = self.agent.tracker.list_resumes()
            self.send_json({"success": True, "resumes": resumes})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_list_resumes(self, data):
        """POST 返回简历列表"""
        self.api_list_resumes_GET(data)

    def api_add_resume(self, data):
        """上传简历到简历库 (POST JSON)"""
        try:
            # 支持两种方式：base64 文本或 multipart 上传
            name = data.get("name", "未命名简历")
            file_b64 = data.get("file", None)
            if file_b64:
                import base64
                file_data = base64.b64decode(file_b64)
                entry = self.agent.tracker.add_resume(name, file_data)
                self.send_json({"success": True, "resume": entry})
            else:
                self.send_json({"success": False, "error": "缺少 file 字段(base64)"}, 400)
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_add_resume_multipart(self, body: bytes, content_type: str):
        """multipart 上传简历到简历库"""
        try:
            boundary = None
            for part in content_type.split(";"):
                part = part.strip()
                if part.startswith("boundary="):
                    boundary = part[9:]
            if not boundary:
                self.send_json({"success": False, "error": "缺少 boundary"}, 400)
                return
            name = "未命名简历"
            file_data = None
            delimiter = b"--" + boundary.encode()
            parts = body.split(delimiter)
            for part in parts:
                if b"Content-Disposition" not in part:
                    continue
                header_end = part.find(b"\r\n\r\n")
                if header_end == -1:
                    continue
                headers_raw = part[:header_end].decode("utf-8", errors="replace")
                content = part[header_end+4:]
                if content.endswith(b"\r\n"):
                    content = content[:-2]
                elif content.endswith(b"--\r\n"):
                    content = content[:-4]
                if 'name="name"' in headers_raw:
                    name = content.decode("utf-8", errors="replace").strip()
                elif 'name="resume"' in headers_raw:
                    file_data = content
            if not file_data:
                self.send_json({"success": False, "error": "缺少 resume 文件"}, 400)
                return
            entry = self.agent.tracker.add_resume(name, file_data)
            self.send_json({"success": True, "resume": entry})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_delete_resume(self, data):
        """从简历库删除简历"""
        try:
            resume_id = data.get("resume_id", "")
            if not resume_id:
                self.send_json({"success": False, "error": "缺少 resume_id"}, 400)
                return
            ok = self.agent.tracker.delete_resume(resume_id)
            self.send_json({"success": ok})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_assign_resume(self, data):
        """给职位关联简历"""
        try:
            job_id = data.get("job_id", "")
            resume_id = data.get("resume_id", "")
            ok = self.agent.tracker.assign_resume(job_id, resume_id)
            self.send_json({"success": ok})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_save_job_resume(self, data):
        """保存职位简历的 HTML 编辑版本（不修改简历库）"""
        try:
            job_id = data.get("job_id", "")
            html = data.get("html", "")
            if not job_id:
                self.send_json({"success": False, "error": "缺少 job_id"}, 400)
                return
            ok = self.agent.tracker.save_job_resume_text(job_id, html)
            self.send_json({"success": ok})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_get_resume_markdown(self, data):
        """返回职位简历的 Markdown 源码"""
        try:
            job_id = data.get("job_id", "")
            if not job_id:
                self.send_json({"success": False, "error": "缺少 job_id"}, 400)
                return
            md = self.agent.tracker.get_job_resume_markdown(job_id)
            self.send_json({"success": True, "markdown": md or ""})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_download_resume_pdf(self, data):
        """下载职位简历的 PDF 版本（从 Markdown 生成）"""
        try:
            job_id = data.get("job_id", "")
            if not job_id:
                self.send_json({"success": False, "error": "缺少 job_id"}, 400)
                return
            # 查找职位信息
            job = None
            for j in self.agent.tracker.tracked_jobs:
                if j["id"] == job_id:
                    job = j
                    break
            md = self.agent.tracker.get_job_resume_markdown(job_id)
            if not md:
                self.send_json({"success": False, "error": "未找到简历内容"}, 404)
                return
            title = (job.get("resume_name", "") if job else "") or "简历"
            pdf_bytes = self.agent.tracker.resume_to_pdf_bytes(md, title)
            if not pdf_bytes:
                self.send_json({"success": False, "error": "PDF 生成失败"}, 500)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", f'attachment; filename="resume_{job_id}.pdf"')
            self.send_header("Content-Length", str(len(pdf_bytes)))
            self.end_headers()
            self.wfile.write(pdf_bytes)
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_convert_markdown(self, data):
        """将 Markdown 转换为 HTML（用于实时预览）"""
        try:
            markdown = data.get("markdown", "")
            html = self.agent.tracker.markdown_to_html(markdown)
            self.send_json({"success": True, "html": html})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_save_job_resume_md(self, data):
        """保存职位简历的 Markdown 版本"""
        try:
            job_id = data.get("job_id", "")
            markdown = data.get("markdown", "")
            if not job_id:
                self.send_json({"success": False, "error": "缺少 job_id"}, 400)
                return
            ok = self.agent.tracker.save_job_resume_markdown(job_id, markdown)
            self.send_json({"success": ok})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_analyze_apply(self, data):
        """分析职位的申请方式"""
        try:
            job_id = data.get("job_id", "")
            job = self.agent.tracker.get_job(job_id)
            if not job:
                # 尝试从搜索缓存中找
                job = self._find_job_from_cache(job_id)
            if not job:
                self.send_json({"success": False, "error": "找不到该职位"}, 404)
                return
            result = self.agent.apply_manager.analyze(job)
            self.send_json({"success": True, "analysis": result, "job": {
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "source": job.get("source", ""),
            }})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_record_apply(self, data):
        """记录申请动作"""
        try:
            job_id = data.get("job_id", "")
            job = self.agent.tracker.get_job(job_id)
            if not job:
                job = self._find_job_from_cache(job_id)
            if not job:
                self.send_json({"success": False, "error": "找不到该职位"}, 404)
                return
            result = self.agent.apply_manager.record_manual_apply(job)
            # 同时更新跟踪状态
            self.agent.tracker.update_status(job_id, "applied")
            self.send_json({"success": True, "record": result.get("record")})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_fetch_job_from_url(self, data):
        """接收URL，抓取并分析职位，返回分析结果供前端预览后保存"""
        try:
            url = data.get("url", "").strip()
            if not url:
                self.send_json({"success": False, "error": "URL不能为空"})
                return
            raw = self.agent.fetch_job_from_url(url)
            if not raw.get("title") or not raw.get("description"):
                self.send_json({"success": False, "error": "无法从此URL提取职位信息，请确认链接是否正确"})
                return

            # Run analyze to get match_score etc.
            job_for_analysis = {
                "title": raw["title"],
                "company": raw.get("company", ""),
                "location": raw.get("location", ""),
                "description": raw.get("description", ""),
                "source": raw.get("url", url),
                "job_type": raw.get("job_type", ""),
                "url": raw.get("url", url),
            }
            analyzed = self.agent.analyzer.analyze_job(job_for_analysis)
            analyzed.update(raw)
            self.send_json({"success": True, "job": analyzed})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)})

    def api_tailor_resume(self, data):
        """根据职位要求优化简历（通过 DeepSeek API）"""
        try:
            job_id = data.get("job_id", "")
            if not job_id:
                self.send_json({"success": False, "error": "缺少 job_id"}, 400)
                return
            job = self.agent.tracker.get_job(job_id)
            if not job:
                self.send_json({"success": False, "error": "找不到该职位"}, 404)
                return
            resume_md = self.agent.tracker.get_job_resume_markdown(job_id)
            if not resume_md:
                self.send_json({"success": False, "error": "未找到简历内容（请先关联简历）"}, 404)
                return

            job_title = job.get("title", "")
            job_desc = job.get("description", "")
            company = job.get("company", "")

            # 调用 DeepSeek API (OpenAI 兼容) 生成优化版简历
            import urllib.request
            import json as j

            system_msg = "你是一位专业的简历优化专家。根据职位要求优化简历，只输出 Markdown，不要额外说明。"
            user_msg = f"""职位: {company} - {job_title}

职位描述:
{job_desc}

当前简历:
{resume_md}

要求：
1. 保留 Markdown 格式
2. 突出与目标职位相关的技能和经验
3. 匹配职位描述中的关键词
4. 精简不相关的内容
5. 保持一页以内
6. 只输出优化后的简历 Markdown，不要额外说明
"""

            req_body = j.dumps({
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                "temperature": 0.6,
                "max_tokens": 32768,
                "stream": False
            })

            # 从环境变量或配置文件读取 DeepSeek API Key
            api_key = os.environ.get("DEEPSEEK_API_KEY", "")
            if not api_key:
                # 从 OpenClaw 配置读取
                models_cfg = os.path.expanduser("~/.openclaw/agents/main/agent/models.json")
                if os.path.exists(models_cfg):
                    with open(models_cfg) as f:
                        cfg = j.load(f)
                    api_key = cfg.get("providers", {}).get("deepseek", {}).get("apiKey", "")
            if not api_key:
                self.send_json({"success": False, "error": "未找到 DeepSeek API Key"}, 500)
                return

            req = urllib.request.Request(
                "https://api.deepseek.com/chat/completions",
                data=req_body.encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + api_key
                },
                method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=120)
            result = j.loads(resp.read().decode())

            choices = result.get("choices", [])
            if not choices:
                self.send_json({"success": False, "error": f"API 返回为空: {result}"}, 500)
                return
            tailored_md = choices[0]["message"]["content"].strip()

            # 保存优化后的简历
            self.agent.tracker.save_job_resume_markdown(job_id, tailored_md)
            self.send_json({"success": True, "markdown": tailored_md})
        except Exception as e:
            self.send_json({"success": False, "error": f"优化失败: {str(e)}"}, 500)

    def api_analyze_skill_gap(self, data):
        """分析简历与职位要求之间的技能差距"""
        try:
            job_id = data.get("job_id", "")
            if not job_id:
                self.send_json({"success": False, "error": "缺少 job_id"}, 400)
                return
            lang = data.get("lang", "")
            if lang not in ("en", "zh-CN", "fr"):
                lang = "zh-CN"
            job = self.agent.tracker.get_job(job_id)
            if not job:
                self.send_json({"success": False, "error": "找不到该职位"}, 404)
                return
            if not job.get("resume_id"):
                self.send_json({"success": False, "error": "未关联简历"}, 400)
                return

            resume_md = self.agent.tracker.get_job_resume_markdown(job_id)
            if not resume_md:
                self.send_json({"success": False, "error": "未找到简历内容"}, 404)
                return

            job_title = job.get("title", "")
            job_desc = job.get("description", "")
            company = job.get("company", "")

            prompt = f"""分析以下简历和职位描述的技能差距。
请使用{lang}语言输出答案和描述，技能名称保持英文。

### 职位
{company} - {job_title}

### 职位描述
{job_desc}

### 简历
{resume_md}

请以 JSON 格式输出分析结果，不要其他文字：
{{
  "matching_skills": ["skillA", "skillB"],  // 简历中有且职位也要求的技能
  "missing_skills": ["skillC", "skillD"],    // 职位要求但在简历中未体现的关键技能
  "weak_skills": ["skillE"],               // 简历中有但需要加强的技能
  "suggestions": ["建议1", "建议2"]       // 学习或提升建议，用对应语言输出
}}
"""

            import urllib.request
            import json as j

            api_key = os.environ.get("DEEPSEEK_API_KEY", "")
            if not api_key:
                models_cfg = os.path.expanduser("~/.openclaw/agents/main/agent/models.json")
                if os.path.exists(models_cfg):
                    with open(models_cfg) as f:
                        cfg = j.load(f)
                    api_key = cfg.get("providers", {}).get("deepseek", {}).get("apiKey", "")
            if not api_key:
                self.send_json({"success": False, "error": "未找到 DeepSeek API Key"}, 500)
                return

            req_body = j.dumps({
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是技能分析专家。输出纯 JSON，不要 markdown 代码块。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 2048,
                "stream": False
            })

            req = urllib.request.Request(
                "https://api.deepseek.com/chat/completions",
                data=req_body.encode(),
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + api_key},
                method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=120)
            result = j.loads(resp.read().decode())
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            # 清理可能包裹的 markdown 代码块
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
                content = content.rsplit("```", 1)[0].strip()
            if content.startswith("json"):
                content = content[4:].strip()

            gap_data = j.loads(content)

            # 生成 HTML 标签，存储在 job dict
            missing = gap_data.get("missing_skills", [])
            weak = gap_data.get("weak_skills", [])
            matching = gap_data.get("matching_skills", [])
            suggestions = gap_data.get("suggestions", [])

            _t = lambda k: t(lang, k)
            parts = []
            for s in missing[:5]:
                parts.append(f'<span class="skill-gap-badge gap-missing" title="{_t("gap_missing")}" style="display:inline-block;background:#fee;color:#d32f2f;border:1px solid #fcc;border-radius:4px;padding:1px 6px;font-size:11px;margin:1px">\u26a0 {s}</span>')
            for s in weak[:3]:
                parts.append(f'<span class="skill-gap-badge gap-weak" title="{_t("gap_weak")}" style="display:inline-block;background:#fff3e0;color:#e65100;border:1px solid #ffe0b2;border-radius:4px;padding:1px 6px;font-size:11px;margin:1px">\u2191 {s}</span>')

            # 用 popover 显示详情
            details_html = ""
            if matching:
                details_html += f"<div style='margin-bottom:6px'><b>{_t('gap_skills')}:</b> " + ", ".join(matching) + "</div>"
            if missing:
                details_html += f"<div style='margin-bottom:6px;color:#d32f2f'><b>{_t('gap_missing')}:</b> " + ", ".join(missing) + "</div>"
            if weak:
                details_html += f"<div style='margin-bottom:6px;color:#e65100'><b>{_t('gap_weak')}:</b> " + ", ".join(weak) + "</div>"
            if suggestions:
                details_html += f"<div style='margin-top:6px;color:#1565c0;font-size:12px'><b>{_t('gap_suggestions')}:</b><br>" + "<br>".join(suggestions) + "</div>"

            gap_html = "".join(parts)
            if gap_html:
                # Store details in a data attribute, handle click via event delegation
                import html
                details_escaped = html.escape(j.dumps(details_html, ensure_ascii=False))
                gap_html = '<span class="skill-gap-group" style="display:inline-block;margin-left:4px;cursor:pointer" data-gap-details="' + details_escaped + '" data-gap-jobid="' + str(job_id) + '">' + gap_html + '</span>'

            # 保存 gap_data 到职位数据（用于多语言渲染）
            job["skill_gap_data"] = {
                "matching": gap_data.get("matching_skills", []),
                "missing": gap_data.get("missing_skills", []),
                "weak": gap_data.get("weak_skills", []),
                "suggestions": gap_data.get("suggestions", []),
            }
            job["skill_gap_html"] = gap_html
            self.agent.tracker.save()

            self.send_json({"success": True, "html": gap_html})
        except json.JSONDecodeError:
            self.send_json({"success": False, "error": "AI 返回格式异常，请重试"}, 500)
        except Exception as e:
            self.send_json({"success": False, "error": f"分析失败: {str(e)}"}, 500)

    def api_learn_plan(self, data, method="POST"):
        """根据技能差距生成强化学习计划（POST 生成并保存，GET 获取已保存）"""
        try:
            job_id = data.get("job_id", "")
            if not job_id:
                self.send_json({"success": False, "error": "缺少 job_id"}, 400)
                return
            lang = data.get("lang", "")
            if lang not in ("en", "zh-CN", "fr"):
                lang = "zh-CN"
            job = self.agent.tracker.get_job(job_id)
            if not job:
                self.send_json({"success": False, "error": "找不到该职位"}, 404)
                return

            # GET: return saved plan if exists
            if method == "GET":
                saved = job.get("learn_plan")
                if saved:
                    progress = job.get("learn_plan_progress", {})
                    self.send_json({"success": True, "plan": saved, "progress": progress, "saved": True})
                    return
                self.send_json({"success": True, "plan": None, "saved": False})
                return

            # POST: generate new plan
            regenerate = data.get("regenerate", False)
            job_title = job.get("title", "")
            job_desc = job.get("description", "")
            company = job.get("company", "")
            resume_md = self.agent.tracker.get_job_resume_markdown(job_id) or ""

                        # JSON template as plain string — no f-string to avoid brace escaping issues
            prompt = f"""You are a senior technical mentor. Create a detailed skill improvement study plan for a job seeker applying to the following position.
IMPORTANT: Output ALL text content in {lang} language (skill names should remain in English).
Do NOT use any other language in the output. The entire response must be in {lang}.

### 目标职位
{company} - {job_title}

### 职位描述
{job_desc}

### 当前简历
{resume_md[:3000]}

### ⚠️ 重要要求
1. 每个 focus_skills 必须有至少 2 个推荐资源（resources），且必须提供真实的 url 链接（https 开头）
2. **不要使用 Coursera 或需要付费/登录才能访问的课程平台链接**（这些链接大部分无法直接访问）。优先使用以下类型的免费资源：
   - **YouTube 教程**（搜索链接：https://www.youtube.com/results?search_query=xxx+tutorial）
   - **官方文档**（如 MDN、Python docs、Kubernetes.io 等）
   - **GitHub 仓库**（如 awesome-xxx 项目）
   - **免费博客/文章**（如 Medium、Dev.to、掘金、CSDN 等）
   - **B站/慕课网**（中文用户）
3. 实在找不到精确 URL 时，直接用 Google 搜索链接：https://www.google.com/search?q=教程名
4. 每个资源必须包含 type、title、url、estimated_hours 四个字段，url 不能为空
5. 每周安排 5 个工作日任务（周一至周五），周末不安排任务
6. 每个任务必须包含 day_of_week 字段（1=周一，2=周二，3=周三，4=周四，5=周五）
### 输出格式（纯 JSON，不要 markdown 代码块）
{{
  "position": "目标职位名称",
  "focus_skills": [
    {{
      "skill": "技能名称",
      "priority": "High/Mid/Low",
      "reason": "Explain why this skill is important",
      "resources": [
        {{"type": "Course/Book/Project/Doc", "title": "Resource Title", "url": "https://...", "estimated_hours": 10}}
      ]
    }}
  ],
  "weekly_plan": [
    {{"week": 1, "focus": "Weekly focus topic", "tasks": [
      {{"name": "周一任务", "day_of_week": 1, "advice": "Detailed learning advice in {lang}"}},
      {{"name": "周二任务", "day_of_week": 2, "advice": "Detailed learning advice in {lang}"}},
      {{"name": "周三任务", "day_of_week": 3, "advice": "Detailed learning advice in {lang}"}},
      {{"name": "周四任务", "day_of_week": 4, "advice": "Detailed learning advice in {lang}"}},
      {{"name": "周五任务", "day_of_week": 5, "advice": "Detailed learning advice in {lang}"}}
    ], "estimated_hours": 5}}
  ],
  "projects": [
    {{"name": "项目名", "description": "练习项目简述", "skills": ["涉及的技能"]}}
  ],
  "total_estimated_weeks": 4,
  "advice": "总体建议（一段话）"
}}
"""

            import urllib.request
            import json as j

            api_key = os.environ.get("DEEPSEEK_API_KEY", "")
            if not api_key:
                models_cfg = os.path.expanduser("~/.openclaw/agents/main/agent/models.json")
                if os.path.exists(models_cfg):
                    with open(models_cfg) as f:
                        cfg = j.load(f)
                    api_key = cfg.get("providers", {}).get("deepseek", {}).get("apiKey", "")
            if not api_key:
                self.send_json({"success": False, "error": "未找到 DeepSeek API Key"}, 500)
                return

            req_body = j.dumps({
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是资深技术导师和职业规划专家。输出纯 JSON。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 4096,
                "stream": False
            })

            req = urllib.request.Request(
                "https://api.deepseek.com/chat/completions",
                data=req_body.encode(),
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + api_key},
                method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=120)
            result = j.loads(resp.read().decode())
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            # 清理可能包裹的 markdown 代码块
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
                content = content.rsplit("```", 1)[0].strip()
            if content.startswith("json"):
                content = content[4:].strip()

            plan = j.loads(content)
            # 保存计划到职位数据
            job["learn_plan"] = plan
            # 如果是重新生成，清除旧进度
            if regenerate:
                job.pop("learn_plan_progress", None)
            # 初始化进度：为每个周任务创建 task_id 并初始化为未完成
            progress = {}
            if plan.get("weekly_plan"):
                for w in plan["weekly_plan"]:
                    week_num = w.get("week", 0)
                    if w.get("tasks"):
                        for t_idx, raw in enumerate(w["tasks"]):
                            if isinstance(raw, dict):
                                task_text = raw.get("name", "")
                                task_advice = raw.get("advice", "")
                                dow = raw.get("day_of_week")  # 1=Mon..5=Fri, optional for backward compat
                            else:
                                task_text = raw
                                task_advice = ""
                                dow = None
                            # Use day_of_week in task_id for new plans; fallback to index for old plans
                            if dow is not None:
                                task_id = f"w{week_num}_d{dow}"
                            else:
                                task_id = f"w{week_num}_t{t_idx}"
                            progress[task_id] = {"done": False, "text": task_text, "week": week_num, "advice": task_advice, "day_of_week": dow}
            job["learn_plan_progress"] = progress
            self.agent.tracker.save()
            self.send_json({"success": True, "plan": plan, "saved": True})
        except json.JSONDecodeError:
            import traceback; traceback.print_exc()
            try:
                with open('/tmp/llm_debug.txt', 'w') as _f:
                    _f.write(content)
                    _f.write(f"\n---END (len={len(content)})---")
            except: pass
            self.send_json({"success": False, "error": "AI 返回格式异常，请重试"}, 500)
        except Exception as e:
            import traceback; traceback.print_exc()
            self.send_json({"success": False, "error": f"生成学习计划失败: {str(e)}"}, 500)

    def api_learn_plan_progress(self, data):
        """更新学习计划的进度"""
        try:
            job_id = data.get("job_id", "")
            task_id = data.get("task_id", "")  # e.g. "w1_t0" or "w1_d3"
            done = data.get("done", True)
            if not job_id or not task_id:
                self.send_json({"success": False, "error": "缺少参数"}, 400)
                return
            job = self.agent.tracker.get_job(job_id)
            if not job:
                self.send_json({"success": False, "error": "找不到该职位"}, 404)
                return
            progress = job.get("learn_plan_progress", {})
            if task_id in progress:
                progress[task_id]["done"] = bool(done)
            else:
                progress[task_id] = {"done": bool(done), "text": "", "week": 0}
            job["learn_plan_progress"] = progress
            # 计算统计（引用 plan 中的实际任务数量，而非所有 progress key）
            plan = job.get("learn_plan", {})
            total = 0
            done_count = 0
            if plan.get("weekly_plan"):
                for w in plan["weekly_plan"]:
                    if w.get("tasks"):
                        for t_idx, raw_task in enumerate(w["tasks"]):
                            if isinstance(raw_task, dict) and raw_task.get("day_of_week"):
                                pid = f"w{w['week']}_d{raw_task['day_of_week']}"
                            else:
                                pid = f"w{w['week']}_t{t_idx}"
                            total += 1
                            if progress.get(pid, {}).get("done"):
                                done_count += 1
            self.agent.tracker.save()
            self.send_json({"success": True, "progress": progress, "done": done_count, "total": total})
        except Exception as e:
            self.send_json({"success": False, "error": f"更新进度失败: {str(e)}"}, 500)

    def api_learn_plan_progress_GET(self, params):
        """GET: 获取学习计划最新进度（用于 JS 无刷新更新）"""
        try:
            job_id = params.get("job_id", "")
            if not job_id:
                self.send_json({"success": False, "error": "缺少 job_id"}, 400)
                return
            job = self.agent.tracker.get_job(job_id)
            if not job:
                self.send_json({"success": False, "error": "找不到该职位"}, 404)
                return
            progress = job.get("learn_plan_progress", {})
            plan = job.get("learn_plan", {})
            total = 0
            done_count = 0
            if plan.get("weekly_plan"):
                for w in plan["weekly_plan"]:
                    if w.get("tasks"):
                        for t_idx, raw_task in enumerate(w["tasks"]):
                            if isinstance(raw_task, dict) and raw_task.get("day_of_week"):
                                pid = f"w{w['week']}_d{raw_task['day_of_week']}"
                            else:
                                pid = f"w{w['week']}_t{t_idx}"
                            total += 1
                            if progress.get(pid, {}).get("done"):
                                done_count += 1
            self.send_json({"success": True, "progress": progress, "done": done_count, "total": total})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_learn_plan_ical(self, data):
        """导出学习计划为 iCal (.ics) 文件"""
        try:
            job_id = data.get("job_id", "")
            if not job_id:
                self.send_json({"success": False, "error": "缺少 job_id"}, 400)
                return
            job = self.agent.tracker.get_job(job_id)
            if not job or "learn_plan" not in job:
                self.send_json({"success": False, "error": "没有已保存的学习计划"}, 404)
                return
            plan = job["learn_plan"]
            progress = job.get("learn_plan_progress", {})
            title = job.get("title", "学习计划")
            company = job.get("company", "")

            lang = self._get_lang(data)
            learn_plan_week = t(lang, "learn_plan_week")
            lang_sfx = {"en": "", "zh-CN": "\u5468", "fr": ""}
            learn_plan_suffix = lang_sfx.get(lang, "")
            import uuid
            now = datetime.datetime.utcnow()
            lines = []
            lines.append("BEGIN:VCALENDAR")
            lines.append("VERSION:2.0")
            lines.append("PRODID:-//JobAgent//LearnPlan//EN")
            lines.append("CALSCALE:GREGORIAN")
            lines.append("METHOD:PUBLISH")
            lines.append("X-WR-CALNAME:技能强化计划 - " + title)
            lines.append("X-WR-TIMECONE:UTC")

            base_date = now.date()
            if plan.get("weekly_plan"):
                for w in plan["weekly_plan"]:
                    week_num = w.get("week", 1)
                    # Calculate Monday of this week
                    monday = base_date - datetime.timedelta(days=base_date.weekday()) + datetime.timedelta(weeks=week_num - 1)
                    focus = w.get("focus", f"{learn_plan_week}{week_num}{learn_plan_suffix}")
                    # Create individual events per task (Mon-Fri)
                    if w.get("tasks"):
                        for t_idx, raw in enumerate(w["tasks"]):
                            if isinstance(raw, dict):
                                task_name = raw.get("name", "")
                                task_dow = raw.get("day_of_week")  # 1=Mon..5=Fri
                            else:
                                task_name = raw
                                task_dow = None
                            if task_dow is not None:
                                task_date = monday + datetime.timedelta(days=task_dow - 1)
                            else:
                                # Old format: distribute across Mon-Fri
                                task_date = monday + datetime.timedelta(days=t_idx % 5)
                            # Skip weekends
                            if task_date.weekday() >= 5:
                                continue
                            tid = f"w{week_num}_t{t_idx}" if task_dow is None else f"w{week_num}_d{task_dow}"
                            p = progress.get(tid, {})
                            mark = "✅" if p.get("done") else "⬜"
                            advice = p.get("advice", "") if isinstance(raw, dict) else ""
                            uid = str(uuid.uuid4())
                            lines.append("BEGIN:VEVENT")
                            lines.append(f"UID:{uid}@jobagent")
                            lines.append(f"DTSTART;VALUE=DATE:{task_date.strftime('%Y%m%d')}")
                            lines.append(f"DTEND;VALUE=DATE:{(task_date + datetime.timedelta(days=1)).strftime('%Y%m%d')}")
                            lines.append(f"SUMMARY:{mark} {task_name}")
                            desc = f"目标职位: {company} - {title}\
"
                            desc += f"第{week_num}周 · {focus}\
"
                            if advice:
                                desc += f"\
建议: {advice}"
                            lines.append(f"DESCRIPTION:{desc}")
                            lines.append("END:VEVENT")
                    else:
                        # Fallback: weekly summary event if no tasks
                        uid = str(uuid.uuid4())
                        lines.append("BEGIN:VEVENT")
                        lines.append(f"UID:{uid}@jobagent")
                        lines.append(f"DTSTART;VALUE=DATE:{monday.strftime('%Y%m%d')}")
                        week_end = monday + datetime.timedelta(days=6)
                        lines.append(f"DTEND;VALUE=DATE:{week_end.strftime('%Y%m%d')}")
                        lines.append(f"SUMMARY:📚 第{week_num}周: {focus}")
                        lines.append("END:VEVENT")

            if plan.get("advice"):
                uid = str(uuid.uuid4())
                lines.append("BEGIN:VTODO")
                lines.append(f"UID:{uid}@jobagent")
                lines.append(f"SUMMARY:💡 学习建议")
                lines.append(f"DESCRIPTION:{plan['advice']}")
                lines.append("STATUS:NEEDS-ACTION")
                lines.append("END:VTODO")

            lines.append("END:VCALENDAR")
            ical_content = "\r\n".join(lines)

            self.send_response(200)
            self.send_header("Content-Type", "text/calendar; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="learn_plan_{job_id}.ics"')
            self.send_header("Content-Length", str(len(ical_content.encode())))
            self.end_headers()
            self.wfile.write(ical_content.encode())
        except Exception as e:
            self.send_json({"success": False, "error": f"导出日历失败: {str(e)}"}, 500)

    def api_generate_quiz(self, data):
        """Generate quiz on demand"""
        import urllib.request
        import json as jq
        try:
            job_id = data.get("job_id", "")
            task_id = data.get("task_id", "")
            lang = data.get("lang", "zh-CN")
            if not job_id or not task_id:
                self.send_json({"success": False, "error": "缺少参数"}, 400)
                return
            job = self.agent.tracker.get_job(job_id)
            if not job:
                self.send_json({"success": False, "error": "找不到该职位"}, 404)
                return
            plan = job.get("learn_plan", {})
            progress = job.get("learn_plan_progress", {})
            # Find task text and context
            task_text = ""
            task_advice = ""
            week_focus = ""
            if plan.get("weekly_plan"):
                for w in plan["weekly_plan"]:
                    week_num = w.get("week", 0)
                    if w.get("tasks"):
                        for t_idx, raw in enumerate(w["tasks"]):
                            if isinstance(raw, dict) and raw.get("day_of_week"):
                                tid = f"w{week_num}_d{raw['day_of_week']}"
                            else:
                                tid = f"w{week_num}_t{t_idx}"
                            if tid == task_id:
                                task_text = raw.get("name", "") if isinstance(raw, dict) else raw
                                task_advice = raw.get("advice", "") if isinstance(raw, dict) else ""
                                week_focus = w.get("focus", "")
                                break
                    if task_text:
                        break
            
            position = plan.get("position", "")
            focus_skills = [s.get("skill", "") for s in plan.get("focus_skills", [])]
            
            # Build prompt for 5 quiz questions
            if lang == "zh-CN":
                quiz_prompt = f"""根据以下学习任务生成5道测试题（4道选择题 + 1道简答题），严格返回JSON数组。

### 目标职位
{position}

### 关键技能
{', '.join(focus_skills[:3])}

### 当前任务
任务: {task_text}
学习建议: {task_advice}
所属周主题: {week_focus}

### 输出格式
[
  {{"q": "问题", "type": "choice", "options": ["A选项", "B选项", "C选项", "D选项"], "answer": 0}},
  {{"q": "问题2", "type": "essay", "reference": "参考答案要点"}}
]

要求：选择题答案索引从0开始，简答题提供参考要点。每题都针对该学习任务的核心知识点设计。"""
            else:
                quiz_prompt = f"""Based on the following learning task, generate 5 quiz questions (4 multiple-choice + 1 essay). Return a strict JSON array.

### Target Position
{position}

### Key Skills
{', '.join(focus_skills[:3])}

### Current Task
Task: {task_text}
Study Advice: {task_advice}
Week Theme: {week_focus}

### Output Format
[
  {{"q": "Question", "type": "choice", "options": ["Option A", "Option B", "Option C", "Option D"], "answer": 0}},
  {{"q": "Question 2", "type": "essay", "reference": "Reference answer key points"}}
]

Requirements: Choice answers use 0-based index. Essay questions provide reference key points. Each question must target core knowledge of the learning task."""

            api_key = os.environ.get("DEEPSEEK_API_KEY", "")
            if not api_key:
                models_cfg = os.path.expanduser("~/.openclaw/agents/main/agent/models.json")
                if os.path.exists(models_cfg):
                    with open(models_cfg) as f:
                        cfg = jq.load(f)
                    api_key = cfg.get("providers", {}).get("deepseek", {}).get("apiKey", "")
            if not api_key:
                self.send_json({"success": False, "error": "未找到 API Key"}, 500)
                return

            req_body = jq.dumps({
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": ("你是技术面试官。生成测试题，只输出JSON数组。" if lang == "zh-CN" else "You are a technical interviewer. Generate quiz questions, output only JSON array.")},
                    {"role": "user", "content": quiz_prompt}
                ],
                "temperature": 0.5,
                "max_tokens": 2048,
                "stream": False
            })
            req = urllib.request.Request(
                "https://api.deepseek.com/chat/completions",
                data=req_body.encode(),
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + api_key},
                method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=60)
            result = jq.loads(resp.read().decode())
            quiz_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            quiz_content = quiz_content.strip()
            if quiz_content.startswith("```"):
                quiz_content = quiz_content.split("\n", 1)[-1]
                quiz_content = quiz_content.rsplit("```", 1)[0].strip()
            if quiz_content.startswith("json"):
                quiz_content = quiz_content[4:].strip()
            quiz_data = jq.loads(quiz_content)
            # Limit to 5
            if len(quiz_data) > 5:
                quiz_data = quiz_data[:5]
            self.send_json({"success": True, "quiz": quiz_data})
        except json.JSONDecodeError:
            self.send_json({"success": False, "error": "AI 返回格式异常"}, 500)
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def api_quiz_submit(self, data):
        """保存测验成绩"""
        try:
            job_id = data.get("job_id", "")
            task_id = data.get("task_id", "")
            score = data.get("score", 0)
            total = data.get("total", 0)
            if not job_id or not task_id:
                self.send_json({"success": False, "error": "缺少参数"}, 400)
                return
            job = self.agent.tracker.get_job(job_id)
            if not job:
                self.send_json({"success": False, "error": "找不到该职位"}, 404)
                return
            progress = job.get("learn_plan_progress", {})
            if task_id in progress:
                progress[task_id]["quiz_score"] = {"score": score, "total": total}
            job["learn_plan_progress"] = progress
            self.agent.tracker.save()
            self.send_json({"success": True, "score": score, "total": total})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def _find_job_from_cache(self, job_id: str) -> Optional[Dict]:
        """从搜索缓存中查找职位"""
        try:
            from job_agent_core import JobAgent
            md_path = os.path.join(os.path.dirname(self.agent.data_dir), "search_cache.md")
            if os.path.exists(md_path):
                # 简单的 KEY=VALUE 解析
                import re
                for line in open(md_path, encoding="utf-8"):
                    parts = line.strip().split("=", 1)
                    if len(parts) == 2 and parts[0] == f"job_{job_id}":
                        return json.loads(parts[1])
        except:
            pass
        return None

    # ===================== 页面 =====================

    def handle_resume_page(self, params):
        lang = self._get_lang(params)
        html = self._page(t(lang, 'resume_title'), f"""
        <h1>{t(lang, 'resume_title')}</h1>
        <div id="resume-list"></div>
        <div style="margin-top:16px">
            <button onclick="uploadResume()" class="btn btn-primary">{t(lang, 'resume_upload')}</button>
            <span style="margin-left:8px;color:#888;font-size:12px">{t(lang, 'resume_upload_hint')}</span>
        </div>
        <script>
        var RESUME_EMPTY = '{t(lang, 'resume_empty')}';
        var RESUME_DELETE = '{t(lang, 'resume_delete')}';
        var RESUME_PREVIEW = '{t(lang, 'btn_preview')}';
        var RESUME_DOWNLOAD = '{t(lang, 'btn_download')}';
        async function loadResumes() {{
            var resp = await (await fetch('/api/list_resumes')).json();
            var list = document.getElementById('resume-list');
            if (!resp.success || resp.resumes.length === 0) {{
                list.innerHTML = '<p style="margin-top:16px;color:#888">' + RESUME_EMPTY + '</p>';
                return;
            }}
            var h = '';
            resp.resumes.forEach(function(r) {{
                h += '<div class="resume-card">';
                h += '<div><span class="resume-name">\U0001F4C4 ' + r.name + '</span><br><span class="resume-date">' + r.created_at + '</span></div>';
                h += '<div class="resume-actions">';
                h += '<button data-resume-id="' + r.id + '" class="btn btn-small btn-preview-resume">' + RESUME_PREVIEW + '</button>';
                h += '<button data-resume-id="' + r.id + '" class="btn btn-small btn-download-resume" style="margin-left:4px">' + RESUME_DOWNLOAD + '</button>';
                h += '<button data-resume-id="' + r.id + '" class="btn btn-small btn-delete btn-del-resume" style="margin-left:4px">' + RESUME_DELETE + '</button>';
                h += '</div></div>';
            }});
            list.innerHTML = h;
        }}

        // Event delegation
        document.addEventListener('click', function(e) {{
            var previewBtn = e.target.closest('.btn-preview-resume');
            if (previewBtn) {{
                e.preventDefault();
                var rid = previewBtn.getAttribute('data-resume-id');
                showResumeLibraryPreview(rid);
                return;
            }}
            var downloadBtn = e.target.closest('.btn-download-resume');
            if (downloadBtn) {{
                e.preventDefault();
                var rid = downloadBtn.getAttribute('data-resume-id');
                window.open('/api/get_resume?resume_id=' + rid, '_blank');
                return;
            }}
            var closeBtn = e.target.closest('.resume-lib-modal-close');
            if (closeBtn) {{
                var modal = closeBtn.closest('#resume-lib-preview-modal');
                if (modal) modal.remove();
                return;
            }}
            var delBtn = e.target.closest('.btn-del-resume');
            if (!delBtn) return;
            var id = delBtn.getAttribute('data-resume-id');
            if (!confirm('\u786E\u5B9A\u5220\u9664\uFF1F')) return;
            fetch('/api/delete_resume', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{resume_id:id}})}})
              .then(function(r){{ return r.json(); }})
              .then(function(d){{ if(d.success) loadResumes(); }});
        }});

        async function showResumeLibraryPreview(resumeId) {{
            var old = document.getElementById('resume-lib-preview-modal');
            if (old) old.remove();
            var h = '<div id="resume-lib-preview-modal" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:1000;display:flex;align-items:center;justify-content:center">';
            h += '<div style="background:#fff;border-radius:12px;padding:0;max-width:700px;width:95%;box-shadow:0 8px 32px rgba(0,0,0,0.2);display:flex;flex-direction:column;max-height:85vh">';
            h += '<div style="display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-bottom:1px solid #e0e0e0;flex-shrink:0">';
            h += '<h3 style="margin:0;font-size:16px">\U0001F4C4 \u7B80\u5386\u9884\u89C8</h3>';
            h += '<div>';
            h += '<a href="/api/get_resume?resume_id=' + resumeId + '" target="_blank" class="btn" style="margin-right:8px;font-size:13px;padding:5px 12px">\U0001F4E5 \u4E0B\u8F7D</a>';
            h += '<button class="resume-lib-modal-close" style="background:none;border:none;font-size:20px;cursor:pointer;color:#888;padding:4px;line-height:1">\u00d7</button>';
            h += '</div></div>';
            h += '<div id="resume-lib-preview-content" style="overflow-y:auto;padding:20px;line-height:1.7;font-size:14px;flex:1">';
            h += '<div style="text-align:center;padding:40px;color:#999">\u52A0\u8F7D\u4E2D...</div></div>';
            h += '</div></div>';
            document.body.insertAdjacentHTML('beforeend', h);
            // Click overlay to close
            var modal = document.getElementById('resume-lib-preview-modal');
            modal.addEventListener('click', function(ev) {{
                if (ev.target === modal) modal.remove();
            }});
            try {{
                var r = await fetch('/api/preview_resume?resume_id=' + resumeId);
                document.getElementById('resume-lib-preview-content').innerHTML = await r.text() || '<p style="color:#888">\u6682\u65E0\u5185\u5BB9</p>';
            }} catch(e) {{
                document.getElementById('resume-lib-preview-content').innerHTML = '<p style="color:red">\u52A0\u8F7D\u5931\u8D25: ' + e + '</p>';
            }}
        }}

        async function uploadResume() {{
            var input = document.createElement('input');
            input.type = 'file';
            input.accept = '.pdf,.doc,.docx';
            input.style.display = 'none';
            document.body.appendChild(input);
            input.onchange = async function(e) {{
                var file = e.target.files[0];
                if (!file) {{ document.body.removeChild(input); return; }}
                var formData = new FormData();
                formData.append('name', file.name);
                formData.append('resume', file);
                try {{
                    var resp = await fetch('/api/add_resume_multipart', {{method:'POST', body:formData}});
                    var d = await resp.json();
                    if (d.success) {{
                        loadResumes();
                    }} else {{
                        alert('\u4E0A\u4F20\u5931\u8D25: ' + (d.error || ''));
                    }}
                }} catch(e) {{
                    alert('\u4E0A\u4F20\u51FA\u9519: ' + e);
                }}
                document.body.removeChild(input);
            }};
            input.click();
        }}
        loadResumes();
        </script>
        """, lang=lang)
        self._send_html(html)

    def _resume_page_script(self):
        return ''

    def _tracked_resume_modal_html(self, lang: str = "zh-CN") -> str:
        """返回跟踪页简历弹窗所需的 JS（硬编码文本已在 JS 文件中替换为变量引用）"""
        base = os.path.join(os.path.dirname(__file__), 'resume_modal_script.js')
        try:
            with open(base, 'r', encoding='utf-8') as _f:
                return '<script>\n' + _f.read() + '\n</script>'
        except Exception:
            return ''

    def handle_resume_view_page(self, params):
        """简历查看/编辑页"""
        job_id = params.get("job_id", "")
        lang = params.get("lang", "zh-CN")
        if not job_id:
            self._send_html('<html><body><p style="padding:40px;color:#888">缺少 job_id</p></body></html>')
            return
        job = None
        for j in self.agent.tracker.tracked_jobs:
            if j["id"] == job_id:
                job = j
                break
        if not job or not job.get("resume_id"):
            self._send_html(f'<html><body><p style="padding:40px;color:#888">未找到职位或未关联简历</p></body></html>')
            return
        resume_name = job.get("resume_name", "简历")
        resume_id = job["resume_id"]
        i18n = {}
        for k in ["resume_edit_title", "resume_edit_subtitle", "btn_back", "btn_export_pdf",
                   "btn_exporting", "md_editor_label", "md_editor_placeholder", "preview_failed",
                   "toolbar_bold", "toolbar_heading", "toolbar_list", "toolbar_link",
                   "status_saved", "status_save_failed", "status_save_error",
                   "status_export_failed", "status_export_error",
                   "btn_save", "_loading_text", "_load_failed"]:
            i18n[k] = t(lang, k)
        html = self._build_resume_editor_page(job_id, resume_name, lang, **i18n)
        self._send_html(html)

    def _build_resume_editor_page(self, job_id: str, resume_name: str, lang: str = "zh-CN", **kw) -> str:
        """Markdown简历编辑器页面 - 分栏布局"""
        import json
        e_title = kw.get("resume_edit_title", "Edit Resume - ")
        e_subtitle = kw.get("resume_edit_subtitle", "Job-specific copy")
        b_back = kw.get("btn_back", "← Back")
        b_export_pdf = kw.get("btn_export_pdf", "📄 Export PDF")
        b_exporting = kw.get("btn_exporting", "Generating...")
        b_save = kw.get("btn_save", "💾 Save")
        m_label = kw.get("md_editor_label", "Markdown Editor")
        m_ph = kw.get("md_editor_placeholder", "Edit...")
        p_fail = kw.get("preview_failed", "Preview failed")
        tb_bold = kw.get("toolbar_bold", "Bold")
        tb_heading = kw.get("toolbar_heading", "Heading")
        tb_list = kw.get("toolbar_list", "List")
        tb_link = kw.get("toolbar_link", "Link")
        s_saved = kw.get("status_saved", "✅ Saved")
        s_save_failed = kw.get("status_save_failed", "❌ Save failed: ")
        s_save_error = kw.get("status_save_error", "❌ Save error: ")
        s_exp_fail = kw.get("status_export_failed", "Export failed: ")
        s_exp_err = kw.get("status_export_error", "Export error: ")
        loading = kw.get("_loading_text", "Loading...")
        load_fail = kw.get("_load_failed", "❌ Load failed: ")
        return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e_title}{resume_name}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#f0f2f5; color:#333; padding:0; display:flex; flex-direction:column; height:100vh; font-size:16px; }}
.header {{ display:flex; align-items:center; justify-content:space-between; padding:12px 20px; background:#fff; border-bottom:1px solid #e0e0e0; flex-shrink:0; }}
.header h1 {{ font-size:20px; }}
.header .subtitle {{ font-size:14px; color:#888; font-weight:normal; margin-left:8px; }}
.btn {{ display:inline-block; padding:8px 16px; background:#f5f5f5; color:#333; border:1px solid #ddd; border-radius:6px; cursor:pointer; text-decoration:none; font-size:14px; }}
.btn:hover {{ background:#e8e8e8; }}
.btn-save {{ background:#34a853; color:#fff; border:none; }}
.btn-save:hover {{ background:#2d9249; }}
.btn-download {{ background:#5f6368; color:#fff; border:none; }}
.btn-download:hover {{ background:#4a4d52; }}
.btn-back {{ background:none; color:#555; border:none; font-size:15px; }}
.btn-back:hover {{ color:#000; }}
.main {{ display:flex; flex:1; overflow:hidden; }}
.editor-pane {{ flex:1; display:flex; flex-direction:column; border-right:1px solid #e0e0e0; background:#fff; }}
.editor-pane textarea {{ flex:1; width:100%; border:none; outline:none; padding:20px; font-family:'SF Mono',Monaco,'Cascadia Code',Consolas,monospace; font-size:15px; line-height:1.7; resize:none; }}
.editor-toolbar {{ display:flex; align-items:center; gap:6px; padding:10px 14px; background:#f8f9fa; border-bottom:1px solid #e0e0e0; font-size:14px; color:#666; flex-shrink:0; }}
.editor-toolbar .btn-icon {{ padding:4px 10px; font-size:14px; cursor:pointer; border-radius:4px; background:none; border:1px solid transparent; font-weight:600; }}
.editor-toolbar .btn-icon:hover {{ background:#e0e0e0; border-color:#ccc; }}
.preview-pane {{ flex:1; overflow-y:auto; padding:24px; background:#fff; line-height:1.7; font-size:14px; }}
.preview-pane h1 {{ font-size:22px; margin:16px 0 8px; }}
.preview-pane h2 {{ font-size:18px; margin:14px 0 6px; border-bottom:1px solid #eee; padding-bottom:4px; }}
.preview-pane h3 {{ font-size:16px; margin:12px 0 4px; }}
.preview-pane p {{ margin:6px 0; }}
.preview-pane ul, .preview-pane ol {{ margin:6px 0; padding-left:24px; }}
.preview-pane li {{ margin:3px 0; }}
.preview-pane a {{ color:#1a73e8; }}
.preview-pane strong {{ color:#111; }}
.status {{ position:fixed; bottom:20px; right:20px; padding:8px 16px; border-radius:6px; font-size:14px; z-index:100; opacity:0; transition:opacity 0.3s; }}
.status.show {{ opacity:1; }}
.status.success {{ background:#e6f4ea; color:#2e7d32; }}
.status.error {{ background:#fce8e6; color:#d32f2f; }}
</style>
</head>
<body>
<div class="header">
  <div><h1>📄 {resume_name} <span class="subtitle">{e_subtitle}</span></h1></div>
  <div>
    <a href="/tracked?lang={lang}" class="btn btn-back">{b_back}</a>
    <button onclick="exportPdf()" class="btn btn-download" id="exportBtn">{b_export_pdf}</button>
    <button onclick="saveResume()" class="btn btn-save">{b_save}</button>
  </div>
</div>
<div id="statusMsg" class="status">{s_saved}</div>
<div class="main">
  <div class="editor-pane">
    <div class="editor-toolbar">
      <span>{m_label}</span>
      <span style="flex:1"></span>
      <button class="btn-icon" onclick="insertMd('**','**')" title="{tb_bold}">B</button>
      <button class="btn-icon" onclick="insertMd('## ','\n## ')" title="{tb_heading}">H</button>
      <button class="btn-icon" onclick="insertMd('\\n- ','\n  ')" title="{tb_list}">•</button>
      <button class="btn-icon" onclick="insertMd('[','](url)')" title="{tb_link}">🔗</button>
    </div>
    <textarea id="editor" spellcheck="false" placeholder="{m_ph}"></textarea>
  </div>
  <div class="preview-pane" id="preview">{loading}</div>
</div>
<script>
var jobId = {json.dumps(job_id, ensure_ascii=False)};
var originalMd = "";
var timer = null;
var _loading_text = {json.dumps(loading, ensure_ascii=False)};
var _load_failed = {json.dumps(load_fail, ensure_ascii=False)};
var _p_fail = {json.dumps(p_fail, ensure_ascii=False)};
var _s_saved = {json.dumps(s_saved, ensure_ascii=False)};
var _s_save_failed = {json.dumps(s_save_failed, ensure_ascii=False)};
var _s_save_error = {json.dumps(s_save_error, ensure_ascii=False)};
var _s_exp_fail = {json.dumps(s_exp_fail, ensure_ascii=False)};
var _s_exp_err = {json.dumps(s_exp_err, ensure_ascii=False)};
var _b_exporting = {json.dumps(b_exporting, ensure_ascii=False)};
var _b_export_pdf = {json.dumps(b_export_pdf, ensure_ascii=False)};

function insertMd(before, after) {{
  var ta = document.getElementById('editor');
  var start = ta.selectionStart;
  var end = ta.selectionEnd;
  var selected = ta.value.substring(start, end);
  ta.value = ta.value.substring(0, start) + before + selected + after + ta.value.substring(end);
  ta.selectionStart = start + before.length;
  ta.selectionEnd = start + before.length + selected.length;
  ta.focus();
  renderPreview(ta.value);
}}

async function loadResume() {{
  try {{
    var resp = await fetch('/api/get_resume_markdown', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id: jobId}})}});
    var d = await resp.json();
    if (d.success) {{
      originalMd = d.markdown || "";
      document.getElementById('editor').value = originalMd;
      renderPreview(originalMd);
    }} else {{
      document.getElementById('preview').innerHTML = '<p style="color:red">' + _load_failed + (d.error || '') + '</p>';
    }}
  }} catch(e) {{
    document.getElementById('preview').innerHTML = '<p style="color:red">' + _load_failed + e + '</p>';
  }}
}}

async function renderPreview(text) {{
  try {{
    var resp = await fetch('/api/convert_markdown', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{markdown: text}})}});
    var d = await resp.json();
    if (d.success) {{
      document.getElementById('preview').innerHTML = d.html;
    }} else {{
      document.getElementById('preview').innerHTML = '<p style="color:red">' + _p_fail + '</p><pre>' + text + '</pre>';
    }}
  }} catch(e) {{
    document.getElementById('preview').innerHTML = '<pre>' + text + '</pre>';
  }}
}}

async function saveResume() {{
  var md = document.getElementById('editor').value;
  try {{
    var resp = await fetch('/api/save_job_resume_md', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id: jobId, markdown: md}})}});
    var d = await resp.json();
    var status = document.getElementById('statusMsg');
    status.className = 'status ' + (d.success ? 'show success' : 'show error');
    status.textContent = d.success ? _s_saved : _s_save_failed + (d.error || '');
    setTimeout(function() {{ status.className = 'status'; }}, 3000);
    if (d.success) originalMd = md;
  }} catch(e) {{
    var status = document.getElementById('statusMsg');
    status.className = 'status show error';
    status.textContent = _s_save_error + e;
  }}
}}

async function exportPdf() {{
  var btn = document.getElementById('exportBtn');
  btn.disabled = true;
  btn.textContent = _b_exporting;
  try {{
    var resp = await fetch('/api/download_resume_pdf', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id: jobId}})}});
    if (!resp.ok) {{
      var d = await resp.json();
      alert(_s_exp_fail + (d.error || ''));
      return;
    }}
    var blob = await resp.blob();
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'resume_' + jobId + '.pdf';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  }} catch(e) {{
    alert(_s_exp_err + e);
  }} finally {{
    btn.disabled = false;
    btn.textContent = _b_export_pdf;
  }}
}}

document.addEventListener('keydown', function(e) {{
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {{
    e.preventDefault();
    saveResume();
  }}
}});

document.getElementById('editor').addEventListener('input', function() {{
  clearTimeout(timer);
  timer = setTimeout(function() {{
    renderPreview(document.getElementById('editor').value);
  }}, 500);
}});

loadResume();
</script>
</body>
</html>"""

    def _render_skill_gap_html(self, job_data, lang):
        """Render skill gap HTML from job data using i18n labels."""
        gap_data = job_data.get("skill_gap_data")
        if not gap_data:
            return job_data.get("skill_gap_html", "")

        _t = lambda k: t(lang, k)
        missing = gap_data.get("missing", [])
        weak = gap_data.get("weak", [])
        matching = gap_data.get("matching", [])
        suggestions = gap_data.get("suggestions", [])

        parts = []
        for s in missing[:5]:
            parts.append(f'<span class="skill-gap-badge gap-missing" title="{_t("gap_missing")}" style="display:inline-block;background:#fee;color:#d32f2f;border:1px solid #fcc;border-radius:4px;padding:1px 6px;font-size:11px;margin:1px">\u26a0 {s}</span>')
        for s in weak[:3]:
            parts.append(f'<span class="skill-gap-badge gap-weak" title="{_t("gap_weak")}" style="display:inline-block;background:#fff3e0;color:#e65100;border:1px solid #ffe0b2;border-radius:4px;padding:1px 6px;font-size:11px;margin:1px">\u2191 {s}</span>')

        details_html = ""
        if matching:
            details_html += f"<div style='margin-bottom:6px'><b>{_t('gap_skills')}:</b> " + ", ".join(matching) + "</div>"
        if missing:
            details_html += f"<div style='margin-bottom:6px;color:#d32f2f'><b>{_t('gap_missing')}:</b> " + ", ".join(missing) + "</div>"
        if weak:
            details_html += f"<div style='margin-bottom:6px;color:#e65100'><b>{_t('gap_weak')}:</b> " + ", ".join(weak) + "</div>"
        if suggestions:
            details_html += f"<div style='margin-top:6px;color:#1565c0;font-size:12px'><b>{_t('gap_suggestions')}:</b><br>" + "<br>".join(suggestions) + "</div>"

        import json as j
        import html
        gap_html = "".join(parts)
        if gap_html:
            details_escaped = html.escape(j.dumps(details_html, ensure_ascii=False))
            gap_html = '<span class="skill-gap-group" style="display:inline-block;margin-left:4px;cursor:pointer" data-gap-details="' + details_escaped + '" data-gap-jobid="' + str(job_data.get("id","")) + '">' + gap_html + '</span>'
        return gap_html

    def _page(self, title, body, lang="zh-CN"):
        nav_items = ""
        pages = [
            ("/", t(lang, "nav_home")),
            ("/dashboard", t(lang, "nav_dashboard")),
            ("/search", t(lang, "nav_search")),
            ("/tracked", t(lang, "nav_tracked")),
            ("/profile", t(lang, "nav_profile")),
            ("/letter", t(lang, "nav_letter")),
            ("/resumes", t(lang, "nav_resume")),
            ("/learn_plan", t(lang, "nav_learn_calendar")),
        ]
        # Persist lang in nav links so switching pages doesn't lose language
        qs = f"?lang={lang}"
        for href, text in pages:
            nav_items += f'<a href="{href}{qs}" class="nav-link">{text}</a>'
        # 语言切换：下拉选择框
        lang_labels = {"zh-CN": "🇨🇳 中文", "en": "🇬🇧 English", "fr": "🇫🇷 Français"}
        lang_options_html = "".join(
            f'<option value="{k}"{" selected" if k == lang else ""}>{v}</option>'
            for k, v in lang_labels.items()
        )
        lang_switch = f'<select onchange="window.location.href=\'?lang=\'+this.value" class="lang-select" style="margin-left:auto;font-size:12px;border:none;background:none;outline:none;cursor:pointer;color:#1a73e8">{lang_options_html}</select>'
        
        html_lang = lang if lang in LANGUAGES else "zh-CN"
        site_name = t(lang, "page_title")
        return f"""<!DOCTYPE html>
        <html lang="{html_lang}">

        <head>

        <meta charset="UTF-8">

        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <title>{title} - {site_name}</title>

        <style>

        * {{ margin:0; padding:0; box-sizing:border-box; }}

        body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#f0f2f5; color:#333; font-size:16px; }}

        nav {{ background:#fff; display:flex; padding:0 16px; box-shadow:0 2px 8px rgba(0,0,0,0.1); gap:8px; overflow-x:auto; position:sticky; top:0; z-index:100; }}

        nav a {{ padding:14px 14px; text-decoration:none; color:#666; font-weight:500; font-size:15px; border-bottom:3px solid transparent; white-space:nowrap; }}

        nav a:hover {{ color:#333; }}

        nav a.active {{ color:#1a73e8; border-bottom-color:#1a73e8; }}

        .container {{ max-width:1200px; margin:0 auto; padding:20px 28px; }}

        h1 {{ margin-bottom:20px; }}

        .hero {{ text-align:center; padding:60px 30px 40px; }}

        .hero h1 {{ font-size:48px; }}

        .subtitle {{ color:#666; font-size:18px; margin:10px 0 28px; }}

        .hero-actions {{ display:flex; gap:12px; justify-content:center; flex-wrap:wrap; }}

        .features {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:16px; margin:30px 0; }}

        .feature-card {{ background:#fff; padding:24px; border-radius:10px; box-shadow:0 2px 6px rgba(0,0,0,0.06); text-align:center; }}

        .feature-icon {{ font-size:32px; margin-bottom:8px; }}

        .feature-card h3 {{ margin-bottom:6px; font-size:16px; }}

        .feature-card p {{ color:#666; font-size:13px; line-height:1.5; }}

        .btn {{ display:inline-block; padding:8px 16px; background:#f5f5f5; color:#333; border:1px solid #ddd; border-radius:6px; cursor:pointer; text-decoration:none; font-size:14px; }}

        .btn:hover {{ background:#e8e8e8; }}

        .btn-primary {{ background:#1a73e8; color:#fff; border:none; }}

        .btn-primary:hover {{ background:#1557b0; }}

        .btn-secondary {{ background:#5f6368; color:#fff; border:none; }}

        .btn-lg {{ padding:14px 28px; font-size:16px; }}

        .btn-small {{ padding:5px 12px; font-size:14px; }}

        .btn-save {{ background:#34a853; color:#fff; border:none; }}

        .btn-save:hover {{ background:#2d9249; }}

        .btn-interview {{ background:#fbbc04; color:#333; border:none; }}

        .btn-reject {{ background:#ea4335; color:#fff; border:none; }}

        .btn-offer {{ background:#9c27b0; color:#fff; border:none; }}

        .btn-delete {{ background:#d32f2f; color:#fff; border:none; }}


        .stats-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:12px; margin:16px 0; }}

        .stat-card {{ background:#fff; padding:16px; border-radius:8px; text-align:center; box-shadow:0 2px 6px rgba(0,0,0,0.06); }}

        .stat-number {{ font-size:28px; font-weight:700; color:#1a73e8; }}

        .stat-label {{ color:#666; font-size:12px; margin-top:4px; }}

        .status-bar {{ display:flex; height:32px; border-radius:6px; overflow:hidden; margin:12px 0; font-size:12px; color:#fff; font-weight:500; }}

        .status-segment {{ display:flex; align-items:center; justify-content:center; padding:0 6px; }}

        .skills-list {{ margin:12px 0; }}

        .skill-item {{ display:flex; align-items:center; gap:12px; padding:10px 0; border-bottom:1px solid #eee; }}

        .skill-name {{ width:90px; font-weight:500; }}

        .skill-level {{ flex:1; }}

        .skill-years {{ color:#888; font-size:12px; }}

        .dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:3px; background:#ddd; }}

        .dot.filled {{ background:#1a73e8; }}

        .job-card {{ background:#fff; border-radius:10px; padding:18px; margin:12px 0; box-shadow:0 1px 4px rgba(0,0,0,0.08); }}

        .job-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }}

        .job-title {{ font-weight:600; font-size:17px; }}

        .job-score {{ padding:3px 12px; border-radius:14px; font-size:14px; font-weight:600; }}

        .score-high {{ background:#e6f4ea; color:#34a853; }}

        .score-medium {{ background:#fef7e0; color:#f9ab00; }}

        .score-low {{ background:#fce8e6; color:#ea4335; }}

        .job-type-tag {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:600; background:#e8f5e9; color:#2e7d32; vertical-align:middle; margin-left:4px; }}

        .job-meta {{ display:flex; flex-wrap:wrap; gap:14px; font-size:15px; color:#666; margin-bottom:8px; }}

        .job-desc {{ font-size:15px; color:#555; margin-bottom:10px; line-height:1.55; }}

        .job-desc-full {{ font-size:15px; color:#333; margin-bottom:10px; line-height:1.65; white-space:pre-wrap; max-height:none; overflow-y:visible; padding:12px; background:#f9f9f9; border-radius:4px; border:1px solid #eee; }}

        .job-actions {{ display:flex; gap:6px; flex-wrap:wrap; }}

        .job-notes {{ margin-top:6px; color:#888; font-size:14px; }}

        .job-resume {{ margin-top:8px; display:flex; flex-wrap:wrap; align-items:center; gap:6px; font-size:14px; }}
        .resume-icon {{ font-size:18px; line-height:1; }}
        .resume-name {{ font-weight:500; color:#333; }}
        .resume-actions {{ display:flex; flex-wrap:wrap; align-items:center; gap:8px; margin-left:auto; }}
        .resume-actions .link-url {{ display:inline; color:#1a73e8; font-size:13px; }}
        .resume-actions .btn-small {{ font-size:12px; }}

        .search-summary {{ margin:18px 0; }}

        .result-stats {{ display:flex; gap:16px; margin:10px 0; }}

        .link-item {{ background:#fff; border-radius:6px; padding:14px; margin:10px 0; font-size:15px; }}

        .link-url {{ color:#1a73e8; word-break:break-all; display:block; margin-top:3px; }}

        .tab-bar {{ display:flex; flex-wrap:wrap; gap:4px; }}

        .tab {{ padding:8px 16px; border-radius:20px; font-size:14px; text-decoration:none; color:#666; background:#e8e8e8; }}

        .tab.active {{ background:#1a73e8; color:#fff; }}

        .status-tag {{ padding:3px 12px; border-radius:14px; font-size:13px; font-weight:500; }}

        .job-desc-snippet {{ font-size:15px; color:#555; margin-bottom:10px; line-height:1.55; padding:4px 0; border-bottom:1px solid #eee; }}

        .status-saved {{ background:#f0f0f0; color:#666; }}

        .status-applied {{ background:#e8f0fe; color:#1a73e8; }}

        .status-interviewing {{ background:#fef7e0; color:#f9ab00; }}

        .status-rejected {{ background:#fce8e6; color:#ea4335; }}

        .status-offer {{ background:#e6f4ea; color:#34a853; }}
        .status-time {{ font-size:11px; opacity:0.7; margin-left:4px; }}
        .applied-time {{ font-size:11px; color:#34a853; margin-left:4px; }}
        .job-timeline {{ font-size:12px; color:#666; padding:4px 0 2px 0; }}
        .tl-container {{ margin-top:10px; padding:12px; background:#f5f5f5; border-radius:6px; font-size:13px; }}
        .tl-row {{ display:flex; align-items:center; gap:8px; padding:4px 0; }}
        .tl-icon {{ flex:0 0 24px; text-align:center; }}
        .tl-status {{ flex:0 0 80px; font-weight:500; }}
        .tl-time {{ flex:0 0 auto; color:#888; font-size:12px; }}
        .tl-note {{ color:#555; font-size:12px; margin-left:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:240px; }}
        .tl-sep {{ font-size:11px; color:#999; padding:6px 0 2px 0; border-top:1px dashed #ddd; margin-top:6px; }}

        .section {{ margin:28px 0; }}

        .section h2 {{ margin-bottom:14px; font-size:20px; }}

        .profile-form {{ max-width:480px; }}

        .form-row {{ display:flex; align-items:center; gap:10px; margin:10px 0; }}

        .form-row label {{ width:90px; font-size:14px; color:#555; flex-shrink:0; }}

        .form-row input {{ flex:1; padding:8px 12px; border:1px solid #ddd; border-radius:5px; font-size:14px; }}

        .salary-range {{ display:flex; align-items:center; gap:8px; }}

        .salary-range input {{ width:100px; }}

        .skills-table {{ width:100%; border-collapse:collapse; font-size:14px; }}

        .skills-table th, .skills-table td {{ padding:8px; border-bottom:1px solid #eee; text-align:left; }}

        .skills-table th {{ color:#555; }}

        .search-form {{ background:#fff; padding:16px; border-radius:8px; margin-bottom:12px; }}

        .sources-row {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; }}

        .source-check {{ font-size:13px; display:flex; align-items:center; gap:4px; cursor:pointer; }}

        .source-check .src-link {{ font-size:11px; text-decoration:none; color:#1a73e8; opacity:0.6; transition:opacity .15s; }}
        .source-check .src-link:hover {{ opacity:1; text-decoration:underline; }}

        .select-all-cb {{ font-weight:600; margin-right:6px; border-right:1px solid #ddd; padding-right:10px; }}

        .empty {{ color:#888; padding:30px; text-align:center; }}

        .error {{ color:#ea4335; }}

        .loading {{ text-align:center; padding:20px; }}

        .spinner {{ border:3px solid #f3f3f3; border-top:3px solid #1a73e8; border-radius:50%; width:30px; height:30px; animation:spin .8s linear infinite; margin:0 auto 8px; }}

        @keyframes spin {{ 0%{{transform:rotate(0deg)}} 100%{{transform:rotate(360deg)}} }}

        pre {{ background:#f5f5f5; padding:16px; border-radius:6px; white-space:pre-wrap; font-size:13px; line-height:1.5; }}

        </style>

        </head>

        <body>

        <nav>{nav_items}{lang_switch}</nav>

        <div class="container">{body}</div>

        <script>

        // Persist language preference

        (function() {{

    var lang = '{lang}';
    fetch('/api/update_profile', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{language: lang}})}});
        }})();

        </script>

        </body>

        </html>"""


    def _send_html(self, html):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt, *args):
        pass


def main():
    print("=" * 60)
    print("🤖 求职Agent Web服务")
    print("=" * 60)
    
    # 初始化Agent
    agent = JobAgent()
    JobAgentHandler.agent = agent
    
    print("✅ Agent初始化完成")
    print(f"📁 数据目录: {agent.data_dir}")
    print(f"🎯 技能: {', '.join(agent.profile.get_skill_keywords()[:5])}")
    print(f"📋 已跟踪: {agent.tracker.get_stats()['total']} 个职位")
    print()
    
    # 启动服务器
    server = HTTPServer(("", PORT), JobAgentHandler)
    server.allow_reuse_address = True
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print(f"🌐 访问地址: http://localhost:{PORT}")
    print(f"🌐 也可: http://<本机IP>:{PORT}")
    print("按 Ctrl+C 停止")
    print("=" * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
        server.server_close()


if __name__ == "__main__":
    main()
