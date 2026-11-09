"""
Unit tests for FishSol Engine integration.
"""
import unittest
from pupusnipe.core.fishsol import FishSolEngine


class TestFishSol(unittest.TestCase):
    def setUp(self):
        self.status_log = []
        self.stats_log = []
        self.engine = FishSolEngine(
            on_status_change=lambda s: self.status_log.append(s),
            on_stats_update=lambda st: self.stats_log.append(st)
        )

    def test_initial_state(self):
        self.assertFalse(self.engine.is_running)
        self.assertFalse(self.engine.is_paused)
        self.assertEqual(self.engine.pathing_mode, "Vip Pathing")
        self.assertEqual(self.engine.resolution, "1080p")
        self.assertFalse(self.engine.auto_fish_on_join)

    def test_toggle_auto_fish_on_join(self):
        self.engine.auto_fish_on_join = True
        self.assertTrue(self.engine.auto_fish_on_join)

    def test_camping_configuration(self):
        self.assertTrue(self.engine.stay_in_target_biome)
        self.assertEqual(self.engine.camping_target_biome, "CORRUPTION")
        self.engine.camping_target_biome = "GLITCHED"
        self.assertEqual(self.engine.camping_target_biome, "GLITCHED")

    def test_stats_emission(self):
        self.engine.fish_caught = 5
        self.engine.cycles_completed = 5
        self.engine._emit_stats()
        self.assertGreater(len(self.stats_log), 0)
        latest = self.stats_log[-1]
        self.assertEqual(latest["fish_caught"], 5)
        self.assertEqual(latest["cycles_completed"], 5)


if __name__ == "__main__":
    unittest.main()
