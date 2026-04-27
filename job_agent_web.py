#!/usr/bin/env python3
"""
求职Agent - Web界面
美观的浏览器界面，供求职者使用
"""

import json
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
        "cal_weekday_labels": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        "cal_modal_resources": "\U0001f4da Recommended Resources",
        "cal_modal_projects": "\U0001f4a1 Related Projects",
        "cal_modal_advice": "\U0001f4ad Study Advice"

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
        "saved_to_tracker": "✅ 已保存到跟踪列表，刷新页面查看",
        "cal_month_names": ["1\u6708", "2\u6708", "3\u6708", "4\u6708", "5\u6708", "6\u6708", "7\u6708", "8\u6708", "9\u6708", "10\u6708", "11\u6708", "12\u6708"],
        "cal_weekday_labels": ["\u65e5", "\u4e00", "\u4e8c", "\u4e09", "\u56db", "\u4e94", "\u516d"],
        "cal_modal_resources": "\U0001f4da \u63a8\u8350\u8d44\u6e90",
        "cal_modal_projects": "\U0001f4a1 \u76f8\u5173\u9879\u76ee",
        "cal_modal_advice": "\U0001f4ad \u5b66\u4e60\u5efa\u8bae",
        "link_resume_title": "\U0001f4ce 关联简历",
        "btn_assign": "\U0001f517 关联",
        "upload_new_resume": "\U0001f4e4 上传新简历并关联",
        "cancel": "取消",
        "gap_skills": "\u2705 已有技能",
        "gap_missing": "\u26a0 缺少技能",
        "gap_weak": "\u2191 需加强",
        "gap_suggestions": "\U0001f4a1 建议",
        "exists_text": "⚠️ 已存在",

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
        "cal_weekday_labels": ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"],
        "cal_modal_resources": "\U0001f4da Ressources recommand\u00e9es",
        "cal_modal_projects": "\U0001f4a1 Projets connexes",
        "cal_modal_advice": "\U0001f4ad Conseils d'\u00e9tude",
        "btn_letter": "✉️ Lettre de motivation",
        "btn_view": "🔗 Voir l'offre",
        "btn_add_job": "📤 Ajouter un poste",
        "saved_text": "✅ Enregistré",
        "btn_preview": "👁 Aperçu",
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
        "tracked_jobs": "Offres suivies",
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
        """获取语言偏好：URL参数 > profile存储 > 默认"""
        lang = params.get("lang", "")
        if lang in ("en", "zh-CN", "fr"):
            return lang
        try:
            stored = self.agent.engine.profile.profile.get("language", "zh-CN")
            if stored in ("en", "zh-CN", "fr"):
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
        jobs_label = _t('jobs_found')
        high_match = _t('high_match')
        avg_match = _t('avg_match')
        search_results_h2 = _t('search_results')
        job_list_h2 = _t('job_list')

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
                    <label class="source-check"><input type="checkbox" class="src-cb" value="RemoteOK" checked> RemoteOK</label>
                    <label class="source-check"><input type="checkbox" class="src-cb" value="Indeed"> Indeed</label>
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
                h += '<span>📅 ' + (job.date || '').substring(0, 10) + '</span>';
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
            tabs += f'<a href="/tracked?status={key}" class="tab {active}">{label} ({cnt})</a>'

        btn_view = t(lang, "btn_view")
        btn_letter = t(lang, "btn_letter")
        btn_add_job = t(lang, "btn_add_job")
        btn_preview = t(lang, "btn_preview")
        btn_edit = t(lang, "btn_edit")
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
        saved_to_tracker = t(lang, "saved_to_tracker")
        applied_text = t(lang, "applied")
        jobs_html = ""
        if not jobs:
            jobs_html = f'<p class="empty">{t(lang, "no_tracked")}</p>'
        for j in jobs:
            label = labels.get(j["status"], j["status"])
            jobs_html += f"""
            <div class="job-card">
                <div class="job-header" onclick="toggleTrackedDesc('{j['id']}')" style="cursor:pointer">
                    <div class="job-title">{j['title']}{' <span class="job-type-tag">'+j['job_type']+'</span>' if j.get('job_type') else ''}</div>
                    <span class="status-tag status-{j['status']}">{label}</span>
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
                <div class="job-actions">
                    <a href="{j.get('url','#')}" target="_blank" class="btn btn-small">{btn_view}</a>
                    <button onclick="analyzeApply('{j['id']}')" class="btn btn-small {j['status'] == 'applied' and 'btn-save' or 'btn-primary'}" id="apply-anal-btn-{j['id']}">{j['status'] == 'applied' and applied_text or btn_apply}</button>
                    <button onclick="upd('{j['id']}','interviewing')" class="btn btn-small btn-interview">{btn_interview}</button>
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
                    renderLearnPlanModal(jobId, result.plan, result.progress);
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

            function _mapPriority(p) {{
                if (p === '\u9ad8' || p === 'High' || p === 'Haute') return _learn_plan_priority_high;
                if (p === '\u4e2d' || p === 'Mid' || p === 'Moyenne') return _learn_plan_priority_mid;
                if (p === '\u4f4e' || p === 'Low' || p === 'Faible') return _learn_plan_priority_low;
                return p || '';
            }}
            function renderLearnPlanModal(jobId, plan, progress) {{
                var oldModal = document.getElementById('learn-plan-modal');
                if (oldModal) oldModal.remove();
                // Count total tasks
                var totalTasks = 0;
                var doneTasks = 0;
                if (plan.weekly_plan) {{
                    plan.weekly_plan.forEach(function(w){{
                        if (w.tasks) {{ w.tasks.forEach(function(t,i){{
                            var tid = 'w' + w.week + '_t' + i;
                            totalTasks++;
                            if (progress[tid] && progress[tid].done) doneTasks++;
                        }});}}
                    }});
                }}
                var pct = totalTasks > 0 ? Math.round(doneTasks / totalTasks * 100) : 0;
                var h = '<div id="learn-plan-modal" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.35);z-index:1002;display:flex;align-items:center;justify-content:center" onclick="if(event.target===this)this.remove()">';
                h += '<div style="background:#fff;border-radius:10px;padding:20px;max-width:630px;width:92%;max-height:88vh;overflow-y:auto;box-shadow:0 4px 20px rgba(0,0,0,0.2);font-size:15px;line-height:1.6">';
                h += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">';
                h += '<h3 style="margin:0;font-size:15px">' + _learn_plan_modal_title + '</h3>';
                h += '<button class="learn-plan-close-btn" style="background:none;border:none;font-size:20px;cursor:pointer;color:#888">\u00d7</button></div>';

                // Progress bar
                if (totalTasks > 0) {{
                    h += '<div style="margin-bottom:10px">';
                    h += '<div style="display:flex;justify-content:space-between;font-size:13px;color:#666;margin-bottom:2px">';
                    h += '<span>_learn_plan_progress_label</span><span id="learn-progress-txt-' + jobId + '">' + doneTasks + '/' + totalTasks + '</span></div>';
                    h += '<div style="background:#e0e0e0;border-radius:4px;height:8px;overflow:hidden">';
                    h += '<div id="learn-progress-bar-' + jobId + '" style="background:#4caf50;height:8px;width:' + pct + '%;border-radius:4px;transition:width 0.3s"></div></div></div>';
                }}

                // Action buttons: ical export
                h += '<div style="margin-bottom:10px;display:flex;gap:6px">';
                h += '<a href="/api/learn_plan_ical?job_id=' + encodeURIComponent(jobId) + '" download class="btn btn-small" style="font-size:11px;text-decoration:none">' + _learn_plan_export + '</a>';
                h += '</div>';

                // Focus skills
                if (plan.focus_skills) {{
                    h += '<div style="margin-bottom:10px"><b>' + _learn_plan_focus + '</b></div>';
                    plan.focus_skills.forEach(function(s) {{
                        var priColor = s.priority == '\u9ad8' || s.priority == 'High' || s.priority == 'Haute' ? '#d32f2f' : s.priority == '\u4e2d' || s.priority == 'Mid' || s.priority == 'Moyenne' ? '#e65100' : '#1565c0';
                        h += '<div style="background:#f8f9fa;border-radius:6px;padding:8px;margin-bottom:6px">';
                        h += '<div style="display:flex;justify-content:space-between;align-items:center"><b>' + (s.skill || '') + '</b> <span style="font-size:12px;color:' + priColor + ';font-weight:500">' + _mapPriority(s.priority) + '</span></div>';
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
                        h += '<div style="font-weight:500">\u7b2c' + w.week + '\u5468: ' + (w.focus || '') + ' <span style="color:#888;font-size:11px">(\uff5e' + (w.estimated_hours || '') + '' + _learn_plan_hours + ')</span></div>';
                        if (w.tasks) {{
                            w.tasks.forEach(function(t, tIdx) {{
                                var tid = 'w' + w.week + '_t' + tIdx;
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
        var ANALYZING_TEXT = '\u5206\u6790\u4e2d...';
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
                if (!d.success) {{ alert('分析失败: ' + (d.error || '')); return; }}
                showApplyAnalysis(jobId, d.analysis, d.job);
            }} catch(e) {{
                alert('分析出错: ' + e);
            }} finally {{
                if (btn && origText !== null) {{ btn.textContent = origText; btn.disabled = false; }}
            }}
        }}

        function showApplyAnalysis(jobId, analysis, jobInfo) {{
            var h = '<div id="apply-analysis-modal" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:1000;display:flex;align-items:center;justify-content:center">';
            h += '<div style="background:#fff;border-radius:12px;padding:0;max-width:560px;width:95%;box-shadow:0 8px 32px rgba(0,0,0,0.2);display:flex;flex-direction:column;max-height:80vh">';

            // Title
            h += '<div style="display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-bottom:1px solid #e0e0e0;flex-shrink:0">';
            h += '<h3 style="margin:0;font-size:16px">\U0001F4E4 申请分析</h3>';
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
            var methodLabel = method === 'email' ? '\U0001F4E7 邮箱申请' : '\U0001F64B 手动申请';
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
                h += '<div style="font-weight:600;font-size:14px;margin-bottom:6px">\U0001F4CB 下一步</div>';
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
            h += '<button class="btn btn-primary" id="' + recordBtnId + '">\u2705 \u5df2\u7533\u8bf7</button>';
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
                    alert('记录失败: ' + (d.error || ''));
                }}
            }} catch(e) {{
                alert('记录出错: ' + e);
            }}
        }}
        function tailorResume(jobId) {{
            var btn = document.getElementById('tailor-' + jobId);
            if (btn) {{ btn.textContent = '⏳ 生成中...'; btn.disabled = true; }}
            fetch('/api/tailor_resume', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id: jobId}})}})
            .then(function(r){{return r.json()}})
            .then(function(d){{
                if (btn) {{ btn.textContent = '🎯 优化'; btn.disabled = false; }}
                if (d.success) {{
                    window.open('/resume_view?job_id=' + jobId, '_blank');
                }} else {{
                    alert('优化失败: ' + (d.error || ''));
                }}
            }})
            .catch(function(e){{
                if (btn) {{ btn.textContent = '🎯 优化'; btn.disabled = false; }}
                alert('请求出错: ' + e);
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
        html += self._tracked_resume_modal_html()
        self._send_html(html)

    def handle_learn_calendar_page(self, params):
        lang = self._get_lang(params)
        jobs = self.agent.tracker.tracked_jobs
        learn_plan_week = t(lang, "learn_plan_week")
        cal_month_names = t(lang, "cal_month_names")
        cal_weekday_labels = t(lang, "cal_weekday_labels")
        cal_modal_resources = t(lang, "cal_modal_resources")
        cal_modal_projects = t(lang, "cal_modal_projects")
        cal_modal_advice = t(lang, "cal_modal_advice")
        week_focus_tpl = t(lang, "week_focus")
        cal_title = t(lang, "learn_plan_modal_title")
        cal_empty = t(lang, "learn_plan_empty")
        tasks_completed = t(lang, "tasks_completed")
        
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

            # Calculate progress
            total_tasks = 0
            done_tasks = 0
            if plan.get("weekly_plan"):
                for w in plan["weekly_plan"]:
                    if w.get("tasks"):
                        for t_idx in range(len(w["tasks"])):
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
                    focus = w.get("focus", f"第{week_num}周")
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
                        # Check tasks for this week
                        tasks_for_day = ""
                        if w.get("tasks"):
                            for t_idx, raw_task in enumerate(w["tasks"]):
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
                                # Distribute tasks roughly across week days (for display)
                                day_idx = t_idx % 7
                                if day_idx == d:
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
                                        # 1. Extract meaningful keywords from skill name
                                        sk_keys = [k.strip() for k in _re.split(r'[/,、（）()\s]', sk) if len(k.strip()) > 2]
                                        for kw in sk_keys:
                                            if kw in task_lower:
                                                match_skill = True
                                                break
                                        if not match_skill:
                                            # 2. Check if any resource title shares keywords with task text
                                            for r in fs.get("resources", []):
                                                rt = r.get("title","").lower()
                                                rt_keys = [k.strip() for k in _re.split(r'[/,、（）()\s]', rt) if len(k.strip()) > 3]
                                                for rk in rt_keys:
                                                    if rk in task_lower:
                                                        match_skill = True
                                                        break
                                                for tc in task_lower.split():
                                                    if len(tc) > 3 and tc in rt:
                                                        match_skill = True
                                                        break
                                                if match_skill:
                                                    break
                                        if match_skill:
                                            matched_any = True
                                        matched_res.append((match_skill, fs))
                                    # Render: if any skill matched, show only matched skills (all resources).
                                    # If NO skill matched, show ALL skills but only 1 resource each (fallback).
                                    for is_match, fs in matched_res:
                                        sk = fs.get("skill", "")
                                        if matched_any:
                                            # Precision mode: skip unmatched skills entirely
                                            if not is_match:
                                                continue
                                            items = "".join(
                                                '<li>\U0001f4da <strong>' + r.get("title","") + '</strong>' + (
                                                    ' (' + str(r.get("estimated_hours","")) + 'h)' if r.get("estimated_hours") else ''
                                                ) + (
                                                    ' <a href="' + (r.get("url","") or 'https://www.google.com/search?q=' + urllib.parse.quote(r.get("title",""))) + '" target="_blank" style="color:#1a73e8;font-size:11px">\U0001f517 打开</a>'
                                                ) + '</li>'
                                                for r in fs.get("resources", [])
                                            )
                                        else:
                                            # Fallback mode: no skill matched, show 1 resource per skill
                                            items = "".join(
                                                '<li>\U0001f4da <strong>' + r.get("title","") + '</strong>' + (
                                                    ' (' + str(r.get("estimated_hours","")) + 'h)' if r.get("estimated_hours") else ''
                                                ) + (
                                                    ' <a href="' + (r.get("url","") or 'https://www.google.com/search?q=' + urllib.parse.quote(r.get("title",""))) + '" target="_blank" style="color:#1a73e8;font-size:11px">\U0001f517 打开</a>'
                                                ) + '</li>'
                                                for r in (fs.get("resources", []) or [])[:1]
                                            )
                                        if items:
                                            related_res_html += '<div class="td-skill-section"><div class="td-skill-name">\U0001f3af ' + fs.get("skill","") + ' (' + fs.get("priority","") + '优先级)</div>' + fs.get("reason","") + '<ul>' + items + '</ul></div>'
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
                                        "advice_text": task_tip
                                    }
                                    detail_json = json.dumps(json.dumps(detail_obj), ensure_ascii=False)
                                    detail_uri = urllib.parse.quote(detail_json)
                                    detail_b64 = base64.b64encode(detail_uri.encode()).decode()
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

                    # Calculate week progress
                    w_tasks = len(w.get("tasks", []))
                    w_done = 0
                    if w.get("tasks"):
                        for t_idx in range(len(w["tasks"])):
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
        .td-title {{ font-size:17px; font-weight:600; margin-bottom:4px; padding-right:30px; }}
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
        <div class="td-overlay" id="td-overlay" onclick="closeTaskDetail()">
            <div class="td-modal" onclick="event.stopPropagation()">
                <button class="td-close" onclick="closeTaskDetail()">&times;</button>
                <div class="td-title" id="td-title"></div>
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
            </div>
        </div>
        <script>
        var _learn_plan_week = __learn_plan_week;
        var _cal_modal_resources = __cal_modal_resources;
        var _cal_modal_projects = __cal_modal_projects;
        var _cal_modal_advice = __cal_modal_advice;
        // Task detail: click delegation on .cal-task        // Task detail: click delegation on .cal-task
        document.addEventListener('click', function(e) {
            var el = e.target.closest('.cal-task');
            if (!el || !el.dataset.detail) return;
            try {
                var d = JSON.parse(decodeURIComponent(atob(el.dataset.detail)));
                document.getElementById('td-title').textContent = d.task;
                document.getElementById('td-week').textContent = '\U0001f4c5 ' + _learn_plan_week + ' ' + (d.week || '') + ' \u2014 ' + (d.focus || '');

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

                document.getElementById('td-overlay').style.display = 'flex';
            } catch(err) { console.warn('Task detail parse error', err); }
        });

        // Calendar task checkbox: click handler (stops prop to .cal-task detail popup)
        document.addEventListener('click', function(e) {
            var cb = e.target.closest('.cal-task-cb');
            if (!cb) return;
            e.stopPropagation();
        });
        // Calendar task checkbox: toggle progress and strikethrough
        document.addEventListener('change', function(e) {
            var cb = e.target.closest('.cal-task-cb');
            if (!cb) return;
            var jobId = cb.getAttribute('data-jobid');
            var taskId = cb.getAttribute('data-taskid');
            if (!jobId || !taskId) return;
            // Toggle visual strikethrough
            var row = cb.parentElement;
            var taskEl = row ? row.querySelector('.cal-task') : null;
            if (taskEl) {
                if (cb.checked) {
                    taskEl.classList.add('task-done');
                } else {
                    taskEl.classList.remove('task-done');
                }
            }
            toggleLearnTask(jobId, taskId, cb);
        });

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
        skill_header = "Skills" if lang == "en" else "技能"
        kw_header = "Keywords" if lang == "en" else "关键词"
        level_header = "Level" if lang == "en" else "水平"
        exp_header = "Experience" if lang == "en" else "经验"
        saved_text = " ✅ Saved" if lang == "en" else " ✅ 已保存"
        failed_text = " ❌ Failed" if lang == "en" else " ❌ 失败"

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
        hint_text = "Please generate a cover letter from the search page first." if lang == "en" else "请先在搜索页面点击\"求职信\"按钮生成。"
        downloaded_text = "Downloaded!" if lang == "en" else "已下载!"
        copied_text = "Copied!" if lang == "en" else "已复制!"
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
            ok = self.agent.save_job(data.get("job", {}))
            if ok:
                job_data = data.get("job", {})
                try:
                    letter = self.agent.generate_cover_letter(job_data)
                    self.agent.tracker.update_cover_letter(job_data.get("title",""), job_data.get("company",""), letter)
                except Exception:
                    pass
                self.send_json({"success": True})
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
                "max_tokens": 4096,
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
            job_title = job.get("title", "")
            job_desc = job.get("description", "")
            company = job.get("company", "")
            resume_md = self.agent.tracker.get_job_resume_markdown(job_id) or ""

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
2. 资源可以是慕课网、B站、YouTube、官方文档、GitHub 仓库、Coursera、Udemy 等真实存在的学习平台链接
3. 实在找不到精确 URL 时，可以用搜索引擎搜索链接，例如 https://www.google.com/search?q=教程名
4. 每个资源必须包含 type、title、url、estimated_hours 四个字段，url 不能为空

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
    {{"week": 1, "focus": "Weekly focus topic", "tasks": [{{"name": "Concrete task 1", "advice": "Detailed 50-100 word learning advice in {lang} for this task"}}, {{"name": "Concrete task 2", "advice": "Detailed learning advice in {lang}"}}], "estimated_hours": 5}}
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
            # 初始化进度：为每个周任务创建 task_id 并初始化为未完成
            progress = {}
            if plan.get("weekly_plan"):
                for w in plan["weekly_plan"]:
                    week_num = w.get("week", 0)
                    if w.get("tasks"):
                        for t_idx, raw in enumerate(w["tasks"]):
                            task_id = f"w{week_num}_t{t_idx}"
                            if isinstance(raw, dict):
                                task_text = raw.get("name", "")
                                task_advice = raw.get("advice", "")
                            else:
                                task_text = raw
                                task_advice = ""
                            progress[task_id] = {"done": False, "text": task_text, "week": week_num, "advice": task_advice}
            job["learn_plan_progress"] = progress
            self.agent.tracker.save()
            self.send_json({"success": True, "plan": plan, "saved": True})
        except json.JSONDecodeError:
            self.send_json({"success": False, "error": "AI 返回格式异常，请重试"}, 500)
        except Exception as e:
            self.send_json({"success": False, "error": f"生成学习计划失败: {str(e)}"}, 500)

    def api_learn_plan_progress(self, data):
        """更新学习计划的进度"""
        try:
            job_id = data.get("job_id", "")
            task_id = data.get("task_id", "")  # e.g. "w1_t0"
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
            # 计算统计
            total = len(progress)
            done_count = sum(1 for v in progress.values() if v.get("done"))
            self.agent.tracker.save()
            self.send_json({"success": True, "progress": progress, "done": done_count, "total": total})
        except Exception as e:
            self.send_json({"success": False, "error": f"更新进度失败: {str(e)}"}, 500)

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
                    week_start = base_date + datetime.timedelta(days=(week_num - 1) * 7)
                    focus = w.get("focus", f"第{week_num}周")
                    # Create a weekly summary event
                    uid = str(uuid.uuid4())
                    lines.append("BEGIN:VEVENT")
                    lines.append(f"UID:{uid}@jobagent")
                    lines.append(f"DTSTART;VALUE=DATE:{week_start.strftime('%Y%m%d')}")
                    week_end = week_start + datetime.timedelta(days=6)
                    lines.append(f"DTEND;VALUE=DATE:{week_end.strftime('%Y%m%d')}")
                    lines.append(f"SUMMARY:📚 第{week_num}周: {focus}")
                    desc = f"目标职位: {company} - {title}\
"
                    desc += f"重点: {focus}\
"
                    est = w.get("estimated_hours", "")
                    if est:
                        desc += f"预估: {est}h\
"
                    if w.get("tasks"):
                        desc += "\
任务:\
"
                        for t_idx, raw in enumerate(w["tasks"]):
                            tid = f"w{week_num}_t{t_idx}"
                            p = progress.get(tid, {})
                            mark = "✅" if p.get("done") else "⬜"
                            if isinstance(raw, dict):
                                raw = raw.get("name", "")
                            desc += f"{mark} {raw}\
"
                    lines.append(f"DESCRIPTION:{desc}")
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
                h += '<button data-resume-id="' + r.id + '" class="btn btn-small btn-preview-resume">\U0001F441\u200D\U0001F5E8\uFE0F \u9884\u89C8</button>';
                h += '<button data-resume-id="' + r.id + '" class="btn btn-small btn-download-resume" style="margin-left:4px">\U0001F4E5 \u4E0B\u8F7D</button>';
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

    def _tracked_resume_modal_html(self) -> str:
        """返回跟踪页简历弹窗所需的 JS"""
        base = os.path.join(os.path.dirname(__file__), 'resume_modal_script.js')
        try:
            with open(base, 'r', encoding='utf-8') as _f:
                return '<script>\n' + _f.read() + '\n</script>'
        except Exception:
            return ''

    
    def handle_resume_view_page(self, params):
        """简历查看/编辑页"""
        job_id = params.get("job_id", "")
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
        html = self._build_resume_editor_page(job_id, resume_name)
        self._send_html(html)

    def _build_resume_editor_page(self, job_id: str, resume_name: str) -> str:
        """
        Markdown 简历编辑器页面
        分栏布局：左侧 Markdown 编辑器 + 右侧实时 HTML 预览
        """
        import json
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>编辑简历 - {resume_name}</title>
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
  <div><h1>📄 {resume_name} <span class="subtitle">（职位专属副本，修改不影响简历库）</span></h1></div>
  <div>
    <a href="/tracked" class="btn btn-back">← 返回</a>
    <button onclick="exportPdf()" class="btn btn-download" id="exportBtn">📄 导出 PDF</button>
    <button onclick="saveResume()" class="btn btn-save">💾 保存</button>
  </div>
</div>
<div id="statusMsg" class="status">✅ 已保存</div>
<div class="main">
  <div class="editor-pane">
    <div class="editor-toolbar">
      <span>Markdown 编辑器</span>
      <span style="flex:1"></span>
      <button class="btn-icon" onclick="insertMd('**','**')" title="粗体">B</button>
      <button class="btn-icon" onclick="insertMd('## ','\n## ')" title="标题">H</button>
      <button class="btn-icon" onclick="insertMd('\\n- ','\n  ')" title="列表">•</button>
      <button class="btn-icon" onclick="insertMd('[','](url)')" title="链接">🔗</button>
    </div>
    <textarea id="editor" spellcheck="false" placeholder="Markdown 格式的简历内容..."></textarea>
  </div>
  <div class="preview-pane" id="preview">加载中...</div>
</div>
<script>
var jobId = {json.dumps(job_id, ensure_ascii=False)};
var originalMd = "";
var timer = null;

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
      document.getElementById('preview').innerHTML = '<p style="color:red">加载失败: ' + (d.error || '') + '</p>';
    }}
  }} catch(e) {{
    document.getElementById('preview').innerHTML = '<p style="color:red">加载出错: ' + e + '</p>';
  }}
}}

async function renderPreview(text) {{
  try {{
    var resp = await fetch('/api/convert_markdown', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{markdown: text}})}});
    var d = await resp.json();
    if (d.success) {{
      document.getElementById('preview').innerHTML = d.html;
    }} else {{
      document.getElementById('preview').innerHTML = '<p style="color:red">预览失败</p><pre>' + text + '</pre>';
    }}
  }} catch(e) {{
    // fallback: show raw text
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
    status.textContent = d.success ? '✅ 已保存' : '❌ 保存失败: ' + (d.error || '');
    setTimeout(function() {{ status.className = 'status'; }}, 3000);
    if (d.success) originalMd = md;
  }} catch(e) {{
    var status = document.getElementById('statusMsg');
    status.className = 'status show error';
    status.textContent = '❌ 保存出错: ' + e;
  }}
}}

async function exportPdf() {{
  var btn = document.getElementById('exportBtn');
  btn.disabled = true;
  btn.textContent = '生成中...';
  try {{
    var resp = await fetch('/api/download_resume_pdf', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id: jobId}})}});
    if (!resp.ok) {{
      var d = await resp.json();
      alert('导出失败: ' + (d.error || ''));
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
    alert('导出出错: ' + e);
  }} finally {{
    btn.disabled = false;
    btn.textContent = '📄 导出 PDF';
  }}
}}

// Ctrl+S to save
document.addEventListener('keydown', function(e) {{
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {{
    e.preventDefault();
    saveResume();
  }}
}});

// Auto-preview with debounce
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
        qs = f"?lang={lang}" if lang != "zh-CN" else ""
        for href, text in pages:
            nav_items += f'<a href="{href}{qs}" class="nav-link">{text}</a>'
        # 语言切换（循环: zh-CN → en → fr → zh-CN）
        lang_cycle = {"zh-CN": "en", "en": "fr", "fr": "zh-CN"}
        other = lang_cycle.get(lang, "zh-CN")
        lang_labels = {"zh-CN": "🇨🇳 中文", "en": "🇬🇧 English", "fr": "🇫🇷 Français"}
        other_label = lang_labels.get(other, "🇨🇳 中文")
        lang_switch = f'<a href="?lang={other}" class="nav-link lang-switch" style="margin-left:auto;font-size:12px">{other_label}</a>'
        
        html_lang = lang if lang in ("en", "zh-CN", "fr") else "zh-CN"
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
