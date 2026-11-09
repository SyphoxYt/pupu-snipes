"""
Unit tests for Roblox & Bloxstrap Log Watcher.
"""
import unittest
import tempfile
import os
import time
from pupusnipe.core.log_watcher import RobloxLogWatcher, RE_RPC


class TestLogWatcher(unittest.TestCase):
    def test_regex_matching(self):
        line = '{"name":"Roblox","state":"Equipped \\"Archangel\\"","details":"Playing Sol\'s RNG","largeImage":{"hoverText":"GLITCHED"}}'
        match = RE_RPC.search(line)
        self.assertIsNotNone(match)
        self.assertIn("Archangel", match.group(1))
        self.assertEqual(match.group(2), "GLITCHED")

    def test_log_reading(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = RobloxLogWatcher()
            log_path = os.path.join(tmpdir, "test.log")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write('prefix\n{"name":"Roblox","state":"Equipped \\"Abyssal Hunter\\"","largeImage":{"hoverText":"CORRUPTION"}}\n')

            watcher._read_log_tail(log_path)
            self.assertEqual(watcher.current_biome, "CORRUPTION")
            self.assertIn("Abyssal Hunter", watcher.current_aura)


if __name__ == "__main__":
    unittest.main()
