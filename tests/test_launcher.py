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

    def test_vanilla_strict_isolation(self):
        """Verify client='vanilla' with method='direct_exe' launches vanilla exe and NEVER touches bootstrapper."""
        from unittest.mock import patch, MagicMock

        with patch.object(self.launcher, "find_roblox_executable", return_value="C:\\Fake\\RobloxPlayerBeta.exe") as mock_find_vanilla, \
             patch.object(self.launcher, "find_bootstrapper_executable", return_value="D:\\Void Strap 67\\Voidstrap.exe") as mock_find_boot, \
             patch("subprocess.Popen") as mock_popen:

            res = self.launcher.launch(
                protocol_url="roblox://test_vanilla",
                link_code="vanilla_code_1",
                method="direct_exe",
                client="vanilla",
                ignore_cooldown=True
            )

            self.assertTrue(res.success)
            mock_find_vanilla.assert_called_once_with(force_vanilla=True)
            mock_find_boot.assert_not_called()
            mock_popen.assert_called_once()
            args, _ = mock_popen.call_args
            self.assertEqual(args[0], ["C:\\Fake\\RobloxPlayerBeta.exe", "roblox://test_vanilla"])

    def test_voidstrap_routing(self):
        """Verify client='voidstrap' launches bootstrapper."""
        from unittest.mock import patch

        with patch.object(self.launcher, "find_bootstrapper_executable", return_value="D:\\Void Strap 67\\Voidstrap.exe") as mock_find_boot, \
             patch("subprocess.Popen") as mock_popen:

            res = self.launcher.launch(
                protocol_url="roblox://test_voidstrap",
                link_code="voidstrap_code_1",
                method="direct_exe",
                client="voidstrap",
                ignore_cooldown=True
            )

            self.assertTrue(res.success)
            mock_find_boot.assert_called_once()
            mock_popen.assert_called_once()
            args, _ = mock_popen.call_args
            self.assertEqual(args[0], ["D:\\Void Strap 67\\Voidstrap.exe", "-player", "roblox://test_voidstrap"])


if __name__ == "__main__":
    unittest.main()
