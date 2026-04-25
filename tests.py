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
