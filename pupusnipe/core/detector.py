"""
Roblox Link Detector & Anti-Phishing Validator
High-speed extraction and validation for Sol's RNG Private Server links.
Supports standard Roblox links, share codes, deep-links, and custom links (RoPro, JoinRBX, RoSeal, FishStrap).
"""
import re
import urllib.parse
from typing import Optional, Tuple, Dict, Any, List
from .config import (
    DEFAULT_SOLS_RNG_PLACE_ID,
    JOIN_GATEWAY_PLACE_ID,
    SUPPORTED_PLACE_IDS,
    LEGITIMATE_ROBLOX_DOMAINS
)

# Link types that resolve to an actual Roblox game/server join
GAME_LINK_TYPES = (
    "share", "protocol", "standard", "deeplink",
    "ropro", "joinrbx", "roseal", "fishstrap", "joingate"
)

# UUID (8-4-4-4-12 hex) used as gameInstanceId by join-gateway pages
RE_UUID = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'

# Precompiled regular expressions for maximum extraction speed
RE_STANDARD_LINK = re.compile(
    r'https?://(?:[a-zA-Z0-9_\-]+\.)*roblox\.com/games/(\d+)(?:/[^?\s#<>\)]*)?\?[^#\s<>\)]*?(?:privateServerLinkCode|linkCode)=([a-zA-Z0-9_\-]+)',
    re.IGNORECASE
)

# Share links: roblox.com/share?code=XYZ or roblox.com/share-links?code=XYZ or roblox.com/share-link?code=XYZ
RE_SHARE_LINK = re.compile(
    r'https?://(?:[a-zA-Z0-9_\-]+\.)*roblox\.com/(?:share|share-links?|experiences/share)[^#\s<>\)]*?[?&]code=([a-zA-Z0-9_\-]+)',
    re.IGNORECASE
)

# Native share protocol links: roblox://navigation/share_links?code=XYZ
RE_SHARE_PROTOCOL = re.compile(
    r'roblox://(?:navigation/share_links|experiences/share|\?)?[^#\s<>\)]*?[?&]code=([a-zA-Z0-9_\-]+)',
    re.IGNORECASE
)

# Deep-links: roblox.com/games/start?placeId=...&launchData=...
RE_DEEPLINK = re.compile(
    r'roblox\.com/games/start\?placeId=(\d+)[^#\s<>\)]*?launchData=(\d+)/([a-zA-Z0-9_\-]+)',
    re.IGNORECASE
)

# Native protocol links: roblox://placeId=15532314909&linkCode=XYZ
RE_PROTOCOL_LINK = re.compile(
    r'roblox://(?:experiences/start\?|navigation/game_details\?|\?)?[^#\s<>\)]*?placeId=(\d+)&(?:amp;)?linkCode=([a-zA-Z0-9_\-]+)',
    re.IGNORECASE
)
RE_PROTOCOL_LINK_ALT = re.compile(
    r'roblox://(?:experiences/start\?|navigation/game_details\?|\?)?[^#\s<>\)]*?linkCode=([a-zA-Z0-9_\-]+)&(?:amp;)?placeId=(\d+)',
    re.IGNORECASE
)

# Custom Links (Sol Sniper V3 compatibility)
RE_ROPRO = re.compile(
    r'(?:https?://)?(?:ro\.pro|ropro\.io)/(?:join/)?([a-zA-Z0-9_\-]+)',
    re.IGNORECASE
)

RE_JOIN_RBX_PRIVATE = re.compile(
    r'(?:https?://)?join-rbx\.vexsys\.site/private\?(?:placeid=(\d+)&)?(?:link_code|share_code)=([a-zA-Z0-9_\-]+)',
    re.IGNORECASE
)

RE_JOIN_RBX_PUBLIC = re.compile(
    r'(?:https?://)?join-rbx\.vexsys\.site/public\?placeid=(\d+)&gameinstanceid=([a-zA-Z0-9_\-]+)',
    re.IGNORECASE
)

RE_ROSEAL = re.compile(
    r'(?:https?://)?roseal\.live/join\?placeId=(\d+)&gameInstanceId=([a-zA-Z0-9_\-]+)',
    re.IGNORECASE
)

RE_FISHSTRAP = re.compile(
    r'(?:https?://)?fishstrap\.app/v1/joingame\?placeId=(\d+)&gameInstanceId=([a-zA-Z0-9_\-]+)',
    re.IGNORECASE
)

