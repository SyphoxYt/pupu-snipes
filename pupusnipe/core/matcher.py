"""
Keyword Matching and Anti-Bait Profile Engine
Evaluates Discord message content & embeds against configurable profiles with priority, regex, and anti-bait filters.
"""
import re
import time
from typing import List, Dict, Any, Optional, Tuple


class KeywordProfile:
    def __init__(
        self,
        id: str,
        name: str,
        category: str = "Custom",
        keywords: List[str] = None,
        is_regex: bool = False,
        priority: int = 5,
        enabled: bool = True,
        pause_duration: int = 0,
        exclude_keywords: List[str] = None
    ):
        self.id = id
        self.name = name
        self.category = category
        self.keywords = keywords or []
        self.is_regex = is_regex
        self.priority = priority
        self.enabled = enabled
        self.pause_duration = pause_duration  # seconds cooldown after match
        self.exclude_keywords = exclude_keywords or []
        
        self.last_matched_time: float = 0.0
        self._compiled_regexes = []
        if self.is_regex:
            self._compile_regexes()

    def _compile_regexes(self):
        self._compiled_regexes = []
        for kw in self.keywords:
            try:
                self._compiled_regexes.append((kw, re.compile(kw, re.IGNORECASE)))
            except re.error:
                pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "keywords": self.keywords,
            "is_regex": self.is_regex,
            "priority": self.priority,
            "enabled": self.enabled,
            "pause_duration": self.pause_duration,
            "exclude_keywords": self.exclude_keywords
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KeywordProfile":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            category=data.get("category", "Custom"),
            keywords=data.get("keywords", []),
            is_regex=data.get("is_regex", False),
            priority=data.get("priority", 5),
            enabled=data.get("enabled", True),
            pause_duration=data.get("pause_duration", 0),
            exclude_keywords=data.get("exclude_keywords", [])
        )


class MatchResult:
    __slots__ = ("matched", "profile", "matched_keyword", "reason", "is_blacklisted")

    def __init__(
        self,
        matched: bool,
        profile: Optional[KeywordProfile] = None,
        matched_keyword: Optional[str] = None,
        reason: str = "",
        is_blacklisted: bool = False
    ):
        self.matched = matched
        self.profile = profile
        self.matched_keyword = matched_keyword
        self.reason = reason
        self.is_blacklisted = is_blacklisted

    def __repr__(self):
        return f"<MatchResult matched={self.matched} profile={self.profile.name if self.profile else None} kw={self.matched_keyword}>"


class KeywordMatcher:
    """High-throughput keyword and anti-bait profile evaluator."""

    def __init__(self, profiles: List[KeywordProfile] = None):
        self.profiles: List[KeywordProfile] = profiles or []
        self.user_blacklist: set[str] = set()
        self.keyword_blacklist: set[str] = set()
        self._sort_profiles()

    def set_profiles(self, profiles: List[KeywordProfile]):
        self.profiles = profiles
        self._sort_profiles()

    def _sort_profiles(self):
        """Sort profiles by priority descending for immediate fast-path matching."""
        self.profiles.sort(key=lambda p: p.priority, reverse=True)

    def set_blacklists(self, users: List[str], keywords: List[str]):
        self.user_blacklist = {u.strip().lower() for u in users if u.strip()}
        self.keyword_blacklist = {k.strip().lower() for k in keywords if k.strip()}

    def evaluate(self, text: str, author_id: str = "", author_name: str = "") -> MatchResult:
        """
        Evaluates the text against anti-bait filters and enabled keyword profiles.
        Returns MatchResult with matched profile and keyword.
        """
        now = time.time()
        text_lower = text.lower()

        # 1. Author blacklist check
        if author_id and str(author_id).lower() in self.user_blacklist:
            return MatchResult(False, reason=f"Author ID {author_id} is blacklisted", is_blacklisted=True)
        if author_name and author_name.lower() in self.user_blacklist:
            return MatchResult(False, reason=f"Author {author_name} is blacklisted", is_blacklisted=True)

        # 2. Keyword blacklist check (Anti-bait)
        for bad_kw in self.keyword_blacklist:
            if bad_kw in text_lower:
                return MatchResult(False, reason=f"Contains blacklisted word: '{bad_kw}'", is_blacklisted=True)

        # 3. Check profiles in descending priority order
        for profile in self.profiles:
            if not profile.enabled:
                continue

            # Check profile cooldown/pause duration
            if profile.pause_duration > 0 and (now - profile.last_matched_time) < profile.pause_duration:
                continue

            # Check exclude keywords
            if profile.exclude_keywords:
                if any(ex.lower() in text_lower for ex in profile.exclude_keywords if ex.strip()):
                    continue

            # Check matching keywords
            if profile.is_regex:
                for raw_pat, comp_pat in profile._compiled_regexes:
                    if comp_pat.search(text):
                        profile.last_matched_time = now
                        return MatchResult(True, profile=profile, matched_keyword=raw_pat, reason="Regex match")
            else:
                for kw in profile.keywords:
                    if kw.lower() in text_lower:
                        profile.last_matched_time = now
                        return MatchResult(True, profile=profile, matched_keyword=kw, reason="Substring match")

        return MatchResult(False, reason="No matching enabled keyword profile")
