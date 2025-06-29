import time
import logging
import re
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent  # repository root

@lru_cache(maxsize=1)
def load_passmark_data(filepath: str = 'passmark.txt') -> dict[str, int]:
    """Return a mapping of *upper-cased* CPU name -> PassMark score."""
    scores: dict[str, int] = {}
    start = time.time()
    file_path = DATA_DIR / filepath
    if not file_path.exists():
        logger.error("PassMark file not found at '%s'", file_path)
        return scores

    with file_path.open(encoding='utf-8') as fh:
        for line in fh:
            parts = line.strip().split('\t')
            if len(parts) != 2:
                continue
            name, score_raw = parts
            try:
                scores[name.strip().upper()] = int(score_raw.replace(',', '').strip())
            except ValueError:
                logger.warning("Could not parse score '%s' for CPU '%s'", score_raw, name)

    logger.info("Loaded %d PassMark scores in %.2fs", len(scores), time.time() - start)
    return scores

@lru_cache(maxsize=1)
def load_idle_power_data(filepath: str = 'idlepower.txt') -> dict[str, float]:
    """Return mapping of *upper-cased* CPU name -> idle power (Watts)."""
    data: dict[str, float] = {}
    start = time.time()
    file_path = DATA_DIR / filepath
    if not file_path.exists():
        logger.error("Idle power file not found at '%s'", file_path)
        return data

    with file_path.open(encoding='utf-8') as fh:
        next(fh, None)  # skip header if present
        for line in fh:
            line_content = line.strip()
            if not line_content:
                continue
            match = re.match(r"^(.*?)(\s+[\d\.]+)$", line_content)
            if not match:
                continue
            name_part = match.group(1).strip().upper()
            power_part = match.group(2).strip()
            try:
                data[name_part] = float(power_part)
            except ValueError:
                logger.warning("Could not parse idle power '%s' for CPU '%s'", power_part, name_part)

    logger.info("Loaded %d idle-power entries in %.2fs", len(data), time.time() - start)
    return data

# Load once at import for backwards compatibility
PASSMARK_SCORES = load_passmark_data()
IDLE_POWER_DATA = load_idle_power_data() 