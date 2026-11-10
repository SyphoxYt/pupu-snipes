"""
Unit tests for multi-channel parsing and Discord gateway channel filtering.
"""
import unittest
import os
import tempfile
from pupusnipe.core.discord_monitor import DiscordMonitor
from pupusnipe.core.config import AppConfig
from pupusnipe.core.storage import StorageManager
from pupusnipe.core.detector import LinkDetector
from pupusnipe.core.matcher import KeywordMatcher
from pupusnipe.core.launcher import RobloxLauncher
from pupusnipe.ui.tabs.sniper_tab import SniperTab
from PySide6 import QtWidgets


class MockChannel:
    def __init__(self, id: int, parent_id: int = None, guild = None):
        self.id = id
        self.parent_id = parent_id
        self.guild = guild


class MockGuild:
    def __init__(self, id: int, name: str = "Test Server"):
        self.id = id
        self.name = name


class TestChannelFiltering(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_channels.db")
        self.config = AppConfig()
        self.storage = StorageManager(db_path=self.db_path)
        self.detector = LinkDetector()
        self.matcher = KeywordMatcher()
        self.launcher = RobloxLauncher()
        self.monitor = DiscordMonitor(
            config=self.config,
            storage=self.storage,
            detector=self.detector,
            matcher=self.matcher,
            launcher=self.launcher
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_channel_filtering_empty_allows_all(self):
        self.monitor.set_monitored_channels([])
        self.assertTrue(self.monitor._is_channel_monitored(123456789012))

    def test_channel_filtering_direct_match(self):
        self.monitor.set_monitored_channels(["111111111111", "222222222222", "333333333333"])
        self.assertTrue(self.monitor._is_channel_monitored(222222222222))
        self.assertFalse(self.monitor._is_channel_monitored(999999999999))

    def test_channel_filtering_thread_parent(self):
        # Monitored channel is parent forum/text channel: 111111111111
        # Message is posted in sub-thread 555555555555 with parent_id 111111111111
        self.monitor.set_monitored_channels(["111111111111"])
        thread = MockChannel(id=555555555555, parent_id=111111111111)
        self.assertTrue(self.monitor._is_channel_monitored(555555555555, channel_obj=thread))

    def test_channel_filtering_guild_id(self):
        # User entered guild ID: 777777777777
        self.monitor.set_monitored_channels(["777777777777"])
        guild = MockGuild(id=777777777777)
        ch = MockChannel(id=888888888888, guild=guild)
        self.assertTrue(self.monitor._is_channel_monitored(888888888888, channel_obj=ch))

    def test_multi_channel_parser(self):
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        tab = SniperTab(self.storage)

        # 9 channels formatted with URLs, mentions, spaces, commas, and plain IDs
        sample_input = """
https://discord.com/channels/1271189424750989343/1337886908251902114
https://discord.com/channels/1271189424750989343/1444176397286510852
1271189513619902515, 1497517434859683910
<#1546359525471166484>
1290022552105648168
1472430010571816961
1271189425459826702
1111111111111111111
"""
        tab.edit_channels.setPlainText(sample_input)
        parsed = tab.get_channel_ids()
        self.assertEqual(len(parsed), 9)
        self.assertIn("1337886908251902114", parsed)
        self.assertIn("1444176397286510852", parsed)
        self.assertIn("1546359525471166484", parsed)
        self.assertIn("1111111111111111111", parsed)
        # Guild ID must not be extracted as a channel ID
        self.assertNotIn("1271189424750989343", parsed)

    def test_metadata_update_and_preservation(self):
        # Initial set of channels
        self.storage.set_channel_ids(["1396152378495078531", "1445417690201325741"])
        channels = {c["channel_id"]: c for c in self.storage.get_channels()}
        self.assertEqual(channels["1396152378495078531"]["server_name"], "Discord Server")

        # Live metadata resolution
        self.storage.update_channel_metadata(
            channel_id="1396152378495078531",
            server_id="123456789",
            server_name="xe33Hunt",
            channel_name="#🌸dreamspace"
        )
        channels = {c["channel_id"]: c for c in self.storage.get_channels()}
        self.assertEqual(channels["1396152378495078531"]["server_name"], "xe33Hunt")
        self.assertEqual(channels["1396152378495078531"]["channel_name"], "#🌸dreamspace")
        self.assertEqual(channels["1396152378495078531"]["server_id"], "123456789")

        # When set_channel_ids is called again with the same channel, preserved metadata is retained
        self.storage.set_channel_ids(["1396152378495078531", "999999999999999999"])
        channels = {c["channel_id"]: c for c in self.storage.get_channels()}
        self.assertEqual(channels["1396152378495078531"]["server_name"], "xe33Hunt")
        self.assertEqual(channels["1396152378495078531"]["channel_name"], "#🌸dreamspace")
        self.assertEqual(channels["999999999999999999"]["server_name"], "Discord Server")


if __name__ == "__main__":
    unittest.main()
