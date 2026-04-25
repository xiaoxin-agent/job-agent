#!/usr/bin/env python3
"""
求职Agent - 测试套件
验证所有核心功能和HTTP接口正常
"""

import sys
import os
import json
import time
import io
import unittest
import threading
from http.server import HTTPServer
from urllib.request import Request, urlopen
from urllib.error import URLError

# 确保能导入job_agent_core
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from job_agent_core import JobAgent, UserProfile, JobAnalyzer, JobTracker


class TestCoreModule(unittest.TestCase):
    """核心模块单元测试"""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = "/tmp/agent_test_data"
        os.makedirs(cls.test_dir, exist_ok=True)
        cls.agent = JobAgent(data_dir=cls.test_dir)
    
    def test_01_agent_init(self):
        """Agent初始化正常"""
        self.assertIsNotNone(self.agent)
        self.assertIsNotNone(self.agent.profile)
        self.assertIsNotNone(self.agent.engine)
        self.assertIsNotNone(self.agent.analyzer)
        self.assertIsNotNone(self.agent.tracker)
    
    def test_02_profile_load(self):
        """用户画像加载正常，有默认技能"""
        p = self.agent.profile.profile
        self.assertIn("skills", p)
        self.assertGreater(len(p.get("skills", {})), 0)
        self.assertIn("Cloud", p.get("skills", {}))
    
    def test_03_profile_update(self):
        """更新用户画像"""
        self.agent.update_profile({"name": "测试用户", "experience_years": 8})
        p = self.agent.profile.profile
        self.assertEqual(p.get("name"), "测试用户")
        self.assertEqual(p.get("experience_years"), 8)
    
    def test_04_skill_keywords(self):
        """获取技能关键词非空"""
        keywords = self.agent.profile.get_skill_keywords()
        self.assertIsInstance(keywords, list)
        self.assertGreater(len(keywords), 0)
    
    def test_05_search_links(self):
        """生成搜索链接"""
        links = self.agent.engine.generate_search_links(["Kernel", "ML", "Cloud"])
        self.assertIsInstance(links, list)
        self.assertGreater(len(links), 0)
        for link in links:
            self.assertIn("url", link)
            self.assertIn("title", link)
            self.assertIn("company", link)
    
    def test_06_analyze_job(self):
        """职位分析正常，生成匹配度"""
        job = {
            "title": "Senior ML Kernel Engineer",
            "company": "NVIDIA",
            "location": "Toronto, Canada",
            "description": "Deep learning GPU performance optimization with PyTorch, CUDA, Linux kernel",
            "url": "https://example.com/job/1",
            "source": "test"
        }
        result = self.agent.analyzer.analyze_job(job)
        self.assertTrue(result.get("analyzed"))
        self.assertGreaterEqual(result.get("match_score", 0), 0)
        self.assertLessEqual(result.get("match_score", 0), 100)
        self.assertIn("match_details", result)
    
    def test_07_tracker_save_and_stats(self):
        """保存职位到跟踪列表"""
        job = {
            "title": "Cloud AI Engineer",
            "company": "Amazon",
            "location": "Vancouver",
            "match_score": 85,
            "source": "test"
        }
        ok = self.agent.save_job(job)
        self.assertTrue(ok)
        
        stats = self.agent.tracker.get_stats()
        self.assertGreaterEqual(stats.get("total"), 1)
        self.assertGreaterEqual(stats.get("avg_match_score"), 0)
    
    def test_08_tracker_duplicate(self):
        """重复保存应返回False"""
        job = {
            "title": "Cloud AI Engineer",
            "company": "Amazon",
            "location": "Vancouver",
            "match_score": 85,
            "source": "test"
        }
        ok = self.agent.save_job(job)
        self.assertFalse(ok)
    
    def test_09_tracker_update_status(self):
        """更新申请状态"""
        job_id = self.agent.tracker.tracked_jobs[0]["id"]
        ok = self.agent.update_job_status(job_id, "applied", "已提交简历")
        self.assertTrue(ok)
        
        job = self.agent.tracker.get_job(job_id)
        self.assertEqual(job.get("status"), "applied")
        self.assertEqual(job.get("notes"), "已提交简历")
        self.assertIsNotNone(job.get("applied_date"))
    
    def test_10_generate_letter(self):
        """生成求职信"""
        job = {
            "title": "Senior ML Performance Engineer",
            "company": "Google DeepMind",
            "match_score": 78,
            "match_details": {
                "skill_match": [
                    {"category": "AI/ML", "keyword": "Machine Learning", "level": "expert"},
                    {"category": "Python", "keyword": "Python", "level": "expert"}
                ]
            }
        }
        letter = self.agent.generate_cover_letter(job)
        self.assertIsInstance(letter, str)
        self.assertGreater(len(letter), 50)
        self.assertIn("Google DeepMind", letter)
        self.assertIn("Senior ML Performance Engineer", letter)
    
    def test_11_search_all(self):
        """全源搜索不崩溃"""
        result = self.agent.run_search()
        self.assertIn("jobs", result)
        self.assertIn("search_links", result)
        self.assertIn("stats", result)
    
    def test_12_search_history(self):
        """搜索历史保存正常"""
        history = self.agent._get_search_history()
        self.assertIsInstance(history, list)
        self.assertGreaterEqual(len(history), 1)


