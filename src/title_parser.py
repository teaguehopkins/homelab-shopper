import re
from typing import TypedDict, Optional
import logging

logger = logging.getLogger(__name__)

class ParsedTitle(TypedDict):
    cpu_model: str
    generic_intel_core_type: Optional[str]
    is_generic_intel_core_type: bool
    ram: str
    storage: str

# Pre-compile regex patterns for performance
_CPU_RE = re.compile(r"(?:(i[3579])(?:[\s-]?([\d]{4,5}[a-z\d]*))?|(?<![a-z0-9])n(\d{3,4})(?![a-z0-9]))", re.I)
_STORAGE_RE = re.compile(
    r"(\d+\.?\d*\s*(?:TB|GB))\s*(?:SSD|HDD|NVME|SSHD|STORAGE|DRIVE|EMMC)|"
    r"(?:SSD|HDD|NVME|SSHD|STORAGE|DRIVE|EMMC)\s*(\d+\.?\d*\s*(?:TB|GB))",
    re.I,
)
_RAM_RE = re.compile(r"(\d+\s*GB)\s*RAM|RAM\s*(\d+\s*GB)|(\d+GB)\s*(?:DDR[345])", re.I)

_GENERIC_CPU_KEYWORDS = {
    'celeron': 'CELERON',
    'pentium': 'PENTIUM',
    'atom': 'ATOM',
    'xeon': 'XEON',
    'ryzen': 'RYZEN',
    'athlon': 'ATHLON',
}


def parse_title(title_raw: str) -> ParsedTitle:
    """Extract CPU model, RAM amount, and storage capacity from an eBay title.

    Returns a dict with uppercase, whitespace-stripped values or 'N/A' when not found.
    """
    title = title_raw.lower()

    cpu_model: str = ''
    is_generic_i_core = False
    generic_i_core_type: Optional[str] = None

    cpu_match = _CPU_RE.search(title)
    if cpu_match:
        i_core_family = cpu_match.group(1)
        i_core_digits = cpu_match.group(2)
        n_series = cpu_match.group(3)
        if i_core_family and i_core_digits:
            cpu_model = f"{i_core_family.upper()}-{i_core_digits.upper()}"
            generic_i_core_type = i_core_family.upper()
        elif i_core_family:
            cpu_model = i_core_family.upper()
            generic_i_core_type = cpu_model
            is_generic_i_core = True
        elif n_series:
            cpu_model = f"N{n_series.upper()}"

    # Generic fall-back keywords (Celeron, Ryzen...)
    if not cpu_model:
        for kw, rep in _GENERIC_CPU_KEYWORDS.items():
            if kw in title:
                cpu_model = rep
                break

    if not cpu_model and 'no cpu' in title:
        cpu_model = 'None'
        generic_i_core_type = 'None'

    if not cpu_model:
        cpu_model = 'N/A'

    # --- Storage ---
    storage = 'N/A'
    storage_match = _STORAGE_RE.search(title)
    if storage_match:
        storage = (storage_match.group(1) or storage_match.group(2) or '').upper().replace(' ', '')

    # --- RAM ---
    ram = 'N/A'
    ram_match = _RAM_RE.search(title)
    if ram_match:
        ram = (ram_match.group(1) or ram_match.group(2) or ram_match.group(3) or '').upper().replace(' ', '')

    # Fallback: look for standalone values like "8GB" not directly followed by storage keywords
    if ram == 'N/A':
        storage_keywords = {"SSD", "HDD", "NVME", "SSHD", "EMMC", "DRIVE", "STORAGE"}
        # Tokenize by whitespace and common separators
        tokens = re.split(r"[\s,;/]+", title.upper())
        for idx, tok in enumerate(tokens):
            gb_match = re.fullmatch(r"(\d+)GB", tok)
            if gb_match:
                # Skip if the token is immediately followed or preceded by a storage keyword
                next_tok = tokens[idx + 1] if idx + 1 < len(tokens) else ""
                prev_tok = tokens[idx - 1] if idx - 1 >= 0 else ""
                if next_tok in storage_keywords or prev_tok in storage_keywords:
                    continue  # Likely describing storage, not RAM
                ram = f"{gb_match.group(1)}GB"
                break

    return ParsedTitle(
        cpu_model=cpu_model,
        generic_intel_core_type=generic_i_core_type,
        is_generic_intel_core_type=is_generic_i_core,
        ram=ram,
        storage=storage,
    ) 