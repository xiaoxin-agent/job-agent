#!/usr/bin/env python3
"""
求职Agent - Web界面
美观的浏览器界面，供求职者使用
"""

import json
import os
import datetime
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict

from job_agent_core import JobAgent

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
        "nav_letter": "✉️ Cover Letter",
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
        "applied": "Applied",
        "interviewing": "Interviewing",
        "rejected": "Rejected",
        "offer": "Offer",
        "no_results": "No results yet. Try a search!",
        "loading": "Searching...",
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
        "saved_text": "✅ Saved",
        "exists_text": "⚠️ Exists",

    },
    "zh-CN": {
        "nav_home": "🏠 首页",
        "nav_dashboard": "📊 仪表盘",
        "nav_search": "🔍 搜索",
        "nav_tracked": "📋 跟踪",
        "nav_profile": "👤 画像",
        "nav_letter": "✉️ 求职信",
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
        "saved_text": "✅ 已保存",
        "exists_text": "⚠️ 已存在",

    },
    "fr": {
        # Navigation
        "nav_home": "🏠 Accueil",
        "nav_dashboard": "📊 Tableau de bord",
        "nav_search": "🔍 Recherche",
        "nav_tracked": "📋 Suivi",
        "nav_profile": "👤 Profil",
        "nav_letter": "✉️ Lettre de motivation",
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
        "btn_letter": "✉️ Lettre de motivation",
        "btn_view": "🔗 Voir l'offre",
        "saved_text": "✅ Enregistré",
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
        }

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
        var _searching = {json.dumps(searching_text)};
        var _src_prefix = {json.dumps(status_searching)};
        var _done_prefix = {json.dumps(status_done)};
        var _done_suffix = {json.dumps(status_done_end)};
        var _failed = {json.dumps(status_failed)};
        var _btn_search = {json.dumps(btn_search)};
        var _btn_search_again = {json.dumps(btn_search_again)};
        var _btn_save = {json.dumps(btn_save)};
        var _btn_letter = {json.dumps(btn_letter)};
        var _btn_view = {json.dumps(btn_view)};
        var _saved_text = {json.dumps(saved_text)};
        var _exists_text = {json.dumps(exists_text)};
        var _jobs_label = {json.dumps(jobs_label)};
        var _high_match = {json.dumps(high_match)};
        var _avg_match = {json.dumps(avg_match)};
        var _sr_h2 = {json.dumps(search_results_h2)};
        var _jl_h2 = {json.dumps(job_list_h2)};
        
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
                h += '<span>🏢 ' + (job.company || '') + '</span>';
                h += '<span>📍 ' + (job.location || '') + '</span>';
                h += '<span>📅 ' + (job.date || '').substring(0, 10) + '</span>';
                h += '<span>📡 ' + (job.source || '') + '</span></div>';
                h += '<div class="job-desc" id="desc-' + i + '">' + shortDesc + '</div>';
                h += '<div class="job-desc-full" id="fulldesc-' + i + '" style="display:none">' + desc.replace(/\\n/g, '<br>') + '</div>';
                h += '<div class="job-actions">';
                if (job.url) h += '<a href="' + job.url + '" target="_blank" class="btn btn-small">' + _btn_view + '</a>';
                h += '<button onclick="saveJob(' + i + ')" class="btn btn-small btn-save" id="save-' + i + '">' + _btn_save + '</button>';
                h += '<button onclick="genLetter(' + i + ')" class="btn btn-small">' + _btn_letter + '</button>';
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
        async function genLetter(i) {{
            if (!searchData || !searchData.jobs[i]) return;
            var resp = await fetch('/api/generate_letter', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job: searchData.jobs[i]}})}});
            var d = await resp.json();
            if (d.success) {{
                var w = window.open('/letter', '_blank');
                w.letterContent = d.letter;
            }}
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
        jobs_html = ""
        if not jobs:
            jobs_html = f'<p class="empty">{t(lang, "no_tracked")}</p>'
        for j in jobs:
            label = labels.get(j["status"], j["status"])
            jobs_html += f"""
            <div class="job-card">
                <div class="job-header">
                    <div class="job-title">{j['title']}{' <span class="job-type-tag">'+j['job_type']+'</span>' if j.get('job_type') else ''}</div>
                    <span class="status-tag status-{j['status']}">{label}</span>
                </div>
                <div class="job-meta">
                    <span>🏢 {j['company']}</span>
                    <span>📍 {j['location']}</span>
                    <span>📊 {j.get('match_score',0)}% 匹配</span>
                </div>
                <div class="job-desc-toggle" onclick="toggleTrackedDesc('{j['id']}')" style="cursor:pointer">
                    <div class="job-desc-snippet" id="tdesc-{j['id']}">{(j.get('description','') or '')[:150].replace(chr(10),' ')}</div>
                    <div class="job-desc-full" id="tfull-{j['id']}" style="display:none">{j.get('description','').replace(chr(10),'<br>').replace(chr(10)+'<br>','<br>')}</div>
                </div>
                <div class="job-actions">
                    <a href="{j.get('url','#')}" target="_blank" class="btn btn-small">{btn_view}</a>
                    <button onclick="applyWithResume('{j['id']}')" class="btn btn-small" id="apply-btn-{j['id']}">{btn_apply}</button>
                    <button onclick="upd('{j['id']}','interviewing')" class="btn btn-small btn-interview">{btn_interview}</button>
                    <button onclick="upd('{j['id']}','rejected')" class="btn btn-small btn-reject">{btn_reject}</button>
                    <button onclick="upd('{j['id']}','offer')" class="btn btn-small btn-offer">{btn_offer}</button>
                    <button onclick="delJob('{j['id']}')" class="btn btn-small btn-delete">{btn_delete}</button>
                </div>
                {f'<div class="job-notes">📝 {j.get("notes","")}</div>' if j.get("notes") else ''}
                {('<div class="job-resume">📄 简历已上传 <a href="/api/get_resume?job_id='+j['id']+'" class="link-url" target="_blank">查看</a></div>') if j.get('has_resume') else ''}
            </div>"""

        html = self._page(t(lang, 'tracked_title'), f"""
        <h1>{t(lang, 'tracked_title')}</h1>
        <div class="section"><div class="tab-bar">{tabs}</div></div>
        <div id="tracked-list">{jobs_html}</div>
        <script>
        async function delJob(id) {{
            if (!confirm('确定删除？')) return;
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
            var notes = prompt('备注（可选）:','')||'';
            await fetch('/api/update_status', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id:id, status:st, notes:notes}})}});
            location.reload();
        }}
        async function applyWithResume(id) {{
            var input = document.createElement('input');
            input.type = 'file';
            input.accept = '.pdf,.doc,.docx,.png,.jpg';
            input.onchange = async function(e) {{
                var file = e.target.files[0];
                if (!file) return;
                var btn = document.getElementById('apply-btn-' + id);
                btn.disabled = true;
                btn.textContent = '⏳ 上传中…';
                var formData = new FormData();
                formData.append('job_id', id);
                formData.append('resume', file);
                try {{
                    var resp = await fetch('/api/upload_resume', {{method:'POST', body:formData}});
                    var d = await resp.json();
                    if (d.success) {{
                        // 简历上传成功，更新状态为 applied
                        var notes = prompt('备注（可选）:','')||'';
                        await fetch('/api/update_status', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{job_id:id, status:'applied', notes:notes}})}});
                        location.reload();
                    }} else {{
                        alert('上传失败: ' + (d.error || '未知错误'));
                        btn.disabled = false;
                        btn.textContent = '📤 申请';
                    }}
                }} catch(e) {{
                    alert('上传出错: ' + e);
                    btn.disabled = false;
                    btn.textContent = '📤 申请';
                }}
            }};
            input.click();
        }}
        </script>
        """, lang=lang)
        self._send_html(html)

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
            self.send_json({"success": ok})
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

    def api_get_resume(self, data):
        """返回简历文件供下载"""
        try:
            job_id = data.get("job_id", "")
            content = self.agent.tracker.get_resume(job_id)
            if content is None:
                self.send_json({"success": False, "error": "未找到简历"}, 404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", f'attachment; filename="resume_{job_id}.pdf"')
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    # ===================== 工具 =====================

    def _page(self, title, body, lang="zh-CN"):
        nav_items = ""
        pages = [
            ("/", t(lang, "nav_home")),
            ("/dashboard", t(lang, "nav_dashboard")),
            ("/search", t(lang, "nav_search")),
            ("/tracked", t(lang, "nav_tracked")),
            ("/profile", t(lang, "nav_profile")),
            ("/letter", t(lang, "nav_letter")),
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
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#f0f2f5; color:#333; }}
nav {{ background:#fff; display:flex; padding:0 16px; box-shadow:0 2px 8px rgba(0,0,0,0.1); gap:8px; overflow-x:auto; position:sticky; top:0; z-index:100; }}
nav a {{ padding:14px 12px; text-decoration:none; color:#666; font-weight:500; border-bottom:3px solid transparent; white-space:nowrap; }}
nav a:hover {{ color:#333; }}
nav a.active {{ color:#1a73e8; border-bottom-color:#1a73e8; }}
.container {{ max-width:960px; margin:0 auto; padding:20px; }}
h1 {{ margin-bottom:20px; }}
.hero {{ text-align:center; padding:50px 20px 30px; }}
.hero h1 {{ font-size:42px; }}
.subtitle {{ color:#666; font-size:16px; margin:8px 0 24px; }}
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
.btn-small {{ padding:4px 10px; font-size:12px; }}
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
.job-card {{ background:#fff; border-radius:8px; padding:14px; margin:10px 0; box-shadow:0 1px 3px rgba(0,0,0,0.06); }}
.job-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }}
.job-title {{ font-weight:600; font-size:14px; }}
.job-score {{ padding:2px 8px; border-radius:10px; font-size:12px; font-weight:600; }}
.score-high {{ background:#e6f4ea; color:#34a853; }}
.score-medium {{ background:#fef7e0; color:#f9ab00; }}
.score-low {{ background:#fce8e6; color:#ea4335; }}
.job-type-tag {{ display:inline-block; padding:1px 6px; border-radius:4px; font-size:10px; font-weight:600; background:#e8f5e9; color:#2e7d32; vertical-align:middle; margin-left:4px; }}
.job-meta {{ display:flex; flex-wrap:wrap; gap:10px; font-size:12px; color:#666; margin-bottom:6px; }}
.job-desc {{ font-size:13px; color:#555; margin-bottom:8px; line-height:1.4; }}
.job-desc-full {{ font-size:13px; color:#333; margin-bottom:8px; line-height:1.5; white-space:pre-wrap; max-height:400px; overflow-y:auto; padding:8px; background:#f9f9f9; border-radius:4px; border:1px solid #eee; }}
.job-actions {{ display:flex; gap:6px; flex-wrap:wrap; }}
.job-notes {{ margin-top:6px; color:#888; font-size:12px; }}
.search-summary {{ margin:16px 0; }}
.result-stats {{ display:flex; gap:16px; margin:8px 0; }}
.link-item {{ background:#fff; border-radius:6px; padding:10px; margin:6px 0; font-size:13px; }}
.link-url {{ color:#1a73e8; word-break:break-all; display:block; margin-top:3px; }}
.tab-bar {{ display:flex; flex-wrap:wrap; gap:4px; }}
.tab {{ padding:6px 12px; border-radius:16px; font-size:12px; text-decoration:none; color:#666; background:#e8e8e8; }}
.tab.active {{ background:#1a73e8; color:#fff; }}
.status-tag {{ padding:2px 8px; border-radius:10px; font-size:11px; font-weight:500; }}
.job-desc-snippet {{ font-size:13px; color:#555; margin-bottom:8px; line-height:1.4; padding:4px 0; border-bottom:1px solid #eee; }}
.status-saved {{ background:#f0f0f0; color:#666; }}
.status-applied {{ background:#e8f0fe; color:#1a73e8; }}
.status-interviewing {{ background:#fef7e0; color:#f9ab00; }}
.status-rejected {{ background:#fce8e6; color:#ea4335; }}
.status-offer {{ background:#e6f4ea; color:#34a853; }}
.section {{ margin:24px 0; }}
.section h2 {{ margin-bottom:12px; font-size:18px; }}
.profile-form {{ max-width:480px; }}
.form-row {{ display:flex; align-items:center; gap:10px; margin:10px 0; }}
.form-row label {{ width:90px; font-size:13px; color:#555; flex-shrink:0; }}
.form-row input {{ flex:1; padding:7px 10px; border:1px solid #ddd; border-radius:5px; font-size:13px; }}
.salary-range {{ display:flex; align-items:center; gap:6px; }}
.salary-range input {{ width:100px; }}
.skills-table {{ width:100%; border-collapse:collapse; font-size:13px; }}
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
