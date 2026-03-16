"""Periodic cleanup of expired session directories.

Each Streamlit session stores its IFC and JSONL artefacts in directories
named after a random session token (``Dashboard/static/<session_id>/``
and ``Dashboard/data/<session_id>/``).  This module provides a
lightweight background thread that deletes directories whose contents
have not been modified for longer than *SESSION_TTL_SECONDS*.
"""

import logging
import os
import shutil
import threading
import time

logger = logging.getLogger(__name__)

# Default TTL: 2 hours.  Override via the ``SESSION_TTL_SECONDS``
# environment variable if desired.
SESSION_TTL_SECONDS: int = int(os.environ.get("SESSION_TTL_SECONDS", "7200"))

# How often the cleanup thread wakes up and scans.
_CLEANUP_INTERVAL_SECONDS: int = 300  # 5 minutes

# Module-level flag so only one cleanup thread is ever started, even
# when Streamlit re-runs the top-level script multiple times.
_cleanup_started = False
_cleanup_lock = threading.Lock()


def _newest_mtime(directory: str) -> float:
    """Return the newest ``st_mtime`` of any file inside *directory*."""
    newest = 0.0
    for root, _dirs, files in os.walk(directory):
        for fname in files:
            try:
                mtime = os.path.getmtime(os.path.join(root, fname))
                if mtime > newest:
                    newest = mtime
            except OSError:
                continue
    return newest


def _cleanup_expired(base_dirs: list[str], ttl: int) -> None:
    """Delete subdirectories of *base_dirs* that are older than *ttl* seconds."""
    now = time.time()
    for base in base_dirs:
        if not os.path.isdir(base):
            continue
        for entry in os.listdir(base):
            sub = os.path.join(base, entry)
            if not os.path.isdir(sub):
                continue
            try:
                age = now - _newest_mtime(sub)
                if age > ttl:
                    shutil.rmtree(sub, ignore_errors=False)
                    logger.info("Cleaned up expired session dir: %s (age %.0fs)", sub, age)
            except OSError as exc:
                logger.warning("Failed to remove session dir %s: %s", sub, exc)


def _cleanup_loop(base_dirs: list[str]) -> None:
    """Background loop – runs forever in a daemon thread."""
    while True:
        try:
            _cleanup_expired(base_dirs, SESSION_TTL_SECONDS)
        except Exception:
            logger.exception("Session cleanup error")
        time.sleep(_CLEANUP_INTERVAL_SECONDS)


def start_cleanup_thread(*base_dirs: str) -> None:
    """Start the background cleanup thread (idempotent, at most once)."""
    global _cleanup_started
    with _cleanup_lock:
        if _cleanup_started:
            return
        _cleanup_started = True

    dirs = [d for d in base_dirs if d]
    t = threading.Thread(target=_cleanup_loop, args=(dirs,), daemon=True)
    t.start()
    logger.info("Session cleanup thread started (TTL=%ds, interval=%ds)", SESSION_TTL_SECONDS, _CLEANUP_INTERVAL_SECONDS)
