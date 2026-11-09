"""
Unit tests for LinkDetector and Anti-Phishing logic.
"""
import unittest
from pupusnipe.core.detector import LinkDetector, ExtractedLink
from pupusnipe.core.config import DEFAULT_SOLS_RNG_PLACE_ID


class TestLinkDetector(unittest.TestCase):
    def setUp(self):
        self.detector = LinkDetector()

    def test_standard_private_server_link(self):
        sample = "Found server! https://www.roblox.com/games/15532314909/Sols-RNG?privateServerLinkCode=987654321abcdef join fast!"
        link = self.detector.extract_from_text(sample)
        self.assertIsNotNone(link)
        self.assertTrue(link.is_valid)
        self.assertEqual(link.place_id, "15532314909")
        self.assertEqual(link.link_code, "987654321abcdef")
        self.assertEqual(link.protocol_url, "roblox://placeId=15532314909&linkCode=987654321abcdef")

    def test_web_roblox_format(self):
        sample = "Here: https://web.roblox.com/games/15532314909/test?privateServerLinkCode=abc_123-XYZ"
        link = self.detector.extract_from_text(sample)
        self.assertIsNotNone(link)
        self.assertTrue(link.is_valid)
        self.assertEqual(link.link_code, "abc_123-XYZ")

    def test_share_link_format(self):
        sample = "https://www.roblox.com/share?code=5544332211&type=Server"
        link = self.detector.extract_from_text(sample)
        self.assertIsNotNone(link)
        self.assertTrue(link.is_valid)
        self.assertEqual(link.link_code, "5544332211")
        self.assertEqual(link.place_id, DEFAULT_SOLS_RNG_PLACE_ID)
        self.assertEqual(link.protocol_url, "roblox://navigation/share_links?code=5544332211&type=Server")

    def test_share_code_standalone(self):
        # 32-hex share code
        code = "c4dd5666e863e546af98323b73170685"
        link = self.detector.extract_from_text(code)
        self.assertIsNotNone(link)
        self.assertTrue(link.is_valid)
        self.assertEqual(link.link_code, code)
        self.assertEqual(link.protocol_url, f"roblox://navigation/share_links?code={code}&type=Server")

    def test_native_protocol_link(self):
        sample = "roblox://placeId=15532314909&linkCode=testcode999"
        link = self.detector.extract_from_text(sample)
        self.assertIsNotNone(link)
        self.assertTrue(link.is_valid)
        self.assertEqual(link.link_code, "testcode999")

        # Test sub-instance place ID (15532962292)
        sub_sample = "roblox://placeId=15532962292&linkCode=48412578674238545032846748351919"
        link_sub = self.detector.extract_from_text(sub_sample)
        self.assertIsNotNone(link_sub)
        self.assertTrue(link_sub.is_valid)
        self.assertEqual(link_sub.place_id, "15532962292")

        # Test reversed parameters (linkCode before placeId)
        alt_sample = "roblox://linkCode=48412578674238545032846748351919&placeId=15532962292"
        link_alt = self.detector.extract_from_text(alt_sample)
        self.assertIsNotNone(link_alt)
        self.assertTrue(link_alt.is_valid)
        self.assertEqual(link_alt.place_id, "15532962292")

    def test_native_share_protocol_with_type_server(self):
        sample = "roblox://navigation/share_links?code=73bdae862028394f9351c5487f4ada5b&type=Server"
        link = self.detector.extract_from_text(sample)
        self.assertIsNotNone(link)
        self.assertTrue(link.is_valid)
        self.assertEqual(link.link_code, "73bdae862028394f9351c5487f4ada5b")
        self.assertEqual(link.protocol_url, "roblox://navigation/share_links?code=73bdae862028394f9351c5487f4ada5b&type=Server")

    def test_phishing_detection(self):
        phish_1 = "Free vip: https://roblox.com.py/games/15532314909?privateServerLinkCode=123"
        link = self.detector.extract_from_text(phish_1)
        self.assertTrue(link.is_phishing or not link.is_valid)

        phish_2 = "Click here: https://robl0x-login.com/games/15532314909"
        link2 = self.detector.extract_from_text(phish_2)
        self.assertTrue(link2.is_phishing or not link2.is_valid)

    def test_custom_links_extraction(self):
        # RoPro
        ropro = "Check ro.pro/join/abcde123"
        l1 = self.detector.extract_from_text(ropro)
        self.assertIsNotNone(l1)
        self.assertTrue(l1.is_valid)
        self.assertEqual(l1.link_code, "abcde123")
        self.assertEqual(l1.link_type, "ropro")

        # JoinRBX
        joinrbx = "Join here: https://join-rbx.vexsys.site/private?placeid=15532314909&link_code=customlink99"
        l2 = self.detector.extract_from_text(joinrbx)
        self.assertIsNotNone(l2)
        self.assertTrue(l2.is_valid)
        self.assertEqual(l2.link_code, "customlink99")
        self.assertEqual(l2.link_type, "joinrbx")

        # RoSeal
        roseal = "RoSeal link: https://roseal.live/join?placeId=15532314909&gameInstanceId=inst-1122"
        l3 = self.detector.extract_from_text(roseal)
        self.assertIsNotNone(l3)
        self.assertTrue(l3.is_valid)
        self.assertEqual(l3.link_code, "inst-1122")
        self.assertEqual(l3.link_type, "roseal")

        # FishStrap
        fishstrap = "Fishstrap link: https://fishstrap.app/v1/joingame?placeId=15532314909&gameInstanceId=fish-4455"
        l4 = self.detector.extract_from_text(fishstrap)
        self.assertIsNotNone(l4)
        self.assertTrue(l4.is_valid)
        self.assertEqual(l4.link_code, "fish-4455")
        self.assertEqual(l4.link_type, "fishstrap")

    def test_embed_extraction(self):
        embed = {
            "title": "Glitched Biome Spawned!",
            "description": "Join now: https://www.roblox.com/games/15532314909/Sols-RNG?privateServerLinkCode=embedcode123",
            "fields": [{"name": "Biome", "value": "Glitched"}]
        }
        link, combined_text = self.detector.extract_from_message("", [embed])
        self.assertIsNotNone(link)
        self.assertTrue(link.is_valid)
        self.assertEqual(link.link_code, "embedcode123")
        self.assertIn("Glitched", combined_text)


if __name__ == "__main__":
    unittest.main()
