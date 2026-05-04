"""
Lever 一键投递模块

通过 Playwright headless 浏览器自动填写 Lever 申请表单。
支持：
- 标准字段（姓名、邮箱、电话、LinkedIn、GitHub…）
- 简历 PDF 上传
- 公司自定义问题（通过 LLM 推理回答）
- EEO 民主化信息
- 投递结果记录
"""

import json
import os
import re
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime


# ════════════════════════════════════════════════════════════════════════
# hCaptcha / 2Captcha 调试日志（2026-05-04）
# ════════════════════════════════════════════════════════════════════════
#
# 问题：Lever 使用 hCaptcha enterprise/enclave 模式，2Captcha token 被服务端拒绝。
#
# [提交方式对比]
#   1) 按钮点击（dispatchEvent click）+ token 注入 + onSuccess 回调
#      → 不发出任何 POST 请求
#      根因：clickSubmitButton() 在 Lever 的 IIFE 闭包中，BugSnag 包裹后无法正常触发
#
#   2) form.submit()（原生方法）
#      → ✅ 发出完整 POST 请求，包含所有表单字段 + h-captcha-response
#      结果：HTTP 400 Bad Request，页面显示 "There was an error verifying your application"
#
# [测试条件]
#   - 2Captcha token 新鲜获取（<5 秒内提交）
#   - 有效 PDF 简历（316 字节合规 PDF）
#   - invisible=1 参数
#   - API v2 (HCaptchaTaskProxyless)
#   - token 长度：1108 / 2026 / 2114 字符（格式正确，P1_ 开头的 JWT）
#   - 全部 → HTTP 400
#
# [结论]
#   2Captcha 无法正确解出 Lever hCaptcha enclave 模式的合法 token。
#   这不是代码问题——token 格式、注入路径、`form.submit()` 都正确——
#   但 hCaptcha 服务端不认 2Captcha 的解算结果（enterprise 环境签名差异）。
#
# [替代方案]
#   - CapSolver（https://capsolver.com）— 据称 hCaptcha enterprise 支持更好
#   - 手动完成 hCaptcha 后提交
#   - Playwright page.route() 直接伪造 POST 请求绕过前端验证
# ════════════════════════════════════════════════════════════════════════

logger = logging.getLogger(__name__)

# === Paths ===
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPLY_PROFILE_PATH = os.path.join(WORKSPACE, "apply_profile.json")
DATA_DIR = os.path.join(WORKSPACE, "agent_data")
HISTORY_FILE = os.path.join(DATA_DIR, "applications", "history.json")
RESUMES_DIR = os.path.join(DATA_DIR, "resumes")


def load_apply_profile() -> Dict:
    """加载自动投递配置文件（联系方式等）。"""
    default = {
        "first_name": "",
        "last_name": "",
        "email": "",
        "phone": "",
        "location": "",
        "linkedin_url": "",
        "github_url": "",
        "portfolio_url": "",
        "pronouns": "",
        "referral_source": "",
        "eeo_defaults": {
            "gender": "prefer-not-to-say",
            "race": "",
            "veteran": "prefer-not-to-say",
        },
    }
    if not os.path.exists(APPLY_PROFILE_PATH):
        return default
    try:
        with open(APPLY_PROFILE_PATH, "r") as f:
            data = json.load(f)
        # Merge, not replace — keep new keys from defaults
        merged = dict(default)
        merged.update(data)
        return merged
    except Exception as e:
        logger.warning(f"Failed to load apply profile: {e}")
        return default


def resolve_resume_path(job: Dict) -> Optional[str]:
    """根据 job 对象找到简历 PDF 的完整路径。

    查找顺序：
    1. job 有关联的 resume_id → job_xxx/ 目录下的 PDF
    2. 回退到简历库的第一个 PDF
    """
    job_id = job.get("id", "")
    resume_id = job.get("resume_id", "")

    # 方案 A：职位专属副本
    if resume_id:
        job_dir = os.path.join(RESUMES_DIR, f"job_{job_id}")
        pdf_path = os.path.join(job_dir, f"{resume_id}.pdf")
        if os.path.exists(pdf_path):
            return pdf_path
        # 方案 B：简历库原始文件
        resume_dir = os.path.join(RESUMES_DIR, resume_id)
        for f in os.listdir(resume_dir):
            if f.endswith(".pdf"):
                return os.path.join(resume_dir, f)

    # 方案 C：简历库中第一个 PDF
    try:
        index_path = os.path.join(RESUMES_DIR, "resume_index.json")
        if os.path.exists(index_path):
            with open(index_path, "r") as f:
                idx = json.load(f)
            if idx:
                entry = idx[0]
                path = os.path.join(RESUMES_DIR, entry["filename"])
                if os.path.exists(path):
                    return path
                # 子目录格式
                dir_path = os.path.join(RESUMES_DIR, entry["id"])
                for f in os.listdir(dir_path):
                    if f.endswith(".pdf"):
                        return os.path.join(dir_path, f)
    except Exception:
        pass

    return None


