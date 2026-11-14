"""
Unit tests for Roblox Launcher with Voidstrap / Bloxstrap detection.
"""
import unittest
import os
from unittest.mock import patch

from pupusnipe.core import launcher as launcher_module
from pupusnipe.core.launcher import RobloxLauncher


class TestRobloxLauncher(unittest.TestCase):
    def setUp(self):
        self.launcher = RobloxLauncher(cooldown_seconds=60)

    def test_duplicate_suppression(self):
        link = "link_code_test_12345"
        self.assertFalse(self.launcher.is_duplicate(link))
        self.launcher.record_join(link)
        self.assertTrue(self.launcher.is_duplicate(link))

    def test_ignore_cooldown_benchmark(self):
        link = "link_code_benchmark_123"
        self.launcher.record_join(link)
        self.assertTrue(self.launcher.is_duplicate(link))

        # Launching with ignore_cooldown=True must bypass the duplicate block
        res = self.launcher.launch(
            protocol_url="roblox://test",
            link_code=link,
            ignore_cooldown=True
        )
        self.assertNotEqual(res.error_message, f"Duplicate link ignored (Cooldown active for {link[:8]}...)")

    def test_web_gateway_launch_opens_default_browser(self):
        url = "https://xe33hunt.com/j/AaVtbe-dyiZRtlBWAFH4R5tzWaD6PXLG0Cwp7fNWwpgDd0EmQGoyl9mclSydP0502_neuQ"
        with patch.object(self.launcher, "is_roblox_running", return_value=False), \
                patch.object(launcher_module.webbrowser, "open", return_value=True) as browser_open:
            result = self.launcher.launch(
                protocol_url=url,
                link_code="AaVtbe-test-token",
                ignore_cooldown=True,
            )

        self.assertTrue(result.success)
        self.assertEqual(result.protocol_url, url)
        browser_open.assert_called_once()
        self.assertEqual(browser_open.call_args.args[0], url)

    def test_web_gateway_launch_reports_browser_failure(self):
        url = "https://xe33hunt.com/j/AaVtbe-test-token"
        with patch.object(self.launcher, "is_roblox_running", return_value=False), \
                patch.object(self.launcher, "_open_web_join_gateway", return_value=False):
            result = self.launcher.launch(
                protocol_url=url,
                link_code="AaVtbe-test-token-2",
                ignore_cooldown=True,
            )

        self.assertFalse(result.success)
        self.assertIn("protected join page", result.error_message)

    def test_roblox_discovery(self):
        exe = self.launcher.find_roblox_executable(force_vanilla=True)
        if exe:
            self.assertTrue(exe.lower().endswith("robloxplayerbeta.exe"))

    def test_global_10m_cooldown_and_reset(self):
        import time
        self.assertFalse(self.launcher.is_on_global_cooldown())
        self.assertEqual(self.launcher.get_cooldown_remaining(), 0.0)

        # Simulate a server join
        self.launcher.last_join_time = time.time()
        self.assertTrue(self.launcher.is_on_global_cooldown())
        self.assertGreater(self.launcher.get_cooldown_remaining(), 550.0)

        # Reset cooldown manually
        self.launcher.reset_global_cooldown()
        self.assertFalse(self.launcher.is_on_global_cooldown())
        self.assertEqual(self.launcher.get_cooldown_remaining(), 0.0)


if __name__ == "__main__":
    unittest.main()
