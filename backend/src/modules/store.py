"""Ledger store — manages the on-disk store directory.

The store directory is used for file uploads and any other files that need to
persist across server restarts.  Dedup hashes and categorize rules are now
stored in SQLite (see db/models/); this module retains only directory-level
configuration used by the CLI and health endpoints.

The store directory defaults to ``./ledger_store`` relative to this file and
can be overridden via the ``LEDGER_STORE_DIR`` environment variable or by
calling ``configure_store_dir()`` at startup.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Store root ────────────────────────────────────────────────────────────────

_DEFAULT_STORE_DIR = Path(__file__).parent.parent / "ledger_store"

_store_dir: Path = Path(os.environ.get("LEDGER_STORE_DIR", str(_DEFAULT_STORE_DIR)))

# When False, write operations are no-ops.  Set to False in test suites.
_PERSIST_ENABLED: bool = True


def configure_store_dir(path: str | Path) -> None:
    """Override the store directory at startup (call before first use)."""
    global _store_dir
    _store_dir = Path(path)
    _store_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Ledger store dir set to: %s", _store_dir.resolve())


def configure_persistence(enabled: bool) -> None:
    """Enable or disable on-disk persistence (used by test suites)."""
    global _PERSIST_ENABLED
    _PERSIST_ENABLED = enabled
    logger.debug("Store persistence %s", "enabled" if enabled else "disabled")


def get_store_dir() -> Path:
    return _store_dir


# ── Store status (for CLI / health reporting) ─────────────────────────────────

def store_stats() -> dict:
    """Return basic stats about the current store directory."""
    return {"store_dir": str(_store_dir.resolve()), "exists": _store_dir.is_dir()}
