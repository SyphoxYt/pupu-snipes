"""
Roblox Link Detector & Anti-Phishing Validator
High-speed extraction and validation for Sol's RNG Private Server links.
Supports standard Roblox links, share codes, deep-links, and custom links (RoPro, JoinRBX, RoSeal, FishStrap).
"""
import re
import urllib.parse
from typing import Optional, Tuple, Dict, Any, List
from .config import DEFAULT_SOLS_RNG_PLACE_ID, SUPPORTED_PLACE_IDS, LEGITIMATE_ROBLOX_DOMAINS

# Precompiled regular expressions for maximum extraction speed
RE_STANDARD_LINK = re.compile(
    r'https?://(?:[a-zA-Z0-9_\-]+\.)*roblox\.com/games/(\d+)(?:/[^?\s#<>\)]*)?\?[^#\s<>\)]*?privateServerLinkCode=([a-zA-Z0-9_\-]+)',
    re.IGNORECASE
)

# Share links: roblox.com/share?code=XYZ or roblox.com/share-links?code=XYZ
RE_SHARE_LINK = re.compile(
    r'https?://(?:[a-zA-Z0-9_\-]+\.)*roblox\.com/(?:share|share-links)\?[^#\s<>\)]*?code=([a-zA-Z0-9_\-]+)',
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
        snipe_fishstrap: bool = True
    ):
        self.target_place_id = str(target_place_id)
        self.strict_place_id = strict_place_id
        self.snipe_ropro = snipe_ropro
        self.snipe_joinrbx = snipe_joinrbx
        self.snipe_roseal = snipe_roseal
        self.snipe_fishstrap = snipe_fishstrap

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

    def extract_from_message(self, content: str, embeds: List[Dict[str, Any]]) -> Tuple[Optional[ExtractedLink], str]:
        """
        Extracts link and builds combined search text from message content and all embeds.
        Zero external network requests for sub-millisecond execution.
        """
        parts = [content or ""]
        extracted = None

        if content:
            extracted = self.extract_from_text(content)

        for emb in embeds:
            title = emb.get("title", "")
            desc = emb.get("description", "")
            url = emb.get("url", "")
            footer = emb.get("footer", {}).get("text", "") if isinstance(emb.get("footer"), dict) else ""
            
            if title:
                parts.append(title)
            if desc:
                parts.append(desc)
            if footer:
                parts.append(footer)
            if url:
                parts.append(url)

            for f in emb.get("fields", []):
                fn = f.get("name", "")
                fv = f.get("value", "")
                if fn:
                    parts.append(fn)
                if fv:
                    parts.append(fv)

            if not extracted:
                for text_candidate in (url, desc, title):
                    if text_candidate:
                        found = self.extract_from_text(text_candidate)
                        if found and found.is_valid:
                            extracted = found
                            break

        combined_text = " ".join(parts)
        return extracted, combined_text

    def extract_from_text(self, text: str) -> Optional[ExtractedLink]:
        """
        Extracts and validates a Roblox private server link from plain text or Markdown.
        Zero external network requests for sub-millisecond execution.
        """
        if not text:
            return None

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

        # 7. Raw standalone code (e.g. 32-character shareCode or privateServerLinkCode)
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
