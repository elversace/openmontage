"""Smoke tests for the ChatGPT MCP bridge (no provider calls or spend)."""
import unittest

from chatgpt_mcp.server import _PROJECT_ID, _TOOL_NAME
from lib.pipeline_loader import list_pipelines, load_pipeline


class ChatGPTMCPBridgeTests(unittest.TestCase):
    def test_project_ids_are_kebab_case_and_not_paths(self):
        self.assertTrue(_PROJECT_ID.fullmatch("anime-short"))
        self.assertFalse(_PROJECT_ID.fullmatch("../outside"))
        self.assertFalse(_PROJECT_ID.fullmatch("Upper Case"))

    def test_tool_names_are_registry_identifiers(self):
        self.assertTrue(_TOOL_NAME.fullmatch("image_selector"))
        self.assertFalse(_TOOL_NAME.fullmatch("../shell"))
        self.assertFalse(_TOOL_NAME.fullmatch("Tool Name"))

    def test_pipeline_manifests_validate(self):
        pipelines = list_pipelines()
        self.assertTrue(pipelines, "No pipeline manifests discovered")
        for pipeline in pipelines:
            manifest = load_pipeline(pipeline)
            self.assertTrue(manifest.get("stages"), pipeline)


if __name__ == "__main__":
    unittest.main()
