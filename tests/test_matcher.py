"""
Unit tests for KeywordMatcher and anti-bait filters.
"""
import unittest
from pupusnipe.core.matcher import KeywordMatcher, KeywordProfile


class TestKeywordMatcher(unittest.TestCase):
    def setUp(self):
        p1 = KeywordProfile(id="glitched", name="Glitched", category="Biomes", keywords=["glitched"], priority=10, enabled=True)
        p2 = KeywordProfile(id="mari", name="Mari", category="Merchants", keywords=["mari"], priority=5, enabled=True)
        p3 = KeywordProfile(id="jester_regex", name="Jester RegEx", category="Merchants", keywords=[r"jester\s+(spawned|here)"], is_regex=True, priority=9, enabled=True)
        p4 = KeywordProfile(id="disabled_prof", name="Disabled", category="Custom", keywords=["disabled_kw"], priority=20, enabled=False)
        p5 = KeywordProfile(id="ex_profile", name="Exclude Test", category="Custom", keywords=["starfall"], exclude_keywords=["fake"], priority=6, enabled=True)

        self.matcher = KeywordMatcher([p1, p2, p3, p4, p5])
        self.matcher.set_blacklists(users=["123456789", "TrollUser"], keywords=["scam", "troll"])

    def test_simple_keyword_match(self):
        res = self.matcher.evaluate("Hey guys Glitched biome is here!")
        self.assertTrue(res.matched)
        self.assertEqual(res.profile.id, "glitched")

    def test_regex_keyword_match(self):
        res = self.matcher.evaluate("Omg jester spawned quick!")
        self.assertTrue(res.matched)
        self.assertEqual(res.profile.id, "jester_regex")

    def test_disabled_profile_skipped(self):
        res = self.matcher.evaluate("Here is disabled_kw")
        self.assertFalse(res.matched)

    def test_exclude_keyword_prevents_match(self):
        res = self.matcher.evaluate("starfall but fake")
        self.assertFalse(res.matched)

    def test_author_blacklist(self):
        res = self.matcher.evaluate("Glitched biome!", author_id="123456789")
        self.assertFalse(res.matched)
        self.assertTrue(res.is_blacklisted)

        res2 = self.matcher.evaluate("Glitched biome!", author_name="TrollUser")
        self.assertFalse(res2.matched)
        self.assertTrue(res2.is_blacklisted)

    def test_keyword_blacklist(self):
        res = self.matcher.evaluate("Glitched biome scam link!")
        self.assertFalse(res.matched)
        self.assertTrue(res.is_blacklisted)


if __name__ == "__main__":
    unittest.main()