class TestWebServer(unittest.TestCase):
    """HTTP接口集成测试"""

    # 共享agent引用，供测试方法访问
    _agent = None

    @classmethod
    def setUpClass(cls):
        cls.port = 19876  # 测试端口
        
        # 启动测试服务器
        from job_agent_web import JobAgentHandler
        
        # 用临时目录的agent
        cls.test_dir = "/tmp/agent_test_web"
        os.makedirs(cls.test_dir, exist_ok=True)
        cls._agent = JobAgent(data_dir=cls.test_dir)
        JobAgentHandler.agent = cls._agent
        
        cls.server = HTTPServer(("", cls.port), JobAgentHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)  # 等服务器启动
        
        # 验证服务器启动
        try:
            resp = urlopen(f"http://localhost:{cls.port}/")
            cls.server_ok = resp.status == 200
        except:
            cls.server_ok = False
    
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
    
    def test_01_home_page(self):
        """首页返回200"""
        resp = urlopen(f"http://localhost:{self.port}/")
        self.assertEqual(resp.status, 200)
        html = resp.read().decode("utf-8")
        self.assertIn("求职Agent", html)
    
    def test_02_dashboard_page(self):
        """仪表盘返回200"""
        resp = urlopen(f"http://localhost:{self.port}/dashboard")
        self.assertEqual(resp.status, 200)
        html = resp.read().decode("utf-8")
        self.assertIn("仪表盘", html)
    
    def test_03_search_page(self):
        """搜索页面返回200"""
        resp = urlopen(f"http://localhost:{self.port}/search")
        self.assertEqual(resp.status, 200)
        html = resp.read().decode("utf-8")
        self.assertIn("搜索", html)
    
    def test_04_tracked_page(self):
        """跟踪页面返回200"""
        resp = urlopen(f"http://localhost:{self.port}/tracked")
        self.assertEqual(resp.status, 200)
        html = resp.read().decode("utf-8")
        self.assertIn("跟踪职位", html)
    
    def test_05_profile_page(self):
        """画像页面返回200"""
        resp = urlopen(f"http://localhost:{self.port}/profile")
        self.assertEqual(resp.status, 200)
        html = resp.read().decode("utf-8")
        self.assertIn("用户画像", html)
        self.assertIn("Cloud", html)  # 需要有技能数据
    
    def test_06_letter_page(self):
        """求职信页面返回200"""
        resp = urlopen(f"http://localhost:{self.port}/letter")
        self.assertEqual(resp.status, 200)
        html = resp.read().decode("utf-8")
        self.assertIn("求职信", html)
    
    def test_07_api_search(self):
        """搜索API返回正确JSON"""
        req = Request(
            f"http://localhost:{self.port}/api/run_search",
            method="POST"
        )
        resp = urlopen(req)
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(data.get("success"))
        self.assertIn("jobs", data)
        self.assertIn("stats", data)
        self.assertIn("search_links", data)

    def test_07b_api_search_space_separated(self):
        """空格分隔的关键词应正确解析并返回结果"""
        req = Request(
            f"http://localhost:{self.port}/api/run_search",
            data=json.dumps({"keywords": "software cloud"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        resp = urlopen(req)
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(data.get("success"))
        self.assertGreater(len(data.get("jobs", [])), 0,
            msg="空格分隔 'software cloud' 应返回至少1个职位")

    def test_07c_api_search_comma_separated(self):
        """逗号分隔的关键词也应正确解析"""
        req = Request(
            f"http://localhost:{self.port}/api/run_search",
            data=json.dumps({"keywords": "software,cloud"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        resp = urlopen(req)
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(data.get("success"))
        self.assertGreater(len(data.get("jobs", [])), 0,
            msg="逗号分隔 'software,cloud' 应返回至少1个职位")

    def test_08_api_save_job(self):
        """保存职位API"""
        req = Request(
            f"http://localhost:{self.port}/api/save_job",
            data=json.dumps({
                "job": {
                    "title": "Test Engineer",
                    "company": "Test Corp",
                    "location": "Toronto",
                    "match_score": 80,
                    "source": "test"
                }
            }).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        resp = urlopen(req)
        data = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(data.get("success"))
    
    def test_09_api_update_status(self):
        """更新状态API"""
        # 先保存一个职位
        agent = self._agent
        agent.save_job({
            "title": "Status Test",
            "company": "Test Co",
            "location": "Remote",
            "match_score": 70
        })
        job_id = agent.tracker.tracked_jobs[0]["id"]
        
        req = Request(
            f"http://localhost:{self.port}/api/update_status",
            data=json.dumps({
                "job_id": job_id,
                "status": "interviewing",
                "notes": "第一轮面试"
            }).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        resp = urlopen(req)
        data = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(data.get("success"))
    
    def test_10_api_update_profile(self):
        """更新画像API"""
        req = Request(
            f"http://localhost:{self.port}/api/update_profile",
            data=json.dumps({
                "name": "WebTest User",
                "title": "ML Engineer"
            }).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        resp = urlopen(req)
        data = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(data.get("success"))
        
        # 验证已保存
        agent = self._agent
        self.assertEqual(agent.profile.profile.get("name"), "WebTest User")
    
    def test_11_api_generate_letter(self):
        """生成求职信API"""
        req = Request(
            f"http://localhost:{self.port}/api/generate_letter",
            data=json.dumps({
                "job": {
                    "title": "Senior ML Engineer",
                    "company": "NVIDIA",
                    "match_score": 85,
                    "match_details": {
                        "skill_match": [
                            {"category": "AI/ML", "keyword": "Machine Learning", "level": "expert"}
                        ]
                    }
                }
            }).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        resp = urlopen(req)
        data = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(data.get("success"))
        self.assertIn("letter", data)
        self.assertGreater(len(data["letter"]), 50)
    
    def test_12_404(self):
        """不存在的路径返回404"""
        try:
            resp = urlopen(f"http://localhost:{self.port}/nonexistent")
            self.assertEqual(resp.status, 404)
        except URLError as e:
            # HTTPError 也说明服务器正确响应了
            self.assertEqual(e.code, 404)

    def test_13_resume_page(self):
        """简历库页面返回200"""
        resp = urlopen(f"http://localhost:{self.port}/resumes")
        self.assertEqual(resp.status, 200)
        html = resp.read().decode("utf-8")
        self.assertIn("简历库", html)

    def test_14_resume_add_and_list(self):
        """模拟浏览器添加简历：multipart上传到简历库，然后列表返回新简历"""
        import requests
        url = f"http://localhost:{self.port}/api/add_resume_multipart"
        files = {'resume': ('my_resume.pdf', b'%PDF-1.4 fake resume content', 'application/pdf')}
        data = {'name': '我的简历.pdf'}
        r = requests.post(url, files=files, data=data)
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d.get("success"), f"上传失败: {d.get('error')}")
        self.assertIn("resume", d)
        resume_id = d["resume"]["id"]
        self.assertIsNotNone(resume_id)
        self.assertEqual(d["resume"]["name"], "我的简历.pdf")
        
        # 验证列表API能查到
        r2 = requests.get(f"http://localhost:{self.port}/api/list_resumes")
        d2 = r2.json()
        self.assertTrue(d2.get("success"))
        ids = [r["id"] for r in d2.get("resumes", [])]
        self.assertIn(resume_id, ids, f"新添加的简历 {resume_id} 应在列表中")
        
        # 验证GET下载
        r3 = requests.get(f"http://localhost:{self.port}/api/get_resume?resume_id={resume_id}")
        self.assertEqual(r3.status_code, 200)
        self.assertGreater(len(r3.content), 10)
        self.assertIn(b"fake resume", r3.content)
        
        return resume_id
    
    def test_15_resume_assign_and_delete(self):
        """模拟浏览器：申请职位时关联简历，然后删除简历"""
        import requests
        # 先上传一个简历
        r = requests.post(f"http://localhost:{self.port}/api/add_resume_multipart",
            files={'resume': ('cv.pdf', b'%PDF CV content', 'application/pdf')},
            data={'name': 'cv.pdf'})
        resume_id = r.json()["resume"]["id"]
        
        # 保存一个职位
        agent = self._agent
        agent.save_job({
            "title": "Resume Test Job",
            "company": "Test Co",
            "location": "Toronto",
            "match_score": 75
        })
        job_id = agent.tracker.tracked_jobs[0]["id"]
        
        # 关联简历到职位
        r2 = requests.post(f"http://localhost:{self.port}/api/assign_resume",
            json={"job_id": job_id, "resume_id": resume_id})
        d2 = r2.json()
        self.assertTrue(d2.get("success"))
        
        # 验证职位有了resume_id
        job = agent.tracker.get_job(job_id)
        self.assertEqual(job.get("resume_id"), resume_id)
        self.assertEqual(job.get("resume_name"), "cv.pdf")
        
        # 删除简历
        r3 = requests.post(f"http://localhost:{self.port}/api/delete_resume",
            json={"resume_id": resume_id})
        d3 = r3.json()
        self.assertTrue(d3.get("success"))
        
        # 验证简历不在列表
        r4 = requests.get(f"http://localhost:{self.port}/api/list_resumes")
        ids = [r["id"] for r in r4.json().get("resumes", [])]
        self.assertNotIn(resume_id, ids)
        
        # 验证职位引用也被清除
        job = agent.tracker.get_job(job_id)
        self.assertIsNone(job.get("resume_id"))
        self.assertIsNone(job.get("resume_name"))
    
    def test_16_resume_tracked_page_has_js(self):
        """跟踪页面包含 resume 相关 JS 函数"""
        resp = urlopen(f"http://localhost:{self.port}/tracked")
        html = resp.read().decode("utf-8")
        self.assertIn("quickApply", html)
        self.assertIn("linkResume", html)
        self.assertIn("uploadNewResumeAndLink", html)
        self.assertIn("assignResume", html)
        self.assertIn("assign_resume", html)
    
    def test_18_js_page_validates(self):
        """所有页面的 JS 语法正确 (用 Node.js 验证)"""
        import subprocess, json
        pages = ["/", "/tracked", "/resumes", "/dashboard", "/search"]
        node_script = """
const http = require('http');
const results = [];
let done = 0;
const total = %d;
function check(page) {
    http.get('http://localhost:%d' + page, res => {
        let data = '';
        res.on('data', c => data += c);
        res.on('end', () => {
            const scripts = [...data.matchAll(/<script>([\\s\\S]*?)<\\/script>/g)];
            if (scripts.length === 0) {
                results.push({page, valid: true, note: 'no script tag'});
            } else {
                scripts.forEach((m, i) => {
                    try {
                        new Function(m[1]);
                        results.push({page, idx: i, valid: true});
                    } catch(e) {
                        const lines = m[1].split('\\n');
                        const errLine = e.lineNumber || 0;
                        results.push({page, idx: i, valid: false,
                            error: e.message,
                            line: errLine,
                            context: lines.slice(Math.max(0,errLine-3), errLine+2).join('\\n').trim()});
                    }
                });
            }
            done++;
            if (done >= total) {
                console.log(JSON.stringify(results));
            }
        });
    });
}
""" % (len(pages), self.port)
        for p in pages:
            node_script += f"""
setTimeout(() => check('{p}'), 100);
"""
        node_script += """
setTimeout(() => { if (done < total) { done = total; console.log(JSON.stringify(results)); } }, 5000);
"""
        proc = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 0, f"Node JS error: {proc.stderr}")
        results = json.loads(proc.stdout.strip())
        errors = [r for r in results if not r.get("valid")]
        if errors:
            msg = "JS语法错误:\n"
            for e in errors:
                msg += f"  {e['page']} [script {e.get('idx','?')}]: {e.get('error','?')}\n"
                msg += f"    {e.get('context','')}\n"
            self.fail(msg)
        self.assertGreater(len(results), 0)

    def test_19_resume_page_delete_button_html(self):
        """验证简历库页面删除按钮的 HTML 正确"""
        import requests
        resp = urlopen(f"http://localhost:{self.port}/resumes")
        html = resp.read().decode("utf-8")

        # 不要用 onclick 拼接参数（之前的 bug 来源）
        import re
        # 检查 JS 模板中 data-resume-id 的模式
        # 注意：实际列表由 JS 动态渲染，HTML 源码中只有模板字符串
        self.assertIn('data-resume-id="', html,
            "JS 模板字符串应生成 data-resume-id 属性")
        self.assertIn("btn-del-resume", html,
            "JS 模板字符串应有 btn-del-resume 类")

        # 验证点击事件委托和确认框
        self.assertIn("document.addEventListener", html,
            "页面应使用事件委托处理点击")
        self.assertIn("btn-del-resume", html,
            "事件委托应查找 btn-del-resume 类")
        self.assertIn("delete_resume", html,
            "事件委托应调用 delete_resume API")

    def test_20_resume_page_upload_button_html(self):
        """验证上传按钮 HTML 正确"""
        resp = urlopen(f"http://localhost:{self.port}/resumes")
        html = resp.read().decode("utf-8")
        self.assertIn('onclick="uploadResume()"', html)
        self.assertIn("add_resume_multipart", html)


def cleanup():
    """清理测试数据"""
    import shutil
    for d in ["/tmp/agent_test_data", "/tmp/agent_test_web"]:
        if os.path.exists(d):
            shutil.rmtree(d)


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 求职Agent 测试套件")
    print("=" * 60)
    
    # 先清理
    cleanup()
    
    # 运行测试
    suite = unittest.TestSuite()
    
    # 核心模块测试
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(TestCoreModule))
    
    # Web接口测试
    suite.addTests(loader.loadTestsFromTestCase(TestWebServer))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 清理
    cleanup()
    
    print(f"\n{'='*60}")
    print(f"通过: {result.testsRun - len(result.failures) - len(result.errors)} / {result.testsRun}")
    if result.failures:
        print(f"❌ 失败: {len(result.failures)}")
    if result.errors:
        print(f"❌ 错误: {len(result.errors)}")
    print(f"{'='*60}")
    
    sys.exit(0 if result.wasSuccessful() else 1)
