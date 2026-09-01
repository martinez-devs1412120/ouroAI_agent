"""Tests for the skills loader — the discovery contract.

These guarantee the loader does what its docstring says: every folder
under skills/ with a code.py is found, its TOOLS dict is registered,
and its TOOL_SCHEMAS reach the model. If a future refactor breaks any
of these, the agent silently loses tools — the kind of bug that only
shows up when a user asks 'why can't you...?'."""

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from skills_loader import list_skill_names, get_tools_and_schemas


class TestSkillsDiscovery(unittest.TestCase):
    """The discovery contract."""

    def test_all_skills_discovered(self):
        # Six skills shipped: calculator, run_python, safe_fs, studyrag,
        # sysinfo, web_search. If a future piece renames a folder, update
        # this test, but never let it silently drop.
        names = set(list_skill_names())
        expected = {"calculator", "run_python", "safe_fs", "studyrag", "sysinfo", "web_search"}
        self.assertTrue(expected.issubset(names),
                        f"missing skills: {expected - names}")

    def test_tools_have_callable_functions(self):
        """Every tool in the registry is a real callable — no missing
        implementations would survive this test."""
        tools, _ = get_tools_and_schemas()
        for name, func in tools.items():
            self.assertTrue(callable(func), f"tool {name!r} is not callable")

    def test_schemas_match_tools(self):
        """Every tool name appears in a schema; no schema describes a
        tool that doesn't exist. A mismatch here means the model can
        call a tool we never wrote, or won't see a tool we did write."""
        tools, schemas = get_tools_and_schemas()
        tool_names = set(tools.keys())
        schema_names = {s["function"]["name"] for s in schemas}
        self.assertEqual(tool_names, schema_names,
                         f"tools missing from schemas: {tool_names - schema_names}; "
                         f"schemas with no tool: {schema_names - tool_names}")

    def test_skill_filter_narrows(self):
        """The --skill flag's underlying filter actually filters."""
        all_tools, _ = get_tools_and_schemas()
        from agent import _filter_tools
        narrowed_tools, _ = _filter_tools(all_tools, [], ["calculator"])
        self.assertEqual(set(narrowed_tools.keys()), {"calculator"})

    def test_all_schemas_have_required_fields(self):
        """Every schema has type/function/function.name/function.description/
        function.parameters. If any are missing, the model will silently
        not see the tool when Groq validates the request."""
        _, schemas = get_tools_and_schemas()
        for s in schemas:
            with self.subTest(tool=s.get("function", {}).get("name", "?")):
                self.assertEqual(s.get("type"), "function")
                fn = s.get("function", {})
                self.assertIn("name", fn)
                self.assertIn("description", fn)
                self.assertIn("parameters", fn)


if __name__ == "__main__":
    unittest.main()
