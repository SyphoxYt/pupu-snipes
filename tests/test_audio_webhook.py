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
    build_engine_status_payload,
    _resolve_biome_info,
    _derive_web_url,
    BIOME_COLORS,
    BIOME_FALLBACK_IMAGES
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
        color, emoji, display, img = _resolve_biome_info("DREAMSPACE", "dreamspace")
        self.assertEqual(color, BIOME_COLORS["DREAMSPACE"][0])
        self.assertEqual(emoji, "🌸")
        self.assertIn("Dreamspace", display)
        self.assertIn("dreamspace.png", img)

        color_g, emoji_g, display_g, img_g = _resolve_biome_info("GLITCHED", "glitched")
        self.assertEqual(color_g, BIOME_COLORS["GLITCHED"][0])
        self.assertEqual(emoji_g, "⚡")
        self.assertIn("glitched.png", img_g)

        color_c, emoji_c, _, img_c = _resolve_biome_info("CYBERSPACE", "cyberspace")
        self.assertEqual(color_c, BIOME_COLORS["CYBERSPACE"][0])
        self.assertEqual(emoji_c, "🌐")
        self.assertIn("cyberspace.png", img_c)

    def test_derive_web_url(self):
        # Share link
        proto_share = "roblox://navigation/share_links?code=testcode123&type=Server"
        web_share = _derive_web_url(proto_share, "testcode123")
        self.assertEqual(web_share, "https://www.roblox.com/share-links?code=testcode123&type=Server")

        # Game Instance
        proto_gi = "roblox://experiences/start?placeId=15532962292&gameInstanceId=9de406b3-cb36-4c4b-ae90-a1f2678dda26"
        web_gi = _derive_web_url(proto_gi, "9de406b3-cb36-4c4b-ae90-a1f2678dda26")
        self.assertEqual(web_gi, "https://xe33cc.github.io/join/?s=9de406b3-cb36-4c4b-ae90-a1f2678dda26")

        # Fallback UUID
        web_uuid = _derive_web_url("", "9de406b3-cb36-4c4b-ae90-a1f2678dda26")
        self.assertEqual(web_uuid, "https://xe33cc.github.io/join/?s=9de406b3-cb36-4c4b-ae90-a1f2678dda26")

    def test_build_snipe_payload(self):
        event = {
            "server_name": "xe33Hunt",
            "channel_name": "#🌸dreamspace",
            "author_name": "Shay's Bot",
            "profile_name": "DREAMSPACE",
            "keyword": "dreamspace",
            "link_code": "9de406b3-cb36-4c4b-ae90-a1f2678dda26",
            "raw_url": "https://xe33cc.github.io/join/?s=9de406b3-cb36-4c4b-ae90-a1f2678dda26",
            "protocol_url": "roblox://experiences/start?placeId=15532962292&gameInstanceId=9de406b3-cb36-4c4b-ae90-a1f2678dda26",
            "latency_ms": 13.5,
            "status": "JOINED",
            "image_url": "https://cdn.discordapp.com/attachments/1234/5678/dreamspace.png"
        }

        # With ping
        payload_ping = build_snipe_payload(event, ping_everyone=True)
        self.assertIn("@everyone", payload_ping["content"])
        self.assertIn("https://xe33cc.github.io/join/?s=9de406b3-cb36-4c4b-ae90-a1f2678dda26", payload_ping["content"])
        self.assertEqual(len(payload_ping["embeds"]), 1)
        embed = payload_ping["embeds"][0]
        self.assertIn("Dreamspace", embed["title"])
        self.assertEqual(embed["color"], BIOME_COLORS["DREAMSPACE"][0])
        self.assertIn("CLICK HERE TO JOIN VIP SERVER NOW", embed["description"])
        self.assertEqual(embed["image"]["url"], "https://cdn.discordapp.com/attachments/1234/5678/dreamspace.png")
        self.assertTrue(any(f["name"] == "🌸 Biome / Event" for f in embed["fields"]))
        self.assertTrue(any("13.50 ms" in f["value"] for f in embed["fields"]))
        self.assertTrue(any("Click Here to Launch Roblox Directly" in f["value"] for f in embed["fields"]))
        self.assertTrue(any("Direct Join Link" in f["name"] for f in embed["fields"]))

        # Without ping
        payload_no_ping = build_snipe_payload(event, ping_everyone=False)
        self.assertNotIn("@everyone", payload_no_ping["content"])

    def test_build_engine_status_payload(self):
        channels = [
            {"channel_id": "1271189513619902515", "server_name": "xe33Hunt", "channel_name": "#🌸dreamspace"},
            {"channel_id": "1337886908251902114", "server_name": "Astrald's Hunters", "channel_name": "#🔥glitched"}
        ]
        cfg = {"client": "voidstrap", "method": "protocol", "place_id": "15532962292"}

        # Started
        start_payload = build_engine_status_payload("STARTED", channels=channels, config_info=cfg)
        self.assertIn("ONLINE", start_payload["content"])
        self.assertEqual(len(start_payload["embeds"]), 1)
        start_embed = start_payload["embeds"][0]
        self.assertEqual(start_embed["color"], 0x00ff88)
        self.assertIn("Engine Started", start_embed["title"])
        self.assertTrue(any("Connected Channels" in f["name"] for f in start_embed["fields"]))

        # Stopped
        stats = {"scanned": 150, "joined": 3, "fastest_ms": 11.2}
        stop_payload = build_engine_status_payload("STOPPED", stats=stats)
        self.assertIn("OFFLINE", stop_payload["content"])
        stop_embed = stop_payload["embeds"][0]
        self.assertEqual(stop_embed["color"], 0xef4444)
        self.assertIn("Engine Stopped", stop_embed["title"])
        self.assertTrue(any("11.20 ms" in f["value"] for f in stop_embed["fields"]))


if __name__ == "__main__":
    unittest.main()
