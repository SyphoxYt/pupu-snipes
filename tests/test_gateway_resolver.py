"""Unit tests for the off-screen protected-link resolver."""
import unittest
from unittest.mock import patch

from pupusnipe.core import gateway_resolver as resolver_module
from pupusnipe.core.gateway_resolver import (
    ResolveResult,
    _extract_protocol_url,
    _find_chromium_browser,
)


class TestGatewayResolverHelpers(unittest.TestCase):
    def test_extract_roblox_url(self):
        self.assertEqual(
            _extract_protocol_url("roblox://experiences/start?placeId=1&gameInstanceId=abc"),
            "roblox://experiences/start?placeId=1&gameInstanceId=abc",
        )

    def test_extract_web_start_url(self):
        self.assertEqual(
            _extract_protocol_url(
                "https://www.roblox.com/games/start?placeId=1&gameInstanceId=abc"
            ),
            "roblox://experiences/start?placeId=1&gameInstanceId=abc",
        )

    def test_extract_from_location_header_with_trailing_punctuation(self):
        self.assertEqual(
            _extract_protocol_url("roblox://experiences/start?placeId=1&gameInstanceId=abc)"),
            "roblox://experiences/start?placeId=1&gameInstanceId=abc",
        )

    def test_extract_empty(self):
        self.assertEqual(_extract_protocol_url(""), "")

    def test_find_browser_custom_existing(self):
        import os

        existing = os.path.abspath(__file__)
        self.assertEqual(_find_chromium_browser("custom", existing), existing)

    def test_find_browser_custom_missing(self):
        self.assertIsNone(_find_chromium_browser("custom", "C:\\missing.exe"))

    def test_find_browser_firefox_unsupported(self):
        self.assertIsNone(_find_chromium_browser("firefox"))

    def test_resolve_result_defaults(self):
        result = ResolveResult("timeout")
        self.assertEqual(result.status, "timeout")
        self.assertEqual(result.roblox_url, "")


class TestGatewayResolverBrowserSelection(unittest.TestCase):
    def test_default_finds_chromium(self):
        with patch.object(resolver_module, "find_browser_executable") as mocked:
            mocked.side_effect = lambda browser_id, *args, **kwargs: (
                "C:\\fake\\brave.exe" if browser_id == "brave" else None
            )
            self.assertEqual(_find_chromium_browser("default"), "C:\\fake\\brave.exe")

    def test_unsupported_browser_returns_none_result(self):
        with patch.object(resolver_module, "_find_chromium_browser", return_value=None):
            result = resolver_module.resolve_gateway_url("https://xe33hunt.com/j/token")
        self.assertEqual(result.status, "unsupported")


if __name__ == "__main__":
    unittest.main()
