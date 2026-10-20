import sys, os
sys.path.insert(0, os.getcwd())
import unittest
import sites.telesat as telesat
from sites.registry import get_adapter


class TelesatAdapterTest(unittest.TestCase):
    def test_registered(self):
        self.assertIsNotNone(get_adapter(
            "https://www.telesat.com/careers/jobs/76ec3bf1-6923-4b1c-85b9-339cd3dbe047"))

    def test_normalize_url_adds_trailing_slash(self):
        u = "https://www.telesat.com/careers/jobs/76ec3bf1-6923-4b1c-85b9-339cd3dbe047"
        self.assertTrue(telesat.normalize_url(u).endswith("/"))
        self.assertEqual(telesat.normalize_url(u + "?utm=x"), telesat.normalize_url(u))

    def test_extract_fixture(self):
        html = open("tests_fixtures_telesat.html", encoding="utf-8").read()
        r = telesat.extract(html, "")
        self.assertIn("Network Management", r["title"])
        self.assertEqual(r["company"], "Telesat")
        self.assertEqual(r["location"], "Ottawa, Ontario")
        self.assertGreater(len(r["description"]), 1000)
        self.assertIn("NETCONF", r["description"])
        self.assertIn("apply_url", r)

    def test_live_fetch(self):
        url = "https://www.telesat.com/careers/jobs/76ec3bf1-6923-4b1c-85b9-339cd3dbe047"
        from job_agent_core import JobAgent
        a = JobAgent()
        r = a.fetch_job_from_url(url)
        self.assertTrue(r["title"])
        self.assertGreater(len(r["description"]), 500)


if __name__ == "__main__":
    unittest.main(verbosity=2)
