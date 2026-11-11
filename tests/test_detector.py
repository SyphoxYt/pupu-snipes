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

    def test_component_button_extraction_and_priority(self):
        # Simulates Shay's Glitch Hunt Bot:
        # Message content has Discord jump links & user mentions
        # Components contain [Join Server ↗] pointing to tracking share-link
        content = "Message Jump to Message https://discord.com/channels/123/456/789\nMessage @Shayge"
        embed = {
            "title": "BIOME STARTED - CYBERSPACE Found",
            "description": "Jump to Message: https://discord.com/channels/123/456/789",
            "fields": [
                {"name": "Status", "value": "Valid"},
                {"name": "Place ID", "value": "15532962292"},
                {"name": "Owner Profile", "value": "[Click Here](https://www.roblox.com/users/9999999/profile)"}
            ]
        }
        tracking_url = (
            "https://www.roblox.com/share-links?code=1c0a5b1fedcd9843a7b858192b09806c"
            "&type=Server&deep_link_value=roblox%3A%2F%2Fnavigation%2Fshare_links%3Fcode%3D"
            "1c0a5b1fedcd9843a7b858192b09806c%26type%3DServer&pid=Server&is_retargeting=false"
        )
        components = [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 5,
                        "label": "Join Server",
                        "url": tracking_url
                    }
                ]
            }
        ]

        link, combined_text = self.detector.extract_from_message(
            content=content,
            embeds=[embed],
            components=components
        )
        self.assertIsNotNone(link)
        self.assertTrue(link.is_valid)
        self.assertEqual(link.link_code, "1c0a5b1fedcd9843a7b858192b09806c")
        self.assertIn("1c0a5b1fedcd9843a7b858192b09806c", link.protocol_url)
        self.assertIn("CYBERSPACE", combined_text)
        self.assertEqual(link.place_id, "15532962292")

    def test_tracking_share_link_decoding(self):
        tracking_url = (
            "https://www.roblox.com/share-links?code=1c0a5b1fedcd9843a7b858192b09806c"
            "&type=Server&deep_link_value=roblox%3A%2F%2Fnavigation%2Fshare_links%3Fcode%3D"
            "1c0a5b1fedcd9843a7b858192b09806c%26type%3DServer&pid=Server&is_retargeting=false"
        )
        link = self.detector.extract_from_text(tracking_url)
        self.assertIsNotNone(link)
        self.assertTrue(link.is_valid)
        self.assertEqual(link.link_code, "1c0a5b1fedcd9843a7b858192b09806c")
        self.assertEqual(
            link.protocol_url,
            "roblox://navigation/share_links?code=1c0a5b1fedcd9843a7b858192b09806c&type=Server"
        )

    def test_embed_field_markdown_link(self):
        embed = {
            "title": "Merchant Arrived - MARI Found",
            "fields": [
                {
                    "name": "Server",
                    "value": "[Join Private Server](https://www.roblox.com/share-links?code=abcdef0123456789abcdef0123456789&type=Server)"
                }
            ]
        }
        link, combined_text = self.detector.extract_from_message("", [embed])
        self.assertIsNotNone(link)
        self.assertTrue(link.is_valid)
        self.assertEqual(link.link_code, "abcdef0123456789abcdef0123456789")
        self.assertIn("MARI", combined_text)

    def test_pure_raw_standard_link_message(self):
        # Plain Discord message with no embeds and no buttons
        content = "https://www.roblox.com/games/15532314909/Sols-RNG?privateServerLinkCode=rawlinkcode987654"
        link, combined_text = self.detector.extract_from_message(content=content)
        self.assertIsNotNone(link)
        self.assertTrue(link.is_valid)
        self.assertEqual(link.link_code, "rawlinkcode987654")
        self.assertEqual(link.place_id, "15532314909")
        self.assertEqual(link.protocol_url, "roblox://placeId=15532314909&linkCode=rawlinkcode987654")

    def test_pure_raw_share_link_message(self):
        # Plain share link message with no embeds
        content = "https://www.roblox.com/share-links?code=1c0a5b1fedcd9843a7b858192b09806c&type=Server"
        link, combined_text = self.detector.extract_from_message(content=content)
        self.assertIsNotNone(link)
        self.assertTrue(link.is_valid)
        self.assertEqual(link.link_code, "1c0a5b1fedcd9843a7b858192b09806c")
        self.assertEqual(link.protocol_url, "roblox://navigation/share_links?code=1c0a5b1fedcd9843a7b858192b09806c&type=Server")

    def test_pure_raw_protocol_link_message(self):
        # Pure roblox:// protocol link in chat
        content = "roblox://placeId=15532314909&linkCode=protocode555"
        link, combined_text = self.detector.extract_from_message(content=content)
        self.assertIsNotNone(link)
        self.assertTrue(link.is_valid)
        self.assertEqual(link.link_code, "protocode555")
        self.assertEqual(link.protocol_url, "roblox://placeId=15532314909&linkCode=protocode555")

    def test_raw_link_with_chat_text(self):
        # Raw link mixed with user chat message
        content = "join up fast glitched biome spawned https://www.roblox.com/share?code=glitched112233&type=Server don't miss it"
        link, combined_text = self.detector.extract_from_message(content=content)
        self.assertIsNotNone(link)
        self.assertTrue(link.is_valid)
        self.assertEqual(link.link_code, "glitched112233")
        self.assertIn("glitched", combined_text.lower())

    def test_raw_custom_service_links(self):
        # Custom links like RoPro or JoinRBX sent as raw text
        content = "join via ropro: https://ro.pro/join/roprocustomcode123"
        link, _ = self.detector.extract_from_message(content=content)
        self.assertIsNotNone(link)
        self.assertTrue(link.is_valid)
        self.assertEqual(link.link_code, "roprocustomcode123")

    def test_join_gateway_link(self):
        # xe33Hunt GitHub Pages join link (UUID is used as gameInstanceId)
        sample = "https://xe33cc.github.io/join/?s=9de406b3-cb36-4c4b-ae90-a1f2678dda26"
        link = self.detector.extract_from_text(sample)
        self.assertIsNotNone(link)
        self.assertTrue(link.is_valid)
        self.assertFalse(link.is_phishing)
        self.assertEqual(link.link_type, "joingate")
        self.assertEqual(link.link_code, "9de406b3-cb36-4c4b-ae90-a1f2678dda26")
        self.assertEqual(link.place_id, "15532962292")
        self.assertEqual(
            link.protocol_url,
            "roblox://experiences/start?placeId=15532962292"
            "&gameInstanceId=9de406b3-cb36-4c4b-ae90-a1f2678dda26"
        )

        # Alternate query key (?id=) and extra tracking params before/after
        alt = (
            "https://xe33cc.github.io/join/?utm=discord&id=0a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d"
            "&ref=bot"
        )
        link_alt = self.detector.extract_from_text(alt)
        self.assertIsNotNone(link_alt)
        self.assertTrue(link_alt.is_valid)
        self.assertEqual(link_alt.link_code, "0a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d")

        # Path form: /join/<UUID>
        path_form = "https://xe33cc.github.io/join/11111111-2222-3333-4444-555555555555"
        link_path = self.detector.extract_from_text(path_form)
        self.assertIsNotNone(link_path)
        self.assertTrue(link_path.is_valid)
        self.assertEqual(link_path.link_code, "11111111-2222-3333-4444-555555555555")

        # Invalid UUID must not be treated as a join link
        self.assertIsNone(self.detector.extract_from_text("https://xe33cc.github.io/join/?s=not-a-uuid"))

        # Feature toggle disables detection
        self.detector.snipe_joingate = False
        self.assertIsNone(self.detector.extract_from_text(sample))
        self.detector.snipe_joingate = True

    def test_join_gateway_link_in_discord_message(self):
        content = (
            "Glitched biome found! Join fast: "
            "https://xe33cc.github.io/join/?s=9de406b3-cb36-4c4b-ae90-a1f2678dda26"
        )
        link, combined_text = self.detector.extract_from_message(content=content)
        self.assertIsNotNone(link)
        self.assertTrue(link.is_valid)
        self.assertEqual(link.link_type, "joingate")
        self.assertEqual(link.link_code, "9de406b3-cb36-4c4b-ae90-a1f2678dda26")
        self.assertIn("Glitched", combined_text)


if __name__ == "__main__":
    unittest.main()
