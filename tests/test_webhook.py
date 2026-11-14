"""
Unit tests for Discord webhook payload construction and delivery bookkeeping.
"""
import unittest
from unittest.mock import patch

from pupusnipe.core import webhook
from pupusnipe.core.webhook import (
    WebhookNotifier,
    build_server_link,
    build_snipe_embed,
    build_snipe_payload,
    build_test_payload,
    is_valid_webhook_url,
)

VALID_URL = "https://discord.com/api/webhooks/123456789012345678/abcdefTOKEN"

EVENT = {
    "timestamp": 1763200000.25,
    "server_name": "xe33Hunt",
    "channel_name": "glitch-hunt",
    "author_name": "LinkBot",
    "profile_name": "Glitched",
    "keyword": "glitched",
    "link_code": "ABC123XYZ",
    "protocol_url": "roblox://navigation/share_links?code=ABC123XYZ&type=Server",
    "latency_ms": 12.345,
    "status": "JOINED",
}


class TestWebhookValidation(unittest.TestCase):
    def test_accepts_discord_webhook_hosts(self):
        self.assertTrue(is_valid_webhook_url(VALID_URL))
        self.assertTrue(is_valid_webhook_url(VALID_URL.replace("discord.com", "canary.discord.com")))
        self.assertTrue(is_valid_webhook_url(VALID_URL.replace("discord.com", "ptb.discord.com")))
        self.assertTrue(is_valid_webhook_url(VALID_URL + "?wait=true"))

    def test_rejects_invalid_or_non_https_urls(self):
        for url in [
            "",
            "http://discord.com/api/webhooks/123/token",
            "https://evil.example/api/webhooks/123/token",
            "https://discord.com/api/webhooks/123",
            "https://discord.com/not-a-webhook/123/token",
        ]:
            self.assertFalse(is_valid_webhook_url(url), url)

    def test_server_share_link(self):
        self.assertEqual(
            build_server_link("ABC123"),
            "https://www.roblox.com/share?code=ABC123&type=Server",
        )
        self.assertEqual(build_server_link("A B/C"), "https://www.roblox.com/share?code=A%20B%2FC&type=Server")
        self.assertEqual(build_server_link(""), "")


class TestWebhookPayload(unittest.TestCase):
    def test_ping_everyone_payload(self):
        payload = build_snipe_payload(EVENT, ping_everyone=True)
        self.assertTrue(payload["content"].startswith("@everyone"))
        self.assertEqual(payload["allowed_mentions"]["parse"], ["everyone"])
        self.assertEqual(payload["username"], "PupuSnipe")
        self.assertEqual(len(payload["embeds"]), 1)

    def test_no_ping_payload(self):
        payload = build_snipe_payload(EVENT, ping_everyone=False)
        self.assertNotIn("@everyone", payload["content"])
        self.assertEqual(payload["allowed_mentions"]["parse"], [])

    def test_embed_contains_biome_link_and_metadata(self):
        embed = build_snipe_embed(EVENT)
        self.assertIn("Glitched", embed["title"])
        self.assertEqual(embed["url"], "https://www.roblox.com/share?code=ABC123XYZ&type=Server")

        fields = {field["name"]: field["value"] for field in embed["fields"]}
        self.assertEqual(fields["🧬 Biome"], "Glitched")
        self.assertEqual(fields["⚡ Latency"], "12.35 ms")
        self.assertEqual(fields["🎮 Source Server"], "xe33Hunt")
        self.assertEqual(fields["📺 Channel"], "#glitch-hunt")
        self.assertEqual(fields["👤 Posted By"], "LinkBot")
        self.assertIn("ABC123XYZ", fields["🧾 Link Code"])
        self.assertIn("roblox.com/share", fields["🔗 Join Link"])
        self.assertIn("roblox.com/share", embed["description"])
        self.assertEqual(embed["timestamp"], "2025-11-15T09:46:40.250000Z")

    def test_web_gateway_uses_protected_page_as_join_link(self):
        url = (
            "https://xe33hunt.com/j/"
            "AaVtbe-dyiZRtlBWAFH4R5tzWaD6PXLG0Cwp7fNWwpgDd0EmQGoyl9mclSydP0502_neuQ"
        )
        event = dict(EVENT, protocol_url=url, link_code="AaVtbe-token")
        embed = build_snipe_embed(event)
        self.assertEqual(embed["url"], url)

        fields = {field["name"]: field["value"] for field in embed["fields"]}
        self.assertIn(url, fields["🔗 Join Link"])
        self.assertIn("protected join page", fields["🔗 Join Link"].lower())
        self.assertIn(url, embed["description"])
        self.assertNotIn("roblox.com/share", embed["description"])

    def test_live_biome_overrides_target_profile(self):
        embed = build_snipe_embed(EVENT, biome="Dreamspace")
        fields = {field["name"]: field["value"] for field in embed["fields"]}
        self.assertIn("Dreamspace", embed["title"])
        self.assertEqual(fields["🧬 Biome"], "Dreamspace")
        self.assertEqual(fields["🎯 Target"], "Glitched")

    def test_generic_profile_shows_pending_biome(self):
        event = dict(EVENT, profile_name="Direct Link", keyword="DIRECT_LINK")
        embed = build_snipe_embed(event)
        fields = {field["name"]: field["value"] for field in embed["fields"]}
        self.assertIn("Detecting live biome", fields["🧬 Biome"])
        self.assertEqual(fields["🎯 Target"], "Direct Link")

    def test_test_payload(self):
        payload = build_test_payload(ping_everyone=True)
        self.assertTrue(payload["content"].startswith("@everyone"))
        self.assertIn("Webhook Connected", payload["embeds"][0]["title"])


