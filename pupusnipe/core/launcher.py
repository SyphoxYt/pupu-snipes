"""
High-Speed Roblox Private Server Joining Engine
Handles instant protocol activation, process inspection, pre-warming, and microsecond latency timing.
Includes Sol Sniper V3 optimizations: leave-game automation, process restarts, and window management.
"""
import os
import sys
import time
import ctypes
import threading
import subprocess
import webbrowser
from typing import Optional, Dict, Any, Tuple
from collections import OrderedDict
from .browsers import find_browser_executable
from .logger import get_logger

logger = get_logger()

# Windows Process Entry for Toolhelp32 & Kernel Launch
if sys.platform == "win32":
    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.c_ulong),
            ("cntUsage", ctypes.c_ulong),
            ("th32ProcessID", ctypes.c_ulong),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", ctypes.c_ulong),
            ("cntThreads", ctypes.c_ulong),
            ("th32ParentProcessID", ctypes.c_ulong),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", ctypes.c_ulong),
            ("szExeFile", ctypes.c_char * 260)
        ]

    class STARTUPINFOW(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("lpReserved", ctypes.c_wchar_p),
            ("lpDesktop", ctypes.c_wchar_p),
            ("lpTitle", ctypes.c_wchar_p),
            ("dwX", ctypes.c_ulong),
            ("dwY", ctypes.c_ulong),
            ("dwXSize", ctypes.c_ulong),
            ("dwYSize", ctypes.c_ulong),
            ("dwXCountChars", ctypes.c_ulong),
            ("dwYCountChars", ctypes.c_ulong),
            ("dwFillAttribute", ctypes.c_ulong),
            ("dwFlags", ctypes.c_ulong),
            ("wShowWindow", ctypes.c_ushort),
            ("cbReserved2", ctypes.c_ushort),
            ("lpReserved2", ctypes.c_void_p),
            ("hStdInput", ctypes.c_void_p),
            ("hStdOutput", ctypes.c_void_p),
            ("hStdError", ctypes.c_void_p),
        ]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("hProcess", ctypes.c_void_p),
            ("hThread", ctypes.c_void_p),
            ("dwProcessId", ctypes.c_ulong),
            ("dwThreadId", ctypes.c_ulong),
        ]


class LaunchResult:
    __slots__ = (
        'success', 'protocol_url', 'launch_method', 'roblox_running_before',
        'latency_ms', 'timestamps', 'breakdown', 'error_message'
    )

    def __init__(
        self,
        success: bool,
        protocol_url: str,
        launch_method: str,
        roblox_running_before: bool,
        latency_ms: float,
        timestamps: Dict[str, float],
        breakdown: Dict[str, float],
        error_message: str = ""
    ):
        self.success = success
        self.protocol_url = protocol_url
        self.launch_method = launch_method
        self.roblox_running_before = roblox_running_before
        self.latency_ms = latency_ms
        self.timestamps = timestamps
        self.breakdown = breakdown
        self.error_message = error_message


