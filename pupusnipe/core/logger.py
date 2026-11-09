"""
PupuSnipe Centralized Logging & Diagnostics System
Provides thread-safe in-memory ring buffer for UI console and persistent log file output.
"""
import os
import sys
import logging
from collections import deque
import threading
from typing import List, Callable, Optional


class RingBufferLogHandler(logging.Handler):
    def __init__(self, capacity: int = 1000, on_log: Optional[Callable[[str], None]] = None):
        super().__init__()
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)
        self.on_log = on_log
        self._lock = threading.Lock()

    def emit(self, record):
        try:
            msg = self.format(record)
            with self._lock:
                self.buffer.append(msg)
            if self.on_log:
                self.on_log(msg)
        except Exception:
            self.handleError(record)

    def get_logs(self) -> List[str]:
        with self._lock:
            return list(self.buffer)

    def clear(self):
        with self._lock:
            self.buffer.clear()


_ring_handler: Optional[RingBufferLogHandler] = None
_logger_initialized = False


def setup_logger(on_log_callback: Optional[Callable[[str], None]] = None) -> logging.Logger:
    global _ring_handler, _logger_initialized
    logger = logging.getLogger("PupuSnipe")
    
    if _logger_initialized:
        if on_log_callback and _ring_handler:
            _ring_handler.on_log = on_log_callback
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    # 1. Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # 2. Ring buffer handler for UI
    _ring_handler = RingBufferLogHandler(capacity=1000, on_log=on_log_callback)
    _ring_handler.setFormatter(formatter)
    logger.addHandler(_ring_handler)

    # 3. File handler in LocalAppData
    try:
        appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        log_dir = os.path.join(appdata, "PupuSnipe", "logs")
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(log_dir, "pupusnipe.log"), encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:
        pass

    _logger_initialized = True
    return logger


def get_logger() -> logging.Logger:
    return setup_logger()


def get_in_memory_logs() -> List[str]:
    if _ring_handler:
        return _ring_handler.get_logs()
    return []


def clear_in_memory_logs():
    if _ring_handler:
        _ring_handler.clear()