class TestWebhookNotifier(unittest.TestCase):
    def test_send_worker_tracks_message_and_payload(self):
        notifier = WebhookNotifier()
        with patch.object(webhook, "_request_json", return_value={"id": "999888777"}) as request:
            notifier._send_snipe_worker(dict(EVENT), VALID_URL, True)

        self.assertEqual(notifier._last_message_id, "999888777")
        self.assertEqual(notifier._last_url, VALID_URL)
        self.assertEqual(notifier._last_biome, "Glitched")
        sent_url, sent_payload = request.call_args.args
        self.assertIn("wait=true", sent_url)
        self.assertEqual(sent_payload["allowed_mentions"]["parse"], ["everyone"])

    def test_patch_biome_payload(self):
        notifier = WebhookNotifier()
        with patch.object(webhook, "_request_json", return_value={}) as request:
            notifier._patch_biome_worker(dict(EVENT), VALID_URL, "999", "Corruption")

        patch_url, patch_payload = request.call_args.args
        self.assertTrue(patch_url.endswith("/messages/999"))
        self.assertEqual(request.call_args.kwargs["method"], "PATCH")
        fields = {field["name"]: field["value"] for field in patch_payload["embeds"][0]["fields"]}
        self.assertEqual(fields["🧬 Biome"], "Corruption")
        self.assertIn("Corruption", patch_payload["embeds"][0]["title"])

    def test_biome_update_requires_recent_message(self):
        notifier = WebhookNotifier()
        self.assertFalse(notifier.update_biome_async("Corruption"))

        notifier._last_url = VALID_URL
        notifier._last_message_id = "1"
        notifier._last_event = dict(EVENT)
        notifier._last_sent_at = 0.0
        self.assertFalse(notifier.update_biome_async("Corruption"))

    def test_biome_update_skips_placeholder_and_duplicate(self):
        notifier = WebhookNotifier()
        notifier._last_url = VALID_URL
        notifier._last_message_id = "1"
        notifier._last_event = dict(EVENT)
        notifier._last_sent_at = 9_999_999_999
        self.assertFalse(notifier.update_biome_async("NORMAL"))
        notifier._last_biome = "Glitched"
        self.assertFalse(notifier.update_biome_async("Glitched"))

    def test_pending_biome_survives_in_flight_send(self):
        notifier = WebhookNotifier()
        notifier._sending = 1
        self.assertFalse(notifier.update_biome_async("Corruption"))
        self.assertEqual(notifier._pending_biome, "Corruption")

    def test_invalid_url_fails_without_network(self):
        notifier = WebhookNotifier()
        results = []
        with patch.object(webhook, "_request_json") as request:
            self.assertFalse(
                notifier.send_snipe_async(
                    dict(EVENT), "https://evil.example/hook", True,
                    lambda ok, message: results.append((ok, message)),
                )
            )
            request.assert_not_called()
        self.assertEqual(results, [(False, "Invalid Discord webhook URL")])


if __name__ == "__main__":
    unittest.main()