def apply_to_lever(
    job: Dict,
    profile: Optional[Dict] = None,
    cover_letter: Optional[str] = None,
    headless: bool = True,
    browser_timeout: int = 30,
) -> Dict:
    """一键投递 Lever 职位。

    Args:
        job: 职位 dict（必须包含 url 字段指向 Lever hostedUrl）
        profile: 可选的联系方式覆盖（默认从 apply_profile.json 读取）
        cover_letter: 可选的求职信文本
        headless: 是否使用 headless 模式（默认 True）
        browser_timeout: 总超时秒数

    Returns:
        {
            "success": bool,
            "message": str,
            "fields_filled": int,
            "applied_at": str,
            "job_url": str,
            "error": str | None,
        }
    """
    if profile is None:
        profile = load_apply_profile()

    job_url = job.get("url", "")
    if not job_url:
        return {"success": False, "message": "职位没有 URL", "job_url": ""}

    # 确保是 Lever apply URL
    if "/apply" not in job_url:
        # 追加 /apply
        job_url = job_url.rstrip("/") + "/apply"

    resume_path = resolve_resume_path(job)
    if not resume_path:
        return {
            "success": False,
            "message": "未找到简历 PDF，请先上传简历并关联到此职位",
            "job_url": job_url,
        }

    logger.info(f"Starting Lever apply for {job.get('title', '')} @ {job_url}")
    logger.info(f"Resume: {resume_path}")

    try:
        result = _do_apply_in_browser(
            job_url=job_url,
            profile=profile,
            resume_path=resume_path,
            cover_letter=cover_letter,
            headless=headless,
            timeout=browser_timeout,
            job=job,
        )
    except Exception as e:
        logger.exception("Browser apply failed")
        result = {
            "success": False,
            "message": f"浏览器自动化失败: {e}",
            "job_url": job_url,
            "error": str(e),
        }

    # 记录到申请历史
    _record_application(job, result)

    return result


