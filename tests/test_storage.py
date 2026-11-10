"""
Unit tests for SQLite Storage and Configuration.
"""
import unittest
import os
import tempfile
from pupusnipe.core.storage import StorageManager
from pupusnipe.core.matcher import KeywordProfile


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_pupusnipe.db")
        self.storage = StorageManager(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_settings(self):
        self.storage.set_setting("auto_join", False)
        self.assertFalse(self.storage.get_setting("auto_join"))
        self.storage.set_setting("hotkey_toggle", "F9")
        self.assertEqual(self.storage.get_setting("hotkey_toggle"), "F9")
        
        # Test join methods
        self.storage.set_setting("launch_method", "direct_exe")
        self.assertEqual(self.storage.get_setting("launch_method"), "direct_exe")
        self.storage.set_setting("roblox_client", "vanilla")
        self.assertEqual(self.storage.get_setting("roblox_client"), "vanilla")

        # Test UI scaling and window geometry
        self.storage.set_setting("ui_scale", 1.25)
        self.assertEqual(self.storage.get_setting("ui_scale"), 1.25)
        self.storage.set_setting("window_width", 1400)
        self.assertEqual(self.storage.get_setting("window_width"), 1400)
        self.storage.set_setting("window_maximized", True)
        self.assertTrue(self.storage.get_setting("window_maximized"))

        # Test get_all_settings
        all_s = self.storage.get_all_settings()
        self.assertIn("launch_method", all_s)
        self.assertEqual(all_s["launch_method"], "direct_exe")
        self.assertEqual(all_s["ui_scale"], 1.25)

    def test_channels(self):
        self.storage.add_channel("111", "Server A", "222", "Channel General", True)
        channels = self.storage.get_channels()
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0]["channel_id"], "222")
        self.storage.toggle_channel("222", False)
        self.assertEqual(self.storage.get_channels()[0]["enabled"], 0)
        self.storage.delete_channel("222")
        self.assertEqual(len(self.storage.get_channels()), 0)

    def test_profiles(self):
        p = KeywordProfile(id="test_p", name="Test P", category="Custom", keywords=["kw1", "kw2"], priority=8)
        self.storage.save_profile(p)
        profiles = self.storage.get_profiles()
        found = next((x for x in profiles if x.id == "test_p"), None)
        self.assertIsNotNone(found)
        self.assertEqual(found.keywords, ["kw1", "kw2"])

    def test_history(self):
        self.storage.add_history_entry(
            server_name="TestGuild",
            channel_name="vip-links",
            author_name="User#1234",
            profile_name="Glitched",
            keyword="glitched",
            link_code="code123",
            protocol_url="roblox://...",
            latency_ms=1.42,
            status="JOINED"
        )
        hist = self.storage.get_recent_history(10)
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["link_code"], "code123")
        self.assertEqual(hist[0]["status"], "JOINED")

    def test_set_channel_ids_batch(self):
        cids = ["123456789012345678", "987654321098765432"]
        self.storage.set_channel_ids(cids)
        channels = self.storage.get_channels()
        self.assertEqual(len(channels), 2)
        saved_ids = [ch["channel_id"] for ch in channels]
        self.assertIn("123456789012345678", saved_ids)
        self.assertIn("987654321098765432", saved_ids)

        # Clear back to 0
        self.storage.set_channel_ids([])
        self.assertEqual(len(self.storage.get_channels()), 0)


if __name__ == "__main__":
    unittest.main()
