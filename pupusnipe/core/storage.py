"""
SQLite Storage & Windows Credential Manager Backend
Handles configuration, channels, keyword profiles, join history, and secure token storage.
"""
import os
import json
import sqlite3
import time
from typing import List, Dict, Any, Optional
import keyring
from .config import APP_NAME, DEFAULT_PROFILES, DEFAULT_ANTI_BAIT_KEYWORDS, DEFAULT_SOLS_RNG_PLACE_ID
from .matcher import KeywordProfile


KEYRING_SERVICE = "PupuSnipe_DiscordSniper"
KEYRING_USERNAME = "bot_token"


class StorageManager:
    """Persistent storage manager backed by SQLite and Windows Credential Manager."""

    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
            pupu_dir = os.path.join(appdata, "PupuSnipe")
            os.makedirs(pupu_dir, exist_ok=True)
            db_path = os.path.join(pupu_dir, "pupusnipe.db")

        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Settings Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            # Channels Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id TEXT NOT NULL,
                    server_name TEXT,
                    channel_id TEXT NOT NULL UNIQUE,
                    channel_name TEXT,
                    enabled INTEGER DEFAULT 1
                )
            """)

            # Keyword Profiles Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    id TEXT PRIMARY KEY,
                    category TEXT,
                    name TEXT,
                    keywords TEXT,
                    is_regex INTEGER DEFAULT 0,
                    priority INTEGER DEFAULT 5,
                    enabled INTEGER DEFAULT 1,
                    pause_duration INTEGER DEFAULT 0,
                    exclude_keywords TEXT
                )
            """)

            # Blacklists Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blacklists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    value TEXT NOT NULL UNIQUE
                )
            """)

            # Detection & Join History Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    server_name TEXT,
                    channel_name TEXT,
                    author_name TEXT,
                    profile_name TEXT,
                    keyword TEXT,
                    link_code TEXT,
                    protocol_url TEXT,
                    latency_ms REAL,
                    status TEXT,
                    error_reason TEXT
                )
            """)

            conn.commit()
        finally:
            conn.close()

        # Seed default profiles if empty
        self._seed_defaults()

    def _seed_defaults(self):
        existing_ids = {p.id for p in self.get_profiles()}
        for p in DEFAULT_PROFILES:
            if p["id"] not in existing_ids:
                self.save_profile(KeywordProfile(
                    id=p["id"],
                    name=p["name"],
                    category=p["category"],
                    keywords=p["keywords"],
                    is_regex=p["is_regex"],
                    priority=p["priority"],
                    enabled=p["enabled"],
                    pause_duration=p.get("pause_duration", 0)
                ))

        # Seed default anti-bait keywords
        kws = self.get_blacklist("keyword")
        if not kws:
            for bad_kw in DEFAULT_ANTI_BAIT_KEYWORDS:
                self.add_blacklist_item("keyword", bad_kw)

    def close(self):
        pass

    # --- Token Management (Windows Credential Manager + SQLite Fallback) ---
    def save_bot_token(self, token: str):
        tok = token.strip()
        try:
            keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, tok)
        except Exception:
            pass
        # ALWAYS persist to SQLite settings as well so token is never lost if keyring fails
        self.set_setting("bot_token_fallback", tok)

    def get_bot_token(self) -> str:
        try:
            token = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
            if token and token.strip():
                return token.strip()
        except Exception:
            pass
        fb = self.get_setting("bot_token_fallback", "")
        if fb and str(fb).strip():
            return str(fb).strip()
        return ""

    # --- Settings Key-Value ---
    def set_setting(self, key: str, value: Any):
        try:
            val_str = json.dumps(value)
        except Exception:
            val_str = str(value)
        conn = self._get_connection()
        try:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, val_str))
            conn.commit()
        finally:
            conn.close()

    def get_setting(self, key: str, default: Any = None) -> Any:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                val = row["value"]
                try:
                    return json.loads(val)
                except Exception:
                    return val
            return default
        finally:
            conn.close()

    def get_all_settings(self) -> Dict[str, Any]:
        """Loads all stored settings into a dictionary."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            result = {}
            for row in cursor.fetchall():
                k = row["key"]
                v = row["value"]
                try:
                    result[k] = json.loads(v)
                except Exception:
                    result[k] = v
            return result
        finally:
            conn.close()

    # --- Channels ---
    def get_channels(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM channels ORDER BY id ASC")
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def add_channel(self, server_id: str, server_name: str, channel_id: str, channel_name: str, enabled: bool = True):
        conn = self._get_connection()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO channels (server_id, server_name, channel_id, channel_name, enabled) VALUES (?, ?, ?, ?, ?)",
                (server_id.strip(), server_name.strip(), channel_id.strip(), channel_name.strip(), 1 if enabled else 0)
            )
            conn.commit()
        finally:
            conn.close()

    def delete_channel(self, channel_id: str):
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM channels WHERE channel_id = ?", (str(channel_id).strip(),))
            conn.commit()
        finally:
            conn.close()

    def toggle_channel(self, channel_id: str, enabled: bool):
        conn = self._get_connection()
        try:
            conn.execute("UPDATE channels SET enabled = ? WHERE channel_id = ?", (1 if enabled else 0, str(channel_id).strip()))
            conn.commit()
        finally:
            conn.close()

    def get_channel_ids(self) -> List[str]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT channel_id FROM channels WHERE enabled = 1")
            return [str(r["channel_id"]).strip() for r in cursor.fetchall()]
        finally:
            conn.close()

    def set_channel_ids(self, channel_ids: List[str]):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT channel_id, server_id, server_name, channel_name, enabled FROM channels")
            existing = {str(r["channel_id"]).strip(): dict(r) for r in cursor.fetchall()}

            conn.execute("DELETE FROM channels")
            for cid in channel_ids:
                clean_cid = str(cid).strip()
                if clean_cid:
                    ex = existing.get(clean_cid)
                    if ex and ex.get("server_name") and ex["server_name"] not in ("0", "Sniper Channel", ""):
                        s_id = str(ex.get("server_id", "0"))
                        s_name = str(ex.get("server_name", "Discord Server"))
                        c_name = str(ex.get("channel_name", f"channel-{clean_cid[-4:]}"))
                        enabled = int(ex.get("enabled", 1))
                    else:
                        s_id = "0"
                        s_name = "Discord Server"
                        c_name = f"channel-{clean_cid[-4:]}"
                        enabled = 1
                    conn.execute(
                        "INSERT OR REPLACE INTO channels (server_id, server_name, channel_id, channel_name, enabled) VALUES (?, ?, ?, ?, ?)",
                        (s_id, s_name, clean_cid, c_name, enabled)
                    )
            conn.commit()
        finally:
            conn.close()

    def update_channel_metadata(self, channel_id: str, server_id: str, server_name: str, channel_name: str):
        """Updates the resolved server name, server ID, and channel name for a monitored channel."""
        clean_cid = str(channel_id).strip()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE channels SET server_id = ?, server_name = ?, channel_name = ? WHERE channel_id = ?",
                (str(server_id).strip(), str(server_name).strip(), str(channel_name).strip(), clean_cid)
            )
            if cursor.rowcount == 0:
                conn.execute(
                    "INSERT OR REPLACE INTO channels (server_id, server_name, channel_id, channel_name, enabled) VALUES (?, ?, ?, ?, ?)",
                    (str(server_id).strip(), str(server_name).strip(), clean_cid, str(channel_name).strip(), 1)
                )
            conn.commit()
        finally:
            conn.close()

    # --- Profiles ---
    def get_profiles(self) -> List[KeywordProfile]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM profiles ORDER BY priority DESC")
            results = []
            for row in cursor.fetchall():
                try:
                    kws = json.loads(row["keywords"]) if row["keywords"] else []
                except Exception:
                    kws = []
                try:
                    ex_kws = json.loads(row["exclude_keywords"]) if row["exclude_keywords"] else []
                except Exception:
                    ex_kws = []

                results.append(KeywordProfile(
                    id=row["id"],
                    name=row["name"],
                    category=row["category"],
                    keywords=kws,
                    is_regex=bool(row["is_regex"]),
                    priority=int(row["priority"]),
                    enabled=bool(row["enabled"]),
                    pause_duration=int(row["pause_duration"] or 0),
                    exclude_keywords=ex_kws
                ))
            return results
        finally:
            conn.close()

    def save_profile(self, profile: KeywordProfile):
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO profiles 
                (id, category, name, keywords, is_regex, priority, enabled, pause_duration, exclude_keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.id,
                profile.category,
                profile.name,
                json.dumps(profile.keywords),
                1 if profile.is_regex else 0,
                profile.priority,
                1 if profile.enabled else 0,
                profile.pause_duration,
                json.dumps(profile.exclude_keywords)
            ))
            conn.commit()
        finally:
            conn.close()

    def delete_profile(self, profile_id: str):
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
            conn.commit()
        finally:
            conn.close()

    # --- Blacklists ---
    def get_blacklist(self, item_type: str) -> List[str]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM blacklists WHERE type = ? ORDER BY value ASC", (item_type,))
            return [row["value"] for row in cursor.fetchall()]
        finally:
            conn.close()

    def add_blacklist_item(self, item_type: str, value: str):
        val = value.strip()
        if not val:
            return
        conn = self._get_connection()
        try:
            conn.execute("INSERT OR IGNORE INTO blacklists (type, value) VALUES (?, ?)", (item_type, val))
            conn.commit()
        finally:
            conn.close()

    def remove_blacklist_item(self, item_type: str, value: str):
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM blacklists WHERE type = ? AND value = ?", (item_type, value.strip()))
            conn.commit()
        finally:
            conn.close()

    # --- History ---
    def add_history_entry(
        self,
        server_name: str,
        channel_name: str,
        author_name: str,
        profile_name: str,
        keyword: str,
        link_code: str,
        protocol_url: str,
        latency_ms: float,
        status: str,
        error_reason: str = ""
    ):
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO history
                (timestamp, server_name, channel_name, author_name, profile_name, keyword, link_code, protocol_url, latency_ms, status, error_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                time.time(),
                server_name,
                channel_name,
                author_name,
                profile_name,
                keyword,
                link_code,
                protocol_url,
                latency_ms,
                status,
                error_reason
            ))
            conn.commit()
        finally:
            conn.close()

    def get_recent_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def clear_history(self):
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM history")
            conn.commit()
        finally:
            conn.close()
