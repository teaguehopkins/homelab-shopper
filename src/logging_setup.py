"""Central logging configuration for the whole application.

Call ``configure()`` once in each executable entry-point (Flask app startup,
CLI scripts, tests).  Subsequent calls become no-ops so it's safe to import
widely.
"""

from __future__ import annotations

import logging
import os


def configure() -> None:
    """Initialise root logger unless it's already configured."""

    if logging.getLogger().handlers:  # pragma: no cover – already configured
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    ) 