"""
Unit tests for Roblox Launcher with Voidstrap / Bloxstrap detection.
"""
import unittest
import os
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
