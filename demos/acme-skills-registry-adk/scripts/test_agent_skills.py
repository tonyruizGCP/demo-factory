#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""End-to-End Automated Test Suite for ACME Retail Skills & ADK Agent."""

import asyncio
import json
import subprocess
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.tools import query_store_sales, query_store_inventory, query_store_metadata
from app.registry import get_skill_registry
from app.agent import root_agent, app, skill_toolset


class TestRetailDataTools(unittest.TestCase):
    """Verifies that retail business data tools function correctly."""

    def test_query_store_sales_downtown(self):
        sales = query_store_sales(store_id="104", date_range="last_30_days")
        self.assertEqual(sales["store_id"], "104")
        self.assertEqual(sales["gross_revenue"], 982500.00)
        self.assertGreater(sales["foot_traffic"], 40000)
        self.assertIn("Apparel & Outerwear", sales["departments"])

    def test_query_store_sales_yesterday(self):
        sales = query_store_sales(store_id="208", date_range="yesterday")
        self.assertEqual(sales["store_id"], "208")
        self.assertEqual(sales["gross_revenue"], 28400.00)
        self.assertEqual(sales["reporting_period"], "yesterday")

    def test_query_store_inventory(self):
        inv = query_store_inventory(store_id="104")
        self.assertEqual(inv["store_id"], "104")
        self.assertGreater(inv["in_stock_rate_pct"], 90.0)
        self.assertGreater(len(inv["out_of_stock_skus"]), 0)


class TestSkillRegistryAndLoading(unittest.TestCase):
    """Verifies the Skill Registry discovery, retrieval, and schema adherence."""

    def setUp(self):
        self.registry = get_skill_registry()

    def test_list_and_search_skills(self):
        async def run_search():
            # Search for performance review
            res1 = await self.registry.search_skills(query="store performance")
            names1 = [f.name for f in res1]
            self.assertIn("store-performance-review", names1)

            # Search for morning recap
            res2 = await self.registry.search_skills(query="daily huddle recap")
            names2 = [f.name for f in res2]
            self.assertIn("daily-summary-recap", names2)

            # Search for inventory
            res3 = await self.registry.search_skills(query="inventory audit")
            names3 = [f.name for f in res3]
            self.assertIn("inventory-optimization-audit", names3)

        asyncio.run(run_search())

    def test_get_skill_content(self):
        async def run_get():
            skill = await self.registry.get_skill(name="store-performance-review")
            self.assertEqual(skill.name, "store-performance-review")
            self.assertIn("calculate_store_kpis.py", skill.resources.list_scripts())
            self.assertIn("kpi_benchmarks.md", skill.resources.list_references())
            self.assertIn("Store Performance Review Skill", skill.instructions)

        asyncio.run(run_get())


class TestSkillScriptExecution(unittest.TestCase):
    """Verifies that scripts bundled in skills execute accurately and return structured JSON."""

    def test_calculate_store_kpis_script(self):
        script_path = ROOT_DIR / "skills" / "store-performance-review" / "scripts" / "calculate_store_kpis.py"
        cmd = [
            sys.executable, str(script_path),
            "--revenue", "982500",
            "--target", "950000",
            "--traffic", "46200",
            "--transactions", "11840",
            "--labor_hours", "4480"
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Script failed: {proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertEqual(data["revenue_actual"], 982500.0)
        self.assertEqual(data["variance_dollars"], 32500.0)
        self.assertAlmostEqual(data["conversion_rate_percent"], 25.63, places=1)
        self.assertEqual(data["evaluation_flags"]["budget_status"], "🟢 On Target")

    def test_generate_huddle_brief_script(self):
        script_path = ROOT_DIR / "skills" / "daily-summary-recap" / "scripts" / "generate_huddle_brief.py"
        cmd = [
            sys.executable, str(script_path),
            "--sales", "34850",
            "--target", "33000",
            "--transactions", "482"
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Script failed: {proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertEqual(data["sales"], 34850.0)
        self.assertGreater(data["variance_pct"], 0.0)


class TestADKAgentConfiguration(unittest.TestCase):
    """Verifies ADK agent structure, module app object, and tools binding."""

    def test_agent_attributes(self):
        self.assertEqual(root_agent.name, "retail_data_analyst")
        self.assertEqual(app.name, "app")
        tool_names = [getattr(t, "__name__", getattr(t, "name", str(t))) for t in root_agent.tools]
        self.assertIn("query_store_sales", tool_names)
        self.assertIn("query_store_inventory", tool_names)

    def test_skill_toolset_tools(self):
        async def check_tools():
            tools = await skill_toolset.get_tools()
            tool_names = [t.name for t in tools]
            self.assertIn("list_skills", tool_names)
            self.assertIn("load_skill", tool_names)
            self.assertIn("load_skill_resource", tool_names)
            self.assertIn("run_skill_script", tool_names)
            self.assertIn("search_skills", tool_names)

        asyncio.run(check_tools())


def main():
    print("=" * 70)
    print("🧪 Running ACME Retail Skills & ADK Agent E2E Verification Suite")
    print("=" * 70)
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n✅ All 7 verification test cases passed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Verification failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
