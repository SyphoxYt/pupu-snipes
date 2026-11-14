"""
Unit tests for browser discovery used by protected join pages.
"""
import os
import unittest
from unittest.mock import patch

from pupusnipe.core import browsers
from pupusnipe.core.browsers import BROWSER_CHOICES, describe_browser, find_browser_executable


class TestBrowserResolution(unittest.TestCase):
    def test_choices_have_unique_ids(self):
        ids = [choice["id"] for choice in BROWSER_CHOICES]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("default", ids)
        self.assertIn("custom", ids)

    def test_default_returns_none(self):
        self.assertIsNone(find_browser_executable("default"))
        self.assertIsNone(find_browser_executable(""))

    def test_unknown_browser_returns_none(self):
        self.assertIsNone(find_browser_executable("netscape"))

    def test_custom_browser_requires_existing_file(self):
        existing = os.path.abspath(__file__)
        self.assertEqual(find_browser_executable("custom", existing), existing)
        self.assertIsNone(find_browser_executable("custom", existing + ".missing"))
        self.assertIsNone(find_browser_executable("custom", ""))

    def test_builtin_candidate_is_used(self):
        with patch.object(browsers.os.path, "isfile", side_effect=lambda p: p.lower().endswith("brave.exe")):
            path = find_browser_executable("brave")
        self.assertIsNotNone(path)
        self.assertTrue(path.lower().endswith("brave.exe"))

    def test_describe_browser(self):
        self.assertIn("default", describe_browser("default").lower())
        self.assertIn("not found", describe_browser("netscape").lower())


if __name__ == "__main__":
    unittest.main()