# Join-gateway pages (e.g. https://xe33cc.github.io/join/?s=<UUID>)
# These static pages resolve client-side to:
#   roblox://experiences/start?placeId=15532962292&gameInstanceId=<UUID>
# Query form: /join/?s=<UUID> or /join/?id=<UUID> (extra params allowed)
RE_JOIN_GATEWAY_QUERY = re.compile(
    r'https?://[a-zA-Z0-9_\-\.]+(?::\d+)?/join/?\?(?:[^#\s<>\)"\']*?&)?(?:s|id)=(' + RE_UUID + r')',
    re.IGNORECASE
)

# Path form: /join/<UUID>
RE_JOIN_GATEWAY_PATH = re.compile(
    r'https?://[a-zA-Z0-9_\-\.]+(?::\d+)?/join/(' + RE_UUID + r')(?![0-9a-zA-Z\-])',
    re.IGNORECASE
)

# Suspicious / phishing domain indicators
SUSPICIOUS_PATTERNS = [
    re.compile(r'robl[o0]x[^\.]*\.[a-z]+', re.IGNORECASE),
    re.compile(r'roblox\.[a-z]+\.[a-z]+', re.IGNORECASE),
    re.compile(r'roblox-(?:link|login|verify|gift|vip|auth)', re.IGNORECASE),
    re.compile(r'grabify|iplogger|bit\.ly|tinyurl|discord\.gift', re.IGNORECASE)
]


class ExtractedLink:
    __slots__ = ('raw_url', 'place_id', 'link_code', 'protocol_url', 'is_valid', 'is_phishing', 'error_reason', 'link_type')

    def __init__(
        self,
        raw_url: str,
        place_id: str,
        link_code: str,
        protocol_url: str,
        is_valid: bool = True,
        is_phishing: bool = False,
        error_reason: str = "",
        link_type: str = "standard"
    ):
        self.raw_url = raw_url
        self.place_id = place_id
        self.link_code = link_code
        self.protocol_url = protocol_url
        self.is_valid = is_valid
        self.is_phishing = is_phishing
        self.error_reason = error_reason
        self.link_type = link_type

    def __repr__(self):
        return f"<ExtractedLink valid={self.is_valid} place_id={self.place_id} code={self.link_code[:8]}... type={self.link_type}>"