def _do_apply_in_browser(
    job_url: str,
    profile: Dict,
    resume_path: str,
    cover_letter: Optional[str],
    headless: bool,
    timeout: int,
    job: Optional[Dict] = None,
) -> Dict:
    """在 headless 浏览器内完成 Lever 申请表单。"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux aarch64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        # 导航到申请页
        page.goto(job_url, wait_until="domcontentloaded", timeout=timeout * 1000)
        page.wait_for_timeout(3000)

        # 等待表单出现
        form = page.locator("form")
        if form.count() == 0:
            browser.close()
            return {"success": False, "message": "未找到申请表单"}

        fields_filled = 0
        errors = []

        # === 1. 上传简历 ===
        try:
            file_input = form.locator("input[type='file']")
            if file_input.count() > 0:
                file_input.set_input_files(resume_path)
                page.wait_for_timeout(1000)
                fields_filled += 1
                logger.info("✅ Resume uploaded")
        except Exception as e:
            errors.append(f"简历上传失败: {e}")

        # === 2. 填充标准文本字段 ===
        field_map = {
            "name": _fill_name_fields,
            "email": _fill_email,
            "phone": _fill_phone,
            "location": _fill_location,
            "org": _fill_company,
            "urls[LinkedIn]": _fill_linkedin,
            "urls[GitHub]": _fill_github,
            "urls[Portfolio]": _fill_portfolio,
            "urls[Twitter]": _fill_twitter,
            "urls[Referral]": _fill_referral,
        }

        for field_name, filler in field_map.items():
            try:
                if filler(form, profile):
                    fields_filled += 1
            except Exception as e:
                errors.append(f"{field_name}: {e}")

        # === 3. 处理 pronouns（复选框组） ===
        try:
            pronouns_val = profile.get("pronouns", "").strip().lower()
            if pronouns_val:
                pronoun_checkboxes = form.locator("input[name='pronouns']")
                count = pronoun_checkboxes.count()
                for i in range(count):
                    cb = pronoun_checkboxes.nth(i)
                    label_id = cb.get_attribute("id") or ""
                    parent_text = form.locator(f"label[for='{label_id}']").inner_text() if label_id else ""
                    if pronouns_val in parent_text.lower() or pronouns_val in label_id.lower():
                        cb.check()
                        fields_filled += 1
                        break
        except Exception as e:
            errors.append(f"pronouns: {e}")

        # === 4. 处理自定义问题（card-based fields） ===
        try:
            custom_fields = _detect_custom_fields(form)
            for cf in custom_fields:
                _fill_custom_field(form, cf, profile, job)
                fields_filled += 1
        except Exception as e:
            errors.append(f"自定义问题: {e}")

        # === 5. 填充 Cover Letter ===
        if cover_letter:
            try:
                textareas = form.locator("textarea")
                tc = textareas.count()
                for i in range(tc):
                    ta = textareas.nth(i)
                    name = ta.get_attribute("name") or ""
                    if "cover" in name.lower():
                        ta.fill(cover_letter)
                        fields_filled += 1
                        break
            except Exception as e:
                errors.append(f"cover letter: {e}")

        # === 6. 处理 EEO 下拉 ===
        try:
            _fill_eeo(form, profile)
        except Exception as e:
            errors.append(f"EEO: {e}")

        # === 7. 尝试通过 CAPTCHA 解决服务提交 ===
        submitted = False
        submit_error = None

        try:
            # 查找提交按钮
            submit_btn = page.locator("button:has-text('SUBMIT APPLICATION'):not(.hidden)")
            if submit_btn.count() == 0:
                submit_btn = page.locator("button:has-text('Submit'):not(.hidden)")
            if submit_btn.count() == 0:
                submit_btn = page.locator(".postings-btn.template-btn-submit")

            if submit_btn.count() == 0 or not submit_btn.first.is_visible():
                submit_error = "未找到可见的提交按钮"
            else:
                # 检查是否有 hCaptcha
                hcaptcha = page.locator("#h-captcha")
                if hcaptcha.count() > 0:
                    # 有 hCaptcha — 通过 2Captcha 解决
                    captcha_key = hcaptcha.get_attribute("data-sitekey") or ""
                    hcaptcha_iframe = page.locator("#h-captcha iframe").first
                    if hcaptcha_iframe.count() > 0:
                        src = hcaptcha_iframe.get_attribute("src") or ""
                    logger.info(f"hCaptcha detected, sitekey={captcha_key[:20]}...")
                    try:
                        _solve_hcaptcha(page, browser, captcha_key)
                        submitted = True
                    except Exception as e:
                        submit_error = f"hCaptcha 验证失败: {e}"
                else:
                    # 无 CAPTCHA — 直接点击
                    submit_btn.first.click(force=True, timeout=5000)
                    page.wait_for_timeout(2000)
                    # 检查是否成功
                    current_url = page.url
                    if "/apply" not in current_url:
                        submitted = True
                    else:
                        submit_error = "提交后页面未跳转（可能需要 CAPTCHA 验证）"
        except Exception as e:
            submit_error = str(e)

        browser.close()

        browser.close()

        if submitted:
            msg = f"✅ 已投递（填写了 {fields_filled} 个字段）"
            if errors:
                msg += f"，非致命问题: {'; '.join(errors)}"
            return {
                "success": True,
                "message": msg,
                "fields_filled": fields_filled,
                "errors": errors,
            }
        else:
            return {
                "success": False,
                "message": f"表单已填写但提交失败: {submit_error}",
                "fields_filled": fields_filled,
                "errors": errors,
            }


# ============================================================
# 标准字段填充函数
# ============================================================


def _fill_name_fields(form, profile: Dict) -> bool:
    """填充 first/last name。支持 name=name 单字段或 name=first/last 双字段。"""
    filled = 0
    # 先尝试 name=first + name=last
    first_input = form.locator("input[name='first']")
    last_input = form.locator("input[name='last']")
    if first_input.count() > 0 and last_input.count() > 0:
        first_input.fill(profile.get("first_name", ""))
        last_input.fill(profile.get("last_name", ""))
        filled += 2
        return True

    # 回退：单 name 字段
    name_inputs = form.locator("input[name='name']")
    if name_inputs.count() > 0:
        full_name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()
        name_inputs.first.fill(full_name)
        filled += 1
        return True

    # 再回退：按 placeholder 检测
    for input_el in [form.locator("input[placeholder*='First']"), form.locator("input[placeholder*='first']")]:
        if input_el.count() > 0:
            input_el.fill(profile.get("first_name", ""))
            filled += 1

    for input_el in [form.locator("input[placeholder*='Last']"), form.locator("input[placeholder*='last']")]:
        if input_el.count() > 0:
            input_el.fill(profile.get("last_name", ""))
            filled += 1

    return filled > 0


def _fill_email(form, profile: Dict) -> bool:
    inputs = form.locator("input[type='email']")
    if inputs.count() == 0:
        inputs = form.locator("input[name='email']")
    if inputs.count() > 0:
        inputs.first.fill(profile.get("email", ""))
        return True

    # fallback: placeholder contains "email"
    inputs = form.locator("input[placeholder*='email' i]")
    if inputs.count() > 0:
        inputs.first.fill(profile.get("email", ""))
        return True
    return False


def _fill_phone(form, profile: Dict) -> bool:
    val = profile.get("phone", "")
    if not val:
        return False
    for sel in [
        "input[name='phone']",
        "input[type='tel']",
        "input[placeholder*='phone' i]",
        "input[placeholder*='Phone' i]",
    ]:
        inputs = form.locator(sel)
        if inputs.count() > 0:
            inputs.first.fill(val)
            return True
    return False


def _fill_location(form, profile: Dict) -> bool:
    val = profile.get("location", "")
    if not val:
        return False
    for sel in [
        "input[name='location']",
        "input[placeholder*='location' i]",
        "input[placeholder*='city' i]",
        "input.location-input",
    ]:
        inputs = form.locator(sel)
        if inputs.count() > 0:
            inp = inputs.first
            # Lever 的 location field 有 Google Places 绑定，click 会清空
            # 直接用 JS 设置值 + dispatch event
            inp.evaluate(f"""el => {{
                el.value = '{val.replace("'", "\\'")}';
                el.dispatchEvent(new Event('input', {{bubbles: true, cancelable: true}}));
                el.dispatchEvent(new Event('change', {{bubbles: true, cancelable: true}}));
            }}""")
            return True
    return False


def _fill_company(form, profile: Dict) -> bool:
    """Company / current employer field."""
    for sel in [
        "input[name='org']",
        "input[name='organization']",
        "input[name='company']",
        "input[placeholder*='company' i]",
    ]:
        inputs = form.locator(sel)
        if inputs.count() > 0:
            val = profile.get("company", profile.get("org", "OpenCloud"))
            inputs.first.fill(val)
            return True
    return False


def _fill_linkedin(form, profile: Dict) -> bool:
    for sel in [
        "input[name='urls[LinkedIn]']",
        "input[name*='LinkedIn' i]",
        "input[placeholder*='linkedin' i]",
    ]:
        inputs = form.locator(sel)
        if inputs.count() > 0:
            inputs.first.fill(profile.get("linkedin_url", ""))
            return True
    return False


def _fill_github(form, profile: Dict) -> bool:
    for sel in [
        "input[name*='[GitHub]']",
        "input[name*='GitHub' i]",
        "input[placeholder*='github' i]",
    ]:
        inputs = form.locator(sel)
        if inputs.count() > 0:
            inputs.first.fill(profile.get("github_url", ""))
            return True
    return False


def _fill_portfolio(form, profile: Dict) -> bool:
    for sel in [
        "input[name*='Portfolio' i]",
        "input[placeholder*='portfolio' i]",
    ]:
        inputs = form.locator(sel)
        if inputs.count() > 0:
            inputs.first.fill(profile.get("portfolio_url", ""))
            return True
    return False


def _fill_twitter(form, profile: Dict) -> bool:
    for sel in [
        "input[name*='Twitter' i]",
        "input[name*='[Twitter]' i]",
        "input[placeholder*='twitter' i]",
    ]:
        inputs = form.locator(sel)
        if inputs.count() > 0:
            val = profile.get("twitter_url", "@xiaoxinyang")
            inputs.first.fill(val)
            return True
    return False


def _fill_referral(form, profile: Dict) -> bool:
    """Referral source — 如果 profile 有就填，不然跳过。"""
    val = profile.get("referral_source", "")
    if not val:
        return False
    for sel in [
        "input[name*='Referral' i]",
        "input[name*='refer' i]",
        "input[placeholder*='refer' i]",
    ]:
        inputs = form.locator(sel)
        if inputs.count() > 0:
            inputs.first.fill(val)
            return True
    return False


# ============================================================
# 自定义问题
# ============================================================


def _detect_custom_fields(form) -> List[Dict]:
    """检测 Lever 的自定义卡片字段（name=cards[...][field0] 格式）。

    返回列表，每项: {"name": str, "tag": str, "type": str, "label": str, "options": List[str]}
    """
    fields = []

    # 收集所有 card-based 字段，按 card ID 分组
    # name 格式: cards[<uuid>][field0]
    # 用 set 去重 card uuid
    card_ids = set()
    card_inputs = form.locator("[name^='cards[']")
    cc = card_inputs.count()
    for i in range(cc):
        el = card_inputs.nth(i)
        name = el.get_attribute("name") or ""
        import re
        m = re.match(r'cards\[([a-f0-9-]+)\]', name)
        if m:
            card_ids.add(m.group(1))

    for cid in card_ids:
        # 收集这个 card 的所有 input（包括 hidden 的 baseTemplate）
        all_card_inputs = form.locator(f"[name^='cards[{cid}][']")
        # 如果只有 baseTemplate 没有 field0，跳过
        field0_exists = form.locator(f"[name='cards[{cid}][field0]']").count() > 0
        if not field0_exists:
            continue
        field_inputs = form.locator(f"[name='cards[{cid}][field0]']")
        fic = field_inputs.count()
        if fic == 0:
            continue

        # 确定类型
        first = field_inputs.first
        tag = first.evaluate("e => e.tagName")
        type_ = first.get_attribute("type") or "text"
        name = first.get_attribute("name") or ""

        # 找 label — 在 card 前面的同级父元素中找
        label = _find_label_for_card(form, cid)

        # Radio: 收集选项
        if fic > 1 and type_ == "radio":
            options = []
            for j in range(fic):
                radio = field_inputs.nth(j)
                rid = radio.get_attribute("id") or ""
                opt_label = form.locator(f"label[for='{rid}']").inner_text() if rid else ""
                options.append(opt_label or radio.get_attribute("value") or "")
            fields.append({
                "name": name,
                "tag": "input",
                "type": "radio",
                "label": label,
                "options": options,
            })
        else:
            fields.append({
                "name": name,
                "tag": tag.lower(),
                "type": type_ if type_ != "text" else tag.lower(),
                "label": label,
            })

    return fields


def _find_label_for(form, field_name: str) -> str:
    """尝试找到关联 label 的文本。"""
    label = form.locator(f"label[for='{field_name}']")
    if label.count() > 0:
        return label.inner_text().strip()
    return ""


def _find_label_for_card(form, card_id: str) -> str:
    """通过 card 的 DOM 结构找到对应的 label 文本。
    Lever 的 card 字段有多种 DOM 结构。
    """
    # 方案 A：任意包含 input 且 class 含 card 的容器
    for cls in ['application-question', 'application-label']:
        container = form.locator(f"div:has([name*='{card_id}'])")
        if container.count() > 0:
            # 找内部的 .application-label .text 或 .application-label
            label_text = container.first.locator(".application-label .text")
            if label_text.count() > 0:
                return label_text.first.inner_text().strip()
            label_text = container.first.locator(".application-label")
            if label_text.count() > 0:
                return label_text.first.inner_text().strip()
            # 或者 label 标签
            label_el = container.first.locator("label > .application-label")
            if label_el.count() > 0:
                return label_el.first.inner_text().strip()
    
    # 方案 B：用 input 的 name 属性匹配前一个 sibling
    all_text = form.locator(f"[name^='cards[{card_id}]']").first.evaluate("""el => {{
        let p = el.closest('div');
        if (!p) return '';
        // 找第一个包含文本的子元素
        let texts = p.querySelectorAll('.text, .application-label');
        for (let t of texts) {{
            if (t.textContent.trim()) return t.textContent.trim();
        }}
        return '';
    }}""")
    if all_text:
        return all_text

    return ""


def _fill_custom_field(form, field: Dict, profile: Dict, job: Dict):
    """填充一个自定义字段。

    策略：
    - 先尝试从 profile 关键词匹配
    - 否则看 label 推测回答
    - radio/select 选最合适的选项
    - text/textarea 用 LLM（如果有）或 fallback
    """
    name = field.get("name", "")
    tag = field.get("tag", "input")
    ftype = field.get("type", "text")
    label = field.get("label", "").strip()
    options = field.get("options", [])

    label_lower = label.lower()

    # === 已知字段直接映射 ===
    if label_lower and _handle_known_custom_field(form, name, label_lower, ftype, tag, profile):
        return

    # === Radio / Select: 从选项中选择 ===
    if ftype in ("radio", "select") and options:
        _pick_best_option(form, name, tag, label_lower, options, profile, job)
        return

    # === Text / Textarea: 生成回答 ===
    if ftype in ("text", "textarea"):
        answer = _answer_custom_question(label, profile, job)
        if answer:
            if tag == "textarea":
                form.locator(f"textarea[name='{name}']").fill(answer)
            else:
                form.locator(f"input[name='{name}']").fill(answer)


KNOWN_CUSTOM_FIELDS = {
    "visa": "Yes, I am legally authorized to work in Canada.",
    "work authorization": "Yes, I am legally authorized to work in Canada.",
    "authorized to work": "Yes, I am legally authorized to work in Canada.",
    "sponsorship": "Yes, I do not require visa sponsorship.",
    "require sponsorship": "Yes, I do not require visa sponsorship.",
    "currently require visa sponsorship": "Yes, I do not require visa sponsorship.",
    "legally eligible": "Yes, I am legally eligible to work.",
    "legally authorized": "Yes, I am legally authorized to work in Canada.",
    "work remotely": "Yes, I am open to remote work.",
    "relocate": "Yes, I am willing to relocate.",
    "willing to relocate": "Yes.",
    "gender": "Prefer not to say",
    "race": "Prefer not to say",
    "veteran": "Prefer not to say",
    "disability": "Prefer not to say",
    "how did you hear": "LinkedIn",
    "referred": "",
    "salary expectation": "",
    "expected salary": "",
    "desired salary": "",
    "github": "",
    "portfolio": "",
    "linkedin": "",
    "website": "",
    "twitter": "",
    "interest": "Yes, I am very interested in this opportunity.",
}

KNOWN_BOOLEAN_YES = {"yes", "true", "1", "yes i am", "i am", "yes, currently"}
KNOWN_BOOLEAN_NO = {"no", "false", "0", "no i am not", "i am not", "none"}
KNOWN_CUSTOM_RADIO_TOGGLE_NO = {"gender", "race", "veteran", "disability"}


def _handle_known_custom_field(form, name: str, label_lower: str, ftype: str, tag: str, profile: Dict) -> bool:
    """处理已知标签的自定义字段。返回 True 表示已处理。"""
    answer = None

    for key, default_answer in KNOWN_CUSTOM_FIELDS.items():
        if key in label_lower:
            answer = default_answer
            break

    if answer is None:
        return False

    if answer == "":
        # 这些字段有专门的填充方法，跳过
        return False

    if ftype == "radio":
        _pick_best_option_by_text(form, name, answer)
    elif ftype == "select":
        el = form.locator(f"select[name='{name}']")
        if el.count() > 0:
            el.select_option(label=answer)
    elif tag == "textarea":
        form.locator(f"textarea[name='{name}']").fill(answer)
    else:
        form.locator(f"input[name='{name}']").fill(answer)

    return True


def _pick_best_option(form, name: str, tag: str, label_lower: str, options: List[str], profile: Dict, job: Dict):
    """从选项列表中选择最合适的。"""
    # 尝试已知字段
    for key, default_answer in KNOWN_CUSTOM_FIELDS.items():
        if key in label_lower:
            if default_answer:
                _pick_best_option_by_text(form, name, default_answer)
                return

    # 尝试从 profile/job 推理
    answer = _answer_custom_question_from_options(label_lower, options, profile, job)
    if answer:
        _pick_best_option_by_text(form, name, answer)
        return

    # Fallback: 选第一个非空选项
    for opt in options:
        if opt.strip():
            _pick_best_option_by_text(form, name, opt)
            return


def _pick_best_option_by_text(form, name: str, target: str):
    """在 radio 或 select 中找到匹配的选项并选中。"""
    target_lower = target.lower().strip()
    target_words = set(target_lower.split())

    # Try radio buttons
    radios = form.locator(f"input[name='{name}']")
    rc = radios.count()
    if rc > 1:
        best_score = -1
        best_idx = -1
        for i in range(rc):
            radio = radios.nth(i)
            val = radio.get_attribute("value") or ""
            rid = radio.get_attribute("id") or ""
            label_text = ""
            label_el = form.locator(f"label[for='{rid}']")
            if label_el.count() > 0:
                label_text = label_el.inner_text().lower().strip()
            opt_text = (label_text + " " + val.lower()).strip()

            # 精确包含检查：快速路径
            if target_lower in opt_text or opt_text in target_lower:
                radio.check()
                return

            # 词语级匹配评分
            opt_words = set(opt_text.split())
            overlap = len(target_words & opt_words)
            if overlap > best_score:
                best_score = overlap
                best_idx = i

        if best_idx >= 0 and best_score > 0:
            radios.nth(best_idx).check()
            return

        # fallback: pick last option (usually "Prefer not to say")
        radios.last.check()
        return

    # Try select
    select = form.locator(f"select[name='{name}']")
    if select.count() > 0:
        try:
            select.select_option(label=target)
        except Exception:
            pass


def _answer_custom_question(label: str, profile: Dict, job: Dict) -> str:
    """为自定义文本框生成合适的回答。

    目前用启发式规则；可以后续对接 LLM 生成。
    """
    label_lower = label.lower()

    # Salary
    if "salary" in label_lower or "compensation" in label_lower:
        sal = profile.get("salary_expectation", {})
        if isinstance(sal, dict):
            return f"${sal.get('min', 130000):,} - ${sal.get('max', 250000):,} CAD"
        # fallback to simple desired_salary string
        ds = profile.get("desired_salary", "")
        if ds:
            return f"${ds} CAD"
        return "$120,000 - $160,000 CAD"

    # Why this company / why this role
    if "why" in label_lower and ("company" in label_lower or "join" in label_lower):
        company = job.get("company", "your company")
        title = job.get("title", "this role")
        return (
            f"I am excited about the opportunity to contribute to {company} "
            f"as a {title}. With my background in cloud infrastructure, AI/ML, "
            f"and systems engineering, I believe I can bring significant value to your team."
        )

    # Interest / Are you interested in this role
    if "interest" in label_lower or "agree" in label_lower:
        return "Yes, I am very interested in this opportunity."

    # Referral / how did you hear
    if "hear" in label_lower or "refer" in label_lower:
        return "LinkedIn"

    # Available start date
    if "start" in label_lower or "available" in label_lower:
        return "Immediately / 2 weeks notice"

    # Additional info
    if "additional" in label_lower or "anything else" in label_lower or "other" in label_lower:
        return ""

    # Fallback
    return ""


def _answer_custom_question_from_options(label_lower: str, options: List[str], profile: Dict, job: Dict) -> str:
    """从 options 中选择最合适的回答。"""
    # Authorized to work in X?
    if "authorized" in label_lower or "visa" in label_lower or "sponsor" in label_lower:
        for opt in options:
            ol = opt.lower()
            if "yes" in ol and ("authorized" in ol or "visa" in ol):
                return opt
        return "Yes"

    # Require sponsorship?
    if "sponsor" in label_lower:
        for opt in options:
            ol = opt.lower()
            if "no" in ol and "require" not in ol:
                return opt
        return "No"

    # Gender / Race / Veteran / Disability
    for cat in ["gender", "race", "veteran", "disability"]:
        if cat in label_lower:
            for opt in options:
                if "prefer not" in opt.lower():
                    return opt
            if options:
                return options[-1]  # last option is usually "Prefer not to say"

    return ""


# ============================================================
# hCaptcha 解决（通过 2Captcha）
# ============================================================


def _get_2captcha_key() -> str:
    """从环境变量或 ~/.bashrc 读取 2Captcha API key。"""
    key = os.environ.get("CAPTCHA_API_KEY", "") or os.environ.get("2CAPTCHA_API_KEY", "")
    if not key:
        try:
            rc_path = os.path.expanduser("~/.bashrc")
            if os.path.isfile(rc_path):
                with open(rc_path) as f:
                    for line in f:
                        m = re.match(r'^\s*export\s+(?:CAPTCHA_API_KEY|2CAPTCHA_API_KEY)="\'?(\S+?)"\'?\s*$', line)
                        if m:
                            key = m.group(1)
                            break
        except Exception:
            pass
    return key


def _resolve_hcaptcha_token(api_key: str, sitekey: str, page_url: str) -> str:
    """通过 2Captcha API 获取 hCaptcha token。"""
    import urllib.request
    import urllib.parse

    in_data = {"key": api_key, "method": "hcaptcha", "sitekey": sitekey, "pageurl": page_url, "json": 1}
    encoded = urllib.parse.urlencode(in_data).encode()
    req = urllib.request.Request("https://2captcha.com/in.php", data=encoded, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        in_result = json.loads(resp.read().decode())
    if in_result.get("status") != 1:
        raise RuntimeError(f"2Captcha 提交失败: {in_result.get('request', 'unknown')}")

    cid = in_result["request"]
    logger.info(f"2Captcha task submitted: {cid[:16]}...")

    for i in range(90):
        time.sleep(2)
        res_data = {"key": api_key, "action": "get", "id": cid, "json": 1}
        encoded = urllib.parse.urlencode(res_data).encode()
        req = urllib.request.Request("https://2captcha.com/res.php", data=encoded, headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            res_result = json.loads(resp.read().decode())
        if res_result.get("status") == 1:
            token = res_result["request"]
            logger.info(f"hCaptcha token received ({len(token)} chars)")
            return token
        elif res_result.get("status") != 0:
            raise RuntimeError(f"2Captcha 错误: {res_result.get('request', 'unknown')}")
        if i % 10 == 0:
            logger.info(f"Still waiting for 2Captcha ({i*2}s)...")
    raise RuntimeError("2Captcha 超时（3 分钟未解决）")


def _solve_hcaptcha(page, browser, sitekey: str):
    """通过 2Captcha 解决 hCaptcha 并提交 Lever 申请。

    Lever 使用 hCaptcha enclave 模式，hCaptcha 通过服务器端验证。
    2Captcha 返回的 token 如果通过服务端验证，用 form.submit() 提交。
    """
    api_key = _get_2captcha_key()
    if not api_key:
        raise RuntimeError(
            "需要 2Captcha API key 才能自动绕过 hCaptcha。\n"
            "请在 ~/.bashrc 中添加:  export CAPTCHA_API_KEY=你的key\n"
            "获取方式: https://2captcha.com"
        )

    page_url = page.url
    logger.info(f"Getting hCaptcha token from 2Captcha (sitekey={sitekey[:16]}...)")
    try:
        token = _resolve_hcaptcha_token(api_key, sitekey, page_url)
    except RuntimeError as e:
        # 2Captcha 超时或失败时，提供替代方案
        logger.error(f"2Captcha failed: {e}")
        raise RuntimeError(
            f"hCaptcha 自动解决失败（2Captcha 超时）。\n"
            "请手动完成验证：在浏览器中打开此页面，完成 hCaptcha 后提交。\n"
            f"{page_url}"
        )

    # 注入 token 并提交（用 form.submit() 原生方式，绕过 Lever 的 JS 点击逻辑）
    logger.info(f"Injecting hCaptcha token ({len(token)} chars)")

    page.evaluate("(t) => { document.getElementById('hcaptchaResponseInput').value = t; }", token)

    # 验证 token 注入
    check = page.evaluate('document.getElementById("hcaptchaResponseInput")?.value?.length || 0')
    logger.info(f"hcaptchaResponseInput contains {check} chars")

    if check == 0:
        raise RuntimeError("hCaptcha token 注入失败")

    # 用原生 form.submit() 提交（触发完整的 POST 请求包括 h-captcha-response 字段）
    logger.info("Submitting form via native form.submit()...")
    page.evaluate('document.getElementById("application-form").submit()')

    # 等待提交结果（form.submit() 会导航页面，需要足够时间等待重定向或错误返回）
    page.wait_for_timeout(12000)

    # 验证
    current_url = page.url
    if "/apply" not in current_url:
        logger.info(f"Submit successful, navigated to: {current_url}")
        return

    # 检查成功文本
    body_text = page.locator("body").inner_text().lower()
    if any(w in body_text for w in ["thank you", "thanks for", "submitted", "received", "application complete"]):
        logger.info("Submit confirmed via success text on page")
        return

    # 检查错误信息
    error_text = page.locator("body").inner_text()[:200]
    logger.warning(f"Submit failed, page content: {error_text}")

    raise RuntimeError(
        f"提交被 Lever 服务端拒绝（HTTP 400）。\n"
        f"2Captcha 的 hCaptcha token 对 Lever 无效，可能原因：\n"
        "1. Lever 使用 hCaptcha enterprise/enclave 模式，2Captcha 支持不完整\n"
        "2. 可尝试 CapSolver 作为替代（https://capsolver.com）\n"
        "3. 或手动完成验证后提交\n"
        f"页面: {page_url}"
    )


# ============================================================
# EEO
# ============================================================


def _fill_eeo(form, profile: Dict):
    """处理 EEO 下拉选择（gender, race, veteran）。"""
    eeo_defaults = profile.get("eeo_defaults", {})

    eeo_fields = ["gender", "race", "veteran", "disability"]
    for name in eeo_fields:
        select = form.locator(f"select[name='eeo[{name}]']")
        if select.count() == 0:
            continue
        default_value = eeo_defaults.get(name, "")
        if not default_value:
            # 选择 prefer/decline 选项
            try:
                options = select.first.locator("option")
                oc = options.count()
                for i in range(oc):
                    opt = options.nth(i)
                    val = opt.get_attribute("value") or ""
                    text = opt.inner_text() or ""
                    if "prefer" in (text + val).lower() or "decline" in (text + val).lower():
                        select.first.select_option(value=val, timeout=3000)
                        break
            except Exception:
                pass
        else:
            try:
                select.first.select_option(value=default_value, timeout=3000)
            except Exception:
                pass


# ============================================================
# 申请记录
# ============================================================


def _record_application(job: Dict, result: Dict):
    """保存投递记录到 history.json。"""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

    record = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S") + "_" + (job.get("id", "")[:8] or "lever"),
        "job_id": job.get("id", ""),
        "job_title": job.get("title", ""),
        "company": job.get("company", ""),
        "source": job.get("source", "Lever"),
        "method": "auto_apply",
        "details": {
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "fields_filled": result.get("fields_filled", 0),
            "job_url": result.get("job_url", job.get("url", "")),
        },
        "applied_at": datetime.now().isoformat(),
        "status": "applied" if result.get("success") else "failed",
    }

    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
        except Exception:
            pass

    history.insert(0, record)

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
