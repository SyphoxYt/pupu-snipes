"""
Unit tests for custom audio sound effects and Discord webhook payload formatting.
"""
import unittest
import os
from pupusnipe.core.audio import (
    get_available_sounds,
    resolve_sound_path,
    BUILTIN_SOUNDS
)
from pupusnipe.core.webhook import (
    build_snipe_payload,
    _resolve_biome_info,
    _derive_web_url,
    BIOME_COLORS
)


class TestAudioAndWebhook(unittest.TestCase):
    def test_available_sounds_registry(self):
        sounds = get_available_sounds()
        self.assertGreater(len(sounds), 5)
        keys = [k for k, _ in sounds]
        self.assertIn("vine_boom", keys)
        self.assertIn("metal_pipe", keys)
        self.assertIn("taco_bell", keys)
        self.assertIn("bruh", keys)
        self.assertIn("roblox_oof", keys)
        self.assertIn("default", keys)
        self.assertIn("custom", keys)

    def test_resolve_sound_path(self):
        # Default should resolve to None (uses winsound)
        self.assertIsNone(resolve_sound_path("default"))

        # Valid sound in assets/sounds should resolve to existing file
        vine_path = resolve_sound_path("vine_boom")
        if vine_path:
            self.assertTrue(os.path.isfile(vine_path))

        # Custom non-existent should be None
        self.assertIsNone(resolve_sound_path("custom", "non_existent_file.mp3"))

    def test_biome_colors_and_emojis(self):
        color, emoji, display = _resolve_biome_info("DREAMSPACE", "dreamspace")
        self.assertEqual(color, BIOME_COLORS["DREAMSPACE"][0])
        self.assertEqual(emoji, "🌸")
        self.assertIn("Dreamspace", display)

        color_g, emoji_g, display_g = _resolve_biome_info("GLITCHED", "glitched")
        self.assertEqual(color_g, BIOME_COLORS["GLITCHED"][0])
        self.assertEqual(emoji_g, "⚡")

        color_c, emoji_c, _ = _resolve_biome_info("CYBERSPACE", "cyberspace")
        self.assertEqual(color_c, BIOME_COLORS["CYBERSPACE"][0])
        self.assertEqual(emoji_c, "🌐")

    def test_derive_web_url(self):
        # Share link
        proto_share = "roblox://navigation/share_links?code=testcode123&type=Server"
        web_share = _derive_web_url(proto_share, "testcode123")
        self.assertEqual(web_share, "https://www.roblox.com/share-links?code=testcode123&type=Server")

        # Game Instance
        proto_gi = "roblox://experiences/start?placeId=15532962292&gameInstanceId=9de406b3-cb36-4c4b-ae90-a1f2678dda26"
        web_gi = _derive_web_url(proto_gi, "9de406b3-cb36-4c4b-ae90-a1f2678dda26")
        self.assertEqual(web_gi, "https://www.roblox.com/games/start?placeId=15532962292&gameInstanceId=9de406b3-cb36-4c4b-ae90-a1f2678dda26")

        # Fallback UUID
        web_uuid = _derive_web_url("", "9de406b3-cb36-4c4b-ae90-a1f2678dda26")
        self.assertIn("15532962292", web_uuid)
        self.assertIn("9de406b3-cb36-4c4b-ae90-a1f2678dda26", web_uuid)

    def test_build_snipe_payload(self):
        event = {
            "server_name": "xe33Hunt",
            "channel_name": "#🌸dreamspace",
            "author_name": "Shay's Bot",
            "profile_name": "DREAMSPACE",
            "keyword": "dreamspace",
            "link_code": "9de406b3-cb36-4c4b-ae90-a1f2678dda26",
            "protocol_url": "roblox://experiences/start?placeId=15532962292&gameInstanceId=9de406b3-cb36-4c4b-ae90-a1f2678dda26",
            "latency_ms": 13.5,
            "status": "JOINED"
        }

        # With ping
        payload_ping = build_snipe_payload(event, ping_everyone=True)
        self.assertIn("@everyone", payload_ping["content"])
        self.assertEqual(len(payload_ping["embeds"]), 1)
        embed = payload_ping["embeds"][0]
        self.assertIn("Dreamspace", embed["title"])
        self.assertEqual(embed["color"], BIOME_COLORS["DREAMSPACE"][0])
        self.assertTrue(any(f["name"] == "🌸 Biome / Event" for f in embed["fields"]))
        self.assertTrue(any("13.50 ms" in f["value"] for f in embed["fields"]))
        self.assertTrue(any("Click Here to Launch Roblox Directly" in f["value"] for f in embed["fields"]))

        # Without ping
        payload_no_ping = build_snipe_payload(event, ping_everyone=False)
        self.assertNotIn("@everyone", payload_no_ping["content"])


if __name__ == "__main__":
    unittest.main()