class LinkDetector:
    """Ultra-fast regex-based extractor & validator for Sol's RNG private server links."""

    def __init__(
        self,
        target_place_id: str = DEFAULT_SOLS_RNG_PLACE_ID,
        strict_place_id: bool = False,
        snipe_ropro: bool = True,
        snipe_joinrbx: bool = True,
        snipe_roseal: bool = True,
        snipe_fishstrap: bool = True,
        snipe_joingate: bool = True
    ):
        self.target_place_id = str(target_place_id)
        self.strict_place_id = strict_place_id
        self.snipe_ropro = snipe_ropro
        self.snipe_joinrbx = snipe_joinrbx
        self.snipe_roseal = snipe_roseal
        self.snipe_fishstrap = snipe_fishstrap
        self.snipe_joingate = snipe_joingate

    def is_phishing_url(self, text: str) -> bool:
        """Check for known phishing patterns and malicious typosquatting."""
        # Allow legit custom domains
        allowed_custom = ["ro.pro", "ropro.io", "join-rbx.vexsys.site", "roseal.live", "fishstrap.app"]
        for domain in allowed_custom:
            if domain in text.lower():
                return False

        for pattern in SUSPICIOUS_PATTERNS:
            match = pattern.search(text)
            if match:
                matched_str = match.group(0).lower()
                if not any(matched_str.endswith(legit) for legit in LEGITIMATE_ROBLOX_DOMAINS):
                    return True
        return False

    def extract_from_message(
        self,
        content: str = "",
        embeds: List[Any] = None,
        components: List[Any] = None,
        attachments: List[Any] = None,
        raw_message: Any = None
    ) -> Tuple[Optional[ExtractedLink], str]:
        """
        Extracts link and builds combined search text from message content, all embeds,
        interactive Button components, and attachments.
        Prioritizes Discord 'Join Server' button links and Sol's RNG private server links.
        Zero external network requests for sub-millisecond execution.
        """
        parts = []
        if content:
            parts.append(str(content))

        # Prioritized candidate URLs: tuples of (candidate_string, priority_weight, label)
        # Priority 1: Component button links (especially 'Join Server', 'Join', 'Play')
        # Priority 2: Markdown links with join/server labels
        # Priority 3: Embed fields (values and names)
        # Priority 4: Embed titles, descriptions, URLs
        # Priority 5: Raw message content and attachments
        candidates: List[Tuple[str, int, str]] = []

        # 1. Extract from Discord Components (Interactive Buttons / ActionRows)
        if components:
            for row in components:
                children = getattr(row, "children", None) or getattr(row, "components", None)
                if children is None and isinstance(row, dict):
                    children = row.get("components") or row.get("children") or []

                if children:
                    for comp in children:
                        btn_url = getattr(comp, "url", None)
                        label = getattr(comp, "label", "") or ""
                        custom_id = getattr(comp, "custom_id", None)
                        if isinstance(comp, dict):
                            btn_url = btn_url or comp.get("url")
                            label = label or comp.get("label", "")
                            custom_id = custom_id or comp.get("custom_id")
                        elif hasattr(comp, "to_dict"):
                            try:
                                cd = comp.to_dict()
                                btn_url = btn_url or cd.get("url")
                                label = label or cd.get("label", "")
                                custom_id = custom_id or cd.get("custom_id")
                            except Exception:
                                pass

                        if label:
                            parts.append(str(label))
                        
                        # Boost buttons labeled 'Join Server', 'Join', 'Play', 'VIP'
                        lbl_lower = str(label).lower()
                        prio = 1 if any(k in lbl_lower for k in ("join", "server", "vip", "play", "link")) else 2

                        if btn_url:
                            candidates.append((str(btn_url), prio, str(label)))
                        if custom_id and len(str(custom_id)) >= 20 and not str(custom_id).startswith("http"):
                            candidates.append((str(custom_id), prio, str(label)))

        # 2. Extract from Embeds (Titles, descriptions, author, footer, and fields)
        if embeds:
            for emb in embeds:
                if hasattr(emb, "to_dict"):
                    emb_dict = emb.to_dict()
                elif isinstance(emb, dict):
                    emb_dict = emb
                else:
                    emb_dict = {}

                title = emb_dict.get("title", "")
                desc = emb_dict.get("description", "")
                e_url = emb_dict.get("url", "")
                author = emb_dict.get("author", {})
                footer = emb_dict.get("footer", {})
                fields = emb_dict.get("fields", [])

                if title:
                    parts.append(title)
                    candidates.append((title, 4, "title"))
                if desc:
                    parts.append(desc)
                    candidates.append((desc, 3, "description"))
                if e_url:
                    candidates.append((e_url, 3, "embed_url"))
                if isinstance(author, dict):
                    if author.get("name"):
                        parts.append(author["name"])
                    if author.get("url"):
                        candidates.append((author["url"], 4, "author_url"))
                if isinstance(footer, dict) and footer.get("text"):
                    parts.append(footer["text"])

                for f in fields:
                    fn = f.get("name", "")
                    fv = f.get("value", "")
                    if fn:
                        parts.append(fn)
                        candidates.append((fn, 4, "field_name"))
                    if fv:
                        parts.append(fv)
                        # Check for markdown links in field value: [Label](URL)
                        md_links = re.findall(r'\[([^\]]*)\]\((https?://[^\s)]+|roblox://[^\s)]+)\)', fv)
                        for md_lbl, md_u in md_links:
                            lbl_low = md_lbl.lower()
                            prio = 2 if any(k in lbl_low for k in ("join", "server", "vip", "play", "link")) else 3
                            candidates.append((md_u, prio, md_lbl))
                        candidates.append((fv, 3, "field_value"))

        # 3. Extract from Content
        if content:
            # Markdown links in content
            md_links = re.findall(r'\[([^\]]*)\]\((https?://[^\s)]+|roblox://[^\s)]+)\)', content)
            for md_lbl, md_u in md_links:
                lbl_low = md_lbl.lower()
                prio = 2 if any(k in lbl_low for k in ("join", "server", "vip", "play", "link")) else 3
                candidates.append((md_u, prio, md_lbl))
            candidates.append((content, 4, "content"))

        # 4. Extract from Attachments
        if attachments:
            for att in attachments:
                a_url = getattr(att, "url", None) or (att.get("url") if isinstance(att, dict) else None)
                if a_url:
                    candidates.append((str(a_url), 5, "attachment"))

        combined_text = " ".join(parts)

        # Look for explicit Place ID in the message text (e.g. "Place ID 15532962292")
        detected_place_id = None
        pid_match = re.search(r'Place\s*ID\s*[:=]?\s*(\d{8,12})', combined_text, re.IGNORECASE)
        if pid_match:
            pid_candidate = pid_match.group(1)
            if pid_candidate in SUPPORTED_PLACE_IDS:
                detected_place_id = pid_candidate

        # Sort candidates by priority ascending (1 = highest priority)
        candidates.sort(key=lambda x: x[1])

        extracted = None
        for cand_str, prio, label in candidates:
            if not cand_str:
                continue

            # Check raw URL or text
            found = self.extract_from_text(cand_str)
            if found and found.is_valid and not found.is_phishing:
                # Discard non-game links (e.g. discord.com links, roblox user profile links)
                if found.link_type in GAME_LINK_TYPES:
                    extracted = found
                    break

            # If cand_str has URL-encoded query params (e.g. af_dp=roblox%3A%2F%2F... or deep_link_value=...)
            if "%2f" in cand_str.lower() or "%3a" in cand_str.lower() or "af_dp=" in cand_str or "deep_link_value=" in cand_str:
                try:
                    unquoted = urllib.parse.unquote(cand_str)
                    found_unq = self.extract_from_text(unquoted)
                    if found_unq and found_unq.is_valid and not found_unq.is_phishing:
                        if found_unq.link_type in GAME_LINK_TYPES:
                            extracted = found_unq
                            break
                except Exception:
                    pass

        # Fallback: scan combined_text
        if not extracted and combined_text:
            found_fallback = self.extract_from_text(combined_text)
            if found_fallback and found_fallback.is_valid and not found_fallback.is_phishing:
                extracted = found_fallback

        # If a specific place ID was found in the embed text, attach it
        if extracted and detected_place_id:
            extracted.place_id = detected_place_id
            if extracted.protocol_url.startswith("roblox://placeId="):
                extracted.protocol_url = f"roblox://placeId={detected_place_id}&linkCode={extracted.link_code}"

        return extracted, combined_text

    def extract_from_text(self, text: str) -> Optional[ExtractedLink]:
        """
        Extracts and validates a Roblox private server link from plain text or Markdown.
        Zero external network requests for sub-millisecond execution.
        """
        if not text:
            return None

        # If text contains encoded deep links, check decoded version as well
        if "roblox%3a" in text.lower() or "af_dp=" in text.lower() or "deep_link_value=" in text.lower():
            try:
                decoded_text = urllib.parse.unquote(text)
                if "%2f" in decoded_text.lower():
                    decoded_text = urllib.parse.unquote(decoded_text)
                proto_share_match = RE_SHARE_PROTOCOL.search(decoded_text)
                if proto_share_match:
                    link_code = proto_share_match.group(1)
                    proto_url = f"roblox://navigation/share_links?code={link_code}&type=Server"
                    return ExtractedLink(
                        raw_url=text,
                        place_id=self.target_place_id,
                        link_code=link_code,
                        protocol_url=proto_url,
                        is_valid=True,
                        link_type="share"
                    )
            except Exception:
                pass

        clean_text = text.replace("<", " ").replace(">", " ").replace(")", " ")

        # 1. First test: Protocol format (e.g. roblox://placeId=...&linkCode=... or roblox://navigation/share_links?code=...)
        proto_share_match = RE_SHARE_PROTOCOL.search(clean_text)
        if proto_share_match:
            link_code = proto_share_match.group(1)
            proto_url = f"roblox://navigation/share_links?code={link_code}&type=Server"
            return ExtractedLink(
                raw_url=proto_share_match.group(0),
                place_id=self.target_place_id,
                link_code=link_code,
                protocol_url=proto_url,
                is_valid=True,
                link_type="share"
            )

        proto_match = RE_PROTOCOL_LINK.search(clean_text)
        if not proto_match:
            proto_alt = RE_PROTOCOL_LINK_ALT.search(clean_text)
            if proto_alt:
                link_code, place_id = proto_alt.group(1), proto_alt.group(2)
                if self.strict_place_id and place_id != self.target_place_id and place_id not in SUPPORTED_PLACE_IDS:
                    return ExtractedLink(
                        raw_url=proto_alt.group(0),
                        place_id=place_id,
                        link_code=link_code,
                        protocol_url="",
                        is_valid=False,
                        error_reason=f"Place ID {place_id} does not match target {self.target_place_id}"
                    )
                proto_url = f"roblox://placeId={place_id}&linkCode={link_code}"
                return ExtractedLink(
                    raw_url=proto_alt.group(0),
                    place_id=place_id,
                    link_code=link_code,
                    protocol_url=proto_url,
                    is_valid=True,
                    link_type="protocol"
                )

        if proto_match:
            place_id, link_code = proto_match.group(1), proto_match.group(2)
            if self.strict_place_id and place_id != self.target_place_id and place_id not in SUPPORTED_PLACE_IDS:
                return ExtractedLink(
                    raw_url=proto_match.group(0),
                    place_id=place_id,
                    link_code=link_code,
                    protocol_url="",
                    is_valid=False,
                    error_reason=f"Place ID {place_id} does not match target {self.target_place_id}"
                )
            proto_url = f"roblox://placeId={place_id}&linkCode={link_code}"
            return ExtractedLink(
                raw_url=proto_match.group(0),
                place_id=place_id,
                link_code=link_code,
                protocol_url=proto_url,
                is_valid=True,
                link_type="protocol"
            )

        # 2. Check for phishing patterns
        if self.is_phishing_url(clean_text):
            return ExtractedLink(
                raw_url="",
                place_id="",
                link_code="",
                protocol_url="",
                is_valid=False,
                is_phishing=True,
                error_reason="Suspected phishing or unauthorized redirect link"
            )

        # 3. Standard Roblox web link format
        std_match = RE_STANDARD_LINK.search(clean_text)
        if std_match:
            place_id, link_code = std_match.group(1), std_match.group(2)
            raw_url = std_match.group(0)

            # Fast domain validation
            try:
                parsed = urllib.parse.urlparse(raw_url)
                hostname = parsed.hostname.lower() if parsed.hostname else ""
                if not any(hostname == d or hostname.endswith("." + d) for d in LEGITIMATE_ROBLOX_DOMAINS):
                    return ExtractedLink(
                        raw_url=raw_url,
                        place_id="",
                        link_code="",
                        protocol_url="",
                        is_valid=False,
                        is_phishing=True,
                        error_reason=f"Unauthorized host: {hostname}"
                    )
            except Exception:
                pass

            if self.strict_place_id and place_id != self.target_place_id and place_id not in SUPPORTED_PLACE_IDS:
                return ExtractedLink(
                    raw_url=raw_url,
                    place_id=place_id,
                    link_code=link_code,
                    protocol_url="",
                    is_valid=False,
                    error_reason=f"Place ID {place_id} does not match target {self.target_place_id}"
                )

            proto_url = f"roblox://placeId={place_id}&linkCode={link_code}"
            return ExtractedLink(
                raw_url=raw_url,
                place_id=place_id,
                link_code=link_code,
                protocol_url=proto_url,
                is_valid=True,
                link_type="standard"
            )

        # 4. Share link format (roblox.com/share?code=XYZ or roblox.com/share-links?code=XYZ)
        share_match = RE_SHARE_LINK.search(clean_text)
        if share_match:
            link_code = share_match.group(1)
            raw_url = share_match.group(0)
            proto_url = f"roblox://navigation/share_links?code={link_code}&type=Server"
            return ExtractedLink(
                raw_url=raw_url,
                place_id=self.target_place_id,
                link_code=link_code,
                protocol_url=proto_url,
                is_valid=True,
                link_type="share"
            )

        # 5. Deep link format (roblox.com/games/start?placeId=...&launchData=...)
        deeplink_match = RE_DEEPLINK.search(clean_text)
        if deeplink_match:
            place_id = deeplink_match.group(1)
            link_code = deeplink_match.group(3)
            raw_url = deeplink_match.group(0)
            proto_url = f"roblox://placeId={place_id}&linkCode={link_code}"
            return ExtractedLink(
                raw_url=raw_url,
                place_id=place_id,
                link_code=link_code,
                protocol_url=proto_url,
                is_valid=True,
                link_type="deeplink"
            )

        # 6. Custom Links (RoPro, JoinRBX, RoSeal, FishStrap)
        if self.snipe_ropro:
            ropro_match = RE_ROPRO.search(clean_text)
            if ropro_match:
                link_code = ropro_match.group(1)
                proto_url = f"roblox://placeId={self.target_place_id}&linkCode={link_code}"
                return ExtractedLink(
                    raw_url=ropro_match.group(0),
                    place_id=self.target_place_id,
                    link_code=link_code,
                    protocol_url=proto_url,
                    is_valid=True,
                    link_type="ropro"
                )

        if self.snipe_joinrbx:
            joinrbx_priv = RE_JOIN_RBX_PRIVATE.search(clean_text)
            if joinrbx_priv:
                place_id = joinrbx_priv.group(1) or self.target_place_id
                link_code = joinrbx_priv.group(2)
                proto_url = f"roblox://placeId={place_id}&linkCode={link_code}"
                return ExtractedLink(
                    raw_url=joinrbx_priv.group(0),
                    place_id=place_id,
                    link_code=link_code,
                    protocol_url=proto_url,
                    is_valid=True,
                    link_type="joinrbx"
                )

            joinrbx_pub = RE_JOIN_RBX_PUBLIC.search(clean_text)
            if joinrbx_pub:
                place_id = joinrbx_pub.group(1) or self.target_place_id
                instance_id = joinrbx_pub.group(2)
                proto_url = f"roblox://experiences/start?placeId={place_id}&gameInstanceId={instance_id}"
                return ExtractedLink(
                    raw_url=joinrbx_pub.group(0),
                    place_id=place_id,
                    link_code=instance_id,
                    protocol_url=proto_url,
                    is_valid=True,
                    link_type="joinrbx"
                )

        if self.snipe_roseal:
            roseal_match = RE_ROSEAL.search(clean_text)
            if roseal_match:
                place_id = roseal_match.group(1) or self.target_place_id
                instance_id = roseal_match.group(2)
                proto_url = f"roblox://experiences/start?placeId={place_id}&gameInstanceId={instance_id}"
                return ExtractedLink(
                    raw_url=roseal_match.group(0),
                    place_id=place_id,
                    link_code=instance_id,
                    protocol_url=proto_url,
                    is_valid=True,
                    link_type="roseal"
                )

        if self.snipe_fishstrap:
            fishstrap_match = RE_FISHSTRAP.search(clean_text)
            if fishstrap_match:
                place_id = fishstrap_match.group(1) or self.target_place_id
                instance_id = fishstrap_match.group(2)
                proto_url = f"roblox://experiences/start?placeId={place_id}&gameInstanceId={instance_id}"
                return ExtractedLink(
                    raw_url=fishstrap_match.group(0),
                    place_id=place_id,
                    link_code=instance_id,
                    protocol_url=proto_url,
                    is_valid=True,
                    link_type="fishstrap"
                )

        # 7. Join-gateway pages (e.g. https://xe33cc.github.io/join/?s=<UUID>)
        if self.snipe_joingate:
            gateway_match = RE_JOIN_GATEWAY_QUERY.search(clean_text)
            if not gateway_match:
                gateway_match = RE_JOIN_GATEWAY_PATH.search(clean_text)
            if gateway_match:
                instance_id = gateway_match.group(1)
                proto_url = (
                    f"roblox://experiences/start?"
                    f"placeId={JOIN_GATEWAY_PLACE_ID}&gameInstanceId={instance_id}"
                )
                return ExtractedLink(
                    raw_url=gateway_match.group(0),
                    place_id=JOIN_GATEWAY_PLACE_ID,
                    link_code=instance_id,
                    protocol_url=proto_url,
                    is_valid=True,
                    link_type="joingate"
                )

        # 8. Raw standalone code (e.g. 32-character shareCode or privateServerLinkCode)
        stripped = clean_text.strip()
        if re.match(r'^[a-fA-F0-9]{32}$', stripped):
            proto_url = f"roblox://navigation/share_links?code={stripped}&type=Server"
            return ExtractedLink(
                raw_url=stripped,
                place_id=self.target_place_id,
                link_code=stripped,
                protocol_url=proto_url,
                is_valid=True,
                link_type="share"
            )
        elif re.match(r'^[a-zA-Z0-9_\-]{20,50}$', stripped) and not stripped.startswith("http"):
            proto_url = f"roblox://placeId={self.target_place_id}&linkCode={stripped}"
            return ExtractedLink(
                raw_url=stripped,
                place_id=self.target_place_id,
                link_code=stripped,
                protocol_url=proto_url,
                is_valid=True,
                link_type="standard"
            )

        return None