class RobloxLauncher:
    """
    Sub-millisecond Roblox private server launcher.
    Prioritizes direct native Windows protocol invocation with process awareness.
    """

    def __init__(self, cooldown_seconds: int = 180, global_cooldown_seconds: int = 600):
        self.cooldown_seconds = cooldown_seconds
        self.global_cooldown_seconds = global_cooldown_seconds  # 10 minutes default
        self.last_join_time: float = 0.0
        self._joined_links: Dict[str, float] = OrderedDict()
        self._lock = threading.Lock()
        self._cached_exe_path: Optional[str] = None
        self._last_exe_scan: float = 0.0
        # Browser used for Turnstile-protected join pages (xe33hunt).
        self.gateway_browser: str = "default"
        self.gateway_browser_path: str = ""

    def get_cooldown_remaining(self) -> float:
        """Returns remaining seconds for the 10-minute global join cooldown, or 0.0 if ready."""
        with self._lock:
            if self.last_join_time <= 0:
                return 0.0
            elapsed = time.time() - self.last_join_time
            remaining = self.global_cooldown_seconds - elapsed
            return max(0.0, remaining)

    def is_on_global_cooldown(self) -> bool:
        """Returns True if the 10-minute join cooldown is currently active."""
        return self.get_cooldown_remaining() > 0.0

    def reset_global_cooldown(self):
        """Manually resets the 10-minute post-join cooldown so a new server can be joined immediately."""
        with self._lock:
            self.last_join_time = 0.0
            self._joined_links.clear()
        logger.info("[RobloxLauncher] 10-minute join cooldown manually reset! Ready to join new servers.")

    def is_roblox_running(self) -> bool:
        """
        Ultra-fast Windows Toolhelp32 process check for 'RobloxPlayerBeta.exe'.
        Bypasses slow shell / wmic calls for pure C performance (~0.5ms).
        """
        if sys.platform != "win32":
            return False

        try:
            kernel32 = ctypes.windll.kernel32
            snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
            if snapshot == -1:
                return False

            pe = PROCESSENTRY32()
            pe.dwSize = ctypes.sizeof(PROCESSENTRY32)

            success = kernel32.Process32First(snapshot, ctypes.byref(pe))
            while success:
                exe_name = pe.szExeFile.decode('utf-8', errors='ignore').lower()
                if "robloxplayerbeta" in exe_name:
                    kernel32.CloseHandle(snapshot)
                    return True
                success = kernel32.Process32Next(snapshot, ctypes.byref(pe))

            kernel32.CloseHandle(snapshot)
            return False
        except Exception:
            return False

    def kill_roblox_process(self):
        """Terminates RobloxPlayerBeta.exe if running."""
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/IM", "RobloxPlayerBeta.exe"], capture_output=True, timeout=2)
                logger.info("Terminated existing Roblox process before snipe.")
        except Exception as ex:
            logger.warning(f"Failed to kill Roblox process: {ex}")

    def execute_leave_game(self):
        """Sends Esc -> L -> Enter key sequence to leave existing game cleanly."""
        try:
            from pynput.keyboard import Controller, Key
            kb = Controller()
            kb.press(Key.esc)
            kb.release(Key.esc)
            time.sleep(0.08)
            kb.press('l')
            kb.release('l')
            time.sleep(0.08)
            kb.press(Key.enter)
            kb.release(Key.enter)
            logger.info("Executed leave game sequence (Esc -> L -> Enter).")
        except Exception as ex:
            logger.warning(f"Could not execute leave game sequence: {ex}")

    def minimize_other_windows(self):
        """Minimizes other windows to give Roblox focus."""
        if sys.platform != "win32":
            return
        try:
            user32 = ctypes.windll.user32
            def enum_proc(hwnd, lParam):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value
                        if "Roblox" not in title and "PupuSnipe" not in title:
                            user32.ShowWindow(hwnd, 6) # SW_MINIMIZE
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            user32.EnumWindows(WNDENUMPROC(enum_proc), 0)
        except Exception:
            pass

    def is_duplicate(self, link_code: str) -> bool:
        """Checks if this linkCode was already processed within the cooldown window."""
        with self._lock:
            now = time.time()
            expired = [k for k, t in self._joined_links.items() if now - t > self.cooldown_seconds]
            for k in expired:
                del self._joined_links[k]
            return link_code in self._joined_links

    def record_join(self, link_code: str):
        """Records join attempt to avoid immediate duplicates."""
        with self._lock:
            self._joined_links[link_code] = time.time()

    def find_roblox_executable(self, force_vanilla: bool = True) -> Optional[str]:
        """
        Locates the vanilla Normal Roblox player executable (RobloxPlayerBeta.exe).
        Prioritizes official %LOCALAPPDATA%\\Roblox\\Versions to completely bypass Voidstrap wrapper latency.
        """
        now = time.time()
        if self._cached_exe_path and (now - self._last_exe_scan < 300) and os.path.exists(self._cached_exe_path):
            return self._cached_exe_path

        local_app_data = os.environ.get("LOCALAPPDATA", "")
        search_dirs = []

        # 1. Primary Priority: Official Normal Roblox directory
        if local_app_data:
            search_dirs.append(os.path.join(local_app_data, "Roblox", "Versions"))

        prog_files = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        search_dirs.append(os.path.join(prog_files, "Roblox", "Versions"))

        prog_files_64 = os.environ.get("ProgramFiles", r"C:\Program Files")
        search_dirs.append(os.path.join(prog_files_64, "Roblox", "Versions"))

        # Fallback to bootstrapper directories only if normal Roblox not found
        if not force_vanilla:
            if local_app_data:
                search_dirs.append(os.path.join(local_app_data, "Bloxstrap", "Versions"))
                search_dirs.append(os.path.join(local_app_data, "Voidstrap", "Versions"))
                search_dirs.append(os.path.join(local_app_data, "Voidstrap", "RblxVersions"))
            search_dirs.append(r"D:\Void Strap 67\RblxVersions")

        best_path = None
        latest_mtime = 0.0

        for base_dir in search_dirs:
            if not os.path.isdir(base_dir):
                continue
            try:
                for folder in os.listdir(base_dir):
                    full_folder = os.path.join(base_dir, folder)
                    if os.path.isdir(full_folder):
                        for exe_name in ["RobloxPlayerBeta.exe", "RobloxPlayerLauncher.exe"]:
                            target = os.path.join(full_folder, exe_name)
                            if os.path.exists(target):
                                try:
                                    mtime = os.path.getmtime(target)
                                    if mtime > latest_mtime:
                                        latest_mtime = mtime
                                        best_path = target
                                except OSError:
                                    continue
            except Exception:
                continue

        if best_path:
            self._cached_exe_path = best_path
            self._last_exe_scan = now
            logger.info(f"Using Normal Roblox Player executable (Fastest): {best_path}")
            return best_path

        # If vanilla was forced but not found, fallback to any available bootstrapper
        if force_vanilla and not best_path:
            return self.find_roblox_executable(force_vanilla=False)

        return best_path

    def find_bootstrapper_executable(self) -> Optional[str]:
        """Locates custom bootstrapper (Voidstrap or Bloxstrap) if installed."""
        candidates = [
            r"D:\Void Strap 67\Voidstrap.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Voidstrap", "Voidstrap.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Bloxstrap", "Bloxstrap.exe"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        return None

    def prewarm_client(self) -> bool:
        """Pre-warms the Roblox client so that subsequent link joins connect immediately."""
        if self.is_roblox_running():
            return True

        try:
            boot = self.find_bootstrapper_executable()
            if boot:
                subprocess.Popen([boot], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            exe = self.find_roblox_executable()
            if exe:
                subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            else:
                os.startfile("roblox://")
                return True
        except Exception:
            return False

    def _resolve_gateway_browser_path(self) -> Optional[str]:
        """Returns the selected browser executable, or None for the OS default."""
        return find_browser_executable(self.gateway_browser, self.gateway_browser_path)

    def _open_web_join_gateway(self, url: str) -> bool:
        """
        Opens Turnstile-protected join pages in a real browser.
        These pages intentionally hide the Roblox URL until Cloudflare verifies
        the browser, then submit directly to roblox:// and join the server.

        If a specific browser is selected, it is launched directly so the page
        reuses that browser's profile, cookies, and Roblox session.
        """
        browser_path = self._resolve_gateway_browser_path()
        if browser_path:
            try:
                subprocess.Popen(
                    [browser_path, url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                logger.info(f"Opened protected join page in {self.gateway_browser}: {url}")
                return True
            except Exception as ex:
                logger.warning(f"Selected browser could not open join page: {ex}")

        try:
            if webbrowser.open(url, new=2):
                logger.info(f"Opened protected join page in default browser: {url}")
                return True
        except Exception as ex:
            logger.warning(f"Default browser could not open join page: {ex}")

        try:
            if sys.platform == "win32":
                result = ctypes.windll.shell32.ShellExecuteW(None, "open", url, None, None, 1)
                if result > 32:
                    logger.info(f"Opened protected join page via Windows shell: {url}")
                    return True
            else:
                os.startfile(url)
                return True
        except Exception as ex:
            logger.warning(f"Could not open protected join page: {ex}")
        return False

    def resolve_and_launch_web_gateway(
        self,
        gateway_url: str,
        link_code: str,
        method: str = "protocol",
        client: str = "voidstrap",
        recv_time: Optional[float] = None,
        extract_time: Optional[float] = None,
        match_time: Optional[float] = None,
        close_roblox_before: bool = False,
        leave_game_before: bool = False,
        minimize_other: bool = False,
        timeout: float = 20.0,
    ) -> Tuple[LaunchResult, Any]:
        """
        Resolves a Turnstile-protected join page into a native ``roblox://`` URL
        and dispatches it through the normal launcher.

        The browser work is intentionally kept out of the Discord event loop: the
        caller should run this method on a background thread. If Cloudflare cannot
        be satisfied automatically, the page is opened visibly so the user can
        finish the verification manually.
        """
        from .gateway_resolver import resolve_gateway_url

        t_resolve_start = time.time()
        resolution = resolve_gateway_url(
            gateway_url,
            browser_id=self.gateway_browser,
            custom_path=self.gateway_browser_path,
            timeout=timeout,
        )
        resolve_ms = (time.time() - t_resolve_start) * 1000.0

        if resolution.status == "resolved" and resolution.roblox_url:
            result = self.launch(
                protocol_url=resolution.roblox_url,
                link_code=link_code,
                method=method,
                client=client,
                recv_time=recv_time,
                extract_time=extract_time,
                match_time=match_time,
                close_roblox_before=close_roblox_before,
                leave_game_before=leave_game_before,
                minimize_other=minimize_other,
            )
            result.breakdown["resolve_ms"] = resolve_ms
            return result, resolution

        if resolution.status in ("expired", "not_found"):
            # The link is dead; do not open a browser. Remember it so repeated
            # Discord messages do not spawn the browser again.
            self.record_join(link_code)
            t_failed = time.time()
            t_recv = recv_time or t_resolve_start
            latency_ms = (t_failed - t_recv) * 1000.0
            return LaunchResult(
                success=False,
                protocol_url=gateway_url,
                launch_method="gateway_resolver",
                roblox_running_before=False,
                latency_ms=latency_ms,
                timestamps={
                    "received": t_recv,
                    "resolved": t_failed,
                    "failed": t_failed,
                },
                breakdown={
                    "extract_ms": (extract_time - t_recv) * 1000.0 if extract_time else 0.0,
                    "match_ms": (match_time - extract_time) * 1000.0 if extract_time and match_time else 0.0,
                    "resolve_ms": resolve_ms,
                    "total_ms": latency_ms,
                },
                error_message=resolution.message or resolution.status,
            ), resolution

        # timeout / challenge_failed / unsupported / error: fall back to a
        # visible browser so the user can finish the Cloudflare check.
        logger.warning(
            f"[GatewayResolver] Falling back to the browser: {resolution.status}"
            + (f" ({resolution.message})" if resolution.message else "")
        )
        result = self.launch(
            protocol_url=gateway_url,
            link_code=link_code,
            method=method,
            client=client,
            recv_time=recv_time,
            extract_time=extract_time,
            match_time=match_time,
            close_roblox_before=close_roblox_before,
            leave_game_before=leave_game_before,
            minimize_other=minimize_other,
        )
        result.breakdown["resolve_ms"] = resolve_ms
        return result, resolution

    @staticmethod
    def _win32_fast_spawn(exe_path: str, protocol_url: str) -> bool:
        """
        Pure Win32 CreateProcessW invocation (<0.005ms).
        Assigns HIGH_PRIORITY_CLASS (0x00000080) directly in the Windows kernel for maximum CPU scheduling priority.
        """
        if sys.platform != "win32":
            return False
        try:
            cmd = f'"{exe_path}" {protocol_url}'
            si = STARTUPINFOW()
            si.cb = ctypes.sizeof(STARTUPINFOW)
            pi = PROCESS_INFORMATION()
            # HIGH_PRIORITY_CLASS (0x00000080)
            flags = 0x00000080
            res = ctypes.windll.kernel32.CreateProcessW(
                None,
                cmd,
                None,
                None,
                False,
                flags,
                None,
                None,
                ctypes.byref(si),
                ctypes.byref(pi)
            )
            if res:
                ctypes.windll.kernel32.CloseHandle(pi.hProcess)
                ctypes.windll.kernel32.CloseHandle(pi.hThread)
                return True
            return False
        except Exception:
            return False

    def launch(
        self,
        protocol_url: str,
        link_code: str,
        method: str = "protocol",
        client: str = "voidstrap",
        recv_time: Optional[float] = None,
        extract_time: Optional[float] = None,
        match_time: Optional[float] = None,
        close_roblox_before: bool = False,
        leave_game_before: bool = False,
        minimize_other: bool = False,
        ignore_cooldown: bool = False
    ) -> LaunchResult:
        """
        Instantly triggers the private server join workflow.
        Returns measured timestamps and full latency breakdown.
        """
        t_recv = recv_time or time.time()
        t_extracted = extract_time or t_recv
        t_matched = match_time or t_extracted
        t_start_launch = time.time()

        timestamps = {
            "received": t_recv,
            "extracted": t_extracted,
            "matched": t_matched,
            "launch_started": t_start_launch
        }

        # Check 5-minute global post-join cooldown
        if not ignore_cooldown and self.is_on_global_cooldown():
            rem = self.get_cooldown_remaining()
            mins = int(rem // 60)
            secs = int(rem % 60)
            return LaunchResult(
                success=False,
                protocol_url=protocol_url,
                launch_method=method,
                roblox_running_before=False,
                latency_ms=0.0,
                timestamps=timestamps,
                breakdown={},
                error_message=f"5-minute join cooldown active ({mins}m {secs:02d}s remaining)"
            )

        # Check duplicate (bypassed if ignore_cooldown is True, e.g. for speed benchmark testing)
        if not ignore_cooldown and self.is_duplicate(link_code):
            return LaunchResult(
                success=False,
                protocol_url=protocol_url,
                launch_method=method,
                roblox_running_before=False,
                latency_ms=0.0,
                timestamps=timestamps,
                breakdown={},
                error_message=f"Duplicate link ignored (Cooldown active for {link_code[:8]}...)"
            )

        roblox_was_running = self.is_roblox_running()

        # Handle leave game or close roblox options
        if roblox_was_running:
            if leave_game_before:
                self.execute_leave_game()
            if close_roblox_before:
                self.kill_roblox_process()
                roblox_was_running = False

        if minimize_other:
            self.minimize_other_windows()

        is_web_gateway = protocol_url.lower().startswith(("http://", "https://"))

        try:
            launched_successfully = False

            # 0. Turnstile-protected join page: hand off to the default browser.
            if is_web_gateway:
                launched_successfully = self._open_web_join_gateway(protocol_url)
                if not launched_successfully:
                    raise RuntimeError("Could not open the protected join page in a browser")

            # 1. User Choice: Voidstrap
            elif client == "voidstrap":
                boot = self.find_bootstrapper_executable()
                if boot:
                    subprocess.Popen(
                        [boot, "-player", protocol_url],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0
                    )
                    launched_successfully = True

            # 2. User Choice: Normal Roblox (Vanilla RobloxPlayerBeta.exe)
            elif client == "vanilla":
                exe = self.find_roblox_executable(force_vanilla=True)
                if exe:
                    subprocess.Popen(
                        [exe, protocol_url],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0
                    )
                    launched_successfully = True

            # 3. Default / Fallback: Windows Native Protocol Handler (Universal & Secure)
            if not launched_successfully:
                if sys.platform == "win32":
                    res = ctypes.windll.shell32.ShellExecuteW(None, "open", protocol_url, None, None, 1)
                    if res <= 32:
                        os.startfile(protocol_url)
                else:
                    os.startfile(protocol_url)

            t_launched = time.time()
            timestamps["launched"] = t_launched

            total_latency_ms = (t_launched - t_recv) * 1000.0
            breakdown = {
                "extract_ms": (t_extracted - t_recv) * 1000.0,
                "match_ms": (t_matched - t_extracted) * 1000.0,
                "launch_exec_ms": (t_launched - t_start_launch) * 1000.0,
                "total_ms": total_latency_ms
            }

            if not ignore_cooldown:
                self.record_join(link_code)
                with self._lock:
                    self.last_join_time = time.time()

            return LaunchResult(
                success=True,
                protocol_url=protocol_url,
                launch_method=method,
                roblox_running_before=roblox_was_running,
                latency_ms=total_latency_ms,
                timestamps=timestamps,
                breakdown=breakdown
            )
        except Exception as ex:
            t_fail = time.time()
            timestamps["failed"] = t_fail
            total_latency_ms = (t_fail - t_recv) * 1000.0
            breakdown = {
                "extract_ms": (t_extracted - t_recv) * 1000.0,
                "match_ms": (t_matched - t_extracted) * 1000.0,
                "launch_exec_ms": (t_fail - t_start_launch) * 1000.0,
                "total_ms": total_latency_ms
            }
            return LaunchResult(
                success=False,
                protocol_url=protocol_url,
                launch_method=method,
                roblox_running_before=roblox_was_running,
                latency_ms=total_latency_ms,
                timestamps=timestamps,
                breakdown=breakdown,
                error_message=str(ex)
            )
