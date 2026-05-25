"""
Apply Manager — Plugin-based application system
支持不同来源的职位申请流程
"""
import json
import os
import re
import datetime
import logging
from typing import Dict, List, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ApplyAdapter(ABC):
    """申请适配器基类"""

    @abstractmethod
    def analyze(self, job: Dict) -> Dict:
        """分析职位申请方式：
        {
            "can_auto_apply": bool,     # 是否支持自动申请
            "method": str,              # "email" / "url" / "manual" / "api"
            "instructions": str,        # 给用户的申请指引
            "target": str,              # 邮箱地址 / 申请URL / 公司名称
            "details": str,             # 额外细节（如申请词、注意事项）
            "next_steps": List[str],    # 下一步操作建议
        }
        """
        ...


class RemoteOKApplyAdapter(ApplyAdapter):
    """RemoteOK 申请适配器
    RemoteOK 是一个聚合器，不提供站内申请。
    需要分析职位描述提取申请方式。
    """

    def analyze(self, job: Dict) -> Dict:
        desc = job.get("description", "")
        company = job.get("company", "")
        url = job.get("url", "")

        # 1. 尝试从描述中提取邮箱
        emails = self._extract_emails(desc)
        # 2. 尝试提取申请关键词（反 spam 要求）
        apply_words = self._extract_apply_words(desc)
        # 3. 尝试提取公司官网
        company_links = self._extract_company_links(desc)

        if emails:
            return {
                "can_auto_apply": True,
                "method": "email",
                "instructions": f"发送简历到 {emails[0]}",
                "target": emails[0],
                "details": self._format_details(emails, apply_words, company_links),
                "next_steps": [
                    "生成求职信",
                    "发送简历到指定邮箱",
                    "等待对方回复"
                ]
            }

        return {
            "can_auto_apply": False,
            "method": "manual",
            "instructions": f"请自行前往公司官网或求职平台投递",
            "target": company,
            "details": self._format_details(emails, apply_words, company_links),
            "next_steps": [
                f"搜索 {company} 官网查找 Careers 页面",
                "或通过 LinkedIn 找到招聘负责人联系",
                "准备求职信和简历"
            ]
        }

    def _extract_emails(self, text: str) -> List[str]:
        """从文本中提取邮箱地址"""
        return re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)

    def _extract_apply_words(self, text: str) -> List[str]:
        """提取描述中的隐藏申请词（反 spam）"""
        words = []
        # RemoteOK 的反 spam 格式：mention the word **PROLIFIC**
        for m in re.finditer(r'\*\*([A-Z]+)\*\*', text):
            words.append(m.group(1))
        return words

    def _extract_company_links(self, text: str) -> List[str]:
        """提取可能存在的公司官网链接"""
        # Look for URLs in description
        urls = re.findall(r'https?://(?!remoteok)[^\s"\'<>]+', text)
        # Filter out common non-company URLs
        filtered = []
        for u in urls:
            if any(domain in u.lower() for domain in ['remoteok', 'example', 'placeholder']):
                continue
            filtered.append(u)
        return filtered

    def _format_details(self, emails, apply_words, company_links) -> str:
        parts = []
        if emails:
            parts.append(f"📧 邮箱: {', '.join(emails)}")
        if apply_words:
            parts.append(f"🔑 申请关键词: 请在申请中提及 {', '.join(apply_words)}")
        if company_links:
            parts.append(f"🔗 相关链接: {', '.join(company_links)}")
        return "\n".join(parts)


class LeverApplyAdapter(ApplyAdapter):
    """Lever 申请适配器
    Lever 的职位可以直接通过 Playwright headless 浏览器自动投递。
    """

    def analyze(self, job: Dict) -> Dict:
        url = job.get("url", "")
        company = job.get("company", "")
        title = job.get("title", "")

        return {
            "can_auto_apply": True,
            "method": "auto_browser",
            "instructions": f"一键投递至 {company}（Lever 自动表单）",
            "target": url,
            "details": (
                f"🏢 {company}\n"
                f"📌 Lever 自动投递\n"
                f"系统将通过 headless 浏览器自动填写简历、联系方式、"
                f"并处理自定义问题后提交申请。"
            ),
            "next_steps": [
                f"一键投递至 {company} 的 {title}",
                "系统自动填写表单并提交",
                "投递结果会记录到申请历史",
            ],
        }


class IndeedApplyAdapter(ApplyAdapter):
    """Indeed 申请适配器"""

    def analyze(self, job: dict) -> dict:
        company = job.get("company", "")
        desc = job.get("description", "")
        job_type = job.get("job_type", "")
        location = job.get("location", "")

        emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", desc)
        company_links = []
        for link in re.findall(r"https?://[^\s\"'<>]+", desc):
            domain = link.lower().split("/")[2] if "://" in link else ""
            if "indeed" not in domain and "example" not in domain:
                company_links.append(link)

        domain = re.sub(r"[^a-zA-Z0-9]", "", company.lower()) if company else "unknown"
        career_url = f"https://careers.{domain}.com"

        return {
            "can_auto_apply": False,
            "method": "url",
            "instructions": f"前往 {company} 官网提交申请",
            "target": company,
            "details": self._details(company, job_type, location, career_url, emails, company_links),
            "next_steps": [
                "打开 Indeed 页面，点击 \"Apply on Company Site\"",
                f"或直接前往 {career_url} 搜索职位",
                "上传定制简历和求职信",
                "返回系统记录申请状态"
            ]
        }

    def _details(self, company, job_type, location, career_url, emails, company_links) -> str:
        parts = [f"\U0001f3e2 {company}"]
        if job_type:
            parts.append(f"\U0001f4cb {job_type}")
        if location:
            parts.append(f"\U0001f4cd {location}")
        parts.append("")
        parts.append("\U0001f4cc Indeed 申请方式：")
        parts.append("   1. Easy Apply — 通过 Indeed 直接投递")
        parts.append(f"   2. Apply on Company Site — 前往 {company} 官网")
        parts.append(f"\U0001f517 猜测的招聘页: {career_url}")
        if emails:
            parts.append(f"\U0001f4e7 描述中邮箱: {', '.join(emails)}")
        if company_links:
            parts.append(f"\U0001f517 链接: {', '.join(company_links)}")
        return "\n".join(parts)


class ApplyManager:
    """申请管理器——统一入口"""

    def __init__(self, data_dir: str = None):
        self.adapters: Dict[str, ApplyAdapter] = {
            "RemoteOK": RemoteOKApplyAdapter(),
            "GitHub Jobs": RemoteOKApplyAdapter(),
            "Indeed": IndeedApplyAdapter(),
            "Fullscript": LeverApplyAdapter(),
            "MagnetForensics": LeverApplyAdapter(),
            "Telesat": LeverApplyAdapter(),
            "Lever": LeverApplyAdapter(),  # fallback for any other Lever company
        }
        self.data_dir = data_dir or os.path.join(os.path.dirname(__file__), "agent_data")
        self._ensure_dirs()

    def _ensure_dirs(self):
        app_dir = os.path.join(self.data_dir, "applications")
        os.makedirs(app_dir, exist_ok=True)

    def _history_file(self) -> str:
        return os.path.join(self.data_dir, "applications", "history.json")

    def analyze(self, job: Dict) -> Dict:
        """分析职位的申请方式"""
        source = job.get("source", "")
        adapter = self.adapters.get(source)
        if not adapter:
            logger.info(f"No specific adapter for source '{source}', using fallback")
            adapter = self.adapters.get("RemoteOK")  # fallback
        result = adapter.analyze(job)
        logger.info(f"Analyzed apply method for {job.get('company','?')}/{job.get('title','?')}: {result['method']}")
        return result

    def apply_via_email(self, job: Dict, resume_text: str, cover_letter: str,
                         email_target: str) -> Dict:
        """通过邮箱申请（占位——后续对接 SMTP）"""
        logger.info(f"Email apply to {email_target} for {job.get('company','?')}/{job.get('title','?')}")
        # 记录申请历史
        record = self._create_record(job, "email", {
            "to": email_target,
            "resume_length": len(resume_text),
            "has_cover_letter": bool(cover_letter)
        })
        self._save_record(record)
        return {"success": True, "method": "email", "record": record}

    def auto_apply_lever(self, job: Dict, cover_letter: str = None) -> Dict:
        """一键自动投递 Lever 职位。

        使用 Playwright headless 浏览器自动填写并提交 Lever 申请表单。
        """
        from sites.lever_apply import apply_to_lever as lever_apply_browser
        logger.info(f"Auto-apply Lever: {job.get('company','?')}/{job.get('title','?')}")
        return lever_apply_browser(job, cover_letter=cover_letter)

    def record_manual_apply(self, job: Dict) -> Dict:
        """记录用户手动申请"""
        logger.info(f"Manual apply recorded: {job.get('company','?')}/{job.get('title','?')}")
        record = self._create_record(job, "manual", {})
        self._save_record(record)
        return {"success": True, "method": "manual", "record": record}

    def get_application_history(self, job_id: str = None) -> List[Dict]:
        """获取申请历史"""
        history = self._load_history()
        if job_id:
            return [h for h in history if h.get("job_id") == job_id]
        return history

    def _create_record(self, job: Dict, method: str, details: Dict) -> Dict:
        return {
            "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S") + "_" + job.get("id", "")[:8],
            "job_id": job.get("id", ""),
            "job_title": job.get("title", ""),
            "company": job.get("company", ""),
            "source": job.get("source", ""),
            "method": method,
            "details": details,
            "applied_at": datetime.datetime.now().isoformat(),
            "status": "pending"  # pending / no_reply / rejected / interview / offer
        }

    def _save_record(self, record: Dict):
        history = self._load_history()
        history.insert(0, record)
        with open(self._history_file(), "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def _load_history(self) -> List[Dict]:
        if not os.path.exists(self._history_file()):
            return []
        try:
            with open(self._history_file(), "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
